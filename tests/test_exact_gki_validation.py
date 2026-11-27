"""Offline tests for manual exact-SHA GKI validation admission."""
import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.stage5_exact_request import (
    EXPECTED,
    MARKER,
    REF,
    reject_duplicate_fields,
    validate_request,
)
from scripts.validate_upstreams import (
    BASELINE,
    choose_pinned_provider_commit,
    parse_exact_bakasu_commit,
    review_pinned_request,
    select_compile_patch,
)

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = '2734e0bc155759955880f5fb99be640fc5b92156'


class ExactGkiValidationTests(unittest.TestCase):
    def test_compile_patch_explicit_upstream_or_reviewed_adapter(self):
        workspace = Path('fixture-workspace')
        self.assertEqual(select_compile_patch({'compatibility_patch': None}, workspace),
                         workspace / 'upstreams/susfs/kernel_patches/50_add_susfs_in_gki-android14-6.1.patch')
        catalog = ROOT / 'patches/compat/susfs'
        reviewed = json.loads((catalog / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(select_compile_patch({'compatibility_patch': reviewed}, workspace),
                         catalog / reviewed['file'])

    def test_compile_patch_rejects_malformed_or_unreviewed_selection(self):
        for record in (None, [], {}, {'compatibility_patch': False},
                       {'compatibility_patch': {}}, {'compatibility_patch': {'file': ''}},
                       {'compatibility_patch': {'file': '../outside.patch'}},
                       {'compatibility_patch': {'file': 'C:\\outside.patch'}},
                       {'compatibility_patch': {'file': 'unreviewed.patch'}}):
            with self.subTest(record=record), self.assertRaises(ValueError):
                select_compile_patch(record, Path('fixture-workspace'))

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
            with self.subTest(provider=provider, susfs=susfs, pinned=pinned), self.assertRaisesRegex(ValueError, 'requires'):
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
            result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=20, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('requires --provider bakasu', result.stderr)
            self.assertFalse(folder.exists())

    def test_bad_cli_ref_fails_before_workspace_created(self):
        for bad in ('main', 'latest_branch', CANDIDATE[:12]):
            with self.subTest(value=bad), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / 'must-not-create'
                cmd = [sys.executable, str(ROOT / 'scripts/validate_upstreams.py'),
                       '--provider', 'bakasu', '--susfs', '--pinned-baseline',
                       '--bakasu-commit', bad, '--workspace', str(folder)]
                result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=20, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('40-hex', result.stderr)
                self.assertFalse(folder.exists())


    def test_stage64_admits_reviewed_pinned_combinations_before_fetch(self):
        for provider, sha in (
            ('official', BASELINE['official']),
            ('bakasu', BASELINE['bakasu']),
            ('bakasu', CANDIDATE),
        ):
            with self.subTest(provider=provider, sha=sha):
                report = review_pinned_request(provider, True, True, sha)
                self.assertEqual(report['status'], 'DECLARED_PINNED_TRIPLE_REVIEWED')
                self.assertFalse(report['release_eligible'])
                self.assertEqual(report['provider_commit'], sha)

    def test_stage64_rejects_current_unreviewed_bakasu_commit(self):
        current_unreviewed = '63ad1ea3a90455dee9d77163cdafb028d8a90416'
        with self.assertRaisesRegex(ValueError, 'not reviewed'):
            review_pinned_request('bakasu', True, True, current_unreviewed)

    def test_moving_branch_probe_never_inherits_pinned_admission(self):
        for provider in ('official', 'bakasu'):
            for pinned, susfs in ((False, True), (True, False)):
                report = review_pinned_request(provider, susfs, pinned, BASELINE[provider])
                self.assertFalse(report['release_eligible'])
                self.assertEqual(report['status'], 'NOT_ADMITTED_MOVING_OR_NO_SUSFS')

    def test_unreviewed_exact_sha_cli_fails_before_workspace_created(self):
        unknown_sha = '63ad1ea3a90455dee9d77163cdafb028d8a90416'
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'not-created'
            cmd = [sys.executable, str(ROOT / 'scripts/validate_upstreams.py'),
                   '--provider', 'bakasu', '--susfs', '--pinned-baseline',
                   '--bakasu-commit', unknown_sha, '--workspace', str(folder)]
            result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=20, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('not reviewed', result.stderr)
            self.assertFalse(folder.exists())

    def test_workflow_rejects_bad_sha_before_any_download_step(self):
        workflow = yaml.load(
            (ROOT / '.github/workflows/upstream-validation.yml').read_text(encoding='utf-8'),
            Loader=yaml.BaseLoader,
        )
        jobs = workflow['jobs']
        self.assertIn("inputs.exact_bakasu_commit == ''", jobs['sources']['if'])
        self.assertIn("inputs.exact_bakasu_commit != ''", jobs['exact_bakasu']['if'])
        first, *remaining = jobs['exact_bakasu']['steps']
        self.assertEqual(first['name'], 'Reject invalid SHA before checkout or dependency install')
        self.assertIn('^[0-9a-fA-F]{40}$', first['run'])
        self.assertIn('exit 2', first['run'])
        self.assertTrue(any('actions/checkout@' in step.get('uses', '') for step in remaining))
        self.assertTrue(any('pip install' in step.get('run', '') for step in remaining))

    def test_push_request_is_only_heavy_ci_branch_trigger(self):
        flow = yaml.load((ROOT / '.github/workflows/upstream-validation.yml').read_text(encoding='utf-8'),
                         Loader=yaml.BaseLoader)
        self.assertNotIn('pull_request', flow['on'])
        self.assertEqual(flow['on']['push']['branches'], ['stage1/initial-foundation'])
        self.assertEqual(flow['on']['push']['paths'], [MARKER])
        self.assertIn("github.event_name != 'push'", flow['jobs']['sources']['if'])
        exact = flow['jobs']['exact_bakasu']
        self.assertIn("github.event_name == 'push'", exact['if'])
        steps = exact['steps']
        self.assertEqual(steps[0]['name'], 'Reject invalid SHA before checkout or dependency install')
        idx = next(i for i, s in enumerate(steps) if 'stage5_exact_request.py' in s.get('run', ''))
        checkout = next(i for i, s in enumerate(steps) if 'actions/checkout@' in s.get('uses', ''))
        pip = next(i for i, s in enumerate(steps) if 'pip install' in s.get('run', ''))
        self.assertLess(checkout, idx)
        self.assertLess(idx, pip)
        self.assertIn(EXPECTED['provider_commit'], steps[0]['env']['BAKASU_COMMIT'])
        cmd = next(s['run'] for s in steps if s.get('name', '').startswith('Validate pinned BakaSU'))
        self.assertNotIn('--full-kernel', cmd)
        self.assertIn('--bakasu-commit', cmd)

    def test_request_marker_fail_closed_and_exact_version(self):
        validate_request(dict(EXPECTED), REF, {MARKER})
        for field, wrong in [('provider_commit', '0'*40), ('kernel_commit', '0'*40),
                             ('susfs_commit', '0'*40), ('full_kernel', True),
                             ('request_id', 'other'), ('schema_version', 2)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_request({**EXPECTED, field: wrong}, REF, {MARKER})
        for val, branch, changed in [
            (dict(EXPECTED), 'refs/heads/main', {MARKER}),
            (dict(EXPECTED), REF, set()),
            ({**EXPECTED, 'extra': 1}, REF, {MARKER}),
        ]:
            with self.assertRaises(ValueError):
                validate_request(val, branch, changed)

    def test_duplicate_keys_rejected_before_build(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            json.loads('{"request_id":"foo","request_id":"bar"}',
                       object_pairs_hook=reject_duplicate_fields)


if __name__ == '__main__':
    unittest.main()
