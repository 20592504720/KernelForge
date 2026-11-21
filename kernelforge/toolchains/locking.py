"""Portable exclusive directory locks used by the toolchain cache."""
from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path


class LockTimeout(TimeoutError):
    pass


class FileLock:
    """Cross-platform lock based on atomic mkdir, with bounded stale recovery."""

    def __init__(self, path: Path, timeout: float = 120, stale_after: float = 21600, poll: float = 0.05):
        self.path, self.timeout, self.stale_after, self.poll = path, timeout, stale_after, poll
        self.acquired = False

    def __enter__(self):
        deadline = time.monotonic() + self.timeout
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self.path.mkdir()
                try:
                    (self.path / "owner.json").write_text(json.dumps({"pid": os.getpid(), "host": socket.gethostname(), "created": time.time()}), encoding="utf-8")
                except OSError:
                    (self.path / "owner.json").unlink(missing_ok=True)
                    self.path.rmdir()
                    raise
                self.acquired = True
                return self
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                    if age > self.stale_after:
                        owner_file = self.path / "owner.json"
                        owner = json.loads(owner_file.read_text(encoding="utf-8")) if owner_file.exists() else {}
                        # Only reclaim an old lock from this host when its PID is demonstrably gone.
                        if owner.get("host") == socket.gethostname() and not _pid_alive(owner.get("pid")):
                            owner_file.unlink(missing_ok=True)
                            self.path.rmdir()
                            continue
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    pass
                if time.monotonic() >= deadline:
                    raise LockTimeout(f"timed out waiting for toolchain lock: {self.path}")
                time.sleep(self.poll)

    def __exit__(self, *_exc):
        if self.acquired:
            try:
                (self.path / "owner.json").unlink(missing_ok=True)
                self.path.rmdir()
            finally:
                self.acquired = False


def _pid_alive(pid) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
