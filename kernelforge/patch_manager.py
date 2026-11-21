"""Transactional application of reviewed text patches to build-owned sources."""
from contextlib import contextmanager
import hashlib
import heapq
from pathlib import Path
import re
import stat

from .source import _run_git


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


def apply_series(root, entries, patch_root, *, kernel_commit):
    """Apply independent text edits. Shared files require manual consolidation."""
    root, patch_root = Path(root).resolve(), Path(patch_root).resolve()
    if Path(_run_git(["rev-parse", "--show-toplevel"], cwd=root)).resolve() != root:
        raise ValueError("patch series requires the source repository root")
    if _run_git(["rev-parse", "HEAD"], cwd=root) != kernel_commit:
        raise ValueError("kernel checkout differs from locked commit")
    plans, owners = [], {}
    for entry in order(entries):
        key = entry["id"]
        if kernel_commit not in entry["kernel_commits"]:
            raise ValueError(f"{key}: unsupported kernel commit")
        patch = (patch_root / entry["file"]).resolve()
        if patch_root not in patch.parents:
            raise ValueError(f"{key}: patch escapes manifest directory")
        data = patch.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"{key}: SHA256 mismatch")
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
            if root not in resolved.parents or not path.is_file() or path.is_symlink():
                raise ValueError(f"{key}: patch must modify existing source: {name}")
            identity = str(resolved).casefold()
            if identity in owners:
                raise ValueError(f"{key}: shared patch target with {owners[identity]}: {name}")
            owners[identity] = key
            targets.append(resolved)
        if not targets or re.search(rb"^(new file mode|deleted file mode|old mode|new mode|rename |copy |GIT binary patch)", data, re.M):
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
