"""Stage 7.3 build-engine ccache opt-in integration (no real ccache or kernel)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kernelforge.build import run_build, BuildError
from kernelforge.build_cache import BuildCacheNamespaces, BuildCacheError


COMMIT = "a" * 40


class Stage73BuildIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    @staticmethod
    def source(_repository, _ref, destination, **_kw):
        destination.mkdir(parents=True, exist_ok=False)
        (destination / ".config").write_text("CONFIG_EXACT=y\n", encoding="utf-8")
        return COMMIT

    def config(self, *, enabled=True, mode="gki", script=None):
        script = script or (
            "import os; from pathlib import Path; "
            "Path('Image').write_text("
            "os.getenv('CCACHE_DIR','NO_CACHE')+'|'+"
            "os.getenv('CCACHE_REMOTE_STORAGE','NO_REMOTE'))"
        )
        profile = {
            "kind": "llvm", "name": "test-compiler",
            "version": "18.1.0", "target_arch": "aarch64",
            "local_path": sys.executable,
            "version_args": ["-c", "print('clang version 18.1.0')"],
            "executables": {"CC": "clang"},
        }
        adapter = {
            "argv": [sys.executable, "-c", script],
            "directory": ".", "targets": ["Image"],
            "artifacts": ["Image"], "toolchain_profile": profile
        }
        build = {"mode": mode, "jobs": 1,
                 "gki": {**adapter, "system": "kleaf"}, "vendor": adapter}
        if enabled:
            build["ccache"] = {"enabled": True, "max_size_mib": 256}
        return {
            "schema_version": 1, "device": {"id": "fixture-device"},
            "kernel_version": "6.1",
            "source": {"repository": "https://example.invalid/kernel.git", "ref": COMMIT},
            "toolchain": {"required": [], "mode": "LOCAL_ONLY",
                          "cache_dir": str(self.base / "toolchains")},
            "build": build,
            "artifacts": {"paths": ["Image"], "require_at_least_one": True},
        }

    def execute(self, config, *, workspace=None, output=None, source=None):
        work = workspace or self.base / "workspace"
        out = output or self.base / "output"
        with patch("kernelforge.build.checkout",
                   side_effect=source or self.source):
            return run_build(config, work, out)

    def test_disabled_by_default_does_not_create_cache(self):
        result = self.execute(self.config(enabled=False))
        self.assertEqual(result["build"]["status"], "success")
        self.assertNotIn("build_cache", result)
        self.assertEqual((self.base/"output/Image").read_text().split("|")[0], "NO_CACHE")
        self.assertFalse((self.base/"workspace/.kernelforge-build-cache").exists())

    def test_opt_in_provisions_exact_namespace_and_safe_env(self):
        with patch.dict(os.environ, {
            "CCACHE_DIR": "POISONED_OTHER_DEVICE",
            "CCACHE_REMOTE_STORAGE": "https://unapproved.example/ccache",
            "CCACHE_SLOPPINESS": "all",
        }):
            result = self.execute(self.config())
        self.assertEqual(result["build"]["status"], "success")
        cache = result["build_cache"]
        self.assertEqual(cache["status"], "NAMESPACE_READY_INTERCEPTION_UNTESTED")
        self.assertFalse(cache["device_level_cache_authorized"])
        self.assertFalse(cache["physical_disk_quota_enforced"])
        self.assertEqual(cache["cache_hit_rate"], "UNTESTED")
        self.assertFalse(cache["ccache_binary_executed"])
        self.assertTrue(Path(cache["path"]).is_dir())
        contents = (self.base/"output/Image").read_text()
        self.assertTrue(contents.startswith(cache["path"]))
        self.assertTrue(contents.endswith("|NO_REMOTE"))
        ctl = BuildCacheNamespaces(self.base/"workspace/.kernelforge-build-cache/ccache", max_size_mib=256)
        self.assertEqual(ctl.inspect(cache["key"])["active_or_unreconciled_leases"], 0)

    def test_moving_source_ref_rejected_before_build_and_cache(self):
        config = self.config()
        config["source"]["ref"] = "main"
        with self.assertRaisesRegex(BuildError, "exact pinned source"):
            self.execute(config)
        report = json.loads((self.base/"output/build-report.json").read_text())
        self.assertEqual(report["build"]["status"], "failure")
        self.assertFalse((self.base/"workspace/.kernelforge-build-cache").exists())
        self.assertFalse((self.base/"workspace/source/Image").exists())

    def test_missing_managed_compiler_rejected(self):
        config = self.config()
        config["build"]["gki"].pop("toolchain_profile")
        with self.assertRaisesRegex(BuildError, "verified managed toolchain"):
            self.execute(config)
        self.assertFalse((self.base/"workspace/.kernelforge-build-cache").exists())

    def test_missing_final_config_rejected_without_cache(self):
        def checkout(repo, ref, dest, **kwargs):
            dest.mkdir(parents=True, exist_ok=False)
            return COMMIT
        with self.assertRaisesRegex(BuildError, "final .config"):
            self.execute(self.config(), source=checkout)
        self.assertFalse((self.base/"workspace/.kernelforge-build-cache").exists())

    def test_device_profile_cache_blocked_before_new_real_oki_admission(self):
        config = self.config()
        # The profile gate will be checked before the test cache gate;
        # exercise Stage 7.3 admission directly without touching OEM source.
        from kernelforge.build import _prepare_opt_in_ccache
        config["device_profile"] = "oneplus13-pjz110"
        with self.assertRaisesRegex(BuildError, "Stage 7.4"):
            _prepare_opt_in_ccache(config, self.base, self.base/"output",
                                   self.base/"source", COMMIT, None, None, {}, None)

    def test_wrong_cache_directory_overlap_never_creates_cache_data(self):
        config = self.config()
        config["build"]["ccache"]["directory"] = str(self.base/"workspace/source")
        with self.assertRaisesRegex(BuildError, "overlaps protected"):
            self.execute(config)
        self.assertTrue((self.base/"workspace/source/.config").is_file())
        self.assertFalse((self.base/"workspace/source/.kernelforge-ccache-root.json").exists())

    def test_build_error_quarantines_namespace(self):
        config = self.config(script="raise SystemExit(3)")
        with self.assertRaisesRegex(BuildError, "exit code 3"):
            self.execute(config)
        report = json.loads((self.base/"output/build-report.json").read_text())
        cache = report["build_cache"]
        self.assertEqual(report["build"]["status"], "failure")
        flag = Path(cache["path"]) / ".kernelforge-cache-invalid.json"
        self.assertTrue(flag.is_file())
        ctl = BuildCacheNamespaces(self.base/"workspace/.kernelforge-build-cache/ccache", max_size_mib=256)
        # Recreate exact identity for attempting the same namespace.
        ident = json.loads((Path(cache["path"])/".kernelforge-ccache-identity.json").read_text())["identity"]
        with self.assertRaisesRegex(BuildCacheError, "invalidated"):
            ctl.open(ident)
        self.assertTrue(flag.exists())

    def test_changed_config_during_build_quarantines_namespace(self):
        config = self.config(script=(
            "from pathlib import Path; "
            "Path('.config').write_text('CONFIG_CHANGED=y');"
            "Path('Image').write_text('compiled-but-not-admitted')"
        ))
        with self.assertRaisesRegex(BuildError, "final .config changed"):
            self.execute(config)
        report = json.loads((self.base/"output/build-report.json").read_text())
        self.assertEqual(report["build_cache"]["status"], "BLOCKED_CONFIG_CHANGED_DURING_BUILD")
        self.assertTrue((Path(report["build_cache"]["path"]) /
                         ".kernelforge-cache-invalid.json").exists())

    def test_build_schema_cache_policy_is_disabled_by_default_and_strict(self):
        from jsonschema import Draft202012Validator
        root = Path(__file__).resolve().parents[1]
        schema = json.loads((root/"schemas/build.schema.json").read_text())
        v = Draft202012Validator(schema)
        good = self.config()
        self.assertFalse(list(v.iter_errors(good)))
        missing_enabled = self.config()
        missing_enabled["build"]["ccache"].pop("enabled")
        self.assertTrue(list(v.iter_errors(missing_enabled)))
        unexpected = self.config()
        unexpected["build"]["ccache"]["unreviewed"] = True
        self.assertTrue(list(v.iter_errors(unexpected)))
        invalid_max = self.config()
        invalid_max["build"]["ccache"]["max_size_mib"] = 0
        self.assertTrue(list(v.iter_errors(invalid_max)))


if __name__ == "__main__":
    unittest.main()
