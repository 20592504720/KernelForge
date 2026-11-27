"""Conservative Windows path admission for external tools without a long-path proof."""
from __future__ import annotations

import os
from pathlib import Path

EXTERNAL_PATH_LIMIT = 240


def require_external_paths(*paths: Path, reserve: int = 0) -> None:
    """Reject over-budget operations before network/download/process work.

    A Python long-path probe does not qualify Git, a compiler or an extractor.
    The reserve allows room for the operation's expected descendant paths;
    individual archive members and discovered executables need their own check.
    """
    if os.name != 'nt':
        return
    for path in paths:
        size = len(str(Path(path).absolute()).encode('utf-16-le')) // 2
        if size + reserve > EXTERNAL_PATH_LIMIT:
            raise ValueError('external tool path budget exceeded; select a shorter owned workspace/cache path')
