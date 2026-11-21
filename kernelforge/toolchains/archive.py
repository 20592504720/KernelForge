"""Safe extraction for explicitly supported toolchain archive formats."""
from __future__ import annotations

import shutil
import tarfile
import zipfile
from pathlib import Path, PurePosixPath


class ArchiveError(RuntimeError):
    pass


def _safe_name(name: str) -> Path:
    normalized = name.replace("\\", "/")
    candidate = PurePosixPath(normalized)
    if candidate.is_absolute() or any(part in ("..", "") for part in candidate.parts) or (candidate.parts and ":" in candidate.parts[0]):
        raise ArchiveError(f"archive contains an unsafe path: {name!r}")
    return Path(*candidate.parts)


def extract(archive: Path, destination: Path, fmt: str) -> None:
    archive, destination = Path(archive), Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        if fmt == "zip":
            with zipfile.ZipFile(archive) as handle:
                for item in handle.infolist():
                    relative = _safe_name(item.filename)
                    target = destination / relative
                    if item.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with handle.open(item) as src, target.open("xb") as dst:
                            shutil.copyfileobj(src, dst)
                        mode = (item.external_attr >> 16) & 0o777
                        if mode:
                            target.chmod(mode & 0o755)
        elif fmt in {"tar", "tar.gz", "tgz", "tar.xz", "tar.bz2"}:
            with tarfile.open(archive, mode="r:*") as handle:
                members = handle.getmembers()
                for member in members:
                    relative = _safe_name(member.name)
                    if member.issym() or member.islnk() or member.isdev() or not (member.isfile() or member.isdir()):
                        raise ArchiveError(f"archive contains an unsupported entry: {member.name!r}")
                    target = destination / relative
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = handle.extractfile(member)
                    if source is None:
                        raise ArchiveError(f"cannot read archive entry: {member.name!r}")
                    with source, target.open("xb") as output:
                        shutil.copyfileobj(source, output)
                    target.chmod(member.mode & 0o755)
        else:
            raise ArchiveError(f"unsupported toolchain archive format: {fmt}")
    except (zipfile.BadZipFile, tarfile.TarError, OSError, RuntimeError) as exc:
        shutil.rmtree(destination, ignore_errors=True)
        if isinstance(exc, ArchiveError):
            raise
        raise ArchiveError(f"cannot extract toolchain archive: {exc}") from exc
