"""Resolve user-configurable kernel build time without starting a build.

For workflow_dispatch, set KERNELFORGE_BUILD_TIMESTAMP to an empty string for
current UTC or a strict explicit-offset timestamp. GitHub outputs are written
only after validation succeeds.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from kernelforge.build_timestamp import (
    BuildTimestampError,
    kernel_build_environment,
    resolve_build_timestamp,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requested", default=None,
                        help="optional explicit ISO8601 timestamp; omit for env/default")
    parser.add_argument("--json-output", type=Path,
                        help="optional runner-temp JSON evidence path")
    parser.add_argument("--github-output", type=Path,
                        help="optional GITHUB_OUTPUT destination")
    args = parser.parse_args(argv)
    requested = (os.environ.get("KERNELFORGE_BUILD_TIMESTAMP", "")
                 if args.requested is None else args.requested)
    try:
        stamp = resolve_build_timestamp(requested)
        values = kernel_build_environment(stamp)
        serialized = json.dumps(stamp, sort_keys=True, ensure_ascii=True) + "\n"
        if args.json_output:
            args.json_output.write_text(serialized, encoding="utf-8")
        if args.github_output:
            with args.github_output.open("a", encoding="utf-8") as out:
                out.write("build_timestamp_utc=" + stamp["utc_iso8601"] + "\n")
                out.write("build_timestamp_mode=" + stamp["mode"] + "\n")
                out.write("source_date_epoch=" + values["SOURCE_DATE_EPOCH"] + "\n")
                out.write("kbuild_build_timestamp=" + values["KBUILD_BUILD_TIMESTAMP"] + "\n")
        sys.stdout.write(serialized)
        return 0
    except (BuildTimestampError, OSError) as exc:
        sys.stderr.write("BUILD_TIMESTAMP_REJECTED: " + str(exc) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
