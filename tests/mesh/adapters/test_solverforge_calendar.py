"""Tests for SolverforgeCalendarAdapter."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.contracts.task_change import PropagationEvent, TaskAction


def _create_schema(conn: sqlite3.Connection) -> None:
    """Idempotent schema bootstrap with ueid column (v3 migration equivalent)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS unified_planning_items (
            id TEXT PRIMARY KEY,
            ueid TEXT UNIQUE,
            status TEXT,
            start_at TEXT,
            end_at TEXT,
            blocked_by TEXT,
            tags TEXT,
            ikigai TEXT,
            provenance TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_upi_ueid ON unified_planning_items(ueid);
    """)


@pytest.fixture
def upi_db_with_migration(tmp_path: Path, monkeypatch) -> Path:
    """Create UPI DB with v3 migration applied (ueid TEXT UNIQUE column)."""
    db_path = tmp_path / "test_unified_planning.db"
    conn = sqlite3.connect(db_path)
    # Create table directly with ueid column (equivalent to v3 migration result)
    conn.executescript("""
        CREATE TABLE unified_planning_items (
            id TEXT PRIMARY KEY,
            ueid TEXT UNIQUE,
            status TEXT,
            start_at TEXT,
            end_at TEXT,
            blocked_by TEXT,
            tags TEXT,
            ikigai TEXT,
            provenance TEXT
        );
    """)
    conn.commit()
    conn.close()

    # Patch the UPI_DB path in the adapter module
    from src.mesh.adapters import solverforge_calendar
    monkeypatch.setattr(solverforge_calendar, "UPI_DB", db_path)
    return db_path


def _sample_event() -> PropagationEvent:
    return PropagationEvent(
        event_id="evt_001",
        ueid="tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
        action=TaskAction.CREATE,
        fields={"title": "Test task", "due": "2099-01-01"},
        approved_at=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
        source_fork="interfaces/cli",
    )


def test_solverforge_adapter_apply_change_inserts_upi_row(upi_db_with_migration: Path):
    """apply_change inserts new UPI row with ueid column populated."""
    from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter

    adapter = SolverforgeCalendarAdapter()
    event = _sample_event()
    adapter.apply_change(event)

    conn = sqlite3.connect(upi_db_with_migration)
    row = conn.execute(
        "SELECT ueid, status, ikigai FROM unified_planning_items WHERE ueid = ?",
        (event.ueid,),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == event.ueid
    assert row[1] == "planned"
    ikigai = json.loads(row[2])
    assert ikigai["title"] == "Test task"
    assert ikigai["source_fork"] == "interfaces/cli"


def test_solverforge_adapter_read_returns_slice(upi_db_with_migration: Path):
    """read() returns slice for given UEID."""
    from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter

    adapter = SolverforgeCalendarAdapter()
    event = _sample_event()
    adapter.apply_change(event)

    slice = adapter.read(event.ueid)
    assert slice is not None
    assert slice["ueid"] == event.ueid


def test_solverforge_adapter_supports_field():
    """SolverforgeCalendarAdapter supports scheduling + aggregate fields."""
    from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter

    adapter = SolverforgeCalendarAdapter()
    assert adapter.supports_field("title") is True
    assert adapter.supports_field("status") is True
    assert adapter.supports_field("start_at") is True
    assert adapter.supports_field("end_at") is True
    assert adapter.supports_field("rrule") is True
    assert adapter.supports_field("deadline") is False  # taskdog uses this
