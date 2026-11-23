"""Stage 6.4 immutable provider/SUSFS negative and regression checks; no network."""
from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from kernelforge.compatibility_gate import (
    BAKA_REPO, OFFICIAL_REPO, SUSFS_REPO, KERNEL_REPO,
    CompatibilityGateError, evaluate_reviewed, require_release_eligible,
)

ROOT = Path(__file__).resolve().parents[1]
REAL_CATALOG = ROOT / "patches/compat/susfs/manifest.json"
OLD_BAKA = "7b65bde0710b5e7c6f755545cb15a4abd417f3a8"
NEW_BAKA = "2734e0bc155759955880f5fb99be640fc5b92156"
OFFICIAL = "2a60b2893b8d0d885d1ceff2287d8ad854f0e0f4"
NEWER_UNREVIEWED_BAKA = "63ad1ea3a90455dee9d77163cdafb028d8a90416"


def pinned(sha, repo):
    return {"repository": repo, "policy": "pinned", "ref_type": "commit",
            "requested_ref": sha, "commit_sha": sha}


def fixture(provider="bakasu", sha=NEW_BAKA):
    return {
        "android_gki": "android14-6.1",
        "kernel": pinned("498f91c17b0822a09aede17d26a63bf8c6813725", KERNEL_REPO),
        "kernelsu": pinned(sha, OFFICIAL_REPO if provider == "official" else BAKA_REPO),
        "susfs": pinned("756abbf2d81557e36664fc67dffaee26d3dfc57c", SUSFS_REPO),
    }


class Stage64ReviewedGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.catalog = self.base / "manifest.json"
        self.original = json.loads(REAL_CATALOG.read_text(encoding="utf-8"))
        self.adapter = self.base / self.original["file"]
        shutil.copyfile(REAL_CATALOG.parent / self.original["file"], self.adapter)
        self.save(self.original)

    def save(self, value):
        self.catalog.write_text(json.dumps(value), encoding="utf-8")

    def assess(self, source=None, provider="bakasu"):
        return evaluate_reviewed(source if source is not None else fixture(),
                                 provider=provider, catalog=self.catalog)

    def test_two_bakasu_versions_remain_reviewed_but_not_release_eligible(self):
        for sha in (OLD_BAKA, NEW_BAKA):
            with self.subTest(sha=sha):
                report = self.assess(fixture(sha=sha))
                self.assertEqual(report["status"], "DECLARED_PINNED_TRIPLE_REVIEWED")
                self.assertEqual(report["object_compilation"], "NOT_INFERRED")
                self.assertEqual(report["source_checkout_identity"],
                                 "REQUIRES_INDEPENDENT_GIT_VERIFICATION")
                self.assertFalse(report["release_eligible"])
                with self.assertRaisesRegex(CompatibilityGateError, "never authorizes"):
                    require_release_eligible(report)

    def test_official_is_reviewed_not_mistaken_for_bakasu(self):
        report = self.assess(fixture("official", OFFICIAL), "official")
        self.assertEqual(report["provider"], "official")
        with self.assertRaisesRegex(CompatibilityGateError, "not reviewed"):
            self.assess(fixture("bakasu", OFFICIAL), "bakasu")

    def test_bakssu_alias_is_normalized(self):
        self.assertEqual(self.assess(provider="bakssu")["provider"], "bakasu")

    def test_unreviewed_moving_bakasu_head_is_rejected(self):
        with self.assertRaisesRegex(CompatibilityGateError, "not reviewed"):
            self.assess(fixture(sha=NEWER_UNREVIEWED_BAKA))

    def test_moving_policy_fails_even_when_resolved_sha_matches(self):
        for name in ("kernel", "kernelsu", "susfs"):
            lock = fixture()
            lock[name]["policy"] = "latest_branch"
            lock[name]["requested_ref"] = "main"
            lock[name]["ref_type"] = "branch"
            with self.subTest(name=name), self.assertRaisesRegex(CompatibilityGateError, "must be pinned"):
                self.assess(lock)

    def test_tag_or_nonmatching_requested_ref_is_rejected(self):
        for key, val in (("ref_type", "tag"), ("requested_ref", "main"),
                         ("requested_ref", "b" * 40)):
            lock = fixture()
            lock["kernelsu"][key] = val
            with self.subTest(key=key, value=val), self.assertRaises(CompatibilityGateError):
                self.assess(lock)

    def test_wrong_repository_rejected_for_each_source(self):
        for name in ("kernel", "kernelsu", "susfs"):
            lock = fixture()
            lock[name]["repository"] = "https://attacker.example/redirect"
            with self.subTest(name=name), self.assertRaisesRegex(CompatibilityGateError, "repository identity"):
                self.assess(lock)

    def test_wrong_sha_rejected_for_kernel_susfs_and_provider(self):
        for name in ("kernel", "kernelsu", "susfs"):
            lock = fixture()
            lock[name]["commit_sha"] = "f" * 40
            lock[name]["requested_ref"] = "f" * 40
            with self.subTest(name=name), self.assertRaises(CompatibilityGateError):
                self.assess(lock)

    def test_abbreviated_uppercase_or_invalid_sha_rejected(self):
        for sha in ("abcd", "A" * 40, "g" * 40):
            lock = fixture()
            lock["kernelsu"]["commit_sha"] = sha
            lock["kernelsu"]["requested_ref"] = sha
            with self.subTest(sha=sha), self.assertRaisesRegex(CompatibilityGateError, "lowercase"):
                self.assess(lock)

    def test_gki_identity_mismatch_rejected(self):
        lock = fixture()
        lock["android_gki"] = "android15-6.6"
        with self.assertRaisesRegex(CompatibilityGateError, "Android GKI"):
            self.assess(lock)

    def test_catalog_unreviewed_provider_insertion_rejected(self):
        mutated = copy.deepcopy(self.original)
        mutated["provider_commits"].append("f" * 40)
        self.save(mutated)
        with self.assertRaisesRegex(CompatibilityGateError, "unreviewed addition"):
            self.assess()

    def test_catalog_duplicate_provider_rejected(self):
        mutated = copy.deepcopy(self.original)
        mutated["provider_commits"].append(NEW_BAKA)
        self.save(mutated)
        with self.assertRaises(CompatibilityGateError):
            self.assess()

    def test_catalog_removal_rejected(self):
        mutated = copy.deepcopy(self.original)
        mutated["provider_commits"].remove(OLD_BAKA)
        self.save(mutated)
        with self.assertRaisesRegex(CompatibilityGateError, "unreviewed addition"):
            self.assess()

    def test_catalog_mismatched_kernel_susfs_rejected(self):
        for key in ("kernel_commit", "susfs_commit"):
            mutated = copy.deepcopy(self.original)
            mutated[key] = "f" * 40
            self.save(mutated)
            with self.subTest(key=key), self.assertRaises(CompatibilityGateError):
                self.assess()
        self.save(self.original)

    def test_tampered_adapter_bytes_rejected(self):
        self.adapter.write_bytes(self.adapter.read_bytes() + b"\n#tampered")
        with self.assertRaisesRegex(CompatibilityGateError, "SHA256 differs"):
            self.assess()

    def test_adapter_path_traversal_rejected(self):
        mutated = copy.deepcopy(self.original)
        mutated["file"] = "../outside.patch"
        self.save(mutated)
        with self.assertRaisesRegex(CompatibilityGateError, "unsafe"):
            self.assess()

    def test_duplicate_manifest_json_key_rejected(self):
        self.catalog.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")
        with self.assertRaisesRegex(CompatibilityGateError, "duplicate"):
            self.assess()

    def test_bad_manifest_schema_rejected(self):
        mutated = copy.deepcopy(self.original)
        mutated["schema_version"] = 99
        self.save(mutated)
        with self.assertRaisesRegex(CompatibilityGateError, "schema"):
            self.assess()

    def test_symlinked_adapter_is_rejected_when_supported(self):
        original = self.base / "real.patch"
        self.adapter.rename(original)
        try:
            self.adapter.symlink_to(original)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unsupported on this host")
        with self.assertRaisesRegex(CompatibilityGateError, "symlinked adapter"):
            self.assess()


if __name__ == "__main__":
    unittest.main()
