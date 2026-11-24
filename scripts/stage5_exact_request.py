"""Zero-dependency preflight for one exact Stage 5 BakaSU/SUSFS GKI CI request."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

MARKER = ".github/stage5-exact-gki-request.json"
REF = "refs/heads/stage1/initial-foundation"
EXPECTED = {
    "schema_version": 1,
    "request_id": "stage5-bakasu-susfs-gki-20261123",
    "provider": "bakasu",
    "provider_commit": "2734e0bc155759955880f5fb99be640fc5b92156",
    "kernel_commit": "498f91c17b0822a09aede17d26a63bf8c6813725",
    "susfs_commit": "756abbf2d81557e36664fc67dffaee26d3dfc57c",
    "full_kernel": False,
}

def validate_request(payload: object, ref: str, changed: set[str]) -> None:
    if ref != REF:
        raise ValueError("unexpected branch for exact GKI request")
    if MARKER not in changed:
        raise ValueError("marker must change in the current HEAD commit")
    if type(payload) is not dict or payload != EXPECTED:
        raise ValueError("request must match the reviewed version triple and no-full-Image policy")

def reject_duplicate_fields(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate request key")
        value[key] = item
    return value

def main() -> int:
    sha = os.environ.get("GITHUB_SHA", "")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
        raise ValueError("GITHUB_SHA must be an exact commit")
    output = subprocess.run(["git", "show", "--format=", "--name-only", sha],
                            capture_output=True, text=True, encoding="utf-8",
                            timeout=15, check=True)
    payload = json.loads(Path(MARKER).read_text(encoding="utf-8"),
                         object_pairs_hook=reject_duplicate_fields)
    validate_request(payload, os.environ.get("GITHUB_REF", ""),
                     set(output.stdout.splitlines()))
    print("STAGE5_EXACT_REQUEST_ACCEPTED: " + EXPECTED["provider_commit"])
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print("STAGE5_EXACT_REQUEST_REJECTED: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
