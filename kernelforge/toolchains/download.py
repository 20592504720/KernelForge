"""HTTP(S) downloader with isolated temporary files and atomic publication."""
from __future__ import annotations

import os
import shutil
import time
import uuid
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from ..security import redact_diagnostic

MAX_DOWNLOAD_BYTES = 8 * 1024**3
MIN_FREE_BYTES = 64 * 1024**2


class DownloadError(RuntimeError):
    pass


def download(url: str, destination: Path, *, timeout: float = 60, retries: int = 2,
             expected_size: int | None = None, opener=urlopen,
             max_bytes: int = MAX_DOWNLOAD_BYTES) -> dict:
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        raise DownloadError("toolchain download URL must use HTTP or HTTPS")
    if retries < 0 or timeout <= 0:
        raise DownloadError("download retries must be non-negative and timeout must be positive")
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_DOWNLOAD_BYTES:
        raise DownloadError("invalid download byte budget")
    if expected_size is not None and (type(expected_size) is not int or not 0 <= expected_size <= max_bytes):
        raise DownloadError("expected size exceeds download byte budget")
    limit = max_bytes if expected_size is None else expected_size
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    last_error = None
    for attempt in range(retries + 1):
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.part")
        try:
            request = Request(url, headers={"User-Agent": "KernelForge-toolchain-manager/1"})
            size = 0
            with opener(request, timeout=timeout) as response, temporary.open("xb") as output:
                declared = response.headers.get("Content-Length")
                declared_size = None
                if declared is not None:
                    try:
                        declared_size = int(declared)
                    except (ValueError, TypeError) as exc:
                        raise DownloadError("invalid Content-Length header") from exc
                    if not 0 <= declared_size <= limit:
                        raise DownloadError("declared download exceeds byte budget")
                while True:
                    chunk = response.read(min(1024 * 1024, limit - size + 1))
                    if not chunk:
                        break
                    if size + len(chunk) > limit:
                        raise DownloadError("stream exceeds download byte budget")
                    if shutil.disk_usage(destination.parent).free < MIN_FREE_BYTES + len(chunk):
                        raise DownloadError("download would violate free disk reserve")
                    output.write(chunk)
                    size += len(chunk)
                if declared_size is not None and size != declared_size:
                    raise DownloadError(f"incomplete download: expected {declared_size} bytes, received {size}")
                output.flush()
                os.fsync(output.fileno())
            if expected_size is not None and size != expected_size:
                raise DownloadError(f"download size mismatch: expected {expected_size} bytes, received {size}")
            os.replace(temporary, destination)
            return {"size": size, "duration_seconds": round(time.monotonic() - started, 3), "attempts": attempt + 1}
        except (OSError, URLError, TimeoutError, DownloadError) as exc:
            last_error = exc
            temporary.unlink(missing_ok=True)
            if attempt >= retries:
                break
            time.sleep(min(0.1 * (attempt + 1), 1.0))
    raise DownloadError(redact_diagnostic(f"download failed after {retries + 1} attempt(s): {last_error}")) from last_error
