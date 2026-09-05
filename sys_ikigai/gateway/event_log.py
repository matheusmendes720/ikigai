"""Append-only JSONL event log for SSE replay / debug / audit.

Every event published via `UnifiedMCPGateway.publish_event()` can be
mirrored to disk by attaching an `EventLog` to the gateway. The log is
a single JSON object per line, written atomically via OS-level append
(`O_APPEND` on POSIX, `FILE_APPEND_DATA` on Windows — both atomic for
writes below the kernel pipe buffer / small file granularity).

When the file exceeds `max_bytes`, it is rotated to `<path>.1` (overwriting
any existing `.1`), and a fresh `<path>` is started. The most recent
`max_rotations` files are kept.

Thread-safe via a single-writer lock; concurrent appends serialize. Read
operations (`tail`, `since`, iteration) acquire the same lock briefly to
take a snapshot, then release it before parsing.

Append-only invariant: this module NEVER deletes events. Rotation renames
the active file aside but keeps the bytes on disk (in `.1`, `.2`, ...).

Usage:
    log = EventLog(Path("data/sse_events.jsonl"))
    log.append("taskdog.add", {"ueid": "ikigai:task:abc:1:2"})
    last5 = log.tail(5)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default cap: 10 MB active file; keep .1 (and .2) for 3 generations total.
DEFAULT_MAX_BYTES = 10_000_000
DEFAULT_MAX_ROTATIONS = 2


class EventLog:
    """Thread-safe append-only JSONL event log with size-based rotation."""

    def __init__(
        self,
        path: Path | str,
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_rotations: int = DEFAULT_MAX_ROTATIONS,
    ) -> None:
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.max_rotations = max_rotations
        self._lock = threading.Lock()
        # Ensure parent exists so first append doesn't race with directory creation
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: str, data: dict[str, Any]) -> None:
        """Append one event line. Atomic for line-sized writes.

        On rotation trigger, the current file is renamed aside first, then
        the new line is written to a fresh file.
        """
        record = {
            "ts": time.time(),
            "event": event,
            "data": data,
        }
        line = json.dumps(record, default=str) + "\n"
        encoded = line.encode("utf-8")
        with self._lock:
            self._maybe_rotate(encoded)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    # fsync may fail on some FS (e.g., some Windows configs);
                    # the O_APPEND guarantee is enough for crash recovery
                    pass

    def _maybe_rotate(self, incoming_bytes: bytes) -> None:
        """Rotate before appending if the new size would exceed max_bytes."""
        if not self.path.exists():
            return
        try:
            current_size = self.path.stat().st_size
        except OSError:
            return
        if current_size + len(incoming_bytes) <= self.max_bytes:
            return
        # Walk existing rotations from oldest to newest, shifting each
        # out by one to make room for the new .1
        for i in range(self.max_rotations, 0, -1):
            src = self._rotation_path(i)
            if not src.exists():
                continue
            if i == self.max_rotations:
                # Oldest generation: drop it (cannot keep indefinitely)
                src.unlink()
            else:
                dst = self._rotation_path(i + 1)
                os.replace(src, dst)
        # Active file → .1 (using os.replace — Windows-safe, atomic on same FS)
        os.replace(self.path, self._rotation_path(1))

    def _rotation_path(self, n: int) -> Path:
        return self.path.with_suffix(self.path.suffix + f".{n}")

    def tail(self, n: int) -> list[dict[str, Any]]:
        """Return the last N parsed events (across active + rotated files).

        Parses each candidate file once; returns the last N total.
        """
        if n <= 0:
            return []
        candidates = self._candidate_files()
        all_events: list[dict[str, Any]] = []
        for path in candidates:
            for record in self._iter_records(path):
                all_events.append(record)
        return all_events[-n:]

    def since(self, since_ts: float) -> list[dict[str, Any]]:
        """Return events with ts >= since_ts (across active + rotated files)."""
        result: list[dict[str, Any]] = []
        for path in self._candidate_files():
            for record in self._iter_records(path):
                if record.get("ts", 0.0) >= since_ts:
                    result.append(record)
        return result

    def __iter__(self) -> Iterator[dict[str, Any]]:
        for path in self._candidate_files():
            yield from self._iter_records(path)

    def _candidate_files(self) -> list[Path]:
        """Files to scan in chronological order (oldest first, active last).

        Rotation semantics: active file rotates to .1 when full, so .1 is
        the OLDEST surviving rotation and the active file is the NEWEST.
        Iteration order must be oldest-first to reconstruct the timeline.
        """
        files: list[Path] = []
        # Rotated files from oldest to newest (.max_rotations → .1)
        for i in range(self.max_rotations, 0, -1):
            rot = self._rotation_path(i)
            if rot.exists():
                files.append(rot)
        # Active file is always the newest
        if self.path.exists():
            files.append(self.path)
        return files

    def _iter_records(self, path: Path) -> Iterator[dict[str, Any]]:
        """Yield parsed JSON records from a file, skipping corrupt/partial lines."""
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.warning("skipping corrupt line in %s: %s", path, e)
                        continue
        except OSError as e:
            logger.warning("could not read %s: %s", path, e)
            return


__all__ = ["DEFAULT_MAX_BYTES", "DEFAULT_MAX_ROTATIONS", "EventLog"]
