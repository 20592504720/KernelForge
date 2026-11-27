"""Schema-driven validation with actionable file and JSON-path diagnostics."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


def _read_json(path: Path) -> tuple[Any | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"{path}: invalid or unreadable JSON: {exc}"]


def _schema_errors(data: Any, schema: Any, path: Path) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [f"{path}: {error.message} at {'.'.join(map(str, error.absolute_path)) or '<root>'}" for error in validator.iter_errors(data)]


def validate_configs(root: Path) -> list[str]:
    problems: list[str] = []
    schema_path = root / "schemas/kernel.schema.json"
    schema, errors = _read_json(schema_path)
    problems.extend(errors)
    project_schema_path = root / "schemas/project.schema.json"
    project_schema, errors = _read_json(project_schema_path)
    problems.extend(errors)
    toolchain_schema_path = root / "schemas/toolchain.schema.json"
    toolchain_schema, errors = _read_json(toolchain_schema_path)
    problems.extend(errors)
    if problems:
        return problems
    for data_path, selected_schema in [(root / "configs/defaults.json", project_schema)]:
        data, errors = _read_json(data_path)
        problems.extend(errors)
        if not errors:
            problems.extend(_schema_errors(data, selected_schema, data_path.relative_to(root)))
    toolchain_defaults = root / "configs/toolchains/defaults.json"
    data, errors = _read_json(toolchain_defaults)
    problems.extend(errors)
    if not errors:
        problems.extend(_schema_errors(data, toolchain_schema, toolchain_defaults.relative_to(root)))
    build_schema_path = root / "schemas/build.schema.json"
    if (root / "configs/kernelsu").exists():
        build_schema, errors = _read_json(build_schema_path)
        problems.extend(errors)
        if not errors and isinstance(build_schema, dict):
            for path in sorted((root / "configs/kernelsu").glob("*.json")):
                data, errors = _read_json(path)
                problems.extend(errors)
                if not errors:
                    problems.extend(_schema_errors(data, build_schema["$defs"]["kernelsu"], path.relative_to(root)))
    paths = sorted((root / "configs/kernels").glob("*/kernel.json"))
    expected = {"5.10", "5.15", "6.1", "6.6", "6.12"}
    actual = {path.parent.name for path in paths}
    if actual != expected:
        problems.append(f"kernel profile directories mismatch: expected {sorted(expected)}, got {sorted(actual)}")
    for path in paths:
        data, errors = _read_json(path)
        problems.extend(errors)
        if not errors:
            issues = _schema_errors(data, schema, path.relative_to(root))
            problems.extend(issues)
            if issues:
                continue
            if not isinstance(data, dict):
                problems.append(f'{path.relative_to(root)}: expected a configuration object')
                continue
            manifest = root / data["features"]["patch_manifest"]
            if not manifest.is_file():
                problems.append(f"{path.relative_to(root)} references missing patch manifest {manifest.relative_to(root)}")
    try:
        from .source_provider import PROFILE_IDS, load_profile
        for profile_id in sorted(PROFILE_IDS):
            try:
                load_profile(root, profile_id)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                problems.append(f'device profile {profile_id}: {exc}')
    except ImportError as exc:
        problems.append(f'cannot validate device profiles: {exc}')
    return problems


def validate_manifests(root: Path) -> list[str]:
    problems: list[str] = []
    schema_path = root / "schemas/patch-manifest.schema.json"
    schema, errors = _read_json(schema_path)
    problems.extend(errors)
    if errors:
        return problems
    for path in sorted((root / "patches").glob("*/manifest.json")):
        data, errors = _read_json(path)
        problems.extend(errors)
        if errors:
            continue
        issues = _schema_errors(data, schema, path.relative_to(root))
        problems.extend(issues)
        if issues:
            continue  # never interpret paths from invalid data
        if not isinstance(data, dict):
            problems.append(f'{path.relative_to(root)}: expected a manifest object')
            continue
        identifiers = {item.get("id") for item in data.get("patches", [])}
        if len(identifiers) != len(data.get("patches", [])):
            problems.append(f"{path.relative_to(root)}: duplicate patch identifiers")
            continue
        for entry in data.get("patches", []):
            missing = set(entry.get("depends_on", [])) - identifiers
            if missing:
                problems.append(f"{path.relative_to(root)}: {entry['id']} has unknown dependencies {sorted(missing)}")
            relative = PurePosixPath(entry["file"])
            parent = path.parent.resolve()
            patch_path = path.parent.joinpath(*relative.parts)
            # Reject links at every component, Windows drive/ADS syntax,
            # and paths outside the particular manifest's own directory.
            if (relative.is_absolute() or ".." in relative.parts or
                    "\\" in entry["file"] or ":" in entry["file"] or
                    root.resolve() not in parent.parents or
                    any(p.is_symlink() for p in (patch_path, *patch_path.parents) if p != root.parent) or
                    parent not in patch_path.resolve().parents):
                problems.append(f"{path.relative_to(root)}: unsafe patch path")
                continue
            if not patch_path.is_file():
                problems.append(f"{path.relative_to(root)}: missing patch file {patch_path.relative_to(root)}")
                continue
            digest = hashlib.sha256(patch_path.read_bytes()).hexdigest()
            if digest != entry["sha256"]:
                problems.append(f"{path.relative_to(root)}: SHA256 mismatch for {patch_path.relative_to(root)}")
    catalog = root / 'patches/compat/susfs/manifest.json'
    if catalog.exists():
        data, errors = _read_json(catalog)
        problems.extend(errors)
        compat_schema, errors = _read_json(root / 'schemas/susfs-compat.schema.json')
        problems.extend(errors)
        if data is not None and not errors:
            issues = _schema_errors(data, compat_schema, catalog.relative_to(root))
            problems.extend(issues)
            if not issues:
                patch = (catalog.parent / data['file']).resolve()
                if catalog.parent.resolve() not in patch.parents or not patch.is_file():
                    problems.append('unsafe or missing SUSFS compatibility patch')
                elif hashlib.sha256(patch.read_bytes()).hexdigest() != data['sha256']:
                    problems.append('SUSFS compatibility patch SHA256 mismatch')
    return problems
