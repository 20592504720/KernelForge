"""Linux-only locked OnePlus 13 repo sync; never creates a flashable artifact."""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kernelforge.git_policy import git_command
from kernelforge.source import git_environment
from kernelforge.xml_safety import ManifestXMLerror, read_manifest_xml


def disk_sample(path, stage):
    usage = shutil.disk_usage(path)
    sample = {'at': datetime.now(UTC).isoformat(), 'stage': stage,
              'free_bytes': usage.free, 'total_bytes': usage.total}
    statvfs = getattr(os, 'statvfs', None)
    if statvfs is not None:
        stats = statvfs(path)
        sample.update(free_inodes=stats.f_favail, total_inodes=stats.f_files)
    return sample


def stop_group(process, grace_seconds=15):
    if os.name == 'posix':
        # repo may have exited while a sync child remains in its process group.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        if process.poll() is not None:
            time.sleep(0.1)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            return
    else:
        if process.poll() is not None:
            return
        process.terminate()
    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        if os.name == 'posix':
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            process.kill()
        process.wait(timeout=grace_seconds)


def run_monitored(command, cwd, log, timeout, reserve_bytes, on_sample,
                  interval: float = 30,
                  popen: Callable[..., subprocess.Popen[str]] = subprocess.Popen,
                  host_disk_path=None,
                  host_reserve_bytes=0):
    """Stop the whole repo process group before free space reaches the reserve."""
    with log.open('a', encoding='utf-8') as stream:
        stream.write('$ ' + ' '.join(command) + '\n')
        stream.flush()
        safe_command = git_command(command[1:], cwd=cwd, env=git_environment()) if command and command[0] == 'git' else command
        process = popen(safe_command, cwd=cwd, env=git_environment(), stdout=stream,
                        stderr=subprocess.STDOUT, start_new_session=(os.name == 'posix'))
        deadline = time.monotonic() + timeout
        try:
            while True:
                sample = disk_sample(cwd, command[1])
                on_sample(sample)
                if sample['free_bytes'] < reserve_bytes:
                    raise RuntimeError('RUNNER_DISK_CAPACITY_INSUFFICIENT: '
                                       f"{sample['free_bytes']} bytes free; reserve {reserve_bytes}")
                if host_disk_path is not None:
                    host_sample = disk_sample(host_disk_path, command[1] + ':host')
                    on_sample(host_sample)
                    if host_sample['free_bytes'] < host_reserve_bytes:
                        raise RuntimeError('HOST_DISK_CAPACITY_INSUFFICIENT: '
                                           f"{host_sample['free_bytes']} bytes free; "
                                           f"reserve {host_reserve_bytes}")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f'{command[0]} {command[1]} timed out after {timeout}s')
                try:
                    code = process.wait(timeout=min(interval, remaining))
                except subprocess.TimeoutExpired:
                    continue
                on_sample(disk_sample(cwd, command[1] + ':exit'))
                if code:
                    raise RuntimeError(f'command exited {code}: {command[0]} {command[1]}; see {log.name}')
                return
        except BaseException:
            stop_group(process)
            on_sample(disk_sample(cwd, command[1] + ':stopped'))
            raise


def write_report(path, record):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


ROOT_PROJECT = 'android_kernel_modules_and_devicetree_oneplus_sm8750'
ROOT_REPOSITORY = ('https://github.com/OnePlusOSS/'
                   'android_kernel_modules_and_devicetree_oneplus_sm8750.git')


def project_path(work, item):
    """Accept only locked repo paths; the manifest's one root project is explicit."""
    raw = item['path']
    if not isinstance(raw, str) or not raw or '\\' in raw or ':' in raw:
        raise ValueError('UNSAFE_PATH')
    if raw == './':
        if item['name'] != ROOT_PROJECT or item['repository'] != ROOT_REPOSITORY:
            raise ValueError('UNSAFE_PATH')
        return work.resolve()
    relative = PurePosixPath(raw)
    if relative.is_absolute() or any(part in ('', '.', '..') for part in raw.split('/')):
        raise ValueError('UNSAFE_PATH')
    target = (work / raw).resolve()
    if work.resolve() not in target.parents:
        raise ValueError('UNSAFE_PATH')
    return target


def git_value(path, *args):
    return subprocess.check_output(git_command(['-C', str(path), *args], cwd=path, env=git_environment()), text=True,
                                   stderr=subprocess.PIPE, timeout=15,
                                   env=git_environment()).strip()


def inspect_project(work, item):
    """Classify checkout, metadata, object and HEAD failures separately."""
    try:
        path = project_path(work, item)
    except (KeyError, ValueError):
        return 'UNSAFE_PATH', {}
    marker = path / '.git'
    metadata = work / '.repo' / 'projects' / (
        '.git' if item['path'] == './' else item['path'] + '.git')
    details = {'directory_exists': path.is_dir(), 'git_marker_exists': marker.exists(),
               'repo_project_metadata_exists': metadata.exists()}
    if not path.is_dir():
        return 'NOT_DOWNLOADED', details
    if not marker.exists():
        return 'INCOMPLETE_CHECKOUT', details
    try:
        git_dir = Path(git_value(path, 'rev-parse', '--absolute-git-dir')).resolve()
        if work.resolve() != git_dir and work.resolve() not in git_dir.parents:
            return 'UNSAFE_PATH', details
        if Path(git_value(path, 'rev-parse', '--show-toplevel')).resolve() != path:
            return 'GIT_METADATA_CORRUPT', details
        if (item['path'] == './' and
                git_value(path, 'remote', 'get-url', 'origin').removesuffix('.git') !=
                ROOT_REPOSITORY.removesuffix('.git')):
            return 'PROJECT_IDENTITY_MISMATCH', details
        actual = git_value(path, 'rev-parse', '--verify', 'HEAD^{commit}')
        if actual == item['commit_sha']:
            return actual, details
        try:
            git_value(path, 'cat-file', '-e', item['commit_sha'] + '^{commit}')
            details['target_object_present'] = True
        except (OSError, subprocess.SubprocessError):
            details['target_object_present'] = False
        return actual, details
    except (OSError, subprocess.SubprocessError) as exc:
        details['git_error'] = str(exc)
        try:
            git_value(path, 'cat-file', '-e', item['commit_sha'] + '^{commit}')
            details['target_object_present'] = True
            return 'INCOMPLETE_CHECKOUT', details
        except (OSError, subprocess.SubprocessError):
            details['target_object_present'] = False
            return 'GIT_METADATA_CORRUPT', details


def inspect_projects(work, projects):
    results = []
    for item in projects:
        actual, details = inspect_project(work, item)
        if actual == item['commit_sha']:
            diagnosis = 'MATCH'
        elif len(actual) == 40 and all(ch in '0123456789abcdef' for ch in actual):
            diagnosis = ('HEAD_MISMATCH' if details.get('target_object_present')
                         else 'TARGET_COMMIT_MISSING')
        else:
            diagnosis = actual
        results.append({'name': item['name'], 'path': item['path'],
                        'expected': item['commit_sha'], 'actual': actual, 'diagnosis': diagnosis,
                        'matches_lock': actual == item['commit_sha'], **details})
    return results


def verify_manifest_selection(work, lock):
    """Verify Repo's generated include or legacy symlink without editing .repo."""
    name = lock['manifest_path']
    if (not isinstance(name, str) or not name or '/' in name or '\\' in name or
            name in ('.', '..')):
        raise RuntimeError('unsafe locked manifest name')
    repo_dir = work / '.repo'
    if (repo_dir / 'local_manifest.xml').exists() or any(
            (repo_dir / 'local_manifests').glob('*.xml')):
        raise RuntimeError('unexpected local manifest overlay in locked workspace')
    selected = repo_dir / 'manifest.xml'
    expected = repo_dir / 'manifests' / name
    if (work.resolve() not in expected.resolve().parents or
            work.resolve() not in selected.resolve().parents):
        raise RuntimeError('manifest path escapes locked workspace')
    if not selected.is_file() or not expected.is_file():
        raise RuntimeError('locked manifest file is missing')
    if subprocess.run(git_command(['-C', str(repo_dir / 'manifests'), 'diff', '--quiet',
                       'HEAD', '--', name], cwd=repo_dir / 'manifests', env=git_environment()),
                      timeout=15, check=False, env=git_environment()).returncode != 0:
        raise RuntimeError('locked manifest checkout has local modifications')
    if selected.is_symlink():
        if selected.resolve() != expected.resolve():
            raise RuntimeError('selected manifest symlink differs from lock')
    else:
        try:
            root = read_manifest_xml(selected)
        except ManifestXMLerror as exc:
            raise RuntimeError('invalid selected manifest XML') from exc
        if (root.tag != 'manifest' or len(root) != 1 or root[0].tag != 'include' or
                root[0].attrib != {'name': name}):
            raise RuntimeError('selected generated manifest differs from lock')


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--reserve-gib', type=int, default=10)
    parser.add_argument('--sample-seconds', type=int, default=30)
    parser.add_argument('--sync-timeout-seconds', type=int, default=2700)
    parser.add_argument('--host-disk-path', type=Path,
                        help='mounted Windows host drive to monitor during WSL sync')
    parser.add_argument('--host-reserve-gib', type=int, default=50)
    parser.add_argument('--resume', action='store_true',
                        help='reuse an existing repo workspace after verifying its manifest')
    args = parser.parse_args(argv)
    if (args.reserve_gib < 1 or args.host_reserve_gib < 1 or
            not 10 <= args.sample_seconds <= 60 or args.sync_timeout_seconds < 60):
        parser.error('reserve-gib must be positive; sample-seconds 10..60; sync timeout >= 60')
    if args.host_disk_path is not None and not args.host_disk_path.is_dir():
        parser.error('host-disk-path must be an existing mounted directory')
    work = args.workspace.resolve()
    existing = work.exists() and any(work.iterdir())
    if existing and not args.resume:
        raise ValueError(f'refusing to overwrite nonempty workspace: {work}')
    if args.resume and not (work / '.repo/manifests/.git').exists():
        raise ValueError(f'resume requires intact .repo manifest checkout: {work}')
    work.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    record = {'started_at': datetime.now(UTC).isoformat(), 'stage': 'preflight',
              'source_sync': 'UNTESTED', 'reserve_bytes': args.reserve_gib * (1024 ** 3),
              'full_build': 'UNTESTED', 'module_abi': 'UNTESTED', 'device_boot': 'UNTESTED',
              'project_results': [], 'resource_samples': []}
    if args.host_disk_path is not None:
        record['host_reserve_bytes'] = args.host_reserve_gib * (1024 ** 3)
    log = args.report.with_suffix('.log')
    def sampled(sample):
        record['resource_samples'].append(sample)
        if sample['stage'] == 'preflight':
            record['free_bytes_start'] = sample['free_bytes']
        elif sample['stage'] == 'repo_init:complete':
            record['free_bytes_after_repo_init'] = sample['free_bytes']
        elif sample['stage'] == 'final':
            record['free_bytes_end'] = sample['free_bytes']
        record['minimum_free_bytes'] = min(record.get('minimum_free_bytes', sample['free_bytes']),
                                           sample['free_bytes'])
        if 'free_inodes' in sample:
            record['minimum_free_inodes'] = min(record.get('minimum_free_inodes', sample['free_inodes']),
                                               sample['free_inodes'])
        write_report(args.report, record)
        with log.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(sample) + '\n')

    lock = None
    prior_handler = None
    if os.name == 'posix':
        prior_handler = signal.getsignal(signal.SIGTERM)
        def interrupted(*_):
            raise InterruptedError('job terminated')
        signal.signal(signal.SIGTERM, interrupted)
    try:
        sampled(disk_sample(work, 'preflight'))
        if args.host_disk_path is not None:
            host_sample = disk_sample(args.host_disk_path, 'preflight:host')
            sampled(host_sample)
            if host_sample['free_bytes'] < record['host_reserve_bytes']:
                raise RuntimeError('HOST_DISK_CAPACITY_INSUFFICIENT before sync')
        lock = json.loads(args.lock.read_text(encoding='utf-8'))
        if not isinstance(lock, dict):
            raise TypeError('source lock must be a JSON object')
        source_lock = lock.get('source_lock')
        if lock.get('device_profile') != 'oneplus13-pjz110':
            raise ValueError('complete OnePlus 13 source lock required')
        if not isinstance(source_lock, dict):
            raise TypeError('source_lock must be a JSON object')
        if source_lock.get('all_refs_locked') is not True:
            raise ValueError('complete OnePlus 13 source lock required')
        projects = source_lock.get('projects')
        if not isinstance(projects, list):
            raise TypeError('source_lock projects must be a list')
        if len(projects) != 35 or source_lock.get('project_count') != 35:
            raise ValueError('expected exactly 35 locked OnePlus 13 projects')
        for field in ('manifest_commit', 'manifest_repository', 'manifest_path'):
            if not isinstance(lock.get(field), str) or not lock[field]:
                raise ValueError(f'source lock is missing {field}')
        record.update(device_profile=lock['device_profile'], manifest_commit=lock['manifest_commit'],
                      project_count=35)
        if os.name != 'posix' or shutil.which('repo') is None:
            raise RuntimeError('Linux repo tool is required')
        if not args.resume:
            record['stage'] = 'repo_init'
            run_monitored(['repo', 'init', '-u', lock['manifest_repository'], '-b', 'oneplus/sm8750',
                           '-m', lock['manifest_path'], '--no-clone-bundle'], work, log, 300,
                          record['reserve_bytes'], sampled, args.sample_seconds,
                          host_disk_path=args.host_disk_path,
                          host_reserve_bytes=record.get('host_reserve_bytes', 0))
            sampled(disk_sample(work, 'repo_init:complete'))
        else:
            record['resumed_workspace'] = True
            record['stage'] = 'resume_manifest_validation'
        manifest_head = subprocess.check_output(
            git_command(['-C', str(work / '.repo/manifests'), 'rev-parse', 'HEAD'],
                        cwd=work / '.repo/manifests', env=git_environment()),
            text=True, env=git_environment()).strip()
        record['actual_manifest_commit'] = manifest_head
        if manifest_head != lock['manifest_commit']:
            raise RuntimeError('manifest branch moved after locking; refusing mixed source versions')
        verify_manifest_selection(work, lock)
        if args.resume:
            record['pre_sync_project_results'] = inspect_projects(work, projects)
        record['stage'] = 'repo_sync'
        run_monitored(['repo', 'sync', '-c', '-j2', '--fail-fast', '--no-clone-bundle',
                       '--no-manifest-update'],
                      work, log, args.sync_timeout_seconds, record['reserve_bytes'],
                      sampled, args.sample_seconds,
                      host_disk_path=args.host_disk_path,
                      host_reserve_bytes=record.get('host_reserve_bytes', 0))
        record['stage'] = 'head_validation'
        record['project_results'] = inspect_projects(work, projects)
        if not all(row['matches_lock'] for row in record['project_results']):
            raise RuntimeError('one or more synced projects differ from locked commits')
        record['source_sync'] = 'TESTED'
        record['build_entry_present'] = (work / 'kernel_platform/build_with_bazel.py').is_file()
        record['bazel_present'] = (work / 'kernel_platform/tools/bazel').is_file()
    except (
        OSError, TypeError, ValueError, RuntimeError,
        subprocess.SubprocessError, ManifestXMLerror, KeyboardInterrupt,
    ) as exc:
        record['failure_reason'] = str(exc)
        record['failure_stage'] = record['stage']
        source_lock = lock.get('source_lock') if isinstance(lock, dict) else None
        projects = source_lock.get('projects') if isinstance(source_lock, dict) else None
        if isinstance(projects, list):
            record['project_results'] = inspect_projects(work, projects)
    finally:
        if prior_handler is not None:
            signal.signal(signal.SIGTERM, prior_handler)
        sampled(disk_sample(work, 'final'))
        record['matched_projects'] = sum(row['matches_lock'] for row in record['project_results'])
        record['ended_at'] = datetime.now(UTC).isoformat()
        write_report(args.report, record)
    return 0 if record['source_sync'] == 'TESTED' else 1


if __name__ == '__main__':
    sys.exit(main())
