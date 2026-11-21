"""Build-scoped upstream locks and development-source preparation."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from .source import checkout
from .versions import resolve, freeze, timestamp
from . import susfs


def prepare(config, workspace: Path, output: Path):
    manifest = {'schema_version': 1, 'created_at': timestamp(), 'status': 'resolving', 'upstreams': {}}
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'versions.lock.json'
    def save():
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, path)
    save()
    try:
        provider = config.get('kernelsu', {})
        requested_susfs = config.get('susfs', {})
        if requested_susfs.get('enabled') and not provider.get('enabled'):
            raise ValueError('SUSFS requires one enabled KernelSU provider')
        if provider.get('enabled'):
            manifest['upstreams']['kernelsu'] = resolve(provider)
        if requested_susfs.get('enabled'):
            manifest['upstreams']['susfs'] = resolve(susfs.requirement(requested_susfs))
        save()
        for name, lock in manifest['upstreams'].items():
            destination = workspace / 'upstreams' / name
            sha = checkout(lock['repository'], lock['commit_sha'], destination)
            if sha != lock['commit_sha']:
                raise ValueError(f'{name} checkout differs from locked Commit')
            lock['source_path'] = str(destination)
            if name == 'susfs':
                layout = susfs.inventory(destination, requested_susfs['android_gki'])
                lock.update(layout)
        manifest['status'] = 'locked'
        save()
        return manifest
    except Exception as exc:
        manifest.update(status='failure', failure_reason=str(exc))
        save()
        raise


def integrate_locked(config, manifest, source, output, *, mode, integrator):
    from .kernelsu import _inside
    record = {'status': 'SKIP'}
    provider_spec = config.get('kernelsu', {'enabled': False})
    if not provider_spec.get('enabled'):
        return integrator(provider_spec, source, output, mode=mode), record
    lock = manifest['upstreams']['kernelsu']
    spec = freeze(provider_spec, lock)
    staged = Path(lock['source_path'])
    enabled_susfs = config.get('susfs', {}).get('enabled', False)
    kernel = _inside(source, spec.get('kernel_directory', '.'))
    if enabled_susfs:
        upstream = Path(manifest['upstreams']['susfs']['source_path'])
        record = susfs.integrate(kernel, staged, upstream, config['susfs'], spec['provider'],
                                {key: manifest['upstreams']['susfs'][key] for key in ('version', 'patches')})
    def transfer(repository, commit, destination, **_kwargs):
        if repository != lock['repository'] or commit != lock['commit_sha'] or destination.exists():
            raise ValueError('locked source transfer identity mismatch')
        shutil.move(str(staged), str(destination))
        return commit
    result = integrator(spec, source, output, mode=mode, fetch=transfer, susfs_ready=enabled_susfs)
    result['version_lock'] = lock
    return result, record


def checks(spec, kernel, *, environment=None):
    """Run real Kconfig/Kbuild commands when explicitly configured; fail on any error."""
    import subprocess
    if not spec:
        return {'kconfig': 'UNTESTED', 'kbuild': 'UNTESTED', 'reason': 'no validation commands configured'}
    report = {}
    for name in ('kconfig', 'kbuild'):
        command = spec[name]
        result = subprocess.run(command, cwd=kernel, env=environment, capture_output=True, text=True,
                                timeout=spec.get('timeout_seconds', 600), check=False)
        report[name] = {'status': 'TESTED' if result.returncode == 0 else 'FAIL', 'argv': command,
                        'exit_code': result.returncode, 'output': (result.stdout + result.stderr)[-4000:]}
        if result.returncode:
            raise ValueError(f'final {name} check failed (exit {result.returncode})')
    from .kernelsu import _inside
    text = _inside(kernel, spec.get('final_config', '.config')).read_text(encoding='utf-8')
    for name in set(spec.get('required_configs', [])) | {'KSU'}:
        if f'CONFIG_{name}=y' not in text.splitlines():
            raise ValueError(f'final Kconfig dropped CONFIG_{name}=y')
    return report
