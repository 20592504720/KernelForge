"""Windows CI unittest launcher: preserve all tests, isolate console events.

Run the existing full unittest suite in a separate Windows process group with
no console window. This keeps Ctrl-C events sent to the workflow shell's
console group from spuriously aborting the test interpreter. It does not mask
failures, shorten discovery, or change application/test code. Forward the
entire child output and exact exit status; record diagnostic metadata.
"""
from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/windows_test_runner.py"


def run_suite(*, creationflags: int,
              popen: Callable[..., subprocess.Popen[str]] = subprocess.Popen, stream=None,
              python=None, runner=None) -> int:
    """An injectable wrapper for offline verification of status propagation."""
    stream = stream if stream is not None else sys.stdout
    args = [python or sys.executable, "-u", str(runner or RUNNER)]
    stream.write(f"WINDOWS_LAUNCH_START process={os.getpid()} flags={creationflags} "
                 f"command=python -u scripts/windows_test_runner.py\\n")
    stream.flush()
    with popen(args, cwd=ROOT, stdin=subprocess.DEVNULL,
               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
               encoding="utf-8", errors="replace", bufsize=1,
               creationflags=creationflags) as process:
        if process.stdout is None:
            raise RuntimeError("Windows test launcher missing captured child output")
        for line in process.stdout:
            stream.write(line)
            stream.flush()
        code = process.wait()
    stream.write(f"WINDOWS_LAUNCH_EXIT child_exit={code}\\n")
    stream.flush()
    return int(code)


def main() -> int:
    if os.name != "nt":
        print("Windows test launcher only runs on Windows", file=sys.stderr)
        return 2
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    return run_suite(creationflags=flags)


if __name__ == "__main__":
    raise SystemExit(main())
