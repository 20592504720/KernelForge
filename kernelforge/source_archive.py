"""Stage 6 fail-closed archive preflight; no extraction or Git identity claim.

Preflight verifies a locked project identity, expected archive bytes and basic
container metadata. It does not establish Git tree equivalence or a buildable
checkout. Patch Manager must continue to use the existing Git-backed source.
"""
from __future__ import annotations

import hashlib
import re
import stat
import tarfile
import zipfile
from pathlib import Path, PureWindowsPath
from urllib.parse import urlsplit


class ArchivePreflightError(ValueError):
    pass


_SHA40 = re.compile(r"[0-9a-f]{40}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_FORMATS = {"zip", "tar", "tar.gz", "tgz", "tar.xz", "tar.bz2"}
MAX_MEMBERS = 250_000
MAX_UNPACKED_BYTES = 512 * 1024**3


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ArchivePreflightError(reason)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portable_component(part: str) -> bool:
    """Reject Windows aliases, device paths and alternate streams on every host."""
    return (bool(part) and part not in (".", "..")
            and not part.endswith((".", " "))
            and not PureWindowsPath(part).is_reserved()
            and not any(c in '<>:"|?*' or ord(c) < 32 or ord(c) == 127 for c in part))


def _safe_project_path(path: str) -> str:
    _require(isinstance(path, str) and bool(path), "project path is empty")
    if path == "./":
        return path
    _require(not path.startswith(("/", "\\")) and "\\" not in path, "unsafe project path")
    parts = path.split("/")
    _require(all(_portable_component(part) for part in parts), "unsafe project path")
    return path


def _safe_repo(url: str) -> None:
    _require(isinstance(url, str), "repository URL missing")
    parts = urlsplit(url)
    _require(parts.scheme == "https" and bool(parts.hostname) and not parts.username
             and not parts.password and not parts.query and not parts.fragment
             and bool(parts.path) and not any(ord(c) < 32 for c in url), "unsafe repository URL")


def locked_projects(lock: dict) -> dict[str, dict]:
    """Validate declared 35-project lock identities without accessing sources."""
    _require(isinstance(lock, dict) and lock.get("schema_version") == 1, "unsupported source lock schema")
    _require(isinstance(lock.get("device_profile"), str) and lock["device_profile"], "missing device profile")
    _require(bool(_SHA40.fullmatch(str(lock.get("manifest_commit", "")))), "unlocked manifest commit")
    _safe_repo(lock.get("manifest_repository"))
    source = lock.get("source_lock")
    _require(isinstance(source, dict), "missing source lock")
    projects = source.get("projects")
    _require(isinstance(projects, list) and bool(projects), "missing locked projects")
    _require(len(projects) == source.get("project_count") and source.get("all_refs_locked") is True,
             "project count or lock state mismatch")
    by_name, paths = {}, set()
    for project in projects:
        _require(isinstance(project, dict), "invalid project record")
        name = project.get("name")
        _require(isinstance(name, str) and bool(name) and name not in by_name, "duplicate or invalid project name")
        path = _safe_project_path(project.get("path"))
        normalized = path.casefold()
        _require(normalized not in paths, "duplicate or case-colliding project paths")
        _safe_repo(project.get("repository"))
        _require(bool(_SHA40.fullmatch(str(project.get("commit_sha", "")))), "unlocked project commit")
        _require(project.get("ref_state") == "LOCKED", "project is not locked")
        paths.add(normalized)
        by_name[name] = project
    return by_name


def _safe_member(name: str, *, directory: bool) -> str:
    _require(isinstance(name, str) and bool(name), "empty archive member")
    _require("\\" not in name and not name.startswith("/"), "unsafe archive member path")
    normalized = name[:-1] if directory and name.endswith("/") else name
    components = normalized.split("/")
    _require(all(_portable_component(p) for p in components), "unsafe archive member path")
    return normalized


def _check_entries(entries: list[tuple[str, bool, int]]) -> dict:
    _require(len(entries) <= MAX_MEMBERS, "archive exceeds member-count limit")
    seen, file_names, total = set(), set(), 0
    for name, is_dir, size in entries:
        clean = _safe_member(name, directory=is_dir)
        identity = clean.casefold()
        _require(identity not in seen, "duplicate or case-colliding archive entry")
        _require(isinstance(size, int) and size >= 0, "invalid member size")
        total += size
        _require(total <= MAX_UNPACKED_BYTES, "archive exceeds expanded-size budget")
        seen.add(identity)
        if not is_dir:
            file_names.add(identity)
    for name in seen:
        parts = name.split("/")
        for index in range(1, len(parts)):
            _require("/".join(parts[:index]) not in file_names, "archive file/directory collision")
    return {"members": len(entries), "declared_unpacked_bytes": total,
            "path_policy": "STRICT_NO_LINKS", "payload_integrity": "UNTESTED"}


def inspect_archive(path: Path, fmt: str) -> dict:
    """Validate container directory metadata; deliberately never extract."""
    _require(fmt in _FORMATS, "unsupported archive format")
    path = Path(path)
    _require(path.is_file() and not path.is_symlink(), "missing or symlinked archive")
    entries = []
    try:
        if fmt == "zip":
            with zipfile.ZipFile(path) as archive:
                for item in archive.infolist():
                    _require(len(entries) < MAX_MEMBERS, "archive exceeds member-count limit")
                    mode = item.external_attr >> 16
                    kind = stat.S_IFMT(mode)
                    _require(not item.flag_bits & 1, "encrypted ZIP entry forbidden")
                    _require(kind in (0, stat.S_IFREG, stat.S_IFDIR), "ZIP link/special member forbidden")
                    _require((not item.is_dir() or kind != stat.S_IFREG), "ZIP directory mode mismatch")
                    _require((not (mode & 0o6000)), "setuid/setgid archive mode forbidden")
                    entries.append((item.filename, item.is_dir(), 0 if item.is_dir() else item.file_size))
        else:
            with tarfile.open(path, mode="r:*") as archive:
                for item in archive:
                    _require(len(entries) < MAX_MEMBERS, "archive exceeds member-count limit")
                    _require(item.isfile() or item.isdir(), "TAR link/special member forbidden")
                    _require(not (item.mode & 0o6000), "setuid/setgid archive mode forbidden")
                    entries.append((item.name, item.isdir(), 0 if item.isdir() else item.size))
    except (zipfile.BadZipFile, tarfile.TarError, EOFError, OSError) as exc:
        raise ArchivePreflightError("corrupt or unreadable archive metadata") from exc
    return _check_entries(entries)


def preflight_archive(lock: dict, candidate: dict, archive: Path) -> dict:
    """Verify candidate against an existing lock and expected SHA256.

    The SHA256 must come from a trusted out-of-band manifest. A matching hash
    alone does not prove this archive reproduces the locked Git commit/tree.
    """
    projects = locked_projects(lock)
    _require(isinstance(candidate, dict), "missing archive candidate")
    project = projects.get(candidate.get("project"))
    _require(project is not None, "archive project not in source lock")
    for field, expected in (("repository", project["repository"]),
                            ("path", project["path"]), ("commit_sha", project["commit_sha"])):
        _require(candidate.get(field) == expected, f"archive {field} disagrees with locked Git project")
    digest = candidate.get("sha256")
    _require(isinstance(digest, str) and bool(_SHA256.fullmatch(digest)), "trusted archive SHA256 required")
    fmt = candidate.get("archive_format")
    _require(fmt in _FORMATS, "unsupported archive format")
    archive = Path(archive)
    _require(archive.is_file() and not archive.is_symlink(), "archive not a regular file")
    actual = _sha256_file(archive)
    _require(actual == digest, "archive SHA256 mismatch")
    inspection = inspect_archive(archive, fmt)
    return {"schema_version": 1, "strategy": "pinned-archive-v1", "project": candidate["project"],
            "locked_commit": project["commit_sha"], "archive_sha256": actual,
            "archive_bytes": archive.stat().st_size, "archive_checksum": "TESTED",
            "archive_metadata": "TESTED", "git_tree_equivalence": "UNTESTED",
            "patch_manager_eligible": False, "source_sync": "UNTESTED", **inspection}


def require_git_patch_source(strategy: str) -> None:
    """Keep current Patch Manager strictly on real, independently verified Git checkouts."""
    if strategy != "repo-git-lock-v1":
        raise ArchivePreflightError("patch targets require a verified Git checkout; archive is not eligible")
