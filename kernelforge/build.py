"""Separate GKI and Vendor build adapters using explicit argv configuration."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Protocol

from .source import checkout
from .toolchain import check_tools

LOG = logging.getLogger(__name__)


class BuildError(RuntimeError):
    pass


class Adapter(Protocol):
    def command(self, config: dict, context: dict[str, str]) -> list[str]: ...


def _expand(argv: list[str], context: dict[str, str]) -> list[str]:
    expanded = []
    for value in argv:
        try:
            expanded.append(value.format_map(context))
        except KeyError as exc:
            raise BuildError(f"unknown build command placeholder: {exc.args[0]}") from exc
    return expanded


class GkiAdapter:
    """GKI/Kleaf or build.sh command is intentionally supplied by its profile."""

    def command(self, config: dict, context: dict[str, str]) -> list[str]:
        mode = config["build"]["gki"]["system"]
        if mode not in {"kleaf", "build-sh"}:
            raise BuildError(f"unsupported GKI system: {mode}")
        return _expand(config["build"]["gki"]["argv"], context)


class VendorAdapter:
    """Vendor command/arguments are profile-defined; shell interpolation is disabled."""

    def command(self, config: dict, context: dict[str, str]) -> list[str]:
        return _expand(config["build"]["vendor"]["argv"], context)


ADAPTERS: dict[str, Adapter] = {"gki": GkiAdapter(), "vendor": VendorAdapter()}


def run_build(config: dict, workspace: Path, output_dir: Path) -> dict:
    source_cfg = config["source"]
    build_cfg = config["build"]
    mode = build_cfg["mode"]
    if mode not in ADAPTERS:
        raise BuildError(f"unsupported build mode: {mode}")
    source_dir = workspace / "source"
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    versions = check_tools(config["toolchain"]["required"])
    source_sha = checkout(source_cfg["repository"], source_cfg["ref"], source_dir)
    env = os.environ.copy()
    env.update({key: str(value) for key, value in config.get("environment", {}).items()})
    context = {"source": str(source_dir.resolve()), "out": str(output_dir.resolve()), "jobs": str(config["build"]["jobs"]), "defconfig": config.get("defconfig", "")}
    if mode == "gki":
        argv = ADAPTERS[mode].command(config, context)
    else:
        argv = ADAPTERS[mode].command(config, context)
    if not argv or not argv[0]:
        raise BuildError(f"{mode} build command is empty")
    log_path = output_dir / "build.log"
    LOG.info("Executing %s adapter: %s", mode, shlex.join(argv))
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"$ {shlex.join(argv)}\n")
        log.flush()
        result = subprocess.run(argv, cwd=source_dir, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise BuildError(f"{mode} build failed with exit code {result.returncode}; see {log_path}")
    artifacts = []
    for pattern in config["artifacts"]["paths"]:
        for artifact in source_dir.glob(pattern):
            if artifact.is_file():
                digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
                target = output_dir / artifact.name
                target.write_bytes(artifact.read_bytes())
                artifacts.append({"source": str(artifact.relative_to(source_dir)), "file": target.name, "size": target.stat().st_size, "sha256": digest})
    if config["artifacts"].get("require_at_least_one", True) and not artifacts:
        raise BuildError("build command succeeded but no configured artifact files were produced")
    report = {"mode": mode, "source_repository": source_cfg["repository"], "source_commit": source_sha, "tool_versions": versions, "command": argv, "duration_seconds": round(time.time() - started, 2), "artifacts": artifacts, "build_log": log_path.name}
    (output_dir / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
