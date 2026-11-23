"""Stage 6.3: exact, read-only archive-versus-locked-Git-tree comparisons.

Git source is independently acquired and pinned; this module never downloads,
extracts, patches, rewrites source locks or promotes an archive as build input.
On Windows, POSIX executable mode cannot be proven: fail closed.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
from pathlib import Path
from xml.etree import ElementTree

from .source_archive import locked_projects, _safe_member


class SourceEquivalenceError(ValueError):
    """Archive or manifest cannot be proved equivalent to locked source."""


MAX_TREE_FILES = 250_000
MAX_VERIFY_BYTES = 64 * 1024**3
_SHA40 = re.compile(r"[0-9a-f]{40}\Z")


def _valid_path(name: str) -> str:
    if not isinstance(name, str):
        raise SourceEquivalenceError("invalid path type")
    try:
        path = _safe_member(name, directory=False)
    except ValueError as exc:
        raise SourceEquivalenceError("unsafe manifest or tree path") from exc
    if any(part in (".git", ".repo") or part.startswith(".repo") for part in path.split("/")):
        raise SourceEquivalenceError("Git/Repo metadata paths are reserved")
    return path


def workspace_plan(lock: dict, manifest_xml: str | None = None) -> dict:
    """Static mounting plan, never a statement that 35 source trees were overlaid.

    Manifest XML is a declaration, not authenticated unless independently read
    from the locked manifest commit. No copyfile/linkfile is executed here.
    """
    projects = locked_projects(lock)
    rows = []
    for name, item in projects.items():
        raw_path = item["path"]
        path = "" if raw_path == "./" else _valid_path(raw_path)
        rows.append({"name": name, "path": raw_path, "commit_sha": item["commit_sha"],
                     "depth": 0 if not path else path.count("/") + 1})
    rows.sort(key=lambda r: (r["depth"], r["path"].casefold(), r["name"]))
    root_count = sum(1 for row in rows if row["path"] == "./")
    if root_count > 1:
        raise SourceEquivalenceError("multiple root projects forbidden")
    mounts = [row["path"] for row in rows if row["path"] != "./"]
    nested = [{"parent": a, "child": b} for a in mounts for b in mounts if b.startswith(a + "/")]
    directives = []
    manifest_state = "NOT_SUPPLIED"
    if manifest_xml is not None:
        if not isinstance(manifest_xml, str) or any(s in manifest_xml.upper() for s in ("<!DOCTYPE", "<!ENTITY")):
            raise SourceEquivalenceError("unsafe manifest XML")
        try:
            doc = ElementTree.fromstring(manifest_xml)
        except ElementTree.ParseError as exc:
            raise SourceEquivalenceError("invalid manifest XML") from exc
        if doc.tag != "manifest" or doc.findall("include") or doc.findall("submanifest") or doc.findall("extend-project"):
            raise SourceEquivalenceError("manifest must be a fully resolved snapshot")
        items = doc.findall("project")
        if len(items) != len(projects):
            raise SourceEquivalenceError("manifest project count differs from source lock")
        seen = set()
        destinations = set()
        for p in items:
            name = p.get("name")
            if name not in projects or name in seen:
                raise SourceEquivalenceError("manifest project identity differs from source lock")
            seen.add(name)
            locked = projects[name]
            actual_path = p.get("path") or name
            if actual_path != locked["path"]:
                raise SourceEquivalenceError("manifest path differs from source lock")
            # Revision can be a moving branch in original snapshot. Never resolve it here.
            if p.get("revision") is not None and p.get("revision") != locked.get("revision"):
                raise SourceEquivalenceError("manifest revision differs from source lock")
            for elt in p:
                if elt.tag in ("copyfile", "linkfile"):
                    src = "." if elt.tag == "linkfile" and elt.get("src") == "." else _valid_path(elt.get("src"))
                    dst = _valid_path(elt.get("dest"))
                    key = dst.casefold()
                    if key in destinations:
                        raise SourceEquivalenceError("duplicate copyfile/linkfile destination")
                    destinations.add(key)
                    directives.append({"project": name, "kind": elt.tag, "src": src, "dest": dst,
                                       "application": "UNTESTED"})
                elif elt.tag not in ("annotation",):
                    raise SourceEquivalenceError("unsupported manifest project directive")
        manifest_state = "DECLARATIONS_CHECKED_UNAUTHENTICATED"
    return {"schema_version": 1, "device_profile": lock["device_profile"],
            "project_count": len(rows), "locked_project_count": len(projects),
            "root_projects": root_count, "nested_mounts": nested, "mount_order": rows,
            "root_overlay_files": "UNTESTED", "project_file_collisions": "UNTESTED",
            "manifest_state": manifest_state, "copyfile_linkfile": directives,
            "copyfile_linkfile_application": "UNTESTED", "workspace_content_equivalence": "UNTESTED"}


def _git(repo: Path, *args: str, binary: bool = False, timeout: int = 90):
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("GIT_CONFIG_") or k in (
               "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
               "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_REPLACE_REF_BASE"))}
    env["GIT_NO_REPLACE_OBJECTS"] = "1"
    env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        result = subprocess.run(["git", "-C", str(repo), *args], env=env, capture_output=True,
                                text=not binary, encoding=None if binary else "utf-8",
                                timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SourceEquivalenceError("local Git object inspection unavailable") from exc
    if result.returncode:
        raise SourceEquivalenceError("local pinned Git object inspection failed")
    return result.stdout if binary else result.stdout.strip()


def _git_entries(repo: Path, commit: str, *, max_files: int) -> tuple[dict[str, tuple[str, str]], str]:
    actual = _git(repo, "rev-parse", "--verify", "HEAD^{commit}").lower()
    if actual != commit:
        raise SourceEquivalenceError("Git HEAD differs from exact locked Commit")
    fmt = _git(repo, "rev-parse", "--show-object-format")
    if fmt != "sha1":
        raise SourceEquivalenceError("unsupported Git object format for 40-hex source lock")
    tree = _git(repo, "rev-parse", "--verify", "HEAD^{tree}").lower()
    raw = _git(repo, "ls-tree", "-rz", "--full-tree", "HEAD", binary=True)
    rows: dict[str, tuple[str, str]] = {}
    casefolded = set()
    for item in raw.split(b"\x00"):
        if not item:
            continue
        if len(rows) >= max_files:
            raise SourceEquivalenceError("pinned Git tree exceeds file-count budget")
        try:
            metadata, filename = item.split(b"\t", 1)
            mode, obj_type, oid = metadata.decode("ascii").split(" ")
            path = _valid_path(filename.decode("utf-8", errors="strict"))
        except (UnicodeError, ValueError) as exc:
            raise SourceEquivalenceError("invalid Git tree entry") from exc
        if obj_type != "blob" or mode not in ("100644", "100755") or not _SHA40.fullmatch(oid):
            raise SourceEquivalenceError("Git tree uses links, gitlinks, or unsupported modes")
        if path.casefold() in casefolded:
            raise SourceEquivalenceError("Git tree contains case-insensitive name collision")
        casefolded.add(path.casefold())
        rows[path] = (mode, oid)
    return rows, tree


def _staged_files(directory: Path, *, max_files: int) -> dict[str, Path]:
    if directory.is_symlink() or not directory.is_dir():
        raise SourceEquivalenceError("archive staging root must be a real directory")
    result: dict[str, Path] = {}
    casefolded = set()
    for base, dirs, files in os.walk(directory, followlinks=False):
        for name in dirs + files:
            entry = Path(base) / name
            rel = _valid_path(entry.relative_to(directory).as_posix())
            if entry.is_symlink():
                raise SourceEquivalenceError("archive staging contains symlink")
            if entry.is_dir():
                continue
            if not entry.is_file() or not stat.S_ISREG(entry.stat().st_mode):
                raise SourceEquivalenceError("archive staging contains special file")
            if rel.casefold() in casefolded:
                raise SourceEquivalenceError("archive staging contains case-insensitive collision")
            casefolded.add(rel.casefold())
            result[rel] = entry
            if len(result) > max_files:
                raise SourceEquivalenceError("archive staging exceeds file-count budget")
    return result


def verify_archive_git_tree(lock: dict, project_name: str, staging: Path, git_repo: Path,
                            *, archive_root: str = "", max_files: int = MAX_TREE_FILES,
                            max_bytes: int = MAX_VERIFY_BYTES) -> dict:
    """Compare every staged regular-file blob and POSIX execute bit with pinned Git.

    This is a *read-only* proof against an independently verified Git checkout,
    not a grant to the Patch Manager or actual vendor-kernel build pipeline.
    """
    projects = locked_projects(lock)
    if project_name not in projects:
        raise SourceEquivalenceError("unknown project in source lock")
    if max_files < 1 or max_bytes < 1:
        raise SourceEquivalenceError("invalid comparison budgets")
    if os.name != "posix":
        raise SourceEquivalenceError("POSIX mode equivalence requires Linux/WSL2")
    if archive_root:
        prefix = _valid_path(archive_root)
    else:
        prefix = ""
    git_repo = Path(git_repo).absolute()
    staging = Path(staging).absolute()
    if git_repo.is_symlink() or not git_repo.is_dir():
        raise SourceEquivalenceError("Git reference checkout is not a real directory")
    if staging == git_repo or git_repo in staging.parents or staging in git_repo.parents:
        raise SourceEquivalenceError("reference Git repo and archive staging must be separate")
    expected, tree_sha = _git_entries(git_repo, projects[project_name]["commit_sha"], max_files=max_files)
    present = _staged_files(staging, max_files=max_files)
    if prefix:
        prefix_slash = prefix + "/"
        if any(not p.startswith(prefix_slash) for p in present):
            raise SourceEquivalenceError("archive contains files outside declared root prefix")
        present = {p[len(prefix_slash):]: file for p, file in present.items()}
    missing = expected.keys() - present.keys()
    extra = present.keys() - expected.keys()
    if missing or extra:
        raise SourceEquivalenceError(f"Git/archive file set differs: missing={len(missing)} extra={len(extra)}")
    verified_bytes = 0
    for path, (mode, expected_oid) in expected.items():
        archive_file = present[path]
        size = archive_file.stat().st_size
        verified_bytes += size
        if verified_bytes > max_bytes:
            raise SourceEquivalenceError("Git/archive comparison exceeds byte budget")
        if (bool(archive_file.stat().st_mode & 0o111)) != (mode == "100755"):
            raise SourceEquivalenceError("Git/archive executable mode differs")
        blob = hashlib.sha1()
        blob.update(b"blob " + str(size).encode("ascii") + b"\x00")
        with archive_file.open("rb") as src:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                blob.update(chunk)
        if blob.hexdigest() != expected_oid:
            raise SourceEquivalenceError("Git/archive file bytes differ")
    return {"schema_version": 1, "project": project_name,
            "locked_commit": projects[project_name]["commit_sha"], "git_tree_sha": tree_sha,
            "git_tree_equivalence": "TESTED", "mode_equivalence": "TESTED",
            "files_verified": len(expected), "bytes_verified": verified_bytes,
            "reference_kind": "LOCAL_PINNED_GIT_OBJECTS", "archive_root": prefix,
            "workspace_35_project_equivalence": "UNTESTED",
            "copyfile_linkfile": "UNTESTED", "patch_manager_eligible": False,
            "build_input_eligible": False, "device_boot": "UNTESTED"}
