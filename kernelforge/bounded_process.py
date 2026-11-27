"""Bounded generic build stdout/stderr spool, without changing build argv.

A reader drains discarded bytes after the limit so a noisy child does not
deadlock. Only the direct child is controlled: a retained descendant pipe
fails closed after a short drain deadline. This is not a process-tree sandbox
or a physical-host disk quota.
"""
from __future__ import annotations

import shutil
import subprocess
import threading
from io import BufferedReader

MAX_RAW_LOG = 128 * 1024**2
DISK_RESERVE = 64 * 1024**2


def run_bounded_capture(argv, *, cwd, env, timeout, spool, disk_path, evidence,
                        max_bytes=MAX_RAW_LOG, reserve=DISK_RESERVE, drain_timeout=2):
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_RAW_LOG:
        raise ValueError("invalid raw log budget")
    if shutil.disk_usage(disk_path).free < reserve:
        raise OSError("raw log disk reserve exhausted")
    state = {"bytes": 0, "line_end": 0, "limited": False, "error": None, "stopped": False}
    mutex = threading.Lock()
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)

    def reader():
        try:
            if process.stdout is None:
                raise OSError('child stdout pipe is unavailable')
            with process.stdout as source:
                while True:
                    chunk = source.read1(64 * 1024) if isinstance(source, BufferedReader) else source.read(64 * 1024)
                    if not chunk:
                        break
                    with mutex:
                        if state["stopped"]:
                            return
                        if state["limited"] or state["error"]:
                            continue
                        try:
                            remaining = max_bytes - state["bytes"]
                            data = chunk[:remaining]
                            if shutil.disk_usage(disk_path).free < reserve + len(data):
                                state["error"] = OSError("raw log disk reserve exhausted")
                                continue
                            spool.write(data)
                            last = data.rfind(b"\n")
                            if last >= 0:
                                state["line_end"] = state["bytes"] + last + 1
                            state["bytes"] += len(data)
                            if len(chunk) > len(data):
                                state["limited"] = True
                        except OSError as exc:
                            state["error"] = exc
        except (OSError, ValueError) as exc:
            with mutex:
                if not state["stopped"]:
                    state["error"] = exc

    worker = threading.Thread(target=reader, daemon=True, name="kernelforge-log-drain")
    worker.start()
    try:
        result = process.wait(timeout=timeout)
    except BaseException:
        if process.poll() is None:
            process.kill()
            process.wait()
        raise
    finally:
        worker.join(drain_timeout)
        with mutex:
            state["stopped"] = True
            incomplete = worker.is_alive() or state["limited"] or state["error"] is not None
            if incomplete:
                # Never expose a partial credential at the byte boundary.
                spool.truncate(state["line_end"])
            spool.flush()
            evidence.update(raw_spool_bytes=state["line_end"] if incomplete else state["bytes"],
                            raw_capture_truncated=bool(incomplete),
                            raw_capture_limit=max_bytes,
                            raw_capture_drain_complete=not worker.is_alive())
    if worker.is_alive():
        raise OSError("subprocess output pipe did not close; descendant state unverified")
    if state["error"]:
        raise OSError("bounded subprocess log capture failed") from state["error"]
    return result
