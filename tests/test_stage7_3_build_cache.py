"""Stage 7.3 ccache identity and namespace safety tests, no ccache binary."""
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from kernelforge.build_cache import (
    BuildCacheError,
    BuildCacheNamespaces,
    cache_key,
    digest_file,
    verify_identity,
)


def pinned():
    return {
        "schema_version": 1,
        "device": "oneplus13-pjz110", "kernel_version": "6.6",
        "build_mode": "vendor", "target_arch": "aarch64",
        "source_repository": "https://github.com/OnePlusOSS/kernel_oneplus_sm8750",
        "source_commit": "a" * 40,
        "manifest_lock_sha256": "1" * 64,
        "compiler_sha256": "2" * 64, "compiler_version": "18.0.0",
        "root_provider": "bakasu", "root_commit": "b" * 40,
        "susfs_enabled": True, "susfs_commit": "c" * 40,
        "patch_lock_sha256": "3" * 64, "config_sha256": "4" * 64,
        "build_arguments_sha256": "5" * 64,
        "effective_environment_sha256": "6" * 64,
    }


class IdentityTests(unittest.TestCase):
    def test_reviewed_identity_is_deterministic_and_order_independent(self):
        x = pinned()
        y = dict(reversed(list(x.items())))
        self.assertEqual(cache_key(x), cache_key(y))
        self.assertEqual(verify_identity(x), x)
        self.assertEqual(len(cache_key(x)), 64)

    def test_each_build_dimension_is_isolated(self):
        original = pinned()
        mutations = {
            "device": "oneplus13s",
            "kernel_version": "6.12",
            "build_mode": "gki",
            "target_arch": "riscv64",
            "source_repository": "https://github.com/vendor/kernel-other",
            "source_commit": "f" * 40,
            "manifest_lock_sha256": "f" * 64,
            "compiler_sha256": "f" * 64,
            "compiler_version": "19.0.0",
            "root_provider": "official",
            "root_commit": "f" * 40,
            "susfs_commit": "f" * 40,
            "patch_lock_sha256": "f" * 64,
            "config_sha256": "f" * 64,
            "build_arguments_sha256": "f" * 64,
            "effective_environment_sha256": "f" * 64,
        }
        key = cache_key(original)
        for field, val in mutations.items():
            changed = dict(original, **{field: val})
            with self.subTest(field=field):
                self.assertNotEqual(key, cache_key(changed))
        disabled = dict(original, susfs_enabled=False, susfs_commit=None)
        self.assertNotEqual(key, cache_key(disabled))
        no_root = dict(original, root_provider="none", root_commit=None,
                       susfs_enabled=False, susfs_commit=None)
        self.assertNotEqual(key, cache_key(no_root))

    def test_unknown_missing_unpinned_or_moving_values_are_rejected(self):
        source = pinned()
        cases = [
            dict(source, config_sha256="0"),
            dict(source, source_commit="main"),
            dict(source, compiler_sha256="A" * 64),
            dict(source, root_commit="latest_branch"),
            dict(source, susfs_commit=None),
            dict(source, source_repository="https://token@host/kernel"),
            dict(source, schema_version=True),
            dict(source, susfs_enabled="true"),
            dict(source, root_provider="none"),
            dict(source, extra_field="untrusted"),
        ]
        for index, c in enumerate(cases):
            with self.subTest(case=index), self.assertRaises(BuildCacheError):
                cache_key(c)
        missing = dict(source)
        missing.pop("patch_lock_sha256")
        with self.assertRaises(BuildCacheError):
            cache_key(missing)

    def test_file_digest_reacts_to_actual_byte_change(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "clang"
            p.write_bytes(b"trusted")
            expected = digest_file(p)
            self.assertEqual(expected, __import__("hashlib").sha256(b"trusted").hexdigest())
            p.write_bytes(b"modified")
            self.assertNotEqual(expected, digest_file(p))

    def test_cache_key_not_merely_filename_or_label(self):
        x = pinned()
        changed = dict(x, compiler_sha256="f"*64)
        self.assertNotEqual(cache_key(x), cache_key(changed))


class NamespaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manager = BuildCacheNamespaces(self.root / "ccache", max_size_mib=512)

    def test_namespace_creation_exports_isolated_overlay_and_records_lease(self):
        with self.manager.open(pinned()) as lease:
            env = lease.environment()
            self.assertEqual(env["CCACHE_COMPILERCHECK"], "content")
            self.assertEqual(env["CCACHE_MAXSIZE"], "512M")
            self.assertTrue(Path(env["CCACHE_DIR"]).is_dir())
            self.assertEqual(self.manager.inspect(lease.key)["active_or_unreconciled_leases"], 1)
        self.assertEqual(self.manager.inspect(lease.key)["active_or_unreconciled_leases"], 0)

    def test_repeated_identity_reuses_one_namespace_without_rewrite(self):
        with self.manager.open(pinned()) as a:
            location = a.path
        marker = location / ".kernelforge-ccache-identity.json"
        old = marker.read_bytes()
        with self.manager.open(pinned()) as b:
            self.assertEqual(location, b.path)
        self.assertEqual(marker.read_bytes(), old)

    def test_separate_device_and_root_use_distinct_directories(self):
        x = pinned()
        y = dict(x, device="device2")
        with self.manager.open(x) as a, self.manager.open(y) as b:
            self.assertNotEqual(a.path, b.path)

    def test_concurrent_same_identity_holds_individual_leases(self):
        def run_once(_):
            with self.manager.open(pinned()) as lease:
                return lease.key
        with ThreadPoolExecutor(max_workers=4) as pool:
            result = list(pool.map(run_once, range(8)))
        self.assertEqual(len(set(result)), 1)
        self.assertEqual(self.manager.inspect(result[0])["active_or_unreconciled_leases"], 0)

    def test_uncertified_nonempty_root_never_claimed_or_deleted(self):
        root = self.root / "existing"
        root.mkdir()
        (root / "user.txt").write_text("valuable")
        mgr = BuildCacheNamespaces(root)
        with self.assertRaisesRegex(BuildCacheError, "unowned nonempty"):
            mgr.open(pinned())
        self.assertEqual((root / "user.txt").read_text(), "valuable")

    def test_source_overlap_and_source_parent_rejected(self):
        source = self.root / "repo/source"
        source.mkdir(parents=True)
        for root in (source / "cache", source, source.parent):
            with self.subTest(root=root), self.assertRaisesRegex(BuildCacheError, "overlaps"):
                BuildCacheNamespaces(root, forbidden_roots=(source,))

    def test_symlink_root_refused_when_supported(self):
        original = self.root / "real"
        original.mkdir()
        link = self.root / "link"
        try:
            link.symlink_to(original, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unsupported")
        with self.assertRaisesRegex(BuildCacheError, "symlink"):
            BuildCacheNamespaces(link)

    def test_metadata_poisoning_blocks_reuse_and_cleanup(self):
        with self.manager.open(pinned()) as lease:
            key = lease.key
            p = lease.path / ".kernelforge-ccache-identity.json"
        obj = json.loads(p.read_text())
        obj["identity"]["compiler_sha256"] = "f"*64
        p.write_text(json.dumps(obj))
        with self.assertRaisesRegex(BuildCacheError, "identity mismatch"):
            self.manager.open(pinned())
        with self.assertRaises(BuildCacheError):
            self.manager.prune(key, dry_run=False)
        self.assertTrue(p.exists())

    def test_dry_run_does_not_delete_valid_namespace(self):
        with self.manager.open(pinned()) as lease:
            key, ns = lease.key, lease.path
        result = self.manager.prune(key)
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["removed"])
        self.assertTrue(ns.exists())

    def test_explicit_cleanup_blocks_live_or_stale_use(self):
        with self.manager.open(pinned()) as lease:
            with self.assertRaisesRegex(BuildCacheError, "lease blocks cleanup"):
                self.manager.prune(lease.key, dry_run=False)
            key, ns = lease.key, lease.path
        fake_use = self.manager.root / "uses" / f"{key}.crashed.use"
        fake_use.write_text("untrusted marker")
        with self.assertRaisesRegex(BuildCacheError, "lease blocks cleanup"):
            self.manager.prune(key, dry_run=False)
        fake_use.unlink()
        result = self.manager.prune(key, dry_run=False)
        self.assertTrue(result["removed"])
        self.assertFalse(ns.exists())

    def test_existing_symlinked_lease_or_lock_dir_is_rejected(self):
        for name in ("uses", "locks"):
            with self.subTest(name=name):
                root = self.root / ("symlink-" + name)
                root.mkdir()
                outside = self.root / ("outside-" + name)
                outside.mkdir()
                link = root / name
                try:
                    link.symlink_to(outside, target_is_directory=True)
                except (OSError, NotImplementedError):
                    self.skipTest("symlink unsupported")
                other = BuildCacheNamespaces(root)
                with self.assertRaises(BuildCacheError):
                    other.open(pinned())
                self.assertEqual(list(outside.iterdir()), [])

    def test_namespace_parent_symlink_is_never_followed_by_prune_or_inspect(self):
        with self.manager.open(pinned()) as lease:
            key = lease.key
        top = self.manager.root / "namespaces"
        actual = self.manager.root / "namespaces-physical"
        top.rename(actual)
        try:
            top.symlink_to(actual, target_is_directory=True)
        except (OSError, NotImplementedError):
            actual.rename(top)
            self.skipTest("directory symlink unsupported on this host")
        real_metadata = actual / key[:2] / key / ".kernelforge-ccache-identity.json"
        self.assertTrue(real_metadata.exists())
        with self.assertRaisesRegex(BuildCacheError, "symlink"):
            self.manager.prune(key, dry_run=False)
        with self.assertRaisesRegex(BuildCacheError, "symlink"):
            self.manager.inspect(key)
        self.assertTrue(real_metadata.exists())

    def test_cache_not_system_disk_quota_and_no_fake_hits(self):
        with self.manager.open(pinned()) as lease:
            status = self.manager.inspect(lease.key)
        self.assertEqual(status["hit_rate"], "UNTESTED")
        self.assertEqual(status["physical_disk_quota"], "NOT_ENFORCED")
        self.assertEqual(status["compiler_cache_used"], "UNTESTED")

    def test_corrupt_root_marker_prevents_changes(self):
        with self.manager.open(pinned()):
            pass
        marker = self.manager.root / ".kernelforge-ccache-root.json"
        marker.write_text("not-json")
        with self.assertRaises(BuildCacheError):
            self.manager.open(pinned())


if __name__ == "__main__":
    unittest.main()
