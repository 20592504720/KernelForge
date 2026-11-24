"""Stage 7.1 offline inventory and fail-closed regression coverage."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.stage7_1_preflight import (
    ROOT, Stage71AuditError, audit_repository, audit_local,
)


INPUTS = [
    "configs/toolchains/defaults.json",
    "schemas/toolchain.schema.json",
    "devices/profiles/oneplus13-pjz110.json",
    "manifests/oneplus13-pjz110-sm8750-source.lock.json",
    "kernelforge/toolchains/manager.py",
    ".github/workflows/build.yml",
    ".github/workflows/release.yml",
    ".github/workflows/source-audit.yml",
    ".github/workflows/stage1-6-full-acceptance.yml",
]


class Stage71PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        for rel in INPUTS:
            dst = self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dst)

    def rewrite(self, rel, mutate):
        p = self.root / rel
        src = json.loads(p.read_text(encoding="utf-8"))
        mutate(src)
        p.write_text(json.dumps(src), encoding="utf-8")

    def test_current_repository_inventory_is_fail_closed(self):
        status = audit_repository(ROOT)
        self.assertEqual(status["status"], "REPOSITORY_PREFLIGHT_TESTED_WITH_BLOCKERS")
        self.assertEqual(status["build_profiles"]["fixed_project_count"], 35)
        self.assertEqual(status["build_profiles"]["oneplus13_fast_build"], "NOT_IMPLEMENTED")
        self.assertEqual(status["cache"]["ccache_shared_build_cache"], "NOT_IMPLEMENTED")
        self.assertFalse(status["build_authorized"])
        self.assertFalse(status["flashable_release_eligible"])

    def test_unchanged_temp_repository_accepts(self):
        self.assertEqual(audit_repository(self.root)["status"],
                         "REPOSITORY_PREFLIGHT_TESTED_WITH_BLOCKERS")

    def test_disabling_download_sha256_is_rejected(self):
        self.rewrite(INPUTS[0], lambda x: x["download"].update(require_sha256=False))
        with self.assertRaisesRegex(Stage71AuditError, "checksum"):
            audit_repository(self.root)

    def test_disabling_cache_checks_is_rejected(self):
        self.rewrite(INPUTS[0], lambda x: x["cache"].update(enabled=False))
        with self.assertRaisesRegex(Stage71AuditError, "checksum"):
            audit_repository(self.root)

    def test_removed_toolchain_safety_method_rejected(self):
        path = self.root / "kernelforge/toolchains/manager.py"
        code = path.read_text(encoding="utf-8")
        self.assertIn("    def _cached(", code)
        path.write_text(code.replace("    def _cached(", "    def _cached_removed(", 1),
                        encoding="utf-8")
        with self.assertRaisesRegex(Stage71AuditError, "methods missing"):
            audit_repository(self.root)

    def test_changed_manifest_lock_rejected(self):
        self.rewrite("manifests/oneplus13-pjz110-sm8750-source.lock.json",
                     lambda x: x.update(manifest_commit="a"*40))
        with self.assertRaisesRegex(Stage71AuditError, "device/source-lock"):
            audit_repository(self.root)

    def test_added_or_missing_locked_project_rejected(self):
        def mutate(x):
            x["source_lock"]["projects"].pop()
        self.rewrite("manifests/oneplus13-pjz110-sm8750-source.lock.json", mutate)
        with self.assertRaisesRegex(Stage71AuditError, "35-project"):
            audit_repository(self.root)

    def test_release_gate_removed_rejected(self):
        p = self.root / ".github/workflows/release.yml"
        p.write_text(p.read_text(encoding="utf-8").replace("if: ${{ false }}", "if: true"),
                     encoding="utf-8")
        with self.assertRaisesRegex(Stage71AuditError, "release workflow"):
            audit_repository(self.root)

    def test_build_placeholder_gate_removed_rejected(self):
        p = self.root / ".github/workflows/build.yml"
        p.write_text(p.read_text(encoding="utf-8").replace("Stop after preflight", "Run full build"),
                     encoding="utf-8")
        with self.assertRaisesRegex(Stage71AuditError, "legacy build"):
            audit_repository(self.root)

    def test_missing_source_sync_guard_rejected(self):
        p = self.root / ".github/workflows/source-audit.yml"
        p.write_text(p.read_text(encoding="utf-8").replace("[run-sm8750-once]", "[unsafe-sync]"),
                     encoding="utf-8")
        with self.assertRaisesRegex(Stage71AuditError, "source sync gate"):
            audit_repository(self.root)

    def test_local_inventory_does_not_create_files_or_execute_versions(self):
        workspace = Path(self.temp.name) / "source"
        (workspace / ".repo/manifests").mkdir(parents=True)
        (workspace / ".repo/manifest.xml").write_text("manifest", encoding="utf-8")
        before = sorted(str(x.relative_to(workspace)) for x in workspace.rglob("*"))
        result = audit_local(workspace)
        after = sorted(str(x.relative_to(workspace)) for x in workspace.rglob("*"))
        self.assertEqual(before, after)
        self.assertTrue(result["workspace"]["repo_manifest_directory_present"])
        self.assertFalse(result["version_commands_executed"])
        self.assertFalse(result["git_commands_executed"])
        self.assertFalse(result["build_eligible"])

    def test_missing_workspace_is_reported_not_created(self):
        missing = Path(self.temp.name) / "not-created"
        result = audit_local(missing)
        self.assertFalse(result["workspace"]["exists"])
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
