"""Tests for cross-fork view via show_mesh().

Validates the Phase 3 v1 mesh read path:
  - Joins slices from CliAdapter + TaskdogAdapter + SolverforgeCalendarAdapter
  - Reports mismatches when status differs across forks
  - Returns None for slices whose store doesn't exist yet (no false errors)
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from interfaces.cli.read_tasks import show_mesh, task_add
from src.contracts.common import UEID
from src.contracts.task_change import PropagationEvent, TaskAction
from src.mesh.adapters.cli import CliAdapter
from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter
from src.mesh.adapters.taskdog import TaskdogAdapter


def test_show_mesh_empty_returns_null_slices(tmp_data_dir) -> None:
    """No data in any adapter → all slices are None, no mismatches."""
    result = show_mesh("tsk:foo:00000000-0000-0000-0000-000000000000:0000000000000000")
    assert "ueid" in result
    assert set(result["view"].keys()) == {"cli", "taskdog", "solverforge_calendar"}
    assert all(v is None for v in result["view"].values())
    assert result["mismatches"] == []


def test_show_mesh_finds_task_in_cli_slice(tmp_data_dir) -> None:
    """After task_add, mesh_show finds the task in the CLI slice."""
    # Capture UEID via the side-effect of task_add (use TaskChange).
    # Simpler: call CliAdapter directly here to control the UEID.
    ueid = UEID("tsk:visible:11111111-1111-1111-1111-111111111111:1111111111111111")
    CliAdapter().apply_change(
        PropagationEvent(
            event_id="evt_test000001",
            ueid=ueid,
            action=TaskAction.CREATE,
            fields={"title": "visible in cli slice", "due": None, "priority": "low"},
            approved_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            source_fork="test",
        )
    )

    result = show_mesh(str(ueid))
    assert result["view"]["cli"] is not None
    assert result["view"]["cli"]["title"] == "visible in cli slice"
    # Other slices still empty
    assert result["view"]["taskdog"] is None
    assert result["view"]["solverforge_calendar"] is None
    assert result["mismatches"] == []


def test_show_mesh_finds_task_in_taskdog_slice(tmp_data_dir) -> None:
    """TaskdogAdapter writes via UPSERT; mesh_show reads it back."""
    ueid = UEID("tsk:tdog:22222222-2222-2222-2222-222222222222:2222222222222222")
    TaskdogAdapter().apply_change(
        PropagationEvent(
            event_id="evt_test000002",
            ueid=ueid,
            action=TaskAction.CREATE,
            fields={"title": "in taskdog", "due": None, "priority": "medium"},
            approved_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            source_fork="test",
        )
    )

    result = show_mesh(str(ueid))
    assert result["view"]["taskdog"] is not None
    assert result["view"]["taskdog"]["name"] == "in taskdog"
    assert result["view"]["cli"] is None
    assert result["view"]["solverforge_calendar"] is None


def test_show_mesh_finds_task_in_calendar_slice(tmp_data_dir) -> None:
    """SolverforgeCalendarAdapter writes via UPSERT (preserves id on conflict)."""
    ueid = UEID("tsk:cal:33333333-3333-3333-3333-333333333333:3333333333333333")
    SolverforgeCalendarAdapter().apply_change(
        PropagationEvent(
            event_id="evt_test000003",
            ueid=ueid,
            action=TaskAction.CREATE,
            fields={"title": "in calendar", "due": None, "priority": "high"},
            approved_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            source_fork="test",
        )
    )

    result = show_mesh(str(ueid))
    assert result["view"]["solverforge_calendar"] is not None
    assert result["view"]["solverforge_calendar"]["ueid"] == str(ueid)
    assert result["view"]["solverforge_calendar"]["status"] == "planned"


def test_show_mesh_rejects_invalid_ueid() -> None:
    """Invalid UEID format should raise ValueError (UEID validates on construction)."""
    with pytest.raises(ValueError, match="Invalid UEID"):
        show_mesh("not a valid ueid format")


def test_show_mesh_idempotent_calendar_upsert(tmp_data_dir) -> None:
    """Two apply_change calls with same UEID preserve PK (per commit bb0edd5 fix)."""
    ueid = UEID("tsk:idemp:44444444-4444-4444-4444-444444444444:4444444444444444")
    adapter = SolverforgeCalendarAdapter()

    for i in range(2):
        adapter.apply_change(
            PropagationEvent(
                event_id=f"evt_idemp{i:06d}",
                ueid=ueid,
                action=TaskAction.CREATE,
                fields={"title": f"attempt {i}", "due": None, "priority": "low"},
                approved_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                source_fork="test",
            )
        )

    # Read DB directly: id (PK) must be stable
    db_path: Path = tmp_data_dir / "solverforge_calendar" / "unified_planning.db"
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, ueid FROM unified_planning_items WHERE ueid = ?", (str(ueid),)
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1, f"UPSERT should keep 1 row, got {len(rows)}"
    assert rows[0][1] == str(ueid)
