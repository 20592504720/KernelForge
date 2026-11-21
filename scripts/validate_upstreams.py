"""Opt-in real Android GKI source validation. Never claims boot/root success."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kernelforge import development
from kernelforge.kernelsu import integrate
from kernelforge.source import checkout, _run_git
from kernelforge.versions import resolve


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--provider',choices=['official','bakasu'],required=True)
    parser.add_argument('--susfs',action='store_true')
    parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args()
    work=args.workspace.resolve(); output=work/'report'; output.mkdir(parents=True,exist_ok=True)
    result={'provider':args.provider,'status':'failure','kconfig':'UNTESTED','kbuild':'UNTESTED','kernel_compile':'UNTESTED','boot':'UNTESTED','root':'UNTESTED'}
    try:
        profile=ROOT/'configs/kernelsu'/('official-development.json' if args.provider=='official' else 'bakasu-development.json')
        config={'kernelsu':json.loads(profile.read_text())}
        if args.susfs:
            config['susfs']={'enabled':True,'repository':'https://gitlab.com/simonpunk/susfs4ksu.git','version_policy':'latest_branch','android_gki':'android14-6.1','allow_bakasu_inline':True}
        lock=development.prepare(config,work,output)
        kernel_lock=resolve({'repository':'https://github.com/aosp-mirror/kernel_common.git','version_policy':'latest_branch','branch':'android14-6.1','method':'GKI ARM64 source validation'})
        lock['upstreams']['kernel']=kernel_lock
        (output/'versions.lock.json').write_text(json.dumps(lock,indent=2)+'\n',encoding='utf-8')
        source=work/'source'
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
        # Target code uses LLVM; host helpers in this ACK revision require the
        # GNU host compiler rather than the runner's newer Clang diagnostics.
        command=['make','ARCH=arm64','LLVM=1','HOSTCC=gcc','HOSTCXX=g++']
        def run(argv):
            process=subprocess.run(argv,cwd=source,capture_output=True,text=True,timeout=600,check=False)
            with (output/'source-check.log').open('a',encoding='utf-8') as stream:
                stream.write('$ '+' '.join(argv)+'\n'+process.stdout+process.stderr)
            if process.returncode:
                raise ValueError(f'real source command failed: {argv[0]} (exit {process.returncode})')
        run(command+['gki_defconfig'])
        symbols=['KSU','SECURITY_SELINUX','ARM64','KALLSYMS','KALLSYMS_ALL','TRACEPOINTS','KPROBES','EXT4_FS']
        symbols+=['KSU_SUSFS','THREAD_INFO_IN_TASK'] if args.susfs else (['KSU_TRACEPOINT_HOOK'] if args.provider=='bakasu' else [])
        for symbol in symbols:
            run(['scripts/config','--enable',symbol])
        result['integration'],result['susfs']=development.integrate_locked(config,lock,source,output,mode='gki',integrator=integrate)
        run(command+['olddefconfig'])
        final=(source/'.config').read_text().splitlines()
        for symbol in symbols:
            if f'CONFIG_{symbol}=y' not in final:
                raise ValueError(f'final Kconfig dropped CONFIG_{symbol}=y')
        result['kconfig']='TESTED'
        run(command+['prepare'])
        run(command+['-n','drivers/kernelsu/'])
        result['kbuild']='TESTED (prepare and dry run; no KernelSU object compilation claim)'
        result['status']='success'
    except Exception as exc:
        result['failure_reason']=str(exc)
        print(str(exc),file=sys.stderr)
    finally:
        (output/'real-source-report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return 0 if result['status']=='success' else 1


if __name__=='__main__':
    raise SystemExit(main())
