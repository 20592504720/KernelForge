from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

from kernelforge.build import BuildError, run_build
from kernelforge.toolchains import ToolchainManager, ToolchainManagerError
from kernelforge.toolchains.archive import ArchiveError, extract
from kernelforge.toolchains.download import DownloadError, download
from kernelforge.toolchains.locking import FileLock, LockTimeout
from kernelforge.toolchains.manager import ArchiveSourceAdapter, _binary_architecture, _satisfies, host_arch, normalize_arch
from kernelforge.toolchain import _version_tuple


class FixtureServer:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.requests = 0

        class Handler(BaseHTTPRequestHandler):
            def do_GET(inner):
                self.requests += 1
                if inner.path == "/delay":
                    time.sleep(0.15)
                body = self.payload
                if inner.path == "/drop":
                    inner.send_response(200)
                    inner.send_header("Content-Length", str(len(body) + 10))
                    inner.end_headers()
                    inner.wfile.write(body[:5])
                    inner.wfile.flush()
                    inner.close_connection = True
                    return
                inner.send_response(200)
                inner.send_header("Content-Length", str(len(body)))
                inner.end_headers()
                try:
                    inner.wfile.write(body)
                except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        if self.thread.is_alive():
            # BaseServer.shutdown() can wait forever if an interrupted test has
            # already stopped its serve_forever loop. Set the same flag and
            # join with a bound so fixture teardown remains safe on Windows.
            self.server._BaseServer__shutdown_request = True
            self.thread.join(timeout=2)
        self.server.server_close()
        if self.thread.is_alive():
            raise RuntimeError("fixture HTTP server thread did not stop")


def make_zip() -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        info = zipfile.ZipInfo("pkg/bin/clang")
        info.external_attr = (0o100755 << 16)
        archive.writestr(info, "fixture compiler executable\n")
        archive.writestr("pkg/share/version.txt", "18.1.2")
    return output.getvalue()


def make_tar() -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        info = tarfile.TarInfo("pkg/bin/aarch64-linux-gnu-gcc")
        info.mode = 0o755
        info.size = 9
        archive.addfile(info, io.BytesIO(b"fixturecc"))
    return output.getvalue()


MANAGER_HTTP_SERVER = FixtureServer(make_zip())


def tearDownModule():
    MANAGER_HTTP_SERVER.close()


class ToolchainVersionTests(unittest.TestCase):
    def test_clang_version_parse(self):
        self.assertEqual(_version_tuple("Android clang version 18.1.2 (based on LLVM)"), (18, 1, 2))

    def test_gcc_version_parse(self):
        self.assertEqual(_version_tuple("aarch64-linux-gnu-gcc (GCC) 13.2.0"), (13, 2, 0))

    def test_fixed_version_match_and_mismatch(self):
        _satisfies("18.1", {"version": "18.1.0"})
        with self.assertRaisesRegex(ToolchainManagerError, "version mismatch"):
            _satisfies("18.2", {"version": "18.1"})

    def test_minimum_version_is_enforced(self):
        _satisfies("18.2", {"minimum_version": "18.1"})
        with self.assertRaisesRegex(ToolchainManagerError, "minimum_version"):
            _satisfies("17.9", {"minimum_version": "18.0"})

    def test_maximum_version_is_enforced(self):
        _satisfies("17.9", {"maximum_version": "18.0"})
        with self.assertRaisesRegex(ToolchainManagerError, "maximum_version"):
            _satisfies("18.1", {"maximum_version": "18.0"})

    def test_conflicting_version_range_rejected(self):
        with self.assertRaisesRegex(ToolchainManagerError, "minimum_version exceeds"):
            _satisfies("1.0", {"minimum_version": "3.0", "maximum_version": "2.0"})

    def test_host_architecture_aliases(self):
        self.assertEqual(normalize_arch("AMD64"), "x86_64")
        self.assertEqual(normalize_arch("arm64"), "aarch64")
        self.assertTrue(host_arch())

    def test_elf_host_binary_architecture_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "fake-elf"
            header = bytearray(20); header[:4] = b"\x7fELF"; header[4] = 2; header[5] = 1
            header[18:20] = (183).to_bytes(2, "little"); binary.write_bytes(header)
            self.assertEqual(_binary_architecture(binary), "aarch64")

    def test_supported_target_architecture_and_bad_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ToolchainManager(Path(tmp) / "cache")
            base = profile()
            mgr._validate(base, {})
            base["target_arch"] = "not-a-real-target!"
            with self.assertRaisesRegex(ToolchainManagerError, "unsupported toolchain target"):
                mgr._validate(base, {})

    def test_host_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ToolchainManager(Path(tmp) / "cache")
            spec = profile(); spec["host_arch"] = "aarch64" if host_arch() != "aarch64" else "x86_64"
            with self.assertRaisesRegex(ToolchainManagerError, "architecture mismatch"):
                mgr.prepare(spec)

    def test_non_object_profile_has_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ToolchainManager(Path(tmp) / "cache")
            with self.assertRaisesRegex(ToolchainManagerError, "profile must be an object") as caught:
                mgr.prepare(None)
            self.assertEqual(caught.exception.phase, "requirements")


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.server = MANAGER_HTTP_SERVER
        self.original_payload = self.server.payload

    def tearDown(self):
        self.server.payload = self.original_payload

    def test_download_success_is_atomic_and_size_checked(self):
        self.server.payload = b"download bytes"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "payload"
            result = download(self.server.base + "/ok", target, expected_size=len(b"download bytes"))
            self.assertEqual(target.read_bytes(), b"download bytes")
            self.assertEqual(result["size"], len(b"download bytes"))
            self.assertEqual(list(Path(tmp).glob("*.part")), [])

    def test_download_timeout_retries_then_cleans(self):
        self.server.payload = b"slow"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "payload"
            with self.assertRaises(DownloadError):
                download(self.server.base + "/delay", target, timeout=0.02, retries=1)
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_interrupted_download_detected_and_cleaned(self):
        self.server.payload = b"long payload"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "payload"
            with self.assertRaisesRegex(DownloadError, "incomplete download"):
                download(self.server.base + "/drop", target, retries=0)
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_failed_download_does_not_destroy_preexisting_destination(self):
        self.server.payload = b"payload"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "payload"; target.write_bytes(b"keep me")
            with self.assertRaises(DownloadError):
                download(self.server.base + "/drop", target, retries=0)
            self.assertEqual(target.read_bytes(), b"keep me")

    def test_invalid_url_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(DownloadError, "HTTP or HTTPS"):
                download("file:///tmp/evil", Path(tmp) / "x")


class ArchiveTests(unittest.TestCase):
    def test_zip_and_tar_formats_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); zip_path = root / "a.zip"; tar_path = root / "a.tgz"
            zip_path.write_bytes(make_zip()); tar_path.write_bytes(make_tar())
            extract(zip_path, root / "zip", "zip")
            extract(tar_path, root / "tar", "tar.gz")
            self.assertEqual((root / "zip/pkg/share/version.txt").read_text(), "18.1.2")
            self.assertTrue((root / "tar/pkg/bin/aarch64-linux-gnu-gcc").is_file())
            self.assertTrue(os.access(root / "zip/pkg/bin/clang", os.X_OK) or os.name == "nt")

    def test_invalid_archive_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); archive = root / "broken.zip"; archive.write_bytes(b"not zip")
            with self.assertRaises(ArchiveError):
                extract(archive, root / "out", "zip")
            self.assertFalse((root / "out").exists())

    def test_zip_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("../escape", "bad")
            with self.assertRaisesRegex(ArchiveError, "unsafe path"):
                extract(archive, root / "out", "zip")
            self.assertFalse((root.parent / "escape").exists())

    def test_tar_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); archive = root / "bad.tar"
            with tarfile.open(archive, "w") as handle:
                info = tarfile.TarInfo("../../escape"); info.size = 1
                handle.addfile(info, io.BytesIO(b"x"))
            with self.assertRaisesRegex(ArchiveError, "unsafe path"):
                extract(archive, root / "out", "tar")


def profile(**updates):
    spec = {"kind": "llvm", "name": "fixture-clang", "version": "18.1.2", "host_arch": host_arch(), "target_arch": "aarch64",
            "source_type": "custom", "url": "http://127.0.0.1/fixture", "sha256": hashlib.sha256(make_zip()).hexdigest(),
            "archive_format": "zip", "layout_root": "pkg", "executables": {"CC": "bin/clang"}, "version_args": ["--version"],
            "version_timeout_seconds": 2}
    spec.update(updates)
    return spec


class ManagerFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.payload = MANAGER_HTTP_SERVER.payload
        self.server = MANAGER_HTTP_SERVER
        self.payload = make_zip()
        self.server.payload = self.payload
        self.server.requests = 0
        self.manager = ToolchainManager(self.root / "cache", lock_timeout=1)
        self.mock_version()

    def tearDown(self):
        self.server.payload = make_zip()
        self.tmp.cleanup()

    def mock_version(self):
        self.version_patch = patch("kernelforge.toolchains.manager.subprocess.run", return_value=subprocess.CompletedProcess(["clang"], 0, "clang version 18.1.2\n", ""))
        self.version_patch.start()
        self.addCleanup(self.version_patch.stop)

    def spec(self, **kwargs):
        values = {"url": self.server.base + "/archive", "sha256": hashlib.sha256(self.payload).hexdigest()}
        values.update(kwargs)
        return profile(**values)


class ManagerInstallTests(ManagerFixture):
    def test_download_hash_verify_extract_atomic_install(self):
        result = self.manager.prepare(self.spec())
        self.assertTrue(Path(result["root"]).is_dir())
        self.assertEqual(result["audit"]["actual_sha256"], hashlib.sha256(self.payload).hexdigest())
        self.assertTrue(result["audit"]["sha256_verified"])
        self.assertTrue(Path(result["executables"]["CC"]).is_file())

    def test_sha_mismatch_blocks_extraction_install_and_cache(self):
        spec = self.spec(sha256="0" * 64)
        with patch.object(self.manager, "extractor", side_effect=AssertionError("extract should not run")):
            with self.assertRaisesRegex(ToolchainManagerError, "SHA256 verification failed") as caught:
                self.manager.prepare(spec)
        self.assertEqual(caught.exception.audit["failure_phase"], "sha256")
        self.assertFalse(list((self.root / "cache" / "install").glob("*")))
        self.assertFalse(list((self.root / "cache" / "downloads").glob("*")))

    def test_missing_sha_refuses_download(self):
        spec = self.spec(); spec.pop("sha256")
        with self.assertRaisesRegex(ToolchainManagerError, "trusted 64-character SHA256"):
            self.manager.prepare(spec)
        self.assertEqual(self.server.requests, 0)

    def test_bad_sha_shape_refuses_download(self):
        with self.assertRaisesRegex(ToolchainManagerError, "trusted 64-character SHA256"):
            self.manager.prepare(self.spec(sha256="1234"))
        self.assertEqual(self.server.requests, 0)

    def test_version_failure_does_not_publish_cache(self):
        with patch("kernelforge.toolchains.manager.subprocess.run", return_value=subprocess.CompletedProcess(["clang"], 1, "", "broken")):
            with self.assertRaisesRegex(ToolchainManagerError, "version query failed"):
                self.manager.prepare(self.spec())
        self.assertEqual(self.manager.list_cache(), [])

    def test_gcc_toolchain_uses_cross_compile_prefix(self):
        self.payload = make_tar(); self.server.payload = self.payload
        server = self.server
        spec = {"kind": "gcc", "name": "fixture-aarch64-gcc", "version": "13.2.1", "host_arch": host_arch(), "target_arch": "aarch64-linux-gnu",
                "source_type": "custom", "url": server.base + "/gcc", "sha256": hashlib.sha256(self.payload).hexdigest(), "archive_format": "tar.gz",
                "layout_root": "pkg", "executables": {"CC": "bin/aarch64-linux-gnu-gcc"}, "version_args": ["--version"]}
        with patch("kernelforge.toolchains.manager.subprocess.run", return_value=subprocess.CompletedProcess(["gcc"], 0, "aarch64-linux-gnu-gcc 13.2.1", "")):
            result = self.manager.prepare(spec)
        self.assertIn("CROSS_COMPILE", result["environment"], result["environment"])
        self.assertTrue(result["environment"]["CROSS_COMPILE"].endswith("aarch64-linux-gnu-"))

    def test_gcc_target_mismatch_rejected(self):
        payload = make_tar(); self.server.payload = payload
        server = self.server
        spec = {"kind": "gcc", "name": "wrong-target", "version": "13.2.1", "host_arch": host_arch(), "target_arch": "aarch64",
                "source_type": "custom", "url": server.base + "/gcc", "sha256": hashlib.sha256(payload).hexdigest(), "archive_format": "tar.gz",
                "layout_root": "pkg", "executables": {"CC": "bin/aarch64-linux-gnu-gcc"}, "version_args": ["--version"]}
        with patch("kernelforge.toolchains.manager.subprocess.run", side_effect=[subprocess.CompletedProcess(["gcc"], 0, "gcc 13.2.1", ""), subprocess.CompletedProcess(["gcc"], 0, "arm-linux-gnueabi", "")]):
            with self.assertRaisesRegex(ToolchainManagerError, "target mismatch"):
                self.manager.prepare(spec)

    def test_riscv_target_mismatch_is_detected(self):
        payload = make_tar(); self.server.payload = payload
        server = self.server
        spec = {"kind": "gcc", "name": "wrong-riscv-target", "version": "13.2.1", "host_arch": host_arch(), "target_arch": "riscv64-linux-gnu",
                "source_type": "custom", "url": server.base + "/gcc", "sha256": hashlib.sha256(payload).hexdigest(), "archive_format": "tar.gz",
                "layout_root": "pkg", "executables": {"CC": "bin/aarch64-linux-gnu-gcc"}, "version_args": ["--version"]}
        with patch("kernelforge.toolchains.manager.subprocess.run", side_effect=[subprocess.CompletedProcess(["gcc"], 0, "gcc 13.2.1", ""), subprocess.CompletedProcess(["gcc"], 0, "aarch64-linux-gnu", "")]):
            with self.assertRaisesRegex(ToolchainManagerError, "target mismatch"):
                self.manager.prepare(spec)

    def test_clang_minimum_rejected(self):
        with self.assertRaisesRegex(ToolchainManagerError, "minimum_version"):
            self.manager.prepare(self.spec(minimum_version="19.0"))


class ManagerCacheTests(ManagerFixture):
    def test_valid_cache_reused_without_redownload(self):
        first = self.manager.prepare(self.spec())
        requests = self.server.requests
        second = self.manager.prepare(self.spec())
        self.assertEqual(self.server.requests, requests)
        self.assertTrue(second["audit"]["cache_used"])
        self.assertEqual(first["root"], second["root"])

    def test_missing_cache_metadata_is_quarantined_and_reacquired(self):
        self.manager.prepare(self.spec())
        metadata = next((self.root / "cache/metadata").glob("*.json")); metadata.unlink()
        with self.assertLogs("kernelforge.toolchains.manager", level="WARNING"):
            second = self.manager.prepare(self.spec())
        self.assertFalse(second["audit"]["cache_used"])
        self.assertEqual(self.server.requests, 2)

    def test_bad_cache_metadata_is_quarantined_and_reacquired(self):
        self.manager.prepare(self.spec())
        metadata = next((self.root / "cache/metadata").glob("*.json")); metadata.write_text("{")
        with self.assertLogs("kernelforge.toolchains.manager", level="WARNING"):
            self.manager.prepare(self.spec())
        self.assertEqual(self.server.requests, 2)

    def test_changed_cached_archive_is_reacquired(self):
        self.manager.prepare(self.spec())
        archive = next((self.root / "cache/downloads").glob("*.archive")); archive.write_bytes(b"tampered")
        with self.assertLogs("kernelforge.toolchains.manager", level="WARNING"):
            result = self.manager.prepare(self.spec())
        self.assertFalse(result["audit"]["cache_used"])
        self.assertEqual(self.server.requests, 2)

    def test_changed_installed_files_are_not_reused(self):
        self.manager.prepare(self.spec())
        compiler = next((self.root / "cache/install").glob("*/pkg/bin/clang"))
        compiler.write_text("tampered compiler")
        with self.assertLogs("kernelforge.toolchains.manager", level="WARNING"):
            result = self.manager.prepare(self.spec())
        self.assertFalse(result["audit"]["cache_used"])
        self.assertEqual(self.server.requests, 2)

    def test_forged_metadata_cannot_authorize_changed_executable(self):
        from kernelforge.toolchains.manager import _tree_digest
        first = self.manager.prepare(self.spec())
        install = Path(first["root"])
        compiler = Path(first["executables"]["CC"])
        compiler.write_bytes(b"forged compiler")
        metadata = next((self.root / "cache/metadata").glob("*.json"))
        data = json.loads(metadata.read_text())
        data["installed_tree_sha256"] = _tree_digest(install)
        metadata.write_text(json.dumps(data))
        with self.assertLogs("kernelforge.toolchains.manager", level="WARNING"):
            result = self.manager.prepare(self.spec())
        self.assertFalse(result["audit"]["cache_used"])
        self.assertNotEqual(Path(result["executables"]["CC"]).read_bytes(), b"forged compiler")

    def test_invalid_cache_with_active_lease_is_not_removed(self):
        first = self.manager.prepare(self.spec(), lease=True)
        try:
            compiler = Path(first["executables"]["CC"])
            compiler.write_bytes(b"changed")
            with self.assertRaisesRegex(ToolchainManagerError, "active lease"):
                self.manager.prepare(self.spec())
            self.assertEqual(compiler.read_bytes(), b"changed")
        finally:
            self.manager.release(first)

    def test_metadata_path_cannot_nominate_external_cleanup(self):
        outside = self.root / "outside"
        outside.mkdir()
        marker = outside / "marker"
        marker.write_text("keep")
        metadata = self.root / "cache" / "metadata"
        metadata.mkdir(parents=True)
        (metadata / "malformed.json").write_text(json.dumps({"key": str(outside)}))
        self.assertEqual(self.manager.clean_cache(), [])
        self.assertEqual(marker.read_text(), "keep")

    def test_interrupted_install_backup_is_restored(self):
        first = self.manager.prepare(self.spec())
        install = Path(first["root"])
        backup = install.with_name(f".{install.name}.old-interrupted")
        os.replace(install, backup)
        second = self.manager.prepare(self.spec())
        self.assertTrue(second["audit"]["cache_used"])
        self.assertTrue(Path(second["root"]).is_dir())
        self.assertFalse(backup.exists())

    def test_second_version_installs_in_isolated_directory(self):
        first = self.manager.prepare(self.spec())
        with patch("kernelforge.toolchains.manager.subprocess.run", return_value=subprocess.CompletedProcess(["clang"], 0, "clang version 19.0.0\n", "")):
            second = self.manager.prepare(self.spec(name="fixture-clang", version="19.0.0"))
        self.assertNotEqual(first["root"], second["root"])
        self.assertTrue(Path(first["root"]).is_dir())
        self.assertTrue(Path(second["root"]).is_dir())

    def test_cache_keys_isolate_version_source_and_architecture(self):
        mgr = self.manager
        keys = {mgr._key(self.spec()), mgr._key(self.spec(version="19.0.0")), mgr._key(self.spec(url=self.server.base + "/other")), mgr._key(self.spec(target_arch="arm"))}
        self.assertEqual(len(keys), 4)

    def test_cache_key_isolates_executable_layout(self):
        self.assertNotEqual(self.manager._key(self.spec()), self.manager._key(self.spec(executables={"CC": "other/clang"})))

    def test_cache_listing_reports_integrity_and_size(self):
        self.manager.prepare(self.spec())
        rows = self.manager.list_cache()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["valid"])
        self.assertGreater(rows[0]["size_bytes"], 0)

    def test_cache_clean_by_version(self):
        self.manager.prepare(self.spec())
        removed = self.manager.clean_cache(name="fixture-clang", version="18.1.2")
        self.assertEqual(len(removed), 1)
        self.assertEqual(self.manager.list_cache(), [])

    def test_live_lease_prevents_cache_clean(self):
        prepared = self.manager.prepare(self.spec(), lease=True)
        try:
            self.assertEqual(self.manager.clean_cache(), [])
            self.assertTrue(Path(prepared["root"]).exists())
        finally:
            self.manager.release(prepared)
        self.assertEqual(len(self.manager.clean_cache()), 1)

    def test_corrupt_cache_can_be_cleaned_by_damaged_only(self):
        self.manager.prepare(self.spec())
        archive = next((self.root / "cache/downloads").glob("*.archive")); archive.write_bytes(b"bad")
        rows = self.manager.list_cache()
        self.assertFalse(rows[0]["valid"])
        self.assertEqual(len(self.manager.clean_cache(damaged_only=True)), 1)


class ManagerModeTests(ManagerFixture):
    def test_auto_downloads_when_cache_misses(self):
        result = self.manager.prepare(self.spec())
        self.assertTrue(result["audit"]["sha256_verified"])

    def test_local_only_reuses_cache_and_refuses_miss_without_network(self):
        ToolchainManager(self.root / "cache").prepare(self.spec())
        local = ToolchainManager(self.root / "cache", mode="LOCAL_ONLY")
        self.assertTrue(local.prepare(self.spec())["audit"]["cache_used"])
        local.clean_cache()
        with self.assertRaisesRegex(ToolchainManagerError, "LOCAL_ONLY mode"):
            local.prepare(self.spec())

    def test_local_only_never_downloads(self):
        local = ToolchainManager(self.root / "empty", mode="LOCAL_ONLY", downloader=lambda *_a, **_k: self.fail("network called"))
        with self.assertRaises(ToolchainManagerError):
            local.prepare(self.spec())
        self.assertEqual(self.server.requests, 0)

    def test_download_only_ignores_explicit_local_toolchain(self):
        local_spec = self.spec(local_path=sys.executable, version_args=["-c", "print('clang version 18.1.2')"])
        result = ToolchainManager(self.root / "download-only", mode="DOWNLOAD_ONLY").prepare(local_spec)
        self.assertFalse(result["audit"]["local_toolchain"])
        self.assertTrue(result["audit"]["sha256_verified"])

    def test_local_executable_path_supported_and_trust_recorded(self):
        manager = ToolchainManager(self.root / "cache", mode="LOCAL_ONLY")
        spec = self.spec(local_path=sys.executable, layout_root="", trust_source="user-supplied-local-compiler", version_args=["-c", "print('clang version 18.1.2')"])
        result = manager.prepare(spec)
        self.assertTrue(result["audit"]["local_toolchain"])
        self.assertFalse(result["audit"]["sha256_verified"])
        self.assertEqual(result["audit"]["trust_source"], "user-supplied-local-compiler")

    def test_sensitive_url_credentials_are_redacted_from_report(self):
        result = self.manager.prepare(self.spec(url=self.server.base + "/archive?token=secret"))
        self.assertNotIn("token", result["audit"]["source"])
        self.assertNotIn("secret", result["audit"]["source"])


class LockTests(unittest.TestCase):
    def test_exclusive_lock_blocks_second_owner_then_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.lock"
            with FileLock(path):
                with self.assertRaises(LockTimeout):
                    with FileLock(path, timeout=0.05, poll=0.01):
                        pass
            with FileLock(path, timeout=0.1):
                self.assertTrue(path.exists())

    def test_exception_exit_releases_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.lock"
            with self.assertRaises(ValueError):
                with FileLock(path):
                    raise ValueError("fixture")
            self.assertFalse(path.exists())

    def test_abandoned_old_dead_owner_lock_is_recovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "stale.lock"; lock.mkdir()
            (lock / "owner.json").write_text(json.dumps({"pid": 99999999, "host": __import__("socket").gethostname(), "created": 0}))
            old = time.time() - 1000; os.utime(lock, (old, old))
            with FileLock(lock, timeout=0.2, stale_after=0.01):
                self.assertTrue(lock.exists())


class ConcurrentManagerTests(ManagerFixture):
    def test_concurrent_requests_share_one_download_and_install(self):
        spec = self.spec()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.manager.prepare(spec), range(2)))
        self.assertEqual(self.server.requests, 1)
        self.assertEqual(results[0]["root"], results[1]["root"])
        self.assertTrue(any(result["audit"]["cache_used"] for result in results))

    def test_concurrent_cache_writes_leave_valid_metadata(self):
        spec = self.spec()
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: self.manager.prepare(spec), range(4)))
        self.assertTrue(self.manager.list_cache()[0]["valid"])


class SourceAdapterTests(ManagerFixture):
    def test_staging_path_is_bounded_under_long_cache_root(self):
        observed = []
        def observe(archive, destination, fmt):
            observed.append(destination)
            extract(archive, destination, fmt)

        manager = ToolchainManager(self.root / ('long-root-' + 'x' * 95) / 'cache',
                                   extractor=observe)
        result = manager.prepare(self.spec())
        self.assertTrue(result['audit']['sha256_verified'])
        self.assertEqual(len(observed), 1)
        self.assertLessEqual(len(observed[0].parent.name), 25)

    def test_custom_source_adapter_can_resolve_archive_and_layout(self):
        class ProfileAdapter(ArchiveSourceAdapter):
            requires_archive_format = False

            def resolve(self, spec):
                return spec["url"], "zip", "pkg"

        manager = ToolchainManager(self.root / "custom-cache", source_adapters={"fixture-release": ProfileAdapter()})
        spec = self.spec(source_type="fixture-release")
        spec.pop("archive_format")
        result = manager.prepare(spec)
        self.assertTrue(result["audit"]["sha256_verified"])


class BuildToolchainIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)

    @staticmethod
    def fake_checkout(_repository, _ref, destination, **_kwargs):
        destination.mkdir(parents=True, exist_ok=False)
        return "a" * 40

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, mode):
        profile_local = {"kind": "llvm", "name": f"local-{mode}", "version": "18.1.0", "minimum_version": "18.0", "target_arch": "aarch64",
                         "local_path": sys.executable, "version_args": ["-c", "print('clang version 18.1.0')"], "executables": {"CC": "clang"}}
        output_code = "from pathlib import Path; import os; Path('Image').write_text(os.environ['KERNELFORGE_TOOLCHAIN_ROOT'])"
        adapter = {"argv": [sys.executable, "-c", output_code], "directory": ".", "targets": ["fixture"], "artifacts": ["Image"], "toolchain_profile": profile_local}
        return {"schema_version": 1, "device": {"id": "fixture"}, "kernel_version": "6.1", "source": {"repository": "https://example.invalid/kernel.git", "ref": "a" * 40},
                "toolchain": {"required": [], "mode": "LOCAL_ONLY", "cache_dir": str(self.root / "cache")}, "build": {"mode": mode, "jobs": 1, "gki": {**adapter, "system": "kleaf"}, "vendor": adapter},
                "artifacts": {"paths": ["Image"], "require_at_least_one": True}}

    def test_gki_adapter_receives_managed_toolchain_environment_and_report(self):
        out = self.root / "gki-out"
        with patch("kernelforge.build.checkout", side_effect=self.fake_checkout):
            report = run_build(self.config("gki"), self.root / "gki-work", out)
        managed = report["toolchain"]["managed"]
        self.assertEqual(managed["version"], "18.1.0")
        self.assertEqual(managed["version_check"], "passed")
        self.assertIn("CC", report["build"]["toolchain_environment"]["keys"])
        self.assertIn("environment_summary", managed)
        self.assertEqual(report["build"]["status"], "success")

    def test_vendor_adapter_receives_independent_toolchain_profile(self):
        cfg = self.config("vendor"); cfg["build"]["vendor"]["toolchain_profile"]["name"] = "vendor-clang"
        with patch("kernelforge.build.checkout", side_effect=self.fake_checkout):
            report = run_build(cfg, self.root / "vendor-work", self.root / "vendor-out")
        self.assertEqual(report["toolchain"]["managed"]["name"], "vendor-clang")
        self.assertEqual(report["build"]["status"], "success")

    def test_toolchain_failure_prevents_build_and_writes_failure_report(self):
        cfg = self.config("vendor"); cfg["build"]["vendor"]["toolchain_profile"].pop("local_path")
        out = self.root / "failed"
        with patch("kernelforge.build.checkout", side_effect=self.fake_checkout):
            with self.assertRaisesRegex(BuildError, "toolchain preparation failed"):
                run_build(cfg, self.root / "fail-work", out)
        report = json.loads((out / "build-report.json").read_text())
        self.assertEqual(report["build"]["status"], "failure")
        self.assertIn("failure_phase", report["toolchain"]["managed"])
        self.assertIn("failure_reason", report["toolchain"]["managed"])


if __name__ == "__main__":
    unittest.main()
