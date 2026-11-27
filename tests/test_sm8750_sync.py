"""Fast subprocess and report checks; no kernel source or network required."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from scripts import verify_sm8750_sync as sync


class MonitoredSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.log = self.work / 'sync.log'
        self.samples = []

    def run_child(self, code, *, timeout=2, reserve=0, callback=None):
        return sync.run_monitored([sys.executable, '-c', code], self.work, self.log,
                                  timeout, reserve, callback or self.samples.append,
                                  interval=0.05)

    def test_success_and_nonzero_exit(self):
        self.run_child("print('success marker')")
        self.assertIn('success marker', self.log.read_text(encoding='utf-8'))
        self.assertTrue(self.samples)
        with self.assertRaisesRegex(RuntimeError, 'command exited 7'):
            self.run_child('import sys; sys.exit(7)')

    def test_timeout_stops_process(self):
        processes = []
        def capture(*args, **kwargs):
            process = subprocess.Popen(*args, **kwargs)
            processes.append(process)
            return process
        with self.assertRaises(TimeoutError):
            sync.run_monitored([sys.executable, '-c', 'import time; time.sleep(5)'],
                               self.work, self.log, 0.15, 0, self.samples.append,
                               interval=0.05, popen=capture)
        self.assertIsNotNone(processes[0].poll())

    def test_low_space_stops_process_and_records_sample(self):
        processes = []
        def capture(*args, **kwargs):
            process = subprocess.Popen(*args, **kwargs)
            processes.append(process)
            return process
        with mock.patch.object(sync, 'disk_sample', return_value={'free_bytes': 1,
                                                                   'free_inodes': 2}), self.assertRaisesRegex(RuntimeError, 'RUNNER_DISK_CAPACITY_INSUFFICIENT'):
            sync.run_monitored([sys.executable, '-c', 'import time; time.sleep(5)'],
                               self.work, self.log, 2, 10, self.samples.append,
                               interval=0.05, popen=capture)
        self.assertIsNotNone(processes[0].poll())
        self.assertTrue(self.samples)

    def test_host_drive_low_space_stops_download_group(self):
        processes = []
        def capture(*args, **kwargs):
            process = subprocess.Popen(*args, **kwargs)
            processes.append(process)
            return process
        def sample(path, stage):
            return {'stage': stage, 'free_bytes': 1 if stage.endswith(':host') else 100}
        with mock.patch.object(sync, 'disk_sample', side_effect=sample), self.assertRaisesRegex(RuntimeError, 'HOST_DISK_CAPACITY_INSUFFICIENT'):
            sync.run_monitored([sys.executable, '-c', 'import time; time.sleep(5)'],
                               self.work, self.log, 2, 10, self.samples.append,
                               interval=0.05, popen=capture,
                               host_disk_path=self.work, host_reserve_bytes=50)
        self.assertIsNotNone(processes[0].poll())
        self.assertTrue(any(x['stage'].endswith(':host') for x in self.samples))

    def test_interrupt_stops_process(self):
        processes = []
        def capture(*args, **kwargs):
            process = subprocess.Popen(*args, **kwargs)
            processes.append(process)
            return process
        def interrupt(_):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            sync.run_monitored([sys.executable, '-c', 'import time; time.sleep(5)'],
                               self.work, self.log, 2, 0, interrupt,
                               interval=0.05, popen=capture)
        self.assertIsNotNone(processes[0].poll())

    def test_atomic_report_and_failed_preflight(self):
        report = self.work / 'report.json'
        sync.write_report(report, {'stage': 'sample', 'minimum_free_bytes': 123})
        self.assertEqual(json.loads(report.read_text())['minimum_free_bytes'], 123)
        lock = self.work / 'lock.json'
        invalid_locks = ['{}', 'null', '[]', '{',
                         '{"device_profile":"oneplus13-pjz110","source_lock":null}',
                         '{"device_profile":"oneplus13-pjz110","source_lock":{"all_refs_locked":true,"projects":null}}',
                         None]
        for content in invalid_locks:
            with self.subTest(content=content):
                if content is None:
                    lock.unlink()
                else:
                    lock.write_text(content, encoding='utf-8')
                result = sync.main(['--lock', str(lock), '--workspace', str(self.work / 'source'),
                                    '--report', str(report)])
                self.assertEqual(result, 1)
                data = json.loads(report.read_text())
                self.assertEqual(data['source_sync'], 'UNTESTED')
                self.assertEqual(data['failure_stage'], 'preflight')
                self.assertTrue(data['resource_samples'])

    def test_cleanup_is_scoped_and_sync_requires_explicit_event(self):
        workflow = yaml.safe_load((Path(__file__).resolve().parents[1] /
                                   '.github/workflows/source-audit.yml').read_text(encoding='utf-8'))
        manifest_steps = workflow['jobs']['manifest']['steps']
        sync_job = workflow['jobs']['locked-sync']
        self.assertNotIn('sudo rm', str(manifest_steps))
        condition = sync_job['if']
        self.assertIn("github.event_name == 'workflow_dispatch'", condition)
        self.assertIn('[run-sm8750-once]', condition)
        self.assertNotIn("github.event_name == 'pull_request'", condition)
        cleanup = next(step['run'] for step in sync_job['steps']
                       if step.get('name') == 'Reclaim only verified optional .NET preinstall')
        self.assertEqual(cleanup.count('sudo rm -rf'), 1)
        self.assertIn('dir=/usr/share/dotnet', cleanup)
        self.assertIn('--one-file-system', cleanup)
        self.assertIn('mountpoint -q "$dir"', cleanup)
        self.assertIn('RUNNER_ENVIRONMENT', cleanup)

    def _project(self, name='example', path='child', repository='https://example.org/repo.git'):
        return {'name': name, 'path': path, 'repository': repository,
                'commit_sha': '0' * 40}

    def test_root_project_requires_exact_manifest_identity_and_git_remote(self):
        root = self._project(sync.ROOT_PROJECT, './', sync.ROOT_REPOSITORY)
        subprocess.run(['git', 'init', '-q', str(self.work)], check=True)
        subprocess.run(['git', '-C', str(self.work), 'config', 'user.email', 'test@example.org'], check=True)
        subprocess.run(['git', '-C', str(self.work), 'config', 'user.name', 'Test'], check=True)
        subprocess.run(['git', '-C', str(self.work), 'commit', '-q', '--allow-empty', '-m', 'fixture'], check=True)
        subprocess.run(['git', '-C', str(self.work), 'remote', 'add', 'origin', sync.ROOT_REPOSITORY], check=True)
        root['commit_sha'] = subprocess.check_output(['git', '-C', str(self.work), 'rev-parse', 'HEAD'],
                                                   text=True).strip()
        row = sync.inspect_projects(self.work, [root])[0]
        self.assertTrue(row['matches_lock'])
        self.assertEqual(sync.inspect_project(self.work, {**root, 'name': 'impostor'})[0], 'UNSAFE_PATH')
        subprocess.run(['git', '-C', str(self.work), 'remote', 'set-url', 'origin',
                        'https://example.org/impostor.git'], check=True)
        self.assertEqual(sync.inspect_project(self.work, root)[0], 'PROJECT_IDENTITY_MISMATCH')

    def test_path_escape_and_missing_checkout_classification(self):
        for path in ('../escape', '/tmp/escape', 'C:/escape', 'child/../escape',
                     'child//escape', './', 'child\\escape'):
            self.assertEqual(sync.inspect_project(self.work, self._project(path=path))[0],
                             'UNSAFE_PATH', path)
        project = self._project()
        self.assertEqual(sync.inspect_project(self.work, project)[0], 'NOT_DOWNLOADED')
        (self.work / 'child').mkdir()
        self.assertEqual(sync.inspect_project(self.work, project)[0], 'INCOMPLETE_CHECKOUT')

    def test_symlink_escape_rejected(self):
        outside = self.work.parent / (self.work.name + '-outside')
        outside.mkdir(exist_ok=True)
        self.addCleanup(lambda: outside.rmdir())
        try:
            (self.work / 'child').symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlink creation unavailable')
        self.assertEqual(sync.inspect_project(self.work, self._project())[0], 'UNSAFE_PATH')

    def test_resume_refuses_missing_repo_metadata(self):
        report = self.work / 'report.json'
        with self.assertRaisesRegex(ValueError, 'intact .repo manifest'):
            sync.main(['--lock', str(self.work / 'missing.json'), '--workspace', str(self.work),
                       '--report', str(report), '--resume'])

    def test_missing_target_and_mismatched_head_are_distinct(self):
        child = self.work / 'child'
        subprocess.run(['git', 'init', '-q', str(child)], check=True)
        subprocess.run(['git', '-C', str(child), 'config', 'user.email', 'test@example.org'], check=True)
        subprocess.run(['git', '-C', str(child), 'config', 'user.name', 'Test'], check=True)
        subprocess.run(['git', '-C', str(child), 'commit', '-q', '--allow-empty', '-m', 'first'], check=True)
        first = subprocess.check_output(['git', '-C', str(child), 'rev-parse', 'HEAD'], text=True).strip()
        subprocess.run(['git', '-C', str(child), 'commit', '-q', '--allow-empty', '-m', 'second'], check=True)
        project = self._project()
        self.assertEqual(sync.inspect_projects(self.work, [project])[0]['diagnosis'],
                         'TARGET_COMMIT_MISSING')
        project['commit_sha'] = first
        row = sync.inspect_projects(self.work, [project])[0]
        self.assertEqual(row['diagnosis'], 'HEAD_MISMATCH')
        self.assertTrue(row['target_object_present'])

    def test_corrupt_git_marker_is_reported(self):
        child = self.work / 'child'
        child.mkdir()
        (child / '.git').write_text('gitdir: nowhere\n', encoding='utf-8')
        self.assertEqual(sync.inspect_projects(self.work, [self._project()])[0]['diagnosis'],
                         'GIT_METADATA_CORRUPT')

    def test_generated_manifest_is_verified_without_symlink_assumption(self):
        manifest_dir = self.work / '.repo/manifests'
        manifest_dir.mkdir(parents=True)
        git_env = sync.git_environment()
        subprocess.run(['git', 'init', '-q', str(manifest_dir)], check=True, env=git_env)
        subprocess.run(['git', '-C', str(manifest_dir), 'config', 'user.email',
                        'test@example.org'], check=True, env=git_env)
        subprocess.run(['git', '-C', str(manifest_dir), 'config', 'user.name', 'Test'],
                       check=True, env=git_env)
        source = manifest_dir / 'oneplus_13_b.xml'
        source.write_text('<manifest/>\n', encoding='utf-8')
        subprocess.run(['git', '-C', str(manifest_dir), 'add', 'oneplus_13_b.xml'],
                       check=True, env=git_env)
        subprocess.run(['git', '-C', str(manifest_dir), 'commit', '-q', '-m', 'locked'],
                       check=True, env=git_env)
        selected = self.work / '.repo/manifest.xml'
        selected.write_text('<manifest><include name="oneplus_13_b.xml"/></manifest>',
                            encoding='utf-8')
        lock = {'manifest_path': 'oneplus_13_b.xml'}
        sync.verify_manifest_selection(self.work, lock)
        selected.write_text('<manifest><include name="other.xml"/></manifest>', encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'differs from lock'):
            sync.verify_manifest_selection(self.work, lock)
        selected.write_text('<manifest><include name="oneplus_13_b.xml"/></manifest>',
                            encoding='utf-8')
        source.write_text('<manifest><project name="moved"/></manifest>', encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'local modifications'):
            sync.verify_manifest_selection(self.work, lock)


if __name__ == '__main__':
    unittest.main()
