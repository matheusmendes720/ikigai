import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.contracts.task_change import PropagationEvent, TaskAction


@pytest.fixture
def taskdog_db(tmp_path: Path, monkeypatch) -> Path:
    """Create simplified taskdog SQLite schema in tmp."""
    db_path = tmp_path / "test_tasks.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ueid TEXT,
            name TEXT,
            status TEXT,
            priority INTEGER,
            planned_start TEXT,
            planned_end TEXT,
            deadline TEXT,
            created_at TEXT
        );
        CREATE INDEX idx_tasks_ueid ON tasks(ueid);
    """)
    conn.commit()
    conn.close()

    from src.mesh.adapters import taskdog
    monkeypatch.setattr(taskdog, "TASKDOG_DB", db_path)
    return db_path


def _sample_event() -> PropagationEvent:
    return PropagationEvent(
        event_id="evt_001",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action=TaskAction.CREATE,
        fields={"title": "Test task", "due": "2099-01-01", "priority": 2},
        approved_at=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
        source_fork="interfaces/cli",
    )


def test_taskdog_adapter_apply_change_inserts_task(taskdog_db: Path):
    """apply_change inserts new row with ueid FK."""
    from src.mesh.adapters.taskdog import TaskdogAdapter

    adapter = TaskdogAdapter()
    event = _sample_event()
    adapter.apply_change(event)

    conn = sqlite3.connect(taskdog_db)
    row = conn.execute(
        "SELECT ueid, name, deadline, priority FROM tasks WHERE ueid = ?",
        (event.ueid,),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == event.ueid
    assert row[1] == "Test task"
    assert row[2] == "2099-01-01"


def test_taskdog_adapter_read_returns_slice(taskdog_db: Path):
    """read() returns slice for given UEID."""
    from src.mesh.adapters.taskdog import TaskdogAdapter

    adapter = TaskdogAdapter()
    event = _sample_event()
    adapter.apply_change(event)

    slice = adapter.read(event.ueid)
    assert slice is not None
    assert slice["ueid"] == event.ueid
    assert slice["name"] == "Test task"


def test_taskdog_adapter_is_idempotent(taskdog_db: Path):
    """apply_change called twice with same UEID updates, doesn't double-insert."""
    from src.mesh.adapters.taskdog import TaskdogAdapter

    adapter = TaskdogAdapter()
    event = _sample_event()
    adapter.apply_change(event)
    adapter.apply_change(event)  # second call

    conn = sqlite3.connect(taskdog_db)
    count = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE ueid = ?", (event.ueid,)
    ).fetchone()[0]
    conn.close()
    assert count == 1


def test_taskdog_adapter_supports_field():
    """TaskdogAdapter supports lifecycle + planning fields."""
    from src.mesh.adapters.taskdog import TaskdogAdapter

    adapter = TaskdogAdapter()
    assert adapter.supports_field("title") is True  # mapped to `name`
    assert adapter.supports_field("due") is True    # mapped to `deadline`
    assert adapter.supports_field("priority") is True
    assert adapter.supports_field("rrule") is False  # calendar-only
