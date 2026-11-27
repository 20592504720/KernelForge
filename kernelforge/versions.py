"""Resolve moving upstreams once, then use immutable Git commits exclusively."""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from urllib.parse import urlsplit
from urllib.request import Request

from .http_safety import open_metadata, read_bounded, require_https_host
from .source import _run_git, validate_repository


def timestamp():
    return datetime.now(UTC).isoformat()


def releases(repository):
    parsed = require_https_host(repository, 'github.com')
    name = parsed.path.strip('/').removesuffix('.git')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9._-]*', name) or '..' in name:
        raise ValueError('invalid GitHub release repository identity')
    rows = []
    for page in range(1, 11):
        request = Request(f'https://api.github.com/repos/{name}/releases?per_page=100&page={page}', headers={'User-Agent': 'KernelForge'})
        with open_metadata(request, host='api.github.com', timeout=60, allow_query=True) as response:
            batch = json.loads(read_bounded(response, 8 * 1024 * 1024))
        if not isinstance(batch, list) or len(batch) > 100 or any(not isinstance(row, dict) for row in batch):
            raise ValueError('invalid release API response')
        rows.extend(batch)
        if len(batch) < 100:
            return rows
    raise ValueError('release discovery pagination limit exceeded; refusing incomplete results')


def resolve(spec, *, git=_run_git, release_query=releases):
    repository = spec['repository']
    validate_repository(repository)
    parsed = urlsplit(repository)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('upstream URL must not contain credentials or query parameters')
    policy = spec.get('version_policy', 'pinned')
    ref_type, ref = spec.get('ref_type', 'commit'), spec.get('ref')
    branch = None
    if policy == 'latest_branch':
        branch = spec.get('branch', 'main')
        ref, ref_type = branch, 'branch'
    elif policy in ('latest_release', 'latest_prerelease'):
        prerelease = policy == 'latest_prerelease'
        candidates = [r for r in release_query(repository) if not r.get('draft') and bool(r.get('prerelease')) == prerelease]
        if not candidates:
            raise ValueError(f'no upstream release satisfies {policy}')
        selected = max(candidates, key=lambda r: (r.get('published_at') or '', r.get('id', 0)))
        ref, ref_type = selected['tag_name'], 'tag'
    elif policy != 'pinned':
        raise ValueError(f'unsupported version policy: {policy}')
    if not isinstance(ref, str) or not ref or ref.startswith('-') or any(c.isspace() for c in ref):
        raise ValueError('invalid upstream reference')
    if ref_type == 'commit':
        sha = ref
    else:
        branch = ref if ref_type == 'branch' else None
        namespace = 'heads' if ref_type == 'branch' else 'tags'
        output = git(['ls-remote', repository, f'refs/{namespace}/{ref}', f'refs/{namespace}/{ref}^{{}}'], timeout=60)
        refs = {line.split()[1]: line.split()[0] for line in output.splitlines() if len(line.split()) == 2}
        sha = refs.get(f'refs/{namespace}/{ref}^{{}}') or refs.get(f'refs/{namespace}/{ref}')
    if not isinstance(sha, str) or not re.fullmatch('[0-9a-fA-F]{40}', sha):
        raise ValueError('upstream reference did not resolve to a full Commit SHA')
    if policy == 'pinned' and sha.lower() != spec.get('expected_commit', sha).lower():
        raise ValueError('upstream reference differs from expected_commit')
    return {'repository': repository, 'policy': policy, 'requested_ref': ref, 'ref_type': ref_type,
            'branch': branch, 'commit_sha': sha.lower(), 'resolved_at': timestamp(),
            'method': spec.get('method'), 'patches': []}


def freeze(spec, lock):
    """Produce a pinned integration input without looking up a moving ref again."""
    result = dict(spec)
    for key in ('version_policy', 'branch'):
        result.pop(key, None)
    result.update(ref_type='commit', ref=lock['commit_sha'], expected_commit=lock['commit_sha'])
    return result
