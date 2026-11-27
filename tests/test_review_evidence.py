"""Adversarial evidence types, bounds and durable publication failures."""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kernelforge.evidence import read_json, write_json
from kernelforge.file_safety import read_regular_bytes


class BoundedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / 'evidence.json'

    def read(self, data, **kwargs):
        self.path.write_bytes(data)
        return read_json(self.path, hashlib.sha256(data).hexdigest(), **kwargs)

    def test_private_windows_handles_refuse_other_hosts_before_native_calls(self):
        from kernelforge.file_safety import _win_open
        from kernelforge.windows_junction import _create_directory_handle
        with patch('os.name', 'posix'), patch('ctypes.WinDLL', create=True) as native:
            with self.assertRaisesRegex(OSError, 'non-Windows'):
                _win_open(self.path, directory=False)
            with self.assertRaisesRegex(OSError, 'non-Windows'):
                _create_directory_handle(self.path)
        native.assert_not_called()

    def test_limit_and_strict_utf8(self):
        self.assertEqual(self.read(b'{}', max_bytes=2), {})
        with self.assertRaisesRegex(ValueError, 'size'):
            self.read(b'{} ', max_bytes=2)
        with self.assertRaises(UnicodeDecodeError):
            self.read(b'"\xff"')
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            read_json(self.path, 'unknown')
        for size in [0, -1, True, 17 * 1024 * 1024]:
            with self.subTest(size=size), self.assertRaisesRegex(ValueError, 'limit'):
                read_json(self.path, '0' * 64, max_bytes=size)

    def test_directory_and_hardlink_refused(self):
        self.path.mkdir()
        with self.assertRaises((ValueError, OSError)):
            read_json(self.path, '0' * 64)
        self.path.rmdir()
        self.path.write_bytes(b'{}')
        os.link(self.path, self.root / 'alias')
        with self.assertRaisesRegex(ValueError, 'linked'):
            read_json(self.path, hashlib.sha256(b'{}').hexdigest())

    @unittest.skipUnless(os.name == 'posix', 'POSIX symlink/FIFO fixtures')
    def test_fifo_symlink_and_parent_link_refused(self):
        mkfifo = getattr(os, 'mkfifo', None)
        if not callable(mkfifo):
            self.skipTest('POSIX FIFO creation is unavailable')
        mkfifo(self.path)
        with self.assertRaisesRegex(ValueError, 'nonregular'):
            read_json(self.path, '0' * 64)
        self.path.unlink()
        self.path.symlink_to('/dev/zero')
        with self.assertRaises(OSError):
            read_json(self.path, '0' * 64)
        alias = self.root / 'parent'
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(OSError):
            read_json(alias / 'file.json', '0' * 64)
        with self.assertRaises(OSError):
            write_json(alias / 'new.json', {})
        self.assertFalse((self.root / 'new.json').exists())

    def test_growing_file_cannot_exceed_budget(self):
        self.path.write_bytes(b'{}')
        with patch('kernelforge.file_safety.os.read', return_value=b'123'), self.assertRaisesRegex(ValueError, 'size'):
            read_regular_bytes(self.path, max_bytes=2)

    def test_size_or_timestamp_change_during_read_is_refused(self):
        self.path.write_bytes(b'{}')
        original = os.fstat
        count = 0

        def changed(descriptor):
            nonlocal count
            count += 1
            info = original(descriptor)
            if count == 1:
                return info
            from types import SimpleNamespace
            return SimpleNamespace(st_size=info.st_size, st_mtime_ns=info.st_mtime_ns + 1, st_ctime_ns=info.st_ctime_ns)

        with patch('kernelforge.file_safety.os.fstat', side_effect=changed), self.assertRaisesRegex(ValueError, 'changed'):
            read_regular_bytes(self.path, max_bytes=2)

    @unittest.skipUnless(os.name == 'posix', 'POSIX directory descriptor replacement')
    def test_parent_replacement_keeps_read_bound_to_opened_directory(self):
        parent = self.root / 'parent'
        parent.mkdir()
        (parent / 'data').write_bytes(b'original')
        native_open = os.open

        def replace_path(name, flags, *args, **kwargs):
            if name == 'data':
                parent.rename(self.root / 'retained')
                parent.mkdir()
                (parent / 'data').write_bytes(b'replacement')
            return native_open(name, flags, *args, **kwargs)

        with patch('kernelforge.file_safety.os.open', side_effect=replace_path):
            self.assertEqual(read_regular_bytes(parent / 'data', max_bytes=32), b'original')

    def test_failed_file_fsync_does_not_publish(self):
        with patch('kernelforge.evidence.os.fsync', side_effect=OSError('flush failed')), self.assertRaises(OSError):
            write_json(self.path, {})
        self.assertFalse(self.path.exists())

    @unittest.skipUnless(os.name == 'posix', 'POSIX directory fsync')
    def test_failed_directory_flush_reports_failure_after_atomic_publication(self):
        with patch('kernelforge.evidence.os.fsync', side_effect=[None, OSError('directory flush failed')]), self.assertRaises(OSError):
            write_json(self.path, {})
        self.assertEqual(self.path.read_bytes(), b'{}\n')
        with self.assertRaises(FileExistsError):
            write_json(self.path, {})

    @unittest.skipUnless(os.name == 'nt', 'Windows junction fixture')
    def test_reparse_parent_and_file_refused(self):
        from kernelforge.windows_junction import create_junction

        target = self.root / 'target'
        target.mkdir()
        create_junction(target, self.root / 'junction')
        self.addCleanup(os.rmdir, self.root / 'junction')
        with self.assertRaisesRegex(ValueError, 'linked'):
            read_json(self.root / 'junction' / 'evidence.json', '0' * 64)
        with self.assertRaisesRegex(ValueError, 'linked'):
            write_json(self.root / 'junction' / 'evidence.json', {})
        with self.assertRaisesRegex(ValueError, 'linked'):
            read_json(self.root / 'junction', '0' * 64)
