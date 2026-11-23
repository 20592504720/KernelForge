"""Offline Stage 6.2 acquisition/attack/rollback regression suite."""
import copy
import hashlib
import io
import json
import stat
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from kernelforge.source_acquisition import (
    SourceAcquisitionError, _RedirectPolicy, _checked_url,
    acquire_archive,
)
from kernelforge.source_archive import ArchivePreflightError
from test_stage6_source_archive import fixture_lock


class Stream(io.BytesIO):
    def __init__(self, data: bytes, *, actual_length=None, url="https://files.example.org/src.tar"):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data) if actual_length is None else actual_length)}
        self.url = url

    def geturl(self):
        return self.url


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.work = Path(t.name)
        self.cache = self.work / "cache"
        self.dest = self.work / "output"
        self.report = self.work / "report.json"
        self.lock = fixture_lock()
        self.project = self.lock["source_lock"]["projects"][0]
        self.payload = self.make_tar([("project/file.sh", b"#!/bin/sh\necho ok\n", "file", 0o755)])
        self.candidate = self.make_candidate(self.payload)

    def make_candidate(self, payload):
        return {"project": self.project["name"], "path": self.project["path"],
                "repository": self.project["repository"], "commit_sha": self.project["commit_sha"],
                "sha256": hashlib.sha256(payload).hexdigest(), "archive_format": "tar",
                "archive_url": "https://files.example.org/src.tar"}

    def make_tar(self, items):
        sink = io.BytesIO()
        with tarfile.open(fileobj=sink, mode="w") as archive:
            for name, data, kind, mode in items:
                item = tarfile.TarInfo(name)
                item.mode = mode
                if kind == "dir":
                    item.type = tarfile.DIRTYPE
                    archive.addfile(item)
                elif kind == "symlink":
                    item.type = tarfile.SYMTYPE
                    item.linkname = "../../escape"
                    archive.addfile(item)
                else:
                    item.size = len(data)
                    archive.addfile(item, io.BytesIO(data))
        return sink.getvalue()

    def run_acquire(self, payload=None, **kwargs):
        payload = self.payload if payload is None else payload
        return acquire_archive(self.lock, self.candidate, self.dest, self.cache,
                               allowed_hosts={"files.example.org"},
                               opener=lambda req, timeout: Stream(payload), report_path=self.report, **kwargs)

    def test_trusted_archive_quarantine_and_report(self):
        evidence = self.run_acquire()
        self.assertEqual((self.dest / "project/file.sh").read_bytes(), b"#!/bin/sh\necho ok\n")
        self.assertTrue(self.dest.exists())
        self.assertEqual(evidence["payload_integrity"], "TESTED")
        self.assertEqual(evidence["git_tree_equivalence"], "UNTESTED")
        self.assertFalse(evidence["build_input_eligible"])
        self.assertFalse(evidence["patch_manager_eligible"])
        self.assertEqual(json.loads(self.report.read_text()), evidence)

    def test_cache_hit_bypasses_network(self):
        self.run_acquire()
        self.dest.rename(self.work / "first")
        result = acquire_archive(self.lock, self.candidate, self.dest, self.cache,
                                 allowed_hosts={"files.example.org"},
                                 opener=lambda req, timeout: self.fail("network requested on cache hit"))
        self.assertTrue(result["cache_hit"])

    def test_modified_cached_archive_rejected(self):
        self.run_acquire()
        (self.cache / "sha256" / self.candidate["sha256"]).write_bytes(b"tampered")
        self.dest.rename(self.work / "first")
        with self.assertRaisesRegex(SourceAcquisitionError, "cached archive"):
            self.run_acquire()

    def test_different_payload_rejected_no_destination_or_cache_artifact(self):
        with self.assertRaisesRegex(SourceAcquisitionError, "SHA256 mismatch"):
            self.run_acquire(payload=b"evil")
        self.assertFalse(self.dest.exists())
        self.assertFalse((self.cache / "sha256" / self.candidate["sha256"]).exists())

    def test_truncated_download_header_rejected(self):
        with self.assertRaisesRegex(SourceAcquisitionError, "incomplete"):
            acquire_archive(self.lock, self.candidate, self.dest, self.cache,
                            allowed_hosts={"files.example.org"},
                            opener=lambda req, timeout: Stream(self.payload, actual_length=len(self.payload)+4))
        self.assertFalse(self.dest.exists())

    def test_download_budget_rejects_declared_size(self):
        with self.assertRaisesRegex(SourceAcquisitionError, "byte budget"):
            self.run_acquire(max_download_bytes=3)
        self.assertFalse(self.dest.exists())

    def test_zip_crc_corruption_rejected_even_when_sha_matches(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as z:
            z.writestr("file.txt", b"GOODCONTENT")
        invalid = buf.getvalue().replace(b"GOODCONTENT", b"EVILCONTENT")
        self.candidate = self.make_candidate(invalid)
        self.candidate["archive_format"] = "zip"
        with self.assertRaises(SourceAcquisitionError):
            self.run_acquire(payload=invalid)
        self.assertFalse(self.dest.exists())
        self.assertFalse(any(self.work.glob(".stage6-archive-*")))

    def test_tar_links_rejected_and_cleaned(self):
        bad = self.make_tar([("x", b"", "symlink", 0o777)])
        self.candidate = self.make_candidate(bad)
        with self.assertRaises((ArchivePreflightError, SourceAcquisitionError)):
            self.run_acquire(payload=bad)
        self.assertFalse(self.dest.exists())

    def test_path_traversal_rejected_before_promotion(self):
        bad = self.make_tar([("../outside.txt", b"x", "file", 0o644)])
        self.candidate = self.make_candidate(bad)
        with self.assertRaises((ArchivePreflightError, SourceAcquisitionError)):
            self.run_acquire(payload=bad)
        self.assertFalse(self.dest.exists())
        self.assertFalse((self.work / "outside.txt").exists())

    def test_case_conflict_and_nested_file_rejected(self):
        for entries in ([('A', b'a','file',0o644),('a', b'b','file',0o644)],
                        [('a', b'a','file',0o644),('a/b', b'b','file',0o644)]):
            payload = self.make_tar(entries)
            self.candidate = self.make_candidate(payload)
            with self.subTest(entries=entries), self.assertRaises((ArchivePreflightError, SourceAcquisitionError)):
                self.run_acquire(payload=payload)
            self.assertFalse(self.dest.exists())

    def test_expanded_size_budget_rollback(self):
        with self.assertRaisesRegex(SourceAcquisitionError, "extraction budget"):
            self.run_acquire(max_unpacked_bytes=5)
        self.assertFalse(self.dest.exists())

    def test_destination_existing_not_overwritten(self):
        self.dest.mkdir()
        (self.dest / "keep").write_text("original")
        with self.assertRaisesRegex(SourceAcquisitionError, "already exists"):
            self.run_acquire()
        self.assertEqual((self.dest / "keep").read_text(), "original")

    def test_identity_mismatch_fails_before_network(self):
        self.candidate["commit_sha"] = "d" * 40
        with self.assertRaisesRegex(SourceAcquisitionError, "identity"):
            self.run_acquire()
        self.assertFalse(self.cache.exists())

    def test_allowlist_required_and_wrong_host_rejected(self):
        with self.assertRaisesRegex(SourceAcquisitionError, "allowlist"):
            acquire_archive(self.lock,self.candidate,self.dest,self.cache,allowed_hosts=set())
        self.candidate["archive_url"] = "https://evil.org/abc.tar"
        with self.assertRaisesRegex(SourceAcquisitionError, "approved HTTPS"):
            self.run_acquire()

    def test_http_and_ip_literal_rejected(self):
        for host in ("http://files.example.org/x", "https://127.0.0.1/x",
                     "https://localhost/x", "https://files.example.org@evil.org/x"):
            with self.subTest(host=host), self.assertRaises(SourceAcquisitionError):
                _checked_url(host, frozenset({"files.example.org", "localhost", "127.0.0.1"}))

    def test_redirect_policy_refuses_disallowed_host(self):
        policy = _RedirectPolicy(frozenset({"files.example.org"}))
        from urllib.request import Request
        request = Request("https://files.example.org/src.tar")
        with self.assertRaises(SourceAcquisitionError):
            policy.redirect_request(request, None, 302, "Moved", {}, "http://evil.org/x")
        with self.assertRaises(SourceAcquisitionError):
            policy.redirect_request(request, None, 302, "Moved", {}, "https://evil.org/x")

    def test_fake_opener_final_url_checked(self):
        with self.assertRaises(SourceAcquisitionError):
            acquire_archive(self.lock, self.candidate, self.dest, self.cache,
                            allowed_hosts={"files.example.org"},
                            opener=lambda req, timeout: Stream(self.payload,url="https://bad.org/redirect"))
        self.assertFalse(self.dest.exists())

    def test_invalid_configured_budget_and_nested_cache_rejected(self):
        with self.assertRaises(SourceAcquisitionError):
            self.run_acquire(max_members=0)
        with self.assertRaisesRegex(SourceAcquisitionError, "separate"):
            acquire_archive(self.lock,self.candidate,self.dest,self.dest / "cache",allowed_hosts={"files.example.org"})

    def test_root_project_identity_and_35_project_lock(self):
        root = self.lock["source_lock"]["projects"][1]
        self.assertEqual(root["path"], "./")
        from kernelforge.source_archive import locked_projects
        self.assertEqual(len(locked_projects(self.lock)), 2)

if __name__ == "__main__":
    unittest.main()
