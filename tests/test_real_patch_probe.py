import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from kernelforge.real_patch_probe import check_real_source


class RealPatchProbeTests(unittest.TestCase):
    def test_clean_checkout_restored_after_success_repeat_and_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'
            root.mkdir()
            env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_CONFIG_')}
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True, env=env).strip()
            git('init', '-q')
            git('config', 'core.autocrlf', 'false')
            (root / 'Makefile').write_bytes(b'VERSION = 6\n')
            git('add', '.')
            git('-c', 'user.email=test@example.invalid', '-c', 'user.name=Test', 'commit', '-qm', 'baseline')
            sha = git('rev-parse', 'HEAD')
            report = check_real_source(root, Path(tmp) / 'work', Path(tmp) / 'report', sha)
            self.assertEqual(report['first_apply'], 'APPLIED')
            self.assertEqual(report['repeat_apply'], 'ALREADY_APPLIED')
            self.assertEqual(report['rollback'], 'TESTED')
            self.assertEqual(git('status', '--porcelain'), '')
            self.assertEqual((root / 'Makefile').read_bytes(), b'VERSION = 6\n')

    def test_rejects_dirty_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'
            root.mkdir()
            env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_CONFIG_')}
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True, env=env).strip()
            git('init', '-q')
            (root / 'Makefile').write_bytes(b'VERSION = 6\n')
            git('add', '.')
            git('-c', 'user.email=test@example.invalid', '-c', 'user.name=Test', 'commit', '-qm', 'baseline')
            (root / 'Makefile').write_bytes(b'VERSION = 5\n')
            with self.assertRaisesRegex(ValueError, 'clean source'):
                check_real_source(root, Path(tmp) / 'work', Path(tmp) / 'report', git('rev-parse', 'HEAD'))
