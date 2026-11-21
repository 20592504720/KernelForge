import hashlib
import json
import os
import struct
import tempfile
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from kernelforge import compatibility
from kernelforge.objects import inspect_object
from kernelforge.workspace import Workspace, default_path
from kernelforge.source import _run_git, SourceError

ROOT = Path(__file__).resolve().parents[1]


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
        self.assertEqual(selected,self.adapted.resolve()); self.assertEqual(meta['kernel_commit'],self.identities[0])

    def test_new_upstream_or_provider_never_receives_old_adapter(self):
        for index in range(3):
            original=self.identities[index]; self.identities[index]='f'*40
            self.assertEqual(self.select(),(self.original,None))
            self.identities[index]=original

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
        with self.assertRaises(Exception): self.select()

    def test_repository_patch_digest(self):
        meta=json.loads((ROOT/'patches/compat/susfs/manifest.json').read_text())
        path=ROOT/'patches/compat/susfs'/meta['file']
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),meta['sha256'])


class RealContextTests(unittest.TestCase):
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
