"""Small, dependency-free measurement helpers; no change to build admission."""
from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from pathlib import Path


def file_sha256(path: Path) -> str:
    """Hash actual file bytes with bounded memory (Python 3.11+)."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class PhaseTimer:
    """Record consecutive phases using a monotonic clock, including failure paths.

    Names are internal constants, not user arguments or command output.
    Durations cover the instrumented interval, not runner queue or setup.
    """
    def __init__(self, *, clock: Callable[[], int] = time.monotonic_ns):
        self._clock = clock
        self._phase: str | None = None
        self._start_ns = 0
        self._records: list[dict] = []
        self._finished = False

    def _close(self, now: int, status: str) -> None:
        if self._phase is not None:
            self._records.append({
                "phase": self._phase,
                "duration_ns": max(0, now - self._start_ns),
                "status": status,
            })

    def start(self, phase: str) -> None:
        if self._finished:
            raise RuntimeError("phase timer already finished")
        now = self._clock()
        self._close(now, "success")
        self._phase = phase
        self._start_ns = now

    def finish(self, *, success: bool) -> dict:
        if self._finished:
            raise RuntimeError("phase timer already finished")
        self._close(self._clock(), "success" if success else "failure")
        self._finished = True
        return {
            "schema_version": 1,
            "clock": "monotonic_ns",
            "phases": list(self._records),
            "total_ns": sum(record["duration_ns"] for record in self._records),
        }
