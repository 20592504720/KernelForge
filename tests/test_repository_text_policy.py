import unittest

from scripts.check_repository_text_policy import verify_checkout_matrix, verify_repo


class RepositoryTextPolicyTests(unittest.TestCase):
    def test_current_index_and_worktree_obey_text_and_digest_lock_policy(self):
        result = verify_repo()
        self.assertGreater(result["tracked_text_files_lf"], 0)
        self.assertEqual(result["locked_manifest_policy"], "BYTE_IDENTICAL_TO_HEAD_NO_FILTER")

    def test_autocrlf_and_core_eol_checkout_matrix_preserves_exact_bytes(self):
        result = verify_checkout_matrix()
        self.assertEqual(result["checkout_configurations"], 3)
        self.assertTrue(result["all_lf_text_and_lock_bytes_stable"])


if __name__ == "__main__":
    unittest.main()
