import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kernelforge.versions import resolve, freeze
from kernelforge import susfs, development
from kernelforge.source import _run_git, SourceError
from kernelforge.providers import OfficialModern


class VersionTests(unittest.TestCase):
    def spec(self, **kwargs):
        return {'repository': 'https://github.com/Baka-SU/BakaSU.git', 'version_policy': 'latest_branch', **kwargs}

    def test_branch_resolved_once_and_frozen(self):
        calls=[]
        def git(args, **kw):
            calls.append(args)
            return 'a'*40+'\trefs/heads/main'
        lock=resolve(self.spec(),git=git)
        pinned=freeze(self.spec(),lock)
        self.assertEqual(len(calls),1)
        self.assertEqual(lock['branch'],'main'); self.assertEqual(pinned['ref'],'a'*40)
        self.assertEqual(pinned['ref_type'],'commit'); self.assertIn('resolved_at',lock)

    def test_missing_branch_fails(self):
        with self.assertRaisesRegex(ValueError,'full Commit'):
            resolve(self.spec(),git=lambda *_a,**_k:'')

    def test_network_failure_no_fallback(self):
        with self.assertRaisesRegex(SourceError,'offline'):
            resolve(self.spec(),git=lambda *_a,**_k: (_ for _ in ()).throw(SourceError('offline')))

    def test_pinned_branch_drift_fails(self):
        with self.assertRaisesRegex(ValueError,'expected_commit'):
            resolve(self.spec(version_policy='pinned',ref_type='branch',ref='main',expected_commit='b'*40),git=lambda *_a,**_k:'a'*40+'\trefs/heads/main')

    def test_release_and_prerelease_are_distinct(self):
        rows=[{'id':1,'tag_name':'stable','prerelease':False,'published_at':'2026-01-01'},
              {'id':2,'tag_name':'dev','prerelease':True,'published_at':'2026-02-01'},
              {'id':3,'tag_name':'draft','draft':True,'prerelease':False,'published_at':'2026-03-01'}]
        for policy,tag in [('latest_release','stable'),('latest_prerelease','dev')]:
            result=resolve(self.spec(version_policy=policy),release_query=lambda _:rows,
                           git=lambda args,**_k:'a'*40+'\trefs/tags/'+tag)
            self.assertEqual(result['requested_ref'],tag)

    def test_release_api_failure_is_fatal(self):
        with self.assertRaisesRegex(OSError,'API'):
            resolve(self.spec(version_policy='latest_release'),release_query=lambda _:(_ for _ in ()).throw(OSError('API unavailable')))

    def test_annotated_tag_is_peeled(self):
        r=resolve(self.spec(version_policy='pinned',ref_type='tag',ref='v1',expected_commit='b'*40),
                  git=lambda *_a,**_k:'a'*40+'\trefs/tags/v1\n'+'b'*40+'\trefs/tags/v1^{}')
        self.assertEqual(r['commit_sha'],'b'*40)

    def test_susfs_mapping_requires_android_generation(self):
        with self.assertRaises(ValueError):
            susfs.requirement({'android_gki':'6.1','repository':susfs.REPOSITORY})
        with self.assertRaisesRegex(ValueError,'branch'):
            susfs.requirement({'android_gki':'android14-6.1','repository':susfs.REPOSITORY,'branch':'gki-android15-6.6-dev'})

    def test_lock_written_on_discovery_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with patch('kernelforge.development.resolve',side_effect=OSError('offline')):
                with self.assertRaises(OSError):
                    development.prepare({'kernelsu':{'enabled':True}},root/'work',root/'out')
            self.assertEqual(json.loads((root/'out/versions.lock.json').read_text())['status'],'failure')


class SusfsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.kernel=self.root/'kernel'; self.provider=self.root/'provider'; self.up=self.root/'up'
        self.kernel.mkdir(); (self.provider/'kernel').mkdir(parents=True)
        for folder in ('KernelSU','fs','include/linux'):
            (self.up/'kernel_patches'/folder).mkdir(parents=True,exist_ok=True)
        (self.kernel/'Makefile').write_text('VERSION = 6\nPATCHLEVEL = 1\n')
        (self.kernel/'fs').mkdir(); (self.kernel/'include/linux').mkdir(parents=True)
        (self.kernel/'target.c').write_text('old\n'); (self.provider/'kernel/Kconfig').write_text('config KSU\n')
        (self.up/'kernel_patches/fs/susfs.c').write_text('/* fixture */\n')
        (self.up/'kernel_patches/include/linux/susfs.h').write_text('#define SUSFS_VERSION "v2.4.0"\n')
        (self.up/'kernel_patches/include/linux/susfs_def.h').write_text('/* fixture */\n')
        (self.up/'kernel_patches/50_add_susfs_in_gki-android14-6.1.patch').write_text('diff --git a/target.c b/target.c\n--- a/target.c\n+++ b/target.c\n@@ -1 +1 @@\n-old\n+new\n')
        (self.up/'kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch').write_text('diff --git a/kernel/Kconfig b/kernel/Kconfig\n--- a/kernel/Kconfig\n+++ b/kernel/Kconfig\n@@ -1 +1,2 @@\n config KSU\n+config KSU_SUSFS\n')
        self.spec={'android_gki':'android14-6.1'}
        self.inventory=susfs.inventory(self.up,'android14-6.1')

    def run_patch(self,provider='official'):
        return susfs.integrate(self.kernel,self.provider,self.up,self.spec,provider,self.inventory)

    def test_apply_real_patches_and_copies(self):
        r=self.run_patch(); self.assertEqual(r['state'],'PROVIDER_AND_KERNEL_PATCHES_APPLIED')
        self.assertEqual((self.kernel/'target.c').read_text(),'new\n')
        self.assertTrue((self.kernel/'fs/susfs.c').exists())
        self.assertEqual(len(r['applied']),2)
        self.assertEqual({entry['target'] for entry in r['applied']},{'kernel','provider'})
        self.assertTrue(all('sha256' in entry for entry in r['copied']))

    def test_nested_kernel_repo_does_not_silently_skip_patches(self):
        _run_git(['init', str(self.root)])
        self.run_patch()
        self.assertEqual((self.kernel/'target.c').read_text(), 'new\n')
        self.assertIn('config KSU_SUSFS', (self.provider/'kernel/Kconfig').read_text())

    def test_duplicate_application_is_skipped(self):
        self.run_patch(); result=self.run_patch()
        self.assertEqual(result['state'],'ALREADY_INTEGRATED'); self.assertEqual(result['applied'],[])

    def test_conflict_preserves_both_trees(self):
        (self.kernel/'target.c').write_text('conflict\n')
        with self.assertRaisesRegex(ValueError,'conflict'):
            self.run_patch()
        self.assertEqual((self.provider/'kernel/Kconfig').read_text(),'config KSU\n')
        self.assertFalse((self.kernel/'fs/susfs.c').exists())

    def test_failure_after_first_apply_restores_bytes(self):
        def git(args,**kwargs):
            if '--check' not in args and args[-1].endswith('android14-6.1.patch'):
                raise SourceError('interrupted apply')
            return _run_git(args,**kwargs)
        with patch('kernelforge.susfs._run_git',side_effect=git):
            with self.assertRaisesRegex(SourceError,'interrupted'):
                self.run_patch()
        self.assertEqual((self.provider/'kernel/Kconfig').read_text(),'config KSU\n')
        self.assertEqual((self.kernel/'target.c').read_text(),'old\n')

    def test_checksum_tamper_fails(self):
        (self.up/'kernel_patches/fs/susfs.c').write_text('tampered')
        with self.assertRaisesRegex(ValueError,'checksum'):
            self.run_patch()

    def test_partial_integration_is_not_overwritten(self):
        (self.kernel/'fs/susfs.c').write_text('existing')
        with self.assertRaisesRegex(ValueError,'partial'):
            self.run_patch()

    def test_baka_ksu_features_do_not_mean_kernel_patched(self):
        (self.provider/'kernel/Kconfig').write_text('config KSU\nconfig KSU_SUSFS\n')
        (self.provider/'kernel/tools').mkdir(); (self.provider/'kernel/tools/susfs_compat.mk').write_text('# fixture')
        self.spec['allow_bakasu_inline']=True
        r=self.run_patch('bakasu'); self.assertTrue(r['provider_patch_skipped'])
        self.assertEqual(r['state'],'EXTRA_KERNEL_PATCHES_APPLIED')
        self.assertEqual([p['target'] for p in r['applied']],['kernel'])

    def test_baka_missing_hook_layout_rejected(self):
        with self.assertRaisesRegex(ValueError,'INCOMPATIBLE'):
            self.run_patch('bakasu')

    def test_no_kconfig_commands_is_untested(self):
        self.assertEqual(development.checks(None,self.kernel)['kconfig'],'UNTESTED')

    def test_kconfig_command_failure_blocks(self):
        import sys
        with self.assertRaisesRegex(ValueError,'kconfig check failed'):
            development.checks({'kconfig':[sys.executable,'-c','raise SystemExit(2)'],'kbuild':['ignored']},self.kernel)

    def test_official_new_layout_rejects_legacy(self):
        with self.assertRaisesRegex(ValueError,'modern source layout'):
            OfficialModern().validate(self.provider/'kernel')
