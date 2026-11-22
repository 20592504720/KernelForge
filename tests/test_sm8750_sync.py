"""Fast subprocess and report checks; no kernel source or network required."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
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
                                                                   'free_inodes': 2}):
            with self.assertRaisesRegex(RuntimeError, 'RUNNER_DISK_CAPACITY_INSUFFICIENT'):
                sync.run_monitored([sys.executable, '-c', 'import time; time.sleep(5)'],
                                   self.work, self.log, 2, 10, self.samples.append,
                                   interval=0.05, popen=capture)
        self.assertIsNotNone(processes[0].poll())
        self.assertTrue(self.samples)

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
        lock.write_text('{}', encoding='utf-8')
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


if __name__ == '__main__':
    unittest.main()
