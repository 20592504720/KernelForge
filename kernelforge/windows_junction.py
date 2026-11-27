"""Create NTFS directory junctions through Win32 APIs, never cmd.exe."""
from __future__ import annotations

import ctypes
import os
from contextlib import ExitStack
from ctypes import wintypes
from pathlib import Path

_FSCTL_SET_REPARSE_POINT = 0x000900A4
_IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003
_GENERIC_WRITE = 0x40000000
_OPEN_EXISTING = 3
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def _extended(path: Path) -> str:
    value = str(path)
    if value.startswith("\\\\?\\"):
        return value
    if value.startswith("\\\\"):
        return "\\\\?\\UNC\\" + value[2:]
    return "\\\\?\\" + value


def _mount_target(path: Path) -> tuple[str, str]:
    display = str(path.resolve(strict=True))
    if display.startswith("\\\\?\\UNC\\"):
        substitute = "\\??\\UNC\\" + display[8:]
    elif display.startswith("\\\\?\\"):
        substitute = "\\??\\" + display[4:]
    elif display.startswith("\\\\"):
        substitute = "\\??\\UNC\\" + display[2:]
    else:
        substitute = "\\??\\" + display
    return substitute, display


def _create_directory_handle(link: Path):
    """Atomically create a new directory and return its exclusive handle.

    NtCreateFile FILE_CREATE fails if any object already occupies the name.
    There is no CreateDirectoryW/open gap in which a replacement can be used.
    Ancestors are pinned by create_junction before this function is called.
    """
    if os.name != 'nt':
        raise OSError('Windows junction creation requested on a non-Windows host')
    class UnicodeString(ctypes.Structure):
        _fields_ = [('Length', wintypes.USHORT), ('MaximumLength', wintypes.USHORT),
                    ('Buffer', wintypes.LPWSTR)]

    class ObjectAttributes(ctypes.Structure):
        _fields_ = [('Length', wintypes.ULONG), ('RootDirectory', wintypes.HANDLE),
                    ('ObjectName', ctypes.POINTER(UnicodeString)), ('Attributes', wintypes.ULONG),
                    ('SecurityDescriptor', wintypes.LPVOID), ('SecurityQualityOfService', wintypes.LPVOID)]

    class IoStatus(ctypes.Structure):
        _fields_ = [('Status', ctypes.c_void_p), ('Information', ctypes.c_size_t)]

    native = ctypes.WinDLL('ntdll')
    native.NtCreateFile.argtypes = [ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD,
                                  ctypes.POINTER(ObjectAttributes), ctypes.POINTER(IoStatus),
                                  wintypes.LPVOID, wintypes.ULONG, wintypes.ULONG, wintypes.ULONG,
                                  wintypes.ULONG, wintypes.LPVOID, wintypes.ULONG]
    native.NtCreateFile.restype = ctypes.c_int32
    native.RtlNtStatusToDosError.argtypes = [ctypes.c_int32]
    native.RtlNtStatusToDosError.restype = wintypes.ULONG
    name = '\\??\\' + _extended(link)[4:]
    size = len(name.encode('utf-16-le'))
    if size > 65532:
        raise OSError('junction destination exceeds NT path limits')
    buffer = ctypes.create_unicode_buffer(name)
    text = UnicodeString(size, size + 2, ctypes.cast(buffer, wintypes.LPWSTR))
    attributes = ObjectAttributes(ctypes.sizeof(ObjectAttributes), None, ctypes.pointer(text), 0x40, None, None)
    handle, status = wintypes.HANDLE(), IoStatus()
    result = native.NtCreateFile(ctypes.byref(handle), _GENERIC_WRITE | 0x10000 | 0x100000,
                                 ctypes.byref(attributes), ctypes.byref(status), None, 0x10,
                                 0, 2, 0x1 | 0x20 | 0x200000, None, 0)
    if result < 0:
        raise ctypes.WinError(native.RtlNtStatusToDosError(result))
    return handle


def create_junction(target: Path, link: Path) -> None:
    """Pin real parent directories and the target against rename during creation.

    Requires caller-owned parent directories. A hostile writer with the same
    access rights is outside this API's isolation boundary.
    """
    if os.name != 'nt':
        raise OSError('Windows junction creation requested on a non-Windows host')
    target, link = Path(target).absolute(), Path(link).absolute()
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                   wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    kernel32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    with ExitStack() as held:
        # Omit FILE_SHARE_DELETE so a checked ancestor cannot be renamed while
        # later path-based operations are in progress. Inspect the reparse tag
        # on the opened handle, rather than following a path and checking later.
        directories = {*target.parents, target, *link.parent.parents, link.parent}
        for directory in sorted(directories, key=lambda p: (len(p.parts), str(p))):
            handle = kernel32.CreateFileW(_extended(directory), 0x80, 3, None, _OPEN_EXISTING,
                                         _FILE_FLAG_OPEN_REPARSE_POINT | _FILE_FLAG_BACKUP_SEMANTICS, None)
            if handle == _INVALID_HANDLE_VALUE:
                raise ctypes.WinError(ctypes.get_last_error())
            held.callback(kernel32.CloseHandle, handle)
            info = (wintypes.DWORD * 2)()
            if not kernel32.GetFileInformationByHandleEx(handle, 9, info, ctypes.sizeof(info)):
                raise ctypes.WinError(ctypes.get_last_error())
            if info[0] & 0x400 or not info[0] & 0x10:
                raise OSError('junction ancestors and target must be real directories without reparse points')
        _create_pinned_junction(target, link)


def _create_pinned_junction(target: Path, link: Path) -> None:
    if os.name != "nt":
        raise OSError("Windows junction creation requested on a non-Windows host")
    target, link = Path(target).absolute(), Path(link).absolute()
    if (not target.is_dir() or target.is_symlink() or getattr(target, "is_junction", lambda: False)()
            or link.exists() or link.is_symlink()):
        raise OSError("junction target must be a real directory and destination must not exist")
    substitute, display = _mount_target(target)
    sub = substitute.encode("utf-16-le")
    shown = display.encode("utf-16-le")
    sub_term, shown_term = sub + b"\0\0", shown + b"\0\0"
    path_buffer = sub_term + shown_term
    data_length = 8 + len(path_buffer)
    if len(sub) > 0xFFFF or len(shown) > 0xFFFF or data_length + 8 > 16 * 1024:
        raise OSError("junction target exceeds Windows reparse-point limits")
    header = (ctypes.c_uint32(_IO_REPARSE_TAG_MOUNT_POINT),
              ctypes.c_uint16(data_length), ctypes.c_uint16(0),
              ctypes.c_uint16(0), ctypes.c_uint16(len(sub)),
              ctypes.c_uint16(len(sub) + 2), ctypes.c_uint16(len(shown)))
    prefix = b"".join(value.value.to_bytes(ctypes.sizeof(value), "little") for value in header)
    payload = prefix + path_buffer
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID,
                                        wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                                        ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    kernel32.DeviceIoControl.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.SetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    kernel32.SetFileInformationByHandle.restype = wintypes.BOOL
    handle = None
    try:
        handle = _create_directory_handle(link)
        buffer = ctypes.create_string_buffer(payload)
        returned = ctypes.c_uint32()
        if not kernel32.DeviceIoControl(
                handle, _FSCTL_SET_REPARSE_POINT, buffer, len(payload),
                None, 0, ctypes.byref(returned), None):
            raise ctypes.WinError(ctypes.get_last_error())
    except BaseException:
        if handle is not None and handle != _INVALID_HANDLE_VALUE:
            # Mark the actual opened directory for deletion. Do not close the
            # handle then delete a path which another process could replace.
            disposition = wintypes.BOOLEAN(1)
            kernel32.SetFileInformationByHandle(handle, 4, ctypes.byref(disposition), ctypes.sizeof(disposition))
            kernel32.CloseHandle(handle)
            handle = None
        raise
    finally:
        if handle is not None and handle != _INVALID_HANDLE_VALUE:
            kernel32.CloseHandle(handle)
