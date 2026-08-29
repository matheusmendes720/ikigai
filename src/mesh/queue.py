"""Filesystem-based append-only review queue. Atomic writes via temp + rename.

Per audit B5.0-F13: queue.enqueue() and ack() are wrapped with retry decorators
to handle transient filesystem errors (EBUSY on Windows, NFS stale handles, etc.).
"""
import os
import time
from pathlib import Path
from typing import Iterator

from src.contracts.task_change import TaskChange, TaskStatus

# Project root is 2 levels up from src/mesh/
PROJECT_ROOT = Path(__file__).parent.parent.parent
QUEUE_DIR = PROJECT_ROOT / "data" / "review_queue"

# Retry configuration for atomic file operations. Transient errors (Windows
# EBUSY when another process has the file open, NFS stale handles) are common
# in concurrent scenarios. Retries with exponential backoff + jitter.
_MAX_ATTEMPTS = 4
_INITIAL_BACKOFF_S = 0.1
_MAX_BACKOFF_S = 2.0
_RETRYABLE_EXCEPTIONS = (OSError, PermissionError)


def _retry_atomic_write(write_fn):
    """Decorator: retry an atomic file operation on transient OSError.

    The wrapped function should perform the entire temp+rename sequence and
    raise on failure. Backoff is exponential with jitter.
    """
    def wrapper(*args, **kwargs):
        backoff = _INITIAL_BACKOFF_S
        last_exc = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return write_fn(*args, **kwargs)
            except _RETRYABLE_EXCEPTIONS as exc:
                last_exc = exc
                if attempt >= _MAX_ATTEMPTS:
                    raise
                # Jitter: ±50% of backoff
                sleep_for = backoff * (0.5 + (attempt * 0.137) % 1.0)
                time.sleep(min(sleep_for, _MAX_BACKOFF_S))
                backoff = min(backoff * 2.0, _MAX_BACKOFF_S)
        # Unreachable, but mypy wants it
        raise last_exc  # type: ignore[misc]
    return wrapper


def _ensure_queue_dir() -> Path:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return QUEUE_DIR


@_retry_atomic_write
def _atomic_write_json(target: Path, content: str) -> None:
    """Write content to target via temp + fsync + rename. Idempotent retry wrapper."""
    tmp = target.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, target)


def enqueue(event: TaskChange) -> str:
    """Append event to queue. Atomic write via temp file + rename."""
    qdir = _ensure_queue_dir()
    target = qdir / f"{event.event_id}.json"
    _atomic_write_json(target, event.model_dump_json())
    return event.event_id


def _read_event_file(path: Path) -> TaskChange:
    return TaskChange.model_validate_json(path.read_text())


def consume_pending() -> Iterator[TaskChange]:
    """Iterate over events with status='pending'."""
    qdir = _ensure_queue_dir()
    for path in sorted(qdir.glob("*.json")):
        try:
            event = _read_event_file(path)
            if event.status == "pending":
                yield event
        except Exception:
            continue  # skip malformed files


def ack(event_id: str, status: TaskStatus) -> None:
    """Update event status in place. Idempotent (no-op if event not pending)."""
    qdir = _ensure_queue_dir()
    target = qdir / f"{event_id}.json"
    if not target.exists():
        return  # idempotent

    event = _read_event_file(target)
    if event.status != "pending":
        return  # already processed

    # Re-emit with new status (frozen model requires new instance)
    updated = event.model_copy(update={"status": status})
    _atomic_write_json(target, updated.model_dump_json())


def replay_after_restart() -> Iterator[TaskChange]:
    """Re-process all pending events (called on agent startup)."""
    yield from consume_pending()
