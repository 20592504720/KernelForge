"""Stage 7.4-O: measurement, hash parity and cache I/O regression."""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kernelforge.performance import PhaseTimer, file_sha256
from kernelforge.toolchains import manager


class PerformanceTests(unittest.TestCase):
    def test_monotonic_phases_and_failure(self):
        timer = PhaseTimer(clock=iter([100, 150, 210]).__next__)
        timer.start("source")
        timer.start("compile")
        report = timer.finish(success=False)
        self.assertEqual(report["total_ns"], 110)
        self.assertEqual(report["phases"], [
            {"phase": "source", "duration_ns": 50, "status": "success"},
            {"phase": "compile", "duration_ns": 60, "status": "failure"},
        ])
        with self.assertRaises(RuntimeError):
            timer.finish(success=True)

    def test_successful_phase(self):
        timer = PhaseTimer(clock=iter([10, 20]).__next__)
        timer.start("artifact")
        self.assertEqual(timer.finish(success=True)["phases"][0]["status"], "success")

    def test_streaming_hash_matches_bytes_without_read_bytes(self):
        data = b"test" * 700000
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "Image"
            target.write_bytes(data)
            expected = hashlib.sha256(data).hexdigest()
            with patch.object(Path, "read_bytes", side_effect=AssertionError("unbounded read")):
                self.assertEqual(file_sha256(target), expected)

    def test_combined_proof_matches_legacy_and_strict_reads_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a").mkdir()
            (root / "a" / "z").write_bytes(b"inner")
            (root / "a.txt").write_bytes(b"other")
            (root / "B").write_bytes(b"third")
            (root / "empty").mkdir()
            strict = manager._trusted_tree_digest(root)
            legacy = manager._tree_digest(root)
            with patch.object(manager, "_digest", wraps=manager._digest) as read:
                self.assertEqual(manager._tree_proofs(root, include_legacy=True), (strict, legacy))
                self.assertEqual(read.call_count, 3)

    @unittest.skipIf(os.name == "nt", "POSIX executable bits")
    def test_executable_bit_changes_strict_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "compiler"
            target.write_bytes(b"data")
            target.chmod(0o600)
            before = manager._tree_proofs(root, include_legacy=True)
            target.chmod(0o700)
            after = manager._tree_proofs(root, include_legacy=True)
            self.assertNotEqual(before[0], after[0])
            self.assertEqual(before[1], after[1])

    def test_combined_proof_rejects_hardlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "compiler"
            target.write_bytes(b"data")
            try:
                os.link(target, root / "alias")
            except (OSError, NotImplementedError):
                self.skipTest("hardlink unavailable")
            with self.assertRaises(ValueError):
                manager._tree_proofs(root, include_legacy=True)

    def test_combined_proof_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "compiler"
            target.write_bytes(b"data")
            try:
                (root / "alias").symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            with self.assertRaises(ValueError):
                manager._tree_proofs(root, include_legacy=True)
