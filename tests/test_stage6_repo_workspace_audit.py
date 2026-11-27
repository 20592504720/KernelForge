"""Read-only Repo workspace audit fixtures; no network or vendor sync."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_stage6_source_archive import fixture_lock

from kernelforge.repo_workspace_audit import audit_locked_workspace
from kernelforge.source_equivalence import SourceEquivalenceError


def git(root, *args):
    p = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)
    return p.stdout.strip()


def init_git(root, files):
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    git(root, "config", "user.name", "CI Fixture")
    git(root, "config", "user.email", "ci@kernelforge.example")
    for name, value in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value)
    git(root, "add", "-A")
    git(root, "commit", "-qm", "locked test fixture")
    return git(root, "rev-parse", "HEAD")


@unittest.skipUnless(os.name == "posix" and shutil.which("git"), "POSIX symlinks and Git required")
class RepoWorkspaceAuditTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.workspace = self.base / "workspace"
        self.kernel = self.workspace / "kernel_platform" / "common"
        self.manifest = self.base / "manifest-checkout"
        root_sha = init_git(self.workspace, {"README": "root project"})
        kernel_sha = init_git(self.kernel, {"README": "locked kernel tree"})
        xml = ("<manifest><project name='kernel' path='kernel_platform/common' revision='kernel-rev'>"
               "<linkfile src='.' dest='kernel_platform/.source_date_epoch_dir'/></project>"
               "<project name='root' path='./' revision='root-rev'/></manifest>")
        manifest_sha = init_git(self.manifest, {"pinned.xml": xml})
        (self.workspace / "kernel_platform" / ".source_date_epoch_dir").symlink_to("common", target_is_directory=True)
        self.lock = fixture_lock()
        self.lock["manifest_commit"] = manifest_sha
        self.lock["manifest_path"] = "pinned.xml"
        self.lock["source_lock"]["projects"][0]["commit_sha"] = kernel_sha
        self.lock["source_lock"]["projects"][0]["revision"] = "kernel-rev"
        self.lock["source_lock"]["projects"][1]["commit_sha"] = root_sha
        self.lock["source_lock"]["projects"][1]["revision"] = "root-rev"

    def audited(self):
        return audit_locked_workspace(self.lock, self.workspace, self.manifest)

    def test_root_project_two_pinned_heads_and_directory_linkfile(self):
        report = self.audited()
        self.assertEqual(report["project_count"], 2)
        self.assertEqual(report["manifest_git_identity"], "TESTED")
        self.assertEqual(report["locked_heads"], "TESTED")
        self.assertEqual(report["link_copyfile_count"], 1)
        self.assertEqual(report["link_copyfile_application"], "TESTED")
        self.assertEqual(report["workspace_overlay_byte_equivalence"], "UNTESTED")
        self.assertEqual(report["real_vendor_archive_git_tree_equivalence"], "UNTESTED")

    def test_missing_linkfile_is_blocked(self):
        (self.workspace / "kernel_platform" / ".source_date_epoch_dir").unlink()
        with self.assertRaisesRegex(SourceEquivalenceError, "not materialized"):
            self.audited()

    def test_wrong_linkfile_target_is_blocked(self):
        link = self.workspace / "kernel_platform" / ".source_date_epoch_dir"
        link.unlink()
        link.symlink_to("../README")
        with self.assertRaises(SourceEquivalenceError):
            self.audited()

    def test_wrong_source_head_is_blocked(self):
        self.lock["source_lock"]["projects"][0]["commit_sha"] = "a" * 40
        with self.assertRaisesRegex(SourceEquivalenceError, "project HEAD differs"):
            self.audited()

    def test_manifest_must_be_exact_pinned_head(self):
        (self.manifest / "other").write_text("moved")
        git(self.manifest, "add", "other")
        git(self.manifest, "commit", "-qm", "changed")
        with self.assertRaisesRegex(SourceEquivalenceError, "manifest checkout HEAD differs"):
            self.audited()

    def test_manifest_revision_mismatch_blocked(self):
        (self.manifest / "pinned.xml").write_text((self.manifest / "pinned.xml").read_text().replace("kernel-rev", "wrong"))
        git(self.manifest, "add", "pinned.xml")
        git(self.manifest, "commit", "-qm", "moved")
        self.lock["manifest_commit"] = git(self.manifest, "rev-parse", "HEAD")
        with self.assertRaisesRegex(SourceEquivalenceError, "manifest revision"):
            self.audited()

    def test_workspace_must_not_be_reused_as_manifest_repo(self):
        with self.assertRaisesRegex(SourceEquivalenceError, "manifest checkout HEAD differs"):
            audit_locked_workspace(self.lock, self.workspace, self.workspace)


if __name__ == "__main__":
    unittest.main()
