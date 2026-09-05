"""Tests for investigation dispatcher — Plan C Task 5."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pytest

from contracts.investigation import Investigation
from agents.v2.workers.investigation_dispatcher import (
    STALE_THRESHOLD_DAYS,
    _has_crystallized,
    _is_stale,
    _should_emit_hint,
    dispatch_once,
)


@pytest.fixture
def tmp_queue(monkeypatch, tmp_path):
    """Redirect investigation queue dir to tmp_path."""
    import mesh.investigation_queue as q
    monkeypatch.setattr(q, "QUEUE_DIR", tmp_path)
    monkeypatch.setattr(q, "audit_log_path", lambda: tmp_path / ".investigation_audit.log")
    return tmp_path


def _make_inv(
    inq_id: str,
    status: str = "open",
    updated_at: datetime | None = None,
    tags: tuple[str, ...] = (),
    payload: str = "x",
    inq_ueid: str | None = None,
) -> Investigation:
    now = updated_at or datetime.now()
    return Investigation(
        inq_id=inq_id,
        source="agent",
        payload=payload,
        created_at=now,
        updated_at=now,
        status=status,  # type: ignore[arg-type]
        tags=tags,
        inq_ueid=inq_ueid,
    )


# ---------------------------------------------------------------------------
# Unit tests for pure helpers
# ---------------------------------------------------------------------------


def test_is_stale_returns_false_for_open():
    """open is never stale."""
    inv = _make_inv("inq-x", status="open")
    assert _is_stale(inv) is False


def test_is_stale_returns_false_for_recent_in_progress():
    """in_progress <STALE_THRESHOLD_DAYS old → not stale."""
    inv = _make_inv("inq-x", status="in_progress", updated_at=datetime.now())
    assert _is_stale(inv) is False


def test_is_stale_returns_true_for_old_in_progress():
    """in_progress >STALE_THRESHOLD_DAYS old → stale."""
    old = datetime.now() - timedelta(days=STALE_THRESHOLD_DAYS + 1)
    inv = _make_inv("inq-x", status="in_progress", updated_at=old)
    assert _is_stale(inv) is True


def test_has_crystallized_no_ueid():
    """No inq_ueid → not crystallized."""
    inv = _make_inv("inq-x", inq_ueid=None)
    assert _has_crystallized(inv) is False


def test_has_crystallized_with_ueid():
    """inq_ueid set → crystallized."""
    inv = _make_inv("inq-x", inq_ueid="abc:def:0123:4567")
    assert _has_crystallized(inv) is True


def test_should_emit_hint_no_tags():
    """No 'ready' tag → no hint."""
    inv = _make_inv("inq-x", tags=("research",), payload="x" * 100)
    assert _should_emit_hint(inv) is False


def test_should_emit_hint_short_payload():
    """'ready' tag but short payload → no hint."""
    inv = _make_inv("inq-x", tags=("ready",), payload="x")
    assert _should_emit_hint(inv) is False


def test_should_emit_hint_ready_tag_and_long_payload():
    """'ready' tag + long payload → hint."""
    inv = _make_inv("inq-x", tags=("ready",), payload="x" * 30)
    assert _should_emit_hint(inv) is True


# ---------------------------------------------------------------------------
# Integration: dispatch_once
# ---------------------------------------------------------------------------


def test_dispatch_once_empty_queue(tmp_queue):
    """Empty queue → all zeros."""
    summary = dispatch_once()
    assert summary["processed"] == 0
    assert summary["archived_stale"] == 0
    assert summary["crystallized"] == 0
    assert summary["hints_emitted"] == 0
    assert summary["errors"] == []


def test_dispatch_once_archives_stale(tmp_queue):
    """Stale in_progress → archived."""
    old = datetime.now() - timedelta(days=STALE_THRESHOLD_DAYS + 5)
    stale = _make_inv("inq-stale", status="in_progress", updated_at=old)
    # Persist
    from mesh.investigation_queue import enqueue
    enqueue(stale)

    summary = dispatch_once()
    assert summary["archived_stale"] == 1
    # Verify it's now archived
    from mesh.investigation_queue import get
    assert get("inq-stale").status == "archived"


def test_dispatch_once_resolves_crystallized(tmp_queue):
    """Crystallized → resolved."""
    crystallized = _make_inv("inq-crystal", inq_ueid="abc:def:0123:4567")
    from mesh.investigation_queue import enqueue
    enqueue(crystallized)

    summary = dispatch_once()
    assert summary["crystallized"] == 1
    from mesh.investigation_queue import get
    assert get("inq-crystal").status == "resolved"


def test_dispatch_once_emits_hint(tmp_queue):
    """Ready tag + long payload → hint emitted (no state change)."""
    ready_inv = _make_inv(
        "inq-ready",
        tags=("ready",),
        payload="x" * 50,
    )
    from mesh.investigation_queue import enqueue
    enqueue(ready_inv)

    summary = dispatch_once()
    assert summary["hints_emitted"] == 1
    # State unchanged
    from mesh.investigation_queue import get
    assert get("inq-ready").status == "open"


def test_dispatch_once_skips_terminal(tmp_queue):
    """Resolved/archived are NOT processed (already terminal)."""
    resolved = _make_inv("inq-done", status="resolved")
    from mesh.investigation_queue import enqueue
    enqueue(resolved)

    summary = dispatch_once()
    assert summary["processed"] == 0  # terminal skipped


def test_dispatch_once_logs_transitions(tmp_queue, caplog):
    """Stale + crystallized emit audit log entries."""
    import mesh.investigation_queue as q
    from mesh.investigation_queue import enqueue

    old = datetime.now() - timedelta(days=STALE_THRESHOLD_DAYS + 5)
    enqueue(_make_inv("inq-stale", status="in_progress", updated_at=old))
    enqueue(_make_inv("inq-crystal", inq_ueid="abc:def:0123:4567"))

    with caplog.at_level(logging.INFO):
        dispatch_once()

    log_text = q.audit_log_path().read_text(encoding="utf-8")
    assert "in_progress->archived" in log_text
    assert "open->resolved" in log_text or "open->resolved" in log_text.replace(" ", "")


def test_dispatch_once_handles_malformed_gracefully(tmp_queue):
    """Malformed JSON files don't crash the dispatcher."""
    # Write a malformed file
    (tmp_queue / "inq-bad.json").write_text("{ not valid json", encoding="utf-8")
    summary = dispatch_once()
    # Should complete without raising
    assert summary["processed"] == 0  # malformed skipped
    assert summary["errors"] == []  # malformed is silently skipped
