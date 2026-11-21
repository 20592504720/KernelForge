"""SUSFS discovery and narrow transactional GKI patch integration, not a general patch engine."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .source import _run_git

REPOSITORY = 'https://gitlab.com/simonpunk/susfs4ksu.git'
GKI_BRANCHES = {
    'android12-5.10': 'gki-android12-5.10-dev',
    'android13-5.15': 'gki-android13-5.15-dev',
    'android14-6.1': 'gki-android14-6.1-dev',
    'android15-6.6': 'gki-android15-6.6-dev',
    'android16-6.12': 'gki-android16-6.12-dev',
}


def requirement(spec):
    gki = spec['android_gki']
    if gki not in GKI_BRANCHES:
        raise ValueError('SUSFS requires an explicitly supported Android GKI identity; Linux version alone is insufficient')
    if spec['repository'] != REPOSITORY:
        raise ValueError('SUSFS source must be the reviewed upstream repository')
    result = dict(spec)
    expected = GKI_BRANCHES[gki]
    if result.get('branch', expected) != expected:
        raise ValueError('SUSFS branch does not match the declared Android GKI identity')
    result['branch'] = expected
    result['method'] = 'susfs-gki-patch-v1'
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root, android_gki):
    paths = ['kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch',
             f'kernel_patches/50_add_susfs_in_gki-{android_gki}.patch',
             'kernel_patches/fs/susfs.c', 'kernel_patches/include/linux/susfs.h',
             'kernel_patches/include/linux/susfs_def.h']
    rows = []
    for relative in paths:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'SUSFS upstream layout missing or unsafe: {relative}')
        rows.append({'file': relative, 'sha256': digest(path)})
    header = (root / paths[3]).read_text(encoding='utf-8')
    version = re.search(r'^#define SUSFS_VERSION\s+"([^"]+)"', header, re.M)
    if not version:
        raise ValueError('cannot identify SUSFS source version')
    return {'version': version.group(1), 'patches': rows}


def touched(patch):
    names = []
    for line in patch.read_text(encoding='utf-8').splitlines():
        if line.startswith(('--- ', '+++ ')):
            name = line[4:].split('\t')[0]
            if name == '/dev/null':
                raise ValueError('SUSFS patch adds/deletes files; unsupported narrow patch format')
            if not name.startswith(('a/', 'b/')) or any(p in ('..', '') for p in name[2:].split('/')) or ':' in name or '\\' in name:
                raise ValueError('unsafe SUSFS patch path')
            names.append(name[2:])
    if not names:
        raise ValueError('SUSFS patch has no recognized file changes')
    return sorted(set(names))


def _check(root, patch, reverse=False):
    try:
        _run_git(['apply', '--check', *(['--reverse'] if reverse else []), str(patch)], cwd=root)
        return True
    except RuntimeError:
        return False


def integrate(root: Path, provider: Path, upstream: Path, spec: dict, provider_name: str, locked_inventory: dict):
    """Check all patch applicability before mutation; restore bytes on failure.

    BakaSU supplies its KSU-side SUSFS code, so its official-KSU patch is never
    reapplied. Kernel-side changes still require exact applicability checks.
    """
    android = spec['android_gki']
    version = (root / 'Makefile').read_text(encoding='utf-8')
    family = '.'.join(re.search(rf'^{key}\s*=\s*(\d+)', version, re.M).group(1) for key in ('VERSION', 'PATCHLEVEL'))
    if android.split('-', 1)[1] != family:
        raise ValueError('SUSFS Android GKI identity disagrees with actual kernel Makefile')
    current = inventory(upstream, android)
    if current != locked_inventory:
        raise ValueError('SUSFS source/patch checksum changed after locking')
    baka = provider_name in ('bakasu', 'bakssu')
    kconfig = (provider / 'kernel/Kconfig').read_text(encoding='utf-8')
    patch_root = upstream / 'kernel_patches'
    kernel_patch = patch_root / f'50_add_susfs_in_gki-{android}.patch'
    provider_patch = patch_root / 'KernelSU/10_enable_susfs_for_ksu.patch'
    has_ksu = bool(re.search(r'^config KSU_SUSFS$', kconfig, re.M))
    if baka and (not has_ksu or not (provider / 'kernel/tools/susfs_compat.mk').is_file()):
        raise ValueError('INCOMPATIBLE: BakaSU SUSFS code/compatibility hooks missing')
    patches = [(root, kernel_patch)]
    if not baka:
        patches.insert(0, (provider, provider_patch))
    elif not spec.get('allow_bakasu_inline', False):
        raise ValueError('BakaSU inline hook requires explicit reviewed opt-in')
    # Static symbol agreement is necessary, but is not a compiler/linker proof.
    if baka:
        code = '\n'.join(p.read_text(encoding='utf-8', errors='replace') for p in (provider / 'kernel').rglob('*.c'))
        required = set(re.findall(r'^\+extern[^;]*?\b(ksu_\w+)\s*\(', kernel_patch.read_text(encoding='utf-8'), re.M))
        missing = sorted(name for name in required if not re.search(r'\b' + name + r'\s*\(', code))
        if missing:
            raise ValueError(f'INCOMPATIBLE: BakaSU lacks SUSFS hook symbols {missing}')
    copies = [(patch_root / 'fs/susfs.c', root / 'fs/susfs.c'),
              (patch_root / 'include/linux/susfs.h', root / 'include/linux/susfs.h'),
              (patch_root / 'include/linux/susfs_def.h', root / 'include/linux/susfs_def.h')]
    already = all(_check(tree, patch, True) for tree, patch in patches)
    if already and all(dest.is_file() and digest(src) == digest(dest) for src, dest in copies):
        return {'state': 'ALREADY_INTEGRATED', 'status': 'TESTED', 'version': current['version'], 'applied': [], 'provider_patch_skipped': baka}
    if any(dest.exists() for _, dest in copies):
        raise ValueError('INCOMPATIBLE: partial/different SUSFS payload already present; refusing overwrite')
    for tree, patch in patches:
        if not _check(tree, patch):
            raise ValueError(f'INCOMPATIBLE: SUSFS patch conflict: {patch.name}')
    snapshots = {}
    for tree, patch in patches:
        for relative in touched(patch):
            path = tree / relative
            if path.is_symlink() or tree.resolve() not in path.resolve().parents or not path.is_file():
                raise ValueError('unsafe or missing SUSFS patch target')
            snapshots[path] = path.read_bytes()
    for _, dest in copies:
        if dest.parent.is_symlink() or root.resolve() not in dest.resolve().parents:
            raise ValueError('unsafe SUSFS copy destination')
        snapshots[dest] = None
    try:
        for tree, patch in patches:
            _run_git(['apply', str(patch)], cwd=tree)
        for src, dest in copies:
            dest.write_bytes(src.read_bytes())
        if not all(_check(tree, patch, True) for tree, patch in patches):
            raise ValueError('SUSFS application verification failed')
    except BaseException:
        for path, content in snapshots.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)
        raise
    return {'state': 'EXTRA_KERNEL_PATCHES_APPLIED' if baka else 'PROVIDER_AND_KERNEL_PATCHES_APPLIED',
            'status': 'IMPLEMENTED', 'version': current['version'], 'applied': current['patches'],
            'provider_patch_skipped': baka, 'compile_compatibility': 'UNTESTED'}
