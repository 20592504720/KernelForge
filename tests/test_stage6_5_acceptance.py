"""Offline negative tests for Stage 6.5 evidence reconciliation; no network."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.stage6_acceptance import (
    ACCEPTED,
    CATALOG,
    DEPENDENCIES,
    LOCK,
    ROOT,
    WORKTREE,
    Stage6AcceptanceError,
    audit,
)


class Stage65EvidenceTests(unittest.TestCase):
    def test_repository_evidence_reconciles_without_overclaiming(self):
        result = audit(ROOT)
        self.assertEqual(result["result"], "COMMITTED_EVIDENCE_RECONCILED_NOT_FULL_RUN_RESULT")
        self.assertEqual(result["source_lock"]["raw_byte_equivalence"], "34_OF_35_LZ4_CRLF")
        self.assertEqual(result["full_run_acceptance"], "PENDING")
        self.assertFalse(result["flashable_release_eligible"])
        self.assertIn("DFR_INCLUDE_DYNAMIC_MODULE_DEPENDENCY_BLOCKED_UNDETERMINED",
                      result["deferred_blockers"])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.source_files = [LOCK, ACCEPTED, WORKTREE, DEPENDENCIES, CATALOG]
        for name in self.source_files:
            dest = self.home / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        manifest = json.loads((ROOT / CATALOG).read_text(encoding="utf-8"))
        patch = Path("patches/compat/susfs") / manifest["file"]
        shutil.copyfile(ROOT / patch, self.home / patch)

    def rewrite(self, filename, updater):
        path = self.home / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        updater(data)
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_duplicate_or_missing_source_head_rejected(self):
        self.rewrite(ACCEPTED, lambda a: a["source_audit"].update(matched_heads=34))
        with self.assertRaises(Stage6AcceptanceError):
            audit(self.home)

    def test_commit_tree_evidence_mismatch_rejected(self):
        def flip(a):
            a["source_audit"]["project_commit_tree_records"][0]["tree_sha"] = "f" * 40
        self.rewrite(ACCEPTED, flip)
        with self.assertRaises(Stage6AcceptanceError):
            audit(self.home)

    def test_dfr_blocker_cannot_be_silently_cleared(self):
        self.rewrite(DEPENDENCIES, lambda a: a["all_29_risk_counts_after_this_audit"].update(
            BLOCKED_UNDETERMINED=0, VERIFIED_NOT_REQUIRED=29))
        with self.assertRaises(Stage6AcceptanceError):
            audit(self.home)

    def test_lz4_raw_crlf_difference_cannot_be_masked(self):
        self.rewrite(DEPENDENCIES, lambda a: a["lz4"].update(raw_byte_equivalence="TESTED"))
        with self.assertRaises(Stage6AcceptanceError):
            audit(self.home)

    def test_unreviewed_provider_insertion_rejected(self):
        self.rewrite(CATALOG, lambda a: a["provider_commits"].append("f" * 40))
        with self.assertRaises(Stage6AcceptanceError):
            audit(self.home)

    def test_changed_patch_bytes_rejected(self):
        name = json.loads((self.home / CATALOG).read_text(encoding="utf-8"))["file"]
        with (self.home / "patches/compat/susfs" / name).open("ab") as f:
            f.write(b"\nMUTATION")
        with self.assertRaises(Stage6AcceptanceError):
            audit(self.home)

    def test_manifest_missing_project_rejected(self):
        def drop(a):
            a["source_lock"]["projects"].pop()
        self.rewrite(LOCK, drop)
        with self.assertRaises(Stage6AcceptanceError):
            audit(self.home)


if __name__ == "__main__":
    unittest.main()
