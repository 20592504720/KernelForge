"""Select reviewed SUSFS context adapters only for exact locked source combinations."""
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from .source import _run_git
from .susfs import digest

ROOT=Path(__file__).resolve().parents[1]


def select(kernel, provider, upstream, original, *, catalog=None):
    catalog=Path(catalog) if catalog else ROOT/'patches/compat/susfs/manifest.json'
    if not catalog.is_file():
        return original,None
    meta=json.loads(catalog.read_text(encoding='utf-8'))
    schema=json.loads((ROOT/'schemas/susfs-compat.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator(schema).validate(meta)
    try:
        identities=[_run_git(['rev-parse','HEAD'],cwd=path) for path in (kernel,provider,upstream)]
    except RuntimeError:
        return original,None
    if identities[0]!=meta['kernel_commit'] or identities[1] not in meta['provider_commits'] or identities[2]!=meta['susfs_commit']:
        return original,None
    if digest(original)!=meta['upstream_patch_sha256']:
        raise ValueError('exact-baseline SUSFS upstream patch hash mismatch')
    unresolved=catalog.parent/meta['file']
    candidate=unresolved.resolve()
    if catalog.parent.resolve() not in candidate.parents or unresolved.is_symlink() or not candidate.is_file():
        raise ValueError('unsafe or missing SUSFS compatibility patch')
    if digest(candidate)!=meta['sha256']:
        raise ValueError('SUSFS compatibility patch SHA256 mismatch')
    # Context adaptation must not remove or alter any upstream code changes.
    changes=lambda path:[line for line in path.read_text(encoding='utf-8').splitlines() if line.startswith(('+','-')) and not line.startswith(('+++','---'))]
    if changes(original)!=changes(candidate):
        raise ValueError('context adapter altered upstream code changes')
    return candidate,meta
