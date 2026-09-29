"""Tests for M162 — cadence helpers (daily/weekly/monthly/quarterly)."""
from __future__ import annotations

from datetime import date

import pytest

from agents.v2.skills import cadence


# ---------------------------------------------------------------------------
# date helpers
# ---------------------------------------------------------------------------


def test_daily_path_format():
    """daily_path produces vault/daily/YYYY-MM-DD.md."""
    p = cadence.daily_path(date(2026, 9, 29))
    assert p.as_posix() == "vault/daily/2026-09-29.md"


def test_weekly_path_iso_format():
    """weekly_path produces vault/weekly/YYYY-Www.md (ISO week)."""
    p = cadence.weekly_path(date(2026, 9, 29))
    assert "2026-W" in p.as_posix()
    assert p.as_posix().endswith(".md")


def test_monthly_path_format():
    """monthly_path produces vault/monthly/YYYY-MM.md."""
    p = cadence.monthly_path(date(2026, 9, 29))
    assert p.as_posix() == "vault/monthly/2026-09.md"


def test_quarterly_path_format():
    """quarterly_path produces vault/quarterly/YYYY-Qn.md."""
    p1 = cadence.quarterly_path(date(2026, 1, 15))
    p2 = cadence.quarterly_path(date(2026, 4, 1))
    p3 = cadence.quarterly_path(date(2026, 7, 1))
    p4 = cadence.quarterly_path(date(2026, 10, 1))
    assert "2026-Q1" in p1.as_posix()
    assert "2026-Q2" in p2.as_posix()
    assert "2026-Q3" in p3.as_posix()
    assert "2026-Q4" in p4.as_posix()


# ---------------------------------------------------------------------------
# window heuristics
# ---------------------------------------------------------------------------


def test_was_done_in_window_true():
    """Task done with created_at in window returns True."""
    today = date(2026, 9, 29)
    task = {"status": "done", "created_at": "2026-09-28"}
    assert cadence.was_done_in_window(task, date(2026, 9, 22), today) is True


def test_was_done_in_window_false_status():
    """Task with status != done returns False even if in window."""
    today = date(2026, 9, 29)
    task = {"status": "planned", "created_at": "2026-09-28"}
    assert cadence.was_done_in_window(task, date(2026, 9, 22), today) is False


def test_was_done_in_window_no_created_at():
    """Task with no created_at but status=done → True (best-effort)."""
    today = date(2026, 9, 29)
    task = {"status": "done"}
    assert cadence.was_done_in_window(task, date(2026, 9, 22), today) is True


def test_was_created_in_window_true():
    """Task created in window returns True."""
    today = date(2026, 9, 29)
    task = {"created_at": "2026-09-25"}
    assert cadence.was_created_in_window(task, date(2026, 9, 22), today) is True


def test_was_created_in_window_no_date():
    """Task without created_at → False (no info)."""
    task = {}
    assert cadence.was_created_in_window(task, date(2026, 9, 22), date(2026, 9, 29)) is False


# ---------------------------------------------------------------------------
# vault helpers
# ---------------------------------------------------------------------------


def test_read_vault_note_missing_returns_empty(tmp_path):
    """read_vault_note on missing file returns empty string."""
    assert cadence.read_vault_note(tmp_path / "nope.md") == ""


def test_read_vault_note_existing(tmp_path):
    """read_vault_note reads existing file content."""
    p = tmp_path / "note.md"
    p.write_text("hello", encoding="utf-8")
    assert cadence.read_vault_note(p) == "hello"


def test_list_vault_notes_in_range_empty(tmp_path):
    """list_vault_notes_in_range with no matching files returns []."""
    out = cadence.list_vault_notes_in_range(
        lambda d: tmp_path / f"{d.isoformat()}.md",
        date(2026, 9, 22),
        date(2026, 9, 29),
    )
    assert out == []


def test_list_vault_notes_in_range_finds_some(tmp_path):
    """list_vault_notes_in_range finds existing files in window."""
    # Create 3 files in the window
    for d in [22, 24, 28]:
        (tmp_path / f"2026-09-{d:02d}.md").write_text(f"day {d}", encoding="utf-8")
    out = cadence.list_vault_notes_in_range(
        lambda d: tmp_path / f"{d.isoformat()}.md",
        date(2026, 9, 22),
        date(2026, 9, 29),
    )
    assert len(out) == 3


# ---------------------------------------------------------------------------
# render helpers
# ---------------------------------------------------------------------------


def test_render_weekly_review_includes_required_sections():
    """render_weekly_review has Stats, Daily Reports, Tasks sections."""
    md = cadence.render_weekly_review(
        today=date(2026, 9, 29),
        daily_reports=[],
        done_tasks=[],
        created_tasks=[],
    )
    assert "## Stats" in md
    assert "## Daily Reports" in md
    assert "## Tasks completed this week" in md
    assert "## Tasks created this week" in md


def test_render_weekly_review_handles_no_data():
    """render_weekly_review with no data has graceful placeholders."""
    md = cadence.render_weekly_review(
        today=date(2026, 9, 29),
        daily_reports=[],
        done_tasks=[],
        created_tasks=[],
    )
    assert "_No daily reports found" in md
    assert "_None._" in md


def test_render_monthly_review_includes_summary():
    """render_monthly_review has Summary section."""
    md = cadence.render_monthly_review(
        today=date(2026, 9, 29), weekly_reviews=[]
    )
    assert "## Summary" in md
    assert "Weekly reviews: 0" in md


def test_render_quarterly_review_includes_cadence_summary():
    """render_quarterly_review has cadence summary."""
    md = cadence.render_quarterly_review(
        today=date(2026, 9, 29),
        monthly_reviews=[],
        weekly_reviews=[],
    )
    assert "## Cadence summary" in md
    assert "Monthly reviews aggregated: 0" in md


def test_extract_okrs_from_review_with_checkboxes():
    """extract_okrs_from_review picks up '- [ ]' lines."""
    md = """
# Goal: ship M162
- [ ] Cadence helpers
- [ ] 4 skills modules
- [ ] Tests
"""
    okrs = cadence.extract_okrs_from_review(md)
    titles = [o["title"] for o in okrs]
    assert "ship M162" in titles
    assert "Cadence helpers" in titles
    assert "Tests" in titles


def test_extract_okrs_from_review_empty():
    """Empty review → empty okrs list."""
    assert cadence.extract_okrs_from_review("") == []
    assert cadence.extract_okrs_from_review("# Just a heading") == []
