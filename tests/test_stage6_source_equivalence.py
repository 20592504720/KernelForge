"""Stage 6.3 offline exact Git Tree and Repo layout negative tests."""
from __future__ import annotations

import copy
import hashlib
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_stage6_source_archive import fixture_lock

from kernelforge.source_equivalence import (
    SourceEquivalenceError,
    verify_archive_git_tree,
    workspace_plan,
)


def git(path: Path, *args: str, binary: bool = False):
    result = subprocess.run(["git", "-C", str(path), *args], capture_output=True,
                            text=not binary, check=True)
    return result.stdout if binary else result.stdout.strip()


@unittest.skipUnless(shutil.which("git"), "Git command required")
class EquivalenceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.git_dir = self.root / "reference"
        self.git_dir.mkdir()
        git(self.git_dir, "init", "-q")
        git(self.git_dir, "config", "user.email", "ci@kernel-forge.example")
        git(self.git_dir, "config", "user.name", "CI Fixture")
        (self.git_dir / "README.txt").write_bytes(b"pinned real Git blob\n")
        tool = self.git_dir / "bin" / "tool.sh"
        tool.parent.mkdir()
        tool.write_bytes(b"#!/bin/sh\necho hi\n")
        tool.chmod(0o755)
        git(self.git_dir, "add", "-A")
        git(self.git_dir, "commit", "-qm", "fixture")
        self.lock = fixture_lock()
        self.lock["source_lock"]["projects"][0]["commit_sha"] = git(self.git_dir, "rev-parse", "HEAD")
        self.stage = self.root / "archive"
        self.stage.mkdir()
        (self.stage / "README.txt").write_bytes((self.git_dir / "README.txt").read_bytes())
        staged_tool = self.stage / "bin" / "tool.sh"
        staged_tool.parent.mkdir()
        staged_tool.write_bytes(tool.read_bytes())
        staged_tool.chmod(0o755)

    def verify(self, **kw):
        return verify_archive_git_tree(self.lock, "kernel", self.stage, self.git_dir, **kw)

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_stage62_acquire_then_stage63_verify(self):
        from kernelforge.source_acquisition import acquire_archive

        class Response(io.BytesIO):
            def __init__(self, payload):
                super().__init__(payload)
                self.headers = {"Content-Length": str(len(payload))}

            def geturl(self):
                return "https://mirror.example.org/pinned.tar"

        prefix = "source-revision/"
        payload = git(self.git_dir, "archive", "--format=tar", "--prefix=" + prefix, "HEAD", binary=True)
        project = self.lock["source_lock"]["projects"][0]
        candidate = {"project": project["name"], "repository": project["repository"],
                     "path": project["path"], "commit_sha": project["commit_sha"],
                     "sha256": hashlib.sha256(payload).hexdigest(), "archive_format": "tar",
                     "archive_url": "https://mirror.example.org/pinned.tar"}
        staged = self.root / "acquired"
        acquired = acquire_archive(self.lock, candidate, staged, self.root / "cache",
                                   allowed_hosts={"mirror.example.org"},
                                   opener=lambda req, timeout: Response(payload))
        self.assertEqual(acquired["git_tree_equivalence"], "UNTESTED")
        proof = verify_archive_git_tree(self.lock, "kernel", staged, self.git_dir,
                                        archive_root="source-revision")
        self.assertEqual(proof["git_tree_equivalence"], "TESTED")
        self.assertEqual(proof["files_verified"], 2)
        self.assertFalse(proof["build_input_eligible"])

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_exact_real_git_objects_and_modes(self):
        proof = self.verify()
        self.assertEqual(proof["git_tree_equivalence"], "TESTED")
        self.assertEqual(proof["mode_equivalence"], "TESTED")
        self.assertEqual(proof["files_verified"], 2)
        self.assertEqual(len(proof["git_tree_sha"]), 40)
        self.assertFalse(proof["patch_manager_eligible"])
        self.assertFalse(proof["build_input_eligible"])
        self.assertEqual(proof["workspace_35_project_equivalence"], "UNTESTED")

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_modified_file_bytes_rejected(self):
        (self.stage / "README.txt").write_bytes(b"tamper")
        with self.assertRaisesRegex(SourceEquivalenceError, "file bytes differ"):
            self.verify()

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_missing_file_rejected(self):
        (self.stage / "README.txt").unlink()
        with self.assertRaisesRegex(SourceEquivalenceError, "file set differs"):
            self.verify()

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_extra_file_rejected(self):
        (self.stage / "rogue.txt").write_text("extra")
        with self.assertRaisesRegex(SourceEquivalenceError, "file set differs"):
            self.verify()

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_execute_bit_mismatch_rejected(self):
        (self.stage / "bin" / "tool.sh").chmod(0o644)
        with self.assertRaisesRegex(SourceEquivalenceError, "executable mode differs"):
            self.verify()

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_git_head_mismatch_rejected(self):
        self.lock["source_lock"]["projects"][0]["commit_sha"] = "d" * 40
        with self.assertRaisesRegex(SourceEquivalenceError, "Git HEAD differs"):
            self.verify()

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_moved_branch_not_accepted(self):
        (self.git_dir / "next.txt").write_text("new")
        git(self.git_dir, "add", "next.txt")
        git(self.git_dir, "commit", "-qm", "moved")
        with self.assertRaisesRegex(SourceEquivalenceError, "Git HEAD differs"):
            self.verify()

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_root_prefix_exact_matches(self):
        wrapped = self.root / "wrapped"
        self.stage.rename(wrapped)
        self.stage.mkdir()
        wrapped.rename(self.stage / "source-tag")
        proof = self.verify(archive_root="source-tag")
        self.assertEqual(proof["files_verified"], 2)
        with self.assertRaisesRegex(SourceEquivalenceError, "outside declared root"):
            self.verify(archive_root="wrong-tag")

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_prefix_is_not_allowed_to_hide_extra_files(self):
        wrapped = self.root / "wrapped"
        self.stage.rename(wrapped)
        self.stage.mkdir()
        wrapped.rename(self.stage / "source-tag")
        (self.stage / "evil.txt").write_text("hidden")
        with self.assertRaisesRegex(SourceEquivalenceError, "outside declared root"):
            self.verify(archive_root="source-tag")

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_staged_link_fails_closed(self):
        (self.stage / "badlink").symlink_to("README.txt")
        with self.assertRaisesRegex(SourceEquivalenceError, "symlink"):
            self.verify()

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_pinned_git_tree_link_fails_closed(self):
        (self.git_dir / "linked").symlink_to("README.txt")
        git(self.git_dir, "add", "linked")
        git(self.git_dir, "commit", "-qm", "link")
        self.lock["source_lock"]["projects"][0]["commit_sha"] = git(self.git_dir, "rev-parse", "HEAD")
        with self.assertRaisesRegex(SourceEquivalenceError, "links"):
            self.verify()

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_gitlink_submodule_type_fails_closed(self):
        git(self.git_dir, "update-index", "--add", "--cacheinfo", "160000," + "d" * 40 + ",fake-submodule")
        git(self.git_dir, "commit", "-qm", "gitlink")
        self.lock["source_lock"]["projects"][0]["commit_sha"] = git(self.git_dir, "rev-parse", "HEAD")
        with self.assertRaisesRegex(SourceEquivalenceError, "gitlinks"):
            self.verify()

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_export_ignore_and_export_subst_do_not_pass(self):
        attr = self.git_dir / ".gitattributes"
        attr.write_text("README.txt export-ignore\nbin/tool.sh export-subst\n")
        git(self.git_dir, "add", ".gitattributes")
        git(self.git_dir, "commit", "-qm", "export rules")
        self.lock["source_lock"]["projects"][0]["commit_sha"] = git(self.git_dir, "rev-parse", "HEAD")
        with self.assertRaisesRegex(SourceEquivalenceError, "file set differs"):
            self.verify()

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_export_subst_expanded_blob_rejected(self):
        (self.git_dir / "README.txt").write_bytes(b"$Format:%H$\n")
        (self.git_dir / ".gitattributes").write_text("README.txt export-subst\n")
        git(self.git_dir, "add", "-A")
        git(self.git_dir, "commit", "-qm", "subst")
        self.lock["source_lock"]["projects"][0]["commit_sha"] = git(self.git_dir, "rev-parse", "HEAD")
        # Real git-archive, not simulated substitution.
        tar = self.root / "export.tar"
        tar.write_bytes(git(self.git_dir, "archive", "--format=tar", "HEAD", binary=True))
        import tarfile
        shutil.rmtree(self.stage)
        self.stage.mkdir()
        with tarfile.open(tar) as z:
            for item in z:
                if item.isfile():
                    path = self.stage / item.name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    stream = z.extractfile(item)
                    if stream is None:
                        raise AssertionError("regular archive member has no content stream")
                    path.write_bytes(stream.read())
                    path.chmod(0o755 if item.mode & 0o111 else 0o644)
        with self.assertRaisesRegex(SourceEquivalenceError, "file bytes differ"):
            self.verify()

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_metadata_path_in_archive_rejected(self):
        (self.stage / ".git").mkdir()
        (self.stage / ".git" / "config").write_text("not allowed")
        with self.assertRaisesRegex(SourceEquivalenceError, "metadata paths"):
            self.verify()

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_comparison_budgets(self):
        with self.assertRaisesRegex(SourceEquivalenceError, "file-count budget"):
            self.verify(max_files=1)
        with self.assertRaisesRegex(SourceEquivalenceError, "byte budget"):
            self.verify(max_bytes=1)

    @unittest.skipUnless(os.name == "posix", "POSIX mode proof required")
    def test_nested_source_rejected(self):
        with self.assertRaisesRegex(SourceEquivalenceError, "must be separate"):
            verify_archive_git_tree(self.lock, "kernel", self.git_dir / "bin", self.git_dir)

    def test_modes_fail_closed_on_windows(self):
        if os.name == "posix":
            self.assertEqual(self.verify()["mode_equivalence"], "TESTED")
        else:
            with self.assertRaisesRegex(SourceEquivalenceError, "POSIX"):
                self.verify()


class ManifestPlanningTests(unittest.TestCase):
    def setUp(self):
        self.lock = fixture_lock()
        self.manifest = ("<manifest><project name='kernel' path='kernel_platform/common' revision='revision-x'>"
                         "<copyfile src='README' dest='readme-copy'/>"
                         "<linkfile src='docs/index' dest='link-here'/></project>"
                         "<project name='root' path='./' revision='root-branch'/></manifest>")
        self.lock["source_lock"]["projects"][0]["revision"] = "revision-x"
        self.lock["source_lock"]["projects"][1]["revision"] = "root-branch"

    def test_root_first_and_copy_link_declared_unverified(self):
        p = workspace_plan(self.lock, self.manifest)
        self.assertEqual(p["root_projects"], 1)
        self.assertEqual(p["mount_order"][0]["path"], "./")
        self.assertEqual(len(p["copyfile_linkfile"]), 2)
        self.assertEqual(p["copyfile_linkfile_application"], "UNTESTED")
        self.assertEqual(p["workspace_content_equivalence"], "UNTESTED")
        self.assertEqual(p["manifest_state"], "DECLARATIONS_CHECKED_UNAUTHENTICATED")

    def test_real_repo_style_linkfile_source_dot_declared(self):
        xml = self.manifest.replace("src='docs/index'", "src='.'")
        planned = workspace_plan(self.lock, xml)
        self.assertEqual(planned["copyfile_linkfile"][1]["src"], ".")
        self.assertEqual(planned["copyfile_linkfile_application"], "UNTESTED")

    def test_manifest_not_present_is_not_claimed(self):
        p = workspace_plan(self.lock)
        self.assertEqual(p["manifest_state"], "NOT_SUPPLIED")
        self.assertEqual(p["copyfile_linkfile"], [])

    def test_duplicate_directive_destination_rejected(self):
        xml = self.manifest.replace("link-here", "readme-copy")
        with self.assertRaisesRegex(SourceEquivalenceError, "duplicate"):
            workspace_plan(self.lock, xml)

    def test_unsafe_directive_paths_rejected(self):
        for invalid in ("../escape", "/etc/password", "foo/../evil", ".git/config"):
            xml = self.manifest.replace("src='README'", f"src='{invalid}'")
            with self.subTest(invalid=invalid), self.assertRaises(SourceEquivalenceError):
                workspace_plan(self.lock, xml)

    def test_malformed_and_external_entities_rejected(self):
        for xml in ("<manifest>", "<!DOCTYPE manifest><manifest/>", "<!ENTITY x 'foo'><manifest/>"):
            with self.subTest(xml=xml), self.assertRaises(SourceEquivalenceError):
                workspace_plan(self.lock, xml)

    def test_manifest_project_path_and_ref_mismatch_rejected(self):
        for xml in (self.manifest.replace("kernel_platform/common", "different"),
                    self.manifest.replace("revision-x", "different"),
                    self.manifest.replace("name='kernel'", "name='unknown'")):
            with self.subTest(xml=xml), self.assertRaises(SourceEquivalenceError):
                workspace_plan(self.lock, xml)

    def test_include_unresolved_rejected(self):
        xml = self.manifest.replace("<manifest>", "<manifest><include name='extra.xml'/>")
        with self.assertRaisesRegex(SourceEquivalenceError, "fully resolved"):
            workspace_plan(self.lock, xml)

    def test_nested_mounts_sorted_and_not_claimed_verified(self):
        lock = copy.deepcopy(self.lock)
        project = lock["source_lock"]["projects"][0]
        lock["source_lock"]["projects"].append({**project, "name": "kernel-child",
                                                    "path": "kernel_platform/common/drivers"})
        lock["source_lock"]["project_count"] = 3
        plan = workspace_plan(lock)
        self.assertEqual(plan["project_count"], 3)
        self.assertEqual(plan["nested_mounts"], [{"parent": "kernel_platform/common", "child": "kernel_platform/common/drivers"}])
        self.assertEqual(plan["project_file_collisions"], "UNTESTED")

    def test_case_duplicate_paths_preflight_rejected(self):
        lock = copy.deepcopy(self.lock)
        lock["source_lock"]["projects"][1]["path"] = "KERNEL_PLATFORM/COMMON"
        with self.assertRaises(ValueError):
            workspace_plan(lock)


if __name__ == "__main__":
    unittest.main()
