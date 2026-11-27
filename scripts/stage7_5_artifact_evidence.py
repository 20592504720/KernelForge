"""Stage 7.5 offline OnePlus 13 artifact evidence; NEVER starts a build.

Read-only validation of copied Image/vmlinux/.config/log/timestamp bytes against
the exact reviewed source lock. A passing report proves file integrity checks,
NOT that Bazel ran, that the logged compiler environment was applied, or that a
kernel can boot. Keep real-build acceptance independently evidence-gated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

from kernelforge.build_timestamp import resolve_build_timestamp
from scripts.stage7_4_fast_build_gate import (
    ROOT,
    AdmissionBlocked,
    inspect_policy,
    inspect_source,
    require,
)

CLANG_REL = "kernel_platform/prebuilts/clang/host/linux-x86/clang-r510928/bin/clang"
# Stage 7.2 direct WSL2 binary audit; do not treat a different compiler as equivalent.
CLANG_SHA256 = "dc739fc44bb889146bd47732912cad457200af7de7c2fb5a7509b7a9974d6d67"
TARGET = re.compile(r"^//[A-Za-z0-9_./+\-]+:[A-Za-z0-9_.+\-]+$")
INPUT_FILES = ("Image", "vmlinux", ".config", "build.log", "build-time.json")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _within(path: Path, parent: Path) -> bool:
    item, root = path.resolve(), parent.resolve()
    return item == root or root in item.parents


def _regular(path: Path, parent: Path, min_size: int = 1) -> dict:
    require(path.is_file() and not path.is_symlink(), "MISSING_OR_SYMLINK_ARTIFACT:" + path.name)
    require(path.resolve().parent == parent.resolve(), "ARTIFACT_ESCAPES_BUNDLE:" + path.name)
    size = path.stat().st_size
    require(size >= min_size, "ARTIFACT_TOO_SMALL:" + path.name)
    return {"name": path.name, "size_bytes": size, "sha256": sha256_file(path)}


def _verify_vmlinux(path: Path) -> None:
    with path.open("rb") as stream:
        header = stream.read(64)
    require(len(header) >= 64 and header[:4] == b"\x7fELF" and
            header[4:7] == b"\x02\x01\x01", "VMLINUX_NOT_ELF64_LITTLE_ENDIAN")
    elf_type, machine, version = struct.unpack_from("<HHI", header, 16)
    require(machine == 183 and elf_type in (2, 3) and version == 1,
            "VMLINUX_NOT_AARCH64_EXECUTABLE")


def _verify_timestamp(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    require(type(raw) is dict and raw.get("mode") in ("custom", "current_utc"),
            "BUILD_TIMESTAMP_EVIDENCE_INVALID")
    value = raw.get("utc_iso8601")
    if not isinstance(value, str) or not value.endswith("Z"):
        raise AdmissionBlocked("BUILD_TIMESTAMP_UTC_MISSING")
    expected = resolve_build_timestamp(value)
    for key in ("utc_iso8601", "source_date_epoch", "kbuild_build_timestamp", "timezone"):
        require(raw.get(key) == expected[key], "BUILD_TIMESTAMP_INCONSISTENT:" + key)
    requested = raw.get("requested")
    if raw["mode"] == "custom":
        if not isinstance(requested, str) or not requested:
            raise AdmissionBlocked("CUSTOM_TIMESTAMP_REQUEST_MISSING")
        check = resolve_build_timestamp(requested)
        require(check["utc_iso8601"] == expected["utc_iso8601"],
                "CUSTOM_TIMESTAMP_DIFFERENT_INSTANT")
    else:
        require(requested == "", "DEFAULT_TIMESTAMP_HAS_REQUEST")
    return {key: raw[key] for key in (
        "mode", "requested", "utc_iso8601", "source_date_epoch",
        "kbuild_build_timestamp", "timezone"
    )}


def inspect_bundle(repo_root: Path, expected_lock_sha: str, source: Path,
                   host_disk: Path | None, bundle: Path, target: str,
                   declared_exit_code: int) -> dict:
    """Read-only check. No Bazel invocation, download, repo sync or file mutation."""
    require(type(declared_exit_code) is int and declared_exit_code == 0,
            "BUILD_EXIT_NOT_DECLARED_SUCCESS")
    require(isinstance(target, str) and len(target) <= 256 and TARGET.fullmatch(target),
            "EXACT_KLEAF_TARGET_REQUIRED")
    require(bundle.is_dir() and not bundle.is_symlink(), "BUNDLE_DIRECTORY_UNSAFE")
    require(source.is_dir() and not source.is_symlink(), "SOURCE_DIRECTORY_UNSAFE")
    require(not _within(bundle, source) and not _within(bundle, repo_root),
            "BUNDLE_OVERLAPS_SOURCE_OR_REPOSITORY")
    lock, profile, observed = inspect_policy(repo_root, expected_lock_sha)
    source_evidence = inspect_source(lock, source, host_disk)
    compiler = source / CLANG_REL
    require(compiler.is_file() and not compiler.is_symlink() and _within(compiler, source),
            "LOCKED_CLANG_MISSING_OR_UNSAFE")
    compiler_sha = sha256_file(compiler)
    require(compiler_sha == CLANG_SHA256, "LOCKED_CLANG_SHA256_MISMATCH")
    files = {name: _regular(bundle / name, bundle,
                            4096 if name in ("Image", "vmlinux") else 1)
             for name in INPUT_FILES}
    _verify_vmlinux(bundle / "vmlinux")
    with (bundle / "Image").open("rb") as stream:
        require(stream.read(4) != b"\x7fELF", "IMAGE_IS_VMLINUX_ELF")
    with (bundle / ".config").open("r", encoding="utf-8", errors="replace") as stream:
        require(any(line.strip() == "CONFIG_ARM64=y" for line in stream),
                "CONFIG_ARM64_NOT_ENABLED")
    stamp = _verify_timestamp(bundle / "build-time.json")
    return {
        "stage": "7.5", "status": "ARTIFACT_BYTES_CHECKED_BUILD_UNATTESTED",
        "device": profile["id"], "target_label": target,
        "locked_project_count": len(lock["source_lock"]["projects"]),
        "source_lock_sha256": observed, "manifest_commit": lock["manifest_commit"],
        "source_gate": {"project_heads_match": source_evidence["all_project_heads_match"],
                        "tracked_worktrees_clean": source_evidence["tracked_worktrees_clean"],
                        "capacity": source_evidence["capacity"]},
        "compiler": {"relative_path": CLANG_REL, "sha256": compiler_sha},
        "declared_build_exit_code": declared_exit_code,
        "artifacts": files, "timestamp_record": stamp,
        "actual_compiler_timestamp_propagation": "UNTESTED_REQUIRES_SANDBOX_EVIDENCE",
        "bazel_action_graph_and_dfr": "UNTESTED_REQUIRES_SEPARATE_AUDIT",
        "real_build_independently_verified": False,
        "image_vmlinux_built_by_command": "UNATTESTED",
        "device_flashable": False, "abi_kmi": "UNTESTED",
        "boot": "UNTESTED", "root": "UNTESTED",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--reviewed-lock-sha256", required=True)
    parser.add_argument("--source-workspace", required=True, type=Path)
    parser.add_argument("--host-disk", type=Path)
    parser.add_argument("--bundle", required=True, type=Path,
                        help="existing copy of Image, vmlinux, .config, build.log and build-time.json")
    parser.add_argument("--target", required=True, help="exact previously reviewed Kleaf label")
    parser.add_argument("--declared-build-exit-code", required=True, type=int)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        result = inspect_bundle(args.repo_root, args.reviewed_lock_sha256,
                                args.source_workspace, args.host_disk, args.bundle,
                                args.target, args.declared_build_exit_code)
        payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.report:
            require(args.report.parent.is_dir(), "REPORT_PARENT_MISSING")
            require(not args.report.exists() and not args.report.is_symlink(),
                    "REPORT_OVERWRITE_FORBIDDEN")
            require(all(not item.is_symlink() for item in args.report.parents),
                    "REPORT_SYMLINK_ANCESTOR_FORBIDDEN")
            require(all(not _within(args.report, root) for root in
                        (args.repo_root, args.source_workspace, args.bundle)),
                    "REPORT_INSIDE_PROTECTED_DIRECTORY")
            args.report.write_text(payload, encoding="utf-8")
        sys.stdout.write(payload)
        return 0
    except (AdmissionBlocked, ValueError, OSError, KeyError, TypeError) as exc:
        print("STAGE7_5_EVIDENCE_BLOCKED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
