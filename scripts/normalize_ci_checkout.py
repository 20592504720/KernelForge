"""Remove only reviewed, inactive checkout metadata in an isolated Actions workspace."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kernelforge.file_safety import read_regular_bytes
from kernelforge.git_policy import _PASSIVE_CONFIG, audit_repository, git_environment, repository_layout

_DISABLED = {'gc.auto': '0', 'core.sparsecheckout': 'false',
             'core.sparsecheckoutcone': 'false', 'index.sparse': 'false'}
_CREDENTIAL_FILE = re.compile(r'git-credentials-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\.config', re.I)


def _run(args, *, root, env, data=None):
    result = subprocess.run(['git', *args], cwd=root, env=env, input=data,
                            capture_output=True, timeout=30, check=False)
    if result.returncode:
        raise ValueError('reviewed checkout metadata operation failed')
    return result.stdout


def _rows(path, runner_temp, env):
    raw = read_regular_bytes(path, max_bytes=1024 * 1024)
    parsed = _run(['config', '--file', '-', '--no-includes', '--null', '--list'],
                  root=runner_temp, env=env, data=raw)
    for record in parsed.split(b'\0'):
        if record:
            key, _, value = record.partition(b'\n')
            yield key.decode('utf-8', 'strict'), value.decode('utf-8', 'strict')


def normalize_checkout(root: Path, runner_temp: Path) -> int:
    root = root.resolve(strict=True)
    runner_temp = runner_temp.resolve(strict=True)
    env = git_environment()
    layout = repository_layout(root)
    if layout != (root / '.git', root / '.git', root):
        raise ValueError('expected an isolated normal CI checkout')
    gitdir, common, _ = layout
    gitdir_pattern = gitdir.as_posix()
    includes = {f'includeif.gitdir:{gitdir_pattern}.path'.lower(),
                f'includeif.gitdir:{gitdir_pattern}/worktrees/*.path'.lower()}
    changes = []
    for path in sorted({common / 'config', gitdir / 'config.worktree'}):
        if not os.path.lexists(path):
            continue
        for key, value in _rows(path, runner_temp, env):
            lower = key.lower()
            if lower in _DISABLED:
                if value != _DISABLED[lower]:
                    raise ValueError('unexpected enabled checkout setting')
                changes.append((path, key, value, lower))
            elif lower in includes:
                # Checkout's temporary reference is not a repository trust
                # exception. Do not open its target or expose keys/values.
                target = Path(value)
                if (not target.is_absolute() or target.parent.resolve(strict=True) != runner_temp
                        or not _CREDENTIAL_FILE.fullmatch(target.name)):
                    raise ValueError('unreviewed checkout credential reference')
                changes.append((path, key, value, 'checkout credential reference'))
            elif not _PASSIVE_CONFIG.fullmatch(lower):
                raise ValueError('unreviewed checkout configuration retained')
    # Validate the complete plan before any write; preserve exact subsection
    # case and use literal value matching (Windows paths contain backslashes).
    for path, key, value, label in sorted(set(changes)):
        _run(['config', '--file', str(path), '--no-includes', '--fixed-value',
              '--unset-all', key, value], root=runner_temp, env=env)
        print('CI_CHECKOUT_NORMALIZED', path.name, label, flush=True)
    audit_repository(root, env)
    entries = [row for row in _run(['ls-files', '-v', '-z'], root=root, env=env).split(b'\0') if row]
    expected = set(_run(['ls-tree', '-r', '--name-only', '-z', 'HEAD'], root=root, env=env).split(b'\0')) - {b''}
    if (not expected or len(entries) != len(expected) or {row[2:] for row in entries} != expected
            or any(not row.startswith(b'H ') or not (root / row[2:].decode('utf-8')).is_file()
                   or (root / row[2:].decode('utf-8')).is_symlink() for row in entries)):
        raise ValueError('checkout is not dense and complete')
    _run(['diff', '--exit-code', 'HEAD', '--'], root=root, env=env)
    return len(entries)


def main() -> int:
    try:
        if os.environ.get('GITHUB_ACTIONS') != 'true' or Path(os.environ['GITHUB_WORKSPACE']).resolve(strict=True) != ROOT:
            raise ValueError('normalization is restricted to the Actions checkout')
        count = normalize_checkout(ROOT, Path(os.environ['RUNNER_TEMP']))
        print('CI_DENSE_CHECKOUT_VERIFIED', count, flush=True)
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print('CI checkout normalization blocked:', type(exc).__name__, str(exc) if isinstance(exc, ValueError) else '')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
