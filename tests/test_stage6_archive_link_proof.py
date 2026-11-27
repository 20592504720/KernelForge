"""Stage 6.3 direct archive proof, no links ever materialized."""
from __future__ import annotations

import hashlib
import io
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

from kernelforge.archive_link_proof import verify_archive_link_tree
from kernelforge.source_equivalence import SourceEquivalenceError


def git(repo, *args, output=None):
    cmd = ["git", "-C", str(repo), *args]
    result = subprocess.run(cmd, stdout=subprocess.PIPE if output is None else output,
                            stderr=subprocess.PIPE, check=True)
    return result.stdout.decode().strip() if output is None else None


@unittest.skipUnless(os.name == "posix" and shutil.which("git"), "POSIX Git fixtures required")
class ArchiveLinkTreeProofTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.git_repo = self.base / "reference"
        self.git_repo.mkdir()
        git(self.git_repo, "init", "-q")
        git(self.git_repo, "config", "user.name", "CI Fixture")
        git(self.git_repo, "config", "user.email", "ci@example.org")
        (self.git_repo / "README").write_text("hello\n")
        (self.git_repo / "bin").mkdir()
        executable = self.git_repo / "bin" / "run"
        executable.write_text("#!/bin/sh\n")
        executable.chmod(0o755)
        (self.git_repo / "links").mkdir()
        (self.git_repo / "links" / "config").symlink_to("../README")
        (self.git_repo / "links" / "upstream").symlink_to("../../sibling")
        git(self.git_repo, "add", "-A")
        git(self.git_repo, "commit", "-qm", "pinned")
        self.commit = git(self.git_repo, "rev-parse", "HEAD")
        self.lock = {"schema_version": 1,"device_profile": "oneplus13-pjz110",
                     "manifest_repository": "https://github.com/OnePlusOSS/kernel_manifest.git",
                     "manifest_commit": "a" * 40,
                     "source_lock": {"project_count": 1, "all_refs_locked": True,
                       "projects": [{"name": "fixture", "path": "kernel_platform/common",
                                      "repository": "https://github.com/example/fixture.git",
                                      "commit_sha": self.commit, "ref_state": "LOCKED"}]}}
        self.archive = self.base / "archive.tar"
        with self.archive.open("wb") as out:
            git(self.git_repo, "archive", "--format=tar", "HEAD", output=out)

    def verify(self, *, path=None, fmt="tar", sha=None, **kw):
        path = path or self.archive
        return verify_archive_link_tree(self.lock, "fixture", path, self.git_repo,
                                        archive_format=fmt, expected_sha256=sha or hashlib.sha256(path.read_bytes()).hexdigest(), **kw)

    def mutate_tar(self, mutate):
        target = self.base / "modified.tar"
        entries = []
        with tarfile.open(self.archive) as inp:
            for m in inp:
                payload = b""
                if m.isfile():
                    stream = inp.extractfile(m)
                    if stream is None:
                        raise AssertionError("regular archive member has no content stream")
                    payload = stream.read()
                entries.append((m, payload))
        mutate(entries)
        with tarfile.open(target, "w") as out:
            for member, content in entries:
                out.addfile(member, io.BytesIO(content) if member.isfile() else None)
        return target

    def test_pinned_git_archive_with_symlinks_is_proved_without_extraction(self):
        r = self.verify()
        self.assertEqual(r["symlink_blobs_verified"], 2)
        self.assertEqual(r["regular_files_verified"], 2)
        self.assertEqual(r["git_tree_equivalence"], "TESTED")
        self.assertEqual(r["symlink_destinations_valid"], "UNTESTED")
        self.assertFalse(r["archive_extraction_safe"] == "TESTED")
        self.assertFalse(r["build_input_eligible"])

    def test_git_archive_zip_links(self):
        archive = self.base / "archive.zip"
        with archive.open("wb") as out:
            git(self.git_repo, "archive", "--format=zip", "HEAD", output=out)
        proof = self.verify(path=archive, fmt="zip")
        self.assertEqual(proof["symlink_blobs_verified"], 2)

    def test_modified_target_rejected(self):
        def mut(items):
            for m, contents in items:
                if m.issym() and m.name == "links/config":
                    m.linkname = "../other"
        a = self.mutate_tar(mut)
        with self.assertRaisesRegex(SourceEquivalenceError, "symlink target"):
            self.verify(path=a)

    def test_executable_mode_change_rejected(self):
        def mut(items):
            for m, _ in items:
                if m.name == "bin/run": m.mode = 0o644
        with self.assertRaisesRegex(SourceEquivalenceError, "mode differ"):
            self.verify(path=self.mutate_tar(mut))

    def test_missing_symlink_rejected(self):
        def mut(items): items[:] = [(m,d) for m,d in items if m.name != "links/config"]
        with self.assertRaisesRegex(SourceEquivalenceError, "file set differs"):
            self.verify(path=self.mutate_tar(mut))

    def test_duplicate_and_case_collision_rejected(self):
        def mut(items):
            m = tarfile.TarInfo("readme")
            m.size=1
            items.append((m,b"x"))
        with self.assertRaisesRegex(SourceEquivalenceError, "case-colliding"):
            self.verify(path=self.mutate_tar(mut))

    def test_traversal_member_rejected(self):
        def mut(items):
            m=tarfile.TarInfo("../outside")
            m.size=1
            items.append((m,b"x"))
        with self.assertRaisesRegex((SourceEquivalenceError), "unsafe"):
            self.verify(path=self.mutate_tar(mut))

    def test_hardlink_forbidden(self):
        def mut(items):
            m=tarfile.TarInfo("bad-hardlink")
            m.type=tarfile.LNKTYPE
            m.linkname="README"
            items.append((m,b""))
        with self.assertRaisesRegex(SourceEquivalenceError, "hardlinks"):
            self.verify(path=self.mutate_tar(mut))

    def test_sha256_mismatch_rejected(self):
        with self.assertRaisesRegex(SourceEquivalenceError, "SHA256"):
            self.verify(sha="0"*64)

    def test_wrong_commit_rejected(self):
        self.lock["source_lock"]["projects"][0]["commit_sha"]="f"*40
        with self.assertRaisesRegex(SourceEquivalenceError, "HEAD differs"):
            self.verify()

    def test_budget_enforced(self):
        with self.assertRaisesRegex(SourceEquivalenceError, "byte budget"):
            self.verify(max_bytes=2)
        with self.assertRaisesRegex(SourceEquivalenceError, "member budget"):
            self.verify(max_members=2)

    def test_export_ignore_is_detected_as_incomplete(self):
        # A tracked file omitted by git archive must not be silently accepted.
        (self.git_repo / ".gitattributes").write_text("README export-ignore\n")
        git(self.git_repo, "add", "-A")
        git(self.git_repo, "commit", "-qm", "ignore README on export")
        self.lock["source_lock"]["projects"][0]["commit_sha"]=git(self.git_repo, "rev-parse", "HEAD")
        path=self.base / "ignore.tar"
        with path.open("wb") as out: git(self.git_repo, "archive", "--format=tar", "HEAD", output=out)
        with self.assertRaisesRegex(SourceEquivalenceError, "file set differs"):
            self.verify(path=path)


if __name__ == "__main__": unittest.main()
