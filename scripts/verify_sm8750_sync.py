"""Linux-only locked OnePlus 13 repo sync; never creates a flashable artifact."""

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import subprocess
import sys
from datetime import datetime, timezone
import time


def disk_sample(path, stage):
    usage = shutil.disk_usage(path)
    sample = {'at': datetime.now(timezone.utc).isoformat(), 'stage': stage,
              'free_bytes': usage.free, 'total_bytes': usage.total}
    if hasattr(os, 'statvfs'):
        stats = os.statvfs(path)
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
                  interval=30, popen=subprocess.Popen):
    """Stop the whole repo process group before free space reaches the reserve."""
    with log.open('a', encoding='utf-8') as stream:
        stream.write('$ ' + ' '.join(command) + '\n')
        stream.flush()
        process = popen(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                        start_new_session=(os.name == 'posix'))
        deadline = time.monotonic() + timeout
        try:
            while True:
                sample = disk_sample(cwd, command[1])
                on_sample(sample)
                if sample['free_bytes'] < reserve_bytes:
                    raise RuntimeError('RUNNER_DISK_CAPACITY_INSUFFICIENT: '
                                       f"{sample['free_bytes']} bytes free; reserve {reserve_bytes}")
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
    return subprocess.check_output(['git', '-C', str(path), *args], text=True,
                                   stderr=subprocess.PIPE, timeout=15).strip()


def inspect_project(work, item):
    """Classify checkout, metadata, object and HEAD failures separately."""
    try:
        path = project_path(work, item)
    except (KeyError, ValueError):
        return 'UNSAFE_PATH', {}
    marker = path / '.git'
    metadata = work / '.repo' / 'projects' / (item['path'].rstrip('/') + '.git')
    details = {'directory_exists': path.is_dir(), 'git_marker_exists': marker.exists(),
               'repo_project_metadata_exists': metadata.exists()}
    if not path.is_dir():
        return 'NOT_DOWNLOADED', details
    if not marker.exists():
        return 'INCOMPLETE_CHECKOUT', details
    if marker.is_symlink():
        return 'UNSAFE_PATH', details
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


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--reserve-gib', type=int, default=10)
    parser.add_argument('--sample-seconds', type=int, default=30)
    parser.add_argument('--sync-timeout-seconds', type=int, default=2700)
    parser.add_argument('--resume', action='store_true',
                        help='reuse an existing repo workspace after verifying its manifest')
    args = parser.parse_args(argv)
    if args.reserve_gib < 1 or not 10 <= args.sample_seconds <= 60 or args.sync_timeout_seconds < 60:
        parser.error('reserve-gib must be positive; sample-seconds 10..60; sync timeout >= 60')
    work = args.workspace.resolve()
    existing = work.exists() and any(work.iterdir())
    if existing and not args.resume:
        raise ValueError(f'refusing to overwrite nonempty workspace: {work}')
    if args.resume and not (work / '.repo/manifests/.git').exists():
        raise ValueError(f'resume requires intact .repo manifest checkout: {work}')
    work.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    record = {'started_at': datetime.now(timezone.utc).isoformat(), 'stage': 'preflight',
              'source_sync': 'UNTESTED', 'reserve_bytes': args.reserve_gib * (1024 ** 3),
              'full_build': 'UNTESTED', 'module_abi': 'UNTESTED', 'device_boot': 'UNTESTED',
              'project_results': [], 'resource_samples': []}
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

    prior_handler = None
    if os.name == 'posix':
        prior_handler = signal.getsignal(signal.SIGTERM)
        def interrupted(*_):
            raise InterruptedError('job terminated')
        signal.signal(signal.SIGTERM, interrupted)
    try:
        sampled(disk_sample(work, 'preflight'))
        lock = json.loads(args.lock.read_text(encoding='utf-8'))
        if lock['device_profile'] != 'oneplus13-pjz110' or not lock['source_lock']['all_refs_locked']:
            raise ValueError('complete OnePlus 13 source lock required')
        projects = lock['source_lock']['projects']
        if len(projects) != 35 or lock['source_lock']['project_count'] != 35:
            raise ValueError('expected exactly 35 locked OnePlus 13 projects')
        record.update(device_profile=lock['device_profile'], manifest_commit=lock['manifest_commit'],
                      project_count=35)
        if os.name != 'posix' or shutil.which('repo') is None:
            raise RuntimeError('Linux repo tool is required')
        if not args.resume:
            record['stage'] = 'repo_init'
            run_monitored(['repo', 'init', '-u', lock['manifest_repository'], '-b', 'oneplus/sm8750',
                           '-m', lock['manifest_path'], '--no-clone-bundle'], work, log, 300,
                          record['reserve_bytes'], sampled, args.sample_seconds)
            sampled(disk_sample(work, 'repo_init:complete'))
        else:
            record['resumed_workspace'] = True
            record['stage'] = 'resume_manifest_validation'
        manifest_head = subprocess.check_output(
            ['git', '-C', str(work / '.repo/manifests'), 'rev-parse', 'HEAD'], text=True).strip()
        record['actual_manifest_commit'] = manifest_head
        if manifest_head != lock['manifest_commit']:
            raise RuntimeError('manifest branch moved after locking; refusing mixed source versions')
        if args.resume:
            manifest_name = (work / '.repo/manifest.xml').resolve()
            expected_manifest = (work / '.repo/manifests' / lock['manifest_path']).resolve()
            if manifest_name != expected_manifest:
                raise RuntimeError('resume manifest selection differs from locked manifest path')
            record['pre_sync_project_results'] = inspect_projects(work, projects)
        record['stage'] = 'repo_sync'
        run_monitored(['repo', 'sync', '-c', '-j2', '--fail-fast', '--no-clone-bundle',
                       '--no-manifest-update'],
                      work, log, args.sync_timeout_seconds, record['reserve_bytes'],
                      sampled, args.sample_seconds)
        record['stage'] = 'head_validation'
        record['project_results'] = inspect_projects(work, projects)
        if not all(row['matches_lock'] for row in record['project_results']):
            raise RuntimeError('one or more synced projects differ from locked commits')
        record['source_sync'] = 'TESTED'
        record['build_entry_present'] = (work / 'kernel_platform/build_with_bazel.py').is_file()
        record['bazel_present'] = (work / 'kernel_platform/tools/bazel').is_file()
    except (Exception, KeyboardInterrupt) as exc:
        record['failure_reason'] = str(exc)
        record['failure_stage'] = record['stage']
        if 'lock' in locals() and isinstance(lock, dict) and 'source_lock' in lock:
            record['project_results'] = inspect_projects(work, lock['source_lock'].get('projects', []))
    finally:
        if prior_handler is not None:
            signal.signal(signal.SIGTERM, prior_handler)
        sampled(disk_sample(work, 'final'))
        record['matched_projects'] = sum(row['matches_lock'] for row in record['project_results'])
        record['ended_at'] = datetime.now(timezone.utc).isoformat()
        write_report(args.report, record)
    return 0 if record['source_sync'] == 'TESTED' else 1


if __name__ == '__main__':
    sys.exit(main())
