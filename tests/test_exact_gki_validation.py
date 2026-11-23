"""Offline tests for manual exact-SHA GKI validation admission."""
import argparse
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.validate_upstreams import (
    BASELINE, choose_pinned_provider_commit, parse_exact_bakasu_commit,
)

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = '2734e0bc155759955880f5fb99be640fc5b92156'


class ExactGkiValidationTests(unittest.TestCase):
    def test_existing_fixed_profiles_are_unchanged(self):
        for provider in ('official', 'bakasu'):
            self.assertEqual(
                choose_pinned_provider_commit(provider, False, True, None),
                BASELINE[provider],
            )
            self.assertEqual(
                choose_pinned_provider_commit(provider, True, False, None),
                BASELINE[provider],
            )

    def test_exact_sha_case_and_allowed_combination(self):
        self.assertEqual(parse_exact_bakasu_commit(CANDIDATE.upper()), CANDIDATE)
        self.assertEqual(
            choose_pinned_provider_commit('bakasu', True, True, CANDIDATE),
            CANDIDATE,
        )

    def test_rejects_branches_tags_and_bad_sha(self):
        for bad in ('main', 'latest_branch', 'refs/heads/main', 'a' * 39,
                    'a' * 41, 'z' * 40, '-x', '', ' ' + CANDIDATE, CANDIDATE + '\n'):
            with self.subTest(value=bad), self.assertRaises(argparse.ArgumentTypeError):
                parse_exact_bakasu_commit(bad)

    def test_rejects_override_without_exact_bakasu_pinned_mode(self):
        for provider, susfs, pinned in (
            ('official', True, True), ('bakasu', False, True),
            ('bakasu', True, False), ('official', False, False),
        ):
            with self.subTest(provider=provider, susfs=susfs, pinned=pinned):
                with self.assertRaisesRegex(ValueError, 'requires'):
                    choose_pinned_provider_commit(provider, susfs, pinned, CANDIDATE)

    def test_rejects_invalid_sha_at_selection_boundary(self):
        with self.assertRaisesRegex(ValueError, 'invalid'):
            choose_pinned_provider_commit('bakasu', True, True, 'main')

    def test_invalid_cli_fails_before_workspace_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'must-not-create'
            cmd = [sys.executable, str(ROOT / 'scripts/validate_upstreams.py'),
                   '--provider', 'official', '--susfs', '--pinned-baseline',
                   '--bakasu-commit', CANDIDATE, '--workspace', str(folder)]
            result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('requires --provider bakasu', result.stderr)
            self.assertFalse(folder.exists())


if __name__ == '__main__':
    unittest.main()
