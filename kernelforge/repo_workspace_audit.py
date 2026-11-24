"""Stage 6.3 read-only audit of an already-synchronized Android Repo workspace.

Requires existing pinned manifest Git checkout and existing project checkouts.
Performs no network I/O, repo sync, checkout, patch, file copy or symlink writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from .source_archive import locked_projects
from .source_equivalence import SourceEquivalenceError, _git, _valid_path, workspace_plan


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def audit_locked_workspace(lock: dict, workspace: Path, manifest_checkout: Path) -> dict:
    """Check 35 locked project HEADs/trees and Repo link/copyfile effects.

    This is an audit of current *checkout identity and specific directives*, not
    proof of full workspace byte equivalence, ABI, build, module or device boot.
    """
    projects = locked_projects(lock)
    workspace = Path(workspace).absolute()
    manifest_checkout = Path(manifest_checkout).absolute()
    if workspace.is_symlink() or not workspace.is_dir():
        raise SourceEquivalenceError("workspace root must be a real directory")
    if manifest_checkout.is_symlink() or not manifest_checkout.is_dir():
        raise SourceEquivalenceError("pinned manifest checkout missing")
    expected_manifest = lock["manifest_commit"]
    manifest_head = _git(manifest_checkout, "rev-parse", "--verify", "HEAD^{commit}").lower()
    if manifest_head != expected_manifest:
        raise SourceEquivalenceError("manifest checkout HEAD differs from pinned manifest")
    manifest_path = _valid_path(lock.get("manifest_path"))
    if ":" in manifest_path or manifest_path.startswith("-"):
        raise SourceEquivalenceError("unsafe manifest snapshot path")
    # Inspect exact Git blob in pinned manifest checkout, not an unauthenticated file.
    try:
        original_xml = _git(manifest_checkout, "show", "HEAD:" + manifest_path, binary=True)
        xml = original_xml.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise SourceEquivalenceError("manifest snapshot not valid UTF-8") from exc
    plan = workspace_plan(lock, xml)
    checked_projects = []
    for row in plan["mount_order"]:
        path = workspace if row["path"] == "./" else workspace.joinpath(*row["path"].split("/"))
        if path.is_symlink() or not path.is_dir() or not _inside(path.absolute(), workspace):
            raise SourceEquivalenceError("locked project workspace directory missing or unsafe")
        commit = _git(path, "rev-parse", "--verify", "HEAD^{commit}").lower()
        if commit != row["commit_sha"]:
            raise SourceEquivalenceError("workspace project HEAD differs from pinned lock: " + row["name"])
        tree = _git(path, "rev-parse", "--verify", "HEAD^{tree}").lower()
        checked_projects.append({"name": row["name"], "path": row["path"],
                                 "commit_sha": commit, "tree_sha": tree,
                                 "head_identity": "TESTED"})
    evidence = []
    for directive in plan["copyfile_linkfile"]:
        project = projects[directive["project"]]
        root = workspace if project["path"] == "./" else workspace.joinpath(*project["path"].split("/"))
        src = root if directive["src"] == "." else root.joinpath(*directive["src"].split("/"))
        dst = workspace.joinpath(*directive["dest"].split("/"))
        if not src.exists() or not _inside(src.resolve(strict=True), workspace.resolve(strict=True)):
            raise SourceEquivalenceError("link/copy source missing or outside repo workspace")
        if directive["kind"] == "linkfile":
            if not dst.is_symlink() or not dst.exists():
                raise SourceEquivalenceError("Repo linkfile not materialized as a valid symlink")
            if dst.resolve(strict=True) != src.resolve(strict=True):
                raise SourceEquivalenceError("Repo linkfile target does not match pinned manifest")
            result = "TESTED"
        else:
            if dst.is_symlink() or not src.is_file() or not dst.is_file():
                raise SourceEquivalenceError("Repo copyfile source/destination not regular files")
            if src.stat().st_size != dst.stat().st_size or _sha(src) != _sha(dst):
                raise SourceEquivalenceError("Repo copyfile bytes differ")
            result = "TESTED"
        evidence.append({"project": directive["project"], "kind": directive["kind"],
                         "src": directive["src"], "dest": directive["dest"],
                         "application": result})
    return {"schema_version": 1, "device_profile": lock["device_profile"],
            "manifest_repository": lock["manifest_repository"],
            "manifest_commit": manifest_head,
            "manifest_path": manifest_path,
            "manifest_sha256": hashlib.sha256(original_xml).hexdigest(),
            "manifest_git_identity": "TESTED",
            "project_count": len(checked_projects),
            "locked_heads": "TESTED" if len(checked_projects) == len(projects) else "UNTESTED",
            "projects": checked_projects,
            "root_projects": plan["root_projects"],
            "nested_mounts": plan["nested_mounts"],
            "link_copyfile_count": len(evidence),
            "link_copyfiles": evidence,
            "link_copyfile_application": "TESTED",
            "workspace_overlay_byte_equivalence": "UNTESTED",
            "real_vendor_archive_git_tree_equivalence": "UNTESTED",
            "device_abi": "UNTESTED", "device_boot": "UNTESTED"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--manifest-checkout", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        lock = json.loads(arguments.lock.read_text(encoding="utf-8"))
        evidence = audit_locked_workspace(lock, arguments.workspace, arguments.manifest_checkout)
    except (SourceEquivalenceError, OSError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({"status": "PASS", "evidence": evidence}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
