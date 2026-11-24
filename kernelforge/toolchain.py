"""Common toolchain discovery and numeric version constraints."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


class ToolchainError(RuntimeError):
    pass


def _version_tuple(text: str) -> tuple[int, ...] | None:
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)+)", text)
    return tuple(int(part) for part in match.group(1).split(".")) if match else None


def _resolve(item: dict[str, str]) -> str:
    path = item.get("path")
    name = item["name"]
    candidate = str(Path(path).expanduser()) if path else shutil.which(name)
    if not candidate or not Path(candidate).is_file():
        raise ToolchainError(f"required tool '{name}' not found; set an absolute path or add it to PATH")
    return str(Path(candidate).resolve())


def check_tools(requirements: list[dict[str, str]], *, timeout: int = 15) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for item in requirements:
        name = item["name"]
        executable = _resolve(item)
        args = item.get("version_args", "--version").split()
        try:
            result = subprocess.run([executable, *args], capture_output=True, text=True, check=False, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise ToolchainError(f"version query for {name} timed out after {timeout}s") from exc
        except OSError as exc:
            raise ToolchainError(f"cannot execute tool '{name}' at {executable}: {exc}") from exc
        output = (result.stdout or result.stderr).strip()
        first_line = output.splitlines()[0] if output else "no version output"
        version = _version_tuple(output)
        minimum = item.get("minimum")
        if result.returncode:
            raise ToolchainError(f"version query for {name} exited {result.returncode}: {first_line}")
        if minimum:
            required = _version_tuple(minimum)
            if not required:
                raise ToolchainError(f"invalid minimum version for {name}: {minimum}")
            if not version:
                raise ToolchainError(f"cannot parse {name} version from: {first_line}")
            width = max(len(required), len(version))
            if version + (0,) * (width-len(version)) < required + (0,) * (width-len(required)):
                raise ToolchainError(f"{name} version too old: requires >= {minimum}, found {first_line}")
        found[name] = {"path": executable, "version": first_line}
    return found
