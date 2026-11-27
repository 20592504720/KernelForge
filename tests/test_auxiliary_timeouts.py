"""Auxiliary queries fail within a deadline and preserve tool failures."""
import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kernelforge.objects import archive_members
from scripts import validate_upstreams as upstream
from scripts import verify_sm8750_sync as sync

ROOT = Path(__file__).resolve().parents[1]


class AuxiliaryTimeoutTests(unittest.TestCase):
    def test_tool_query_success_preserves_output_and_cwd(self):
        with tempfile.TemporaryDirectory() as folder:
            output = upstream.tool_output(
                [sys.executable, '-c', 'import os; print(os.getcwd())'], cwd=folder)
            self.assertEqual(Path(output.strip()).resolve(), Path(folder).resolve())

    def test_tool_query_nonzero_exit_is_not_success(self):
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            upstream.tool_output([sys.executable, '-c', 'raise SystemExit(7)'])
        self.assertEqual(caught.exception.returncode, 7)

    def test_tool_query_hung_child_is_killed_and_reaped(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'child-started'
            code = f'from pathlib import Path; import time; Path({str(marker)!r}).write_text("started"); time.sleep(30)'
            with self.assertRaises(subprocess.TimeoutExpired):
                upstream.tool_output([sys.executable, '-c', code], timeout=1)
            # check_output uses run(): TimeoutExpired is raised only after the
            # direct child has been killed and communicate() has completed.
            self.assertTrue(marker.is_file())

    def test_archive_timeout_and_nonzero_never_return_objects(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); archive = root / 'built-in.a'
            archive.write_bytes(b'!<thin>\n')
            for failure in (subprocess.TimeoutExpired(['llvm-ar'], 120),
                            subprocess.CalledProcessError(9, ['llvm-ar'])):
                with self.subTest(failure=type(failure).__name__):
                    with mock.patch('kernelforge.objects.subprocess.check_output', side_effect=failure) as query, \
                            self.assertRaises(type(failure)):
                        archive_members(archive, root)
                    self.assertEqual(query.call_args.kwargs['timeout'], 120)

    def test_manifest_query_timeout_retains_failed_report(self):
        if sys.platform == 'win32':
            self.skipTest('Linux-only repo sync entry; WSL exercises the failed report')
        lock = json.loads((ROOT / 'manifests/oneplus13-pjz110-sm8750-source.lock.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); lockfile = root / 'lock.json'; report = root / 'report.json'
            lockfile.write_text(json.dumps(lock), encoding='utf-8')
            with mock.patch.object(sync.shutil, 'which', return_value='repo'), \
                    mock.patch.object(sync, 'run_monitored') as monitored, \
                    mock.patch.object(sync, 'git_command', return_value=['git', 'rev-parse', 'HEAD']), \
                    mock.patch.object(sync.subprocess, 'check_output', side_effect=subprocess.TimeoutExpired('git', 15)) as query, \
                    mock.patch.object(sync, 'inspect_projects', return_value=[]):
                result = sync.main(['--lock', str(lockfile), '--workspace', str(root / 'work'), '--report', str(report)])
            self.assertEqual(result, 1)
            self.assertEqual(query.call_args.kwargs['timeout'], 15)
            self.assertEqual(monitored.call_count, 1)  # init only; sync never reached
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(data['source_sync'], 'UNTESTED')
            self.assertIn('timed out', data['failure_reason'])
            self.assertIn('ended_at', data)

    def test_auxiliary_call_sites_require_deadlines(self):
        # Prevent a future caller from bypassing the shared tool/Git helpers.
        tree = ast.parse((ROOT / 'scripts/validate_upstreams.py').read_text(encoding='utf-8'))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and
                 isinstance(n.func, ast.Attribute) and n.func.attr == 'check_output']
        self.assertEqual(len(calls), 1)
        self.assertTrue(any(k.arg == 'timeout' for k in calls[0].keywords))
        tree = ast.parse((ROOT / 'scripts/verify_sm8750_sync.py').read_text(encoding='utf-8'))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and
                 isinstance(n.func, ast.Attribute) and n.func.attr == 'check_output']
        self.assertEqual(len(calls), 1)
        self.assertTrue(any(k.arg == 'timeout' for k in calls[0].keywords))
