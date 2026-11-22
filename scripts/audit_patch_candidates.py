"""Read-only, exact-commit preflight for optional third-party patch candidates."""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

UNICODE_COMMIT = '70c394f16d82b0f85a4f07617630d82dde6d203c'
BBG_COMMIT = '028ff7fd509e2104596da7cc1ef8e6ce2a0c9082'
BASELINES = {
    'gki-android14-6.1': ('aosp-mirror/kernel_common', '498f91c17b0822a09aede17d26a63bf8c6813725'),
    'oneplus13-6.6.118': ('OnePlusOSS/android_kernel_common_oneplus_sm8750', 'e1b346b6b4f4096eb342ae3684838a942fd6f6c4'),
}


def get(url: str) -> bytes:
    with urlopen(Request(url, headers={'User-Agent': 'KernelForge-source-audit'}), timeout=30) as response:
        data = response.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise ValueError('candidate audit input exceeds 2 MiB')
    return data


def audit(output: Path) -> dict:
    patch_url = (f'https://raw.githubusercontent.com/WildKernels/kernel_patches/{UNICODE_COMMIT}'
                 '/common/unicode_bypass_fix_6.1-.patch')
    patch = get(patch_url)
    unicode = {'candidate_commit': UNICODE_COMMIT, 'patch_url': patch_url,
               'patch_sha256': hashlib.sha256(patch).hexdigest(), 'baselines': {}}
    for name, (repository, commit) in BASELINES.items():
        source = get(f'https://raw.githubusercontent.com/{repository}/{commit}/fs/unicode/utf8-norm.c')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'fs/unicode/utf8-norm.c'
            target.parent.mkdir(parents=True)
            target.write_bytes(source)
            patch_path = root / 'candidate.patch'
            patch_path.write_bytes(patch)
            check = subprocess.run(['git', 'apply', '--check', '--', str(patch_path)],
                                   cwd=root, capture_output=True, text=True, timeout=30, check=False)
        unicode['baselines'][name] = {'kernel_commit': commit,
                                     'source_sha256': hashlib.sha256(source).hexdigest(),
                                     'git_apply_check_exit': check.returncode,
                                     'git_apply_check_error': check.stderr.strip(),
                                     'integration': 'NOT_IMPLEMENTED'}
    compat = get(f'https://raw.githubusercontent.com/vc-teahouse/Baseband-guard/{BBG_COMMIT}/kernel_compat.h')
    missing_headers = []
    for name in ('objsec.h', 'blk.h'):
        if f'#include "{name}"'.encode() not in compat:
            continue
        try:
            get(f'https://raw.githubusercontent.com/vc-teahouse/Baseband-guard/{BBG_COMMIT}/{name}')
        except HTTPError as exc:
            if exc.code != 404:
                raise
            missing_headers.append(name)
    missing_headers.sort()
    bbg = {'candidate_commit': BBG_COMMIT, 'license': 'GPL-2.0',
           'kernel_compat_sha256': hashlib.sha256(compat).hexdigest(),
           'missing_in_upstream_tree': missing_headers,
           'integration': 'BLOCKED' if missing_headers else 'NOT_IMPLEMENTED',
           'object_compilation': 'UNTESTED'}
    result = {'unicode': unicode, 'bbg': bbg,
              'note': 'Exact file-level patch check only; no full source sync, build, or runtime test.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('candidate-audit.json')
    report = audit(destination)
    print(json.dumps({'output': str(destination),
                      'unicode_checks': {k: v['git_apply_check_exit'] for k, v in report['unicode']['baselines'].items()},
                      'bbg_missing_headers': report['bbg']['missing_in_upstream_tree']}))
