"""Device-scoped source selection; a manifest is evidence, not build proof."""
from __future__ import annotations

import json
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


def require_flashable(profile: dict, audit: dict):
    if profile['verification']['device_boot'] != 'TESTED' or audit.get('module_abi') != 'TESTED':
        raise ValueError('device boot and module ABI are unverified; flashable release refused')
