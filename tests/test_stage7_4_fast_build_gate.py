"""Stage 7.4 offline admission regression; no source sync, build, or cache."""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.stage7_4_fast_build_gate import (
    ROOT, LOCK, PROFILE, AdmissionBlocked,
    evaluate, inspect_policy, inspect_source, main,
)


class Stage74AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for rel in (LOCK, PROFILE):
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, path)

    def sha(self):
        return hashlib.sha256((self.root / LOCK).read_bytes()).hexdigest()

    def edit(self, rel, change):
        path = self.root / rel
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_locked_35_project_policy_never_authorizes_build(self):
        result = evaluate(self.root, self.sha())
        self.assertEqual(result["locked_projects"], 35)
        self.assertEqual(result["status"], "POLICY_TESTED_SOURCE_UNTESTED")
        self.assertFalse(result["build_started"])
        self.assertFalse(result["build_eligible"])
        self.assertFalse(result["flashable_release_eligible"])
        self.assertFalse(result["ccache_enabled"])

    def test_custom_timestamp_exact_utc(self):
        output = evaluate(self.root, self.sha(),
                          build_timestamp="2026-11-24T17:30:00+08:00")
        self.assertEqual(output["timestamp_preflight_preview"]["utc_iso8601"],
                         "2026-11-24T09:30:00Z")

    def test_default_timestamp_is_preflight_only(self):
        result = evaluate(self.root, self.sha())
        self.assertEqual(result["timestamp_preflight_preview"]["mode"], "current_utc")
        self.assertFalse(result["build_started"])

    def test_invalid_timestamp_fails_closed(self):
        with self.assertRaises(ValueError):
            evaluate(self.root, self.sha(), build_timestamp="2026-11-24T17:30:00")

    def test_missing_or_mismatched_digest_fails(self):
        for bad in ("", "a"*64, "NOT_A_SHA"):
            with self.subTest(bad=bad), self.assertRaises(AdmissionBlocked):
                inspect_policy(self.root, bad)

    def test_manifest_mutation_requires_new_sha_then_still_fails(self):
        previous = self.sha()
        self.edit(LOCK, lambda d: d.update(manifest_commit="b"*40))
        with self.assertRaisesRegex(AdmissionBlocked, "SOURCE_LOCK_SHA256_CHANGED"):
            evaluate(self.root, previous)
        with self.assertRaisesRegex(AdmissionBlocked, "MANIFEST_IDENTITY_MISMATCH"):
            evaluate(self.root, self.sha())

    def test_wrong_device_profile_fails(self):
        self.edit(PROFILE, lambda d: d.update(model="WRONG"))
        with self.assertRaisesRegex(AdmissionBlocked, "DEVICE_PROFILE_UNREVIEWED"):
            evaluate(self.root, self.sha())

    def test_missing_project_fails(self):
        self.edit(LOCK, lambda d: d["source_lock"]["projects"].pop())
        with self.assertRaisesRegex(AdmissionBlocked, "SOURCE_PROJECT_COUNT_NOT_35"):
            evaluate(self.root, self.sha())

    def test_unpinned_commit_fails(self):
        self.edit(LOCK, lambda d: d["source_lock"]["projects"][0].update(commit_sha="latest"))
        with self.assertRaisesRegex(AdmissionBlocked, "MUTABLE_PROJECT_COMMIT"):
            evaluate(self.root, self.sha())

    def test_escape_project_path_fails(self):
        self.edit(LOCK, lambda d: d["source_lock"]["projects"][0].update(path="../escape"))
        with self.assertRaisesRegex(AdmissionBlocked, "UNSAFE_PROJECT_PATH"):
            evaluate(self.root, self.sha())

    def test_duplicate_project_path_fails(self):
        def rewrite(data):
            data["source_lock"]["projects"][1]["path"] = data["source_lock"]["projects"][0]["path"]
        self.edit(LOCK, rewrite)
        with self.assertRaisesRegex(AdmissionBlocked, "DUPLICATE_PROJECT_PATH"):
            evaluate(self.root, self.sha())

    def test_untrusted_https_host_blocks_even_with_reviewed_digest(self):
        self.edit(LOCK, lambda d: d["source_lock"]["projects"][0].update(
            repository="https://attacker.invalid/kernel.git"))
        with self.assertRaisesRegex(AdmissionBlocked, "UNTRUSTED_PROJECT_REPOSITORY"):
            evaluate(self.root, self.sha())

    def test_dirty_tracked_source_blocks_even_if_all_commits_match(self):
        source = self.root / "source"
        (source / ".repo/manifests").mkdir(parents=True)
        lock, _, _ = inspect_policy(self.root, self.sha())
        matches = [{"name": p["name"], "matches_lock": True}
                   for p in lock["source_lock"]["projects"]]
        with patch("scripts.stage7_4_fast_build_gate.sample_capacity", return_value={}):
            with patch("scripts.stage7_4_fast_build_gate.verify_manifest_selection"):
                with patch("scripts.stage7_4_fast_build_gate.git_value",
                           return_value=lock["manifest_commit"]):
                    with patch("scripts.stage7_4_fast_build_gate.inspect_projects",
                               return_value=matches):
                        with patch("scripts.stage7_4_fast_build_gate.project_path",
                                   return_value=source):
                            with patch("scripts.stage7_4_fast_build_gate.subprocess.check_output",
                                       return_value=" M fs/unsafe.c"):
                                with self.assertRaisesRegex(AdmissionBlocked,
                                                            "SOURCE_TRACKED_WORKTREE_DIRTY"):
                                    inspect_source(lock, source)

    def test_missing_source_fails_closed(self):
        with self.assertRaisesRegex(AdmissionBlocked, "EXISTING_REPO_SOURCE_REQUIRED"):
            evaluate(self.root, self.sha(), source=self.root / "missing")

    def test_wsl_requires_physical_host_sample(self):
        source = self.root / "source"
        (source / ".repo/manifests").mkdir(parents=True)
        lock, _, _ = inspect_policy(self.root, self.sha())
        with patch("scripts.stage7_4_fast_build_gate.platform.release",
                   return_value="6.18.1-microsoft-WSL2"):
            with self.assertRaisesRegex(AdmissionBlocked, "WSL_PHYSICAL_HOST_DISK_REQUIRED"):
                inspect_source(lock, source)

    def test_disk_reserve_stops_before_source_git_checks(self):
        source = self.root / "source"
        (source / ".repo/manifests").mkdir(parents=True)
        lock, _, _ = inspect_policy(self.root, self.sha())
        with patch("scripts.stage7_4_fast_build_gate.sample_capacity",
                   side_effect=AdmissionBlocked("DISK_RESERVE_EXHAUSTED")):
            with patch("scripts.stage7_4_fast_build_gate.verify_manifest_selection") as f:
                with self.assertRaisesRegex(AdmissionBlocked, "DISK_RESERVE_EXHAUSTED"):
                    inspect_source(lock, source)
                f.assert_not_called()

    def test_project_mismatch_is_not_overridden_by_manifest_match(self):
        source = self.root / "source"
        (source / ".repo/manifests").mkdir(parents=True)
        lock, _, _ = inspect_policy(self.root, self.sha())
        with patch("scripts.stage7_4_fast_build_gate.sample_capacity", return_value={}):
            with patch("scripts.stage7_4_fast_build_gate.verify_manifest_selection"):
                with patch("scripts.stage7_4_fast_build_gate.git_value",
                           return_value=lock["manifest_commit"]):
                    with patch("scripts.stage7_4_fast_build_gate.inspect_projects",
                               return_value=[{"name":"mismatch","matches_lock":False}]):
                        with self.assertRaisesRegex(AdmissionBlocked, "PROJECT_HEAD_MISMATCH"):
                            inspect_source(lock, source)

    def test_cli_failed_admission_does_not_emit_trusted_report(self):
        report = self.root / "report.json"
        self.assertEqual(main(["--repo-root", str(self.root),
                               "--reviewed-lock-sha256", "bad",
                               "--report", str(report)]), 2)
        self.assertFalse(report.exists())

    def test_valid_report_must_not_be_written_into_repository(self):
        target = self.root / "accidental-source-report.json"
        self.assertEqual(main(["--repo-root", str(self.root),
                               "--reviewed-lock-sha256", self.sha(),
                               "--report", str(target)]), 2)
        self.assertFalse(target.exists())

    def test_valid_report_outside_source_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as outside:
            report = Path(outside) / "read-only-evidence.json"
            args = ["--repo-root", str(self.root),
                    "--reviewed-lock-sha256", self.sha(),
                    "--report", str(report)]
            self.assertEqual(main(args), 0)
            original = report.read_bytes()
            self.assertFalse(json.loads(original)["build_eligible"])
            self.assertEqual(main(args), 2)
            self.assertEqual(report.read_bytes(), original)

    def test_manual_workflow_does_not_compose_automatic_kernel_job(self):
        yaml = (ROOT / ".github/workflows/stage7-4-fast-build.yml").read_text()
        self.assertIn("workflow_dispatch:", yaml)
        self.assertNotIn("\n  push:", yaml)
        self.assertNotIn("\n  pull_request:", yaml)
        self.assertIn("contents: read", yaml)
        self.assertIn("stage1/initial-foundation", yaml)
        self.assertIn("retention-days: 7", yaml)
        self.assertIn("build_timestamp:", yaml)
        self.assertNotIn("bazel build", yaml)
        self.assertNotIn("repo sync", yaml)
        self.assertNotIn("ccache -C", yaml)
        self.assertNotIn("softprops/action-gh-release", yaml)


if __name__ == "__main__":
    unittest.main()
