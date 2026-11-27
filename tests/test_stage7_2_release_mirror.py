"""Stage 7.2 reviewed Release mirror offline provenance tests (no Internet)."""
import copy
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from kernelforge.toolchains.download import DownloadError
from kernelforge.toolchains.manager import (
    ToolchainManager,
    ToolchainManagerError,
    host_arch,
)
from kernelforge.toolchains.release_mirror import (
    MirrorUnavailable,
    ReleaseMirrorError,
    ReviewedGithubReleaseAdapter,
    verify_release_spec,
)

REPO = "ReviewedBuilder/Toolchains"
TAG, NAME = "v18.1.2", "clang-18.1.2-linux.zip"
RELEASE_ID, ASSET_ID, UPLOADER_ID = 12199, 78902, 10008
MIRROR = f"https://github.com/{REPO}/releases/download/{TAG}/{NAME}"
ORIGIN = "https://example.org/pinned/clang.zip"


def archive():
    file = io.BytesIO()
    with zipfile.ZipFile(file, "w") as z:
        info = zipfile.ZipInfo("pkg/bin/clang")
        info.create_system = 3
        info.external_attr = 0o100755 << 16
        z.writestr(info, b"fake-clang")
        z.writestr("pkg/share/version.txt", b"18.1.2")
    return file.getvalue()


def spec_for(raw, *, fallback=True):
    digest = hashlib.sha256(raw).hexdigest()
    lock = {"repository": REPO, "release_id": RELEASE_ID, "asset_id": ASSET_ID,
            "tag": TAG, "asset_name": NAME, "asset_size": len(raw),
            "uploader_id": UPLOADER_ID, "sha256": digest,
            "license": "Apache-2.0", "license_reviewed": True}
    if fallback:
        lock["fallback"] = {
            "url": ORIGIN, "sha256": digest,
            "source_commit": "a" * 40,
            "repository": "https://github.com/upstream/llvm-project",
        }
    return {"kind": "llvm", "name": "fixture", "version": "18.1.2",
            "source_type": "llvm-release", "url": MIRROR,
            "host_arch": host_arch(), "target_arch": "aarch64",
            "sha256": digest, "expected_size": len(raw),
            "archive_format": "zip", "layout_root": "pkg",
            "executables": {"CC": "bin/clang"}, "release_lock": lock}


def metadata(spec):
    lock = spec["release_lock"]
    return (
        {"id": RELEASE_ID, "tag_name": TAG, "draft": False,
         "immutable": False, "assets": [{"id": ASSET_ID}]},
        {"id": ASSET_ID, "name": NAME, "size": lock["asset_size"],
         "state": "uploaded", "digest": "sha256:" + lock["sha256"],
         "browser_download_url": MIRROR,
         "url": f"https://api.github.com/repos/{REPO}/releases/assets/{ASSET_ID}",
         "uploader": {"id": UPLOADER_ID}},
    )


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.raw = archive()
        self.spec = spec_for(self.raw)
        self.release, self.asset = metadata(self.spec)
        self.calls, self.lookups = [], []
        self.mirror_bytes = self.origin_bytes = self.raw
        self.mirror_error = self.metadata_error = None
        adapter = ReviewedGithubReleaseAdapter(metadata_fetch=self.fetch)
        self.mgr = ToolchainManager(self.root / "cache", downloader=self.download,
                                    source_adapters={"llvm-release": adapter})
        self.mgr._verify_tools = self.verify_tools

    def fetch(self, url):
        self.lookups.append(url)
        if self.metadata_error:
            raise self.metadata_error
        if url.endswith(f"/releases/{RELEASE_ID}"):
            return self.release
        if url.endswith(f"/releases/assets/{ASSET_ID}"):
            return self.asset
        raise AssertionError("unexpected GitHub API request")

    def download(self, url, path, *, timeout, retries, expected_size=None):
        self.calls.append(url)
        if url == MIRROR and self.mirror_error:
            raise self.mirror_error
        if url == MIRROR:
            contents = self.mirror_bytes
        elif url == ORIGIN:
            contents = self.origin_bytes
        else:
            raise AssertionError("unapproved network request")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
        return {"duration_seconds": 0.01}

    def verify_tools(self, root, spec):
        exe = (root / "pkg/bin/clang").resolve()
        if not exe.is_file():
            raise ToolchainManagerError("missing compiler", phase="layout")
        return {
            "version": "18.1.2", "binary_host_arch": host_arch(),
            "host_arch_check": "passed", "detected_target_arch": "aarch64",
            "target_arch_check": "passed", "executables": {"CC": str(exe)}
        }, {"CC": str(exe)}

    def no_install(self):
        p = self.root / "cache/install"
        self.assertFalse(list(p.iterdir()) if p.exists() else [])


class Stage72MirrorIntegration(Fixture):
    def test_exact_reviewed_asset_is_installed_with_recorded_identity(self):
        x = self.mgr.prepare(self.spec)
        self.assertTrue(x["audit"]["sha256_verified"])
        self.assertFalse(x["audit"]["mirror_fallback"])
        self.assertEqual(x["audit"]["source_route"], "reviewed-github-release")
        self.assertEqual(x["audit"]["mirror_provenance"]["asset_id"], ASSET_ID)
        self.assertEqual(self.calls, [MIRROR])
        self.assertEqual(len(self.lookups), 2)
        self.assertTrue(self.mgr.list_cache()[0]["valid"])

    def test_cache_hit_does_not_require_repeated_github_api(self):
        self.mgr.prepare(self.spec)
        self.metadata_error = AssertionError("should not call network on cache hit")
        self.calls.clear()
        x = self.mgr.prepare(self.spec)
        self.assertTrue(x["audit"]["cache_used"])
        self.assertFalse(self.calls)

    def test_mirror_transport_failure_falls_back_only_to_pinned_source(self):
        self.mirror_error = DownloadError("unavailable")
        x = self.mgr.prepare(self.spec)
        self.assertEqual(self.calls, [MIRROR, ORIGIN])
        self.assertTrue(x["audit"]["mirror_fallback"])
        self.assertEqual(x["audit"]["fallback_source_commit"], "a" * 40)
        self.assertTrue(x["audit"]["sha256_verified"])

    def test_metadata_outage_uses_pinned_origin_without_mirror_download(self):
        self.metadata_error = MirrorUnavailable("api network down")
        x = self.mgr.prepare(self.spec)
        self.assertEqual(self.calls, [ORIGIN])
        self.assertEqual(x["audit"]["mirror_failure_class"], "metadata_unavailable")

    def test_metadata_outage_without_fallback_is_a_blocker(self):
        self.spec = spec_for(self.raw, fallback=False)
        self.metadata_error = MirrorUnavailable("api network down")
        with self.assertRaisesRegex(ToolchainManagerError, "no pinned upstream fallback"):
            self.mgr.prepare(self.spec)
        self.assertEqual(self.calls, [])
        self.no_install()

    def test_corrupt_mirror_bytes_block_without_silent_fallback(self):
        self.mirror_bytes = self.raw + b"tamper"
        with self.assertRaisesRegex(ToolchainManagerError, "SHA256 verification failed"):
            self.mgr.prepare(self.spec)
        self.assertEqual(self.calls, [MIRROR])
        self.no_install()

    def test_corrupt_upstream_fallback_is_never_installed(self):
        self.mirror_error = DownloadError("unavailable")
        self.origin_bytes = self.raw + b"tamper"
        with self.assertRaisesRegex(ToolchainManagerError, "SHA256 verification failed"):
            self.mgr.prepare(self.spec)
        self.assertEqual(self.calls, [MIRROR, ORIGIN])
        self.no_install()

    def test_mismatched_remote_release_identity_fails_before_transfer(self):
        cases = [
            lambda: self.release.update(id=RELEASE_ID+1),
            lambda: self.release.update(tag_name="another"),
            lambda: self.release.update(draft=True),
            lambda: self.release.update(assets=[]),
            lambda: self.asset.update(id=ASSET_ID+1),
            lambda: self.asset.update(name="evil.zip"),
            lambda: self.asset.update(size=len(self.raw)+1),
            lambda: self.asset.update(state="starter"),
            lambda: self.asset.update(digest="sha256:"+"0"*64),
            lambda: self.asset["uploader"].update(id=99),
            lambda: self.asset.update(browser_download_url="https://evil.example/alt.zip"),
        ]
        for index, mutate in enumerate(cases):
            with self.subTest(case=index):
                self.release, self.asset = metadata(self.spec)
                self.calls.clear()
                mutate()
                with self.assertRaises(ToolchainManagerError):
                    self.mgr.prepare(self.spec)
                self.assertEqual(self.calls, [])
                self.no_install()

    def test_immutable_release_policy_must_be_met(self):
        self.spec["release_lock"]["require_immutable"] = True
        with self.assertRaisesRegex(ToolchainManagerError, "not immutable"):
            self.mgr.prepare(self.spec)
        self.release["immutable"] = True
        x = self.mgr.prepare(self.spec)
        self.assertTrue(x["audit"]["mirror_provenance"]["release_immutable"])

    def test_local_override_cannot_skip_reviewed_lock_requirement(self):
        bad = copy.deepcopy(self.spec)
        bad.pop("release_lock")
        bad["local_root"] = str(self.root)
        with self.assertRaisesRegex(ToolchainManagerError, "reviewed Release lock"):
            self.mgr.prepare(bad)

    def test_cache_key_includes_locked_release_identity(self):
        bad = copy.deepcopy(self.spec)
        bad["release_lock"]["asset_id"] += 1
        self.assertNotEqual(self.mgr._key(self.spec), self.mgr._key(bad))

    def test_tampered_toolchain_cache_is_reacquired_safely(self):
        x = self.mgr.prepare(self.spec)
        p = Path(x["root"]) / "pkg/share/version.txt"
        p.write_bytes(b"changed")
        self.calls.clear()
        y = self.mgr.prepare(self.spec)
        self.assertFalse(y["audit"]["cache_used"])
        self.assertEqual(self.calls, [MIRROR])
        self.assertEqual(p.read_bytes(), b"18.1.2")


class Stage72ReleaseLockNegative(unittest.TestCase):
    def setUp(self):
        self.spec = spec_for(archive())

    def test_reviewed_lock_is_offline_valid(self):
        self.assertEqual(verify_release_spec(self.spec)["asset_id"], ASSET_ID)

    def test_bad_toolchain_kind_or_release_alias_blocked(self):
        for kind, source in [("rust", "llvm-release"), ("gcc", "llvm-release")]:
            bad = copy.deepcopy(self.spec)
            bad["kind"], bad["source_type"] = kind, source
            with self.assertRaises(ReleaseMirrorError):
                verify_release_spec(bad)

    def test_unknown_release_field_and_untrusted_license(self):
        for field, value in (("extra", True), ("license_reviewed", False)):
            bad = copy.deepcopy(self.spec)
            bad["release_lock"][field] = value
            with self.assertRaises(ReleaseMirrorError):
                verify_release_spec(bad)

    def test_lock_digest_url_and_size_mismatch(self):
        changes = [
            ("sha256", "0" * 64), ("asset_size", 42)
        ]
        for field, value in changes:
            bad = copy.deepcopy(self.spec)
            bad["release_lock"][field] = value
            with self.assertRaises(ReleaseMirrorError):
                verify_release_spec(bad)
        bad = copy.deepcopy(self.spec)
        bad["url"] = "https://evil.example/clang.zip"
        with self.assertRaises(ReleaseMirrorError):
            verify_release_spec(bad)

    def test_integer_identifiers_cannot_be_boolean_or_zero(self):
        for field in ("release_id", "asset_id", "asset_size", "uploader_id"):
            for value in (0, -1, True, "7"):
                bad = copy.deepcopy(self.spec)
                bad["release_lock"][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ReleaseMirrorError):
                    verify_release_spec(bad)

    def test_origin_digest_and_full_commit_required(self):
        for field, value in (("sha256", "0"*64), ("source_commit", "main")):
            bad = copy.deepcopy(self.spec)
            bad["release_lock"]["fallback"][field] = value
            with self.assertRaises(ReleaseMirrorError):
                verify_release_spec(bad)

    def test_no_http_credentials_or_moving_origin_url(self):
        for url in ("http://example.org/a.zip", "file:///tmp/a.zip",
                    "https://u:pass@example.org/a.zip",
                    "https://example.org/a.zip?token=secret",
                    "https://example.org/a.zip#x"):
            bad = copy.deepcopy(self.spec)
            bad["release_lock"]["fallback"]["url"] = url
            with self.subTest(url=url), self.assertRaises(ReleaseMirrorError):
                verify_release_spec(bad)

    def test_invalid_names_and_size_declaration_block(self):
        for key, val in (("asset_name", "../escape"),
                         ("tag", "v1/beta")):
            bad = copy.deepcopy(self.spec)
            bad["release_lock"][key] = val
            with self.assertRaises(ReleaseMirrorError):
                verify_release_spec(bad)
        bad = copy.deepcopy(self.spec)
        bad["expected_size"] += 1
        with self.assertRaises(ReleaseMirrorError):
            verify_release_spec(bad)

    def test_github_api_http_downgrade_after_redirect_is_rejected(self):
        from kernelforge.toolchains.release_mirror import github_api_json
        class UnsafeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return None
            def geturl(self):
                return "http://api.github.com/repos/ReviewedBuilder/Toolchains/releases/12199"
            def read(self, limit):
                return b"{}"
        with patch("kernelforge.toolchains.release_mirror.urlopen",
                   return_value=UnsafeResponse()) as mocked:
            with self.assertRaisesRegex(ReleaseMirrorError, "authenticated HTTPS"):
                github_api_json("https://api.github.com/repos/ReviewedBuilder/Toolchains/releases/12199")
            mocked.assert_called_once()

    def test_release_schema_requires_reviewer_lock(self):
        root = Path(__file__).resolve().parents[1]
        s = json.loads((root / "schemas/build.schema.json").read_text(encoding="utf-8"))
        profile = s["$defs"]["toolchainProfile"]
        self.assertIn("release_lock", profile["properties"])
        self.assertIn("reviewedReleaseLock", s["$defs"])
        self.assertTrue(any("release_lock" in r.get("then", {}).get("required", [])
                            for r in profile["allOf"]))


if __name__ == "__main__":
    unittest.main()
