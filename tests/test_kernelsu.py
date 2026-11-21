"""Real local Git fixtures and source-tree integration; no kernel compile claims."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from kernelforge.kernelsu import integrate, IntegrationError, ROOT
from kernelforge.build import run_build, BuildError
from test_build import git
from kernelforge.filesystem import retry_windows


class KernelSUIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(lambda: retry_windows(self.tmp.cleanup))
        self.base = Path(self.tmp.name)
        self.repo = self.base/'upstream'; self.repo.mkdir()
        git(self.repo,'init','-b','main')
        git(self.repo,'config','user.name','Fixture')
        git(self.repo,'config','user.email','fixture@example.invalid')
        # Hash the exact committed fixture bytes on Windows as well as Linux.
        git(self.repo,'config','core.autocrlf','false')
        (self.repo/'kernel').mkdir()
        (self.repo/'kernel/Kconfig').write_text('menu "KernelSU"\nconfig KSU\n tristate "KernelSU"\nendmenu\n')
        (self.repo/'kernel/Makefile').write_text('obj-$(CONFIG_KSU) += kernelsu.o\n')
        (self.repo/'kernel/setup.sh').write_text('# reviewed fixture; never executed\n')
        git(self.repo,'add','.'); git(self.repo,'commit','-m','fixture')
        self.sha=git(self.repo,'rev-parse','HEAD'); git(self.repo,'tag','fixture-v1')
        self.source=self.base/'source'; self.kernel(self.source)
        self.out=self.base/'output'

    def kernel(self, path):
        (path/'drivers').mkdir(parents=True)
        (path/'Makefile').write_text('VERSION = 6\nPATCHLEVEL = 1\nSUBLEVEL = 10\n')
        (path/'drivers/Makefile').write_text('# drivers\n')
        (path/'drivers/Kconfig').write_text('menu "Drivers"\nendmenu\n')
        (path/'.config').write_text(''.join(f'CONFIG_{s}=y\n' for s in ['KSU','KPROBES','HAVE_KPROBES','KPROBE_EVENTS','OVERLAY_FS','SECURITY_SELINUX','ARM64']))

    def spec(self, **kw):
        spec=json.loads((ROOT/'configs/kernelsu/official-legacy.json').read_text())
        spec.update(provider='derived',project='Fixture derivative',repository=self.repo.as_uri(),ref=self.sha,expected_commit=self.sha,
                    review={'upstream_evidence':'Fixture only; no claim of real upstream lineage','setup_sha256':hashlib.sha256((self.repo/'kernel/setup.sh').read_bytes()).hexdigest()})
        spec.update(kw)
        return spec

    def test_derived_commit_real_checkout_and_integration(self):
        r=integrate(self.spec(),self.source,self.out,mode='gki')
        self.assertEqual(r['status'],'success'); self.assertEqual(r['commit_sha'],self.sha)
        self.assertTrue((self.source/'drivers/kernelsu/Kconfig').is_file())
        self.assertEqual(r['compatibility'][1]['status'],'UNTESTED')

    def test_official_adapter_uses_same_integration_engine_fixture(self):
        spec=self.spec(provider='official',repository='https://github.com/tiann/KernelSU.git')
        from kernelforge.source import checkout
        def local_checkout(_url, ref, dest, **kwargs):
            return checkout(self.repo.as_uri(),ref,dest,**kwargs)
        with patch('kernelforge.kernelsu.LEGACY',self.sha):
            r=integrate(spec,self.source,self.out,mode='vendor',fetch=local_checkout)
        self.assertEqual(r['provider'],'official'); self.assertEqual(r['status'],'success')

    def test_tag(self):
        self.assertEqual(integrate(self.spec(ref_type='tag',ref='fixture-v1'),self.source,self.out,mode='gki')['commit_sha'],self.sha)

    def test_branch(self):
        self.assertEqual(integrate(self.spec(ref_type='branch',ref='main'),self.source,self.out,mode='gki')['commit_sha'],self.sha)

    def test_tag_mismatch(self):
        with self.assertRaisesRegex(IntegrationError,'tag does not resolve'):
            integrate(self.spec(ref_type='tag',ref='missing'),self.source,self.out,mode='gki')

    def test_invalid_repository(self):
        with self.assertRaisesRegex(IntegrationError,'repository URL'):
            integrate(self.spec(repository='invalid'),self.source,self.out,mode='gki')

    def test_invalid_commit(self):
        with self.assertRaises(IntegrationError):
            integrate(self.spec(ref='0'*40,expected_commit='0'*40),self.source,self.out,mode='gki')
        self.assertFalse((self.source/'KernelSU').exists())

    def test_incompatible_kernel(self):
        (self.source/'Makefile').write_text('VERSION = 4\nPATCHLEVEL = 19\nSUBLEVEL = 0\n')
        with self.assertRaisesRegex(IntegrationError,'kernel family'):
            integrate(self.spec(),self.source,self.out,mode='gki')

    def test_bakssu_wrong_source_is_explicitly_blocked(self):
        with self.assertRaisesRegex(IntegrationError,'BakaSU provider requires') as ctx:
            integrate(self.spec(provider='bakssu'),self.source,self.out,mode='gki')
        self.assertEqual(ctx.exception.report['status'],'failure')
        self.assertFalse((self.source/'KernelSU').exists())

    def test_bakasu_kbuild_and_hook_requirements(self):
        (self.repo/'kernel/Kbuild').write_text('obj-$(CONFIG_KSU) += kernelsu.o\n')
        git(self.repo,'add','.'); git(self.repo,'commit','-m','Kbuild fixture')
        sha=git(self.repo,'rev-parse','HEAD')
        with (self.source/'.config').open('a') as stream:
            stream.write('CONFIG_KALLSYMS=y\nCONFIG_KALLSYMS_ALL=y\nCONFIG_TRACEPOINTS=y\nCONFIG_KSU_TRACEPOINT_HOOK=y\n')
        from kernelforge.source import checkout
        def local_checkout(_url,ref,dest,**kwargs):
            return checkout(self.repo.as_uri(),ref,dest,**kwargs)
        with patch('kernelforge.kernelsu.BAKA',sha):
            r=integrate(self.spec(provider='bakasu',repository='https://github.com/Baka-SU/BakaSU.git',ref=sha,expected_commit=sha),self.source,self.out,mode='gki',fetch=local_checkout)
        self.assertEqual(r['status'],'success')
        self.assertTrue((self.source/'drivers/kernelsu/Kbuild').exists())

    def test_required_config_missing(self):
        (self.source/'.config').write_text('CONFIG_KSU=y\n')
        with self.assertRaisesRegex(IntegrationError,'required CONFIG_'):
            integrate(self.spec(),self.source,self.out,mode='gki')

    def test_setup_hash_failure_rolls_back(self):
        spec=self.spec(); spec['review']['setup_sha256']='0'*64
        with self.assertRaisesRegex(IntegrationError,'SHA256 mismatch'):
            integrate(spec,self.source,self.out,mode='gki')
        self.assertFalse((self.source/'KernelSU').exists())
        self.assertEqual((self.source/'drivers/Makefile').read_text(),'# drivers\n')

    def test_write_failure_rolls_back(self):
        (self.source/'drivers/Kconfig').write_text('menu "incomplete"\n')
        with self.assertRaisesRegex(IntegrationError,'endmenu'):
            integrate(self.spec(),self.source,self.out,mode='gki')
        self.assertFalse((self.source/'drivers/kernelsu').exists())
        self.assertFalse((self.source/'KernelSU').exists())
        self.assertEqual((self.source/'drivers/Makefile').read_text(),'# drivers\n')

    def test_repeat_refuses_to_overwrite(self):
        integrate(self.spec(),self.source,self.out,mode='gki')
        with self.assertRaisesRegex(IntegrationError,'refusing to overwrite'):
            integrate(self.spec(),self.source,self.out,mode='gki')
        self.assertTrue((self.source/'drivers/kernelsu/Kconfig').exists())

    def test_path_escape(self):
        with self.assertRaisesRegex(IntegrationError,'escapes kernel source'):
            integrate(self.spec(config_file='../outside'),self.source,self.out,mode='gki')

    def test_build_failure_report_and_no_build(self):
        cfg={'build':{'mode':'vendor'},'toolchain':{'required':[]},'source':{'repository':self.repo.as_uri(),'ref':self.sha},'kernelsu':self.spec(provider='bakssu')}
        with self.assertRaisesRegex(BuildError,'KernelSU integration failed'):
            run_build(cfg,self.base/'work',self.out)
        report=json.loads((self.out/'build-report.json').read_text())
        self.assertEqual(report['build']['status'],'failure')
        self.assertEqual(report['kernelsu']['provider'],'bakssu')
        self.assertTrue(report['kernelsu']['failure_reason'])
        self.assertEqual(report['build']['argv'],[])

    def test_isolated_source_trees(self):
        second=self.base/'second'; self.kernel(second)
        integrate(self.spec(),self.source,self.out,mode='gki')
        integrate(self.spec(),second,self.base/'output2',mode='vendor')
        self.assertNotEqual((self.source/'drivers/kernelsu').resolve(),(second/'drivers/kernelsu').resolve())

    def test_schema_rejects_multiple_providers(self):
        schema=json.loads((ROOT/'schemas/build.schema.json').read_text())['$defs']['kernelsu']
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(self.spec(provider=['official','derived']))))
