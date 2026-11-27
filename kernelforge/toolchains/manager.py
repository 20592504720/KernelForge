"""Generic, profile-driven LLVM/GCC provisioning independent of build adapters."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import re
import shutil
import stat
import subprocess
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from ..filesystem import atomic_replace
from ..path_policy import require_external_paths
from ..security import redact_diagnostic
from ..toolchain import _version_tuple
from .archive import ArchiveError, extract
from .download import DownloadError, download
from .locking import FileLock, LockTimeout, _linked
from .release_mirror import ReleaseMirrorError, ReviewedGithubReleaseAdapter

LOG = logging.getLogger(__name__)
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
HOST_ALIASES = {"amd64": "x86_64", "x64": "x86_64", "arm64": "aarch64", "armv8": "aarch64", "i386": "x86", "i686": "x86", "armv7l": "armv7"}
MODES = {"AUTO", "LOCAL_ONLY", "DOWNLOAD_ONLY"}
SUPPORTED_HOSTS = {"x86_64", "aarch64", "x86", "armv7"}
SUPPORTED_TARGETS = {"aarch64", "arm64", "arm", "armv7", "armv7l", "x86_64", "x86", "i686", "riscv64", "riscv32", "loongarch64"}


class ToolchainManagerError(RuntimeError):
    def __init__(self, message: str, *, phase: str = "prepare", audit: dict | None = None):
        super().__init__(message)
        self.phase, self.audit = phase, audit or {}


def normalize_arch(value: str) -> str:
    name = value.strip().lower()
    return HOST_ALIASES.get(name, name)


def host_arch() -> str:
    return normalize_arch(platform.machine())


def _version_key(value: str) -> tuple[int, ...]:
    parsed = _version_tuple(value)
    if not parsed:
        raise ToolchainManagerError(f"invalid toolchain version: {value}", phase="requirements")
    return parsed


def _satisfies(version: str, spec: dict) -> None:
    current = _version_key(version)
    if spec.get("minimum_version") and spec.get("maximum_version") and _version_key(spec["minimum_version"]) > _version_key(spec["maximum_version"]):
        raise ToolchainManagerError("minimum_version exceeds maximum_version", phase="requirements")
    for field, compare in (("minimum_version", lambda a, b: a >= b), ("maximum_version", lambda a, b: a <= b)):
        constraint = spec.get(field)
        if constraint and not compare(current + (0,) * max(0, len(_version_key(constraint)) - len(current)), _version_key(constraint) + (0,) * max(0, len(current) - len(_version_key(constraint)))):
            raise ToolchainManagerError(f"toolchain version {version} violates {field}={constraint}", phase="version")
    fixed = spec.get("version")
    if fixed and current + (0,) * max(0, len(_version_key(fixed)) - len(current)) != _version_key(fixed) + (0,) * max(0, len(current) - len(_version_key(fixed))):
        raise ToolchainManagerError(f"toolchain version mismatch: required {fixed}, found {version}", phase="version")
    if fixed and ((spec.get("minimum_version") and current < _version_key(spec["minimum_version"])) or (spec.get("maximum_version") and current > _version_key(spec["maximum_version"]))):
        raise ToolchainManagerError("fixed version conflicts with the configured version range", phase="requirements")


def _safe_source(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if parsed.port:
        host += f":{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def _digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big")); digest.update(relative)
        digest.update(bytes.fromhex(_digest(path)))
    return digest.hexdigest()


def _trusted_tree_digest(root: Path) -> str:
    """Compare content, path types and executable bits to independently extracted bytes."""
    return _tree_proofs(root, include_legacy=False)[0]


def _tree_proofs(root: Path, *, include_legacy: bool) -> tuple[str, str | None]:
    """Compute the existing strict digest and optional legacy digest in one read pass.

    The two historical formats have different path ordering and record layouts.
    Keep both byte formats unchanged; never reuse these values across validation
    boundaries or after independently extracting the pinned archive.
    """
    def inspect(path):
        info = path.lstat()
        if (path.is_symlink() or getattr(info, "st_file_attributes", 0) &
                getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
            raise ValueError("link or reparse point in managed toolchain")
        return info

    if not stat.S_ISDIR(inspect(root).st_mode):
        raise ValueError("managed toolchain root is not a real directory")
    digest = hashlib.sha256()
    legacy = hashlib.sha256() if include_legacy else None
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        info = inspect(path)
        rel = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(rel).to_bytes(4, "big"))
        digest.update(rel)
        if stat.S_ISDIR(info.st_mode):
            digest.update(b"D")
        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            digest.update(b"F")
            digest.update(bytes([bool(info.st_mode & 0o111) if os.name != "nt" else 0]))
            file_digest = bytes.fromhex(_digest(path))
            digest.update(file_digest)
            if legacy is not None:
                legacy.update(len(rel).to_bytes(4, "big")); legacy.update(rel)
                legacy.update(file_digest)
        else:
            raise ValueError("nonregular or hardlinked file in managed toolchain")
    return digest.hexdigest(), legacy.hexdigest() if legacy is not None else None


def _binary_architecture(path: Path) -> str | None:
    try:
        with path.open("rb") as stream:
            header = stream.read(4096)
    except OSError:
        return None
    if header.startswith(b"\x7fELF") and len(header) >= 20:
        endian = "little" if header[5] == 1 else "big" if header[5] == 2 else None
        if not endian:
            return None
        machine = int.from_bytes(header[18:20], endian)
        return {3: "x86", 40: "armv7", 62: "x86_64", 183: "aarch64", 243: "riscv64", 258: "loongarch64"}.get(machine)
    if header.startswith(b"MZ") and len(header) >= 64:
        offset = int.from_bytes(header[60:64], "little")
        if offset + 6 <= len(header) and header[offset:offset + 4] == b"PE\0\0":
            machine = int.from_bytes(header[offset + 4:offset + 6], "little")
            return {0x14C: "x86", 0x8664: "x86_64", 0x1C4: "armv7", 0xAA64: "aarch64"}.get(machine)
    if len(header) >= 8:
        magic = int.from_bytes(header[:4], "big")
        if magic in {0xFEEDFACE, 0xFEEDFACF, 0xCEFAEDFE, 0xCFFAEDFE}:
            endian = "big" if magic in {0xFEEDFACE, 0xFEEDFACF} else "little"
            cpu = int.from_bytes(header[4:8], endian)
            return {7: "x86", 0x01000007: "x86_64", 12: "armv7", 0x0100000C: "aarch64"}.get(cpu)
    return None


class ArchiveSourceAdapter:
    """Declarative archive source. Custom adapters can override URL and format resolution."""

    requires_archive_format = True

    def resolve(self, spec: dict) -> tuple[str, str, str]:
        return spec["url"], spec["archive_format"], spec.get("layout_root", "")

    def download(self, manager, spec: dict, destination: Path) -> dict:
        url, _archive_format, _layout = self.resolve(spec)
        return manager.downloader(url, destination, timeout=spec.get("download_timeout_seconds", 60), retries=spec.get("retries", 2), expected_size=spec.get("expected_size"))

    def extract(self, manager, spec: dict, archive: Path, destination: Path) -> None:
        _url, archive_format, _layout = self.resolve(spec)
        manager.extractor(archive, destination, archive_format)


class ToolchainManager:
    """Resolve a managed toolchain and return an isolated environment overlay.

    A profile is data, not an adapter: ``kind`` is ``llvm`` or ``gcc`` and
    ``executables`` maps environment role names (for example ``CC``) to paths
    relative to ``layout_root``. Downloads always require an explicit SHA256.
    """

    METADATA_VERSION = 1

    def __init__(self, cache_dir: Path | str, *, mode: str = "AUTO", lock_timeout: float = 120,
                 downloader=download, extractor=extract, source_adapters: dict | None = None):
        self.cache_dir = Path(cache_dir).expanduser().absolute()
        if any(_linked(p) for p in (self.cache_dir, *self.cache_dir.parents)):
            raise ToolchainManagerError("linked cache path refused", phase="cache")
        # Resolve only AFTER checking the requested path for links. Windows
        # Path.resolve() also canonicalizes existing directory-name casing.
        self.cache_dir = self.cache_dir.resolve()
        self.mode = mode.upper()
        if self.mode not in MODES:
            raise ToolchainManagerError(f"unsupported toolchain mode: {mode}", phase="requirements")
        self.lock_timeout, self.downloader, self.extractor = lock_timeout, downloader, extractor
        archive_adapter = ArchiveSourceAdapter()
        reviewed_release = ReviewedGithubReleaseAdapter()
        self.source_adapters = {"archive": archive_adapter, "custom": archive_adapter,
                                "llvm-release": reviewed_release, "gcc-release": reviewed_release,
                                "reviewed-github-release": reviewed_release}
        self.source_adapters.update(source_adapters or {})

    def _key(self, spec: dict) -> str:
        identity = {key: spec.get(key) for key in ("kind", "name", "version", "minimum_version", "maximum_version", "host_arch", "target_arch", "source_type", "url", "sha256", "archive_format", "layout_root", "adapter_version", "executables", "version_executable", "version_args", "target_query_args", "cross_compile", "environment", "release_lock")}
        adapter = self.source_adapters.get(spec.get("source_type", "custom"))
        identity["source_adapter_version"] = getattr(adapter, "version", "1")
        payload = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(payload).hexdigest()

    def prepare(self, spec: object, *, lease: bool = False) -> dict:
        if not isinstance(spec, dict):
            raise ToolchainManagerError("toolchain profile must be an object", phase="requirements", audit={
                "failure_phase": "requirements", "failure_reason": "toolchain profile must be an object"
            })
        audit = {"kind": spec.get("kind"), "name": spec.get("name"), "host_arch": normalize_arch(spec.get("host_arch") or host_arch()),
                 "target_arch": spec.get("target_arch"), "source_type": spec.get("source_type", "custom"),
                 "source": _safe_source(spec.get("url")), "expected_sha256": spec.get("sha256"), "actual_sha256": None,
                 "sha256_verified": False, "verification_object": None, "verification_source": None,
                 "verified_at": None, "cache_used": False, "local_toolchain": False,
                 "download_seconds": None, "verification_seconds": None, "install_seconds": None,
                 "version": None, "version_check": "not-run", "install_path": None, "environment": {}, "failure_phase": None, "failure_reason": None}
        try:
            self._validate(spec, audit)
            # Bound future published/staging paths before cache hashing or any
            # source adapter/network work. Check members again on extraction.
            require_external_paths(self.cache_dir, reserve=100)
            self._check_cache_layout()
            key = self._key(spec)
            lock_path = self.cache_dir / "locks" / f"{key}.lock"
            with FileLock(lock_path, timeout=self.lock_timeout):
                local = spec.get("local_path") or spec.get("local_root")
                if local and self.mode != "DOWNLOAD_ONLY":
                    result = self._local(spec, Path(local), audit)
                    return result
                cached = self._cached(spec, key, audit)
                if cached:
                    return self._lease_result(cached, key) if lease else cached
                if self.mode == "LOCAL_ONLY":
                    raise ToolchainManagerError("LOCAL_ONLY mode: no valid local toolchain or verified cache is available", phase="resolve")
                result = self._download_install(spec, key, audit)
                return self._lease_result(result, key) if lease else result
        except (ToolchainManagerError, ReleaseMirrorError, DownloadError, ArchiveError, LockTimeout, OSError, ValueError, json.JSONDecodeError) as exc:
            phase = getattr(exc, "phase", "resolve")
            audit["failure_phase"], audit["failure_reason"] = phase, redact_diagnostic(str(exc))
            if isinstance(exc, ToolchainManagerError) and exc.audit:
                audit.update(exc.audit)
            if isinstance(exc, LockTimeout):
                phase = "lock"; audit["failure_phase"] = phase
            raise ToolchainManagerError(redact_diagnostic(str(exc)), phase=phase, audit=audit) from exc

    def _validate(self, spec: dict, audit: dict) -> None:
        if not isinstance(spec, dict):
            raise ToolchainManagerError("toolchain profile must be an object", phase="requirements")
        for field in ("kind", "name"):
            if not isinstance(spec.get(field), str) or not spec[field].strip():
                raise ToolchainManagerError(f"toolchain profile requires {field}", phase="requirements")
        if spec["kind"] not in {"llvm", "gcc"}:
            raise ToolchainManagerError(f"unsupported toolchain kind: {spec['kind']}", phase="requirements")
        if spec.get("source_type") and spec["source_type"] not in self.source_adapters and not (spec.get("local_path") or spec.get("local_root")):
            raise ToolchainManagerError(f"no source adapter registered for {spec['source_type']}", phase="requirements")
        source_adapter = self.source_adapters.get(spec.get("source_type", "custom"))
        validate_source = getattr(source_adapter, 'validate', None)
        if callable(validate_source):
            validate_source(spec)
        for field in ("version", "minimum_version", "maximum_version"):
            if spec.get(field):
                _version_key(spec[field])
        if spec.get("minimum_version") and spec.get("maximum_version") and _version_key(spec["minimum_version"]) > _version_key(spec["maximum_version"]):
            raise ToolchainManagerError("minimum_version exceeds maximum_version", phase="requirements")
        current_host = host_arch()
        expected_host = normalize_arch(spec.get("host_arch") or current_host)
        audit["host_arch"] = expected_host
        if expected_host != current_host:
            raise ToolchainManagerError(f"toolchain host architecture mismatch: profile requires {expected_host}, current host is {current_host}", phase="architecture")
        if expected_host not in SUPPORTED_HOSTS:
            raise ToolchainManagerError(f"unsupported toolchain host architecture: {expected_host}", phase="architecture")
        if not isinstance(spec.get("target_arch"), str) or not spec["target_arch"].strip():
            raise ToolchainManagerError("toolchain target_arch is required", phase="requirements")
        target = spec["target_arch"].strip().lower()
        if target not in SUPPORTED_TARGETS and not re.fullmatch(r"[a-z0-9_+.-]+-(?:linux|none|elf|w64|apple)[a-z0-9_.+-]*(?:-gnu[a-z0-9_.+-]*)?", target):
            raise ToolchainManagerError(f"unsupported toolchain target architecture: {target}", phase="architecture")
        if spec.get("version") and spec.get("minimum_version") and _version_key(spec["version"]) < _version_key(spec["minimum_version"]):
            raise ToolchainManagerError("fixed version is below minimum_version", phase="requirements")
        if spec.get("version") and spec.get("maximum_version") and _version_key(spec["version"]) > _version_key(spec["maximum_version"]):
            raise ToolchainManagerError("fixed version exceeds maximum_version", phase="requirements")
        if not spec.get("local_path") and not spec.get("local_root"):
            if not spec.get("source_type") or spec.get("source_type") not in self.source_adapters:
                raise ToolchainManagerError("download source_type is missing or unsupported", phase="requirements")
            if not spec.get("url"):
                raise ToolchainManagerError("download URL is required", phase="requirements")
            digest = spec.get("sha256")
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                raise ToolchainManagerError("trusted 64-character SHA256 is required for downloads", phase="requirements")
            adapter = self.source_adapters.get(spec.get("source_type", "custom"))
            if getattr(adapter, "requires_archive_format", True) and not spec.get("archive_format"):
                raise ToolchainManagerError("archive_format is required for downloads", phase="requirements")
        if self.mode == "DOWNLOAD_ONLY" and (not spec.get("url") or not spec.get("sha256")):
            raise ToolchainManagerError("DOWNLOAD_ONLY mode requires a configured URL and trusted SHA256", phase="requirements")
        if not isinstance(spec.get("executables"), dict) or not spec["executables"]:
            raise ToolchainManagerError("executables mapping is required", phase="requirements")
        for role, relative in spec["executables"].items():
            if not isinstance(role, str) or not isinstance(relative, str) or not relative:
                raise ToolchainManagerError("executables must map environment names to relative executable paths", phase="requirements")
            p = Path(relative)
            if p.is_absolute() or ".." in p.parts:
                raise ToolchainManagerError(f"executable path must stay inside the toolchain: {relative}", phase="requirements")
        layout_root = Path(spec.get("layout_root", ""))
        if layout_root.is_absolute() or ".." in layout_root.parts:
            raise ToolchainManagerError("layout_root must stay inside the extracted toolchain", phase="requirements")

    def _tool_paths(self, root: Path, spec: dict) -> dict[str, Path]:
        layout = root / spec.get("layout_root", "")
        if not layout.is_dir() or (layout.resolve() != root.resolve() and root.resolve() not in layout.resolve().parents):
            raise ToolchainManagerError(f"toolchain layout root not found: {layout}", phase="layout")
        result = {}
        for role, relative in spec["executables"].items():
            path = (layout / relative).resolve()
            require_external_paths(path)
            if layout.resolve() not in path.parents or not path.is_file():
                raise ToolchainManagerError(f"toolchain executable missing or outside layout: {relative}", phase="layout")
            if os.name != "nt" and not os.access(path, os.X_OK):
                raise ToolchainManagerError(f"toolchain executable is not executable: {path}", phase="layout")
            result[role] = path
        return result

    def _verify_tools(self, root: Path, spec: dict) -> tuple[dict, dict]:
        paths = self._tool_paths(root, spec)
        version_role = spec.get("version_executable", "CC")
        executable = paths.get(version_role) or next(iter(paths.values()))
        detected_host = _binary_architecture(executable)
        expected_host = normalize_arch(spec.get("host_arch") or host_arch())
        if detected_host and detected_host != expected_host:
            raise ToolchainManagerError(f"toolchain binary host architecture mismatch: expected {expected_host}, found {detected_host}", phase="architecture")
        args = spec.get("version_args", ["--version"])
        if isinstance(args, str):
            args = args.split()
        try:
            result = subprocess.run([str(executable), *args], capture_output=True, text=True, check=False, timeout=spec.get("version_timeout_seconds", 15))
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ToolchainManagerError(f"cannot query toolchain version using {executable}: {exc}", phase="version") from exc
        output = (result.stdout or result.stderr).strip()
        if result.returncode or not output:
            raise ToolchainManagerError(f"toolchain version query failed (exit {result.returncode}): {output[:240]}", phase="version")
        version = _version_tuple(output)
        if not version:
            raise ToolchainManagerError(f"cannot parse toolchain version from: {output.splitlines()[0]}", phase="version")
        version_text = ".".join(map(str, version))
        _satisfies(version_text, spec)
        target_args = spec.get("target_query_args")
        if target_args is None and spec["kind"] == "gcc":
            target_args = ["-dumpmachine"]
        detected_target = None
        if target_args:
            if isinstance(target_args, str):
                target_args = target_args.split()
            try:
                target_result = subprocess.run([str(executable), *target_args], capture_output=True, text=True, check=False, timeout=spec.get("version_timeout_seconds", 15))
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ToolchainManagerError(f"cannot query toolchain target architecture: {exc}", phase="architecture") from exc
            detected_target = (target_result.stdout or target_result.stderr).strip().splitlines()[0] if (target_result.stdout or target_result.stderr).strip() else None
            if target_result.returncode or not detected_target:
                raise ToolchainManagerError("toolchain target architecture query failed", phase="architecture")
            expected_target = spec["target_arch"].lower()
            normalized_detected = detected_target.lower()
            target_aliases = {
                "aarch64": ("aarch64", "arm64"), "arm64": ("aarch64", "arm64"),
                "arm": ("arm",), "armv7": ("arm",), "armv7l": ("arm",),
                "x86_64": ("x86_64", "amd64"), "x86": ("i386", "i486", "i586", "i686", "x86-"),
                "i686": ("i386", "i486", "i586", "i686", "x86-"),
                "riscv64": ("riscv64",), "riscv32": ("riscv32",), "loongarch64": ("loongarch64",),
            }
            aliases = target_aliases.get(expected_target, (expected_target,))
            target_matches = any(normalized_detected.startswith(alias) for alias in aliases)
            if expected_target in {"arm", "armv7", "armv7l"} and normalized_detected.startswith(("arm64", "aarch64")):
                target_matches = False
            if expected_target in {"x86", "i686"} and normalized_detected.startswith(("x86_64", "amd64")):
                target_matches = False
            if not target_matches:
                raise ToolchainManagerError(f"toolchain target mismatch: expected {expected_target}, compiler reports {detected_target}", phase="architecture")
        env = {}
        bin_dir = executable.parent
        for key, path in paths.items():
            env[key] = str(path)
        env["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        env["KERNELFORGE_TOOLCHAIN_ROOT"] = str(root)
        if spec["kind"] == "gcc":
            prefix = spec.get("cross_compile")
            if prefix is None:
                executable_name = Path(env.get("CC", str(executable))).name
                prefix = executable_name[:-3] if executable_name.endswith("gcc") else ""
            if prefix:
                env["CROSS_COMPILE"] = prefix if Path(prefix).is_absolute() else str(bin_dir / prefix)
        for name, value in spec.get("environment", {}).items():
            env[name] = str(value).replace("{root}", str(root)).replace("{bin}", str(bin_dir))
        return {"version": version_text, "version_output": output.splitlines()[0], "binary_host_arch": detected_host, "host_arch_check": "passed" if detected_host else "unknown-binary-format", "detected_target_arch": detected_target, "target_arch_check": "passed" if detected_target else "not-reported-by-tool", "executables": {k: str(v) for k, v in paths.items()}}, env

    def _local(self, spec: dict, root: Path, audit: dict) -> dict:
        root = root.expanduser().resolve()
        local_spec = dict(spec)
        if root.is_file():
            role = spec.get("version_executable", "CC")
            if role not in spec["executables"]:
                role = next(iter(spec["executables"]))
            executables = dict(spec["executables"])
            executables[role] = root.name
            local_spec["executables"] = executables
            local_spec["layout_root"] = ""
            root = root.parent
        if not root.is_dir():
            raise ToolchainManagerError(f"local toolchain path does not exist: {root}", phase="local")
        details, env = self._verify_tools(root, local_spec)
        audit.update({"install_path": str(root), "local_toolchain": True, "version": details["version"], "version_check": "passed", "binary_host_arch": details["binary_host_arch"], "host_arch_check": details["host_arch_check"], "detected_target_arch": details["detected_target_arch"], "target_arch_check": details["target_arch_check"], "trust_source": spec.get("trust_source", "user-configured-local-path"), "sha256_verified": False})
        compiler = env.get('CC') or next(iter(details['executables'].values()))
        if not isinstance(compiler, str) or not compiler:
            raise ToolchainManagerError('verified compiler path is missing', phase='local')
        audit["environment_summary"] = {"keys": sorted(env), "bin_directories": [str(Path(compiler).parent)]}
        return {"root": str(root), "version": details["version"], "executables": details["executables"], "environment": env, "audit": audit}

    def _lease_result(self, result: dict, key: str) -> dict:
        uses = self.cache_dir / "uses"
        uses.mkdir(parents=True, exist_ok=True)
        lease = uses / f"{key}.{os.getpid()}.{uuid.uuid4().hex}.use"
        lease.write_text(json.dumps({"pid": os.getpid(), "host": platform.node(), "created": time.time()}), encoding="utf-8")
        result["_lease"] = str(lease)
        return result

    @staticmethod
    def release(prepared: dict) -> None:
        lease = prepared.pop("_lease", None)
        if lease:
            Path(lease).unlink(missing_ok=True)

    def _metadata_paths(self, key: str):
        if not isinstance(key, str) or re.fullmatch(r"[0-9a-f]{64}", key) is None:
            raise ToolchainManagerError("invalid managed cache key", phase="cache")
        return self.cache_dir / "install" / key, self.cache_dir / "metadata" / f"{key}.json", self.cache_dir / "downloads" / f"{key}.archive"

    def _check_cache_layout(self):
        # No destructive operations or execution through linked cache directories.
        for path in (self.cache_dir, *(self.cache_dir / part for part in
                     ("install", "metadata", "downloads", "locks", "uses", "staging", "quarantine"))):
            if path.is_symlink() or (path.exists() and (
                    not path.is_dir() or getattr(path.lstat(), "st_file_attributes", 0) &
                    getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))):
                raise ToolchainManagerError("unsafe linked or non-directory cache layout", phase="cache")

    def _verify_cached_tree(self, spec, archive, install, expected_sha):
        # Metadata and installed files are in the same trust domain. Compare
        # against a fresh extraction of the independently pinned archive.
        stage_root = self.cache_dir / "staging"
        stage_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="proof-", dir=stage_root) as temporary:
            reference = Path(temporary) / "root"
            try:
                self.source_adapters[spec.get("source_type", "custom")].extract(
                    self, spec, archive, reference)
            except (ArchiveError, OSError) as exc:
                raise ToolchainManagerError("cache archive proof could not be completed",
                                            phase="cache-proof") from exc
            if _digest(archive) != expected_sha:
                raise ValueError("archive changed during independent cache proof")
            if _trusted_tree_digest(reference) != _trusted_tree_digest(install):
                raise ValueError("cached installed tree differs from pinned archive")


    def _cached(self, spec: dict, key: str, audit: dict) -> dict | None:
        install, metadata_path, archive = self._metadata_paths(key)
        self._recover_install(key, install)
        if not install.exists() and not metadata_path.exists():
            return None
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("schema_version") != self.METADATA_VERSION or metadata.get("key") != key:
                raise ValueError("cache metadata schema or key mismatch")
            if metadata.get("expected_sha256", "").lower() != spec["sha256"].lower():
                raise ValueError("cache metadata expected SHA256 does not match request")
            if (archive.is_symlink() or metadata_path.is_symlink() or install.is_symlink() or
                    not archive.is_file() or not install.is_dir()):
                raise ValueError("cache archive or installed toolchain is missing or linked")
            started = time.monotonic()
            # Strict traversal rejects links and nonregular entries while deriving
            # the unchanged legacy metadata digest from the same file bytes.
            _, installed_digest = _tree_proofs(install, include_legacy=True)
            actual = _digest(archive)
            duration = round(time.monotonic() - started, 3)
            if actual.lower() != spec["sha256"].lower() or metadata.get("actual_sha256", "").lower() != actual.lower():
                raise ValueError("cached archive SHA256 mismatch")
            if metadata.get("installed_tree_sha256") != installed_digest:
                raise ValueError("cached installed toolchain content mismatch")
            self._verify_cached_tree(spec, archive, install, actual)
            details, env = self._verify_tools(install, spec)
            if details["version"] != metadata.get("version"):
                raise ValueError("cached installed tool version does not match metadata")
        except (OSError, ValueError, KeyError, json.JSONDecodeError, ToolchainManagerError) as exc:
            if isinstance(exc, ToolchainManagerError) and exc.phase == "cache-proof":
                raise
            if self._has_live_use(key):
                raise ToolchainManagerError("invalid toolchain cache has an active lease; refusing mutation", phase="cache") from exc
            audit["cache_failure_reason"] = redact_diagnostic(str(exc))
            self._quarantine(key, install, metadata_path, archive)
            LOG.warning("Quarantined invalid toolchain cache %s: %s", key, redact_diagnostic(str(exc)))
            return None
        audit.update({"actual_sha256": actual, "sha256_verified": True, "verification_object": "cached-download-archive", "verification_source": "configured-sha256", "verified_at": metadata.get("verified_at"), "cache_used": True, "install_path": str(install), "version": details["version"], "version_check": "passed", "binary_host_arch": details["binary_host_arch"], "host_arch_check": details["host_arch_check"], "detected_target_arch": details["detected_target_arch"], "target_arch_check": details["target_arch_check"], "verification_seconds": duration, "trust_source": "verified-cache", "independent_archive_tree_verified": True})
        compiler = env.get('CC') or next(iter(details['executables'].values()))
        if not isinstance(compiler, str) or not compiler:
            raise ToolchainManagerError('verified compiler path is missing', phase='cache-proof')
        audit["environment_summary"] = {"keys": sorted(env), "bin_directories": [str(Path(compiler).parent)]}
        return {"root": str(install), "version": details["version"], "executables": details["executables"], "environment": env, "audit": audit}

    def _quarantine(self, key: str, *paths: Path) -> None:
        quarantine = self.cache_dir / "quarantine" / f"{key}-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        for index, path in enumerate(paths):
            if path.exists():
                quarantine.mkdir(parents=True, exist_ok=True)
                try:
                    atomic_replace(path, quarantine / f"{index}-{path.name}")
                except OSError as exc:
                    raise ToolchainManagerError("cache quarantine failed; original retained", phase="cache") from exc

    def _recover_install(self, key: str, install: Path) -> None:
        backups = (sorted((*install.parent.glob(f".{key}.old-*"),
                           *install.parent.glob(f".{key[:16]}.old-*")),
                          key=lambda path: path.stat().st_mtime, reverse=True)
                   if install.parent.exists() else [])
        if not install.exists() and backups:
            atomic_replace(backups.pop(0), install)
        for backup in backups:
            shutil.rmtree(backup, ignore_errors=True)

    def _download_install(self, spec: dict, key: str, audit: dict) -> dict:
        install, metadata_path, archive = self._metadata_paths(key)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # Keep transient paths short for Windows MAX_PATH; the cache lock and
        # published metadata still use the complete SHA256 identity.
        stage = self.cache_dir / "staging" / f"{key[:12]}-{uuid.uuid4().hex[:12]}"
        stage.mkdir(parents=True, exist_ok=False)
        staged_archive = stage / "download.archive"
        try:
            source_adapter = self.source_adapters[spec.get("source_type", "custom")]
            source_url, _archive_format, layout_root = source_adapter.resolve(spec)
            info = source_adapter.download(self, spec, staged_archive)
            audit["download_seconds"] = info.get("duration_seconds")
            source_url = info.get("source_url", source_url)
            if info.get("source_route"):
                audit["source_route"] = info["source_route"]
                audit["mirror_fallback"] = info["mirror_fallback"]
                audit["mirror_provenance"] = info.get("mirror_provenance")
                if info.get("mirror_failure_class"):
                    audit["mirror_failure_class"] = info["mirror_failure_class"]
                if info.get("fallback_source_commit"):
                    audit["fallback_source_commit"] = info["fallback_source_commit"]
            verify_start = time.monotonic()
            actual = _digest(staged_archive); verification_seconds = round(time.monotonic() - verify_start, 3)
            expected = spec["sha256"].lower()
            audit.update({"actual_sha256": actual, "verification_seconds": verification_seconds, "verification_object": "downloaded-archive", "verification_source": "configured-sha256", "verified_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")})
            if actual.lower() != expected:
                audit["sha256_verified"] = False
                raise ToolchainManagerError(f"SHA256 verification failed: expected {expected}, computed {actual}", phase="sha256", audit=audit)
            audit["sha256_verified"] = True
            extract_start = time.monotonic()
            extracted = stage / "root"
            source_adapter.extract(self, spec, staged_archive, extracted)
            # Use the actual physical path while it exists, before moving it.
            # Executable discovery resolves each path, so the relocation base
            # must match that canonical root (especially on Windows).
            if _linked(extracted):
                raise ToolchainManagerError("linked extracted toolchain root", phase="layout")
            extracted = extracted.resolve(strict=True)
            layout = extracted / layout_root
            if not layout.is_dir():
                raise ToolchainManagerError(f"configured layout_root does not exist in archive: {layout_root or '.'}", phase="layout")
            details, env = self._verify_tools(extracted, spec)
            installed_digest = _tree_digest(extracted)
            audit["version"] = details["version"]; audit["version_check"] = "passed"; audit["binary_host_arch"] = details["binary_host_arch"]; audit["host_arch_check"] = details["host_arch_check"]; audit["detected_target_arch"] = details["detected_target_arch"]; audit["target_arch_check"] = details["target_arch_check"]
            install.parent.mkdir(parents=True, exist_ok=True); metadata_path.parent.mkdir(parents=True, exist_ok=True); archive.parent.mkdir(parents=True, exist_ok=True)
            # Publish archive first; metadata and install are committed under the cache lock.
            atomic_replace(staged_archive, archive)
            backup = install.with_name(f".{key[:16]}.old-{uuid.uuid4().hex[:12]}")
            if install.exists():
                atomic_replace(install, backup)
            temp_meta = None
            try:
                atomic_replace(extracted, install)
                # Recompute published executable paths from the destination,
                # not case-sensitive string substitution of staging paths.
                final_paths = {role: str(path) for role, path in self._tool_paths(install, spec).items()}
                metadata = {"schema_version": self.METADATA_VERSION, "key": key, "kind": spec["kind"], "name": spec["name"], "version": details["version"],
                            "host_arch": audit["host_arch"], "target_arch": spec["target_arch"], "source_type": audit["source_type"], "source": _safe_source(source_url),
                            "expected_sha256": expected, "actual_sha256": actual, "verified_at": audit["verified_at"], "archive_format": _archive_format, "adapter_version": spec.get("adapter_version", "1"),
                            "installed_tree_sha256": installed_digest, "executables": final_paths, "installed_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
                            "source_route": audit.get("source_route"), "mirror_provenance": audit.get("mirror_provenance"),
                            "mirror_fallback": audit.get("mirror_fallback", False)}
                temp_meta = metadata_path.with_name(f".{key[:16]}.{uuid.uuid4().hex[:12]}.tmp")
                temp_meta.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                atomic_replace(temp_meta, metadata_path)
            except BaseException:
                if temp_meta is not None:
                    temp_meta.unlink(missing_ok=True)
                if install.exists():
                    shutil.rmtree(install, ignore_errors=True)
                if backup.exists():
                    atomic_replace(backup, install)
                raise
            if backup.exists():
                shutil.rmtree(backup, ignore_errors=True)
            audit.update({"install_path": str(install), "version": details["version"], "version_check": "passed", "install_seconds": round(time.monotonic() - extract_start, 3), "trust_source": "configured-sha256"})
            relocated_environment = self._relocate_environment(env, extracted, install)
            # Executable environment roles must not retain a staging path;
            # final_paths is verified against the published install directory.
            for role, value in final_paths.items():
                if role not in spec.get("environment", {}):
                    relocated_environment[role] = value
            audit["environment_summary"] = {"keys": sorted(relocated_environment), "bin_directories": [str(Path(final_paths.get("CC", next(iter(final_paths.values())))).parent)]}
            return {"root": str(install), "version": details["version"], "executables": final_paths, "environment": relocated_environment, "audit": audit}
        except BaseException:
            shutil.rmtree(stage, ignore_errors=True)
            raise
        finally:
            shutil.rmtree(stage, ignore_errors=True)

    @staticmethod
    def _relocate_environment(environment: dict, source: Path, target: Path) -> dict:
        pattern = re.compile(re.escape(str(source)), re.IGNORECASE if os.name == "nt" else 0)
        return {key: pattern.sub(lambda _match: str(target), value) if isinstance(value, str) else value
                for key, value in environment.items()}

    def _cache_rows(self) -> list[dict]:
        rows = []
        meta_root = self.cache_dir / "metadata"
        metadata_files = sorted(meta_root.glob("*.json")) if meta_root.exists() else []
        known_keys = set()
        for path in metadata_files:
            if path.is_symlink() or not path.is_file() or re.fullmatch(r"[0-9a-f]{64}", path.stem) is None:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                key = data["key"]
                if (not isinstance(key, str) or re.fullmatch(r"[0-9a-f]{64}", key) is None
                        or path.parent != meta_root or path.stem != key or path.is_symlink()):
                    continue  # malformed metadata cannot nominate a deletion target
                known_keys.add(key)
                install, _, archive = self._metadata_paths(key)
                valid = install.is_dir() and archive.is_file() and _digest(archive) == data.get("actual_sha256") == data.get("expected_sha256") and _tree_digest(install) == data.get("installed_tree_sha256")
                rows.append({"key": key, "kind": data.get("kind"), "name": data.get("name"), "version": data.get("version"), "host_arch": data.get("host_arch"), "target_arch": data.get("target_arch"), "source": data.get("source"), "install_path": str(install), "valid": valid, "size_bytes": _tree_size(install) + (archive.stat().st_size if archive.exists() else 0)})
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                key = path.stem
                if path.parent != meta_root or re.fullmatch(r"[0-9a-f]{64}", key) is None or path.is_symlink():
                    continue
                known_keys.add(key)
                install, _, archive = self._metadata_paths(key)
                rows.append({"key": key, "metadata": str(path), "install_path": str(install), "valid": False, "size_bytes": (path.stat().st_size if path.exists() else 0) + _tree_size(install) + (archive.stat().st_size if archive.exists() else 0)})
        install_root, download_root = self.cache_dir / "install", self.cache_dir / "downloads"
        orphan_keys = set()
        if install_root.exists():
            orphan_keys.update(path.name for path in install_root.iterdir() if path.is_dir() and path.name not in known_keys)
        if download_root.exists():
            orphan_keys.update(path.stem for path in download_root.glob("*.archive") if path.stem not in known_keys)
        for key in sorted(orphan_keys):
            if re.fullmatch(r"[0-9a-f]{64}", key) is None:
                continue
            install, _, archive = self._metadata_paths(key)
            rows.append({"key": key, "valid": False, "install_path": str(install), "size_bytes": _tree_size(install) + (archive.stat().st_size if archive.exists() else 0)})
        return rows

    def list_cache(self) -> list[dict]:
        self._check_cache_layout()
        with FileLock(self.cache_dir / "locks" / "maintenance.lock", timeout=self.lock_timeout):
            return self._cache_rows()

    def clean_cache(self, *, kind: str | None = None, name: str | None = None, version: str | None = None, damaged_only: bool = False) -> list[str]:
        removed = []
        self._check_cache_layout()
        with FileLock(self.cache_dir / "locks" / "maintenance.lock", timeout=self.lock_timeout):
            for row in self._cache_rows():
                if row.get("valid") and damaged_only:
                    continue
                if kind and row.get("kind") != kind or name and row.get("name") != name or version and row.get("version") != version:
                    continue
                key = row.get("key")
                if not key:
                    continue
                if self._has_live_use(key):
                    continue
                lock = FileLock(self.cache_dir / "locks" / f"{key}.lock", timeout=self.lock_timeout)
                with lock:
                    if self._has_live_use(key):
                        continue
                    paths = self._metadata_paths(key)
                    if any(path.is_symlink() or (path.exists() and getattr(path.lstat(), "st_file_attributes", 0) &
                                                 getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)) for path in paths):
                        continue
                    for path in paths:
                        if path.is_dir():
                            shutil.rmtree(path)
                        else:
                            path.unlink(missing_ok=True)
                    removed.append(key)
        return removed

    def _has_live_use(self, key: str) -> bool:
        # Unknown, malformed, foreign-host and abandoned leases all block
        # mutation until reconciled explicitly. Age alone is not authorization.
        root = self.cache_dir / "uses"
        if _linked(root):
            raise ToolchainManagerError("linked lease directory refused", phase="cache")
        return root.is_dir() and any(root.glob(f"{key}.*.use"))


def _tree_size(root: Path) -> int:
    if not root.is_dir():
        return 0
    total = 0
    for path in root.rglob("*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            continue
    return total
