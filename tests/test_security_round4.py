"""Offline failure, concurrency and resource-limit regression cases."""
import concurrent.futures
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from kernelforge.bounded_process import run_bounded_capture
from kernelforge.build import BuildError, run_build
from kernelforge.toolchains.locking import FileLock, LockTimeout, _pid_alive
from kernelforge.toolchains.manager import ToolchainManager
from kernelforge.build_cache import BuildCacheNamespaces, BuildCacheError


class RecoveryTests(unittest.TestCase):
    def test_stale_recovery_serialized_across_contenders(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "lock"
            path.mkdir()
            (path / "owner.json").write_text(json.dumps({"host": socket.gethostname(), "pid": 99999999}))
            old = time.time() - 1000
            os.utime(path, (old, old))
            active = 0
            mutex = threading.Lock()
            def task(_):
                nonlocal active
                with FileLock(path, timeout=8, stale_after=.01):
                    with mutex:
                        active += 1
                        self.assertEqual(active, 1)
                    time.sleep(.01)
                    with mutex:
                        active -= 1
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
                list(pool.map(task, range(12)))
            self.assertFalse(path.exists())

    def test_replaced_owner_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "lock"
            lock = FileLock(path)
            with self.assertRaisesRegex(LockTimeout, "ownership changed"):
                with lock:
                    (path / "owner.json").write_text('{"token":"different"}')
            self.assertTrue((path / "owner.json").is_file())

    def test_malformed_stale_owner_retained(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "lock"
            path.mkdir()
            (path / "owner.json").write_text("{}")
            old = time.time() - 1000
            os.utime(path, (old, old))
            with self.assertRaises(LockTimeout):
                with FileLock(path, timeout=.02, stale_after=.01, poll=.005):
                    self.fail("unexpected ownership")
            self.assertTrue(path.exists())

    def test_current_process_is_alive(self):
        self.assertTrue(_pid_alive(os.getpid()))

    def test_cross_workspace_output_serialized(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            entered = threading.Event()
            release = threading.Event()
            def fake_build(*args):
                entered.set()
                self.assertTrue(release.wait(5))
                return {}
            with patch("kernelforge.build._run_build", side_effect=fake_build):
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    first = pool.submit(run_build, {}, root/"a", root/"out")
                    try:
                        self.assertTrue(entered.wait(5))
                        with self.assertRaisesRegex(BuildError, "lock exists"):
                            run_build({}, root/"b", root/"out")
                    finally:
                        release.set()
                    self.assertEqual(first.result(timeout=5), {})

    def test_abandoned_toolchain_lease_blocks_cleanup(self):
        with tempfile.TemporaryDirectory() as td:
            mgr = ToolchainManager(Path(td)/"cache")
            uses = mgr.cache_dir / "uses"
            uses.mkdir(parents=True)
            key = "a"*64
            marker = uses / (key + ".old.use")
            marker.write_text("malformed")
            old = time.time() - 100000
            os.utime(marker, (old, old))
            self.assertTrue(mgr._has_live_use(key))
            self.assertTrue(marker.exists())

    def test_invalid_prune_key_fails_before_lock_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)/"cache"
            ctl = BuildCacheNamespaces(root)
            with self.assertRaisesRegex(BuildCacheError, "namespace key"):
                ctl.prune("../elsewhere", dry_run=False)
            self.assertFalse(root.exists())


class CaptureTests(unittest.TestCase):
    def capture(self, code, *, limit=1024, timeout=10):
        with tempfile.TemporaryDirectory() as td:
            evidence = {}
            with tempfile.TemporaryFile(mode="w+b", dir=td) as spool:
                rc = run_bounded_capture([sys.executable, "-c", code], cwd=td,
                                         env=os.environ.copy(), timeout=timeout,
                                         spool=spool, disk_path=td, evidence=evidence,
                                         max_bytes=limit)
                spool.seek(0)
                return rc, spool.read(), evidence

    def test_noisy_process_drained_and_partial_line_dropped(self):
        rc, content, evidence = self.capture("import sys; sys.stdout.buffer.write(b'ok\\n'+b'x'*200000)", limit=64)
        self.assertEqual(rc, 0)
        self.assertEqual(content, b"ok\n")
        self.assertTrue(evidence["raw_capture_truncated"])
        self.assertLessEqual(evidence["raw_spool_bytes"], 64)

    def test_regular_exit_and_stderr_preserved(self):
        rc, content, evidence = self.capture("import sys; print('normal'); print('error',file=sys.stderr); sys.exit(7)")
        self.assertEqual(rc, 7)
        self.assertIn(b"normal", content)
        self.assertIn(b"error", content)
        self.assertFalse(evidence["raw_capture_truncated"])

    def test_timeout_releases_direct_child(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            self.capture("import time; time.sleep(10)", timeout=.2)

    def test_disk_reserve_refuses_before_spawn(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryFile(mode="w+b") as spool:
            with patch("kernelforge.bounded_process.shutil.disk_usage", return_value=type("Disk", (), {"free": 0})()), \
                    patch("kernelforge.bounded_process.subprocess.Popen") as spawn:
                with self.assertRaisesRegex(OSError, "reserve"):
                    run_bounded_capture(["unused"], cwd=td, env={}, timeout=1,
                                        spool=spool, disk_path=td, evidence={})
                spawn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
