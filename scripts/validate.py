#!/usr/bin/env python3
"""Validate stage-one JSON configuration files against their schemas."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


def validate_file(data_path: Path, schema_path: Path) -> list[str]:
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        return [f"{data_path.relative_to(ROOT)}: {e.message} at {list(e.absolute_path)}" for e in validator.iter_errors(data)]
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"{data_path}: {exc}"]


def main() -> int:
    errors: list[str] = []
    errors.extend(validate_file(ROOT / "configs/defaults.json", ROOT / "schemas/project.schema.json"))
    kernel_files = sorted((ROOT / "configs/kernels").glob("*/kernel.json"))
    expected = {"5.10", "5.15", "6.1", "6.6", "6.12"}
    actual = {p.parent.name for p in kernel_files}
    if actual != expected:
        errors.append(f"kernel config set mismatch: expected {sorted(expected)}, got {sorted(actual)}")
    for path in kernel_files:
        errors.extend(validate_file(path, ROOT / "schemas/kernel.schema.json"))
    if errors:
        print("Configuration validation FAILED", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"Configuration validation PASSED ({len(kernel_files)} kernel profiles + defaults)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
