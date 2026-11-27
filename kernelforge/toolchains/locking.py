"""Directory ownership locks; serialize stale recovery with an OS lock.

Guard files are intentionally persistent: removing a guard while another
process has it open would split the lock domain. Old directory locks without
a verifiable owner fail closed. Not a distributed/network filesystem lock.
"""
from __future__ import annotations

import errno
import json
import os
import socket
import stat
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


class LockTimeout(TimeoutError):
    pass


def _linked(path):
    try:
        info = path.lstat()
        return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) &
                                        getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    except FileNotFoundError:
        return False


def _check_path(path):
    if any(_linked(p) for p in (path, *path.parents)):
        raise LockTimeout("linked lock path refused")


@contextmanager
def _guard(path, deadline, poll):
    _check_path(path)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    locked = False
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise LockTimeout("unsafe lock guard file")
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if time.monotonic() >= deadline:
                    raise LockTimeout("timed out waiting for lock recovery guard") from exc
                time.sleep(poll)
        yield
    finally:
        try:
            if locked:
                if os.name == "nt":
                    import msvcrt
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


class FileLock:
    def __init__(self, path: Path, timeout: float = 120, stale_after: float = 21600, poll: float = 0.05):
        self.path = Path(path).absolute()
        self.timeout, self.stale_after, self.poll = timeout, stale_after, poll
        self.acquired = False
        self.token = uuid.uuid4().hex

    def _read_owner(self):
        p = self.path / "owner.json"
        if _linked(p) or not p.is_file() or p.stat().st_size > 4096 or p.stat().st_nlink != 1:
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    @property
    def guard(self):
        return self.path.with_name("." + self.path.name + ".guard")

    def __enter__(self):
        if self.acquired:
            raise LockTimeout("lock is not reentrant")
        deadline = time.monotonic() + self.timeout
        _check_path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            with _guard(self.guard, deadline, self.poll):
                _check_path(self.path)
                try:
                    self.path.mkdir()
                except FileExistsError:
                    owner = self._read_owner() if self.path.is_dir() else None
                    if (owner and type(owner.get("pid")) is int and owner["pid"] > 0
                            and owner.get("host") == socket.gethostname()
                            and time.time() - self.path.stat().st_mtime > self.stale_after
                            and not _pid_alive(owner["pid"])
                            and {p.name for p in self.path.iterdir()} == {"owner.json"}):
                        (self.path / "owner.json").unlink()
                        self.path.rmdir()
                        continue
                else:
                    owner_path = self.path / "owner.json"
                    # Retain ambiguous ownership state if recording fails.
                    with owner_path.open("x", encoding="utf-8") as stream:
                        json.dump({"pid": os.getpid(), "host": socket.gethostname(),
                                   "created": time.time(), "token": self.token}, stream)
                    self.acquired = True
                    return self
            if time.monotonic() >= deadline:
                raise LockTimeout(f"timed out waiting for toolchain lock: {self.path}")
            time.sleep(self.poll)

    def __exit__(self, *_exc):
        if self.acquired:
            try:
                with _guard(self.guard, time.monotonic() + max(self.timeout, 1), self.poll):
                    _check_path(self.path)
                    owner = self._read_owner()
                    if not owner or owner.get("token") != self.token:
                        raise LockTimeout("lock ownership changed; original state retained")
                    if {p.name for p in self.path.iterdir()} != {"owner.json"}:
                        raise LockTimeout("unexpected lock contents; original state retained")
                    (self.path / "owner.json").unlink()
                    self.path.rmdir()
            finally:
                self.acquired = False


def _pid_alive(pid) -> bool:
    # Unknown identity or query failure is NOT proof of death. In particular,
    # do not call Windows os.kill(pid, 0), which is not a portable liveness probe.
    if type(pid) is not int or not 0 < pid <= 0x7fffffff:
        return True
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        dll = ctypes.WinDLL("kernel32", use_last_error=True)
        dll.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        dll.OpenProcess.restype = wintypes.HANDLE
        dll.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        dll.WaitForSingleObject.restype = wintypes.DWORD
        dll.CloseHandle.argtypes = (wintypes.HANDLE,)
        dll.CloseHandle.restype = wintypes.BOOL
        handle = dll.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only
        if not handle:
            return ctypes.get_last_error() != 87  # ERROR_INVALID_PARAMETER
        try:
            return dll.WaitForSingleObject(handle, 0) != 0  # WAIT_OBJECT_0 means exited
        finally:
            dll.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except OSError:
        return True
