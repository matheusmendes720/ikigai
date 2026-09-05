"""Tests for investigation queue helpers — Plan C Task 2."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from contracts.investigation import Investigation
from mesh.investigation_queue import (
    audit_log_path,
    enqueue,
    get,
    list_all,
    list_by_status,
    log_transition,
    transition,
    _investigation_path,
)


@pytest.fixture
def tmp_queue_dir(tmp_path, monkeypatch):
    """Redirect QUEUE_DIR to tmp_path for test isolation."""
    monkeypatch.setattr("mesh.investigation_queue.QUEUE_DIR", tmp_path)
    # Re-bind the local QUEUE_DIR references in functions that capture it
    monkeypatch.setattr("mesh.investigation_queue.ensure_queue_dir",
                        lambda: _ensure(tmp_path))
    return tmp_path


def _ensure(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _make_inv(inq_id: str, status: str = "open") -> Investigation:
    return Investigation(
        inq_id=inq_id,
        source="agent",
        payload=f"test payload {inq_id}",
        created_at=datetime.now(),
        status=status,  # type: ignore[arg-type]
    )


def test_enqueue_creates_file(tmp_queue_dir):
    """enqueue writes JSON atomically."""
    inv = _make_inv("inq-20260905-001")
    path = enqueue(inv)
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["inq_id"] == "inq-20260905-001"
    assert loaded["status"] == "open"


def test_enqueue_is_idempotent_on_inq_id(tmp_queue_dir):
    """enqueue overwrites existing file with same inq_id (only edit allowed)."""
    inv1 = _make_inv("inq-20260905-001")
    enqueue(inv1)
    inv2 = inv1.model_copy(update={"payload": "updated payload"})
    enqueue(inv2)
    loaded = get("inq-20260905-001")
    assert loaded.payload == "updated payload"


def test_transition_open_to_in_progress(tmp_queue_dir):
    """Valid transition: open → in_progress."""
    enqueue(_make_inv("inq-20260905-001"))
    updated = transition("inq-20260905-001", "in_progress", "user:mathe")
    assert updated.status == "in_progress"
    assert updated.actor == "user:mathe"


def test_transition_terminal_rejected(tmp_queue_dir):
    """Terminal states (resolved, archived) cannot transition further."""
    enqueue(_make_inv("inq-20260905-001", status="resolved"))
    with pytest.raises(ValueError, match="invalid transition"):
        transition("inq-20260905-001", "open", "user:mathe")


def test_transition_resolved_to_archived_rejected(tmp_queue_dir):
    """resolved → archived is NOT allowed (both terminal)."""
    enqueue(_make_inv("inq-20260905-001", status="resolved"))
    with pytest.raises(ValueError, match="invalid transition"):
        transition("inq-20260905-001", "archived", "user:mathe")


def test_transition_in_progress_to_open_allowed(tmp_queue_dir):
    """in_progress → open is allowed (false alarm recovery)."""
    enqueue(_make_inv("inq-20260905-001", status="in_progress"))
    updated = transition("inq-20260905-001", "open", "user:mathe")
    assert updated.status == "open"


def test_transition_not_found(tmp_queue_dir):
    """transition raises KeyError if investigation missing."""
    with pytest.raises(KeyError):
        transition("inq-doesnotexist", "in_progress", "user:mathe")


def test_get_missing_raises_keyerror(tmp_queue_dir):
    """get raises KeyError for missing investigation."""
    with pytest.raises(KeyError):
        get("inq-doesnotexist")


def test_list_all_sorted_by_inq_id(tmp_queue_dir):
    """list_all returns investigations sorted by inq_id."""
    enqueue(_make_inv("inq-20260905-003"))
    enqueue(_make_inv("inq-20260905-001"))
    enqueue(_make_inv("inq-20260905-002"))
    all_inv = list_all()
    assert [i.inq_id for i in all_inv] == [
        "inq-20260905-001",
        "inq-20260905-002",
        "inq-20260905-003",
    ]


def test_list_by_status_filter(tmp_queue_dir):
    """list_by_status filters correctly."""
    enqueue(_make_inv("inq-20260905-001", status="open"))
    enqueue(_make_inv("inq-20260905-002", status="in_progress"))
    enqueue(_make_inv("inq-20260905-003", status="resolved"))
    assert len(list_by_status("open")) == 1
    assert len(list_by_status("in_progress")) == 1
    assert len(list_by_status("resolved")) == 1


def test_invalid_inq_id_path_traversal_rejected(tmp_queue_dir):
    """_investigation_path rejects path traversal attempts in inq_id."""
    with pytest.raises(ValueError):
        _investigation_path("../etc/passwd")
    with pytest.raises(ValueError):
        _investigation_path("inq-../../../bad")


def test_audit_log_appends(tmp_queue_dir):
    """log_transition appends to audit log."""
    enqueue(_make_inv("inq-20260905-001"))
    log_transition("inq-20260905-001", "open", "in_progress", "user:mathe")
    log_transition("inq-20260905-001", "in_progress", "resolved", "user:mathe")
    log_text = audit_log_path().read_text(encoding="utf-8")
    assert "open->in_progress" in log_text
    assert "in_progress->resolved" in log_text
    assert log_text.count("\n") == 2


def test_atomic_write_no_tmp_files_left(tmp_queue_dir):
    """After enqueue, no .tmp.* files remain in QUEUE_DIR."""
    enqueue(_make_inv("inq-20260905-001"))
    tmp_files = list(tmp_queue_dir.glob("*.tmp.*"))
    assert tmp_files == []
