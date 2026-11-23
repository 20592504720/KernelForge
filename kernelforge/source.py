"""Safe Git checkout with explicit ref resolution and failure cleanup."""
from __future__ import annotations

import re
import os
import shutil
import stat
import subprocess
from pathlib import Path
from urllib.parse import urlsplit
from .filesystem import retry_windows
from .security import redact_diagnostic


class SourceError(RuntimeError):
    pass


def remove_checkout(path: Path) -> None:
    """Remove a checkout owned by the caller, including Windows readonly Git objects."""
    def writable_retry(function, name, _error):
        os.chmod(name, stat.S_IWRITE | stat.S_IREAD)
        function(name)
    if path.exists():
        retry_windows(lambda: shutil.rmtree(path, onerror=writable_retry))


_FULL_SHA = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")


def validate_repository(repository: str) -> None:
    if not isinstance(repository, str) or not repository or any(ord(ch) < 32 for ch in repository):
        raise SourceError("source repository URL is empty or contains control characters")
    if repository.startswith(("https://", "http://", "ssh://", "git://", "file://")):
        parts = urlsplit(repository)
        if parts.scheme in {"http", "https", "ssh", "git"} and not parts.hostname:
            raise SourceError("source repository URL must include a host")
        if parts.scheme == "file" and not parts.path:
            raise SourceError("file repository URL must include a path")
        return
    # SCP-style SSH URL, e.g. git@host:owner/repo.git
    if re.fullmatch(r"[^@/:\s]+@[^/:\s]+:.+", repository):
        return
    raise SourceError("unsupported repository URL; use HTTPS, SSH, git, file URL, or SCP-style SSH")


def _run_git(args: list[str], cwd: Path | None = None, timeout: int = 300) -> str:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_CONFIG_")}
    try:
        # Git for Windows emits UTF-8 paths even when Python's locale is CP936.
        result = subprocess.run(["git", *args], cwd=cwd, env=env, text=True, encoding='utf-8',
                                capture_output=True, check=False, timeout=timeout)
    except FileNotFoundError as exc:
        raise SourceError("Git executable not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise SourceError(f"Git operation timed out after {timeout} seconds") from exc
    if result.returncode:
        # Do not echo remotes: they may embed credentials supplied by a caller.
        detail = redact_diagnostic(result.stderr).strip().splitlines()
        if args[0] == 'apply':
            detail = [line for line in detail if line.startswith('error:')] or detail
            raise SourceError(f"git apply failed (exit {result.returncode}): {'; '.join(detail)}")
        raise SourceError(f"git {args[0]} failed (exit {result.returncode}): {detail[-1] if detail else 'no diagnostic'}")
    return result.stdout.strip()


def _resolve_fetch_ref(repository: str, ref: str, timeout: int) -> str:
    if not ref or ref.startswith("-") or any(ord(ch) < 32 for ch in ref):
        raise SourceError("source ref must be a non-empty branch, tag, or full Commit SHA")
    if _FULL_SHA.fullmatch(ref):
        return ref
    # Disambiguate branch and tag explicitly; a raw `git fetch ref` can resolve unexpectedly.
    network_errors = []
    for candidate in (f"refs/heads/{ref}", f"refs/tags/{ref}", f"refs/tags/{ref}^{{}}"):
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_CONFIG_")}
        try:
            result = subprocess.run(["git", "ls-remote", repository, candidate], env=env, text=True, capture_output=True, check=False, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise SourceError(f"Git ref lookup timed out after {timeout} seconds") from exc
        if result.returncode == 0 and result.stdout.strip():
            return candidate
        if result.returncode:
            network_errors.extend(redact_diagnostic(result.stderr).strip().splitlines())
    if network_errors:
        raise SourceError(f"Git ref lookup failed: {network_errors[-1]}")
    raise SourceError(f"branch or tag not found: {ref}")


def checkout(repository: str, ref: str, destination: Path, *, timeout: int = 300) -> str:
    validate_repository(repository)
    if not isinstance(destination, Path):
        destination = Path(destination)
    destination = destination.absolute()
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    existed = destination.exists()
    if existed and (not destination.is_dir() or any(destination.iterdir())):
        raise SourceError(f"source destination exists and is not empty; refusing to overwrite: {destination}")
    fetch_ref = _resolve_fetch_ref(repository, ref, timeout)
    try:
        _run_git(["clone", "--config", "core.autocrlf=false", "--no-checkout", "--filter=blob:none", repository, str(destination)], timeout=timeout)
        _run_git(["fetch", "--depth=1", "origin", fetch_ref], cwd=destination, timeout=timeout)
        _run_git(["checkout", "--detach", "FETCH_HEAD"], cwd=destination, timeout=timeout)
        _run_git(["fsck", "--connectivity-only", "--no-dangling"], cwd=destination, timeout=timeout)
        commit = _run_git(["rev-parse", "--verify", "HEAD^{commit}"], cwd=destination, timeout=timeout)
        if not _FULL_SHA.fullmatch(commit):
            raise SourceError(f"resolved source revision is not a full Git SHA: {commit}")
        if _FULL_SHA.fullmatch(ref) and commit.lower() != ref.lower():
            raise SourceError("checked out Commit SHA does not match requested pinned SHA")
        _run_git(["cat-file", "-e", "HEAD^{tree}"], cwd=destination, timeout=timeout)
        return commit.lower()
    except BaseException:
        # Remove only a directory this call created. A caller-provided empty directory is retained.
        if not existed and destination.exists() and destination.parent == parent:
            remove_checkout(destination)
        raise
