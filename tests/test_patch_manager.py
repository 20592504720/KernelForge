import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from kernelforge.patch_manager import apply_series, order


class PatchSeriesTests(unittest.TestCase):
    def test_order_and_cycle(self):
        first = {"id": "a", "feature": "a"}
        second = {"id": "b", "feature": "b", "depends_on": ["a"]}
        self.assertEqual(order([second, first]), [first, second])
        with self.assertRaisesRegex(ValueError, "cyclic"):
            order([dict(first, depends_on=["b"]), second])

    def test_real_apply_duplicate_and_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "source"
            root.mkdir()

            def git(*args):
                env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_CONFIG_')}
                return subprocess.check_output(["git", *args], cwd=root, text=True, env=env).strip()

            git("init", "-q")
            for name in ("a", "b"):
                (root / name).write_bytes(b"before\n")
            git("add", ".")
            git("-c", "user.email=test@example.invalid", "-c", "user.name=Test", "commit", "-qm", "base")
            head = git("rev-parse", "HEAD")

            def entry(name, before):
                patch = base / f"{name}.patch"
                patch.write_bytes(f"diff --git a/{name} b/{name}\n--- a/{name}\n+++ b/{name}\n@@ -1 +1 @@\n-{before}\n+after\n".encode())
                return {"id": name, "feature": name, "file": patch.name,
                        "kernel_commits": [head], "sha256": hashlib.sha256(patch.read_bytes()).hexdigest()}

            first, bad = entry("a", "before"), entry("b", "wrong")
            with self.assertRaisesRegex(ValueError, "b: text conflict"):
                apply_series(root, [first, bad], base, kernel_commit=head)
            self.assertEqual((root / "a").read_bytes(), b"before\n")
            self.assertEqual(apply_series(root, [first], base, kernel_commit=head)[0]["state"], "APPLIED")
            self.assertEqual(apply_series(root, [first], base, kernel_commit=head)[0]["state"], "ALREADY_APPLIED")
