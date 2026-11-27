"""Real repository layout and command-boundary regressions; no remote requests."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kernelforge.git_policy import (
    GitPolicyError,
    audit_repository,
    git_command,
    git_environment,
)


class GitPolicyFinalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.env = git_environment()

    def raw(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.base, env=self.env, stderr=subprocess.PIPE)

    def repository(self, bare=False, separate=False):
        repo = self.base / 'repo'
        extra = ['--bare'] if bare else []
        if separate:
            extra += ['--separate-git-dir', str(self.base / 'metadata')]
        self.raw('init', '-q', *extra, str(repo))
        return repo

    def test_bare_helper_rejected_and_passive_bare_supported(self):
        repo = self.repository(bare=True)
        layout = audit_repository(repo, self.env)
        if layout is None:
            self.fail("bare repository layout was not detected")
        self.assertIsNone(layout[2])
        result = subprocess.check_output(git_command(['rev-parse', '--is-bare-repository'], cwd=repo, env=self.env), cwd=repo, env=self.env)
        self.assertEqual(result.strip(), b'true')
        self.raw('config', '--file', str(repo / 'config'), 'core.sshCommand', 'untrusted')
        with self.assertRaises(GitPolicyError):
            git_command(['status'], cwd=repo, env=self.env)

    def test_local_bare_source_configuration_audited_before_clone(self):
        from kernelforge.source import SourceError, checkout
        repo = self.repository(bare=True)
        self.raw('config', '--file', str(repo / 'config'), 'uploadpack.packObjectsHook', 'untrusted-fixture')
        with self.assertRaisesRegex(SourceError, 'local source Git configuration'):
            checkout(repo.as_uri(), '0' * 40, self.base / 'destination')
        self.assertFalse((self.base / 'destination').exists())

    def test_separate_gitdir_is_audited(self):
        repo = self.repository(separate=True)
        layout = audit_repository(repo, self.env)
        if layout is None:
            self.fail("separate Git directory layout was not detected")
        self.assertEqual(layout[0], (self.base / 'metadata').resolve())
        self.raw('config', '--file', str(layout[0] / 'config'), 'include.path', '/untrusted')
        with self.assertRaises(GitPolicyError):
            audit_repository(repo, self.env)

    def test_real_submodule_gitdir_and_config_audited(self):
        repo = self.repository()
        self.raw('-C', str(repo), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture')
        parent = self.base / 'parent'
        self.raw('init', '-q', str(parent))
        self.raw('-C', str(parent), 'submodule', 'add', '--', repo.as_uri(), 'child')
        child = parent / 'child'
        layout = audit_repository(child, self.env)
        if layout is None:
            self.fail("submodule layout was not detected")
        gitdir, common, worktree = layout
        self.assertEqual(worktree, child.resolve())
        self.assertEqual(gitdir, common)
        self.assertEqual(gitdir, (parent / '.git/modules/child').resolve())
        self.raw('config', '--file', str(gitdir / 'config'), 'core.sshCommand', 'untrusted')
        with self.assertRaises(GitPolicyError):
            git_command(['status'], cwd=child, env=self.env)

    def test_local_percent_encoded_name_is_audited_once(self):
        from kernelforge.source import checkout
        repo = self.repository()
        self.raw('-C', str(repo), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture')
        renamed = self.base / 'source%20name'
        repo.rename(renamed)
        expected = self.raw('-C', str(renamed), 'rev-parse', 'HEAD').decode().strip()
        self.assertEqual(checkout(renamed.as_uri(), expected, self.base / 'destination'), expected)

    def test_dangling_git_marker_fails_closed(self):
        repo = self.base / 'repo'
        repo.mkdir()
        (repo / '.git').write_text('gitdir: missing\n', encoding='utf-8')
        with self.assertRaises((GitPolicyError, OSError)):
            audit_repository(repo, self.env)

    def test_worktree_local_config_audited(self):
        repo = self.repository()
        self.raw('-C', str(repo), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture')
        worktree = self.base / 'linked'
        self.raw('-C', str(repo), 'worktree', 'add', '-qb', 'linked', str(worktree))
        layout = audit_repository(worktree, self.env)
        if layout is None:
            self.fail("linked worktree layout was not detected")
        gitdir, common, _ = layout
        self.assertNotEqual(gitdir, common)
        self.raw('-C', str(repo), 'config', 'extensions.worktreeConfig', 'true')
        (gitdir / 'config.worktree').write_text('[core]\nsshCommand = untrusted\n', encoding='utf-8')
        with self.assertRaises(GitPolicyError):
            audit_repository(worktree, self.env)

    def test_locators_and_process_overrides_cannot_bypass_audit(self):
        repo = self.repository()
        for option in [['--git-dir', str(repo / '.git')], ['--work-tree=' + str(repo)], ['--config-env=core.sshCommand=PAYLOAD'], ['-c', 'core.sshCommand=payload'], ['-C' + str(repo)]]:
            with self.subTest(option=option), self.assertRaises(GitPolicyError):
                git_command([*option, 'status'], cwd=self.base, env=self.env)

    def test_native_ownership_refusal_precedes_explicit_repository_pin(self):
        repo = self.repository()
        native = subprocess.run

        def refuse_discovery(args, **kwargs):
            if args == ['git', 'rev-parse', '--absolute-git-dir']:
                self.assertEqual(kwargs['cwd'], repo.resolve())
                return subprocess.CompletedProcess(args, 128, b'', b'dubious ownership')
            return native(args, **kwargs)

        with patch('kernelforge.git_policy.subprocess.run', side_effect=refuse_discovery):
            with self.assertRaisesRegex(GitPolicyError, 'ownership check failed'):
                git_command(['status'], cwd=repo, env=self.env)

    def test_native_discovery_mismatch_precedes_explicit_repository_pin(self):
        repo = self.repository()
        native = subprocess.run

        def mismatched_discovery(args, **kwargs):
            if args == ['git', 'rev-parse', '--absolute-git-dir']:
                return subprocess.CompletedProcess(args, 0, str(self.base).encode('utf-8') + b'\n', b'')
            return native(args, **kwargs)

        with patch('kernelforge.git_policy.subprocess.run', side_effect=mismatched_discovery):
            with self.assertRaisesRegex(GitPolicyError, 'differs from audited repository'):
                git_command(['status'], cwd=repo, env=self.env)

    def test_only_global_C_changes_audit_target(self):
        repo = self.repository()
        args = git_command(['status', '--', '-C', 'not-a-directory'], cwd=repo, env=self.env)
        self.assertIn('--git-dir=' + str((repo / '.git').resolve()), args)

    def test_chained_C_and_nested_directory_pin_the_same_repository(self):
        repo = self.repository()
        (repo / 'nested').mkdir()
        command = git_command(['-C', str(repo), '-C', 'nested', 'rev-parse', '--absolute-git-dir'], cwd=self.base, env=self.env)
        actual = subprocess.check_output(command, cwd=self.base, env=self.env).decode().strip()
        self.assertEqual(Path(actual).resolve(), (repo / '.git').resolve())

    def test_unreviewed_config_and_credentials_are_not_echoed(self):
        repo = self.repository()
        for key in ['filter.secret-canary.clean', 'credential.secret-canary.helper', 'http.secret-canary.extraHeader', 'core.gitProxy', 'remote.origin.uploadpack', 'protocol.ext.allow']:
            config = repo / '.git/config'
            original = config.read_bytes()
            self.raw('config', '--file', str(config), key, 'secret-canary')
            with self.assertRaises(GitPolicyError) as caught:
                audit_repository(repo, self.env)
            self.assertNotIn('secret-canary', str(caught.exception))
            config.write_bytes(original)
        self.raw('config', '--file', str(config), 'remote.origin.url', 'https://user:secret-canary@example.invalid/repo')
        with self.assertRaises(GitPolicyError) as caught:
            audit_repository(repo, self.env)
        self.assertNotIn('secret-canary', str(caught.exception))

    @unittest.skipUnless(os.name != 'nt', 'POSIX symbolic-link fixture')
    def test_symlinked_config_rejected(self):
        repo = self.repository()
        config = repo / '.git/config'
        saved = self.base / 'config'
        config.rename(saved)
        config.symlink_to(saved)
        with self.assertRaises(GitPolicyError):
            audit_repository(repo, self.env)
