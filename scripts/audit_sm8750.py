"""Remote manifest/source mapping audit; never publishes a device image."""
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernelforge.source_provider import load_profile, audit_manifest, manifest_source_lock
from kernelforge.versions import resolve, timestamp


def main(output: Path):
    root = Path(__file__).resolve().parents[1]
    official = load_profile(root, 'oneplus13-pjz110')
    ace = load_profile(root, 'oneplus-ace6-plq110')
    def audit(profile):
        manifest = profile['manifest']
        lock = resolve({'repository': manifest['repository'] + '.git',
                        'version_policy': 'latest_branch', 'branch': manifest['branch']})
        url = ('https://raw.githubusercontent.com/OnePlusOSS/kernel_manifest/'
               f'{lock["commit_sha"]}/{manifest["path"]}')
        with urlopen(Request(url, headers={'User-Agent': 'KernelForge'}), timeout=30) as response:
            xml = response.read(1024 * 1024).decode('utf-8')
        result = audit_manifest(xml, profile)
        branch_commits = {}
        for name in result['projects']:
            branch_commits[name] = resolve({
                'repository': f'https://github.com/OnePlusOSS/{name}.git',
                'version_policy': 'latest_branch', 'branch': result['manifest_revision']})['commit_sha']
        result['source_lock'] = manifest_source_lock(xml, branch_commits)
        result['manifest_commit'] = lock['commit_sha']
        return result
    result = audit(official)
    result.update(inspected_at=timestamp(), ace6=audit(ace))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path('sm8750-audit.json'))
