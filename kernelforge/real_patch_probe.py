"""Build-owned, reversible Patch Manager check against a locked kernel tree."""

from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path

from .patch_manager import apply_series, lock_series, verify_lock
from .source import _run_git


def check_real_source(source: Path, workspace: Path, output: Path, kernel_commit: str) -> dict:
    """Exercise apply, repeat, lock integrity and rollback without retained edits.

    The validation patch adds a Makefile comment only. Its bytes are generated
    from the exact locked source and staged in the build report, not published
    as a kernel feature patch.
    """
    source, workspace, output = Path(source).resolve(), Path(workspace).resolve(), Path(output).resolve()
    if _run_git(['rev-parse', 'HEAD'], cwd=source) != kernel_commit:
        raise ValueError('real patch probe requires the locked GKI commit')
    if _run_git(['status', '--porcelain'], cwd=source):
        raise ValueError('real patch probe requires a clean source checkout')
    original = (source / 'Makefile').read_bytes()
    if not original.endswith(b'\n'):
        raise ValueError('unexpected GKI Makefile layout')
    output.mkdir(parents=True, exist_ok=True)
    inputs = output / 'inputs'
    inputs.mkdir()
    before = original.decode('utf-8').splitlines(keepends=True)
    after = before + ['# KernelForge Stage 5 transaction probe (build-local)\n']
    patch = ('diff --git a/Makefile b/Makefile\n' + ''.join(difflib.unified_diff(
        before, after, fromfile='a/Makefile', tofile='b/Makefile'))).encode('utf-8')
    (inputs / 'comment.patch').write_bytes(patch)
    entry = {'id': 'gki-comment', 'feature': 'transaction-probe', 'file': 'comment.patch',
             'kernel_commits': [kernel_commit], 'upstream': 'https://github.com/20592504720/KernelForge',
             'upstream_commit': _run_git(['rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[1]),
             'license': 'GPL-2.0', 'sha256': hashlib.sha256(patch).hexdigest()}
    frozen, stage, lock = lock_series([entry], inputs, workspace / 'lock-work', output)
    verify_lock(frozen, stage, lock)
    applied = apply_series(source, frozen, stage, kernel_commit=kernel_commit)
    repeated = apply_series(source, frozen, stage, kernel_commit=kernel_commit)
    if applied[0]['state'] != 'APPLIED' or repeated[0]['state'] != 'ALREADY_APPLIED':
        raise ValueError('real GKI repeat application state is incorrect')
    _run_git(['apply', '--reverse', '--', str(stage / frozen[0]['file'])], cwd=source)
    if (source / 'Makefile').read_bytes() != original:
        raise ValueError('real GKI Makefile restoration failed')
    # A later text conflict must remove an earlier newly created file.
    new_file = 'kernelforge-stage5-probe.txt'
    create = (f'diff --git a/{new_file} b/{new_file}\nnew file mode 100644\n'
              f'--- /dev/null\n+++ b/{new_file}\n@@ -0,0 +1 @@\n+temporary\n').encode()
    bad = (b'diff --git a/Makefile b/Makefile\n--- a/Makefile\n+++ b/Makefile\n'
           b'@@ -1 +1 @@\n-KERNELFORGE_CONTEXT_THAT_DOES_NOT_EXIST\n+wrong\n')
    (inputs / 'create.patch').write_bytes(create)
    (inputs / 'conflict.patch').write_bytes(bad)
    def item(key: str, data: bytes) -> dict:
        return {'id': key, 'feature': key, 'file': key + '.patch', 'kernel_commits': [kernel_commit],
                'sha256': hashlib.sha256(data).hexdigest()}
    try:
        apply_series(source, [item('create', create), item('conflict', bad)], inputs,
                     kernel_commit=kernel_commit)
    except ValueError as exc:
        failure = str(exc)
        if 'text conflict' not in failure:
            raise
    else:
        raise ValueError('real GKI conflict was accepted')
    if (source / new_file).exists() or (source / 'Makefile').read_bytes() != original:
        raise ValueError('real GKI transaction rollback did not restore source')
    if _run_git(['status', '--porcelain'], cwd=source):
        raise ValueError('real GKI patch probe left a dirty source checkout')
    report = {'status': 'TESTED', 'kernel_commit': kernel_commit,
              'patch_sha256': entry['sha256'], 'lock': str((output / 'patches.lock.json').relative_to(output)),
              'first_apply': applied[0]['state'], 'repeat_apply': repeated[0]['state'],
              'rollback': 'TESTED', 'failure_reason': failure,
              'source_clean_after': True, 'build_local_only': True}
    (output / 'real-patch-probe.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report
