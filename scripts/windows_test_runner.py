"""Run unittest on Windows and exit after verifying worker cleanup.

The Windows runner can keep a subprocess alive during interpreter finalization
after unittest has reported success. The suite and module teardown run normally;
this small entry point verifies that no worker threads remain, flushes output,
and then exits with the test result without waiting on stale interpreter state.
"""
from __future__ import annotations

import os
import sys
import threading
import unittest
import signal
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kernelforge.workspace import Workspace
workspace=Workspace.configured()
if workspace:
    os.environ.update(workspace.temporary_environment())
    import tempfile
    tempfile.tempdir=None

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

class DiagnosticResult(unittest.TextTestResult):
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
