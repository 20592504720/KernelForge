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
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

suite = unittest.defaultTestLoader.discover(
    str(ROOT / "tests"), pattern="test*.py"
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
remaining = [thread.name for thread in threading.enumerate() if thread is not threading.main_thread()]
if remaining:
    print(f"unittest left worker threads running: {remaining}", file=sys.stderr)
sys.stdout.flush()
sys.stderr.flush()
os._exit(0 if result.wasSuccessful() and not remaining else 1)
