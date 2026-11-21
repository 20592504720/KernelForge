"""Fail-fast executable and minimum-version checks."""
from __future__ import annotations

import re
import shutil
import subprocess


class ToolchainError(RuntimeError):
    pass


def check_tools(requirements: list[dict[str, str]]) -> dict[str, str]:
    found: dict[str, str] = {}
    for item in requirements:
        name = item["name"]
        executable = shutil.which(name)
        if not executable:
            raise ToolchainError(f"required tool not found on PATH: {name}")
        result = subprocess.run([executable, "--version"], capture_output=True, text=True, check=False)
        output = (result.stdout or result.stderr).splitlines()
        version = output[0] if output else "version unavailable"
        match = re.search(r"\d+(?:\.\d+)+", version)
        minimum = item.get("minimum")
        if result.returncode or (minimum and (not match or tuple(map(int, match.group().split("."))) < tuple(map(int, minimum.split("."))))):
            raise ToolchainError(f"{name} version check failed; required minimum {minimum or 'available'}, found {version}")
        found[name] = version
    return found
