"""Pre-cost path admission and immutable Git configuration parsing regressions."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kernelforge.build import BuildError, run_build
from kernelforge.git_policy import _config, git_environment
from kernelforge.path_policy import require_external_paths
from kernelforge.source import SourceError, checkout
from kernelforge.toolchains.manager import ToolchainManager, ToolchainManagerError


class BoundaryReviewTests(unittest.TestCase):
    def test_git_parser_uses_checked_snapshot_when_path_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'config'
            original = b'[core]\n bare = false\n'
            path.write_bytes(original)
            native = subprocess.run

            def replace_before_parse(args, **kwargs):
                path.write_text('[include]\n path = untrusted\n', encoding='utf-8')
                self.assertEqual(args[args.index('--file') + 1], '-')
                self.assertEqual(kwargs['input'], original)
                return native(args, **kwargs)

            with patch('kernelforge.git_policy.subprocess.run', side_effect=replace_before_parse):
                self.assertEqual(_config(path, git_environment()), [('core.bare', 'false')])

    @unittest.skipUnless(os.name == 'nt', 'Windows external tool path admission')
    def test_path_rejection_precedes_checkout_download_and_directory_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).joinpath(*(['long-component-1234567890'] * 12))
            with patch('kernelforge.build._run_build') as build, self.assertRaisesRegex(BuildError, 'path budget'):
                run_build({}, root / 'work', root / 'out')
            build.assert_not_called()
            with patch('kernelforge.source._resolve_fetch_ref') as resolve, self.assertRaisesRegex(SourceError, 'path budget'):
                checkout('https://example.invalid/repo', 'main', root / 'source')
            resolve.assert_not_called()
            manager = ToolchainManager(root / 'cache')
            with patch.object(manager, '_validate'), patch.object(manager, '_cached') as cached, patch.object(manager, '_download_install') as download, self.assertRaisesRegex(ToolchainManagerError, 'path budget'):
                manager.prepare({'kind': 'llvm', 'name': 'fixture'})
            cached.assert_not_called()
            download.assert_not_called()
            self.assertFalse(root.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows UTF-16 path budget')
    def test_path_budget_counts_utf16_units(self):
        path = Path('C:/') / ('\U0001f600' * 120)
        with self.assertRaisesRegex(ValueError, 'path budget'):
            require_external_paths(path)
