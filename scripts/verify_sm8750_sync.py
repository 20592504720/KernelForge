"""Linux-only locked OnePlus 13 repo sync; never creates a flashable artifact."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text(encoding='utf-8'))
    if lock['device_profile'] != 'oneplus13-pjz110' or not lock['source_lock']['all_refs_locked']:
        raise ValueError('complete OnePlus 13 source lock required')
    work = args.workspace.resolve()
    if work.exists() and any(work.iterdir()):
        raise ValueError(f'refusing to overwrite nonempty workspace: {work}')
    work.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    record = {'device_profile': lock['device_profile'], 'manifest_commit': lock['manifest_commit'],
              'project_count': lock['source_lock']['project_count'],
              'started_at': datetime.now(timezone.utc).isoformat(),
              'free_bytes_start': shutil.disk_usage(work).free, 'source_sync': 'UNTESTED',
              'full_build': 'UNTESTED', 'module_abi': 'UNTESTED', 'device_boot': 'UNTESTED',
              'project_results': []}
    log = args.report.with_suffix('.log')
    def run(command, timeout):
        with log.open('a', encoding='utf-8') as stream:
            stream.write('$ ' + ' '.join(command) + '\n')
            stream.flush()
            result = subprocess.run(command, cwd=work, stdout=stream, stderr=subprocess.STDOUT,
                                    timeout=timeout, check=False)
        if result.returncode:
            raise RuntimeError(f'command exited {result.returncode}: {command[0]}; see {log.name}')
    try:
        if os.name != 'posix' or shutil.which('repo') is None:
            raise RuntimeError('Linux repo tool is required')
        run(['repo', 'init', '-u', lock['manifest_repository'], '-b', 'oneplus/sm8750',
             '-m', lock['manifest_path'], '--no-clone-bundle'], 300)
        manifest_head = subprocess.check_output(
            ['git', '-C', str(work / '.repo/manifests'), 'rev-parse', 'HEAD'], text=True).strip()
        record['actual_manifest_commit'] = manifest_head
        if manifest_head != lock['manifest_commit']:
            raise RuntimeError('manifest branch moved after locking; refusing mixed source versions')
        run(['repo', 'sync', '-c', '-j2', '--fail-fast', '--no-clone-bundle'], 2700)
        for item in lock['source_lock']['projects']:
            path = (work / item['path']).resolve()
            if path != work and work not in path.parents:
                raise ValueError(f'unsafe project path: {item["path"]}')
            try:
                actual = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'],
                                                 text=True, stderr=subprocess.STDOUT).strip()
            except subprocess.CalledProcessError as exc:
                actual = f'ERROR: {exc.output.strip()}'
            record['project_results'].append({'name': item['name'], 'path': item['path'],
                                              'expected': item['commit_sha'], 'actual': actual,
                                              'matches_lock': actual == item['commit_sha']})
        if not all(row['matches_lock'] for row in record['project_results']):
            raise RuntimeError('one or more synced projects differ from locked commits')
        record['source_sync'] = 'TESTED'
        record['build_entry_present'] = (work / 'kernel_platform/build_with_bazel.py').is_file()
        record['bazel_present'] = (work / 'kernel_platform/tools/bazel').is_file()
    except Exception as exc:
        record['failure_reason'] = str(exc)
    finally:
        record['free_bytes_end'] = shutil.disk_usage(work).free
        record['ended_at'] = datetime.now(timezone.utc).isoformat()
        args.report.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return 0 if record['source_sync'] == 'TESTED' else 1


if __name__ == '__main__':
    sys.exit(main())
