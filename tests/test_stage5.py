import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch as mock_patch

from kernelforge.capabilities import inspect
from kernelforge.patch_manager import lock_series, apply_series, apply_reviewed_operations, verify_lock
from kernelforge.source_provider import load_profile, audit_manifest, manifest_source_lock, require_flashable


REPOSITORY = Path(__file__).resolve().parents[1]


class Stage5Tests(unittest.TestCase):
    def test_profile_isolation_and_flash_gate(self):
        official = load_profile(REPOSITORY, 'oneplus13-pjz110')
        ace = load_profile(REPOSITORY, 'oneplus-ace6-plq110')
        self.assertNotEqual(official['manifest']['revision'], ace['manifest']['revision'])
        self.assertNotEqual(official['manifest']['path'], ace['manifest']['path'])
        self.assertIsNone(official['firmware_build'])
        xml = '<manifest>' + ''.join(
            f'<project name="{name}" path="{i}" revision="{official["manifest"]["revision"]}"/>'
            for i, name in enumerate(sorted(('android_kernel_common_oneplus_sm8750',
                         'android_kernel_oneplus_sm8750',
                         'android_kernel_modules_and_devicetree_oneplus_sm8750')))) + '</manifest>'
        audit = audit_manifest(xml, official)
        self.assertEqual(audit['source_mapping'], 'TESTED')
        with self.assertRaisesRegex(ValueError, 'mismatched revisions'):
            audit_manifest(xml, ace)
        with self.assertRaisesRegex(ValueError, 'flashable release refused'):
            require_flashable(official, audit)
        with self.assertRaisesRegex(ValueError, 'mismatched revisions'):
            audit_manifest(xml.replace(official['manifest']['revision'], 'wrong', 1), official)

    def test_complete_manifest_lock_marks_unresolved_and_unfetched_sources(self):
        xml = ('<manifest><remote name="origin" fetch="https://github.com/OnePlusOSS"/>'
               '<remote name="clo" fetch="https://git.codelinaro.org/clo/la"/>'
               '<project name="kernel/common" path="common" remote="origin" revision="branch"/>'
               '<project name="kernel/build" path="build" remote="clo" revision="' + 'a'*40 + '"/>'
               '</manifest>')
        lock = manifest_source_lock(xml, {'kernel/common': 'b'*40})
        self.assertTrue(lock['all_refs_locked'])
        self.assertEqual(lock['project_count'], 2)
        self.assertEqual(lock['projects'][1]['commit_reachability'], 'UNTESTED')
        self.assertEqual(lock['complete_sync'], 'UNTESTED')
        with self.assertRaisesRegex(ValueError, 'complete, non-including'):
            manifest_source_lock('<manifest><include name="other.xml"/></manifest>', {})

    def test_oneplus_source_locks_are_independent(self):
        locks = {}
        for name in ('oneplus13-pjz110', 'oneplus-ace6-plq110'):
            profile = load_profile(REPOSITORY, name)
            path = REPOSITORY / 'manifests' / (name + '-sm8750-source.lock.json')
            lock = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(lock['device_profile'], name)
            self.assertEqual(lock['manifest_commit'], profile['manifest']['commit'])
            self.assertEqual(lock['source_lock']['project_count'], 35)
            self.assertTrue(lock['source_lock']['all_refs_locked'])
            self.assertTrue(all(len(p['commit_sha']) == 40 for p in lock['source_lock']['projects']))
            locks[name] = lock
        oneplus = 'android_kernel_common_oneplus_sm8750'
        def common_sha(lock):
            return next(p['commit_sha'] for p in lock['source_lock']['projects'] if p['name'] == oneplus)
        self.assertNotEqual(common_sha(locks['oneplus13-pjz110']),
                            common_sha(locks['oneplus-ace6-plq110']))

    def test_source_feature_evidence_levels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, data in {
                'Makefile': 'VERSION = 6\n',
                'net/ipv4/Kconfig': 'config TCP_CONG_BBR\nconfig TCP_CONG_CUBIC\n',
                'net/ipv4/tcp_bbr.c': '.name = "bbr";',
                'net/ipv4/tcp_cubic.c': '.name = "cubic";',
                'drivers/block/zram/Kconfig': 'config ZRAM_DEF_COMP_LZORLE\n',
                'drivers/block/zram/zcomp.c': '"lzo-rle", "lz4"',
                'crypto/Kconfig': '',
                '.config': 'CONFIG_TCP_CONG_BBR=y\nCONFIG_TCP_CONG_CUBIC=m\nCONFIG_ZRAM=y\nCONFIG_ZRAM_DEF_COMP_LZORLE=y\n',
            }.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(data, encoding='utf-8')
            report = inspect(root)
            self.assertTrue(report['network']['bbr']['registration_found'])
            self.assertFalse(report['network']['bbr2']['registration_found'])
            self.assertEqual(report['network']['bbr2']['object_compiled'], 'UNTESTED')
            self.assertTrue(report['zram']['lzo-rle']['default_kconfig_declared'])
            self.assertTrue(report['zram']['lzo-rle']['default_selected'])
            self.assertEqual(report['zram']['lzo-rle']['runtime_selectable'], 'UNTESTED')
            self.assertEqual(report['network']['bbr']['status'], 'UNTESTED')
            self.assertEqual(report['zram']['lzo-rle']['status'], 'UNTESTED')
            for name in ('net/ipv4/tcp_bbr.o', 'drivers/block/zram/zcomp.o',
                         'crypto/lzo-rle.o'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                header = bytearray(64)
                header[:6] = b'\x7fELF\x02\x01'
                header[16:20] = b'\x01\x00\xb7\x00'
                path.write_bytes(header)
            compiled = inspect(root)
            self.assertEqual(compiled['network']['bbr']['status'], 'TESTED')
            self.assertEqual(compiled['network']['bbr']['object_compiled']['sha256'],
                             hashlib.sha256(header).hexdigest())
            self.assertEqual(compiled['zram']['lzo-rle']['status'], 'TESTED')
            self.assertEqual(compiled['zram']['lzo-rle']['zram_final_config'], 'y')
            self.assertEqual(compiled['network']['bbr2']['status'], 'UNTESTED')
            (root / 'net/ipv4/tcp_bbr.o').write_bytes(b'not an object')
            with self.assertRaisesRegex(ValueError, 'not an ELF64'):
                inspect(root)

    def test_dynamic_patch_lock_and_real_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            upstream, kernel = base / 'upstream', base / 'kernel'
            upstream.mkdir(); kernel.mkdir()
            def git(cwd, *args):
                env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_CONFIG_')}
                return subprocess.check_output(['git', *args], cwd=cwd, text=True, env=env).strip()
            for directory in (upstream, kernel):
                git(directory, 'init', '-q')
                git(directory, 'config', 'core.autocrlf', 'false')
            payload = b'diff --git a/hello b/hello\n--- a/hello\n+++ b/hello\n@@ -1 +1 @@\n-before\n+after\n'
            (upstream / 'change.patch').write_bytes(payload)
            (kernel / 'hello').write_bytes(b'before\n')
            for directory in (upstream, kernel):
                git(directory, 'add', '.')
                git(directory, '-c', 'user.email=test@example.invalid', '-c', 'user.name=Test', 'commit', '-qm', 'base')
            upstream_sha = git(upstream, 'rev-parse', 'HEAD')
            kernel_sha = git(kernel, 'rev-parse', 'HEAD')
            repository = upstream.as_uri()
            entry = {'id': 'trial', 'feature': 'trial', 'file': 'change.patch',
                     'kernel_commits': [kernel_sha], 'upstream': repository,
                     'license': 'GPL-2.0', 'source_spec': {'repository': repository,
                     'version_policy': 'latest_branch', 'branch': 'master'}}
            # Resolver is still exercised; Git remote resolution runs against the local fixture.
            frozen, stage, lock = lock_series([entry], base, base / 'work', base / 'report')
            self.assertEqual(lock['patches'][0]['source']['commit_sha'], upstream_sha)
            self.assertEqual(lock['patches'][0]['sha256'], hashlib.sha256(payload).hexdigest())
            verify_lock(frozen, stage, lock)
            with self.assertRaisesRegex(ValueError, 'manifest differs'):
                verify_lock([dict(frozen[0], feature='other')], stage, lock)
            # The upstream branch can move now; the frozen bytes must not.
            (upstream / 'change.patch').write_bytes(b'changed after locking')
            git(upstream, 'add', '.')
            git(upstream, '-c', 'user.email=test@example.invalid', '-c', 'user.name=Test', 'commit', '-qm', 'move branch')
            self.assertEqual((stage / 'trial.patch').read_bytes(), payload)
            self.assertEqual(apply_series(kernel, frozen, stage, kernel_commit=kernel_sha)[0]['state'], 'APPLIED')
            self.assertEqual((kernel / 'hello').read_bytes(), b'after\n')
            self.assertEqual(apply_series(kernel, frozen, stage, kernel_commit=kernel_sha)[0]['state'], 'ALREADY_APPLIED')
            self.assertEqual(json.loads((base / 'report/patches.lock.json').read_text())['state'], 'LOCKED')

    def test_transaction_removes_owned_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'added.c'
            with self.assertRaisesRegex(ValueError, 'verification failed'):
                apply_reviewed_operations([target], [lambda: target.write_bytes(b'new')], lambda: False)
            self.assertFalse(target.exists())

    def test_lock_rejects_invalid_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'p.patch').write_bytes(b'content')
            entry = {'id': 'p', 'feature': 'p', 'file': 'p.patch', 'sha256': '0' * 64,
                     'upstream': 'https://example.invalid/source', 'upstream_commit': '1' * 40}
            with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
                lock_series([entry], root, root / 'work', root / 'report')
            self.assertEqual(json.loads((root / 'report/patches.lock.json').read_text())['state'], 'FAILED')
