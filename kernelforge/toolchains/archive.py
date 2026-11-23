"""Bounded, isolated extraction of reviewed toolchain archives."""
from __future__ import annotations

import shutil
import stat
import tarfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

MAX_MEMBERS = 250_000
MAX_UNPACKED_BYTES = 32 * 1024**3
MAX_MEMBER_BYTES = 8 * 1024**3
MIN_FREE_BYTES = 64 * 1024**2


class ArchiveError(RuntimeError):
    pass


def _safe_name(name: str) -> Path:
    normalized = name.replace("\\", "/")
    candidate = PurePosixPath(normalized)
    if (candidate.is_absolute() or not candidate.parts or
            any(part in ("..", "") or ":" in part or part.endswith((".", " ")) or
                PureWindowsPath(part).is_reserved() or any(ord(c) < 32 for c in part)
                for part in candidate.parts)):
        raise ArchiveError(f"archive contains an unsafe path: {name!r}")
    return Path(*candidate.parts)


def extract(archive: Path, destination: Path, fmt: str, *,
            max_members: int = MAX_MEMBERS, max_bytes: int = MAX_UNPACKED_BYTES,
            max_member_bytes: int = MAX_MEMBER_BYTES) -> None:
    for value, ceiling in ((max_members, MAX_MEMBERS), (max_bytes, MAX_UNPACKED_BYTES),
                           (max_member_bytes, MAX_MEMBER_BYTES)):
        if type(value) is not int or not 0 < value <= ceiling:
            raise ArchiveError("invalid archive resource budget")
    archive, destination = Path(archive), Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    seen = set()
    total = 0

    def admit(name, size, directory):
        nonlocal total
        relative = _safe_name(name)
        key = relative.as_posix().casefold()
        if key in seen:
            raise ArchiveError("duplicate or case-colliding archive entry")
        seen.add(key)
        if len(seen) > max_members:
            raise ArchiveError("archive exceeds member budget")
        if type(size) is not int or not 0 <= size <= max_member_bytes:
            raise ArchiveError("archive exceeds single member byte budget")
        if directory and size != 0:
            raise ArchiveError("directory has unexpected payload")
        if total + size > max_bytes:
            raise ArchiveError("archive exceeds unpacked byte budget")
        total += size
        if shutil.disk_usage(destination).free < MIN_FREE_BYTES + size:
            raise ArchiveError("archive would violate free disk reserve")
        target = destination / relative
        if destination.resolve() not in target.resolve().parents:
            raise ArchiveError("archive path escapes destination")
        return target

    def copy_member(src, target, size, mode):
        target.parent.mkdir(parents=True, exist_ok=True)
        copied = 0
        with src, target.open("xb") as dst:
            while True:
                block = src.read(min(1024 * 1024, size - copied + 1))
                if not block:
                    break
                if copied + len(block) > size:
                    raise ArchiveError("archive member exceeds declared size")
                if shutil.disk_usage(destination).free < MIN_FREE_BYTES + len(block):
                    raise ArchiveError("archive would violate free disk reserve")
                dst.write(block)
                copied += len(block)
        if copied != size:
            raise ArchiveError("archive member truncated")
        if mode:
            target.chmod(mode & 0o755)

    try:
        if fmt == "zip":
            with zipfile.ZipFile(archive) as handle:
                for item in handle.infolist():
                    mode = item.external_attr >> 16
                    kind = stat.S_IFMT(mode)
                    if (item.flag_bits & 1 or mode & 0o6000 or
                            kind not in (0, stat.S_IFREG, stat.S_IFDIR) or
                            (kind == stat.S_IFDIR and not item.is_dir()) or
                            (kind == stat.S_IFREG and item.is_dir())):
                        raise ArchiveError("unsupported ZIP entry type or mode")
                    target = admit(item.filename, item.file_size, item.is_dir())
                    if item.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        copy_member(handle.open(item), target, item.file_size, mode)
        elif fmt in {"tar", "tar.gz", "tgz", "tar.xz", "tar.bz2"}:
            with tarfile.open(archive, mode="r:*") as handle:
                for member in handle:
                    if member.mode & 0o6000 or not (member.isfile() or member.isdir()):
                        raise ArchiveError(f"archive contains an unsupported entry: {member.name!r}")
                    target = admit(member.name, member.size, member.isdir())
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        source = handle.extractfile(member)
                        if source is None:
                            raise ArchiveError("cannot read archive entry")
                        copy_member(source, target, member.size, member.mode)
        else:
            raise ArchiveError(f"unsupported toolchain archive format: {fmt}")
    except (zipfile.BadZipFile, tarfile.TarError, OSError, RuntimeError, EOFError, ValueError) as exc:
        shutil.rmtree(destination, ignore_errors=True)
        if isinstance(exc, ArchiveError):
            raise
        raise ArchiveError(f"cannot extract toolchain archive: {exc}") from exc
