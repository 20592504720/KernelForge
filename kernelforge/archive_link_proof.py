"""Stage 6.3 read-only TAR/ZIP proof against an independently pinned Git Tree.

Symlinks are checked as Git 120000 blob *bytes*, never followed or created.
Passing does not make an archive safe to extract, patch, build or publish.
"""
from __future__ import annotations

import hashlib
import os
import stat
import tarfile
import zipfile
from pathlib import Path

from .source_archive import locked_projects, _safe_member, _SHA256, ArchivePreflightError
from .source_equivalence import SourceEquivalenceError, _git, _valid_path

MAX_MEMBERS = 250_000
MAX_BYTES = 64 * 1024**3
CHUNK = 1024 * 1024


def _reject(message: str) -> None:
    raise SourceEquivalenceError(message)


def _blob(content, expected_size: int, budget: list[int], max_bytes: int) -> str:
    if not isinstance(expected_size, int) or expected_size < 0:
        _reject("invalid archive member size")
    if budget[0] + expected_size > max_bytes:
        _reject("archive payload exceeds byte budget")
    digest = hashlib.sha1()
    digest.update(b"blob " + str(expected_size).encode("ascii") + b"\0")
    read = 0
    while read < expected_size:
        chunk = content.read(min(CHUNK, expected_size - read))
        if not chunk:
            _reject("truncated archive member")
        read += len(chunk)
        digest.update(chunk)
    if content.read(1):
        _reject("archive member exceeds declared size")
    budget[0] += read
    return digest.hexdigest()


def _sha256(path: Path, max_archive_bytes: int) -> str:
    if path.is_symlink() or not path.is_file():
        _reject("archive must be a regular file")
    if not isinstance(max_archive_bytes, int) or max_archive_bytes < 1:
        _reject("invalid archive byte budget")
    h = hashlib.sha256()
    with path.open("rb") as inp:
        size = 0
        for chunk in iter(lambda: inp.read(CHUNK), b""):
            size += len(chunk)
            if size > max_archive_bytes:
                _reject("compressed archive exceeds byte budget")
            h.update(chunk)
    return h.hexdigest()


def _git_tree(repo: Path, commit: str, max_members: int):
    if repo.is_symlink() or not repo.is_dir():
        _reject("reference Git checkout must be a real directory")
    if _git(repo, "rev-parse", "--show-object-format") != "sha1":
        _reject("unsupported Git object format")
    actual = _git(repo, "rev-parse", "--verify", "HEAD^{commit}").lower()
    if actual != commit:
        _reject("Git HEAD differs from locked Commit")
    tree_sha = _git(repo, "rev-parse", "--verify", "HEAD^{tree}").lower()
    raw = _git(repo, "ls-tree", "-rz", "--full-tree", "HEAD", binary=True)
    expected = {}
    folded = set()
    for record in raw.split(b"\0"):
        if not record:
            continue
        if len(expected) >= max_members:
            _reject("Git tree exceeds member budget")
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, kind, oid = metadata.decode("ascii").split(" ")
            name = _valid_path(raw_path.decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise SourceEquivalenceError("invalid Git tree entry") from exc
        if kind != "blob" or mode not in ("100644", "100755", "120000") or len(oid) != 40:
            _reject("Git tree contains unsupported object or mode")
        if name.casefold() in folded:
            _reject("Git tree contains case-colliding paths")
        folded.add(name.casefold())
        expected[name] = (mode, oid)
    return expected, tree_sha


def _name(name: str, directory: bool, prefix: str):
    try:
        safe = _safe_member(name, directory=directory)
    except ArchivePreflightError as exc:
        raise SourceEquivalenceError("unsafe archive member path") from exc
    if prefix:
        if directory and safe == prefix:
            return ""
        if not safe.startswith(prefix + "/"):
            _reject("archive entry outside declared root")
        safe = safe[len(prefix) + 1:]
    if not safe:
        return ""
    return _valid_path(safe)


def verify_archive_link_tree(lock: dict, project_name: str, archive: Path, git_repo: Path,
                             *, archive_format: str = "tar", expected_sha256: str,
                             archive_root: str = "", max_members: int = MAX_MEMBERS,
                             max_bytes: int = MAX_BYTES,
                             max_archive_bytes: int = 4 * 1024**3) -> dict:
    """Prove raw regular-file and symlink-blob identity without extraction.

    SHA256 must be supplied from a *trusted independent* source. This method
    does not authenticate its origin, validate actual link destinations, or
    allow the archive to enter Git-backed Patch/Build Manager.
    """
    projects = locked_projects(lock)
    project = projects.get(project_name)
    if project is None:
        _reject("project not in locked source manifest")
    if (not isinstance(expected_sha256, str) or not _SHA256.fullmatch(expected_sha256)):
        _reject("trusted archive SHA256 required")
    if not isinstance(max_members, int) or not 0 < max_members <= MAX_MEMBERS or not 0 < max_bytes <= MAX_BYTES:
        _reject("invalid verification budget")
    if archive_format not in {"tar", "tar.gz", "tgz", "tar.xz", "tar.bz2", "zip"}:
        _reject("unsupported archive format")
    archive = Path(archive).absolute()
    git_repo = Path(git_repo).absolute()
    if archive == git_repo or git_repo in archive.parents:
        _reject("archive must be outside pinned Git reference")
    prefix = _valid_path(archive_root) if archive_root else ""
    if _sha256(archive, max_archive_bytes) != expected_sha256:
        _reject("archive SHA256 differs from expected bytes")
    expected, tree_sha = _git_tree(git_repo, project["commit_sha"], max_members)
    actual = {}
    folded = set()
    budget = [0]
    symlinks = 0
    entries_seen = 0
    directories = set()

    def accept(raw_name, directory, kind, executable, content=None, size=0, target=None):
        nonlocal symlinks, entries_seen
        entries_seen += 1
        if entries_seen > max_members:
            _reject("archive exceeds member budget")
        path = _name(raw_name, directory, prefix)
        if not path:
            return
        folded_name = path.casefold()
        if folded_name in folded:
            _reject("duplicate or case-colliding archive path")
        folded.add(folded_name)
        if directory:
            if path in expected:
                _reject("directory conflicts with Git blob")
            directories.add(path)
            return
        if kind == "link":
            if not isinstance(target, bytes) or b"\0" in target:
                _reject("invalid symlink target bytes")
            size = len(target)
            from io import BytesIO
            oid = _blob(BytesIO(target), size, budget, max_bytes)
            mode = "120000"
            symlinks += 1
        elif kind == "file":
            if content is None:
                _reject("missing archive payload")
            oid = _blob(content, size, budget, max_bytes)
            mode = "100755" if executable else "100644"
        else:
            _reject("unsupported archive member type")
        if path not in expected:
            _reject("extra archive file or symlink")
        if expected[path] != (mode, oid):
            _reject("Git/archive file bytes, symlink target, or mode differ")
        actual[path] = True

    try:
        if archive_format == "zip":
            with zipfile.ZipFile(archive) as inp:
                for item in inp.infolist():
                    mode = item.external_attr >> 16
                    kind = stat.S_IFMT(mode)
                    if item.flag_bits & 1 or mode & 0o6000:
                        _reject("encrypted or privileged ZIP entry")
                    if kind == stat.S_IFLNK:
                        with inp.open(item) as src:
                            # Zip symlink targets are stored as normal payload bytes.
                            if item.file_size > 4096:
                                _reject("oversized symlink target")
                            target = src.read(4097)
                            if len(target) != item.file_size:
                                _reject("invalid ZIP symlink data")
                            if src.read(1):
                                _reject("oversized ZIP symlink data")
                        accept(item.filename, False, "link", False, target=target)
                    elif item.is_dir() and kind in (0, stat.S_IFDIR):
                        accept(item.filename, True, "dir", False)
                    elif kind in (0, stat.S_IFREG) and not item.is_dir():
                        with inp.open(item) as src:
                            accept(item.filename, False, "file", bool(mode & 0o111), src, item.file_size)
                    else:
                        _reject("unsupported or ambiguous ZIP mode")
        else:
            with tarfile.open(archive, mode="r:*") as inp:
                for member in inp:
                    if member.mode & 0o6000:
                        _reject("privileged TAR entry")
                    if member.isdir():
                        accept(member.name, True, "dir", False)
                    elif member.issym():
                        try:
                            link = member.linkname.encode("utf-8", errors="strict")
                        except UnicodeError as exc:
                            raise SourceEquivalenceError("invalid symlink target encoding") from exc
                        if len(link) > 4096:
                            _reject("oversized symlink target")
                        accept(member.name, False, "link", False, target=link)
                    elif member.isfile():
                        src = inp.extractfile(member)
                        if src is None:
                            _reject("unreadable TAR member")
                        with src:
                            accept(member.name, False, "file", bool(member.mode & 0o111), src, member.size)
                    else:
                        _reject("TAR hardlinks or special members forbidden")
    except (OSError, EOFError, tarfile.TarError, zipfile.BadZipFile, RuntimeError, UnicodeError) as exc:
        raise SourceEquivalenceError("archive payload cannot be verified") from exc

    if set(actual) != set(expected):
        _reject(f"Git/archive file set differs: missing={len(set(expected)-set(actual))}")
    for directory in directories:
        if not any(name.startswith(directory + "/") for name in expected):
            _reject("archive contains untracked empty directory")
    return {"schema_version": 1, "project": project_name,
            "locked_commit": project["commit_sha"], "git_tree_sha": tree_sha,
            "archive_sha256": expected_sha256, "git_tree_equivalence": "TESTED",
            "regular_files_verified": len(expected) - symlinks,
            "symlink_blobs_verified": symlinks, "bytes_verified": budget[0],
            "reference_kind": "INDEPENDENT_PINNED_GIT_OBJECTS",
            "symlink_targets_materialized": False, "symlink_destinations_valid": "UNTESTED",
            "archive_extraction_safe": "UNTESTED", "workspace_content_equivalence": "UNTESTED",
            "independent_vendor_archive_provenance": "UNTESTED",
            "patch_manager_eligible": False, "build_input_eligible": False,
            "device_boot": "UNTESTED"}