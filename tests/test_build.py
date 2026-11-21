import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kernelforge.build import BuildError, GkiAdapter, VendorAdapter, run_build
from kernelforge.source import SourceError, checkout
from kernelforge.toolchain import ToolchainError, check_tools


def git(cwd, *args):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_CONFIG_")}
    result = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"git {args[0]} fixture failed: {result.stderr.strip()}")
    return result.stdout.strip()


def make_repo(root):
    repo = root / "upstream"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "KernelForge tests")
    git(repo, "config", "user.email", "tests@example.invalid")
    (repo / "README").write_text("fixture source\n")
    git(repo, "add", "README")
    git(repo, "commit", "-m", "fixture")
    sha = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "v1.0")
    return repo, sha


class SourceCheckoutTests(unittest.TestCase):
    def test_branch_tag_and_pinned_commit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); repo, sha = make_repo(root)
            for ref in ("main", "v1.0", sha):
                destination = root / ("checkout-" + ref[:6])
                self.assertEqual(checkout(repo.as_uri(), ref, destination), sha)
                self.assertEqual(git(destination, "rev-parse", "HEAD"), sha)

    def test_invalid_repository_rejected_without_creating_destination(self):
        with tempfile.TemporaryDirectory() as td:
            destination = Path(td) / "checkout"
            with self.assertRaisesRegex(SourceError, "unsupported repository URL"):
                checkout("not a remote", "main", destination)
            self.assertFalse(destination.exists())

    def test_missing_ref_failure_cleans_created_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); repo, _ = make_repo(root); destination = root / "bad-checkout"
            with self.assertRaisesRegex(SourceError, "not found"):
                checkout(repo.as_uri(), "missing-ref", destination)
            self.assertFalse(destination.exists())

    def test_nonempty_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); destination = root / "existing"; destination.mkdir()
            marker = destination / "keep.txt"; marker.write_text("keep")
            with self.assertRaisesRegex(SourceError, "refusing to overwrite"):
                checkout("https://github.com/example/kernel.git", "main", destination)
            self.assertEqual(marker.read_text(), "keep")

    def test_git_network_timeout_is_reported_and_cleaned(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); repo, _ = make_repo(root); destination = root / "timeout"
            def clone_then_timeout(args, cwd=None, timeout=300):
                if args[0] == "clone":
                    Path(args[-1]).mkdir()
                    return ""
                raise SourceError("Git operation timed out")
            with patch("kernelforge.source._run_git", side_effect=clone_then_timeout):
                with self.assertRaisesRegex(SourceError, "timed out"):
                    checkout(repo.as_uri(), "main", destination)
            self.assertFalse(destination.exists())


class ToolchainTests(unittest.TestCase):
    def test_missing_tool_has_actionable_error(self):
        with patch("kernelforge.toolchain.shutil.which", return_value=None):
            with self.assertRaisesRegex(ToolchainError, "not found"):
                check_tools([{"name": "clang"}])

    def test_minimum_version_enforced(self):
        completed = subprocess.CompletedProcess(["clang"], 0, "clang version 12.0.0\n", "")
        with patch("kernelforge.toolchain.shutil.which", return_value=sys.executable), patch("kernelforge.toolchain.subprocess.run", return_value=completed):
            with self.assertRaisesRegex(ToolchainError, "too old"):
                check_tools([{"name": "clang", "minimum": "14.0"}])


class AdapterTests(unittest.TestCase):
    def test_gki_and_vendor_have_separate_args_targets_environment_and_directories(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td); out = source / "out"; out.mkdir(); vendor = source / "vendor"; vendor.mkdir()
            config = {"build": {"mode": "gki", "jobs": 8,
                "gki": {"system": "kleaf", "argv": ["bazel", "run", "{jobs}"], "directory": ".", "targets": ["//gki:dist"], "environment": {"GKI_FLAG": "1"}},
                "vendor": {"argv": ["./build-device", "{defconfig}"], "directory": "vendor", "targets": ["vendor-kernel"], "environment": {"VENDOR_FLAG": "1"}}},
                "defconfig": "device_defconfig", "artifacts": {"paths": ["Image"]}}
            gp = GkiAdapter().plan(source, out, config); vp = VendorAdapter().plan(source, out, config)
            self.assertEqual(gp.argv, ["bazel", "run", "8"]); self.assertEqual(gp.targets, ["//gki:dist"])
            self.assertEqual(gp.environment, {"GKI_FLAG": "1"}); self.assertEqual(gp.cwd, source)
            self.assertEqual(vp.argv, ["./build-device", "device_defconfig"]); self.assertEqual(vp.targets, ["vendor-kernel"])
            self.assertEqual(vp.environment, {"VENDOR_FLAG": "1"}); self.assertEqual(vp.cwd, vendor)

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); out = root / "out"; out.mkdir()
            cfg = {"build": {"mode":"vendor", "jobs":1, "vendor":{"argv":["make"],"directory":"../escape"}}, "artifacts":{"paths":[]}}
            with self.assertRaisesRegex(BuildError, "escapes"):
                VendorAdapter().plan(root, out, cfg)

    def test_workspace_lock_prevents_overlapping_builds(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); root.mkdir(exist_ok=True); (root/".kernelforge-build.lock").write_text("pid=1")
            with self.assertRaisesRegex(BuildError, "lock exists"):
                run_build({}, root, root/"out")


class BuildExecutionTests(unittest.TestCase):
    def _config(self, repository, ref, code, timeout=10, patterns=None):
        return {"schema_version":1,"device":{"id":"fixture"},"kernel_version":"6.1",
          "source":{"repository":repository.as_uri(),"ref":ref,"timeout_seconds":10},
          "toolchain":{"required":[{"name":Path(sys.executable).name,"path":sys.executable}]},
          "build":{"mode":"vendor","jobs":1,"timeout_seconds":timeout,"gki":{"system":"kleaf","argv":["false"]},
                    "vendor":{"argv":[sys.executable,"-c",code],"directory":".","targets":["fixture-target"]}},
          "artifacts":{"paths":patterns if patterns is not None else ["Image"],"require_at_least_one":True}}

    def test_success_report_logs_and_artifact_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); repo,sha=make_repo(root); out=root/"artifacts"
            cfg=self._config(repo,sha,"from pathlib import Path; Path('Image').write_bytes(b'kernel-fixture')")
            report=run_build(cfg,root/"work",out)
            self.assertEqual(report["source"]["commit_sha"],sha)
            self.assertEqual(report["build"]["status"],"success")
            self.assertEqual(report["artifacts"][0]["sha256"],hashlib.sha256(b"kernel-fixture").hexdigest())
            self.assertTrue((out/"build.log").is_file())
            saved=json.loads((out/"build-report.json").read_text())
            self.assertEqual(saved["build"]["exit_status"],0)
            for field in ("kernelforge_version", "device", "kernel_version", "build_type", "source", "toolchain", "build", "artifacts"):
                self.assertIn(field, saved)
            self.assertTrue(saved["build"]["started_at"] and saved["build"]["ended_at"])

    def test_command_failure_writes_failure_report(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); repo,sha=make_repo(root); out=root/"out"
            cfg=self._config(repo,sha,"raise SystemExit(7)")
            with self.assertRaisesRegex(BuildError,"exit code 7"):
                run_build(cfg,root/"work",out)
            report=json.loads((out/"build-report.json").read_text())
            self.assertEqual(report["build"]["status"],"failure"); self.assertEqual(report["build"]["exit_status"],7)

    def test_timeout_writes_failure_report(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); repo,sha=make_repo(root); out=root/"out"
            cfg=self._config(repo,sha,"import time; time.sleep(2)",timeout=1)
            with self.assertRaisesRegex(BuildError,"timed out"):
                run_build(cfg,root/"work",out)
            report=json.loads((out/"build-report.json").read_text())
            self.assertTrue(report["build"]["timed_out"]); self.assertEqual(report["build"]["exit_status"],124)

    def test_missing_artifact_fails_and_is_reported(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); repo,sha=make_repo(root); out=root/"out"
            cfg=self._config(repo,sha,"pass")
            with self.assertRaisesRegex(BuildError,"no configured artifact"):
                run_build(cfg,root/"work",out)
            self.assertEqual(json.loads((out/"build-report.json").read_text())["build"]["status"],"failure")

    def test_build_logs_never_inherit_secret_environment(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); repo,sha=make_repo(root); out=root/"out"
            cfg=self._config(repo,sha,"import os; from pathlib import Path; Path('Image').write_text('ok'); print(os.getenv('TEST_TOKEN','missing'))")
            with patch.dict("os.environ", {"TEST_TOKEN":"should-not-leak"}):
                run_build(cfg,root/"work",out)
            self.assertNotIn("should-not-leak",(out/"build.log").read_text())


if __name__ == "__main__":
    unittest.main()
