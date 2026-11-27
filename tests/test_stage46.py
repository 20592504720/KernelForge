import hashlib
import json
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from kernelforge import compatibility
from kernelforge.filesystem import retry_windows
from kernelforge.objects import archive_members, inspect_object
from kernelforge.source import SourceError, _run_git
from kernelforge.workspace import Workspace, default_path

ROOT = Path(__file__).resolve().parents[1]


class WindowsSharingError(PermissionError):
    winerror = 32


class WindowsSharingTests(unittest.TestCase):
    def error(self):
        return WindowsSharingError('sharing violation')

    def test_transient_sharing_violation_retries(self):
        with patch('kernelforge.filesystem.time.sleep'):
            operation=Mock(side_effect=[self.error(),'done'])
            self.assertEqual(retry_windows(operation),'done')
            self.assertEqual(operation.call_count,2)

    def test_permanent_failure_is_bounded(self):
        with patch('kernelforge.filesystem.time.sleep'):
            operation=Mock(side_effect=self.error())
            with self.assertRaises(PermissionError): retry_windows(operation,attempts=3)
            self.assertEqual(operation.call_count,3)

    def test_non_windows_permission_error_is_not_retried(self):
        operation=Mock(side_effect=PermissionError('denied'))
        with self.assertRaises(PermissionError): retry_windows(operation)
        self.assertEqual(operation.call_count,1)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)/'内核构建'

    def test_initialize_utf8_manifest(self):
        workspace=Workspace(self.home)
        manifest=json.loads(workspace.initialize().read_text(encoding='utf-8'))
        self.assertEqual(manifest['home'],str(self.home.resolve()))
        self.assertTrue(workspace.path('sources').is_dir())
        self.assertEqual(manifest['linux_kernel_build_status'],'UNTESTED')
        workspace.initialize()  # Idempotent, preserves directory contents.

    def test_environment_and_fallback(self):
        with patch.dict(os.environ,{'KERNELFORGE_HOME':str(self.home)}):
            self.assertEqual(default_path('cache','fallback','toolchains'),self.home.resolve()/'cache/toolchains')
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(default_path('cache','fallback'),Path('fallback'))

    def test_category_escape_rejected(self):
        for category,parts in [('cache',('..','sources')),('builds',('..','..','outside')),('unknown',())]:
            with self.subTest(category=category),self.assertRaises(ValueError):
                Workspace(self.home).path(category,*parts)

    def test_manifest_collision_rejected(self):
        workspace=Workspace(self.home); path=workspace.initialize()
        path.write_text('{"home":"elsewhere"}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'another location'):
            workspace.initialize()

    def test_temporary_paths_and_cli_overrides(self):
        from kernelforge.build import _safe_environment
        from kernelforge.cli import build_parser
        with patch.dict(os.environ,{'KERNELFORGE_HOME':str(self.home)}):
            self.assertEqual(_safe_environment({})['TMP'],str(self.home.resolve()/'temp'))
            default=build_parser().parse_args(['build','--config','config.json'])
            self.assertEqual(default.workspace,self.home.resolve()/'builds/default')
            explicit=build_parser().parse_args(['build','--config','config.json','--workspace','explicit'])
            self.assertEqual(explicit.workspace,Path('explicit'))


class ObjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.path=self.root/'test.o'

    def elf(self,machine=183,kind=1):
        data=bytearray(64); data[:6]=b'\x7fELF\x02\x01'
        struct.pack_into('<HH',data,16,kind,machine); self.path.write_bytes(data)

    def test_arm64_relocatable_hash(self):
        self.elf(); result=inspect_object(self.path,self.root)
        self.assertEqual(result['sha256'],hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_empty_and_dry_run_rejected(self):
        for data in (b'',b'clang -c fs/susfs.c -o fs/susfs.o'):
            self.path.write_bytes(data)
            with self.assertRaises(ValueError): inspect_object(self.path,self.root)

    def test_wrong_arch_and_executable_rejected(self):
        for machine,kind in ((62,1),(183,2)):
            self.elf(machine,kind)
            with self.assertRaises(ValueError): inspect_object(self.path,self.root)

    def test_missing_and_outside_rejected(self):
        with self.assertRaises(ValueError): inspect_object(self.path,self.root)
        self.elf()
        with self.assertRaises(ValueError): inspect_object(self.path,self.root/'other')

    def test_lto_bitcode_preserves_arm64_check(self):
        self.path.write_bytes(b'BC\xc0\xdecompiled fixture')
        for triple,valid in [('aarch64-linux-gnu',True),('x86_64-linux-gnu',False)]:
            with patch('kernelforge.objects.subprocess.run',return_value=subprocess.CompletedProcess([],0,f'target triple = "{triple}"','')):
                if valid:
                    self.assertEqual(inspect_object(self.path,self.root)['format'],'LLVM ARM64 bitcode')
                else:
                    with self.assertRaises(ValueError): inspect_object(self.path,self.root)

    def test_kbuild_archive_enumerates_real_members(self):
        self.elf(); archive=self.root/'built-in.a'; archive.write_bytes(b'!<thin>\n')
        with patch('kernelforge.objects.subprocess.check_output',return_value='test.o\n'):
            self.assertEqual(archive_members(archive,self.root),[self.path.resolve()])
        with patch('kernelforge.objects.subprocess.check_output',return_value='../outside.o\n'), self.assertRaises(ValueError):
            archive_members(archive,self.root)
        with patch('kernelforge.objects.subprocess.check_output',return_value=''), self.assertRaises(ValueError):
            archive_members(archive,self.root)


class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.meta=json.loads((ROOT/'patches/compat/susfs/manifest.json').read_text())
        self.original=self.root/'original.patch'; self.adapted=self.root/'adapted.patch'
        self.original.write_text('--- a/a\n+++ b/a\n@@ -1 +1 @@\n-old\n+new\n',encoding='utf-8')
        self.adapted.write_bytes(self.original.read_bytes())
        self.meta.update(file='adapted.patch',sha256=hashlib.sha256(self.adapted.read_bytes()).hexdigest(),
                         upstream_patch_sha256=hashlib.sha256(self.original.read_bytes()).hexdigest())
        self.catalog=self.root/'manifest.json'; self.save()
        self.identities=[self.meta['kernel_commit'],self.meta['provider_commits'][0],self.meta['susfs_commit']]

    def save(self): self.catalog.write_text(json.dumps(self.meta),encoding='utf-8')

    def select(self):
        with patch('kernelforge.compatibility._run_git',side_effect=self.identities):
            return compatibility.select(self.root,self.root,self.root,self.original,catalog=self.catalog)

    def test_exact_baseline_selection(self):
        selected,meta=self.select()
        if selected is None or meta is None:
            self.fail("reviewed baseline selection unexpectedly failed")
        self.assertEqual(selected,self.adapted.resolve()); self.assertEqual(meta['kernel_commit'],self.identities[0])

    def test_new_upstream_or_provider_never_receives_old_adapter(self):
        for index in range(3):
            original=self.identities[index]; self.identities[index]='f'*40
            self.assertEqual(self.select(),(self.original,None))
            self.identities[index]=original

    def test_new_bakasu_exact_candidate_selection_is_fixture_only(self):
        # This proves strict selector behavior, NOT real ARM64 compilation.
        newer = '2734e0bc155759955880f5fb99be640fc5b92156'
        self.assertIn(newer, self.meta['provider_commits'])
        original_provider = self.identities[1]
        self.identities[1] = newer
        selected, selected_meta = self.select()
        if selected is None or selected_meta is None:
            self.fail("reviewed BakaSU candidate selection unexpectedly failed")
        self.assertEqual(selected, self.adapted.resolve())
        self.assertIn(newer, selected_meta['provider_commits'])
        for index in (0, 2):
            correct = self.identities[index]
            self.identities[index] = 'f' * 40
            self.assertEqual(self.select(), (self.original, None))
            self.identities[index] = correct
        self.identities[1] = 'f' * 40
        self.assertEqual(self.select(), (self.original, None))
        self.identities[1] = original_provider

    def test_new_bakasu_still_rejects_tampered_original_or_adapter(self):
        self.identities[1] = '2734e0bc155759955880f5fb99be640fc5b92156'
        self.original.write_text('tampered', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'upstream patch hash'):
            self.select()
        self.original.write_bytes(self.adapted.read_bytes())
        self.adapted.write_text('tampered', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            self.select()

    def test_adapter_hash_tamper_blocks(self):
        self.adapted.write_text('tampered')
        with self.assertRaisesRegex(ValueError,'SHA256'): self.select()

    def test_original_hash_tamper_blocks(self):
        self.original.write_text('tampered')
        with self.assertRaisesRegex(ValueError,'upstream patch hash'): self.select()

    def test_code_hunk_removal_is_rejected_even_with_valid_hash(self):
        self.adapted.write_text('--- a/a\n+++ b/a\n-old\n')
        self.meta['sha256']=hashlib.sha256(self.adapted.read_bytes()).hexdigest(); self.save()
        with self.assertRaisesRegex(ValueError,'altered upstream code'): self.select()

    def test_outside_patch_rejected(self):
        self.meta['file']='../outside.patch'; self.save()
        with self.assertRaisesRegex(ValueError, 'unsafe or missing SUSFS compatibility patch'):
            self.select()

    def test_repository_patch_digest(self):
        meta=json.loads((ROOT/'patches/compat/susfs/manifest.json').read_text())
        path=ROOT/'patches/compat/susfs'/meta['file']
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),meta['sha256'])


class RealContextTests(unittest.TestCase):
    def test_missing_gki_hardening_cannot_pass(self):
        from kernelforge.development import require_final_configs
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); path=root/'.config'
            path.write_text('CONFIG_KSU=y\n')
            with self.assertRaisesRegex(ValueError,'CFI_CLANG'):
                require_final_configs(root,['KSU','CFI_CLANG'])
            path.write_text('CONFIG_KSU=y\nCONFIG_CFI_CLANG=y\n')
            self.assertEqual(require_final_configs(root,['KSU','CFI_CLANG'])['CFI_CLANG'],'y')

    """Offline reproduction uses verbatim excerpts from the locked GKI blobs."""
    def test_original_conflict_and_context_adapter_apply_reverse(self):
        fixture=ROOT/'tests/fixtures/susfs-context'
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            shutil.copytree(fixture/'fs',root/'fs')
            meta=json.loads((fixture/'metadata.json').read_text())
            for entry in meta['files']:
                self.assertEqual(hashlib.sha256((root/entry['file']).read_bytes()).hexdigest(),entry['excerpt_sha256'])
            _run_git(['init',str(root)])
            _run_git(['config','core.autocrlf','false'],cwd=root)
            with self.assertRaises(SourceError):
                _run_git(['apply','--check',str(fixture/'original.patch')],cwd=root)
            adapted=str(fixture/'adapted.patch')
            _run_git(['apply','--check',adapted],cwd=root)
            _run_git(['apply',adapted],cwd=root)
            _run_git(['apply','--reverse','--check',adapted],cwd=root)
            _run_git(['apply','--reverse',adapted],cwd=root)
            for entry in meta['files']:
                self.assertEqual((root/entry['file']).read_bytes(),(fixture/entry['file']).read_bytes())
