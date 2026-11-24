"""Offline security regression tests; no real source, external download or build."""
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from kernelforge.build import BuildError, _artifacts, run_build
from kernelforge.security import redact_diagnostic, redact_tree, publish_redacted_log
from kernelforge.source import SourceError, _run_git
from kernelforge.toolchains.archive import ArchiveError, extract
from kernelforge.toolchains.download import DownloadError, download
from kernelforge.validation import validate_manifests

ROOT = Path(__file__).resolve().parents[1]


class ArtifactSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.output = self.root / "output"
        self.source.mkdir()
        self.output.mkdir()
        (self.source / "Image").write_bytes(b"test-image" * 200000)

    def test_streamed_artifact_integrity(self):
        records = _artifacts(self.source, self.output, ["Image"])
        content = (self.output / "Image").read_bytes()
        self.assertEqual(records[0]["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(records[0]["size"], len(content))

    def test_existing_regular_target_never_overwritten(self):
        target = self.output / "Image"
        target.write_bytes(b"keep")
        with self.assertRaises(BuildError):
            _artifacts(self.source, self.output, ["Image"])
        self.assertEqual(target.read_bytes(), b"keep")

    @unittest.skipIf(os.name == "nt", "symlink privileges not guaranteed on Windows")
    def test_existing_symlink_does_not_modify_external_file(self):
        outside = self.root / "external"
        outside.write_bytes(b"keep")
        (self.output / "Image").symlink_to(outside)
        with self.assertRaises(BuildError):
            _artifacts(self.source, self.output, ["Image"])
        self.assertEqual(outside.read_bytes(), b"keep")
        self.assertTrue((self.output / "Image").is_symlink())

    def test_nonempty_output_refused_before_checkout(self):
        (self.output / "build.log").write_bytes(b"keep")
        with patch("kernelforge.build.checkout") as checkout:
            with self.assertRaisesRegex(BuildError, "not empty"):
                run_build({}, self.root / "work", self.output)
            checkout.assert_not_called()
        self.assertEqual((self.output / "build.log").read_bytes(), b"keep")

    def test_reserved_report_names_rejected(self):
        (self.source / "build.log").write_text("fixture")
        with self.assertRaisesRegex(BuildError, "reserved evidence"):
            _artifacts(self.source, self.output, ["build.log"])

    def test_oneplus13_generic_build_fails_closed_before_checkout(self):
        config = {"device_profile": "oneplus13-pjz110", "build": {"mode": "vendor"}}
        with patch("kernelforge.build.checkout") as checkout:
            with self.assertRaisesRegex(BuildError, "Repo/Kleaf build admission is BLOCKED"):
                run_build(config, self.root / "work", self.output)
            checkout.assert_not_called()


class PatchPathSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.directory = self.root / "patches" / "6.6"
        self.directory.mkdir(parents=True)
        (self.root / "schemas").mkdir()
        schema_path = ROOT / "schemas" / "patch-manifest.schema.json"
        shutil.copyfile(schema_path, self.root / "schemas" / schema_path.name)
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))

    def entry(self, file):
        return {"id": "probe", "file": file, "sha256": hashlib.sha256(b"fixture").hexdigest(),
                "source": "https://example.invalid/reviewed", "enabled": True}

    def manifest(self, file):
        return {"schema_version": 1, "kernel": "6.6", "patches": [self.entry(file)]}

    def test_schema_rejects_nonportable_and_traversal_paths(self):
        validator = Draft202012Validator(self.schema)
        for name in ("../../../outside.patch", "sub/../outside.patch", "sub/./file.patch",
                     "/outside.patch", "C:/outside.patch", r"sub\file.patch", "sub/file:ads.patch"):
            with self.subTest(name=name):
                self.assertTrue(list(validator.iter_errors(self.manifest(name))))
        validator.validate(self.manifest("sub/valid.patch"))

    def test_malformed_entry_does_not_raise_keyerror(self):
        (self.directory / "manifest.json").write_text(json.dumps({
            "schema_version": 1, "kernel": "6.6", "patches": [{"id": "probe"}]}))
        self.assertTrue(validate_manifests(self.root))

    def test_traversal_rejected_before_file_read(self):
        (self.directory / "manifest.json").write_text(json.dumps(self.manifest("../../outside.patch")))
        (self.root / "outside.patch").write_bytes(b"fixture")
        self.assertTrue(validate_manifests(self.root))

    @unittest.skipIf(os.name == "nt", "symlink privileges not guaranteed on Windows")
    def test_symlinked_patch_is_rejected(self):
        outside = self.root / "outside.patch"
        outside.write_bytes(b"fixture")
        (self.directory / "linked.patch").symlink_to(outside)
        (self.directory / "manifest.json").write_text(json.dumps(self.manifest("linked.patch")))
        self.assertIn("unsafe patch path", "\n".join(validate_manifests(self.root)))


class DownloadSafetyTests(unittest.TestCase):
    class Response(io.BytesIO):
        def __init__(self, payload, headers=None):
            super().__init__(payload)
            self.headers = headers or {}

    def test_declared_oversized_download_rejected_and_cleaned(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "download"
            response = self.Response(b"12345", {"Content-Length": "5"})
            with self.assertRaisesRegex(DownloadError, "byte budget"):
                download("https://example.invalid/file", dest, max_bytes=4,
                         opener=lambda *a, **k: response, retries=0)
            self.assertEqual(list(Path(td).iterdir()), [])

    def test_undeclared_oversized_download_rejected_and_cleaned(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "download"
            response = self.Response(b"12345")
            with self.assertRaisesRegex(DownloadError, "byte budget"):
                download("https://example.invalid/file", dest, max_bytes=4,
                         opener=lambda *a, **k: response, retries=0)
            self.assertFalse(dest.exists())
            self.assertEqual(list(Path(td).iterdir()), [])

    def test_expected_size_applies_before_writing_oversized_chunk(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "download"
            response = self.Response(b"12345")
            with self.assertRaisesRegex(DownloadError, "byte budget"):
                download("https://example.invalid/file", dest, expected_size=4,
                         opener=lambda *a, **k: response, retries=0)
            self.assertFalse(dest.exists())

    def test_disk_reserve_blocks_download(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "download"
            response = self.Response(b"1")
            with patch("kernelforge.toolchains.download.shutil.disk_usage", return_value=shutil._ntuple_diskusage(100, 100, 0)):
                with self.assertRaisesRegex(DownloadError, "disk reserve"):
                    download("https://example.invalid/file", dest,
                             opener=lambda *a, **k: response, retries=0)
            self.assertFalse(dest.exists())


class ArchiveSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root / "out"
        self.archive = self.root / "test.zip"

    def zip(self, pairs):
        with zipfile.ZipFile(self.archive, "w") as archive:
            for name, data in pairs:
                archive.writestr(name, data)

    def test_member_limit(self):
        self.zip([("a", b"x"), ("b", b"y")])
        with self.assertRaisesRegex(ArchiveError, "member budget"):
            extract(self.archive, self.output, "zip", max_members=1)
        self.assertFalse(self.output.exists())

    def test_single_member_limit(self):
        self.zip([("a", b"12345")])
        with self.assertRaisesRegex(ArchiveError, "single member byte budget"):
            extract(self.archive, self.output, "zip", max_member_bytes=4)
        self.assertFalse(self.output.exists())

    def test_total_expanded_size_limit(self):
        self.zip([("a", b"123"), ("b", b"456")])
        with self.assertRaisesRegex(ArchiveError, "unpacked byte budget"):
            extract(self.archive, self.output, "zip", max_bytes=5)
        self.assertFalse(self.output.exists())

    def test_case_collision(self):
        self.zip([("a", b"1"), ("A", b"2")])
        with self.assertRaisesRegex(ArchiveError, "case-colliding"):
            extract(self.archive, self.output, "zip")
        self.assertFalse(self.output.exists())

    def test_zip_symlink_rejected(self):
        link = zipfile.ZipInfo("link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.zip([(link, b"outside")])
        with self.assertRaisesRegex(ArchiveError, "unsupported ZIP"):
            extract(self.archive, self.output, "zip")
        self.assertFalse(self.output.exists())

    def test_nested_windows_ads_path_rejected(self):
        self.zip([("sub/file:stream", b"1")])
        with self.assertRaisesRegex(ArchiveError, "unsafe path"):
            extract(self.archive, self.output, "zip")
        self.assertFalse(self.output.exists())

    def test_tar_expanded_size_limit(self):
        archive_path = self.root / "test.tar"
        with tarfile.open(archive_path, "w") as archive:
            for name in ("a", "b"):
                info = tarfile.TarInfo(name)
                info.size = 3
                archive.addfile(info, io.BytesIO(b"123"))
        with self.assertRaisesRegex(ArchiveError, "unpacked byte budget"):
            extract(archive_path, self.output, "tar", max_bytes=5)
        self.assertFalse(self.output.exists())

    def test_archive_disk_reserve(self):
        self.zip([("a", b"1")])
        with patch("kernelforge.toolchains.archive.shutil.disk_usage", return_value=shutil._ntuple_diskusage(100, 100, 0)):
            with self.assertRaisesRegex(ArchiveError, "disk reserve"):
                extract(self.archive, self.output, "zip")
        self.assertFalse(self.output.exists())


class RedactionTests(unittest.TestCase):
    def test_url_header_and_token_removed(self):
        sample = ("https://user:fake-pass@example.invalid/file?token=fake-secret "
                  "Authorization: Bearer fake-bearer ghp_" + "A"*36)
        cleaned = redact_diagnostic(sample)
        for secret in ("fake-pass", "fake-secret", "fake-bearer", "ghp_"+"A"*36):
            self.assertNotIn(secret, cleaned)
        self.assertIn("example.invalid", cleaned)

    def test_git_error_redaction(self):
        failure = subprocess.CompletedProcess(["git"], 1, "",
                                               "fatal: https://user:fake-pass@example.invalid")
        with patch("kernelforge.source.subprocess.run", return_value=failure):
            with self.assertRaises(SourceError) as caught:
                _run_git(["fetch", "origin"])
        self.assertNotIn("fake-pass", str(caught.exception))

    def test_raw_log_redaction_and_overlong_line(self):
        source = io.BytesIO(b"Authorization: Bearer example-secret\n" +
                             b"x" * 100 + b"password=must-not-leak\nnormal output\n")
        dest = io.StringIO()
        result = publish_redacted_log(source, dest, line_limit=64)
        self.assertNotIn("example-secret", dest.getvalue())
        self.assertNotIn("must-not-leak", dest.getvalue())
        self.assertIn("normal output", dest.getvalue())
        self.assertFalse(result["truncated"])

    def test_raw_log_limit_and_control_sanitizing(self):
        source = io.BytesIO(b"\x1b[31mhello\x1b[0m\nsecond line\n")
        dest = io.StringIO()
        result = publish_redacted_log(source, dest, byte_limit=7)
        self.assertTrue(result["truncated"])
        self.assertNotIn("\x1b", dest.getvalue())
        self.assertNotIn("second line", dest.getvalue())

    def test_nested_report_redaction(self):
        self.assertEqual(redact_tree({"list": ["https://u:p@example.invalid"]}),
                         {"list": ["https://[REDACTED]@example.invalid"]})


if __name__ == "__main__":
    unittest.main()
