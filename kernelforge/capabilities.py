"""Read-only source and final-config evidence for optional kernel features."""
from __future__ import annotations

import re
from pathlib import Path

from .objects import inspect_object


NETWORK = {
    'bbr': ('TCP_CONG_BBR', 'net/ipv4/tcp_bbr.c', 'bbr'),
    'bbr2': ('TCP_CONG_BBR2', 'net/ipv4/tcp_bbr2.c', 'bbr2'),
    'bbr3': ('TCP_CONG_BBR3', 'net/ipv4/tcp_bbr3.c', 'bbr3'),
    'westwood': ('TCP_CONG_WESTWOOD', 'net/ipv4/tcp_westwood.c', 'westwood'),
    'cubic': ('TCP_CONG_CUBIC', 'net/ipv4/tcp_cubic.c', 'cubic'),
}
ZRAM = {
    'lz4': ('ZRAM_DEF_COMP_LZ4', 'CRYPTO_LZ4'),
    'lz4hc': ('ZRAM_DEF_COMP_LZ4HC', 'CRYPTO_LZ4HC'),
    'zstd': ('ZRAM_DEF_COMP_ZSTD', 'CRYPTO_ZSTD'),
    'lzo': ('ZRAM_DEF_COMP_LZO', 'CRYPTO_LZO'),
    'lzo-rle': ('ZRAM_DEF_COMP_LZORLE', 'CRYPTO_LZO_RLE'),
    '842': ('ZRAM_DEF_COMP_842', 'CRYPTO_842'),
}

CRYPTO_OBJECTS = {
    'lz4': 'crypto/lz4.o', 'lz4hc': 'crypto/lz4hc.o',
    'zstd': 'crypto/zstd.o', 'lzo': 'crypto/lzo.o',
    'lzo-rle': 'crypto/lzo-rle.o', '842': 'crypto/842.o',
}


def _object(root: Path, relative: str):
    path = root / relative
    if not path.is_file() or not path.stat().st_size:
        return 'UNTESTED'
    return inspect_object(path, root)


def _config(path: Path | None):
    if path is None or not path.is_file():
        return {}
    result = {}
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        match = re.fullmatch(r'(CONFIG_[A-Z0-9_]+)=(y|m|n|"[^"]*")', line)
        if match:
            result[match[1][7:]] = match[2]
    return result


def _symbols(paths):
    symbols = set()
    for path in paths:
        if path.is_file():
            symbols.update(re.findall(r'^config\s+([A-Z0-9_]+)\s*$',
                                      path.read_text(encoding='utf-8', errors='replace'), re.M))
    return symbols


def inspect(root: Path, config: Path | None = None) -> dict:
    """Evidence levels are distinct; no runtime or compile claim is inferred."""
    root = Path(root).resolve()
    if not (root / 'Makefile').is_file():
        raise ValueError('kernel root has no Makefile')
    values = _config(config if config is not None else root / '.config')
    tcp_symbols = _symbols([root / 'net/ipv4/Kconfig'])
    zram_symbols = _symbols([root / 'drivers/block/zram/Kconfig'])
    crypto_symbols = _symbols([root / 'crypto/Kconfig'])
    zram_source = root / 'drivers/block/zram/zcomp.c'
    zram_text = zram_source.read_text(encoding='utf-8', errors='replace') if zram_source.is_file() else ''
    network = {}
    for name, (symbol, source, registration) in NETWORK.items():
        path = root / source
        text = path.read_text(encoding='utf-8', errors='replace') if path.is_file() else ''
        # BBRv2/v3 may share a file with another implementation. Never infer them from BBR v1.
        registered = bool(re.search(r'\.name\s*=\s*"' + re.escape(registration) + r'"', text))
        compiled = _object(root, str(Path(source).with_suffix('.o')))
        network[name] = {
            'source_present': path.is_file(), 'kconfig_declared': symbol in tcp_symbols,
            'final_config': values.get(symbol), 'registration_found': registered,
            'object_compiled': compiled, 'runtime': 'UNTESTED',
            'status': 'TESTED' if registered and values.get(symbol) in ('y', 'm')
                      and compiled != 'UNTESTED' else 'UNTESTED',
        }
    zram = {}
    for name, (default_symbol, crypto_symbol) in ZRAM.items():
        token = name
        # zcomp lists algorithms with string names; Kconfig defaults vary across kernels.
        listed = bool(re.search(r'"' + re.escape(token) + r'"', zram_text))
        zcomp_object = _object(root, 'drivers/block/zram/zcomp.o')
        backend_object = _object(root, CRYPTO_OBJECTS[name])
        zram[name] = {
            'algorithm_listed': listed,
            'default_kconfig_declared': default_symbol in zram_symbols,
            'crypto_kconfig_declared': crypto_symbol in crypto_symbols,
            'zram_final_config': values.get('ZRAM'),
            'default_selected': values.get(default_symbol) == 'y',
            'crypto_final_config': values.get(crypto_symbol),
            'object_compiled': zcomp_object, 'backend_object': backend_object,
            'runtime_selectable': 'UNTESTED',
            'status': 'TESTED' if listed and values.get('ZRAM') in ('y', 'm')
                      and (values.get(crypto_symbol) in ('y', 'm') or values.get(default_symbol) == 'y')
                      and zcomp_object != 'UNTESTED' and backend_object != 'UNTESTED'
                      else 'UNTESTED',
        }
    return {'network': network, 'zram': zram,
            'final_config_found': bool(values), 'source_root': str(root),
            'note': 'Source, Kconfig, final config and object hashes are separate evidence; runtime remains untested.'}
