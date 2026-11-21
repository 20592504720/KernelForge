"""GKI and Vendor build plans, execution, logging, and stable reports."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from . import __version__
from .source import checkout
from .patch_manager import apply_series
from .toolchain import check_tools
from .toolchains import ToolchainManager, ToolchainManagerError
from .kernelsu import integrate, IntegrationError
from . import development
from .workspace import Workspace

LOG = logging.getLogger(__name__)
SENSITIVE = re.compile(r"(token|secret|password|passwd|api[_-]?key)", re.I)


class BuildError(RuntimeError):
    pass


class BuildPlan(Protocol):
    argv: list[str]
    cwd: Path
    environment: dict[str, str]
    targets: list[str]
    artifact_patterns: list[str]


class Plan:
    def __init__(self, argv, cwd, environment, targets, artifact_patterns, required_tools):
        self.argv, self.cwd, self.environment = argv, cwd, environment
        self.targets, self.artifact_patterns = targets, artifact_patterns
        self.required_tools = required_tools


def _expand(argv: list[str], context: dict[str, str]) -> list[str]:
    expanded = []
    for arg in argv:
        try:
            expanded.append(arg.format_map(context))
        except KeyError as exc:
            raise BuildError(f"unknown build command placeholder: {exc.args[0]}") from exc
    if not expanded or not expanded[0]:
        raise BuildError("build command argv must not be empty")
    return expanded


def _plan(source: Path, output: Path, config: dict, adapter_key: str) -> Plan:
    spec = config["build"][adapter_key]
    build_dir = (source / spec.get("directory", ".")).resolve()
    if build_dir != source.resolve() and source.resolve() not in build_dir.parents:
        raise BuildError(f"configured build directory escapes source tree: {spec.get('directory')}")
    if not build_dir.is_dir():
        raise BuildError(f"configured build directory does not exist: {build_dir}")
    context = {"source": str(source.resolve()), "out": str(output.resolve()), "build_dir": str(build_dir), "jobs": str(config["build"]["jobs"]), "defconfig": config.get("defconfig", "")}
    return Plan(_expand(spec["argv"], context), build_dir, spec.get("environment", {}), spec.get("targets", []), spec.get("artifacts", config["artifacts"]["paths"]), spec.get("required_tools", []))


class GkiAdapter:
    """GKI plan includes explicit Kleaf/build.sh system, targets and outputs."""
    def plan(self, source: Path, output: Path, config: dict) -> Plan:
        system = config["build"]["gki"]["system"]
        if system not in {"kleaf", "build-sh"}:
            raise BuildError(f"unsupported GKI system: {system}")
        return _plan(source, output, config, "gki")


class VendorAdapter:
    """Vendor plan owns its own working directory, environment, target and outputs."""
    def plan(self, source: Path, output: Path, config: dict) -> Plan:
        return _plan(source, output, config, "vendor")


ADAPTERS = {"gki": GkiAdapter(), "vendor": VendorAdapter()}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_argv(argv: list[str]) -> list[str]:
    safe, redact_next = [], False
    for arg in argv:
        if redact_next:
            safe.append("[REDACTED]"); redact_next = False; continue
        if SENSITIVE.search(arg):
            if "=" in arg:
                safe.append(arg.split("=", 1)[0] + "=[REDACTED]")
            else:
                safe.append(arg); redact_next = True
        else:
            safe.append(arg)
    return safe


def _safe_environment(config_env: dict[str, str], overlay: dict[str, str] | None = None) -> dict[str, str]:
    inherited = {k: v for k, v in os.environ.items() if not SENSITIVE.search(k)}
    home=Workspace.configured()
    if home:
        inherited.update(home.temporary_environment())
    for key, value in config_env.items():
        if SENSITIVE.search(key):
            raise BuildError(f"refusing secret-like environment key in build profile: {key}")
        inherited[key] = str(value)
    for key, value in (overlay or {}).items():
        if SENSITIVE.search(key):
            raise BuildError(f"refusing secret-like environment key in managed toolchain profile: {key}")
        inherited[key] = str(value)
    return inherited


def _artifacts(source: Path, output: Path, patterns: list[str]) -> list[dict]:
    found: dict[Path, Path] = {}
    for pattern in patterns:
        for path in source.glob(pattern):
            resolved = path.resolve()
            if source.resolve() not in resolved.parents or not resolved.is_file():
                continue
            found[resolved] = path
    manifest = []
    for index, (resolved, path) in enumerate(sorted(found.items(), key=lambda pair: str(pair[0]))):
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
        target_name = path.name if index == 0 else f"{index}-{path.name}"
        target = output / target_name
        target.write_bytes(resolved.read_bytes())
        copied_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if copied_hash != digest:
            raise BuildError(f"artifact copy SHA256 verification failed: {path}")
        manifest.append({"source": str(path.relative_to(source)), "file": target.name, "size": target.stat().st_size, "sha256": digest})
    return manifest


def _write_report(output: Path, report: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    temp = output / ".build-report.json.tmp"
    temp.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(output / "build-report.json")


def _run_build(config: dict, workspace: Path, output_dir: Path) -> dict:
    output_dir = output_dir.resolve()
    workspace = workspace.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    started_at, monotonic_start = _utc_now(), time.monotonic()
    mode = config.get("build", {}).get("mode", "unknown")
    report = {
        "report_version": 1, "kernelforge_version": __version__,
        "device": config.get("device", {}).get("id"), "kernel_version": config.get("kernel_version"),
        "build_type": mode, "source": {"repository": config.get("source", {}).get("repository"), "requested_ref": config.get("source", {}).get("ref"), "commit_sha": None},
        "toolchain": {}, "build": {"argv": [], "targets": [], "environment_keys": [], "started_at": started_at, "ended_at": None, "duration_seconds": None, "exit_status": None, "timed_out": False},
        "artifacts": [], "log_file": "build.log", "error": None,
        "kernelsu": {"status": "SKIP", "provider": None},
    }
    log_path = output_dir / "build.log"
    managed_prepared = None
    manager = None
    versions = None
    try:
        if mode not in ADAPTERS:
            raise BuildError(f"unsupported build mode: {mode}")
        if config.get('device_profile'):
            from .source_provider import load_profile
            profile = load_profile(Path(__file__).resolve().parents[1], config['device_profile'])
            expected_repo = ('https://github.com/OnePlusOSS/android_kernel_common_oneplus_sm8750'
                             if profile['source_kind'] == 'oneplus-oss' else
                             'https://github.com/Ace6-Development/android_kernel_oneplus_sm8750')
            if config['source']['repository'].removesuffix('.git') != expected_repo:
                raise BuildError('device profile and kernel source belong to different providers')
            requested = {entry['id'] for entry in config.get('patch_series', [])}
            if requested - set(profile['patch_allowlist']):
                raise BuildError(f'profile has not approved patches: {sorted(requested - set(profile["patch_allowlist"]))}')
            report['device_profile'] = {'id': profile['id'], 'verification': profile['verification'],
                                        'flashable': False, 'reason': 'device boot and ABI unverified'}
        legacy_requirements = config["toolchain"].get("required", [])
        report["toolchain"] = check_tools(legacy_requirements) if legacy_requirements else {}
        development_mode = 'version_policy' in config.get('kernelsu', {}) or config.get('susfs', {}).get('enabled', False)
        if development_mode:
            versions = development.prepare(config, workspace, output_dir)
            report['version_lock'] = versions
        patch_entries, patch_root = config.get('patch_series', []), Path(__file__).resolve().parents[1] / 'patches'
        if patch_entries:
            from .patch_manager import lock_series
            patch_entries, patch_root, report['patch_lock'] = lock_series(patch_entries, patch_root, workspace, output_dir)
        source_dir = workspace / "source"
        source_sha = checkout(config["source"]["repository"], config["source"]["ref"], source_dir, timeout=config["source"].get("timeout_seconds", 300))
        report["source"]["commit_sha"] = source_sha
        if patch_entries:
            try:
                from .patch_manager import verify_lock
                verify_lock(patch_entries, patch_root, report['patch_lock'])
                report["patch_series"] = apply_series(
                    source_dir, patch_entries, patch_root,
                    kernel_commit=source_sha,
                    target={'kernel_version': config.get('kernel_version'),
                            'android_gki': config.get('susfs', {}).get('android_gki'),
                            'architecture': 'arm64' if config.get('device_profile') else None,
                            'build_mode': mode},
                )
            except (ValueError, RuntimeError, OSError) as exc:
                report["patch_series"] = {"state": "FAILED", "error": str(exc)}
                raise BuildError(str(exc)) from exc
        try:
            if versions is not None:
                report['kernelsu'], report['susfs'] = development.integrate_locked(config, versions, source_dir, output_dir, mode=mode, integrator=integrate)
            else:
                report["kernelsu"] = integrate(config.get("kernelsu", {"enabled": False}), source_dir, output_dir, mode=mode)
        except IntegrationError as exc:
            report["kernelsu"] = exc.report
            raise BuildError(f"KernelSU integration failed: {exc}") from exc
        plan = ADAPTERS[mode].plan(source_dir, output_dir, config)
        if plan.required_tools:
            report["toolchain"].update(check_tools(plan.required_tools))
        managed_environment = {}
        profile = config["build"][mode].get("toolchain_profile")
        if profile:
            manager_config = config["toolchain"]
            defaults_path = Path(__file__).resolve().parents[1] / "configs" / "toolchains" / "defaults.json"
            try:
                defaults = json.loads(defaults_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise BuildError(f"cannot read toolchain defaults at {defaults_path}: {exc}") from exc
            cache_settings = defaults.get("cache", {})
            download_settings = defaults.get("download", {})
            cache_dir = Path(profile.get("cache_dir", manager_config.get("cache_dir", cache_settings.get("directory", ".cache/toolchains"))))
            home = Workspace.configured()
            if home and 'cache_dir' not in profile and 'cache_dir' not in manager_config:
                cache_dir = home.path('cache', 'toolchains')
            if not cache_dir.is_absolute():
                cache_dir = workspace / cache_dir
            toolchain_mode = manager_config.get("mode", defaults.get("mode", "AUTO"))
            if not download_settings.get("enabled", True) and toolchain_mode == "AUTO":
                toolchain_mode = "LOCAL_ONLY"
            manager = ToolchainManager(cache_dir, mode=toolchain_mode, lock_timeout=manager_config.get("lock_timeout_seconds", cache_settings.get("lock_timeout_seconds", 120)))
            try:
                prepared = manager.prepare(profile, lease=True)
                managed_prepared = prepared
            except ToolchainManagerError as exc:
                report["toolchain"]["managed"] = exc.audit
                raise BuildError(f"toolchain preparation failed during {exc.phase}: {exc}") from exc
            managed_environment = prepared["environment"]
            report["toolchain"]["managed"] = prepared["audit"]
        report["build"]["argv"] = _safe_argv(plan.argv)
        report["build"]["targets"] = plan.targets
        report["build"]["environment_keys"] = sorted(plan.environment)
        timeout = config["build"].get("timeout_seconds", 3600)
        safe_env = _safe_environment(plan.environment, managed_environment)
        if versions is not None:
            kernel = source_dir / config.get('kernelsu', {}).get('kernel_directory', '.')
            validation = dict(config['validation']) if config.get('validation') else None
            if validation and config.get('susfs', {}).get('enabled'):
                validation['required_configs'] = list(set(validation.get('required_configs', [])) | {'KSU_SUSFS'})
            report['final_checks'] = development.checks(validation, kernel, environment=safe_env)
            if not config.get('validation'):
                raise BuildError('development build requires real Kconfig and Kbuild validation commands; checks remain UNTESTED')
        report["build"]["toolchain_environment"] = {"keys": sorted(managed_environment), "root": report.get("toolchain", {}).get("managed", {}).get("install_path")}
        with log_path.open("w", encoding="utf-8") as log:
            log.write(f"$ {shlex.join(_safe_argv(plan.argv))}\n"); log.flush()
            try:
                result = subprocess.run(plan.argv, cwd=plan.cwd, env=safe_env, stdout=log, stderr=subprocess.STDOUT, check=False, timeout=timeout)
                report["build"]["exit_status"] = result.returncode
            except subprocess.TimeoutExpired:
                report["build"]["timed_out"] = True
                report["build"]["exit_status"] = 124
                raise BuildError(f"{mode} build timed out after {timeout} seconds")
        if report["build"]["exit_status"]:
            raise BuildError(f"{mode} build failed with exit code {report['build']['exit_status']}; see {log_path}")
        if (source_dir / 'Makefile').is_file():
            from .capabilities import inspect as inspect_capabilities
            report['capabilities'] = inspect_capabilities(source_dir)
        report["artifacts"] = _artifacts(source_dir, output_dir, plan.artifact_patterns)
        if config["artifacts"].get("require_at_least_one", True) and not report["artifacts"]:
            raise BuildError("build succeeded but no configured artifact files were produced")
        report["build"]["status"] = "success"
    except Exception as exc:
        if (output_dir / 'patches.lock.json').is_file():
            report['patch_lock'] = json.loads((output_dir / 'patches.lock.json').read_text(encoding='utf-8'))
        if (output_dir / 'versions.lock.json').is_file():
            report['version_lock'] = json.loads((output_dir / 'versions.lock.json').read_text(encoding='utf-8'))
        if manager and managed_prepared:
            manager.release(managed_prepared)
        report["build"]["status"] = "failure"
        report["error"] = f"{type(exc).__name__}: {exc}"
        if not log_path.exists():
            log_path.write_text(report["error"] + "\n", encoding="utf-8")
        _finish_report(report, monotonic_start)
        _write_report(output_dir, report)
        if isinstance(exc, BuildError):
            raise
        raise BuildError(str(exc)) from exc
    if manager and managed_prepared:
        manager.release(managed_prepared)
    _finish_report(report, monotonic_start)
    _write_report(output_dir, report)
    LOG.info("Build succeeded; %d artifact(s)", len(report["artifacts"]))
    return report


def _finish_report(report: dict, monotonic_start: float) -> None:
    report["build"]["ended_at"] = _utc_now()
    report["build"]["duration_seconds"] = round(time.monotonic() - monotonic_start, 3)


def run_build(config: dict, workspace: Path, output_dir: Path) -> dict:
    """Serialize builds sharing a workspace and reject stale/active lock collisions."""
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    lock = workspace / ".kernelforge-build.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise BuildError(f"another build may be using workspace {workspace}; lock exists at {lock}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(f"pid={os.getpid()}\n")
        return _run_build(config, workspace, output_dir)
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass
