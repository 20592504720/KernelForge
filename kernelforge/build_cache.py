"""Stage 7.3 opt-in, isolated compiler-output (ccache) namespace policy.

Not the ToolchainManager archive cache. This module never downloads, builds,
executes ccache, or treats a hit as verification. Unknown/mutable identity
fields are rejected, not silently folded into a shared cache namespace.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import time
import uuid
from pathlib import Path
from typing import Self
from urllib.parse import urlsplit

from .toolchains.locking import FileLock, LockTimeout, _linked

__all__ = ['BuildCacheError', 'BuildCacheNamespaces', 'CacheLease', 'LockTimeout',
           'cache_key', 'canonical_digest', 'digest_file', 'verify_identity']

_SHA = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
_ROOT_MARK = ".kernelforge-ccache-root.json"
_META = ".kernelforge-ccache-identity.json"
_INVALID = ".kernelforge-cache-invalid.json"
_ROOT_ID = "KernelForge-managed-ccache-only-v1"
_ID_FIELDS = frozenset({
    "schema_version", "device", "kernel_version", "build_mode", "target_arch",
    "source_repository", "source_commit", "manifest_lock_sha256",
    "compiler_sha256", "compiler_version",
    "root_provider", "root_commit", "susfs_enabled", "susfs_commit",
    "patch_lock_sha256", "config_sha256", "build_arguments_sha256",
    "effective_environment_sha256",
})
_DIGEST_FIELDS = (
    "manifest_lock_sha256", "compiler_sha256", "patch_lock_sha256",
    "config_sha256", "build_arguments_sha256",
    "effective_environment_sha256",
)


class BuildCacheError(ValueError):
    """Fail closed on cache admission, corruption, or unsafe path."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise BuildCacheError(reason)


def canonical_digest(obj: object) -> str:
    """Stable input digest, never an authenticity claim."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=True,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _name(value: object) -> bool:
    return isinstance(value, str) and _NAME.fullmatch(value) is not None


def verify_identity(identity: dict) -> dict:
    """Verify the *shape* of a build input already established independently.

    Every material compiler/source/config/patch identity is required; this
    does not independently inspect a Git checkout, binary or .config.
    """
    _require(type(identity) is dict and set(identity) == _ID_FIELDS,
             "incomplete or unknown build cache identity fields")
    _require(type(identity["schema_version"]) is int and identity["schema_version"] == 1,
             "unsupported build cache identity schema")
    for field in ("device", "kernel_version", "target_arch", "compiler_version"):
        _require(_name(identity[field]), f"invalid build cache identity {field}")
    _require(identity["build_mode"] in ("gki", "vendor"), "unreviewed build cache mode")
    repo = identity["source_repository"]
    try:
        parsed_repo = urlsplit(repo)
        safe_repo = (parsed_repo.scheme == "https" and bool(parsed_repo.hostname)
                     and not parsed_repo.username and not parsed_repo.password
                     and parsed_repo.port in (None, 443) and not parsed_repo.query
                     and not parsed_repo.fragment and bool(parsed_repo.path)
                     and not any(c in repo for c in ("\r", "\n", "\t", "\\")))
    except (ValueError, TypeError):
        safe_repo = False
    _require(safe_repo, "source repository identity must use credential-free HTTPS")
    _require(isinstance(identity["source_commit"], str)
             and _COMMIT.fullmatch(identity["source_commit"]) is not None,
             "source Commit must be immutable full lowercase SHA")
    for field in _DIGEST_FIELDS:
        _require(isinstance(identity[field], str)
                 and _SHA.fullmatch(identity[field]) is not None,
                 f"missing exact SHA256 for build cache {field}")
    provider = identity["root_provider"]
    _require(provider in ("none", "official", "bakasu", "derived"),
             "unknown Root provider for build cache")
    rcommit = identity["root_commit"]
    _require(rcommit is None if provider == "none"
             else isinstance(rcommit, str) and _COMMIT.fullmatch(rcommit) is not None,
             "Root provider requires its own exact Git Commit")
    _require(type(identity["susfs_enabled"]) is bool, "SUSFS activation must be boolean")
    scommit = identity["susfs_commit"]
    _require(scommit is None if not identity["susfs_enabled"]
             else isinstance(scommit, str) and _COMMIT.fullmatch(scommit) is not None,
             "enabled SUSFS requires its own immutable Commit")
    _require(not identity["susfs_enabled"] or provider != "none",
             "SUSFS cannot be enabled without a reviewed Root provider")
    return identity


def cache_key(identity: dict) -> str:
    verify_identity(identity)
    return hashlib.sha256(b"KernelForge-ccache-identity-v1\x00"
                          + json.dumps(identity, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=True, allow_nan=False).encode("utf-8")).hexdigest()


def digest_file(path: Path) -> str:
    """Read-only hash for the actual compiler/config file, not its filename."""
    path = Path(path)
    _require(path.is_file(), "required build input file is absent")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def _no_symlink_ancestors(path: Path) -> None:
    for candidate in (path, *path.parents):
        _require(not _linked(candidate), f"cache path has a symlink/reparse component: {candidate}")


def _strict_json(path: Path) -> dict:
    _require(path.is_file() and not path.is_symlink(), f"cache identity file missing or unsafe: {path}")
    try:
        def unique(pairs):
            obj = {}
            for key, value in pairs:
                _require(key not in obj, "duplicate cache identity JSON key")
                obj[key] = value
            return obj
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise BuildCacheError(f"corrupt cache identity metadata: {path}") from exc
    _require(type(value) is dict, "cache metadata must be an object")
    return value


class CacheLease:
    """Owns one active-use marker; no data deletion when the lease is released."""
    def __init__(self, controller: BuildCacheNamespaces, key: str, marker: Path):
        self.controller, self.key, self.marker = controller, key, marker
        self.closed = False

    @property
    def path(self) -> Path:
        return self.controller.namespace_path(self.key)

    def environment(self) -> dict[str, str]:
        _require(not self.closed, "closed cache lease cannot be reused")
        return {
            "CCACHE_DIR": str(self.path),
            "CCACHE_MAXSIZE": f"{self.controller.max_size_mib}M",
            "CCACHE_COMPILERCHECK": "content",
        }

    def invalidate(self, reason: str = "BUILD_INPUTS_CHANGED_OR_FAILED") -> None:
        """Quarantine a namespace after failed compilation or config mutation.

        No cache files are deleted. Future opens fail until deliberate,
        lease-aware explicit prune. This does NOT retroactively prove any hit.
        """
        _require(reason in ("BUILD_INPUTS_CHANGED_OR_FAILED", "CONFIG_CHANGED_DURING_BUILD"),
                 "unsupported namespace invalidation reason")
        _no_symlink_ancestors(self.controller.root / "locks" / f"{self.key}.lock")
        with FileLock(self.controller.root / "locks" / f"{self.key}.lock",
                      timeout=self.controller.timeout):
            _no_symlink_ancestors(self.path)
            target = self.path / _INVALID
            _require(self.path.is_dir() and not self.path.is_symlink(),
                     "cannot invalidate missing/unsafe namespace")
            _require(not _linked(target), "unsafe cache invalidation marker")
            if target.exists():
                _require(_strict_json(target).get("key") == self.key,
                         "unexpected existing invalidation marker")
                return
            with target.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps({"key": self.key, "reason": reason}) + "\n")

    def close(self) -> None:
        if self.closed:
            return
        self.marker.unlink(missing_ok=True)
        self.closed = True

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc):
        self.close()


class BuildCacheNamespaces:
    """Fail-closed namespace provisioning and manual, lease-aware pruning.

    max_size_mib is a ccache per-namespace eviction target, NOT a physical
    disk quota. No automatic deleting of existing unknown/user directories.
    """
    def __init__(self, root: Path, *, max_size_mib: int = 2048,
                 forbidden_roots: tuple[Path, ...] = (), timeout: float = 30):
        _require(type(max_size_mib) is int and 64 <= max_size_mib <= 8192,
                 "ccache max_size_mib must be 64..8192")
        _require(type(timeout) in (int, float) and 0 < timeout <= 300,
             "ccache lock timeout must be 0..300 seconds")
        requested_root = Path(root).expanduser().absolute()
        _no_symlink_ancestors(requested_root)
        self.root = requested_root.resolve(strict=False)
        self.max_size_mib = max_size_mib
        self.timeout = timeout
        _no_symlink_ancestors(self.root)
        for forbidden in forbidden_roots:
            f = Path(forbidden).expanduser().resolve(strict=False)
            if self.root == f or f in self.root.parents or self.root in f.parents:
                raise BuildCacheError("ccache root overlaps protected source/toolchain directory")

    def namespace_path(self, key: str) -> Path:
        _require(isinstance(key, str) and _SHA.fullmatch(key) is not None,
                 "invalid compiler cache namespace key")
        return self.root / "namespaces" / key[:2] / key

    def _ensure_root(self):
        _no_symlink_ancestors(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        mark = self.root / _ROOT_MARK
        if mark.exists() or mark.is_symlink():
            _require(_strict_json(mark) == {"owner": _ROOT_ID, "schema_version": 1},
                     "unknown existing compiler cache root; do not modify")
            return
        # Safe for two first-use processes: an atomic lock is held around
        # this function in open(), and only the lock directory can preexist.
        allowed = {"locks"}
        _require(all(p.name in allowed and p.is_dir() and not p.is_symlink()
                     for p in self.root.iterdir()),
                 "unowned nonempty cache root; refusing to take ownership")
        mark.write_text(json.dumps({"owner": _ROOT_ID, "schema_version": 1}) + "\n",
                        encoding="utf-8")

    def open(self, identity: dict) -> CacheLease:
        key = cache_key(identity)
        _no_symlink_ancestors(self.root)
        # Initial lock is inside the caller-selected root; no WSL source or
        # toolchain path is touched. The ownership marker must be validated.
        _no_symlink_ancestors(self.root / "locks" / "root.lock")
        with FileLock(self.root / "locks" / "root.lock", timeout=self.timeout):
            self._ensure_root()
        _no_symlink_ancestors(self.root / "locks" / f"{key}.lock")
        with FileLock(self.root / "locks" / f"{key}.lock", timeout=self.timeout):
            dest = self.namespace_path(key)
            _no_symlink_ancestors(dest)
            metadata = dest / _META
            if dest.exists():
                _require(dest.is_dir() and not dest.is_symlink(),
                         "existing cache namespace is not a real directory")
                expected = {"schema_version": 1, "key": key, "identity": identity}
                _require(_strict_json(metadata) == expected,
                         "existing cache namespace identity mismatch; refusing reuse")
                _require(not (dest / _INVALID).exists() and not (dest / _INVALID).is_symlink(),
                         "invalidated cache namespace requires explicit safe prune")
            else:
                dest.mkdir(parents=True, exist_ok=False)
                try:
                    metadata.write_text(json.dumps({
                        "schema_version": 1, "key": key, "identity": identity
                    }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
                except BaseException:
                    metadata.unlink(missing_ok=True)
                    dest.rmdir()
                    raise
            use = self.root / "uses"
            _no_symlink_ancestors(use)
            use.mkdir(parents=True, exist_ok=True)
            token = use / f"{key}.{uuid.uuid4().hex}.use"
            with token.open("x", encoding="utf-8") as f:
                json.dump({"key": key, "pid": os.getpid(), "host": socket.gethostname(),
                           "created_at_epoch": time.time()}, f)
                f.write("\n")
        return CacheLease(self, key, token)

    def inspect(self, key: str) -> dict:
        """No cache scan or ccache launch; only validated metadata + lease names."""
        dest = self.namespace_path(key)
        _no_symlink_ancestors(dest)
        path = dest / _META
        data = _strict_json(path)
        identity = data.get('identity')
        if not isinstance(identity, dict):
            raise BuildCacheError('cache namespace identity must be an object')
        _require(data.get("key") == key and cache_key(identity) == key,
                 "cache namespace metadata digest mismatch")
        use = self.root / "uses"
        _no_symlink_ancestors(use)
        return {
            "key": key, "path": str(dest),
            "metadata_verified": True,
            "active_or_unreconciled_leases": len(list(use.glob(f"{key}.*.use"))) if use.is_dir() else 0,
            "hit_rate": "UNTESTED",
            "compiler_cache_used": "UNTESTED",
            "physical_disk_quota": "NOT_ENFORCED",
            "max_size_mib_ccache_target": self.max_size_mib,
        }

    def prune(self, key: str, *, dry_run: bool = True) -> dict:
        """Explicit deletion only; blocks even stale use markers, no auto-recovery."""
        _require(type(dry_run) is bool, "cache prune dry_run must be boolean")
        self.namespace_path(key)  # validate before forming any lock path
        _no_symlink_ancestors(self.root)
        _no_symlink_ancestors(self.root / "locks" / f"{key}.lock")
        _require(_strict_json(self.root / _ROOT_MARK) ==
                 {"owner": _ROOT_ID, "schema_version": 1},
                 "refusing to prune a cache root not owned by KernelForge")
        with FileLock(self.root / "locks" / f"{key}.lock", timeout=self.timeout):
            dest = self.namespace_path(key)
            _no_symlink_ancestors(dest)
            status = self.inspect(key)
            _require(status["active_or_unreconciled_leases"] == 0,
                     "active or stale cache lease blocks cleanup")
            _require(not dest.is_symlink(), "symlinked cache namespace cannot be pruned")
            for entry in dest.rglob("*"):
                _require(not _linked(entry), "symlink/reparse point in cache namespace blocks cleanup")
            if not dry_run:
                shutil.rmtree(dest)
            return {"key": key, "dry_run": dry_run,
                    "removed": not dry_run, "target": str(dest)}
