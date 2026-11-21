"""Pinned Git source checkout without executing remote scripts."""
from __future__ import annotations

import subprocess
from pathlib import Path


class SourceError(RuntimeError):
    pass


def git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode:
        raise SourceError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def checkout(repository: str, ref: str, destination: Path) -> str:
    if not repository or not ref:
        raise SourceError("source repository and ref are required")
    if destination.exists() and any(destination.iterdir()):
        raise SourceError(f"source destination is not empty: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    git("clone", "--no-checkout", "--filter=blob:none", repository, str(destination))
    git("fetch", "--depth=1", "origin", ref, cwd=destination)
    git("checkout", "--detach", "FETCH_HEAD", cwd=destination)
    commit = git("rev-parse", "HEAD", cwd=destination)
    if len(commit) != 40:
        raise SourceError(f"resolved source revision is not a full Git SHA: {commit}")
    return commit
