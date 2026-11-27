"""Inspect project prerequisites; optionally initialize one lock-keyed venv.

No registry, execution-policy, global Git trust or WSL configuration changes.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kernelforge.evidence import write_json
from kernelforge.python_environment import _IMPORTS, initialize


def dependencies(root: Path = ROOT) -> dict:
    lock = (root / 'requirements-dev.txt').read_bytes()
    expected = dict(re.findall(r'^([\w-]+)==([^\s]+)', lock.decode('utf-8'), re.MULTILINE))
    observed = {}
    for name, version in expected.items():
        actual = None
        try:
            actual = importlib.metadata.version(name)
            imported = importlib.import_module(_IMPORTS[name])
            import_path = imported.__file__
            import_ok = True
        except importlib.metadata.PackageNotFoundError:
            import_path, import_ok = None, False
        except (ImportError, OSError, KeyError):
            import_path, import_ok = None, False
        observed[name] = {'expected': version, 'actual': actual, 'matches': actual == version and import_ok,
                          'import_ok': import_ok, 'import_path': import_path}
    return {'lock_sha256': hashlib.sha256(lock).hexdigest(), 'packages': observed,
            'status': 'PASS' if all(item['matches'] for item in observed.values()) else 'BLOCKED',
            'installed_artifact_hashes': 'NOT_PROVEN_BY_VERSION_METADATA'}


def path_budget(root: Path = ROOT) -> dict:
    """Probe actual file operations; do not infer ability from a registry flag."""
    with tempfile.TemporaryDirectory(prefix='kf-path-', dir=root) as folder:
        target = Path(folder).joinpath(*(['path-budget-1234567890'] * 13)) / 'probe.txt'
        try:
            target.parent.mkdir(parents=True)
            target.write_bytes(b'probe')
            capable = target.read_bytes() == b'probe'
        except OSError:
            capable = False
        return {'probe_characters': len(str(target)), 'python_long_path_file_io': capable,
                'external_tool_long_paths': 'NOT_IMPLIED_BY_PYTHON_PROBE',
                'safe_external_path_budget': 240, 'project_path_characters': len(str(root)),
                'policy': 'Use existing short cache/temp paths; reject over-budget external paths unless that tool is verified.'}


def inspect(root: Path = ROOT) -> dict:
    dependencies_result = dependencies(root)
    return {'schema_version': 1, 'python': sys.version, 'executable': sys.executable,
            'supported_python': sys.version_info[:2] in ((3, 11), (3, 12)),
            'dependencies': dependencies_result, 'paths': path_budget(root),
            'git': shutil.which('git'), 'uid': getattr(os, 'getuid', lambda: None)(),
            'workspace_owner': root.stat().st_uid, 'filesystem_free_bytes': shutil.disk_usage(root).free,
            'powershell_policy': 'Use Python entry points directly; do not bypass host execution policy.',
            'git_trust': 'No wildcard safe.directory; owner mismatch requires explicit reviewed exact-path trust.',
            'system_settings_changed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--initialize-from-wheelhouse', type=Path)
    parser.add_argument('--repair-environment', action='store_true', help='Retain a damaged environment separately before offline repair')
    args = parser.parse_args()
    if args.initialize_from_wheelhouse:
        print(str(initialize(ROOT, args.initialize_from_wheelhouse, repair=args.repair_environment)))
        return 0
    result = inspect()
    if args.output:
        write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['dependencies']['status'] == 'PASS' and result['supported_python'] and result['git'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
