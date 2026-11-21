"""Bounded retries for Windows sharing violations; permanent errors propagate."""
import os
import time


def retry_windows(operation, *, attempts=7):
    for attempt in range(attempts):
        try:
            return operation()
        except PermissionError as exc:
            if getattr(exc,'winerror',None) not in (5,32,33) or attempt == attempts-1:
                raise
            time.sleep(min(0.05 * 2**attempt,0.4))


def atomic_replace(source, destination):
    return retry_windows(lambda: os.replace(source,destination))
