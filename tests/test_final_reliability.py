"""Chinese paths, raw-byte encoding, immutable evidence and interrupted recovery."""
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kernelforge.evidence import read_json, write_json
from scripts.environment_preflight import dependencies, path_budget


class EvidenceReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / '\u4e2d\u6587\u8def\u5f84'
        self.root.mkdir()

    def test_chinese_report_utf8_and_no_overwrite(self):
        path = self.root / '\u9a8c\u6536\u62a5\u544a.json'
        value = {'\u7ed3\u8bba': '\u6839\u56e0\u5df2\u4fee\u590d\uff0c\u4e2d\u6587\u5b57\u8282\u4fdd\u7559'}
        proof = write_json(path, value)
        self.assertEqual(read_json(path, proof['sha256']), value)
        self.assertIn('\u6839\u56e0\u5df2\u4fee\u590d'.encode('utf-8'), path.read_bytes())
        with self.assertRaises(FileExistsError):
            write_json(path, {'changed': True})
        self.assertEqual(read_json(path, proof['sha256']), value)

    def test_corrupt_evidence_rejected(self):
        path = self.root / 'report.json'
        proof = write_json(path, {'value': 'original'})
        path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            read_json(path, proof['sha256'])

    def test_interrupted_stage_does_not_replace_history(self):
        path = self.root / 'report.json'
        proof = write_json(path, {'state': 'complete'})
        pending = self.root / '.report.json-interrupted.pending'
        pending.write_bytes(b'{"state":')
        self.assertEqual(read_json(path, proof['sha256']), {'state': 'complete'})
        self.assertTrue(pending.exists())

    def test_subprocess_output_raw_bytes_survive_ascii_parent_locale(self):
        environment = dict(os.environ, PYTHONIOENCODING='ascii')
        result = subprocess.run([sys.executable, '-X', 'utf8', '-c', "import sys;sys.stdout.buffer.write('\\u4e2d\\u6587\\u65e5\\u5fd7'.encode('utf-8'))"],
                                cwd=self.root, env=environment, capture_output=True, check=True)
        self.assertEqual(result.stdout.decode('utf-8'), '\u4e2d\u6587\u65e5\u5fd7')
        self.assertEqual(hashlib.sha256(result.stdout).hexdigest(), hashlib.sha256('\u4e2d\u6587\u65e5\u5fd7'.encode('utf-8')).hexdigest())

    def test_missing_or_mismatched_locked_dependency_is_blocked(self):
        (self.root / 'requirements-dev.txt').write_text('jsonschema==0.0.0 --hash=sha256:fixture\n', encoding='utf-8')
        result = dependencies(self.root)
        self.assertEqual(result['status'], 'BLOCKED')

    def test_path_capability_probe_does_not_claim_external_tool_support(self):
        result = path_budget(self.root)
        self.assertGreater(result['probe_characters'], 260)
        self.assertEqual(result['external_tool_long_paths'], 'NOT_IMPLIED_BY_PYTHON_PROBE')
