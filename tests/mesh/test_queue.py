import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.contracts.task_change import TaskChange, TaskAction
from src.mesh import queue


@pytest.fixture
def queue_dir(tmp_path: Path, monkeypatch) -> Path:
    """Create a tmp queue dir and override the module's QUEUE_DIR."""
    qdir = tmp_path / "review_queue"
    qdir.mkdir()
    monkeypatch.setattr(queue, "QUEUE_DIR", qdir)
    return qdir


def _sample_event(event_id: str = "evt_001") -> TaskChange:
    return TaskChange(
        event_id=event_id,
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action=TaskAction.CREATE,
        fields={"title": "Test"},
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )


def test_enqueue_writes_event_file_atomically(queue_dir: Path):
    """enqueue() writes file via temp + atomic rename."""
    event = _sample_event()
    event_id = queue.enqueue(event)

    assert event_id == "evt_001"
    files = list(queue_dir.glob("*.json"))
    assert len(files) == 1
    assert files[0].name == "evt_001.json"

    # Verify content is valid JSON
    content = json.loads(files[0].read_text())
    assert content["event_id"] == "evt_001"


def test_consume_pending_returns_pending_events(queue_dir: Path):
    """consume_pending() returns only events with status='pending'."""
    queue.enqueue(_sample_event("evt_a"))
    queue.enqueue(_sample_event("evt_b"))
    queue.ack("evt_a", "approved")  # not pending anymore

    events = list(queue.consume_pending())
    assert len(events) == 1
    assert events[0].event_id == "evt_b"


def test_ack_updates_status_in_place(queue_dir: Path):
    """ack() updates the event file's status field atomically."""
    queue.enqueue(_sample_event())
    queue.ack("evt_001", "approved")

    event_file = queue_dir / "evt_001.json"
    content = json.loads(event_file.read_text())
    assert content["status"] == "approved"


def test_ack_is_idempotent(queue_dir: Path):
    """Re-acking same event_id is no-op (doesn't error)."""
    queue.enqueue(_sample_event())
    queue.ack("evt_001", "approved")
    queue.ack("evt_001", "propagated")  # no-op
    content = json.loads((queue_dir / "evt_001.json").read_text())
    assert content["status"] == "approved"


def test_replay_after_restart_re_processes_pending(queue_dir: Path):
    """All pending events are visible after replay (simulates crash recovery)."""
    queue.enqueue(_sample_event("evt_1"))
    queue.enqueue(_sample_event("evt_2"))
    queue.enqueue(_sample_event("evt_3"))

    events = list(queue.replay_after_restart())
    assert len(events) == 3
    assert {e.event_id for e in events} == {"evt_1", "evt_2", "evt_3"}


def test_atomic_write_retries_on_transient_oserror(queue_dir: Path, monkeypatch):
    """Per audit B5.0-F13: transient OSError during write should be retried, not crash."""
    target = queue_dir / "retry_test.json"
    call_count = {"n": 0}

    original_replace = queue.os.replace

    def flaky_replace(src, dst):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise PermissionError("simulated EBUSY")
        return original_replace(src, dst)

    monkeypatch.setattr(queue.os, "replace", flaky_replace)

    queue._atomic_write_json(target, '{"ok": true}')

    # After 2 failures, the 3rd attempt succeeds
    assert call_count["n"] == 3
    assert target.exists()
    assert target.read_text() == '{"ok": true}'


def test_atomic_write_gives_up_after_max_attempts(queue_dir: Path, monkeypatch):
    """After max retries, the OSError propagates (caller can decide how to handle)."""
    target = queue_dir / "doomed.json"

    def always_fail(src, dst):
        raise PermissionError("persistent EBUSY")

    monkeypatch.setattr(queue.os, "replace", always_fail)

    with pytest.raises(PermissionError):
        queue._atomic_write_json(target, '{"x": 1}')

    # Target must not exist (write aborted)
    assert not target.exists()
