import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from kernelforge.patch_manager import apply_series, order


class PatchSeriesTests(unittest.TestCase):
    def test_create_delete_and_failure_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); root = base / 'source'; root.mkdir()
            def git(*args):
                env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_CONFIG_')}
                return subprocess.check_output(['git', *args], cwd=root, text=True, env=env).strip()
            git('init', '-q'); git('config', 'core.autocrlf', 'false')
            (root / 'old').write_bytes(b'old\n'); (root / 'bad').write_bytes(b'original\n')
            git('add', '.'); git('-c','user.email=test@example.invalid','-c','user.name=Test','commit','-qm','base')
            head=git('rev-parse','HEAD')
            def entry(key, body):
                path=base/(key+'.patch'); path.write_bytes(body.encode())
                return {'id':key,'feature':key,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'kernel_commits':[head]}
            add=entry('add','diff --git a/new b/new\nnew file mode 100644\n--- /dev/null\n+++ b/new\n@@ -0,0 +1 @@\n+new\n')
            delete=entry('delete','diff --git a/old b/old\ndeleted file mode 100644\n--- a/old\n+++ /dev/null\n@@ -1 +0,0 @@\n-old\n')
            bad=entry('bad','diff --git a/bad b/bad\n--- a/bad\n+++ b/bad\n@@ -1 +1 @@\n-wrong\n+changed\n')
            with self.assertRaisesRegex(ValueError,'text conflict'):
                apply_series(root,[add,delete,bad],base,kernel_commit=head)
            self.assertFalse((root/'new').exists()); self.assertEqual((root/'old').read_bytes(),b'old\n')
            self.assertEqual((root/'bad').read_bytes(),b'original\n')
            states=apply_series(root,[add,delete],base,kernel_commit=head)
            self.assertEqual([row['state'] for row in states],['APPLIED','APPLIED'])
            self.assertEqual([row['state'] for row in apply_series(root,[add,delete],base,kernel_commit=head)],['ALREADY_APPLIED']*2)

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
