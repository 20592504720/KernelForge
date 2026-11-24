"""Stage 6.4 immutable KernelSU/BakaSU/SUSFS compatibility admission preflight.

Read-only by design. Verifies declared version-lock provenance and the reviewed
adapter's local digest. Actual Git HEAD verification and upstream +/- patch
comparison remain required in compatibility.select() at integration time.
This preflight never grants Image, flashable, Root, or ABI/KMI eligibility.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


class CompatibilityGateError(ValueError):
    """A version combination has not met the reviewed-pinned-source gate."""


_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
OFFICIAL_REPO = "https://github.com/tiann/KernelSU.git"
BAKA_REPO = "https://github.com/Baka-SU/BakaSU.git"
SUSFS_REPO = "https://gitlab.com/simonpunk/susfs4ksu.git"
KERNEL_REPO = "https://github.com/aosp-mirror/kernel_common.git"

# Exact source identities with a reviewed adapter; NOT an automatically
# growing list of releases. Source-family bindings are independent of the
# compatibility manifest so adding a new SHA to JSON alone cannot admit it.
REVIEWED_PROVIDERS = {
    "official": frozenset({"2a60b2893b8d0d885d1ceff2287d8ad854f0e0f4"}),
    "bakasu": frozenset({
        "7b65bde0710b5e7c6f755545cb15a4abd417f3a8",
        "2734e0bc155759955880f5fb99be640fc5b92156",
    }),
}
EXPECTED_GKI = "android14-6.1"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CompatibilityGateError(message)


def _pairs_unique(pairs):
    result = {}
    for name, value in pairs:
        _require(name not in result, "duplicate compatibility manifest key")
        result[name] = value
    return result


def _read_catalog(catalog: Path) -> dict:
    catalog = Path(catalog)
    _require(catalog.is_file() and not catalog.is_symlink(), "missing or symlinked compatibility catalog")
    try:
        value = json.loads(catalog.read_text(encoding="utf-8"), object_pairs_hook=_pairs_unique)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CompatibilityGateError("unreadable compatibility catalog") from exc
    _require(type(value) is dict and value.get("schema_version") == 1, "unsupported compatibility catalog schema")
    return value


def _pinned(lock: dict, name: str, expected_repo: str) -> str:
    _require(type(lock) is dict, f"{name} lock missing")
    sha = lock.get("commit_sha")
    _require(isinstance(sha, str) and _SHA.fullmatch(sha) is not None,
             f"{name} requires an exact lowercase 40-hex Commit")
    _require(lock.get("repository") == expected_repo, f"{name} repository identity mismatch")
    _require(lock.get("policy") == "pinned", f"{name} must be pinned before discovery")
    _require(lock.get("ref_type") == "commit" and lock.get("requested_ref") == sha,
             f"{name} must request the exact Commit, not a branch/tag")
    return sha


def evaluate_reviewed(lock: dict, *, provider: str, catalog: Path) -> dict:
    """Classify a declared immutable source triple without fetching or mutating it.

    Only use with a separately verified versions.lock and real Git checkouts.
    A matching declarative lock is not proof that those checkout bytes exist.
    """
    _require(type(lock) is dict, "source-lock record missing")
    normalized = "bakasu" if provider == "bakssu" else provider
    _require(normalized in REVIEWED_PROVIDERS, "unreviewed KernelSU provider")
    provider_repo = OFFICIAL_REPO if normalized == "official" else BAKA_REPO
    _require(lock.get("android_gki") == EXPECTED_GKI, "unsupported Android GKI identity")

    kernel = _pinned(lock.get("kernel"), "kernel", KERNEL_REPO)
    ksu = _pinned(lock.get("kernelsu"), "kernelsu", provider_repo)
    susfs = _pinned(lock.get("susfs"), "susfs", SUSFS_REPO)
    _require(ksu in REVIEWED_PROVIDERS[normalized], "provider Commit is not reviewed for this family")

    manifest = _read_catalog(catalog)
    _require(manifest.get("android_gki") == EXPECTED_GKI, "catalog GKI mismatch")
    _require(manifest.get("kernel_commit") == kernel, "kernel Commit differs from compatibility catalog")
    _require(manifest.get("susfs_commit") == susfs, "SUSFS Commit differs from compatibility catalog")
    commits = manifest.get("provider_commits")
    reviewed = REVIEWED_PROVIDERS["official"] | REVIEWED_PROVIDERS["bakasu"]
    _require(type(commits) is list and len(commits) == len(reviewed)
             and len(set(map(str, commits))) == len(commits)
             and set(commits) == reviewed, "catalog provider matrix has an unreviewed addition/removal")
    _require(ksu in commits, "provider Commit absent from compatibility catalog")

    filename, digest = manifest.get("file"), manifest.get("sha256")
    _require(isinstance(filename, str) and filename not in ("", ".", "..")
             and "/" not in filename and "\\" not in filename, "unsafe adapter filename")
    _require(isinstance(digest, str) and _SHA256.fullmatch(digest) is not None,
             "invalid adapter SHA256 in catalog")
    adapter = Path(catalog).parent / filename
    _require(adapter.is_file() and not adapter.is_symlink(), "missing or symlinked adapter file")
    _require(hashlib.sha256(adapter.read_bytes()).hexdigest() == digest,
             "reviewed adapter SHA256 differs from catalog")

    return {
        "schema_version": 1,
        "stage": "6.4",
        "status": "DECLARED_PINNED_TRIPLE_REVIEWED",
        "provider": normalized,
        "kernel_commit": kernel,
        "provider_commit": ksu,
        "susfs_commit": susfs,
        "adapter_sha256": digest,
        "adapter_bytes": "TESTED",
        "source_checkout_identity": "REQUIRES_INDEPENDENT_GIT_VERIFICATION",
        "upstream_patch_line_equivalence": "REQUIRES_INTEGRATION_CHECK",
        "object_compilation": "NOT_INFERRED",
        "full_vmlinux_image": "UNTESTED",
        "abi_kmi": "UNTESTED",
        "device_boot_root": "UNTESTED",
        "release_eligible": False,
        "archive_build_input_eligible": False,
    }


def require_release_eligible(result: dict) -> None:
    """Fail closed: this scoped source gate is never a flashable release proof."""
    raise CompatibilityGateError(
        "Stage 6.4 static compatibility preflight never authorizes a kernel release"
    )
