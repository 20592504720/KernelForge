"""Stage 6.2 opt-in Git/archive acquisition; archive output remains quarantined.

A matching declared archive SHA256 proves only byte identity against the
caller's trusted expected digest, NOT Git Commit/Tree equivalence or buildability.
Only the existing Git checkout is eligible for source patch operations.
"""
from __future__ import annotations

import hashlib
import secrets
import ipaddress
import json
import os
import shutil
import stat
import tarfile
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .source_archive import (
    ArchivePreflightError, _safe_member, _SHA256, locked_projects,
    preflight_archive, MAX_MEMBERS, MAX_UNPACKED_BYTES,
)
from .toolchains.locking import FileLock


class SourceAcquisitionError(RuntimeError):
    pass


DEFAULT_MAX_DOWNLOAD = 4 * 1024**3
COPY_CHUNK = 1024 * 1024


def _checked_url(url: str, hosts: frozenset[str]) -> str:
    if not isinstance(url, str) or not url or any(ord(c) < 33 or ord(c) == 127 for c in url):
        raise SourceAcquisitionError("invalid archive URL")
    try:
        parts = urlsplit(url)
        hostname = (parts.hostname or "").lower().rstrip(".")
        port = parts.port
    except ValueError as exc:
        raise SourceAcquisitionError("invalid archive URL") from exc
    if (parts.scheme != "https" or not hostname or hostname not in hosts or
            parts.username is not None or parts.password is not None or
            parts.query or parts.fragment or port not in (None, 443) or
            "\\" in parts.path or not parts.path.startswith("/")):
        raise SourceAcquisitionError("archive URL must be approved HTTPS host without credentials/query")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
            raise SourceAcquisitionError("local archive host forbidden")
    else:
        raise SourceAcquisitionError("IP-literal archive URL forbidden")
    return url


class _RedirectPolicy(HTTPRedirectHandler):
    def __init__(self, hosts: frozenset[str]):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _checked_url(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _stream_download(url: str, output: Path, digest: str, hosts: frozenset[str],
                     *, timeout: float, max_bytes: int, opener=None) -> int:
    # Injected opener exists only for offline unit tests. The production opener
    # enforces the HTTPS redirect policy on every hop.
    if opener is None:
        opener = build_opener(_RedirectPolicy(hosts)).open
    hash_value = hashlib.sha256()
    size = 0
    req = Request(_checked_url(url, hosts), headers={"User-Agent": "KernelForge-source-acquisition/1"})
    with opener(req, timeout=timeout) as response:
        _checked_url(response.geturl(), hosts)
        declared = response.headers.get("Content-Length")
        if declared is not None:
            try:
                length = int(declared)
            except (ValueError, TypeError) as exc:
                raise SourceAcquisitionError("invalid archive Content-Length") from exc
            if length < 0 or length > max_bytes:
                raise SourceAcquisitionError("archive download exceeds byte budget")
        with output.open("xb") as destination:
            while True:
                block = response.read(COPY_CHUNK)
                if not block:
                    break
                size += len(block)
                if size > max_bytes:
                    raise SourceAcquisitionError("archive download exceeds byte budget")
                hash_value.update(block)
                destination.write(block)
            destination.flush()
            os.fsync(destination.fileno())
        if declared is not None and size != length:
            raise SourceAcquisitionError("incomplete archive download")
    if hash_value.hexdigest() != digest:
        raise SourceAcquisitionError("archive download SHA256 mismatch")
    return size


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(COPY_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def _regular_file(path: Path) -> bool:
    return not path.is_symlink() and path.is_file()


def _acquire_cache(candidate: dict, cache: Path, *, hosts: frozenset[str],
                   timeout: float, max_download_bytes: int, opener=None) -> tuple[Path, bool]:
    digest = candidate["sha256"]
    _checked_url(candidate.get("archive_url"), hosts)
    if cache.is_symlink():
        raise SourceAcquisitionError("cache directory cannot be a symlink")
    cache.mkdir(parents=True, exist_ok=True)
    objects = cache / "sha256"
    if objects.is_symlink():
        raise SourceAcquisitionError("archive object cache cannot be a symlink")
    objects.mkdir(parents=True, exist_ok=True)
    cached = objects / digest
    with FileLock(cache / "locks" / (digest + ".lock"), timeout=90):
        if cached.exists() or cached.is_symlink():
            if not _regular_file(cached) or cached.stat().st_size > max_download_bytes or _sha_file(cached) != digest:
                raise SourceAcquisitionError("corrupted or unsafe cached archive; refusing reuse")
            return cached, True
        temporary = objects / ("." + digest + ".part-" + secrets.token_hex(12))
        try:
            _stream_download(candidate["archive_url"], temporary, digest, hosts,
                             timeout=timeout, max_bytes=max_download_bytes, opener=opener)
            os.replace(temporary, cached)
        finally:
            temporary.unlink(missing_ok=True)
    return cached, False


def _copy_member(source, target: Path, expected: int, quota: list[int], max_bytes: int) -> None:
    written = 0
    with target.open("xb") as destination:
        while True:
            # Refuse excessive decompressed output even if metadata lies.
            chunk = source.read(min(COPY_CHUNK, expected - written + 1))
            if not chunk:
                break
            written += len(chunk)
            quota[0] += len(chunk)
            if written > expected or quota[0] > max_bytes:
                raise SourceAcquisitionError("archive expansion exceeds declared/allowed size")
            destination.write(chunk)
        if written != expected:
            raise SourceAcquisitionError("archive member truncated")
        destination.flush()
        os.fsync(destination.fileno())


def _extract_verified(archive: Path, fmt: str, staging: Path,
                      *, max_unpacked_bytes: int, max_members: int) -> dict:
    files = []
    try:
        if fmt == "zip":
            with zipfile.ZipFile(archive) as handle:
                items = handle.infolist()
                for item in items:
                    mode = item.external_attr >> 16
                    kind = stat.S_IFMT(mode)
                    if (item.flag_bits & 1 or kind not in (0, stat.S_IFREG, stat.S_IFDIR) or
                            mode & 0o6000 or (item.is_dir() and kind == stat.S_IFREG)):
                        raise SourceAcquisitionError("unsafe ZIP member type/mode")
                    files.append((item.filename, item.is_dir(), item.file_size, mode, item))
                    if len(files) > max_members:
                        raise SourceAcquisitionError("archive exceeds member budget")
                reader = handle.open
                def read_one(item):
                    return reader(item)
                # Reads occur in this ZipFile context, after metadata checks below.
                return _extract_items(files, read_one, staging, max_unpacked_bytes, max_members)
        with tarfile.open(archive, mode="r:*") as handle:
            for item in handle:
                if not (item.isfile() or item.isdir()) or item.mode & 0o6000:
                    raise SourceAcquisitionError("unsafe TAR member type/mode")
                files.append((item.name, item.isdir(), item.size, item.mode, item))
                if len(files) > max_members:
                    raise SourceAcquisitionError("archive exceeds member budget")
            def read_one(item):
                result = handle.extractfile(item)
                if result is None:
                    raise SourceAcquisitionError("unreadable TAR member")
                return result
            return _extract_items(files, read_one, staging, max_unpacked_bytes, max_members)
    except (tarfile.TarError, zipfile.BadZipFile, EOFError, OSError, RuntimeError, ValueError) as exc:
        if isinstance(exc, SourceAcquisitionError):
            raise
        raise SourceAcquisitionError("unreadable or corrupt archive payload") from exc


def _extract_items(files, read_one, staging: Path, max_bytes: int, max_members: int) -> dict:
    if len(files) > max_members:
        raise SourceAcquisitionError("archive exceeds member budget")
    declared, seen, regulars = 0, set(), set()
    for name, is_dir, size, mode, _ in files:
        clean = _safe_member(name, directory=is_dir)
        key = clean.casefold()
        if key in seen:
            raise SourceAcquisitionError("duplicate or case-colliding archive member")
        seen.add(key)
        if not is_dir:
            regulars.add(key)
        if size < 0:
            raise SourceAcquisitionError("negative archive member size")
        if not is_dir:
            declared += size
            if declared > max_bytes:
                raise SourceAcquisitionError("archive exceeds unpacked byte budget")
    for name in seen:
        segments = name.split("/")
        for idx in range(1, len(segments)):
            if "/".join(segments[:idx]) in regulars:
                raise SourceAcquisitionError("file-as-directory archive collision")
    consumed = [0]
    for name, is_dir, size, mode, item in files:
        target = staging.joinpath(*_safe_member(name, directory=is_dir).split("/"))
        if is_dir:
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with read_one(item) as stream:
            _copy_member(stream, target, size, consumed, max_bytes)
        # Only preserve execute intent, never untrusted owner/group/special bits.
        target.chmod(0o755 if mode & 0o111 else 0o644)
    return {"members": len(files), "unpacked_bytes": consumed[0], "payload_integrity": "TESTED"}


def acquire_archive(lock: dict, candidate: dict, destination: Path, cache_dir: Path,
                    *, allowed_hosts: set[str] | frozenset[str], timeout: float = 45,
                    max_download_bytes: int = DEFAULT_MAX_DOWNLOAD,
                    max_unpacked_bytes: int = MAX_UNPACKED_BYTES,
                    max_members: int = MAX_MEMBERS, opener=None,
                    report_path: Path | None = None) -> dict:
    """Acquire a pinned archive into an isolated directory, never a Git checkout.

    Caller must supply a trusted SHA256 and explicit HTTPS host allowlist. The
    returned directory is QUARANTINED, not automatically a build or patch input.
    """
    if (not isinstance(candidate, dict) or timeout <= 0 or max_download_bytes < 1 or
            max_unpacked_bytes < 1 or max_members < 1):
        raise SourceAcquisitionError("invalid acquisition limits")
    if not isinstance(allowed_hosts, (set, frozenset)) or not allowed_hosts:
        raise SourceAcquisitionError("explicit HTTPS host allowlist required")
    hosts = frozenset(allowed_hosts)
    if any(not isinstance(x, str) or not x or x.lower() != x for x in hosts):
        raise SourceAcquisitionError("invalid host allowlist")
    projects = locked_projects(lock)
    if candidate.get("project") not in projects:
        raise SourceAcquisitionError("archive candidate not present in source lock")
    for key in ("repository", "path", "commit_sha"):
        if candidate.get(key) != projects[candidate["project"]][key]:
            raise SourceAcquisitionError("archive identity differs from locked Git project")
    if not isinstance(candidate.get("sha256"), str) or not _SHA256.fullmatch(candidate["sha256"]):
        raise SourceAcquisitionError("trusted expected archive SHA256 is required")
    if candidate.get("archive_format") not in {"zip", "tar", "tar.gz", "tgz", "tar.xz", "tar.bz2"}:
        raise SourceAcquisitionError("unsupported archive format")
    _checked_url(candidate.get("archive_url"), hosts)
    destination = Path(destination).absolute()
    cache_dir = Path(cache_dir).absolute()
    if destination.exists() or destination.is_symlink():
        raise SourceAcquisitionError("destination already exists; refusing overwrite")
    if destination == cache_dir or cache_dir in destination.parents or destination in cache_dir.parents:
        raise SourceAcquisitionError("cache and destination must be separate")
    if report_path is not None and (Path(report_path).absolute() == destination or
                                    Path(report_path).absolute().is_relative_to(destination) or
                                    Path(report_path).absolute().is_relative_to(cache_dir)):
        raise SourceAcquisitionError("source report must remain outside quarantine")
    cached, cache_hit = _acquire_cache(candidate, cache_dir, hosts=hosts, timeout=timeout,
                                       max_download_bytes=max_download_bytes, opener=opener)
    metadata = preflight_archive(lock, candidate, cached)
    if metadata["members"] > max_members or metadata["declared_unpacked_bytes"] > max_unpacked_bytes:
        raise SourceAcquisitionError("archive exceeds configured extraction budget")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".stage6-archive-", dir=destination.parent))
    try:
        verified = _extract_verified(cached, candidate["archive_format"], staging,
                                     max_unpacked_bytes=max_unpacked_bytes, max_members=max_members)
        report = {**metadata, **verified, "schema_version": 1,
                  "phase": "STAGE6_ARCHIVE_ACQUIRED_QUARANTINED", "cache_hit": cache_hit,
                  "git_tree_equivalence": "UNTESTED", "source_sync": "UNTESTED",
                  "patch_manager_eligible": False, "build_input_eligible": False}
        # Atomic publication; never overwrite an existing workspace.
        if destination.exists() or destination.is_symlink():
            raise SourceAcquisitionError("destination appeared during acquisition")
        report_temp = None
        promoted = False
        try:
            if report_path is not None:
                report_path = Path(report_path)
                if report_path.is_symlink():
                    raise SourceAcquisitionError("report path is a symlink")
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_temp = report_path.with_name("." + report_path.name + "." + secrets.token_hex(12) + ".tmp")
                with report_temp.open("x", encoding="utf-8") as handle:
                    json.dump(report, handle, indent=2, sort_keys=True)
                    handle.flush()
                    os.fsync(handle.fileno())
            os.rename(staging, destination)
            promoted = True
            if report_temp is not None:
                os.replace(report_temp, report_path)
            return report
        except BaseException:
            if promoted and destination.exists():
                shutil.rmtree(destination)
            raise
        finally:
            if report_temp is not None:
                report_temp.unlink(missing_ok=True)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def acquire_locked_git(lock: dict, project_name: str, destination: Path, *, timeout: int = 300) -> dict:
    """Existing Git-backed acquisition, independently pinned to locked SHA."""
    project = locked_projects(lock).get(project_name)
    if project is None:
        raise SourceAcquisitionError("unknown locked Git project")
    from .source import checkout
    commit = checkout(project["repository"], project["commit_sha"], Path(destination), timeout=timeout)
    if commit != project["commit_sha"]:
        raise SourceAcquisitionError("Git checkout differs from locked commit")
    return {"schema_version": 1, "strategy": "repo-git-lock-v1", "project": project_name,
            "locked_commit": commit, "source_sync": "TESTED", "git_commit": "TESTED",
            "patch_manager_eligible": True, "archive_checksum": "NOT_APPLICABLE"}


def acquire_locked_source(strategy: str, lock: dict, project_name: str, destination: Path,
                          *, candidate: dict | None = None, cache_dir: Path | None = None,
                          allowed_hosts: set[str] | frozenset[str] | None = None, **options) -> dict:
    """Opt-in strategy switch; archive results are never patch/build eligible."""
    if strategy == "repo-git-lock-v1":
        if candidate is not None:
            raise SourceAcquisitionError("archive candidate forbidden for Git strategy")
        return acquire_locked_git(lock, project_name, destination, **options)
    if strategy == "pinned-archive-v1":
        if candidate is None or candidate.get("project") != project_name or cache_dir is None or allowed_hosts is None:
            raise SourceAcquisitionError("pinned archive needs matching candidate/cache/hosts")
        return acquire_archive(lock, candidate, destination, cache_dir, allowed_hosts=allowed_hosts, **options)
    raise SourceAcquisitionError("unknown source acquisition strategy")
