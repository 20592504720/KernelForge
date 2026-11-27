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

def _prepare_ci_fixture_owner():
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
    finally:
        kernel.CloseHandle(token)
    with tempfile.TemporaryDirectory(prefix='kf-owner-') as folder:
        _owned_directory(Path(folder))
    print(f'WINDOWS_CI_FIXTURE_OWNER_VERIFIED changed={changed}', flush=True)


_prepare_ci_fixture_owner()

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
print(f"WINDOWS_TEST_SUMMARY pid={os.getpid()} passed={test_ok} "
      f"ran={result.testsRun} errors={len(result.errors)} "
      f"failures={len(result.failures)} unexpected={len(result.unexpectedSuccesses)} "
      f"workers={remaining!r} exit={exit_code}", file=sys.stderr, flush=True)
sys.stdout.flush()
sys.stderr.flush()
os._exit(exit_code)
