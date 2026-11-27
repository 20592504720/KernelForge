"""Interpreter identity, offline configuration and safe reuse/repair regression."""
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import unittest
import venv
import zipfile
from pathlib import Path
from unittest.mock import patch

from kernelforge.python_environment import (
    _check_windows_dacl,
    _integrity_directory,
    _owned_directory,
    _write_integrity_record,
    initialize,
    isolated_environment,
    locked_requirements,
    validate_environment,
)
from kernelforge.toolchains.locking import FileLock, LockTimeout


class EnvironmentReviewTests(unittest.TestCase):
    def test_real_offline_install_and_explicit_repair(self):
        # A local wheel fixture exercises pip and the subsequent actual import
        # without a network, package index, build backend or host site packages.
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root, wheels = base / 'project', base / 'wheels'
            root.mkdir()
            wheels.mkdir(mode=0o700)
            wheel = wheels / 'attrs-0.0.0-py3-none-any.whl'
            entries = {
                'attrs/__init__.py': 'OFFLINE_FIXTURE = True\n',
                'attrs-0.0.0.dist-info/METADATA': 'Metadata-Version: 2.1\nName: attrs\nVersion: 0.0.0\n',
                'attrs-0.0.0.dist-info/WHEEL': 'Wheel-Version: 1.0\nGenerator: KernelForge test\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
            }
            entries['attrs-0.0.0.dist-info/RECORD'] = ''.join(f'{name},,\n' for name in [*entries, 'attrs-0.0.0.dist-info/RECORD'])
            with zipfile.ZipFile(wheel, 'x') as archive:
                for name, text in entries.items():
                    archive.writestr(name, text)
            lock = f'--require-hashes\n--only-binary=:all:\nattrs==0.0.0 --hash=sha256:{hashlib.sha256(wheel.read_bytes()).hexdigest()}\n'.encode()
            (root / 'requirements-dev.txt').write_bytes(lock)
            key = hashlib.sha256(lock).hexdigest()[:16]
            destination = base / 'cache/python' / f'{platform.system().lower()}-{sys.version_info.major}{sys.version_info.minor}-{key}'
            destination.mkdir(parents=True, mode=0o700)
            (destination / 'preserve').write_bytes(b'damaged-environment')
            pending = destination.with_name(destination.name + '.pending.json')
            pending.write_text('{}', encoding='utf-8')
            with patch.dict(os.environ, {'PIP_INDEX_URL': 'https://untrusted.invalid', 'PYTHONPATH': str(base / 'untrusted')}):
                executable = initialize(root, wheels, repair=True)
            self.assertEqual(validate_environment(executable, destination, {'attrs': '0.0.0'})['packages']['attrs']['version'], '0.0.0')
            retained = list(destination.parent.glob(destination.name + '.damaged-*'))
            self.assertEqual(len(retained), 1)
            self.assertEqual((retained[0] / 'preserve').read_bytes(), b'damaged-environment')
            self.assertFalse(pending.exists())
            self.assertEqual(len(list(destination.parent.glob(pending.name + '.retained-*'))), 1)
            self.assertEqual(len(list(destination.parent.glob(pending.name + '.completed-*'))), 1)

    @unittest.skipUnless(os.name == 'nt', 'Windows native ACL enforcement')
    def test_native_acl_foreign_write_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cache'
            path.mkdir()
            _owned_directory(path)
            try:
                subprocess.run(['icacls', str(path), '/grant', '*S-1-1-0:(OI)(CI)(W)'], check=True, capture_output=True, timeout=15)
                with self.assertRaisesRegex(ValueError, 'unrelated users'):
                    _owned_directory(path)
            finally:
                subprocess.run(['icacls', str(path), '/remove:g', '*S-1-1-0'], check=True, capture_output=True, timeout=15)

    def test_windows_acl_null_unknown_and_foreign_write_refused(self):
        user = 'S-1-5-21-123-1001'
        for descriptor in ['O:' + user, 'D:NO_ACCESS_CONTROL', 'D:(A;;FA;;;WD)',
                           'D:(A;;0x2;;;AU)', 'D:(A;;FW;;;S-1-5-21-123-1002)',
                           'D:(XA;;FA;;;WD)', 'D:(A;;ZZ;;;WD)']:
            with self.subTest(descriptor=descriptor), self.assertRaises(ValueError):
                _check_windows_dacl(descriptor, user)
        _check_windows_dacl(f'D:(A;;FA;;;{user})(A;;FA;;;SY)(A;;FA;;;BA)(A;;FR;;;BU)', user)
        _check_windows_dacl('D:(A;IO;FA;;;WD)', user)

    def test_explicit_repair_retains_old_environment_on_offline_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'project'
            root.mkdir()
            damaged = root.parent / 'cache/python' / self.destination.name
            damaged.mkdir(parents=True, mode=0o700)
            (damaged / 'original').write_bytes(b'keep')
            with patch('kernelforge.python_environment.locked_requirements', return_value=(self.lock, {})), self.assertRaises(OSError):
                initialize(root, root / 'missing', repair=True)
            retained = list(damaged.parent.glob(damaged.name + '.damaged-*'))
            self.assertEqual(len(retained), 1)
            self.assertEqual((retained[0] / 'original').read_bytes(), b'keep')

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name)
        cls.root = cls.base / 'project'
        cls.root.mkdir()
        cls.lock = b'fixture identity used only by the controlled tests'
        key = hashlib.sha256(cls.lock).hexdigest()[:16]
        cls.destination = cls.base / 'cache/python' / f'{platform.system().lower()}-{sys.version_info.major}{sys.version_info.minor}-{key}'
        venv.EnvBuilder(with_pip=True).create(cls.destination)
        cls.executable = cls.destination / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        _write_integrity_record(cls.destination, lock_sha256=hashlib.sha256(cls.lock).hexdigest(),
                                wheel_sha256=[])

    def test_real_interpreter_and_import_probe(self):
        result = validate_environment(self.executable, self.destination, {})
        self.assertEqual(result['version'], list(sys.version_info[:3]))
        with self.assertRaisesRegex(ValueError, 'import/identity'):
            validate_environment(self.executable, self.destination, {'jsonschema': '0.0.0'})

    def test_cached_dependency_tampering_is_rejected_before_interpreter_start(self):
        package = self.destination / ('Lib/site-packages/pip/__init__.py' if os.name == 'nt'
                                      else f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages/pip/__init__.py')
        original = package.read_bytes()
        try:
            package.write_bytes(original + b'\n# tampered after sealing\n')
            with patch('kernelforge.python_environment.subprocess.run') as run, \
                    self.assertRaisesRegex(ValueError, 'contents differ'):
                validate_environment(self.executable, self.destination, {})
            run.assert_not_called()
        finally:
            package.write_bytes(original)

    def test_unreviewed_python_startup_configuration_is_rejected_before_execution(self):
        site_packages = self.destination / ('Lib/site-packages' if os.name == 'nt'
                                             else f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages')
        startup = site_packages / 'sitecustomize.py'
        startup.write_text("raise RuntimeError('must not execute')\n", encoding='utf-8')
        try:
            with patch('kernelforge.python_environment.subprocess.run') as run, \
                    self.assertRaisesRegex(ValueError, 'startup configuration'):
                validate_environment(self.executable, self.destination, {})
            run.assert_not_called()
        finally:
            startup.unlink()

    def test_missing_independent_integrity_record_is_rejected_before_execution(self):
        record = _integrity_directory(self.destination) / f'{self.destination.name}.json'
        retained = record.with_name(record.name + '.test-retained')
        record.rename(retained)
        try:
            with patch('kernelforge.python_environment.subprocess.run') as run, \
                    self.assertRaises(OSError):
                validate_environment(self.executable, self.destination, {})
            run.assert_not_called()
        finally:
            retained.rename(record)

    def test_integrity_record_lock_identity_is_checked_before_interpreter_start(self):
        with patch('kernelforge.python_environment.subprocess.run') as run, \
                self.assertRaisesRegex(ValueError, 'integrity record identity'):
            validate_environment(self.executable, self.destination, {}, lock_sha256='0' * 64)
        run.assert_not_called()

    def test_unreviewed_virtual_environment_setting_is_rejected_before_execution(self):
        config = self.destination / 'pyvenv.cfg'
        original = config.read_bytes()
        try:
            config.write_bytes(original + b'startup-path = untrusted\n')
            with patch('kernelforge.python_environment.subprocess.run') as run, \
                    self.assertRaisesRegex(ValueError, 'startup configuration'):
                validate_environment(self.executable, self.destination, {})
            run.assert_not_called()
        finally:
            config.write_bytes(original)

    def test_valid_environment_is_reused_without_creation_or_pip(self):
        before = (self.destination / 'pyvenv.cfg').read_bytes()
        with patch('kernelforge.python_environment.locked_requirements', return_value=(self.lock, {})), patch('kernelforge.python_environment.venv.EnvBuilder') as builder:
            actual = initialize(self.root, self.base / 'missing-wheelhouse')
        self.assertEqual(actual, self.executable)
        builder.assert_not_called()
        self.assertEqual(before, (self.destination / 'pyvenv.cfg').read_bytes())

    def test_venv_base_executable_is_validated_independently_of_current_python(self):
        config = self.destination / 'pyvenv.cfg'
        original_config = config.read_bytes()
        lines = original_config.decode('utf-8').splitlines()
        base_executable = sys.__dict__['_base_executable']
        lines = [f'executable = {base_executable}' if line.startswith('executable = ')
                 else line for line in lines]
        config.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        record = _integrity_directory(self.destination) / f'{self.destination.name}.json'
        retained_record = record.with_name(record.name + '.test-retained')
        record.rename(retained_record)
        try:
            _write_integrity_record(self.destination, lock_sha256=hashlib.sha256(self.lock).hexdigest(),
                                    wheel_sha256=[])
            with patch('kernelforge.python_environment.sys.executable', str(self.executable)):
                result = validate_environment(self.executable, self.destination, {})
            self.assertEqual(Path(result['base_executable']).resolve(), Path(base_executable).resolve())
        finally:
            record.unlink(missing_ok=True)
            retained_record.rename(record)
            config.write_bytes(original_config)

    def test_system_packages_and_corruption_refused_without_deleting_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder)
            configuration = destination / 'pyvenv.cfg'
            configuration.write_text('include-system-site-packages = true\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'exclude system'):
                validate_environment(self.executable, destination, {})

    def test_damaged_environment_is_retained(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'project'
            root.mkdir()
            key = hashlib.sha256(self.lock).hexdigest()[:16]
            damaged = root.parent / 'cache/python' / self.destination.name
            damaged.mkdir(parents=True, mode=0o700)
            (damaged / 'preserve.txt').write_text(key, encoding='utf-8')
            with patch('kernelforge.python_environment.locked_requirements', return_value=(self.lock, {})), self.assertRaisesRegex(ValueError, 'damaged; retained'):
                initialize(root, root / 'missing')
            self.assertEqual((damaged / 'preserve.txt').read_text(), key)

    def test_foreign_pip_and_python_configuration_is_removed(self):
        with patch.dict(os.environ, {'PIP_INDEX_URL': 'https://untrusted.invalid', 'PIP_CONFIG_FILE': 'untrusted.ini', 'PYTHONPATH': 'untrusted', 'PYTHONHOME': 'untrusted'}):
            result = isolated_environment()
        self.assertNotIn('PIP_INDEX_URL', result)
        self.assertNotIn('PYTHONPATH', result)
        self.assertNotIn('PYTHONHOME', result)
        self.assertEqual(result['PIP_CONFIG_FILE'], os.devnull)

    def test_requirement_options_and_direct_urls_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for text in ['--extra-index-url https://bad.invalid', 'jsonschema @ https://bad.invalid/file.whl', 'jsonschema==4.26.0', '--find-links ../other']:
                with self.subTest(text=text):
                    (root / 'requirements-dev.txt').write_text(text, encoding='utf-8')
                    with self.assertRaisesRegex(ValueError, 'unreviewed'):
                        locked_requirements(root)

    def test_interrupted_marker_requires_explicit_repair(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'project'
            root.mkdir()
            cache = root.parent / 'cache/python'
            cache.mkdir(parents=True, mode=0o700)
            marker = cache / (self.destination.name + '.pending.json')
            marker.write_text('{}', encoding='utf-8')
            with patch('kernelforge.python_environment.locked_requirements', return_value=(self.lock, {})), self.assertRaisesRegex(ValueError, 'interrupted'):
                initialize(root, root / 'missing')
            self.assertTrue(marker.exists())

    def test_lock_blocks_competing_initializer(self):
        cache = self.destination.parent
        with FileLock(cache / (self.destination.name + '.lock'), timeout=0), patch('kernelforge.python_environment.FileLock', side_effect=lambda path, **kw: FileLock(path, timeout=0)), patch('kernelforge.python_environment.locked_requirements', return_value=(self.lock, {})), self.assertRaises(LockTimeout):
            initialize(self.root, self.base / 'missing')

    @unittest.skipUnless(os.name == 'posix', 'POSIX mode and symlink fixtures')
    def test_unowned_writable_and_linked_cache_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            root.chmod(0o777)
            with self.assertRaisesRegex(ValueError, 'writable'):
                _owned_directory(root)
            root.chmod(0o700)
            alias = root / 'linked'
            alias.symlink_to(root, target_is_directory=True)
            with self.assertRaises(OSError):
                _owned_directory(alias)

    def test_offline_pip_loads_no_configuration(self):
        # Verify the installed pip's actual configuration loader with the same
        # isolated interpreter/environment used for installs, without installing.
        code = 'from pip._internal.configuration import Configuration; c=Configuration(isolated=True); c.load(); import json; print(json.dumps(dict(c.items())))'
        result = subprocess.run([str(self.executable), '-B', '-I', '-c', code], env=isolated_environment(), capture_output=True, check=True, timeout=30)
        self.assertEqual(json.loads(result.stdout), {})
