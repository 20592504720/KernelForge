"""Single-shot, branch-push-only Stage 1–6 full acceptance request preflight.

No network or extra dependencies. Must execute before tool installs/downloads.
The request commit must change *only* the allowed marker, with an exact parent
SHA named in that marker. This keeps the request specific to one code snapshot.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


MARKER = ".github/stage6-full-acceptance-request.json"
BRANCH = "refs/heads/stage1/initial-foundation"
MATRIX = [
    "official-susfs-off", "official-susfs-on",
    "bakasu-susfs-off", "bakasu-susfs-on",
    "bakasu-reviewed-new-susfs-on",
]
EXPECTED = {
    "schema_version": 1,
    "request_id": "stage1-6-full-acceptance-20261123",
    "scope": ["1", "2", "3", "4", "5", "6"],
    "pinned_gki_full_image": True,
    "gki_combinations": MATRIX,
    "sm8750_new_sync": False,
    "sm8750_evidence_replay": True,
    "oki_vendor_build": False,
    "device_release": False,
}


def _pairs_unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError("duplicate Stage 1–6 request JSON key")
        result[k] = v
    return result


def validate(payload: object, *, ref: str, changed: set[str], parent: str) -> None:
    if ref != BRANCH:
        raise ValueError("Stage 1–6 full acceptance restricted to development branch")
    if changed != {MARKER}:
        raise ValueError("full acceptance request commit may modify only the marker")
    if type(payload) is not dict:
        raise ValueError("invalid full acceptance request")
    if set(payload) != set(EXPECTED) | {"base_commit"}:
        raise ValueError("unknown/missing full acceptance request fields")
    for key, val in EXPECTED.items():
        if type(payload[key]) is not type(val) or payload[key] != val:
            raise ValueError("unapproved Stage 1–6 acceptance scope or settings")
    sha = payload.get("base_commit")
    if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
        raise ValueError("missing exact Stage 6.5 base Commit")
    if sha != parent:
        raise ValueError("full acceptance request is not based on the approved code snapshot")


def main() -> int:
    sha = os.environ.get("GITHUB_SHA", "")
    if re.fullmatch(r"[0-9a-fA-F]{40}", sha) is None:
        raise ValueError("invalid GITHUB_SHA")
    changed = subprocess.check_output(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
        text=True, timeout=20).splitlines()
    parent = subprocess.check_output(
        ["git", "rev-parse", f"{sha}^"], text=True, timeout=20).strip()
    payload = json.loads(Path(MARKER).read_text(encoding="utf-8"),
                         object_pairs_hook=_pairs_unique)
    validate(payload, ref=os.environ.get("GITHUB_REF", ""),
             changed=set(changed), parent=parent)
    print("STAGE1_6_FULL_ACCEPTANCE_REQUEST_ACCEPTED: " + sha)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print("STAGE1_6_FULL_ACCEPTANCE_REQUEST_REJECTED: " + str(exc),
              file=sys.stderr)
        raise SystemExit(2)
