"""UTF-8 evidence with atomic publication, integrity checks and immutable names."""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from pathlib import Path

from .file_safety import pinned_parent, read_regular_bytes

MAX_JSON_BYTES = 16 * 1024 * 1024


def write_json(path: Path, value: object) -> dict:
    """Publish only complete JSON. Existing evidence is never overwritten.

    File data is fsynced before publication. POSIX also fsyncs the directory.
    Atomic name publication protects against process interruption; power-loss
    persistence still depends on the filesystem, mount and storage hardware.
    Windows directory durability is not promised. Never infer success from a
    surviving pending file, or retry under an existing published name blindly.
    """
    path = Path(path).absolute()
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')
    if len(data) > MAX_JSON_BYTES:
        raise ValueError('JSON evidence size exceeds limit')
    with pinned_parent(path, create=True) as parent:
        name = '.' + path.name + '-' + uuid.uuid4().hex + '.pending'
        staged = path.parent / name if parent is None else name
        descriptor = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent)
        try:
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(staged, path if parent is None else path.name, src_dir_fd=parent, dst_dir_fd=parent)
            if parent is not None:
                os.fsync(parent)
        finally:
            os.unlink(staged, dir_fd=parent)
        if parent is not None:
            os.fsync(parent)
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'durability': 'FILE_AND_DIRECTORY_FSYNC' if os.name == 'posix' else 'FILE_FSYNC_ONLY'}


def read_json(path: Path, expected_sha256: str, *, max_bytes: int = MAX_JSON_BYTES) -> object:
    if not isinstance(expected_sha256, str) or not re.fullmatch('[0-9a-f]{64}', expected_sha256):
        raise ValueError('expected evidence SHA256 must be lowercase hexadecimal')
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_JSON_BYTES:
        raise ValueError('invalid JSON evidence size limit')
    data = read_regular_bytes(path, max_bytes=max_bytes)
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError('evidence SHA256 mismatch')
    return json.loads(data.decode('utf-8', errors='strict'))
