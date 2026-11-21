"""Transactional application of reviewed text patches to build-owned sources."""
from contextlib import contextmanager
import hashlib
import heapq
import json
import os
from pathlib import Path
import re
import shutil
import stat

from .source import _run_git, checkout
from .versions import resolve, timestamp


@contextmanager
def rollback_files(paths):
    snapshots = {}
    for path in paths:
        if path.is_symlink() or (path.exists() and (not path.is_file() or path.stat().st_nlink != 1)):
            raise ValueError(f"unsafe patch target: {path}")
        snapshots[path] = (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) if path.exists() else None
    try:
        yield
    except BaseException:
        for path, snapshot in snapshots.items():
            if snapshot is None:
                path.unlink(missing_ok=True)
            else:
                data, mode = snapshot
                path.write_bytes(data)
                path.chmod(mode)
        raise


def order(entries):
    by_id = {entry["id"]: entry for entry in entries}
    if len(by_id) != len(entries) or len({e["feature"] for e in entries}) != len(entries):
        raise ValueError("duplicate patch ID or feature")
    successors = {key: [] for key in by_id}
    pending = {}
    for key, entry in by_id.items():
        deps = set(entry.get("depends_on", []))
        if deps - by_id.keys():
            raise ValueError(f"{key}: missing dependencies {sorted(deps - by_id.keys())}")
        conflicts = set(entry.get("conflicts", [])) & by_id.keys()
        if conflicts:
            raise ValueError(f"{key}: conflicting patches {sorted(conflicts)}")
        pending[key] = len(deps)
        for dep in deps:
            successors[dep].append(key)
    ready = [(by_id[k].get("order", 0), k) for k, count in pending.items() if not count]
    heapq.heapify(ready)
    result = []
    while ready:
        _, key = heapq.heappop(ready)
        result.append(by_id[key])
        for child in successors[key]:
            pending[child] -= 1
            if not pending[child]:
                heapq.heappush(ready, (by_id[child].get("order", 0), child))
    if len(result) != len(entries):
        raise ValueError("cyclic patch dependencies")
    return result


def lock_series(entries, local_root, workspace, output):
    """Resolve each moving patch upstream once and stage immutable patch bytes.

    A failed lookup or checksum aborts before the kernel source is modified.
    The lock is written even on failure for diagnosis. It is build scoped.
    """
    local_root, workspace, output = map(lambda p: Path(p).resolve(), (local_root, workspace, output))
    output.mkdir(parents=True, exist_ok=True)
    destination = output / 'patches.lock.json'
    stage = workspace / 'patch-lock'
    if stage.exists():
        raise ValueError('patch lock staging directory already exists; refusing overwrite')
    stage.mkdir(parents=True)
    record = {'schema_version': 1, 'resolved_at': timestamp(), 'state': 'RESOLVING', 'patches': []}
    frozen = []

    def save():
        temporary = destination.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        os.replace(temporary, destination)

    save()
    try:
        for entry in order(entries):
            key = entry['id']
            relative = Path(entry['file'])
            if relative.is_absolute() or '..' in relative.parts or not relative.parts:
                raise ValueError(f'{key}: unsafe patch path')
            source_spec = entry.get('source_spec')
            upstream = None
            if source_spec:
                if source_spec['repository'].removesuffix('.git') != entry['upstream'].removesuffix('.git'):
                    raise ValueError(f'{key}: upstream repository identity mismatch')
                upstream = resolve(source_spec)
                checkout_root = workspace / 'patch-upstreams' / key
                actual = checkout(upstream['repository'], upstream['commit_sha'], checkout_root)
                if actual != upstream['commit_sha']:
                    raise ValueError(f'{key}: patch upstream checkout drifted')
                origin = (checkout_root / relative).resolve()
                if checkout_root.resolve() not in origin.parents:
                    raise ValueError(f'{key}: upstream path escapes checkout')
            else:
                origin = (local_root / relative).resolve()
                if local_root not in origin.parents:
                    raise ValueError(f'{key}: local patch path escapes patch directory')
            if origin.is_symlink() or not origin.is_file() or origin.stat().st_nlink != 1:
                raise ValueError(f'{key}: patch file missing or unsafe')
            data = origin.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if entry.get('sha256') and digest != entry['sha256']:
                raise ValueError(f'{key}: SHA256 mismatch')
            if upstream and entry.get('upstream_commit') and upstream['commit_sha'] != entry['upstream_commit']:
                raise ValueError(f'{key}: resolved upstream differs from declared commit')
            staged = stage / f'{key}.patch'
            staged.write_bytes(data)
            item = {**entry, 'file': staged.name, 'sha256': digest}
            item.pop('source_spec', None)
            frozen.append(item)
            record['patches'].append({'id': key, 'feature': entry['feature'],
                                      'source': upstream or {'repository': entry['upstream'],
                                                             'commit_sha': entry['upstream_commit'], 'policy': 'pinned'},
                                      'source_file': relative.as_posix(), 'sha256': digest,
                                      'compatibility': 'UNTESTED'})
            save()
        record['state'] = 'LOCKED'
        save()
        return frozen, stage, record
    except Exception as exc:
        record.update(state='FAILED', error=str(exc))
        save()
        raise


def apply_reviewed_operations(targets, operations, verify):
    """Shared transaction boundary for reviewed patch edits and SUSFS payload copies."""
    with rollback_files(targets):
        for operation in operations:
            operation()
        if not verify():
            raise ValueError('patch application verification failed')


def verify_lock(entries, stage, record):
    """Reject manifest/lock/staged-byte drift before patch application."""
    if record.get('state') != 'LOCKED' or len(entries) != len(record.get('patches', [])):
        raise ValueError('patch lock is incomplete')
    for entry, locked in zip(entries, record['patches']):
        if entry['id'] != locked['id'] or entry['feature'] != locked['feature'] or entry['sha256'] != locked['sha256']:
            raise ValueError('patch manifest differs from lock')
        path = Path(stage) / entry['file']
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != locked['sha256']:
            raise ValueError(f'{entry["id"]}: staged patch differs from lock')


def apply_series(root, entries, patch_root, *, kernel_commit, target=None):
    """Apply independent text edits. Shared files require manual consolidation."""
    root, patch_root = Path(root).resolve(), Path(patch_root).resolve()
    if Path(_run_git(["rev-parse", "--show-toplevel"], cwd=root)).resolve() != root:
        raise ValueError("patch series requires the source repository root")
    if _run_git(["rev-parse", "HEAD"], cwd=root) != kernel_commit:
        raise ValueError("kernel checkout differs from locked commit")
    plans, owners = [], {}
    for entry in order(entries):
        key = entry["id"]
        target = target or {}
        for field, selected in (('kernel_versions', target.get('kernel_version')),
                                ('android_gki', target.get('android_gki')),
                                ('architectures', target.get('architecture')),
                                ('build_modes', target.get('build_mode'))):
            if field in entry and selected not in entry[field]:
                raise ValueError(f'{key}: target {field} incompatible or unknown: {selected}')
        if entry.get('adaptation', 'git-apply-text-v1') != 'git-apply-text-v1':
            raise ValueError(f'{key}: unsupported adaptation')
        if entry.get('required_configs'):
            config = root / '.config'
            if not config.is_file():
                raise ValueError(f'{key}: final Kconfig unavailable for required symbols')
            enabled = set(re.findall(r'^CONFIG_([A-Z0-9_]+)=[ym]$', config.read_text(encoding='utf-8'), re.M))
            missing = set(entry['required_configs']) - enabled
            if missing:
                raise ValueError(f'{key}: required Kconfig symbols disabled: {sorted(missing)}')
        if kernel_commit not in entry["kernel_commits"]:
            raise ValueError(f"{key}: unsupported kernel commit")
        patch = (patch_root / entry["file"]).resolve()
        if patch_root not in patch.parents:
            raise ValueError(f"{key}: patch escapes manifest directory")
        data = patch.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"{key}: SHA256 mismatch")
        summary = _run_git(["apply", "--summary", "--", str(patch)], cwd=root)
        operations = {}
        for line in summary.splitlines():
            match = re.fullmatch(r"\s*(create|delete) mode 100644 (.+)", line)
            if not match:
                raise ValueError(f"{key}: unsupported patch operation: {line}")
            operations[match[2]] = match[1]
        if re.search(rb"^(old mode|new mode|rename |copy |GIT binary patch)", data, re.M):
            raise ValueError(f"{key}: unsupported patch operation")
        # numstat reports the actual paths Git will use, including rename records.
        stats = _run_git(["apply", "--numstat", "--", str(patch)], cwd=root)
        targets = []
        for row in stats.splitlines():
            fields = row.split("\t")
            if len(fields) != 3 or not all(value.isdecimal() for value in fields[:2]):
                raise ValueError(f"{key}: only text patches are accepted")
            name = fields[2]
            if not re.fullmatch(r"[a-zA-Z0-9_.+/\-]+", name) or any(
                    part.casefold() in ("", ".", "..", ".git") for part in name.split("/")):
                raise ValueError(f"{key}: unsafe patch path {name}")
            path = root / name
            resolved = path.resolve()
            if root not in resolved.parents or path.is_symlink() or resolved.parent.is_symlink():
                raise ValueError(f"{key}: unsafe patch target: {name}")
            if operations.get(name) == 'create':
                if (path.exists() and not path.is_file()) or not path.parent.is_dir():
                    raise ValueError(f"{key}: unsafe new patch target or parent missing: {name}")
            elif operations.get(name) == 'delete':
                if path.exists() and not path.is_file():
                    raise ValueError(f"{key}: unsafe deleted patch target: {name}")
            elif not path.is_file():
                raise ValueError(f"{key}: patch must modify/delete existing source: {name}")
            identity = str(resolved).casefold()
            if identity in owners:
                raise ValueError(f"{key}: shared patch target with {owners[identity]}: {name}")
            owners[identity] = key
            targets.append(resolved)
        if not targets:
            raise ValueError(f"{key}: unsupported patch operation")
        plans.append((key, patch, targets))
    report = []
    with rollback_files(path for _, _, paths in plans for path in paths):
        for key, patch, _ in plans:
            try:
                _run_git(["apply", "--check", "--", str(patch)], cwd=root)
            except RuntimeError:
                try:
                    _run_git(["apply", "--reverse", "--check", "--", str(patch)], cwd=root)
                except RuntimeError as exc:
                    raise ValueError(f"{key}: text conflict: {exc}") from exc
                report.append({"id": key, "state": "ALREADY_APPLIED", "compatibility": "UNTESTED"})
                continue
            try:
                _run_git(["apply", "--", str(patch)], cwd=root)
                _run_git(["apply", "--reverse", "--check", "--", str(patch)], cwd=root)
            except RuntimeError as exc:
                raise ValueError(f"{key}: application failed: {exc}") from exc
            report.append({"id": key, "state": "APPLIED", "compatibility": "UNTESTED"})
    return report
