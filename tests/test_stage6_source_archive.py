"""No network, production source, WSL2 workspace, or real kernel required."""
import copy
import hashlib
import io
import stat
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from kernelforge.source_archive import (
    ArchivePreflightError,
    inspect_archive,
    locked_projects,
    preflight_archive,
    require_git_patch_source,
)


def fixture_lock():
    return {
        "schema_version": 1, "device_profile": "oneplus13-pjz110",
        "manifest_repository": "https://github.com/OnePlusOSS/kernel_manifest.git",
        "manifest_commit": "a" * 40,
        "source_lock": {"project_count": 2, "all_refs_locked": True, "projects": [
            {"name": "kernel", "path": "kernel_platform/common",
             "repository": "https://github.com/example/kernel.git", "commit_sha": "b" * 40, "ref_state": "LOCKED"},
            {"name": "root", "path": "./", "repository": "https://github.com/example/root.git",
             "commit_sha": "c" * 40, "ref_state": "LOCKED"},
        ]},
    }


class SourceArchivePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lock = fixture_lock()

    def tar(self, members):
        path = self.root / "test.tar"
        with tarfile.open(path, "w") as handle:
            for name, content, kind in members:
                info = tarfile.TarInfo(name)
                if kind == "link":
                    info.type = tarfile.SYMTYPE
                    info.linkname = "../../escape"
                    handle.addfile(info)
                elif kind == "file":
                    info.size = len(content)
                    handle.addfile(info, io.BytesIO(content))
                else:
                    info.type = tarfile.DIRTYPE
                    handle.addfile(info)
        return path

    def zip(self, entries):
        path = self.root / "test.zip"
        with zipfile.ZipFile(path, "w") as handle:
            for name, content, link in entries:
                if link:
                    info = zipfile.ZipInfo(name)
                    info.create_system = 3
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
                    handle.writestr(info, content)
                else:
                    handle.writestr(name, content)
        return path

    def test_root_project_and_pinned_lock(self):
        self.assertEqual(len(locked_projects(self.lock)), 2)

    def test_duplicate_project_path_casefold_rejected(self):
        lock = copy.deepcopy(self.lock)
        lock["source_lock"]["projects"][1]["path"] = "KERNEL_PLATFORM/COMMON"
        with self.assertRaisesRegex(ArchivePreflightError, "colliding"):
            locked_projects(lock)

    def test_moving_sha_and_project_traversal_rejected(self):
        for field, value in (("commit_sha", "main"), ("path", "../escape")):
            lock = copy.deepcopy(self.lock)
            lock["source_lock"]["projects"][0][field] = value
            with self.assertRaises(ArchivePreflightError):
                locked_projects(lock)

    def test_mismatched_count_and_unlocked_ref_rejected(self):
        for key, value in (("project_count", 35), ("all_refs_locked", False)):
            lock = copy.deepcopy(self.lock)
            lock["source_lock"][key] = value
            with self.assertRaises(ArchivePreflightError):
                locked_projects(lock)

    def test_tar_path_traversal_rejected(self):
        for bad in ("../evil", "/absolute", "C:/drive", "a/./b", "a\\b"):
            path = self.tar([(bad, b"x", "file")])
            with self.subTest(bad=bad), self.assertRaises(ArchivePreflightError):
                inspect_archive(path, "tar")

    def test_windows_aliases_and_streams_rejected_on_all_hosts(self):
        for bad in ("root/file:stream", "root/NUL.txt", "root/COM1.log",
                    "root/name.", "root/name ", "root/bad?name", "root/bad|name"):
            for fmt in ("tar", "zip"):
                path = (self.tar([(bad, b"x", "file")]) if fmt == "tar"
                        else self.zip([(bad, b"x", False)]))
                with self.subTest(bad=bad, fmt=fmt), self.assertRaises(ArchivePreflightError):
                    inspect_archive(path, fmt)

    def test_windows_project_path_aliases_rejected(self):
        for bad in ("root/file:stream", "root/AUX", "root/name.", "root/name "):
            lock = copy.deepcopy(self.lock)
            lock["source_lock"]["projects"][0]["path"] = bad
            with self.subTest(bad=bad), self.assertRaises(ArchivePreflightError):
                locked_projects(lock)

    def test_tar_link_and_special_rejected(self):
        path = self.tar([("root/link", b"", "link")])
        with self.assertRaisesRegex(ArchivePreflightError, "link"):
            inspect_archive(path, "tar")

    def test_zip_symlink_rejected(self):
        path = self.zip([("link", b"../outside", True)])
        with self.assertRaisesRegex(ArchivePreflightError, "link"):
            inspect_archive(path, "zip")

    def test_zip_case_collision_and_file_ancestor_rejected(self):
        for entries in ([ ("a", b"1", False), ("A", b"2", False)],
                        [("a", b"1", False), ("a/b", b"2", False)]):
            path = self.zip(entries)
            with self.assertRaises(ArchivePreflightError):
                inspect_archive(path, "zip")

    def test_valid_archive_hash_and_identity(self):
        path = self.tar([("src/", b"", "dir"), ("src/file", b"safe", "file")])
        project = self.lock["source_lock"]["projects"][0]
        candidate = {"project": project["name"], "repository": project["repository"],
                     "path": project["path"], "commit_sha": project["commit_sha"],
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "archive_format": "tar"}
        result = preflight_archive(self.lock, candidate, path)
        self.assertEqual(result["archive_checksum"], "TESTED")
        self.assertEqual(result["git_tree_equivalence"], "UNTESTED")
        self.assertFalse(result["patch_manager_eligible"])
        self.assertEqual(result["members"], 2)
        candidate["commit_sha"] = "d" * 40
        with self.assertRaisesRegex(ArchivePreflightError, "commit_sha"):
            preflight_archive(self.lock, candidate, path)

    def test_tampered_archive_rejected(self):
        path = self.zip([("x", b"v1", False)])
        project = self.lock["source_lock"]["projects"][0]
        candidate = {"project": "kernel", "repository": project["repository"],
                     "path": project["path"], "commit_sha": project["commit_sha"],
                     "sha256": "0" * 64, "archive_format": "zip"}
        with self.assertRaisesRegex(ArchivePreflightError, "SHA256 mismatch"):
            preflight_archive(self.lock, candidate, path)

    def test_archive_not_eligible_for_patch_targets(self):
        require_git_patch_source("repo-git-lock-v1")
        with self.assertRaisesRegex(ArchivePreflightError, "Git checkout"):
            require_git_patch_source("pinned-archive-v1")


if __name__ == "__main__":
    unittest.main()
