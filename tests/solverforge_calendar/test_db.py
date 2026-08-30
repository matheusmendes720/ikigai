"""Tests for solverforge_calendar SQLite manager (UPI table wrapper)."""

from __future__ import annotations
from datetime import datetime
from pathlib import Path

from src.solverforge_calendar.db import SolverforgeDB


# Valid UEIDs matching src/contracts/common.py: type:slug:uuid:hash
# Third group must be hex [a-f0-9-], so use UUID format
_UEID_VALID = "sc:task:abc12345-1234-5678-9abc-def012345678:def4567890123456"
_UEID_A = "sc:task:a0b1c2d3-e4f5-6789-abcd-ef0123456789:aaaa1111bbbb2222"
_UEID_B = "sc:task:b0c1d2e3-f4a5-6789-babc-def0123456789:bbbb2222cccc3333"
_UEID_MISSING = "sc:task:missing-ueid-0000-0000-000000000000:0000000000000000"


def test_upsert_creates_row(tmp_path: Path):
    db = SolverforgeDB(tmp_path / "upi.db")
    db.upsert(
        ueid=_UEID_VALID,
        title="BYD research",
        start_at=datetime(2026, 9, 1, 9, 0, 0),
        end_at=datetime(2026, 9, 1, 11, 0, 0),
    )
    row = db.read(_UEID_VALID)
    assert row is not None
    assert row["title"] == "BYD research"
    assert row["status"] == "scheduled"


def test_upsert_updates_existing(tmp_path: Path):
    db = SolverforgeDB(tmp_path / "upi.db")
    db.upsert(
        ueid=_UEID_A, title="Old", start_at=datetime(2026, 9, 1, 9, 0, 0), end_at=None
    )
    db.upsert(
        ueid=_UEID_A, title="New", start_at=datetime(2026, 9, 1, 10, 0, 0), end_at=None
    )
    row = db.read(_UEID_A)
    assert row["title"] == "New"  # updated, not duplicated


def test_read_returns_none_for_missing(tmp_path: Path):
    db = SolverforgeDB(tmp_path / "upi.db")
    assert db.read(_UEID_MISSING) is None


def test_list_busy_in_window(tmp_path: Path):
    db = SolverforgeDB(tmp_path / "upi.db")
    db.upsert(
        ueid=_UEID_A,
        title="A",
        start_at=datetime(2026, 9, 1, 9, 0, 0),
        end_at=datetime(2026, 9, 1, 10, 0, 0),
    )
    db.upsert(
        ueid=_UEID_B,
        title="B",
        start_at=datetime(2026, 9, 1, 14, 0, 0),
        end_at=datetime(2026, 9, 1, 15, 0, 0),
    )
    busy = db.list_busy_in_window(
        start=datetime(2026, 9, 1, 0, 0, 0),
        end=datetime(2026, 9, 1, 23, 59, 59),
    )
    assert len(busy) == 2
