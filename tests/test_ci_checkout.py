"""Exact checkout cleanup must never authorize unknown Git configuration."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from kernelforge.git_policy import git_environment
from scripts.normalize_ci_checkout import normalize_checkout


class CheckoutNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        self.root, self.runner = base / 'repo', base / 'runner'
        self.root.mkdir()
        self.runner.mkdir()
        self.git('init', '-q')
        (self.root / 'sample').write_bytes(b'content\n')
        self.git('add', 'sample')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, env=git_environment(),
                              check=True, timeout=30, capture_output=True).stdout

    def test_only_reviewed_checkout_metadata_is_removed(self):
        self.git('config', '--local', 'gc.auto', '0')
        config = self.root / '.git' / 'config.worktree'
        for name in ('core.sparsecheckout', 'core.sparsecheckoutcone', 'index.sparse'):
            self.git('config', '--file', str(config), name, 'false')
        key = f'includeIf.gitdir:{(self.root / ".git").as_posix()}.path'
        target = self.runner / 'git-credentials-12345678-1234-1234-1234-123456789abc.config'
        target.write_bytes(b'fixture: must not be read or removed\n')
        self.git('config', '--local', key, str(target))
        self.assertEqual(normalize_checkout(self.root, self.runner), 1)
        self.assertEqual(target.read_bytes(), b'fixture: must not be read or removed\n')
        self.assertEqual((self.root / 'sample').read_bytes(), b'content\n')
        self.assertNotIn(b'includeif', self.git('config', '--local', '--no-includes', '--list').lower())

    def test_unknown_include_and_enabled_sparse_config_are_retained(self):
        key = f'includeIf.gitdir:{(self.root / ".git").as_posix()}.path'
        self.git('config', '--local', key, str(self.runner / 'unreviewed.config'))
        before = (self.root / '.git' / 'config').read_bytes()
        with self.assertRaisesRegex(ValueError, 'credential reference'):
            normalize_checkout(self.root, self.runner)
        self.assertEqual((self.root / '.git' / 'config').read_bytes(), before)
        self.git('config', '--local', '--unset-all', key)
        self.git('config', '--local', 'core.sparsecheckout', 'true')
        before = (self.root / '.git' / 'config').read_bytes()
        with self.assertRaisesRegex(ValueError, 'enabled checkout'):
            normalize_checkout(self.root, self.runner)
        self.assertEqual((self.root / '.git' / 'config').read_bytes(), before)

    def test_incomplete_index_is_not_admitted(self):
        self.git('update-index', '--skip-worktree', 'sample')
        with self.assertRaisesRegex(ValueError, 'dense and complete'):
            normalize_checkout(self.root, self.runner)


if __name__ == '__main__':
    unittest.main()
