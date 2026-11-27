"""Verify real ARM64 relocatable objects; dry-run output is not evidence."""
import hashlib
import re
import struct
import subprocess
from pathlib import Path


def archive_members(path, root):
    path,root=Path(path).resolve(),Path(root).resolve()
    if root not in path.parents or not path.is_file() or path.read_bytes()[:8] not in (b'!<arch>\n',b'!<thin>\n'):
        raise ValueError(f'missing or invalid Kbuild archive: {path}')
    names=subprocess.check_output(['llvm-ar','t',str(path)],cwd=root,text=True,timeout=120).splitlines()
    if not names:
        raise ValueError('Kbuild archive contains no compiled objects')
    # Thin archive member names are emitted relative to the build root.
    objects=[]
    for name in names:
        target=(root/name).resolve()
        if not target.is_file():
            target=(path.parent/name).resolve()
        if root not in target.parents or target.suffix!='.o' or not target.is_file():
            raise ValueError(f'unsafe or missing Kbuild archive member: {name}')
        if target not in objects:
            objects.append(target)
    return objects


def inspect_object(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    if root not in path.parents or not path.is_file():
        raise ValueError(f'missing or unsafe object file: {path}')
    data = path.read_bytes()
    format_name = 'ELF64 ARM64 relocatable'
    if data.startswith((b'BC\xc0\xde', b'\xde\xc0\x17\x0b')):
        # Keep the selected kernel's LTO/CFI configuration. LLVM bitcode is a
        # real compiled object; validate with LLVM instead of disabling LTO.
        ir = subprocess.run(['llvm-dis',str(path),'-o','-'],capture_output=True,text=True,timeout=60,check=False)
        if ir.returncode or not re.search(r'target triple = "aarch64[^"\n]*"',ir.stdout):
            raise ValueError(f'invalid or non-ARM64 LLVM bitcode object: {path}')
        format_name = 'LLVM ARM64 bitcode'
    elif len(data) < 64 or data[:6] != b'\x7fELF\x02\x01':
        raise ValueError(f'not an ELF64 little-endian object: {path}')
    else:
        kind, machine = struct.unpack_from('<HH', data, 16)
        if kind != 1 or machine != 183:
            raise ValueError(f'not an ARM64 relocatable object: {path}')
    return {'path':str(path.relative_to(root)), 'bytes':len(data),
            'sha256':hashlib.sha256(data).hexdigest(), 'format':format_name,'status':'TESTED'}
