"""End-to-end smoke tests for the review queue worker pipeline.

These tests exercise the FULL chain:
    enqueue TaskChange → worker.run_once() → validate → propagate →
    adapter.apply_change called → queue.ack updates status.

Mirrors B3.7's "final verification + spec self-review" pattern: ensure the
B4 deliverable works end-to-end, not just at the unit-test level.

Uses the real `data/review_queue/` dir for the queue (test fixtures write
into and clean out of this dir under stable event_ids) and a temp
TASKS_JSONL for the CliAdapter write so production data is not polluted.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import sqlite3
import uuid

from src.contracts.common import UEID
from src.contracts.task_change import PropagationEvent, TaskAction, TaskChange, TaskStatus
from src.mesh import queue as queue_mod
from src.mesh import review_queue_worker as worker_mod


# === Stub adapter (Protocol-conformant) ===

@dataclass
class StubAdapter:
    """Captures PropagationEvents for assertion. Raises on demand."""
    name: str = "stub"
    raise_on_apply: bool = False
    captured: list[PropagationEvent] = field(default_factory=list)

    def read(self, ueid: UEID) -> dict[str, Any] | None:
        return None

    def apply_change(self, event: PropagationEvent) -> None:
        if self.raise_on_apply:
            raise RuntimeError("stub adapter forced failure")
        self.captured.append(event)

    def supports_field(self, field_name: str) -> bool:
        return True


# === Helpers ===

def _make_event(
    event_id: str = "test-evt-001",
    ueid: UEID = "tsk:abc:a1b2:c3d4",
    title: str = "Build the thing",
    due: str | None = None,
    source_fork: str = "cli",
) -> TaskChange:
    if due is None:
        # Default to 30 days in the future so validation passes
        due = (datetime.now() + timedelta(days=30)).date().isoformat()
    return TaskChange(
        event_id=event_id,
        ueid=ueid,  # type: ignore[arg-type]
        action=TaskAction.CREATE,
        fields={"title": title, "due": due, "priority": "high"},
        source_fork=source_fork,
        timestamp=datetime.now(),
        status="pending",
    )


def _read_status(event_id: str) -> TaskStatus | None:
    """Read back the status from the queue file directly."""
    path = queue_mod.QUEUE_DIR / f"{event_id}.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    return raw.get("status")


def _cleanup(event_id: str) -> None:
    """Remove test event file from queue dir (test isolation)."""
    path = queue_mod.QUEUE_DIR / f"{event_id}.json"
    if path.exists():
        path.unlink()


# === Tests ===

def test_end_to_end_approved_propagates_to_adapter() -> None:
    """Happy path: enqueue valid event → adapter receives PropagationEvent → status='propagated'."""
    event = _make_event(event_id="e2e-happy-001", title="Ship the B4 deliverable")
    queue_mod.enqueue(event)

    try:
        adapter = StubAdapter(name="stub-happy")
        result = worker_mod.run_once([adapter])

        assert result.consumed == 1
        assert result.approved == 1
        assert result.rejected == 0
        assert result.clarified == 0
        assert result.partial == 0

        # Adapter was called exactly once with a PropagationEvent
        assert len(adapter.captured) == 1
        prop = adapter.captured[0]
        assert prop.event_id == "e2e-happy-001"
        assert prop.ueid == event.ueid
        assert prop.action == TaskAction.CREATE
        assert prop.fields.get("title") == "Ship the B4 deliverable"

        # Queue file was acked to 'propagated'
        assert _read_status("e2e-happy-001") == "propagated"
    finally:
        _cleanup("e2e-happy-001")


def test_end_to_end_rejected_does_not_call_adapter() -> None:
    """Validation REJECT path: past due date → adapter never called → status='rejected'."""
    event = _make_event(
        event_id="e2e-rejected-001",
        title="Past-due task",
        due="2020-01-01",  # in the past → REJECT
    )
    queue_mod.enqueue(event)

    try:
        adapter = StubAdapter(name="stub-rejected")
        result = worker_mod.run_once([adapter])

        assert result.consumed == 1
        assert result.approved == 0
        assert result.rejected == 1
        assert adapter.captured == []
        assert _read_status("e2e-rejected-001") == "rejected"
    finally:
        _cleanup("e2e-rejected-001")


def test_end_to_end_clarified_does_not_call_adapter() -> None:
    """Validation CLARIFY path: vague title "todo" → status='clarified'."""
    event = _make_event(
        event_id="e2e-clarify-001",
        title="todo",  # vague → CLARIFY
    )
    queue_mod.enqueue(event)

    try:
        adapter = StubAdapter(name="stub-clarify")
        result = worker_mod.run_once([adapter])

        assert result.consumed == 1
        assert result.clarified == 1
        assert adapter.captured == []
        assert _read_status("e2e-clarify-001") == "clarified"
    finally:
        _cleanup("e2e-clarify-001")


def test_end_to_end_partial_propagation_acks_partial() -> None:
    """One adapter fails, one succeeds → status='partial_propagation', partial=1."""
    event = _make_event(event_id="e2e-partial-001", title="Multi-fork task")
    queue_mod.enqueue(event)

    try:
        ok_adapter = StubAdapter(name="ok")
        fail_adapter = StubAdapter(name="fail", raise_on_apply=True)
        result = worker_mod.run_once([ok_adapter, fail_adapter])

        assert result.consumed == 1
        assert result.approved == 1
        assert result.partial == 1
        # OK adapter received the event
        assert len(ok_adapter.captured) == 1
        # Fail adapter did not capture (raised)
        assert fail_adapter.captured == []
        # Queue marked as partial_propagation (propagator handles the ack)
        assert _read_status("e2e-partial-001") == "partial_propagation"
    finally:
        _cleanup("e2e-partial-001")


def test_end_to_end_idempotent_run_once() -> None:
    """Calling run_once twice does not re-process already-acked events."""
    event = _make_event(event_id="e2e-idem-001", title="Idempotency check")
    queue_mod.enqueue(event)

    try:
        adapter = StubAdapter(name="idem")
        first = worker_mod.run_once([adapter])
        second = worker_mod.run_once([adapter])

        assert first.consumed == 1
        assert second.consumed == 0  # already acked, consume_pending skips it
        assert len(adapter.captured) == 1
    finally:
        _cleanup("e2e-idem-001")


def test_end_to_end_with_cli_adapter_writes_real_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real CliAdapter: validates that worker.run_once → CLI TASKS_JSONL write."""
    # Redirect CliAdapter's TASKS_JSONL to a temp file
    import src.mesh.adapters.cli as cli_adapter_mod

    temp_jsonl = tmp_path / "tasks.jsonl"
    monkeypatch.setattr(cli_adapter_mod, "TASKS_JSONL", temp_jsonl)

    event = _make_event(
        event_id="e2e-cli-001",
        ueid="tsk:cli:a1b2:c3d4",
        title="Real CLI write test",
        source_fork="mcp_gateway",
    )
    queue_mod.enqueue(event)

    try:
        from src.mesh.adapters.cli import CliAdapter

        adapter = CliAdapter()
        result = worker_mod.run_once([adapter])

        assert result.consumed == 1
        assert result.approved == 1
        # Real file was written by CliAdapter.apply_change
        assert temp_jsonl.exists()
        lines = temp_jsonl.read_text().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["ueid"] == "tsk:cli:a1b2:c3d4"
        assert record["title"] == "Real CLI write test"
        assert record["source_fork"] == "mcp_gateway"
        assert _read_status("e2e-cli-001") == "propagated"
    finally:
        _cleanup("e2e-cli-001")


def test_end_to_end_with_taskdog_adapter_writes_real_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real TaskdogAdapter: validates worker.run_once → SQLite UPSERT into tasks table."""
    # Redirect TaskdogAdapter's TASKDOG_DB to a temp dir
    import src.mesh.adapters.taskdog as taskdog_adapter_mod

    temp_db = tmp_path / "taskdog.db"
    monkeypatch.setattr(taskdog_adapter_mod, "TASKDOG_DB", temp_db)

    event = _make_event(
        event_id="e2e-taskdog-001",
        ueid="tsk:taskdog:b1c2:d3e4",
        title="Real taskdog UPSERT test",
        source_fork="mcp_gateway",
    )
    queue_mod.enqueue(event)

    try:
        from src.mesh.adapters.taskdog import TaskdogAdapter

        adapter = TaskdogAdapter()
        result = worker_mod.run_once([adapter])

        assert result.consumed == 1
        assert result.approved == 1
        assert result.partial == 0

        # Real DB was written by TaskdogAdapter.apply_change
        assert temp_db.exists()
        conn = sqlite3.connect(temp_db)
        try:
            row = conn.execute(
                "SELECT ueid, name, status, priority, deadline FROM tasks WHERE ueid = ?",
                (event.ueid,),
            ).fetchone()
            assert row is not None, "TaskdogAdapter did not UPSERT the row"
            assert row[0] == "tsk:taskdog:b1c2:d3e4"
            assert row[1] == "Real taskdog UPSERT test"
            assert row[2] == "planned"
            assert row[3] == 1  # high priority
            # deadline is due date (string)
            assert row[4] is not None
        finally:
            conn.close()
        assert _read_status("e2e-taskdog-001") == "propagated"
    finally:
        _cleanup("e2e-taskdog-001")


def test_end_to_end_with_solverforge_calendar_adapter_writes_real_upi(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real SolverforgeCalendarAdapter: validates worker.run_once → UPI write with id reuse."""
    # Redirect SolverforgeCalendarAdapter's UPI_DB to a temp dir
    import src.mesh.adapters.solverforge_calendar as upi_adapter_mod

    temp_db = tmp_path / "upi.db"
    monkeypatch.setattr(upi_adapter_mod, "UPI_DB", temp_db)

    event = _make_event(
        event_id="e2e-upi-001",
        ueid="tsk:upi:b1c2:d3e4",
        title="Real UPI write test",
        source_fork="mcp_gateway",
    )
    queue_mod.enqueue(event)

    try:
        from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter

        adapter = SolverforgeCalendarAdapter()
        result = worker_mod.run_once([adapter])

        assert result.consumed == 1
        assert result.approved == 1
        assert result.partial == 0

        # Real DB was written by SolverforgeCalendarAdapter.apply_change
        assert temp_db.exists()
        conn = sqlite3.connect(temp_db)
        try:
            row = conn.execute(
                "SELECT id, ueid, status, ikigai FROM unified_planning_items WHERE ueid = ?",
                (event.ueid,),
            ).fetchone()
            assert row is not None, "SolverforgeCalendarAdapter did not write the row"
            pk_id, ueid_val, status_val, ikigai_json = row
            assert ueid_val == "tsk:upi:b1c2:d3e4"
            assert status_val == "planned"
            # id is a UUID string (TEXT PRIMARY KEY)
            assert isinstance(pk_id, str) and len(pk_id) > 0

            # ikigai column is JSON with the expected fields
            ikigai = json.loads(ikigai_json)
            assert ikigai["title"] == "Real UPI write test"
            assert ikigai["source_fork"] == "mcp_gateway"
            assert ikigai["due"] is not None  # 30 days from now (set in _make_event)
            assert "approved_at" in ikigai
        finally:
            conn.close()
        assert _read_status("e2e-upi-001") == "propagated"
    finally:
        _cleanup("e2e-upi-001")
