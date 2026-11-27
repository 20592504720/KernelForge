"""Run unittest on Windows and exit after verifying worker cleanup.

The Windows runner can keep a subprocess alive during interpreter finalization
after unittest has reported success. The suite and module teardown run normally;
this small entry point verifies that no worker threads remain, flushes output,
and then exits with the test result without waiting on stale interpreter state.
"""
from __future__ import annotations

import os
import signal
import sys
import threading
import time
import unittest
from pathlib import Path
from typing import TYPE_CHECKING, Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kernelforge.workspace import Workspace

workspace=Workspace.configured()
if workspace:
    os.environ.update(workspace.temporary_environment())
    import tempfile
    tempfile.tempdir=None

def _prepare_ci_fixture_owner() -> Path | None:
    """Use the current user's SID for newly created test objects only.

    Elevated hosted runners can default to the Administrators group as owner.
    Do not change existing filesystem ACLs, enable privileges, or relax the
    production cache ownership check. This dedicated test process exits after
    the suite; the parent runner's token and configuration are not changed.
    """
    if os.name != 'nt' or os.environ.get('GITHUB_ACTIONS') != 'true':
        return
    import ctypes
    import tempfile
    import uuid
    from ctypes import wintypes
    from kernelforge.python_environment import _owned_directory

    security = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    security.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    security.OpenProcessToken.restype = wintypes.BOOL
    security.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    security.GetTokenInformation.restype = wintypes.BOOL
    security.SetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    security.SetTokenInformation.restype = wintypes.BOOL
    security.EqualSid.argtypes = [wintypes.LPVOID, wintypes.LPVOID]
    security.EqualSid.restype = wintypes.BOOL
    token = wintypes.HANDLE()
    if not security.OpenProcessToken(kernel.GetCurrentProcess(), 0x88, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        def token_info(kind):
            needed = wintypes.DWORD()
            security.GetTokenInformation(token, kind, None, 0, ctypes.byref(needed))
            if not 0 < needed.value <= 65536:
                raise OSError('cannot inspect test token owner')
            data = ctypes.create_string_buffer(needed.value)
            if not security.GetTokenInformation(token, kind, data, needed.value, ctypes.byref(needed)):
                raise ctypes.WinError(ctypes.get_last_error())
            return data
        user, owner = token_info(1), token_info(4)
        user_sid = ctypes.cast(user, ctypes.POINTER(wintypes.LPVOID))[0]
        owner_sid = ctypes.cast(owner, ctypes.POINTER(wintypes.LPVOID))[0]
        changed = not security.EqualSid(user_sid, owner_sid)
        if changed:
            # TOKEN_OWNER contains one PSID; user buffer stays alive here.
            requested = wintypes.LPVOID(user_sid)
            if not security.SetTokenInformation(token, 4, ctypes.byref(requested), ctypes.sizeof(requested)):
                raise ctypes.WinError(ctypes.get_last_error())
            owner = token_info(4)
            if not security.EqualSid(user_sid, ctypes.cast(owner, ctypes.POINTER(wintypes.LPVOID))[0]):
                raise ValueError('test token owner did not match current user')
        security.ConvertSidToStringSidW.argtypes = [wintypes.LPVOID, ctypes.POINTER(wintypes.LPWSTR)]
        security.ConvertSidToStringSidW.restype = wintypes.BOOL
        kernel.LocalFree.argtypes = [wintypes.LPVOID]
        kernel.LocalFree.restype = wintypes.LPVOID
        sid_text = wintypes.LPWSTR()
        if not security.ConvertSidToStringSidW(user_sid, ctypes.byref(sid_text)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            sid = sid_text.value
        finally:
            kernel.LocalFree(sid_text)
    finally:
        kernel.CloseHandle(token)

    # The runner's default temp directory can inherit unrelated write grants.
    # Create a NEW fixture root with an explicit protected inheritable DACL.
    # No existing directory ACL is modified. Never print a user SID.
    class SecurityAttributes(ctypes.Structure):
        _fields_ = [('nLength', wintypes.DWORD),
                    ('lpSecurityDescriptor', wintypes.LPVOID),
                    ('bInheritHandle', wintypes.BOOL)]

    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.ULONG)]
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    kernel.CreateDirectoryW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(SecurityAttributes)]
    kernel.CreateDirectoryW.restype = wintypes.BOOL
    if not sid:
        raise ValueError('test token user SID is unavailable')
    descriptor = wintypes.LPVOID()
    sddl = f'O:{sid}D:P(A;OICI;FA;;;{sid})(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)'
    parent = Path(os.environ['RUNNER_TEMP']).resolve(strict=True)
    fixture_root = parent / ('kf-' + uuid.uuid4().hex[:12])
    if not security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl, 1, ctypes.byref(descriptor), None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        attributes = SecurityAttributes(ctypes.sizeof(SecurityAttributes), descriptor, False)
        if not kernel.CreateDirectoryW(str(fixture_root), ctypes.byref(attributes)):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.LocalFree(descriptor)

    try:
        # Check both the new root and a normal inherited child with the actual
        # production gate. If either is rejected, stop before test discovery.
        _owned_directory(fixture_root)
        with tempfile.TemporaryDirectory(prefix='owner-', dir=fixture_root) as folder:
            _owned_directory(Path(folder))
    except BaseException:
        os.rmdir(fixture_root)
        raise
    os.environ.update({key: str(fixture_root) for key in ('TEMP', 'TMP', 'TMPDIR')})
    tempfile.tempdir = str(fixture_root)
    print(f'WINDOWS_CI_FIXTURE_OWNER_VERIFIED changed={changed} private_root=True child=True', flush=True)
    return fixture_root


_ci_fixture_root = _prepare_ci_fixture_owner()

# Preserve the original SIGINT behavior and surface asynchronous console
# interrupts rather than misclassifying them as assertion failures or masking
# them as a passing CI run.
_current_test = {"name": "<not started>"}
_old_sigint = signal.getsignal(signal.SIGINT)

def _diagnose_sigint(signum, frame):
    print(f"WINDOWS_TEST_INTERRUPT pid={os.getpid()} test={_current_test['name']} "
          f"signal={signum} monotonic={time.monotonic():.3f}", file=sys.stderr, flush=True)
    if callable(_old_sigint):
        _old_sigint(signum, frame)
    # Never silently ignore SIGINT if a prior hook returns normally.
    raise KeyboardInterrupt

signal.signal(signal.SIGINT, _diagnose_sigint)

if TYPE_CHECKING:
    _TextTestResult = unittest.TextTestResult[Any]
else:
    _TextTestResult = unittest.TextTestResult


class DiagnosticResult(_TextTestResult):
    def startTest(self, test):
        _current_test["name"] = test.id()
        return super().startTest(test)

suite = unittest.defaultTestLoader.discover(
    str(ROOT / "tests"), pattern="test*.py"
)
print(f"WINDOWS_TEST_START pid={os.getpid()} python={sys.version.split()[0]} "
      f"tests={suite.countTestCases()} monotonic={time.monotonic():.3f}",
      file=sys.stderr, flush=True)
try:
    result = unittest.TextTestRunner(verbosity=2, resultclass=DiagnosticResult).run(suite)
except KeyboardInterrupt:
    print(f"WINDOWS_TEST_ABORTED pid={os.getpid()} test={_current_test['name']} "
          f"monotonic={time.monotonic():.3f}", file=sys.stderr, flush=True)
    raise
remaining = [thread.name for thread in threading.enumerate() if thread is not threading.main_thread()]
test_ok = result.wasSuccessful()
exit_code = 0 if test_ok and not remaining else 1
if remaining:
    print(f"unittest left worker threads running: {remaining}", file=sys.stderr, flush=True)
if _ci_fixture_root is not None and not remaining:
    try:
        # Never recursively delete a path or change permissions to force cleanup.
        os.rmdir(_ci_fixture_root)
        print('WINDOWS_CI_FIXTURE_ROOT_CLEANED', file=sys.stderr, flush=True)
    except OSError as exc:
        print(f'WINDOWS_CI_FIXTURE_ROOT_RETAINED error={getattr(exc, "winerror", None)}',
              file=sys.stderr, flush=True)
        exit_code = 1
print(f"WINDOWS_TEST_SUMMARY pid={os.getpid()} passed={test_ok} "
      f"ran={result.testsRun} errors={len(result.errors)} "
      f"failures={len(result.failures)} unexpected={len(result.unexpectedSuccesses)} "
      f"workers={remaining!r} exit={exit_code}", file=sys.stderr, flush=True)
sys.stdout.flush()
sys.stderr.flush()
os._exit(exit_code)
