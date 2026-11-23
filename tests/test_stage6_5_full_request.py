"""Stage 1–6 request safety tests; no GitHub API requests or builds."""
import json
import unittest
from scripts.stage6_full_request import validate, _pairs_unique, EXPECTED, MARKER, BRANCH


class Stage65RequestTests(unittest.TestCase):
    def setUp(self):
        self.parent = "b" * 40
        self.payload = {**EXPECTED, "base_commit": self.parent}

    def test_only_exact_approved_base_commit_is_accepted(self):
        validate(self.payload, ref=BRANCH, changed={MARKER}, parent=self.parent)

    def test_wrong_branch_rejected(self):
        with self.assertRaises(ValueError):
            validate(self.payload, ref="refs/heads/main", changed={MARKER}, parent=self.parent)

    def test_altered_scope_or_full_image_disable_rejected(self):
        for key, val in (("scope", ["6"]), ("pinned_gki_full_image", False),
                         ("oki_vendor_build", True), ("sm8750_new_sync", True),
                         ("gki_combinations", ["official-susfs-on"])):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate({**self.payload, key: val}, ref=BRANCH,
                         changed={MARKER}, parent=self.parent)

    def test_extra_changed_file_rejected(self):
        with self.assertRaises(ValueError):
            validate(self.payload, ref=BRANCH,
                     changed={MARKER, "src/oneplus.c"}, parent=self.parent)

    def test_wrong_parent_or_invalid_sha_rejected(self):
        with self.assertRaises(ValueError):
            validate(self.payload, ref=BRANCH, changed={MARKER}, parent="a" * 40)
        with self.assertRaises(ValueError):
            validate({**self.payload, "base_commit": "abc"},
                     ref=BRANCH, changed={MARKER}, parent=self.parent)

    def test_unknown_field_and_duplicate_key_rejected(self):
        with self.assertRaises(ValueError):
            validate({**self.payload, "skip_tests": True},
                     ref=BRANCH, changed={MARKER}, parent=self.parent)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            json.loads('{"request_id":"a","request_id":"b"}',
                       object_pairs_hook=_pairs_unique)


if __name__ == "__main__":
    unittest.main()
