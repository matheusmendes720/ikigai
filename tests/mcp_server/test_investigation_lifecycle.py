"""E2E tests for investigation queue MCP tools — Plan C Task 3."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

# Import tool functions (NOT the @MCP.tool wrappers — those require server boot)
from src.ikigai.src.mcp_server.investigation_enqueue import investigation_enqueue
from src.ikigai.src.mcp_server.investigation_status import investigation_status
from src.ikigai.src.mcp_server.investigation_complete import investigation_complete


@pytest.fixture
def tmp_queue(monkeypatch):
    """Redirect investigation queue dir to a temp directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        import mesh.investigation_queue as q
        monkeypatch.setattr(q, "QUEUE_DIR", tmp_path)
        # Patch the audit log path too
        monkeypatch.setattr(q, "audit_log_path", lambda: tmp_path / ".investigation_audit.log")
        yield tmp_path


def test_enqueue_creates_investigation(tmp_queue):
    """investigation_enqueue creates a new record and returns path."""
    result = investigation_enqueue(
        inq_id="inq-20260905-001",
        source="agent",
        payload="Raw CSV observation — needs DECISION",
        tags=("research",),
    )
    assert "inq_id" in result
    assert result["inq_id"] == "inq-20260905-001"
    assert result["status"] == "open"
    assert Path(result["path"]).exists()


def test_enqueue_validation_error(tmp_queue):
    """investigation_enqueue returns error dict on validation failure."""
    result = investigation_enqueue(
        inq_id="bad",
        source="robot",  # invalid source
        payload="x",
    )
    assert result["error"] == "validation_failed"


def test_status_one(tmp_queue):
    """investigation_status returns one investigation's details."""
    investigation_enqueue(
        inq_id="inq-20260905-001",
        source="agent",
        payload="x",
    )
    result = investigation_status(inq_id="inq-20260905-001")
    assert result["status"] == "open"
    assert result["source"] == "agent"


def test_status_summary(tmp_queue):
    """investigation_status with no inq_id returns counts by status."""
    investigation_enqueue(inq_id="inq-20260905-001", source="agent", payload="x")
    investigation_enqueue(inq_id="inq-20260905-002", source="user", payload="y")
    result = investigation_status()
    assert result["total"] == 2
    assert result["by_status"]["open"] == 2


def test_status_not_found(tmp_queue):
    """investigation_status returns error for missing inq_id."""
    result = investigation_status(inq_id="inq-missing")
    assert result["error"] == "not_found"


def test_complete_resolved(tmp_queue):
    """investigation_complete marks resolved."""
    investigation_enqueue(inq_id="inq-20260905-001", source="agent", payload="x")
    # First transition to in_progress, then to resolved (open -> in_progress -> resolved)
    investigation_complete("inq-20260905-001", final_status="in_progress", actor="user:mathe")
    result = investigation_complete("inq-20260905-001", final_status="resolved", actor="user:mathe")
    assert result["status"] == "resolved"
    assert result["old_status"] == "in_progress"


def test_complete_archived(tmp_queue):
    """investigation_complete marks archived."""
    investigation_enqueue(inq_id="inq-20260905-001", source="agent", payload="x")
    result = investigation_complete("inq-20260905-001", final_status="archived", actor="user:mathe")
    assert result["status"] == "archived"


def test_complete_invalid_terminal_state(tmp_queue):
    """investigation_complete rejects final_status='open' (not terminal)."""
    investigation_enqueue(inq_id="inq-20260905-001", source="agent", payload="x")
    result = investigation_complete("inq-20260905-001", final_status="open", actor="user:mathe")
    assert result["error"] == "invalid_terminal_state"


def test_complete_not_found(tmp_queue):
    """investigation_complete returns error for missing inq_id."""
    result = investigation_complete("inq-missing", final_status="resolved", actor="user:mathe")
    assert result["error"] == "not_found"


def test_complete_after_resolved_rejected(tmp_queue):
    """Resolved -> anything is rejected (terminal)."""
    investigation_enqueue(inq_id="inq-20260905-001", source="agent", payload="x")
    # First go to in_progress, then to resolved (terminal)
    investigation_complete("inq-20260905-001", final_status="in_progress", actor="user:mathe")
    investigation_complete("inq-20260905-001", final_status="resolved", actor="user:mathe")
    # Try to transition again - should fail because resolved is terminal
    result = investigation_complete("inq-20260905-001", final_status="archived", actor="user:mathe")
    assert result["error"] == "invalid_transition"
