"""Device-scoped source selection; a manifest is evidence, not build proof."""
from __future__ import annotations

import json
import re
from pathlib import Path
from xml.etree import ElementTree

from jsonschema import Draft202012Validator


PROFILE_IDS = {'oneplus13-pjz110', 'oneplus-ace6-plq110'}
OFFICIAL_PROJECTS = {
    'android_kernel_common_oneplus_sm8750',
    'android_kernel_oneplus_sm8750',
    'android_kernel_modules_and_devicetree_oneplus_sm8750',
}


def load_profile(repository_root: Path, profile_id: str) -> dict:
    if profile_id not in PROFILE_IDS:
        raise ValueError(f'unknown device profile: {profile_id}')
    repository_root = Path(repository_root)
    path = repository_root / 'devices/profiles' / (profile_id + '.json')
    profile = json.loads(path.read_text(encoding='utf-8'))
    schema = json.loads((repository_root / 'schemas/device-profile.schema.json').read_text(encoding='utf-8'))
    errors = list(Draft202012Validator(schema).iter_errors(profile))
    if errors:
        raise ValueError(f'{profile_id}: invalid profile: {errors[0].message}')
    if profile['id'] != profile_id:
        raise ValueError('profile ID differs from its filename')
    return profile


def audit_manifest(xml: str, profile: dict) -> dict:
    """Parse a trusted repo manifest snapshot and reject mixed vendor revisions."""
    if '<!DOCTYPE' in xml or '<!ENTITY' in xml:
        raise ValueError('manifest external entities are forbidden')
    document = ElementTree.fromstring(xml)
    if document.tag != 'manifest':
        raise ValueError('expected Android repo manifest')
    projects = {p.get('name'): p for p in document.findall('project')}
    if profile['source_kind'] != 'oneplus-oss':
        raise ValueError('official manifest cannot be used for a community profile')
    missing = OFFICIAL_PROJECTS - projects.keys()
    if missing:
        raise ValueError(f'manifest missing required OnePlus projects: {sorted(missing)}')
    expected = profile['manifest']['revision']
    selected = {name: {'path': projects[name].get('path'), 'revision': projects[name].get('revision')}
                for name in sorted(OFFICIAL_PROJECTS)}
    if any(item['revision'] != expected for item in selected.values()):
        raise ValueError('official kernel components have mismatched revisions')
    if any(not item['path'] or item['path'].startswith('/') or '..' in Path(item['path']).parts
           for item in selected.values()):
        raise ValueError('manifest has unsafe project path')
    return {'profile': profile['id'], 'projects': selected, 'manifest_revision': expected,
            'source_mapping': 'TESTED', 'source_completeness': 'UNTESTED',
            'module_abi': 'UNTESTED', 'device_boot': 'UNTESTED'}


def manifest_source_lock(xml: str, resolved_branches: dict[str, str]) -> dict:
    """Describe every manifest project; caller resolves all moving branches once.

    A pinned SHA in XML is a declaration, not proof that the commit is fetchable
    or that the vendor build is complete.
    """
    if '<!DOCTYPE' in xml or '<!ENTITY' in xml:
        raise ValueError('manifest external entities are forbidden')
    document = ElementTree.fromstring(xml)
    if document.tag != 'manifest' or document.findall('include'):
        raise ValueError('manifest must be a complete, non-including snapshot')
    remotes = {item.get('name'): item.get('fetch') for item in document.findall('remote')}
    default = document.find('default')
    default_remote = default.get('remote') if default is not None else None
    default_revision = default.get('revision') if default is not None else None
    projects = []
    paths = set()
    for item in document.findall('project'):
        name = item.get('name')
        path = item.get('path') or name
        remote = item.get('remote') or default_remote
        revision = item.get('revision') or default_revision
        if not name or not path or not revision or remote not in remotes:
            raise ValueError('manifest project lacks name, path, revision or remote')
        if path != './' and (path.startswith('/') or '..' in Path(path).parts or path in paths):
            raise ValueError(f'unsafe or duplicate manifest project path: {path}')
        paths.add(path)
        base = remotes[remote]
        if not base.startswith('https://') or not re.fullmatch(r'[A-Za-z0-9_.\-/]+', name):
            raise ValueError(f'unsafe manifest remote or project: {name}')
        commit = revision if re.fullmatch(r'[0-9a-f]{40}', revision) else resolved_branches.get(name)
        if commit is not None and not re.fullmatch(r'[0-9a-f]{40}', commit):
            raise ValueError(f'invalid resolved commit for {name}')
        projects.append({'name': name, 'path': path, 'repository': base.rstrip('/') + '/' + name + '.git',
                         'revision': revision, 'commit_sha': commit,
                         'ref_state': 'LOCKED' if commit else 'UNRESOLVED',
                         'commit_reachability': 'UNTESTED', 'source_sync': 'UNTESTED'})
    if not projects:
        raise ValueError('manifest has no projects')
    return {'project_count': len(projects), 'projects': projects,
            'all_refs_locked': all(p['ref_state'] == 'LOCKED' for p in projects),
            'complete_sync': 'UNTESTED'}


def require_flashable(profile: dict, audit: dict):
    if profile['verification']['device_boot'] != 'TESTED' or audit.get('module_abi') != 'TESTED':
        raise ValueError('device boot and module ABI are unverified; flashable release refused')
