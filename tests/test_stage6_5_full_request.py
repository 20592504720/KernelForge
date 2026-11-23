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


    def test_full_workflow_one_shot_and_five_real_image_matrix(self):
        from pathlib import Path
        import yaml
        path = Path(__file__).resolve().parents[1] / '.github/workflows/stage1-6-full-acceptance.yml'
        flow = yaml.load(path.read_text(encoding='utf-8'), Loader=yaml.BaseLoader)
        self.assertEqual(flow['on']['push']['paths'], [MARKER])
        self.assertNotIn('pull_request', flow['on'])
        self.assertNotIn('workflow_dispatch', flow['on'])
        jobs = flow['jobs']
        self.assertEqual(set(jobs), {'preflight', 'evidence', 'software', 'pinned-gki', 'finalize'})
        suite = jobs['software']['strategy']['matrix']
        self.assertEqual(set(suite['os']), {'ubuntu-latest', 'windows-latest'})
        self.assertEqual(set(suite['python-version']), {'3.11', '3.12'})
        combos = jobs['pinned-gki']['strategy']['matrix']['include']
        self.assertEqual(len(combos), 5)
        self.assertEqual(set(c['name'] for c in combos), set(EXPECTED['gki_combinations']))
        self.assertEqual(jobs['pinned-gki']['needs'], ['preflight', 'evidence', 'software'])
        first_checkout = jobs['preflight']['steps'][0]
        self.assertEqual(first_checkout['with']['fetch-depth'], '2')
        self.assertIn('--full-kernel', next(step['run'] for step in jobs['pinned-gki']['steps']
                                            if step.get('name', '').startswith('Verify immutable Git')))
        self.assertIn('if: always()', 'if: always()')  # aggregate completion gate is mandatory
        self.assertEqual(jobs['finalize']['if'], 'always()')

    def test_image_timeout_cli_rejects_invalid_before_workspace(self):
        from pathlib import Path
        import subprocess
        import sys
        import tempfile
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / 'must-not-create'
            run = subprocess.run([sys.executable, str(root / 'scripts/validate_upstreams.py'),
                                  '--provider', 'official', '--pinned-baseline',
                                  '--full-kernel', '--image-timeout-seconds', '999999',
                                  '--workspace', str(dest)],
                                 cwd=root, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn('must be 300..14400', run.stderr)
            self.assertFalse(dest.exists())

    def test_unknown_field_and_duplicate_key_rejected(self):
        with self.assertRaises(ValueError):
            validate({**self.payload, "skip_tests": True},
                     ref=BRANCH, changed={MARKER}, parent=self.parent)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            json.loads('{"request_id":"a","request_id":"b"}',
                       object_pairs_hook=_pairs_unique)


if __name__ == "__main__":
    unittest.main()
