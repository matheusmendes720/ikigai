"""Integration smoke test — full Plan C lifecycle.

Covers: Investigation schema → queue enqueue → MCP tools → dispatcher → terminal.
Verifies the entire stack works end-to-end without spinning up the actual
MCP server (tools are called directly).
"""
from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.contracts.investigation import Investigation
from src.mesh.investigation_queue import (
    enqueue,
    get,
    transition,
)
from src.ikigai.src.mcp_server.investigation_enqueue import investigation_enqueue
from src.ikigai.src.mcp_server.investigation_status import investigation_status
from src.ikigai.src.mcp_server.investigation_complete import investigation_complete
from src.ikigai.src.agents.v2.workers.investigation_dispatcher import dispatch_once


@pytest.fixture
def fresh_queue(monkeypatch):
    """Redirect all queue operations to a temp directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        import src.mesh.investigation_queue as q
        monkeypatch.setattr(q, "QUEUE_DIR", tmp_path)
        monkeypatch.setattr(q, "audit_log_path", lambda: tmp_path / ".investigation_audit.log")
        yield tmp_path


def test_full_lifecycle_happy_path(fresh_queue):
    """Enqueue → status check → complete (resolved) — happy path."""
    # 1. Enqueue via MCP tool
    enqueue_result = investigation_enqueue(
        inq_id="inq-smoke-001",
        source="agent",
        payload="Investigate why daily_consolidator emits empty after plan rewrite",
        tags=("ready", "investigation"),
    )
    assert enqueue_result["status"] == "open"
    assert enqueue_result["inq_id"] == "inq-smoke-001"

    # 2. Status check
    status_result = investigation_status(inq_id="inq-smoke-001")
    assert status_result["status"] == "open"
    assert status_result["source"] == "agent"
    assert status_result["inq_ueid"] is None

    # 3. Crystallize (assign UEID via transition)
    transition(
        "inq-smoke-001",
        "in_progress",
        actor="user:mathe",
        inq_ueid="ikg:smoke:01:0001",
    )

    # 4. Complete via MCP tool
    complete_result = investigation_complete(
        "inq-smoke-001",
        final_status="resolved",
        actor="user:mathe",
        inq_ueid="ikg:smoke:01:0001",
    )
    assert complete_result["status"] == "resolved"
    assert complete_result["old_status"] == "in_progress"

    # 5. Final state
    final = get("inq-smoke-001")
    assert final.status == "resolved"
    assert final.inq_ueid == "ikg:smoke:01:0001"
    assert final.tags == ("ready", "investigation")


def test_full_lifecycle_dispatcher_picks_up_stale(fresh_queue):
    """Enqueue → wait → dispatcher archives stale."""
    # 1. Enqueue with old updated_at (simulate long-lived in_progress)
    old_inv = Investigation(
        inq_id="inq-smoke-stale",
        source="agent",
        payload="Long-running investigation that was forgotten",
        created_at=datetime.now() - timedelta(days=60),
        updated_at=datetime.now() - timedelta(days=60),
        status="in_progress",
    )
    enqueue(old_inv)

    # 2. Dispatcher runs
    summary = dispatch_once()
    assert summary["archived_stale"] == 1

    # 3. Verify archived
    final = get("inq-smoke-stale")
    assert final.status == "archived"


def test_full_lifecycle_dispatcher_resolves_crystallized(fresh_queue):
    """Enqueue with inq_ueid → dispatcher resolves."""
    inv = Investigation(
        inq_id="inq-smoke-crystal",
        source="agent",
        payload="Crystallized into the planning tree",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status="open",
        inq_ueid="ikg:crystal:01:0002",
    )
    enqueue(inv)

    summary = dispatch_once()
    assert summary["crystallized"] == 1
    assert get("inq-smoke-crystal").status == "resolved"


def test_full_lifecycle_summary_aggregates_correctly(fresh_queue):
    """Multiple investigations of mixed statuses → summary aggregates."""
    # 3 open
    for i in range(3):
        investigation_enqueue(
            inq_id=f"inq-summary-{i:03d}",
            source="agent",
            payload=f"investigation {i}",
        )

    # 1 in_progress (recent)
    investigation_enqueue(
        inq_id="inq-summary-active",
        source="agent",
        payload="active investigation",
    )
    transition("inq-summary-active", "in_progress", actor="user:mathe")

    summary = investigation_status()
    assert summary["total"] == 4
    assert summary["by_status"]["open"] == 3
    assert summary["by_status"]["in_progress"] == 1


def test_full_lifecycle_terminal_states_are_immutable(fresh_queue):
    """Once resolved/archived, no further transitions allowed."""
    investigation_enqueue(
        inq_id="inq-terminal",
        source="agent",
        payload="x",
    )
    investigation_complete("inq-terminal", final_status="resolved", actor="user:mathe")

    # Try to complete again
    result = investigation_complete("inq-terminal", final_status="archived", actor="user:mathe")
    assert result["error"] == "invalid_transition"

    # Try to transition directly
    with pytest.raises(ValueError, match="invalid transition"):
        transition("inq-terminal", "in_progress", "user:mathe")


def test_full_lifecycle_concurrent_enqueue_idempotent(fresh_queue):
    """Enqueueing the same inq_id overwrites (only edit allowed)."""
    inv1 = Investigation(
        inq_id="inq-idem",
        source="agent",
        payload="first version",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    enqueue(inv1)

    # Re-enqueue with different payload (the only 'edit' allowed)
    result = investigation_enqueue(
        inq_id="inq-idem",
        source="agent",
        payload="updated version",
    )
    assert result["status"] == "open"

    loaded = get("inq-idem")
    assert loaded.payload == "updated version"


def test_full_lifecycle_dispatcher_logs_all_transitions(fresh_queue, caplog):
    """Every dispatcher-driven transition is audit-logged."""
    import src.mesh.investigation_queue as q

    # 1 stale → archive
    enqueue(Investigation(
        inq_id="inq-log-stale",
        source="agent",
        payload="stale",
        created_at=datetime.now() - timedelta(days=60),
        updated_at=datetime.now() - timedelta(days=60),
        status="in_progress",
    ))

    # 1 crystallized → resolve
    enqueue(Investigation(
        inq_id="inq-log-crystal",
        source="agent",
        payload="crystal",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        inq_ueid="abc:def:0123:4567",
    ))

    with caplog.at_level(logging.INFO):
        dispatch_once()

    log_text = q.audit_log_path().read_text(encoding="utf-8")
    assert "inq-log-stale" in log_text
    assert "in_progress->archived" in log_text
    assert "inq-log-crystal" in log_text
    assert "open->resolved" in log_text
