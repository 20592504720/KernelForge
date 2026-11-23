"""Stage 7.4 read-only, fail-closed OnePlus 13 fast-build admission."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

from kernelforge.build_timestamp import resolve_build_timestamp
from scripts.verify_sm8750_sync import (
    ROOT_PROJECT, ROOT_REPOSITORY, git_value, inspect_projects,
    project_path, verify_manifest_selection,
)

ROOT = Path(__file__).resolve().parents[1]
LOCK = "manifests/oneplus13-pjz110-sm8750-source.lock.json"
PROFILE = "devices/profiles/oneplus13-pjz110.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")


class AdmissionBlocked(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise AdmissionBlocked(reason)


def inspect_policy(root, expected_sha):
    require(isinstance(expected_sha, str) and SHA64.fullmatch(expected_sha),
            "REVIEWED_LOCK_SHA256_REQUIRED")
    raw = (root / LOCK).read_bytes()
    observed = hashlib.sha256(raw).hexdigest()
    require(observed == expected_sha, "SOURCE_LOCK_SHA256_CHANGED")
    lock = json.loads(raw)
    profile = json.loads((root / PROFILE).read_text(encoding="utf-8"))
    require(lock.get("schema_version") == 1 and
            lock.get("device_profile") == "oneplus13-pjz110" and
            profile.get("id") == "oneplus13-pjz110" and
            profile.get("model") == "PJZ110" and
            profile.get("soc") == "SM8750" and
            profile.get("kernel_version") == "6.6" and
            profile.get("architecture") == "arm64", "DEVICE_PROFILE_UNREVIEWED")
    manifest = profile.get("manifest", {})
    require(lock.get("manifest_commit") == manifest.get("commit")
            and lock.get("manifest_path") == manifest.get("path")
            and str(lock.get("manifest_repository", "")).removesuffix(".git")
                == str(manifest.get("repository", "")).removesuffix(".git")
            and SHA40.fullmatch(str(lock.get("manifest_commit"))),
            "MANIFEST_IDENTITY_MISMATCH")
    source = lock.get("source_lock", {})
    projects = source.get("projects")
    require(source.get("project_count") == 35 and isinstance(projects, list)
            and len(projects) == 35, "SOURCE_PROJECT_COUNT_NOT_35")
    names, paths = set(), set()
    for item in projects:
        require(isinstance(item, dict), "INVALID_PROJECT_ENTRY")
        name, path = item.get("name"), item.get("path")
        require(isinstance(name, str) and name and name not in names,
                "DUPLICATE_PROJECT")
        require(isinstance(path, str) and path and path not in paths,
                "DUPLICATE_PROJECT_PATH")
        require(SHA40.fullmatch(str(item.get("commit_sha"))),
                "MUTABLE_PROJECT_COMMIT")
        require(str(item.get("repository", "")).startswith("https://"),
                "UNTRUSTED_PROJECT_REPOSITORY")
        if path == "./":
            require(name == ROOT_PROJECT and item.get("repository") == ROOT_REPOSITORY,
                    "UNREVIEWED_ROOT_PROJECT")
        else:
            require("\\" not in path and ":" not in path
                    and not PurePosixPath(path).is_absolute()
                    and all(bit not in ("", ".", "..") for bit in path.split("/")),
                    "UNSAFE_PROJECT_PATH")
        names.add(name)
        paths.add(path)
    require("./" in paths, "VENDOR_ROOT_NOT_LOCKED")
    return lock, profile, observed


def sample_capacity(path, reserve_gib):
    require(path.is_dir() and not path.is_symlink(), "RESOURCE_PATH_UNSAFE")
    capacity = shutil.disk_usage(path)
    require(capacity.free >= reserve_gib * (1024 ** 3),
            "DISK_RESERVE_EXHAUSTED")
    result = {"path": str(path), "free_bytes": capacity.free,
              "total_bytes": capacity.total, "reserve_gib": reserve_gib}
    if hasattr(os, "statvfs"):
        stats = os.statvfs(path)
        result["free_inodes"] = stats.f_favail
        require(stats.f_favail >= 100000, "INODE_RESERVE_EXHAUSTED")
    return result


def inspect_source(lock, source, host_disk=None):
    require(source.is_dir() and not source.is_symlink()
            and (source / ".repo/manifests").is_dir(),
            "EXISTING_REPO_SOURCE_REQUIRED")
    is_wsl = "microsoft" in platform.release().lower() or bool(os.getenv("WSL_DISTRO_NAME"))
    require(not is_wsl or host_disk is not None,
            "WSL_PHYSICAL_HOST_DISK_REQUIRED")
    capacity = {"source": sample_capacity(source, 20)}
    if host_disk is not None:
        capacity["host"] = sample_capacity(host_disk, 50)
    try:
        verify_manifest_selection(source, lock)
        manifest_head = git_value(source / ".repo/manifests",
                                  "rev-parse", "--verify", "HEAD^{commit}")
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError) as exc:
        raise AdmissionBlocked("SELECTED_MANIFEST_UNVERIFIED") from exc
    require(manifest_head == lock["manifest_commit"], "MANIFEST_HEAD_MISMATCH")
    projects = lock["source_lock"]["projects"]
    results = inspect_projects(source, projects)
    bad = [entry["name"] for entry in results if not entry["matches_lock"]]
    require(not bad, "PROJECT_HEAD_MISMATCH:" + ",".join(bad[:5]))
    for entry in projects:
        try:
            status = git_value(project_path(source, entry), "status",
                               "--porcelain", "--untracked-files=no")
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            raise AdmissionBlocked("SOURCE_WORKTREE_CHECK_FAILED") from exc
        require(not status, "SOURCE_TRACKED_WORKTREE_DIRTY:" + entry["name"])
    return {"selected_manifest_sha": manifest_head, "checked_projects": len(results),
            "all_project_heads_match": True,
            "tracked_worktrees_clean": True, "capacity": capacity}


def evaluate(root, reviewed_sha, *, build_timestamp="", source=None, host_disk=None):
    lock, profile, sha = inspect_policy(root, reviewed_sha)
    stamp = resolve_build_timestamp(build_timestamp)
    result = {
        "stage": "7.4", "scope": "READ_ONLY_NO_COMPILATION",
        "device": profile["id"], "kernel_version": "6.6",
        "manifest_commit": lock["manifest_commit"],
        "source_lock_sha256": sha, "locked_projects": 35,
        "timestamp_preflight_preview": stamp,
        "ccache_enabled": False, "build_started": False,
        "build_eligible": False, "flashable_release_eligible": False,
        "remaining": ["KLEAF_TARGET_AND_DFR_UNKNOWN", "BAZEL_ACTION_ENV_UNTESTED",
                      "REAL_IMAGE_VMLINUX_UNTESTED", "MODULE_ABI_KMI_UNTESTED",
                      "DEVICE_BOOT_ROOT_UNTESTED"],
    }
    if source is None:
        result["status"] = "POLICY_TESTED_SOURCE_UNTESTED"
    else:
        result["source_evidence"] = inspect_source(lock, source, host_disk)
        result["status"] = "SOURCE_LOCK_TESTED_BUILD_BLOCKED"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--reviewed-lock-sha256", required=True)
    parser.add_argument("--build-timestamp", default="")
    parser.add_argument("--source-workspace", type=Path)
    parser.add_argument("--host-disk", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        require(args.host_disk is None or args.source_workspace is not None,
                "HOST_DISK_WITHOUT_SOURCE")
        result = evaluate(args.repo_root, args.reviewed_lock_sha256,
                          build_timestamp=args.build_timestamp,
                          source=args.source_workspace, host_disk=args.host_disk)
        output = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.report:
            require(args.report.parent.is_dir(), "REPORT_PARENT_ABSENT")
            args.report.write_text(output, encoding="utf-8")
        sys.stdout.write(output)
        return 0
    except (AdmissionBlocked, ValueError, OSError, KeyError) as exc:
        print("STAGE7_4_BLOCKED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
