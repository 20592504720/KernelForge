"""Pinned local file access; caller-controlled storage is still a trust boundary.

POSIX walks use directory descriptors and O_NOFOLLOW. Windows pins each ancestor
without write/delete sharing and inspects opened handles for reparse points.
This is not a sandbox against an administrator or a writer with identical rights.
"""
from __future__ import annotations

import os
import stat
from contextlib import ExitStack, contextmanager
from pathlib import Path


def _win_open(path: Path, *, directory: bool):
    if os.name != 'nt':
        raise OSError('Windows file handle requested on a non-Windows host')
    import ctypes
    from ctypes import wintypes

    dll = ctypes.WinDLL('kernel32', use_last_error=True)
    dll.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                               wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    dll.CreateFileW.restype = wintypes.HANDLE
    dll.CloseHandle.argtypes = [wintypes.HANDLE]
    dll.CloseHandle.restype = wintypes.BOOL
    dll.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    dll.GetFileInformationByHandleEx.restype = wintypes.BOOL
    dll.GetFileType.argtypes = [wintypes.HANDLE]
    dll.GetFileType.restype = wintypes.DWORD
    text = str(path)
    if not text.startswith('\\\\?\\'):
        text = '\\\\?\\UNC\\' + text[2:] if text.startswith('\\\\') else '\\\\?\\' + text
    handle = dll.CreateFileW(text, 0x80 if directory else 0x80000000, 1, None, 3,
                             0x00200000 | 0x02000000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        attributes = (wintypes.DWORD * 2)()
        if not dll.GetFileInformationByHandleEx(handle, 9, attributes, ctypes.sizeof(attributes)):
            raise ctypes.WinError(ctypes.get_last_error())
        if attributes[0] & 0x400 or bool(attributes[0] & 0x10) != directory or dll.GetFileType(handle) != 1:
            raise ValueError('linked or nonregular file path refused')
    except BaseException:
        dll.CloseHandle(handle)
        raise
    return dll, handle


@contextmanager
def pinned_parent(path: Path, *, create: bool = False):
    """Yield a stable POSIX parent fd (None on Windows), refusing linked parents."""
    path = Path(path).absolute()
    if '..' in path.parts or (os.name == 'nt' and ':' in path.name):
        raise ValueError('ambiguous file path refused')
    with ExitStack() as held:
        if os.name == 'nt':
            for directory in reversed((path.parent, *path.parent.parents)):
                if create and not os.path.lexists(directory):
                    directory.mkdir(mode=0o700)
                dll, handle = _win_open(directory, directory=True)
                held.callback(dll.CloseHandle, handle)
            yield None
        else:
            descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            held.callback(os.close, descriptor)
            for component in path.parent.parts[1:]:
                if create:
                    try:
                        os.mkdir(component, mode=0o700, dir_fd=descriptor)
                    except FileExistsError:
                        pass
                descriptor = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                held.callback(os.close, descriptor)
            yield descriptor


def read_regular_bytes(path: Path, *, max_bytes: int) -> bytes:
    """Bound the read even if the file grows; reject special and linked objects."""
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError('positive file size limit required')
    path = Path(path).absolute()
    with pinned_parent(path) as parent, ExitStack() as held:
        if os.name == 'nt':
            import msvcrt

            dll, handle = _win_open(path, directory=False)
            try:
                descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
            except BaseException:
                dll.CloseHandle(handle)
                raise
        else:
            descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        held.callback(os.close, descriptor)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError('linked or nonregular file refused')
        if not 0 <= before.st_size <= max_bytes:
            raise ValueError('file size exceeds limit')
        chunks = []
        size = 0
        while True:
            chunk = os.read(descriptor, min(65536, max_bytes + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise ValueError('file size exceeds limit')
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns) or size != after.st_size:
            raise ValueError('file changed while reading')
        return b''.join(chunks)
