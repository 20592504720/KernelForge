"""Local command line interface for configuration and manifest checks."""
from __future__ import annotations

import argparse
import logging
import platform
import sys
from pathlib import Path

from .validation import validate_configs, validate_manifests
from .build import BuildError, run_build
import json

ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m kernelforge")
    parser.add_argument("--verbose", action="store_true", help="show debug diagnostics")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="validate all configuration and patch manifests")
    sub.add_parser("validate-config", help="validate JSON configuration and references")
    sub.add_parser("validate-patches", help="validate patch manifests and local file hashes")
    sub.add_parser("doctor", help="inspect the local validation environment")
    build = sub.add_parser("build", help="run a configured kernel build")
    build.add_argument("--config", required=True, type=Path)
    build.add_argument("--workspace", type=Path, default=Path(".kernel-work"))
    build.add_argument("--output", type=Path, default=Path("artifacts"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")
    if args.command == "doctor":
        logging.info("Python %s on %s", platform.python_version(), platform.platform())
        try:
            import jsonschema  # noqa: F401
            import yaml  # noqa: F401
        except ImportError as exc:
            logging.error("Missing validation dependency: %s", exc)
            return 1
        logging.info("JSON Schema and YAML validation dependencies are available")
        logging.info("Kernel build toolchains are not inspected by this stage-one doctor")
        return 0
    if args.command == "build":
        try:
            config = json.loads(args.config.read_text(encoding="utf-8"))
            schema = json.loads((ROOT / "schemas/build.schema.json").read_text(encoding="utf-8"))
            from jsonschema import Draft202012Validator, FormatChecker
            errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(config))
            if errors:
                for issue in errors:
                    logging.error("build config: %s", issue.message)
                return 2
            report = run_build(config, args.workspace.resolve(), args.output.resolve())
            logging.info("Build succeeded; %d real artifact(s) recorded", len(report["artifacts"]))
            return 0
        except (OSError, json.JSONDecodeError, KeyError, BuildError) as exc:
            logging.error("Build failed: %s", exc)
            return 1
    checks = []
    if args.command in ("validate", "validate-config"):
        checks.extend(validate_configs(ROOT))
    if args.command in ("validate", "validate-patches"):
        checks.extend(validate_manifests(ROOT))
    if checks:
        for issue in checks:
            logging.error("%s", issue)
        return 1
    logging.info("%s passed", args.command)
    return 0


if __name__ == "__main__":
    sys.exit(main())
