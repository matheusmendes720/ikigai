"""End-to-end integration test for create flow across all forks."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.contracts.task_change import TaskChange, TaskAction, PropagationEvent
from src.mesh import queue
from src.mesh.agent_consumer import validate, ValidationResult
from src.mesh.agent_propagator import propagate
from src.mesh.adapters.cli import CliAdapter
from src.mesh.adapters.taskdog import TaskdogAdapter
from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter
from src.contracts.common import UEID


@pytest.fixture
def isolated_data_dirs(tmp_path: Path, monkeypatch):
    """Set up isolated data dirs for CLI, taskdog, solverforge, queue."""
    cli_jsonl = tmp_path / "tasks.jsonl"
    taskdog_db = tmp_path / "tasks.db"
    upi_db = tmp_path / "upi.db"
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()

    # Patch paths
    from src.mesh.adapters import cli, taskdog, solverforge_calendar

    monkeypatch.setattr(cli, "TASKS_JSONL", cli_jsonl)
    monkeypatch.setattr(taskdog, "TASKDOG_DB", taskdog_db)
    monkeypatch.setattr(solverforge_calendar, "UPI_DB", upi_db)
    monkeypatch.setattr(queue, "QUEUE_DIR", queue_dir)

    # Initialize UPI schema (assumes v3 migration already applied)
    conn = sqlite3.connect(upi_db)
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

    return {
        "cli": cli_jsonl,
        "taskdog": taskdog_db,
        "solverforge": upi_db,
        "queue": queue_dir,
    }


def test_full_create_flow_propagates_to_all_forks(isolated_data_dirs):
    """End-to-end: write to cli -> queue -> agent validates -> propagates to all forks."""
    # Step 1: Simulate `life task add` — write to CLI + enqueue event
    ueid = "tsk:smoke-test:11111111-2222-3333-4444-555555555555:aaaaaaaaaaaaaaaa"
    event = TaskChange(
        event_id="evt_e2e_001",
        ueid=ueid,
        action=TaskAction.CREATE,
        fields={"title": "Smoke test task", "due": "2099-01-01", "priority": "high"},
        source_fork="interfaces/cli",
        timestamp=datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
    )

    # CLI writes its own slice
    cli_adapter = CliAdapter()
    cli_adapter.apply_change(PropagationEvent(
        event_id=event.event_id,
        ueid=event.ueid,
        action=event.action,
        fields=event.fields,
        approved_at=event.timestamp,
        source_fork=event.source_fork,
    ))

    # CLI enqueues event
    queue.enqueue(event)

    # Step 2: Agent consumes queue, validates
    pending_events = list(queue.consume_pending())
    assert len(pending_events) == 1
    assert pending_events[0].event_id == "evt_e2e_001"

    validation = validate(pending_events[0])
    assert validation.decision.value == "approve"

    # Step 3: Agent propagates to all forks
    adapters = [CliAdapter(), TaskdogAdapter(), SolverforgeCalendarAdapter()]
    results = propagate(pending_events[0], validation, adapters)

    assert len(results) == 3
    assert all(r.success for r in results), f"Failures: {[r for r in results if not r.success]}"

    # Step 4: Verify all forks have the task
    # CLI
    cli_lines = isolated_data_dirs["cli"].read_text().strip().split("\n")
    cli_tasks = [json.loads(line) for line in cli_lines if line]
    assert any(t["ueid"] == ueid for t in cli_tasks)

    # taskdog
    conn = sqlite3.connect(isolated_data_dirs["taskdog"])
    taskdog_count = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE ueid = ?", (ueid,)
    ).fetchone()[0]
    conn.close()
    assert taskdog_count == 1

    # solverforge UPI
    conn = sqlite3.connect(isolated_data_dirs["solverforge"])
    upi_count = conn.execute(
        "SELECT COUNT(*) FROM unified_planning_items WHERE ueid = ?", (ueid,)
    ).fetchone()[0]
    conn.close()
    assert upi_count == 1

    # Step 5: Verify queue event is acked
    queue.ack("evt_e2e_001", "propagated")
    pending_after = list(queue.consume_pending())
    assert len(pending_after) == 0
