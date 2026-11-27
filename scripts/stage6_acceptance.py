"""Stage 6.5: strictly scoped, offline Stage 1–6 evidence reconciliation.

This reads committed artifacts only: it does not authenticate the original WSL
disk bytes, start a build, query network resources or grant device-flashability.
Live cross-platform tests and pinned GKI builds belong to the separate
one-shot Stage 1–6 acceptance workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
LOCK = "manifests/oneplus13-pjz110-sm8750-source.lock.json"
ACCEPTED = "docs/evidence/stage6_3_wsl2_acceptance.json"
WORKTREE = "docs/evidence/stage6_3_wsl2_blocker_diagnosis.json"
DEPENDENCIES = "docs/evidence/stage6_3_final_dependency_audit.json"
CATALOG = "patches/compat/susfs/manifest.json"
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class Stage6AcceptanceError(ValueError):
    pass


def require(value: bool, problem: str) -> None:
    if not value:
        raise Stage6AcceptanceError(problem)


def load(root: Path, name: str) -> dict[str, Any]:
    path = root / name
    require(path.is_file() and not path.is_symlink(), f"missing/unsafe committed evidence: {name}")
    try:
        item = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Stage6AcceptanceError(f"invalid committed evidence: {name}") from exc
    require(type(item) is dict, f"invalid evidence object: {name}")
    # JSON object keys are strings by definition; the exact-dict guard above
    # establishes the boundary before the evidence-specific checks use values.
    return cast(dict[str, Any], item)


def dict_rows(value: object, problem: str) -> list[dict[str, Any]]:
    """Validate a JSON array-of-objects before using its evidence fields."""
    if type(value) is not list or any(type(row) is not dict for row in value):
        raise Stage6AcceptanceError(problem)
    return cast(list[dict[str, Any]], value)


def audit(root: Path = ROOT) -> dict:
    root = Path(root)
    lock, first, second, final, compat = (load(root, path) for path in
        (LOCK, ACCEPTED, WORKTREE, DEPENDENCIES, CATALOG))
    projects = dict_rows(lock.get("source_lock", {}).get("projects"),
                         "OnePlus 13 locked project count must be 35")
    require(len(projects) == 35
            and lock["source_lock"].get("project_count") == 35,
            "OnePlus 13 locked project count must be 35")
    require(lock.get("manifest_commit") == "f8e50677874c65b6da41057d2f39be7b4ef3c08a",
            "manifest commit differs from reviewed OnePlus 13 baseline")
    mapped = {}
    for project in projects:
        name, sha = project["name"], project["commit_sha"]
        require(name not in mapped and _HEX40.fullmatch(sha) is not None,
                "source lock contains duplicate/non-immutable projects")
        mapped[name] = (project["path"], sha)
    require(sum(project["path"] == "./" for project in projects) == 1,
            "OnePlus 13 root project mount mismatch")

    prior = first.get("source_audit", {})
    require(first.get("status") == "PARTIAL_TESTED_WITH_BLOCKERS"
            and prior.get("status") == "PASS"
            and prior.get("matched_heads") == 35
            and prior.get("project_count") == 35,
            "Stage 6.3 original 35-project WSL evidence differs")
    rows = dict_rows(prior.get("project_commit_tree_records"),
                     "original WSL project identity inventory incomplete")
    require(len(rows) == 35,
            "original WSL project identity inventory incomplete")
    observed = {}
    for item in rows:
        name = item["name"]
        require(name in mapped and name not in observed
                and item["commit_sha"] == mapped[name][1]
                and item["path"] == mapped[name][0]
                and _HEX40.fullmatch(item["tree_sha"]) is not None
                and item["head_identity"] == "TESTED",
                "original WSL project commit/Tree inventory conflicts with source lock")
        observed[name] = item["tree_sha"]
    counts = first.get("tracked_link_inventory", {}).get("counts", {})
    require(counts.get("tracked_symlinks") == 1206
            and counts.get("materialized_symlinks") == 1206
            and counts.get("target_hash_mismatch") == 0
            and counts.get("broken_target") == 29,
            "Stage 6.3 tracked link inventory changed")

    work = second.get("tracked_worktree", {})
    require(second.get("broken_link_count") == 29
            and work.get("project_count") == 35
            and work.get("raw_byte_equal_projects") == 34
            and work.get("raw_blob_mismatches") == 33
            and work.get("missing_tracked") == 0
            and work.get("wrong_executable_mode") == 0
            and work.get("wrong_symlink_type") == 0
            and work.get("root_child_overlap") == 0
            and work.get("clean_filtered_match") is True,
            "Stage 6.3 worktree status is inconsistent")
    checked = dict_rows(work.get("projects"),
                        "Stage 6.3 tracked worktree project inventory incomplete")
    require(len(checked) == 35,
            "Stage 6.3 tracked worktree project inventory incomplete")
    checked_names = set()
    for item in checked:
        name = item["name"]
        require(name in mapped and name not in checked_names
                and item["actual_commit"] == mapped[name][1]
                and item["tree_sha"] == observed[name]
                and item["counts"]["missing"] == 0
                and item["counts"]["wrong_mode"] == 0
                and item["counts"]["wrong_type"] == 0
                and item["counts"]["overlay_conflict"] == 0,
                "Stage 6.3 tracked worktree conflicts with locked Git")
        checked_names.add(name)
    require(second.get("archive_link_proof", {}).get("status") == "TEST_FIXTURE_ONLY",
            "Archive fixture evidence must not be promoted to vendor proof")

    status = final.get("all_29_risk_counts_after_this_audit")
    require(status == {"VERIFIED_NOT_REQUIRED": 28,
                       "BLOCKED_UNDETERMINED": 1, "BLOCKED_BUILD": 0},
            "Stage 6.3 DFR blocker cannot be removed by report editing")
    require(final.get("reviewed_link_count") == 24
            and final.get("bazel_query_executed") is False
            and final.get("kernel_build_executed") is False
            and final.get("source_modified") is False,
            "Stage 6.3 final dependency audit scope changed")
    lz4 = final.get("lz4", {})
    require(lz4.get("file_count") == 33
            and lz4.get("git_clean_equivalence") == "TESTED"
            and lz4.get("raw_byte_equivalence") == "BLOCKED"
            and lz4.get("source_unchanged") is True,
            "lz4 CRLF exception must retain raw/clean distinction")
    files = dict_rows(lz4.get("files"),
                      "lz4 normalized contents missing original 33-file details")
    require(len(files) == 33
            and len({f["path"] for f in files}) == 33
            and all(f["git_clean_equivalent"] is True
                    and f["raw_worktree_byte_equal"] is False
                    and f["clean_blob"] == f["expected_blob"] for f in files),
            "lz4 normalized contents missing original 33-file details")

    expected_provider = {
        "2a60b2893b8d0d885d1ceff2287d8ad854f0e0f4",
        "7b65bde0710b5e7c6f755545cb15a4abd417f3a8",
        "2734e0bc155759955880f5fb99be640fc5b92156",
    }
    require(compat.get("kernel_commit") == "498f91c17b0822a09aede17d26a63bf8c6813725"
            and compat.get("susfs_commit") == "756abbf2d81557e36664fc67dffaee26d3dfc57c"
            and compat.get("android_gki") == "android14-6.1"
            and type(compat.get("provider_commits")) is list
            and len(compat["provider_commits"]) == 3
            and set(compat["provider_commits"]) == expected_provider,
            "reviewed exact source matrix changed")
    patch_file = root / "patches/compat/susfs" / compat["file"]
    require(patch_file.is_file() and not patch_file.is_symlink()
            and patch_file.parent.resolve() == (root / "patches/compat/susfs").resolve()
            and _HEX64.fullmatch(compat.get("sha256", "")) is not None
            and hashlib.sha256(patch_file.read_bytes()).hexdigest() == compat["sha256"],
            "reviewed SUSFS context adapter digest mismatch")

    stage_ids = ["1", "2", "3", "4", "5", "6.1", "6.2", "6.3", "6.4", "6.5"]
    return {
        "schema_version": 1,
        "scope": "stages_1_through_6_scoped_acceptance",
        "result": "COMMITTED_EVIDENCE_RECONCILED_NOT_FULL_RUN_RESULT",
        "stage_ids": stage_ids,
        "source_lock": {
            "device": "oneplus13-pjz110", "manifest_commit": lock["manifest_commit"],
            "project_commit_tree_inventory": "COMMITTED_LOCAL_WSL2_EVIDENCE_35_OF_35",
            "worktree_git_clean_equivalence": "COMMITTED_LOCAL_WSL2_EVIDENCE_35_OF_35",
            "raw_byte_equivalence": "34_OF_35_LZ4_CRLF",
            "independent_wsl_disk_recheck_this_run": "UNTESTED",
        },
        "compatibility": {
            "reviewed_kernel_commit": compat["kernel_commit"],
            "reviewed_susfs_commit": compat["susfs_commit"],
            "provider_commits": sorted(expected_provider),
            "adapter_sha256_verified": compat["sha256"],
            "latest_branch_bakasu": "BLOCKED_UNREVIEWED",
            "full_kernel_ci": "PENDING_SEPARATE_ONE_SHOT_RUN",
        },
        "deferred_blockers": [
            "DFR_INCLUDE_DYNAMIC_MODULE_DEPENDENCY_BLOCKED_UNDETERMINED",
            "ARCHIVE_INDEPENDENT_VENDOR_PROVENANCE_UNTESTED",
            "STAGE7_TOOLCHAIN_FAST_BUILD_UNTESTED",
            "ONEPLUS13_FULL_OKI_MODULES_ABI_KMI_UNTESTED",
            "DEVICE_IMAGE_BOOT_ROOT_SUSFS_RUNTIME_UNTESTED",
        ],
        "full_run_acceptance": "PENDING",
        "flashable_release_eligible": False,
        "sources": [LOCK, ACCEPTED, WORKTREE, DEPENDENCIES, CATALOG],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print("STAGE6_EVIDENCE_RECONCILED; full CI acceptance still pending")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, Stage6AcceptanceError) as exc:
        print("STAGE6_EVIDENCE_REJECTED: " + str(exc))
        raise SystemExit(2)
