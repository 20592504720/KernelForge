"""Stage 7.1 read-only repository / optional local WSL2 inventory.

This program never runs bazel, bazelisk, git, compilers, syncs, installs,
downloads, or writes a workspace. Standard library only; stdout is JSON.
An inventory is not permission to build or evidence of toolchain usability.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SHA = re.compile(r"^[0-9a-f]{40}$")
_REQUIRED_METHODS = frozenset({
    "prepare", "_validate", "_download_install", "_cached",
    "_key", "_tool_paths", "_verify_tools", "list_cache",
    "clean_cache", "release",
})
_PROBES = (
    "git", "repo", "bazel", "bazelisk", "clang", "ld.lld", "llvm-nm",
    "gcc", "gcc-11", "ccache", "python3", "java", "zstd",
)


class Stage71AuditError(ValueError):
    pass


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise Stage71AuditError(message)


def _text(root: Path, relative: str) -> str:
    p = root / relative
    _require(p.is_file() and not p.is_symlink(), "missing or symlinked reviewed file: " + relative)
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise Stage71AuditError("unreadable reviewed file: " + relative) from exc


def _json(root: Path, relative: str) -> dict:
    try:
        result = json.loads(_text(root, relative))
    except json.JSONDecodeError as exc:
        raise Stage71AuditError("invalid JSON: " + relative) from exc
    _require(type(result) is dict, "expected JSON object: " + relative)
    return result


def _methods(code: str, class_name: str) -> set[str]:
    try:
        module = ast.parse(code)
    except SyntaxError as exc:
        raise Stage71AuditError("ToolchainManager Python AST invalid") from exc
    for item in module.body:
        if isinstance(item, ast.ClassDef) and item.name == class_name:
            return {n.name for n in item.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    raise Stage71AuditError(class_name + " not found")


def audit_repository(root: Path = ROOT) -> dict:
    """Validate pinned Stage 7.1 *policy evidence*, not executable toolchains."""
    root = Path(root)
    tools = _json(root, "configs/toolchains/defaults.json")
    schema = _json(root, "schemas/toolchain.schema.json")
    device = _json(root, "devices/profiles/oneplus13-pjz110.json")
    lock = _json(root, "manifests/oneplus13-pjz110-sm8750-source.lock.json")
    source = _text(root, "kernelforge/toolchains/manager.py")
    build = _text(root, ".github/workflows/build.yml")
    release = _text(root, ".github/workflows/release.yml")
    audit_workflow = _text(root, ".github/workflows/source-audit.yml")
    full_workflow = _text(root, ".github/workflows/stage1-6-full-acceptance.yml")
    _require(tools.get("schema_version") == 1 and schema.get("type") == "object",
             "toolchain schema/defaults identity mismatched")
    _require(tools.get("download", {}).get("require_sha256") is True
             and tools.get("cache", {}).get("enabled") is True
             and tools.get("mode") in {"AUTO", "LOCAL_ONLY", "DOWNLOAD_ONLY"},
             "toolchain checksum/cache safety defaults have been weakened")
    required = {"download", "cache", "mode"}
    _require(required.issubset(set(schema.get("required", []))),
             "toolchain schema no longer requires safety controls")
    _require(_REQUIRED_METHODS.issubset(_methods(source, "ToolchainManager")),
             "ToolchainManager safety/audit methods missing")
    _require("SHA256_RE.fullmatch(digest)" in source
             and "cached installed toolchain content mismatch" in source
             and "source_adapters" in source,
             "ToolchainManager documented trust checks no longer visible")
    _require("llvm-release" in source and "gcc-release" in source,
             "Stage 7.1 source-adapter inventory changed")
    _require(device.get("id") == "oneplus13-pjz110"
             and device.get("kernel_version") == "6.6"
             and device.get("soc") == "SM8750"
             and device.get("manifest", {}).get("commit") == lock.get("manifest_commit"),
             "OnePlus 13 device/source-lock mismatch")
    projects = lock.get("source_lock", {}).get("projects")
    _require(isinstance(projects, list) and len(projects) == 35
             and lock["source_lock"].get("project_count") == 35,
             "OnePlus 13 immutable 35-project lock changed")
    identities = [(p.get("name"), p.get("path")) for p in projects]
    _require(len(set(identities)) == 35
             and all(isinstance(p.get("commit_sha"), str)
                     and _SHA.fullmatch(p["commit_sha"]) for p in projects)
             and sum(p.get("path") == "./" for p in projects) == 1,
             "source lock has duplicate/unsafe or mutable project identity")
    _require("Stop after preflight" in build
             and "preflight only" in build.lower(),
             "legacy build entry no longer clearly refuses real builds")
    # Exact reviewed template: workflow_dispatch is the only trigger, and the
    # job requires an impossible event name. Pin the whole recipe so an added
    # event, job, permission, upload or alternate YAML spelling needs re-review.
    _require(hashlib.sha256(release.encode('utf-8')).hexdigest()
             == '51dbccd13ecfd1bd16f4ff08c437b46d3077a23631054eba6006b7c815c5ac5b',
             "release workflow no longer fail-closed or read-only")
    _require("[run-sm8750-once]" in audit_workflow
             and "full_sync" in audit_workflow,
             "source sync gate changed: requires explicit re-review")
    _require("stage6-full-acceptance-request.json" in full_workflow,
             "historical full-acceptance entry identity changed")
    return {
        "schema_version": 1,
        "stage": "7.1",
        "status": "REPOSITORY_PREFLIGHT_TESTED_WITH_BLOCKERS",
        "audit_kind": "READ_ONLY_STATIC_CODE_AND_CONFIG_REVIEW",
        "does_not_execute": ["git", "repo", "bazel", "bazelisk", "compiler", "downloads", "builds"],
        "toolchain_manager": {
            "implementations": ["LLVM", "GCC"],
            "inspection": "STATIC_METHOD_INVENTORY_ONLY",
            "methods_present": sorted(_REQUIRED_METHODS),
            "defaults_sha256_required": True,
            "cached_archive_and_tree_checks": "STATIC_CODE_PRESENT_PRIOR_CI_EVIDENCE",
            "release_source_aliases": ["llvm-release", "gcc-release"],
            "github_release_asset_provenance": "NOT_IMPLEMENTED",
            "large_upstream_archive_real_layout_test": "UNTESTED",
        },
        "build_profiles": {
            "device": device["id"],
            "kernel_family": device["kernel_version"],
            "manifest_commit": lock["manifest_commit"],
            "fixed_project_count": 35,
            "device_toolchain_pin": "BLOCKED_MISSING" if device.get("toolchain") is None else "DECLARED_UNVERIFIED",
            "firmware_build_pin": "BLOCKED_MISSING" if device.get("firmware_build") is None else "DECLARED_UNVERIFIED",
            "abi_kmi": "UNTESTED" if device.get("abi_kmi") is None else "DECLARED_UNVERIFIED",
            "oneplus13_fast_build": "NOT_IMPLEMENTED",
        },
        "workflow_gates": {
            "build_yml": "PREFLIGHT_ONLY_PLACEHOLDER",
            "release_yml": "DISABLED",
            "locked_sm8750_sync": "EXPLICITLY_GATED",
            "stage1_6_full": "IMMUTABLE_MARKER_GATED_HISTORICAL",
            "stage7_fast_build": "NOT_IMPLEMENTED",
        },
        "cache": {
            "toolchain_cache": "IMPLEMENTED_PRIOR_FIXTURE_TESTED",
            "ccache_shared_build_cache": "NOT_IMPLEMENTED",
            "separate_gki_vendor_cache_keys": "NOT_IMPLEMENTED",
            "cross_device_cache_rejection": "NOT_IMPLEMENTED",
        },
        "remaining": [
            "LOCAL_WSL2_TOOLCHAIN_HOST_INVENTORY_REQUIRED",
            "REVIEWED_RELEASE_MIRROR_PROVENANCE_REQUIRED",
            "ISOLATED_CCACHE_POLICY_REQUIRED",
            "EXPLICIT_STAGE7_FAST_BUILD_WORKFLOW_REQUIRED",
            "ONEPLUS13_FAST_KLEAF_BUILD_UNTESTED",
            "DFR_EXTERNAL_MODULE_DEPENDENCY_BLOCKED_UNDETERMINED",
        ],
        "build_authorized": False,
        "flashable_release_eligible": False,
    }


def _filesystem(path: Path) -> dict:
    result = {"path": str(path), "exists": path.is_dir()}
    if not result["exists"]:
        return result
    try:
        usage = shutil.disk_usage(path)
        result.update(total_bytes=usage.total, used_bytes=usage.used,
                      free_bytes=usage.free)
        statvfs = getattr(os, "statvfs", None)
        if statvfs is not None:
            info = statvfs(path)
            result.update(available_inodes=info.f_favail, total_inodes=info.f_files)
    except OSError as exc:
        result["inspection_error"] = type(exc).__name__
    return result


def _memory() -> dict:
    mem = Path("/proc/meminfo")
    if not mem.is_file():
        return {"status": "NOT_AVAILABLE_ON_HOST"}
    try:
        fields = {}
        for line in mem.read_text(encoding="utf-8").splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
                    fields[key + "_kib"] = int(val.strip().split()[0])
        return fields
    except (OSError, ValueError, IndexError):
        return {"status": "UNREADABLE"}


def audit_local(workspace: Path, host_path: Path | None = None) -> dict:
    """Only stat/check binary locations. Never execute Bazelisk or touch Git index."""
    source = Path(workspace).expanduser().resolve()
    tool_paths = {}
    for name in _PROBES:
        raw = shutil.which(name)
        tool_paths[name] = {"status": "PATH_VISIBLE_VERSION_UNTESTED", "path": raw} if raw else {
            "status": "NOT_ON_PATH"}
    return {
        "status": "LOCAL_READ_ONLY_INVENTORY_NOT_BUILD_VALIDATION",
        "workspace": {
            "path": str(source),
            "exists": source.is_dir(),
            "repo_manifest_directory_present": (source / ".repo/manifests").is_dir(),
            "selected_manifest_entry_present": (source / ".repo/manifest.xml").exists(),
            "source_identity": "NOT_RECHECKED",
            "content_equivalence": "NOT_RECHECKED",
        },
        "filesystems": {
            "ext4_or_workspace": _filesystem(source),
            "windows_host_drive": _filesystem(Path(host_path).expanduser()) if host_path is not None
                                  else {"status": "HOST_DRIVE_NOT_SUPPLIED"},
        },
        "host": {
            "system": platform.system(), "architecture": platform.machine(),
            "python": platform.python_version(), "cpus": os.cpu_count(),
            "memory": _memory(),
        },
        "tools": tool_paths,
        "version_commands_executed": False,
        "git_commands_executed": False,
        "network_access_attempted": False,
        "source_mutated": False,
        "build_eligible": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--workspace", type=Path,
                        help="optional existing WSL2 Repo workspace; never modified")
    parser.add_argument("--host-path", type=Path, help="optional mounted Windows drive")
    args = parser.parse_args(argv)
    if args.host_path is not None and args.workspace is None:
        parser.error("--host-path requires --workspace")
    try:
        result = audit_repository(args.repo)
        if args.workspace is not None:
            result["local"] = audit_local(args.workspace, args.host_path)
    except Stage71AuditError as exc:
        print("STAGE7_1_PREFLIGHT_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
