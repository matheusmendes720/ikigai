"""Filesystem-based append-only review queue. Atomic writes via temp + rename."""
import json
import os
import tempfile
from pathlib import Path
from typing import Iterator

from src.contracts.task_change import TaskChange, TaskStatus

# Project root is 2 levels up from src/mesh/
PROJECT_ROOT = Path(__file__).parent.parent.parent
QUEUE_DIR = PROJECT_ROOT / "data" / "review_queue"


def _ensure_queue_dir() -> Path:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return QUEUE_DIR


def enqueue(event: TaskChange) -> str:
    """Append event to queue. Atomic write via temp file + rename."""
    qdir = _ensure_queue_dir()
    target = qdir / f"{event.event_id}.json"
    tmp = target.with_suffix(".tmp")

    content = event.model_dump_json()
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, target)  # atomic on same filesystem
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
    from src.contracts.task_change import TaskChange

    updated = event.model_copy(update={"status": status})
    tmp = target.with_suffix(".tmp")
    tmp.write_text(updated.model_dump_json())
    os.replace(tmp, target)


def replay_after_restart() -> Iterator[TaskChange]:
    """Re-process all pending events (called on agent startup)."""
    yield from consume_pending()
