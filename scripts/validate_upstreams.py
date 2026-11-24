"""Opt-in real Android GKI source validation. Never claims boot/root success."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import hashlib
from datetime import datetime, timezone
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kernelforge import development
from kernelforge import __version__
from kernelforge.kernelsu import integrate
from kernelforge.source import checkout, _run_git
from kernelforge.versions import resolve
from kernelforge.objects import inspect_object, archive_members

BASELINE={'official':'2a60b2893b8d0d885d1ceff2287d8ad854f0e0f4',
          'bakasu':'7b65bde0710b5e7c6f755545cb15a4abd417f3a8',
          'susfs':'756abbf2d81557e36664fc67dffaee26d3dfc57c',
          'kernel':'498f91c17b0822a09aede17d26a63bf8c6813725'}


def parse_exact_bakasu_commit(value: str) -> str:
    """Accept an immutable 40-hex Git Commit; never accept a moving ref."""
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-fA-F]{40}', value):
        raise argparse.ArgumentTypeError('BakaSU override must be one full 40-hex Commit SHA')
    return value.lower()


def choose_pinned_provider_commit(provider: str, susfs: bool, pinned_baseline: bool, override: str | None) -> str:
    """Keep the ACK/SUSFS baselines pinned when probing one exact BakaSU SHA."""
    if override is not None and (provider != 'bakasu' or not susfs or not pinned_baseline):
        raise ValueError('--bakasu-commit requires --provider bakasu --susfs --pinned-baseline')
    if override is not None and not re.fullmatch(r'[0-9a-f]{40}', override):
        raise ValueError('invalid exact BakaSU Commit')
    return override if override is not None else BASELINE[provider]


def review_pinned_request(provider: str, susfs: bool, pinned_baseline: bool, provider_commit: str) -> dict:
    """Reject an unreviewed exact combination before any source downloads.

    Non-pinned upstream probes remain possible as experimental diagnostics but
    NEVER acquire reviewed/release status, regardless of their resolved SHA.
    """
    if not pinned_baseline or not susfs:
        return {"status": "NOT_ADMITTED_MOVING_OR_NO_SUSFS", "release_eligible": False}
    from kernelforge.compatibility_gate import (
        evaluate_reviewed, OFFICIAL_REPO, BAKA_REPO, SUSFS_REPO, KERNEL_REPO,
    )
    def declared(sha, repository):
        return {"repository": repository, "commit_sha": sha, "policy": "pinned",
                "ref_type": "commit", "requested_ref": sha}
    admission = evaluate_reviewed({
        "android_gki": "android14-6.1",
        "kernel": declared(BASELINE["kernel"], KERNEL_REPO),
        "kernelsu": declared(provider_commit, OFFICIAL_REPO if provider == "official" else BAKA_REPO),
        "susfs": declared(BASELINE["susfs"], SUSFS_REPO),
    }, provider=provider, catalog=ROOT / "patches/compat/susfs/manifest.json")
    return admission


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--provider',choices=['official','bakasu'],required=True)
    parser.add_argument('--susfs',action='store_true')
    parser.add_argument('--pinned-baseline',action='store_true')
    parser.add_argument('--bakasu-commit',type=parse_exact_bakasu_commit,
                        help='exact BakaSU Commit with --provider bakasu --susfs --pinned-baseline')
    parser.add_argument('--full-kernel',action='store_true')
    parser.add_argument('--image-timeout-seconds',type=int,default=3600,
                        help='real Image timeout 300..14400 seconds; hosted runner hard limits still apply')
    parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args()
    if not 300 <= args.image_timeout_seconds <= 14400:
        parser.error('--image-timeout-seconds must be 300..14400')
    try:
        pinned_provider=choose_pinned_provider_commit(args.provider, args.susfs, args.pinned_baseline, args.bakasu_commit)
    except ValueError as exc:
        parser.error(str(exc))
    # This offline gate runs before workspace creation and any upstream fetch.
    try:
        compatibility_admission = review_pinned_request(
            args.provider, args.susfs, args.pinned_baseline, pinned_provider)
    except ValueError as exc:
        parser.error(str(exc))
    work=args.workspace.resolve(); output=work/'report'; output.mkdir(parents=True,exist_ok=True)
    result={'provider':args.provider,'status':'failure','kconfig':'UNTESTED','kbuild':'UNTESTED','kernel_compile':'UNTESTED','boot':'UNTESTED','root':'UNTESTED'}
    result.update(object_compilation='UNTESTED',susfs_enabled=args.susfs,
                  version_policy='pinned' if args.pinned_baseline else 'latest_branch',objects=[],
                  requested_bakasu_commit=args.bakasu_commit,
                  compatibility_admission=compatibility_admission)
    started=datetime.now(timezone.utc)
    result.update(kernelforge_version=__version__,started_at=started.isoformat(),toolchain={})
    step='version resolution'
    try:
        profile=ROOT/'configs/kernelsu'/('official-development.json' if args.provider=='official' else 'bakasu-development.json')
        config={'kernelsu':json.loads(profile.read_text(encoding='utf-8'))}
        if args.pinned_baseline:
            config['kernelsu'].update(version_policy='pinned',ref_type='commit',ref=pinned_provider,expected_commit=pinned_provider)
        if args.susfs:
            config['susfs']={'enabled':True,'repository':'https://gitlab.com/simonpunk/susfs4ksu.git','version_policy':'latest_branch','android_gki':'android14-6.1','allow_bakasu_inline':True}
            if args.pinned_baseline:
                config['susfs'].update(version_policy='pinned',ref_type='commit',ref=BASELINE['susfs'],expected_commit=BASELINE['susfs'])
        lock=development.prepare(config,work,output)
        kernel_spec={'repository':'https://github.com/aosp-mirror/kernel_common.git','version_policy':'latest_branch','branch':'android14-6.1','method':'GKI ARM64 source validation'}
        if args.pinned_baseline:
            kernel_spec.update(version_policy='pinned',ref_type='commit',ref=BASELINE['kernel'],expected_commit=BASELINE['kernel'])
        kernel_lock=resolve(kernel_spec)
        lock['upstreams']['kernel']=kernel_lock
        (output/'versions.lock.json').write_text(json.dumps(lock,indent=2)+'\n',encoding='utf-8')
        source=work/'source'
        step='GKI checkout'
        # Shallow source fetch avoids cloning the entire ACK history. Verify tree
        # connectivity and exact HEAD before any integration.
        source.mkdir()
        _run_git(['init',str(source)])
        _run_git(['remote','add','origin',kernel_lock['repository']],cwd=source)
        _run_git(['fetch','--depth=1','origin',kernel_lock['commit_sha']],cwd=source,timeout=600)
        _run_git(['checkout','--detach','FETCH_HEAD'],cwd=source,timeout=600)
        _run_git(['fsck','--connectivity-only'],cwd=source)
        if _run_git(['rev-parse','HEAD'],cwd=source)!=kernel_lock['commit_sha']:
            raise ValueError('GKI source Commit mismatch')
        result['kernel_commit']=kernel_lock['commit_sha']
        if args.pinned_baseline and args.provider == 'official' and not args.susfs:
            step='real GKI Patch Manager transaction probe'
            from kernelforge.real_patch_probe import check_real_source
            result['patch_manager'] = check_real_source(
                source, work / 'patch-probe', output / 'patch-probe', kernel_lock['commit_sha'])
        # Target code uses LLVM; host helpers in this ACK revision require the
        # GNU host compiler rather than the runner's newer Clang diagnostics.
        command=['make','ARCH=arm64','LLVM=1','HOSTCC=gcc-11','HOSTCXX=g++-11']
        def run(argv,timeout=900):
            with (output/'source-check.log').open('a',encoding='utf-8') as stream:
                stream.write('$ '+' '.join(argv)+'\n'); stream.flush()
                process=subprocess.run(argv,cwd=source,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout,check=False)
            if process.returncode:
                raise ValueError(f'{step} failed (exit {process.returncode}); see source-check.log')
        result['host']={'cpus':os.cpu_count(),'free_bytes':shutil.disk_usage(work).free,
                        'memory':Path('/proc/meminfo').read_text() if Path('/proc/meminfo').exists() else 'unknown'}
        step='toolchain inventory'
        for tool in ('clang','ld.lld','llvm-nm','gcc-11'):
            run([tool,'--version'])
            result['toolchain'][tool]=subprocess.check_output([tool,'--version'],text=True).splitlines()[0]
        step='initial Kconfig'
        run(['clang','--target=aarch64-linux-gnu','-fsanitize=kcfi','-x','c','-c','/dev/null','-o',str(output/'compiler-kcfi-probe.o')])
        defconfig=(source/'arch/arm64/configs/gki_defconfig').read_text().splitlines()
        hardening=[name for name in ('CFI_CLANG','SHADOW_CALL_STACK','STACKPROTECTOR_STRONG','RANDOMIZE_BASE','HARDENED_USERCOPY','FORTIFY_SOURCE') if f'CONFIG_{name}=y' in defconfig]
        result['baseline_hardening']=hardening
        run(command+['gki_defconfig'])
        symbols=['KSU','SECURITY_SELINUX','ARM64','KALLSYMS','KALLSYMS_ALL','TRACEPOINTS','KPROBES','EXT4_FS']+hardening
        symbols+=['KSU_SUSFS','THREAD_INFO_IN_TASK'] if args.susfs else (['KSU_TRACEPOINT_HOOK'] if args.provider=='bakasu' else [])
        for symbol in symbols:
            run(['scripts/config','--enable',symbol])
        step='KernelSU and SUSFS integration'
        result['integration'],result['susfs']=development.integrate_locked(config,lock,source,output,mode='gki',integrator=integrate)
        step='final Kconfig'
        run(command+['olddefconfig'])
        result['required_final_configs']=development.require_final_configs(source,symbols)
        result['kconfig']='TESTED'
        shutil.copyfile(source/'.config',output/'kernel.config')
        from kernelforge.capabilities import inspect as inspect_capabilities
        result['capabilities'] = inspect_capabilities(source, source / '.config')
        (output/'capabilities.json').write_text(json.dumps(result['capabilities'],indent=2)+'\n',encoding='utf-8')
        step='make prepare and UAPI headers'
        run(command+['prepare'])
        run(command+['headers_install'])
        # A directory-only Kbuild does not visit SELinux's host header generator.
        # Build its real target rather than supplying fabricated flask headers.
        run(command+['-j2','security/selinux/'])
        result['kbuild']='TESTED (make prepare; actual object build follows)'
        step='real ARM64 object compilation'
        targets=['drivers/kernelsu/']; objects=[]
        if args.susfs:
            selected=result['susfs'].get('compatibility_patch')
            patch=(ROOT/'patches/compat/susfs'/selected['file']) if selected else work/'upstreams/susfs/kernel_patches/50_add_susfs_in_gki-android14-6.1.patch'
            changed=re.findall(r'^\+\+\+ b/(.+\.c)$',patch.read_text(encoding='utf-8'),re.M)
            targets+=sorted({str(Path(name).with_suffix('.o')) for name in changed}|{'fs/susfs.o'})
            objects+=targets[1:]
        run(command+['-j2']+targets,timeout=1200)
        if args.pinned_baseline and args.provider == 'official' and not args.susfs:
            step='ZRAM module object compilation'
            run(command+['-j2','drivers/block/zram/'],timeout=1200)
            zcomp=source/'drivers/block/zram/zcomp.o'
            if not zcomp.is_file() or not zcomp.stat().st_size:
                raise ValueError('ZRAM module build did not produce zcomp.o')
            result['zram_module_object']=inspect_object(zcomp,source)
        objects=[str(path.relative_to(source)) for path in archive_members(source/'drivers/kernelsu/built-in.a',source)]+objects
        result['objects']=[inspect_object(source/name,source) for name in objects]
        result['object_compilation']='TESTED'
        step='relocatable integration link'
        run(['ld.lld','-r','-o','integration-check.o']+objects)
        result['relocatable_link']=inspect_object(source/'integration-check.o',source)
        undefined=subprocess.check_output(['llvm-nm','--undefined-only','integration-check.o'],cwd=source,text=True)
        (output/'undefined-symbols.txt').write_text(undefined,encoding='utf-8')
        unresolved=sorted(set(re.findall(r'\b(?:__)?(?:ksu|susfs)_\w+',undefined)))
        result['unresolved_root_hooks']=unresolved
        if unresolved:
            raise ValueError(f'unresolved KernelSU/SUSFS hooks after relocatable link: {unresolved}')
        result['acceptance']={'source':'TESTED','kconfig':'TESTED','prepare':'TESTED',
                              'objects':'TESTED','relocatable_link':'TESTED','full_vmlinux':'UNTESTED',
                              'boot':'UNTESTED','root':'UNTESTED'}
        if args.susfs:
            result['susfs']['compile_compatibility']='TESTED (objects and relocatable link only)'
        result['kernel_compile_reason']=('Full Image build requested' if args.full_kernel else 'Full Image build not requested; host resources recorded separately')
        if args.full_kernel:
            step='complete Image build'
            run(command+['-j2','Image'],timeout=args.image_timeout_seconds)
            image=source/'arch/arm64/boot/Image'
            if not image.is_file() or not image.stat().st_size:
                raise ValueError('Image build returned without a nonempty Image')
            vmlinux=source/'vmlinux'
            if not vmlinux.is_file() or not vmlinux.stat().st_size:
                raise ValueError('Image build returned without a nonempty vmlinux')
            with vmlinux.open('rb') as stream:
                result['vmlinux']={'path':str(vmlinux.relative_to(work)),
                                   'bytes':vmlinux.stat().st_size,
                                   'sha256':hashlib.file_digest(stream,'sha256').hexdigest()}
            result['image']={'path':str(image.relative_to(work)),'bytes':image.stat().st_size,'sha256':hashlib.sha256(image.read_bytes()).hexdigest()}
            shutil.copyfile(image,output/'Image')
            if hashlib.sha256((output/'Image').read_bytes()).hexdigest()!=result['image']['sha256']:
                raise ValueError('Image artifact copy SHA256 mismatch')
            result['image']['artifact']='Image'
            result['capabilities'] = inspect_capabilities(source, source / '.config')
            (output/'capabilities.json').write_text(json.dumps(result['capabilities'],indent=2)+'\n',encoding='utf-8')
            result['kernel_compile']='TESTED'
            result['kernel_compile_reason']='Image and vmlinux linked successfully; copied Image SHA256 verified'
            result['acceptance']['full_vmlinux']='TESTED'
        result['status']='success'
    except Exception as exc:
        result['failure_step']=step
        result['failure_reason']=str(exc)
        print(str(exc),file=sys.stderr)
    finally:
        ended=datetime.now(timezone.utc)
        result.update(ended_at=ended.isoformat(),duration_seconds=(ended-started).total_seconds())
        (output/'real-source-report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return 0 if result['status']=='success' else 1


if __name__=='__main__':
    raise SystemExit(main())
