"""Tests for review_queue_worker module.

These tests use the tmp_data_dir fixture which monkeypaths all mesh adapter
paths to a temp directory. Stub adapters are used to avoid real fork stores.
"""
from __future__ import annotations

import os
import tempfile
import threading
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

from src.contracts.common import UEID
from src.contracts.task_change import TaskAction, TaskChange
from src.mesh import queue as _queue
from src.mesh.review_queue_worker import (
    RunResult,
    run_once,
    start_worker,
    stop_worker,
    worker_status,
)


# === Stub Adapter for tests ===
class StubAdapter:
    """Minimal ForkAdapter for testing."""

    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.calls: list[dict[str, Any]] = []

    def read(self, ueid: UEID) -> dict[str, Any] | None:
        return None

    def apply_change(self, event) -> None:
        self.calls.append({"event_id": event.event_id, "ueid": event.ueid})
        if self.should_fail:
            raise RuntimeError(f"StubAdapter {self.name} simulated failure")

    def supports_field(self, field_name: str) -> bool:
        return True


# === Helpers ===
def make_event(
    event_id: str,
    ueid_hash: str,
    action: str = "create",
    fields: dict[str, Any] | None = None,
    source_fork: str = "cli",
) -> TaskChange:
    """Create a TaskChange with defaults.

    UEID format: type:slug:uuid:hash (4 parts, lowercase, hex chars in uuid/hash)
    Regex: ^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$
    """
    # Build valid UEID: cli:test:a1b2c3d4:e5f6a7b8
    # Part 3 and 4 must be hex (a-f + digits)
    uuid_part = "a1b2c3d4"  # valid hex for uuid
    ueid_str = f"cli:test:{uuid_part}:{ueid_hash}"
    return TaskChange(
        event_id=event_id,
        ueid=UEID(ueid_str),
        action=TaskAction(action),
        fields=fields or {"title": "Test task"},
        source_fork=source_fork,
        timestamp=datetime.now(),
        status="pending",
    )


# === Tests ===
def test_run_once_empty_queue(tmp_data_dir: Path) -> None:
    """No events → all counts zero."""
    adapters = [StubAdapter("test")]
    result = run_once(adapters)

    assert result == RunResult(consumed=0, approved=0, rejected=0, clarified=0, partial=0)


def test_run_once_approved_event(tmp_data_dir: Path) -> None:
    """Write one valid TaskChange → run_once returns approved=1, queue shows status=propagated."""
    # Create a valid event
    event = make_event("evt-001", "e5f6a7b8", fields={"title": "Buy groceries"})
    _queue.enqueue(event)

    adapters = [StubAdapter("test")]
    result = run_once(adapters)

    assert result.consumed == 1
    assert result.approved == 1
    assert result.rejected == 0
    assert result.clarified == 0
    assert result.partial == 0

    # Check queue status
    reloaded = _queue._read_event_file(tmp_data_dir / "review_queue" / "evt-001.json")
    assert reloaded.status == "propagated"


def test_run_once_rejected_event(tmp_data_dir: Path) -> None:
    """Write event with past due date → run_once returns rejected=1, status=rejected."""
    # Create event with past due date (yesterday)
    yesterday = (date.today()).isoformat()
    # Create a truly past date by using 2 days ago
    past_date = "2020-01-01"
    event = make_event(
        "evt-002", "a1b2c3d4", fields={"title": "Overdue task", "due": past_date}
    )
    _queue.enqueue(event)

    adapters = [StubAdapter("test")]
    result = run_once(adapters)

    assert result.consumed == 1
    assert result.approved == 0
    assert result.rejected == 1
    assert result.clarified == 0
    assert result.partial == 0

    # Check queue status
    reloaded = _queue._read_event_file(tmp_data_dir / "review_queue" / "evt-002.json")
    assert reloaded.status == "rejected"


def test_run_once_clarified_event(tmp_data_dir: Path) -> None:
    """Write event with vague title 'todo' → run_once returns clarified=1, status=clarify."""
    event = make_event("evt-003", "b2c3d4e5", fields={"title": "todo"})
    _queue.enqueue(event)

    adapters = [StubAdapter("test")]
    result = run_once(adapters)

    assert result.consumed == 1
    assert result.approved == 0
    assert result.rejected == 0
    assert result.clarified == 1
    assert result.partial == 0

    # Check queue status
    reloaded = _queue._read_event_file(tmp_data_dir / "review_queue" / "evt-003.json")
    assert reloaded.status == "clarified"


def test_run_once_partial_propagation(tmp_data_dir: Path) -> None:
    """Write event, one stub adapter succeeds + one raises → status=partial_propagation."""
    event = make_event("evt-004", "c3d4e5f6", fields={"title": "Partial test"})
    _queue.enqueue(event)

    adapters = [StubAdapter("good"), StubAdapter("bad", should_fail=True)]
    result = run_once(adapters)

    assert result.consumed == 1
    assert result.approved == 1
    assert result.partial == 1

    # Check queue status
    reloaded = _queue._read_event_file(tmp_data_dir / "review_queue" / "evt-004.json")
    assert reloaded.status == "partial_propagation"


def test_worker_status_no_pidfile(tmp_data_dir: Path) -> None:
    """Returns running=False."""
    pidfile = tmp_data_dir / "worker.pid"
    result = worker_status(pidfile)

    assert result["running"] is False
    assert result["pid"] is None
    assert result["started_at"] is None


def test_worker_status_stale_pidfile(tmp_data_dir: Path) -> None:
    """Write fake pidfile with PID 999999 → running=False (dead PID)."""
    pidfile = tmp_data_dir / "worker.pid"
    pidfile.write_text("999999")

    result = worker_status(pidfile)

    assert result["running"] is False
    assert result["pid"] is None
    # started_at may still be set from file mtime


def test_stop_worker_idempotent(tmp_data_dir: Path) -> None:
    """No pidfile → returns False, no exception."""
    pidfile = tmp_data_dir / "worker.pid"

    result = stop_worker(pidfile)

    assert result is False
    assert not pidfile.exists()


def test_start_worker_writes_pidfile(tmp_data_dir: Path) -> None:
    """Use a fake adapter list, start in background thread, verify pidfile created then removed."""
    pidfile = tmp_data_dir / "worker.pid"
    adapters = [StubAdapter("test")]

    # Track whether worker has run once
    run_completed = threading.Event()

    import src.mesh.review_queue_worker as worker_module
    original_run_once = worker_module.run_once

    def patched_run_once(adapter_list):
        result = original_run_once(adapter_list)
        run_completed.set()
        # Raise KeyboardInterrupt to stop the loop
        raise KeyboardInterrupt()

    worker_module.run_once = patched_run_once

    try:
        start_worker(adapters, pidfile, poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        # Restore
        worker_module.run_once = original_run_once

    # Verify run_once was called
    assert run_completed.is_set(), "run_once should have been called"

    # After worker exits, pidfile should be removed
    assert not pidfile.exists(), "pidfile should be removed on exit"


# === Fixtures ===
@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """Redirect all mesh adapter paths to a fresh tmp directory."""
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)

    # Redirect queue to tmp
    monkeypatch.setattr(_queue, "QUEUE_DIR", data_root / "review_queue")

    # Ensure queue dir exists
    (data_root / "review_queue").mkdir(parents=True, exist_ok=True)

    return data_root
