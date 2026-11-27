"""Validate and initialize an owned, lock-keyed offline development environment.

Cache and interpreter directories are trusted code: equal-rights writers and
administrators can change executable code and remain outside this boundary.
Damaged or interrupted environments are retained, never silently overwritten.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import sys
import sysconfig
import tempfile
import uuid
import venv
from pathlib import Path

from .file_safety import pinned_parent, read_regular_bytes
from .path_policy import require_external_paths
from .toolchains.locking import FileLock

_IMPORTS = {'attrs': 'attrs', 'jsonschema-specifications': 'jsonschema_specifications',
            'jsonschema': 'jsonschema', 'pyyaml': 'yaml', 'referencing': 'referencing',
            'rpds-py': 'rpds', 'typing-extensions': 'typing_extensions'}
_PROBE = """import importlib, importlib.metadata, json, os, platform, sys
expected = json.loads(sys.argv[1])
import pip
packages = {}
for name, (version, module) in expected.items():
    imported = importlib.import_module(module)
    packages[name] = {'version': importlib.metadata.version(name), 'file': imported.__file__}
print(json.dumps({'executable': sys.executable, 'prefix': sys.prefix, 'base_prefix': sys.base_prefix,
 'base_executable': sys._base_executable, 'version': list(sys.version_info[:3]),
 'implementation': platform.python_implementation(), 'machine': platform.machine(), 'pip_file': pip.__file__, 'packages': packages}))
"""


def isolated_environment() -> dict[str, str]:
    environment = {k: v for k, v in os.environ.items() if not k.upper().startswith(('PYTHON', 'PIP_'))
                   and k.upper() not in {'VIRTUAL_ENV', '__PYVENV_LAUNCHER__'}}
    environment.update(PIP_CONFIG_FILE=os.devnull, PIP_NO_INPUT='1',
                       PIP_DISABLE_PIP_VERSION_CHECK='1', PYTHONDONTWRITEBYTECODE='1')
    return environment


def locked_requirements(root: Path) -> tuple[bytes, dict[str, str]]:
    data = read_regular_bytes(root / 'requirements-dev.txt', max_bytes=65536)
    expected = {}
    for line in data.decode('utf-8', errors='strict').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line in {'--require-hashes', '--only-binary=:all:'}:
            continue
        match = re.fullmatch(r'([\w-]+)==([^\s;]+)((?: --hash=sha256:[a-f0-9]{64})+)', line)
        if not match or match[1] not in _IMPORTS or match[1] in expected:
            raise ValueError('offline dependency lock contains an unreviewed requirement or option')
        expected[match[1]] = match[2]
    if not expected:
        raise ValueError('offline dependency lock is empty')
    return data, expected


def _check_windows_dacl(descriptor: str, user_sid: str) -> None:
    """Conservatively reject write grants to anyone except user/SYSTEM/admins.

    Inherit-only ACEs do not grant access to this directory. Unknown allow ACE
    forms fail closed; a null/missing DACL must never be treated as private.
    """
    if 'D:' not in descriptor or 'NO_ACCESS_CONTROL' in descriptor:
        raise ValueError('environment cache must have a non-null ACL')
    trusted = {user_sid, 'SY', 'BA', 'OW', 'S-1-5-18', 'S-1-5-32-544'}
    write_mask = 0x500D0156
    for ace in re.findall(r'\(([^()]*)\)', descriptor):
        fields = ace.split(';')
        if len(fields) != 6:
            raise ValueError('environment cache ACL contains an unsupported ACE')
        kind, flags, rights, _, _, trustee = fields
        if 'IO' in flags or kind == 'D':
            continue
        if kind != 'A':
            raise ValueError('environment cache ACL contains an unsupported ACE')
        if trustee in trusted:
            continue
        if rights.startswith('0x'):
            writable = bool(int(rights, 16) & write_mask)
        else:
            tokens = re.findall('..', rights)
            if ''.join(tokens) != rights or any(token not in {'GR', 'GX', 'FR', 'FX', 'RC', 'LC', 'LO', 'SW', 'GA', 'GW', 'FA', 'FW', 'WD', 'WO', 'DC', 'SD', 'CC', 'WP'} for token in tokens):
                raise ValueError('environment cache ACL contains unsupported rights')
            writable = any(token in {'GA', 'GW', 'FA', 'FW', 'WD', 'WO', 'DC', 'SD', 'CC', 'WP'} for token in tokens)
        if writable:
            raise ValueError('environment cache ACL grants write access to unrelated users')


def _owned_directory(path: Path, *, create: bool = False) -> None:
    # Descriptor walk rejects linked parents. Cache roots must be caller-owned
    # and private from unrelated writers; Windows ACLs are inspected separately.
    with pinned_parent(path / '.ownership-check', create=create) as descriptor:
        info = os.fstat(descriptor) if descriptor is not None else path.stat()
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError('environment cache is not a directory')
        if os.name == 'posix' and (info.st_uid != os.getuid() or info.st_mode & 0o022):
            raise ValueError('environment cache must be owned by the caller and not group/world writable')
        if os.name == 'nt':
            # Use the Windows security descriptor rather than meaningless st_uid.
            import ctypes
            from ctypes import wintypes

            security = ctypes.WinDLL('advapi32', use_last_error=True)
            security.GetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
            security.GetFileSecurityW.restype = wintypes.BOOL
            needed = wintypes.DWORD()
            security.GetFileSecurityW(str(path), 5, None, 0, ctypes.byref(needed))
            if needed.value == 0 or needed.value > 65536:
                raise OSError('cannot inspect environment cache owner and ACL')
            buffer = ctypes.create_string_buffer(needed.value)
            if not security.GetFileSecurityW(str(path), 5, buffer, needed.value, ctypes.byref(needed)):
                raise ctypes.WinError(ctypes.get_last_error())
            # Convert SDDL locally; never include user SIDs in diagnostics.
            security.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(wintypes.DWORD)]
            security.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = wintypes.BOOL
            text = wintypes.LPWSTR()
            if not security.ConvertSecurityDescriptorToStringSecurityDescriptorW(buffer, 1, 5, ctypes.byref(text), None):
                raise ctypes.WinError(ctypes.get_last_error())
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.LocalFree.argtypes = [wintypes.LPVOID]
            kernel.LocalFree.restype = wintypes.LPVOID
            try:
                security.GetSecurityDescriptorOwner.argtypes = [wintypes.LPVOID, ctypes.POINTER(wintypes.LPVOID), ctypes.POINTER(wintypes.BOOL)]
                security.GetSecurityDescriptorOwner.restype = wintypes.BOOL
                security.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
                security.OpenProcessToken.restype = wintypes.BOOL
                security.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
                security.GetTokenInformation.restype = wintypes.BOOL
                security.EqualSid.argtypes = [wintypes.LPVOID, wintypes.LPVOID]
                security.EqualSid.restype = wintypes.BOOL
                kernel.GetCurrentProcess.restype = wintypes.HANDLE
                kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                owner_sid, defaulted, token = wintypes.LPVOID(), wintypes.BOOL(), wintypes.HANDLE()
                if not security.GetSecurityDescriptorOwner(buffer, ctypes.byref(owner_sid), ctypes.byref(defaulted)):
                    raise ctypes.WinError(ctypes.get_last_error())
                if not security.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
                    raise ctypes.WinError(ctypes.get_last_error())
                try:
                    token_bytes = wintypes.DWORD()
                    security.GetTokenInformation(token, 1, None, 0, ctypes.byref(token_bytes))
                    token_user = ctypes.create_string_buffer(token_bytes.value)
                    if not security.GetTokenInformation(token, 1, token_user, token_bytes, ctypes.byref(token_bytes)):
                        raise ctypes.WinError(ctypes.get_last_error())
                    user_sid = ctypes.cast(token_user, ctypes.POINTER(wintypes.LPVOID))[0]
                    if not security.EqualSid(owner_sid, user_sid):
                        raise ValueError('environment cache must be owned by the invoking user')
                    security.ConvertSidToStringSidW.argtypes = [wintypes.LPVOID, ctypes.POINTER(wintypes.LPWSTR)]
                    security.ConvertSidToStringSidW.restype = wintypes.BOOL
                    user_text = wintypes.LPWSTR()
                    if not security.ConvertSidToStringSidW(user_sid, ctypes.byref(user_text)):
                        raise ctypes.WinError(ctypes.get_last_error())
                    try:
                        _check_windows_dacl(text.value or '', user_text.value or '')
                    finally:
                        kernel.LocalFree(user_text)
                finally:
                    kernel.CloseHandle(token)
            finally:
                kernel.LocalFree(text)


_INTEGRITY_SCHEMA = 'kernelforge-python-environment-integrity-v1'
_MAX_ENVIRONMENT_FILE = 256 * 1024 * 1024
_MAX_ENVIRONMENT_TOTAL = 2 * 1024 * 1024 * 1024
_FORBIDDEN_STARTUP_FILES = {'sitecustomize.py', 'usercustomize.py', 'python._pth',
                            'pythonw._pth'}


def _integrity_directory(destination: Path) -> Path:
    return destination.parent.parent / 'python-integrity'


def _environment_inventory(destination: Path) -> dict[str, dict]:
    """Hash every object without following links or trusting environment code."""
    inventory: dict[str, dict] = {}
    total = 0
    def walk_error(error: OSError) -> None:
        raise error

    for current, directories, files in os.walk(destination, topdown=True,
                                                followlinks=False, onerror=walk_error):
        current_path = Path(current)
        relative_dir = current_path.relative_to(destination)
        for name in list(directories):
            path = current_path / name
            relative = (relative_dir / name).as_posix()
            info = path.lstat()
            if os.name == 'nt' and getattr(info, 'st_file_attributes', 0) & getattr(
                    stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
                raise ValueError('environment contains a Windows reparse point')
            if stat.S_ISLNK(info.st_mode):
                if os.name != 'posix' or relative != 'lib64' \
                        or path.resolve(strict=True) != (destination / 'lib').resolve(strict=True):
                    raise ValueError('environment contains an unreviewed linked directory')
                inventory[relative] = {'kind': 'symlink', 'target': os.readlink(path)}
                directories.remove(name)
                continue
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError('environment contains a linked or non-directory path')
            inventory[relative] = {'kind': 'directory', 'mode': stat.S_IMODE(info.st_mode)}
        for name in files:
            path = current_path / name
            relative = (relative_dir / name).as_posix()
            if name.lower() in _FORBIDDEN_STARTUP_FILES or name.lower().endswith('.pth'):
                raise ValueError('environment contains an unreviewed Python startup configuration')
            info = path.lstat()
            if os.name == 'nt' and getattr(info, 'st_file_attributes', 0) & getattr(
                    stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
                raise ValueError('environment contains a Windows reparse point')
            if stat.S_ISLNK(info.st_mode):
                if os.name != 'posix' or not relative.startswith('bin/') \
                        or name not in {'python', 'python3', f'python{sys.version_info.major}.{sys.version_info.minor}'}:
                    raise ValueError('environment contains an unreviewed symbolic link')
                target = path.resolve(strict=True)
                base = Path(sys.__dict__.get('_base_executable', '')).resolve(strict=True)
                if target != base and not target.is_relative_to(destination.resolve()):
                    raise ValueError('environment interpreter link escapes the trusted locations')
                inventory[relative] = {'kind': 'symlink', 'target': os.readlink(path)}
                continue
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError('environment contains a nonregular or multiply-linked file')
            if info.st_size > _MAX_ENVIRONMENT_FILE:
                raise ValueError('environment file exceeds the integrity scan size limit')
            total += info.st_size
            if total > _MAX_ENVIRONMENT_TOTAL:
                raise ValueError('environment exceeds the integrity scan size limit')
            data = read_regular_bytes(path, max_bytes=_MAX_ENVIRONMENT_FILE)
            inventory[relative] = {'kind': 'file', 'size': len(data),
                                   'sha256': hashlib.sha256(data).hexdigest(),
                                   'mode': stat.S_IMODE(info.st_mode)}
    if not inventory:
        raise ValueError('environment is empty')
    return inventory


def _validate_interpreter_configuration(executable: Path, destination: Path) -> Path:
    base_executable = sys.__dict__.get('_base_executable')
    if not isinstance(base_executable, str) or not base_executable:
        raise ValueError('trusted base interpreter path is unavailable')
    base = Path(base_executable).resolve(strict=True)
    configuration = read_regular_bytes(destination / 'pyvenv.cfg', max_bytes=16384).decode('utf-8', errors='strict')
    values: dict[str, str] = {}
    for line in configuration.splitlines():
        match = re.fullmatch(r'\s*([A-Za-z][A-Za-z0-9_-]*)\s*=\s*(.*?)\s*', line)
        if not match or match[1].lower() in values:
            raise ValueError('virtual environment startup configuration is malformed')
        values[match[1].lower()] = match[2]
    if values.get('include-system-site-packages', '').lower() != 'false':
        raise ValueError('virtual environment must exclude system site packages')
    allowed = {'home', 'include-system-site-packages', 'version', 'executable', 'command'}
    if set(values) - allowed or not {'home', 'include-system-site-packages', 'version'} <= set(values):
        raise ValueError('virtual environment startup configuration contains unreviewed settings')
    if Path(values['home']).resolve(strict=True) != base.parent:
        raise ValueError('virtual environment base path differs from the trusted interpreter')
    if values['version'] != platform.python_version():
        raise ValueError('virtual environment startup version differs from the trusted interpreter')
    configured_executable = Path(values['executable']).resolve(strict=True) if 'executable' in values else None
    trusted_executables = {base, Path(sys.executable).resolve(strict=True)}
    if configured_executable is not None and configured_executable not in trusted_executables:
        raise ValueError('virtual environment startup executable differs from the trusted interpreter')
    # POSIX venv executables are intentional symlinks. Resolve and bind them to
    # the already-running trusted base interpreter, never an arbitrary target.
    actual = executable.resolve(strict=True)
    # EnvBuilder's public default may copy the interpreter on POSIX rather than
    # symlink it. Accept only an exact copy inside this environment; a different
    # executable or a path outside the venv remains untrusted.
    if (os.name == 'posix' and actual != base
            and (not actual.is_relative_to(destination.resolve())
                 or hashlib.sha256(read_regular_bytes(actual, max_bytes=64 * 1024 * 1024)).digest()
                 != hashlib.sha256(read_regular_bytes(base, max_bytes=64 * 1024 * 1024)).digest())):
        raise ValueError('virtual environment interpreter differs from the trusted base interpreter')
    if os.name == 'nt':
        launcher = Path(sys.base_prefix) / 'Lib/venv/scripts/nt/python.exe'
        if read_regular_bytes(executable, max_bytes=64 * 1024 * 1024) != read_regular_bytes(launcher, max_bytes=64 * 1024 * 1024):
            raise ValueError('virtual environment launcher differs from the trusted CPython launcher')
    return base


def _write_integrity_record(destination: Path, *, lock_sha256: str,
                            wheel_sha256: list[str]) -> Path:
    directory = _integrity_directory(destination)
    _owned_directory(directory, create=True)
    record_path = directory / f'{destination.name}.json'
    inventory = _environment_inventory(destination)
    base_executable = Path(sys.__dict__['_base_executable']).resolve(strict=True)
    record = {
        'schema': _INTEGRITY_SCHEMA,
        'environment': destination.name,
        'lock_sha256': lock_sha256,
        'locked_wheel_sha256': sorted(wheel_sha256),
        'base_interpreter_sha256': hashlib.sha256(
            read_regular_bytes(base_executable, max_bytes=_MAX_ENVIRONMENT_FILE)
        ).hexdigest(),
        'python_version': platform.python_version(),
        'platform': platform.system().lower(),
        'files': inventory,
    }
    encoded = (json.dumps(record, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
    with record_path.open('xb') as stream:
        if os.name == 'posix':
            os.chmod(record_path, 0o600)
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    return record_path


def _check_integrity_record(executable: Path, destination: Path, *,
                            lock_sha256: str | None,
                            wheel_sha256: list[str] | None) -> dict:
    base = _validate_interpreter_configuration(executable, destination)
    directory = _integrity_directory(destination)
    _owned_directory(directory)
    record_path = directory / f'{destination.name}.json'
    encoded = read_regular_bytes(record_path, max_bytes=16 * 1024 * 1024)
    info = record_path.stat()
    if os.name == 'posix' and (info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise ValueError('environment integrity record permissions are not private')
    record = json.loads(encoded.decode('utf-8', errors='strict'))
    if not isinstance(record, dict) or record.get('schema') != _INTEGRITY_SCHEMA \
            or record.get('environment') != destination.name \
            or record.get('platform') != platform.system().lower() \
            or record.get('python_version') != platform.python_version() \
            or (lock_sha256 is not None and record.get('lock_sha256') != lock_sha256):
        raise ValueError('environment integrity record identity mismatch')
    base_hash = hashlib.sha256(read_regular_bytes(base, max_bytes=_MAX_ENVIRONMENT_FILE)).hexdigest()
    if record.get('base_interpreter_sha256') != base_hash:
        raise ValueError('trusted base interpreter differs from the integrity record')
    recorded_wheels = record.get('locked_wheel_sha256')
    if not isinstance(recorded_wheels, list) or any(
            not isinstance(value, str) or re.fullmatch(r'[a-f0-9]{64}', value) is None
            for value in recorded_wheels):
        raise ValueError('integrity record locked-artifact list is malformed')
    if wheel_sha256 is not None and recorded_wheels != sorted(set(wheel_sha256)):
        raise ValueError('integrity record locked-artifact identity mismatch')
    expected_files = record.get('files')
    if not isinstance(expected_files, dict):
        raise ValueError('environment integrity record file map is malformed')  # noqa: TRY004
    actual_files = _environment_inventory(destination)
    if actual_files != expected_files:
        raise ValueError('environment contents differ from the independent integrity record')
    return record


def validate_environment(executable: Path, destination: Path, expected: dict[str, str],
                         *, lock_sha256: str | None = None,
                         wheel_sha256: list[str] | None = None) -> dict:
    _owned_directory(destination)
    _check_integrity_record(executable, destination, lock_sha256=lock_sha256,
                            wheel_sha256=wheel_sha256)
    base = Path(sys.__dict__['_base_executable']).resolve(strict=True)
    result = subprocess.run([str(executable), '-B', '-I', '-c', _PROBE,
                             json.dumps({k: [v, _IMPORTS[k]] for k, v in expected.items()})],
                            env=isolated_environment(), capture_output=True, timeout=30, check=False)
    if result.returncode or len(result.stdout) > 65536:
        raise ValueError('virtual environment import/identity probe failed; retained for inspection')
    observed = json.loads(result.stdout.decode('utf-8', errors='strict'))
    if (observed['implementation'] != 'CPython' or observed['version'] != list(sys.version_info[:3])
            or Path(observed['prefix']).resolve() != destination.resolve()
            or Path(observed['base_prefix']).resolve() != Path(sys.base_prefix).resolve()
            or Path(observed['base_executable']).resolve() != base
            or observed['machine'] != platform.machine()):
        raise ValueError('virtual environment interpreter identity/version mismatch')
    if not Path(observed['pip_file']).resolve().is_relative_to(destination.resolve()):
        raise ValueError('virtual environment pip must be installed inside the environment')
    for name, version in expected.items():
        package = observed['packages'][name]
        if package['version'] != version or not Path(package['file']).resolve().is_relative_to(destination.resolve()):
            raise ValueError('locked dependency import/version/path mismatch')
    return observed


def _bootstrap_pip_only(executable: Path, destination: Path) -> None:
    """Use the trusted base interpreter's ensurepip wheel, not setuptools or an index."""
    import ensurepip

    version = ensurepip.version()
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)+(?:[a-zA-Z0-9.]+)?', version):
        raise ValueError('unreviewed bundled pip version')
    stdlib = Path(sysconfig.get_path('stdlib')).resolve(strict=True)
    if Path(ensurepip.__file__).resolve(strict=True).parent != stdlib / 'ensurepip':
        raise ValueError('ensurepip does not originate from the trusted standard library')
    name = f'pip-{version}-py3-none-any.whl'
    roots = [stdlib / 'ensurepip' / '_bundled']
    wheel_directory = sysconfig.get_config_var('WHEEL_PKG_DIR')
    if wheel_directory:
        roots.append(Path(wheel_directory))
    candidates = [root / name for root in roots if os.path.lexists(root / name)]
    if not candidates:
        raise ValueError('trusted bundled pip wheel is unavailable')
    wheels = [read_regular_bytes(path, max_bytes=32 * 1024 * 1024) for path in candidates]
    if any(wheel != wheels[0] for wheel in wheels[1:]):
        raise ValueError('bundled pip wheel identity is ambiguous')
    with tempfile.TemporaryDirectory(prefix='pip-bootstrap-', dir=destination.parent) as temporary:
        wheel = Path(temporary) / name
        with wheel.open('xb') as stream:
            stream.write(wheels[0])
        # The fresh environment has already been inspected and contains no
        # startup files. Import pip directly from the trusted, offline wheel.
        code = ('import runpy, sys; sys.path.insert(0, sys.argv.pop(1)); '
                'runpy.run_module("pip", run_name="__main__", alter_sys=True)')
        subprocess.run([str(executable), '-B', '-I', '-c', code, str(wheel),
                        '--isolated', '--disable-pip-version-check', 'install',
                        '--no-index', '--no-deps', '--only-binary=:all:', '--no-cache-dir', str(wheel)],
                       env=isolated_environment(), check=True, timeout=120)


def _create_environment(destination: Path) -> Path:
    """Create and inspect a new environment without admitting startup hooks."""
    if os.path.lexists(destination):
        raise ValueError('new environment destination already exists')
    # CPython 3.11 ensurepip normally installs setuptools, whose .pth file
    # executes on startup. Bootstrap only pip instead; keep the same strict
    # startup-file rejection before and after installation. Python 3.12's
    # standard venv already bootstraps pip without setuptools.
    pip_only = sys.version_info[:2] == (3, 11)
    venv.EnvBuilder(with_pip=not pip_only).create(destination)
    executable = destination / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    _owned_directory(destination)
    _validate_interpreter_configuration(executable, destination)
    _environment_inventory(destination)
    if pip_only:
        _bootstrap_pip_only(executable, destination)
        _environment_inventory(destination)
    return executable


def initialize(root: Path, wheelhouse: Path, *, repair: bool = False) -> Path:
    if sys.version_info[:2] not in ((3, 11), (3, 12)) or platform.python_implementation() != 'CPython':
        raise ValueError('CPython 3.11 or 3.12 is required')
    root, wheelhouse = Path(root).absolute(), Path(wheelhouse).absolute()
    data, expected = locked_requirements(root)
    identity = hashlib.sha256(data).hexdigest()[:16]
    locked_wheels = sorted({item.decode('ascii') for item in
                            re.findall(rb'--hash=sha256:([a-f0-9]{64})', data)})
    cache = root.parent / 'cache' / 'python'
    require_external_paths(cache, reserve=120)
    _owned_directory(cache.parent, create=True)
    _owned_directory(cache, create=True)
    destination = cache / f'{platform.system().lower()}-{sys.version_info.major}{sys.version_info.minor}-{identity}'
    executable = destination / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    with FileLock(cache / (destination.name + '.lock'), timeout=30, stale_after=0):
        pending = cache / (destination.name + '.pending.json')
        if os.path.lexists(destination):
            _owned_directory(destination)
            try:
                validate_environment(executable, destination, expected,
                                     lock_sha256=hashlib.sha256(data).hexdigest(),
                                     wheel_sha256=locked_wheels)
            except (OSError, ValueError, subprocess.TimeoutExpired, KeyError) as exc:
                if not repair:
                    raise ValueError(f'existing environment is damaged; retained at {destination}; inspect then use explicit repair') from exc
                destination.rename(cache / (destination.name + '.damaged-' + uuid.uuid4().hex))
                integrity_record = _integrity_directory(destination) / f'{destination.name}.json'
                if os.path.lexists(integrity_record):
                    integrity_record.rename(integrity_record.with_name(
                        integrity_record.name + '.damaged-' + uuid.uuid4().hex))
            else:
                # Fully validated existing environments require neither pip nor
                # a wheelhouse; an interrupted completion marker is evidence.
                return executable
        if pending.exists() and not repair:
            raise ValueError('interrupted initialization marker retained; inspect before explicit repair')
        stale_record = _integrity_directory(destination) / f'{destination.name}.json'
        if os.path.lexists(stale_record):
            if not repair:
                raise ValueError('orphaned environment integrity record retained; inspect before explicit repair')
            stale_record.rename(stale_record.with_name(
                stale_record.name + '.retained-' + uuid.uuid4().hex))
        _owned_directory(wheelhouse)
        hashes = set(re.findall(rb'--hash=sha256:([a-f0-9]{64})', data))
        wheels = list(wheelhouse.iterdir())
        if not wheels:
            raise ValueError('offline wheelhouse is empty')
        for wheel in wheels:
            if wheel.suffix != '.whl' or hashlib.sha256(read_regular_bytes(wheel, max_bytes=128 * 1024 * 1024)).hexdigest().encode() not in hashes:
                raise ValueError('wheelhouse contains an unreviewed artifact')
        if pending.exists():
            read_regular_bytes(pending, max_bytes=4096)
            pending.rename(cache / (pending.name + '.retained-' + uuid.uuid4().hex))
        with pending.open('x', encoding='utf-8') as stream:
            json.dump({'state': 'INITIALIZING', 'pid': os.getpid(), 'lock_sha256': hashlib.sha256(data).hexdigest()}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        # Create at the final path: moving a venv would break embedded scripts.
        _create_environment(destination)
        snapshot = destination / 'requirements.verified.txt'
        with snapshot.open('xb') as stream:
            stream.write(data)
        subprocess.run([str(executable), '-B', '-I', '-m', 'pip', '--isolated', '--disable-pip-version-check',
                        'install', '--no-index', '--find-links', str(wheelhouse), '--require-hashes',
                        '--only-binary=:all:', '--no-cache-dir', '-r', str(snapshot)],
                       env=isolated_environment(), check=True, timeout=300)
        _write_integrity_record(destination, lock_sha256=hashlib.sha256(data).hexdigest(),
                                wheel_sha256=locked_wheels)
        validate_environment(executable, destination, expected,
                             lock_sha256=hashlib.sha256(data).hexdigest(),
                             wheel_sha256=locked_wheels)
        pending.rename(cache / (pending.name + '.completed-' + uuid.uuid4().hex))
    return executable
