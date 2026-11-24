"""Offline build timestamp policy and mocked build-engine propagation."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from kernelforge.build_timestamp import (
    BuildTimestampError, kernel_build_environment, resolve_build_timestamp,
)
from kernelforge.build import run_build
from scripts.resolve_build_timestamp import main as resolve_cli


NOW = datetime(2026, 11, 24, 9, 15, 23, tzinfo=timezone.utc)


class TimestampPolicyTests(unittest.TestCase):
    def test_blank_defaults_to_current_utc_once(self):
        a = resolve_build_timestamp("", now=NOW)
        b = resolve_build_timestamp(None, now=NOW)
        self.assertEqual(a, b)
        self.assertEqual(a["mode"], "current_utc")
        self.assertEqual(a["utc_iso8601"], "2026-11-24T09:15:23Z")
        self.assertEqual(a["source_date_epoch"], 1795511723)

    def test_explicit_utc_and_local_offset_resolve_to_same_instant(self):
        utc = resolve_build_timestamp("2026-11-24T09:15:23Z")
        cn = resolve_build_timestamp("2026-11-24T17:15:23+08:00")
        jp = resolve_build_timestamp("2026-11-24T18:15:23+09:00")
        self.assertEqual(utc["utc_iso8601"], cn["utc_iso8601"])
        self.assertEqual(cn["source_date_epoch"], jp["source_date_epoch"])
        self.assertEqual(utc["mode"], "custom")
        self.assertEqual(utc["kbuild_build_timestamp"], "2026-11-24 09:15:23 UTC")

    def test_build_environment_is_consistent(self):
        env = kernel_build_environment(resolve_build_timestamp("2026-11-24T09:15:23Z"))
        self.assertEqual(env["KBUILD_BUILD_TIMESTAMP"], "2026-11-24 09:15:23 UTC")
        self.assertEqual(env["SOURCE_DATE_EPOCH"], "1795511723")

    def test_bad_input_never_falls_back_silently(self):
        invalid = [
            "now", "latest", "2026-11-24", "2026-11-24 09:15:23",
            "2026-11-24T09:15:23", "2026-11-24T09:15:23.123Z",
            "2026-11-24T09:15:23+15:00", "2026-11-24T09:15:23+14:01",
            "2026-02-30T09:15:23Z", "2026-11-24T25:15:23Z",
            "2026-11-24T09:15:23Z\nKBUILD_BUILD_USER=hacked",
            "1999-12-31T23:59:59Z", "2101-01-01T00:00:00Z", True, 0
        ]
        for requested in invalid:
            with self.subTest(requested=requested), self.assertRaises(BuildTimestampError):
                resolve_build_timestamp(requested)

    def test_non_utc_default_is_normalized_without_inference(self):
        other = datetime.fromisoformat("2026-11-24T17:15:23+08:00")
        self.assertEqual(resolve_build_timestamp("", now=other)["utc_iso8601"],
                         "2026-11-24T09:15:23Z")

    def test_unaware_clock_rejected(self):
        with self.assertRaises(BuildTimestampError):
            resolve_build_timestamp("", now=datetime(2026, 11, 24))

    def test_cli_writes_runner_temp_json_and_github_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = {"KERNELFORGE_BUILD_TIMESTAMP": "2026-11-24T17:15:23+08:00"}
            with patch.dict(os.environ, env):
                rc = resolve_cli(["--json-output", str(root / "stamp.json"),
                                  "--github-output", str(root / "outputs.txt")])
            self.assertEqual(rc, 0)
            d = json.loads((root / "stamp.json").read_text())
            self.assertEqual(d["utc_iso8601"], "2026-11-24T09:15:23Z")
            output = (root / "outputs.txt").read_text()
            self.assertIn("source_date_epoch=1795511723\n", output)
            self.assertIn("build_timestamp_mode=custom\n", output)
            self.assertIn("kbuild_build_timestamp=2026-11-24 09:15:23 UTC\n", output)

    def test_bad_cli_writes_no_approved_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / "outputs.txt"
            with patch.dict(os.environ, {"KERNELFORGE_BUILD_TIMESTAMP": "nonsense"}):
                rc = resolve_cli(["--github-output", str(file)])
            self.assertEqual(rc, 2)
            self.assertFalse(file.exists())

    def test_schema_accepts_optional_valid_timestamp_and_refuses_bad_one(self):
        schema = json.loads((Path(__file__).resolve().parents[1] /
                             "schemas/build.schema.json").read_text(encoding="utf-8"))
        prop = schema["properties"]["build"]["properties"]["build_timestamp"]
        validator = Draft202012Validator(prop)
        self.assertTrue(validator.is_valid(""))
        self.assertTrue(validator.is_valid("2026-11-24T17:15:23+08:00"))
        self.assertFalse(validator.is_valid("2026-11-24T17:15:23"))
        self.assertFalse(validator.is_valid(True))


class BuildEngineTimestampTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    @staticmethod
    def checkout(_repo, _ref, folder, **_kwargs):
        folder.mkdir(parents=True, exist_ok=False)
        return "a" * 40

    def config(self, timestamp="2026-11-24T17:15:23+08:00"):
        script = (
            "import os,json;from pathlib import Path;"
            "Path('Image').write_text(json.dumps(dict("
            "kbuild=os.getenv('KBUILD_BUILD_TIMESTAMP'),"
            "epoch=os.getenv('SOURCE_DATE_EPOCH'),"
            "timezone=os.getenv('TZ'))))"
        )
        spec = {"argv": [sys.executable, "-c", script], "directory": ".",
                "targets": ["Image"], "artifacts": ["Image"]}
        return {
            "schema_version": 1,
            "device": {"id": "time-fixture"},
            "kernel_version": "6.1",
            "source": {"repository": "https://github.com/example/kernel", "ref": "a"*40},
            "toolchain": {"required": []},
            "build": {"mode": "vendor", "jobs": 1,
                      "build_timestamp": timestamp, "gki": {"system": "kleaf", **spec},
                      "vendor": spec},
            "artifacts": {"paths": ["Image"], "require_at_least_one": True},
        }

    def test_subprocess_receives_normalized_time_and_report_distinguishes_start(self):
        with patch("kernelforge.build.checkout", side_effect=self.checkout):
            report = run_build(self.config(), self.root / "work", self.root / "output")
        payload = json.loads((self.root / "output" / "Image").read_text())
        self.assertEqual(payload["kbuild"], "2026-11-24 09:15:23 UTC")
        self.assertEqual(payload["epoch"], "1795511723")
        self.assertEqual(report["build"]["build_timestamp"]["mode"], "custom")
        self.assertEqual(report["build"]["build_timestamp"]["utc_iso8601"],
                         "2026-11-24T09:15:23Z")
        self.assertIn("started_at", report["build"])
        self.assertIn("build_timestamp", json.loads(
            (self.root / "output" / "build-report.json").read_text())["build"])

    def test_invalid_explicit_build_time_fails_closed_without_checkout(self):
        with patch("kernelforge.build.checkout") as checkout:
            with self.assertRaisesRegex(Exception, "custom build time"):
                run_build(self.config("garbage"), self.root / "work", self.root / "out")
            checkout.assert_not_called()
        report = json.loads((self.root / "out" / "build-report.json").read_text())
        self.assertEqual(report["build"]["status"], "failure")

    def test_default_current_timestamp_is_recorded(self):
        config = self.config()
        config["build"].pop("build_timestamp")
        with patch("kernelforge.build.checkout", side_effect=self.checkout):
            report = run_build(config, self.root / "work", self.root / "out")
        self.assertEqual(report["build"]["build_timestamp"]["mode"], "current_utc")
        self.assertTrue(report["build"]["build_timestamp"]["utc_iso8601"].endswith("Z"))


if __name__ == "__main__":
    unittest.main()
