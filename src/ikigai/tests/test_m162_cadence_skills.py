"""Tests for M162 — 4 cadence skills (daily/weekly/monthly/quarterly)."""
from __future__ import annotations

from datetime import date

import pytest

from agents.v2.skills import (
    ikigai_daily,
    ikigai_weekly,
    ikigai_monthly,
    ikigai_quarterly,
)


# ---------------------------------------------------------------------------
# ikigai-daily
# ---------------------------------------------------------------------------


def test_daily_propose_returns_readonly_proposal():
    """Daily skill emits a Proposal with empty changes (read-only)."""
    p = ikigai_daily.propose(today=date(2026, 9, 29))
    assert p.skill == "ikigai-daily"
    assert p.changes == []
    assert p.approval_state == "pending"


def test_daily_propose_includes_suggestions_in_metadata():
    """Daily Proposal has suggestions in metadata."""
    p = ikigai_daily.propose(today=date(2026, 9, 29))
    suggestions = p.metadata.get("suggestions")  # type: ignore[attr-defined]
    assert isinstance(suggestions, list)


def test_daily_propose_includes_stats_in_metadata():
    """Daily Proposal has stats in metadata."""
    p = ikigai_daily.propose(today=date(2026, 9, 29))
    stats = p.metadata.get("stats")  # type: ignore[attr-defined]
    assert "done_24h" in stats
    assert "pending" in stats
    assert "cancelled" in stats


def test_daily_run_skill_matches_propose():
    """run_skill is a thin wrapper around propose."""
    p1 = ikigai_daily.run_skill(today=date(2026, 9, 29))
    p2 = ikigai_daily.propose(today=date(2026, 9, 29))
    assert p1.skill == p2.skill
    assert p1.changes == p2.changes


# ---------------------------------------------------------------------------
# ikigai-weekly
# ---------------------------------------------------------------------------


def test_weekly_propose_emits_one_write_file_change():
    """Weekly emits 1 WRITE_FILE change to vault/weekly/."""
    p = ikigai_weekly.propose(today=date(2026, 9, 29))
    assert len(p.changes) == 1
    change = p.changes[0]
    assert change["action"] == "WRITE_FILE"
    assert "weekly" in change["fields"]["path"]
    assert "## Stats" in change["fields"]["content"]


def test_weekly_propose_approval_pending():
    """Weekly Proposal requires user approval."""
    p = ikigai_weekly.propose(today=date(2026, 9, 29))
    assert p.approval_state == "pending"
    assert p.skill == "ikigai-weekly"


def test_weekly_propose_path_uses_iso_week():
    """Weekly path uses ISO week format."""
    p = ikigai_weekly.propose(today=date(2026, 9, 29))
    path = p.changes[0]["fields"]["path"]
    assert "2026-W40" in path  # 2026-09-29 is ISO week 40


# ---------------------------------------------------------------------------
# ikigai-monthly
# ---------------------------------------------------------------------------


def test_monthly_propose_emits_write_file():
    """Monthly emits 1 WRITE_FILE change to vault/monthly/."""
    p = ikigai_monthly.propose(today=date(2026, 9, 29))
    assert len(p.changes) == 1
    change = p.changes[0]
    assert change["action"] == "WRITE_FILE"
    assert "monthly" in change["fields"]["path"]
    assert "2026-09" in change["fields"]["path"]


def test_monthly_propose_approval_pending():
    """Monthly Proposal requires user approval."""
    p = ikigai_monthly.propose(today=date(2026, 9, 29))
    assert p.approval_state == "pending"
    assert p.skill == "ikigai-monthly"


# ---------------------------------------------------------------------------
# ikigai-quarterly
# ---------------------------------------------------------------------------


def test_quarterly_propose_emits_write_file():
    """Quarterly emits at least 1 WRITE_FILE change."""
    p = ikigai_quarterly.propose(today=date(2026, 9, 29))
    assert len(p.changes) >= 1
    first = p.changes[0]
    assert first["action"] == "WRITE_FILE"
    assert "quarterly" in first["fields"]["path"]
    assert "2026-Q3" in first["fields"]["path"]


def test_quarterly_path_uses_correct_quarter():
    """Quarterly path uses the right quarter based on month."""
    p1 = ikigai_quarterly.propose(today=date(2026, 1, 15))
    p2 = ikigai_quarterly.propose(today=date(2026, 4, 1))
    p3 = ikigai_quarterly.propose(today=date(2026, 7, 1))
    p4 = ikigai_quarterly.propose(today=date(2026, 10, 1))
    assert "Q1" in p1.changes[0]["fields"]["path"]
    assert "Q2" in p2.changes[0]["fields"]["path"]
    assert "Q3" in p3.changes[0]["fields"]["path"]
    assert "Q4" in p4.changes[0]["fields"]["path"]


def test_quarterly_propose_approval_pending():
    """Quarterly Proposal requires user approval."""
    p = ikigai_quarterly.propose(today=date(2026, 9, 29))
    assert p.approval_state == "pending"
    assert p.skill == "ikigai-quarterly"


def test_quarterly_propose_with_no_okrs_has_only_write():
    """Quarterly with no OKRs in review → only 1 change (WRITE_FILE)."""
    p = ikigai_quarterly.propose(today=date(2026, 9, 29))
    # Without mock review content, no OKRs extracted
    assert len(p.changes) == 1
    assert all(c["action"] == "WRITE_FILE" for c in p.changes)


# ---------------------------------------------------------------------------
# Skill registry
# ---------------------------------------------------------------------------


def test_all_cadence_skills_registered():
    """All 4 cadence skills are in the registry."""
    from agents.v2.skills import list_skills

    skills = list_skills()
    assert "ikigai-daily" in skills
    assert "ikigai-weekly" in skills
    assert "ikigai-monthly" in skills
    assert "ikigai-quarterly" in skills


def test_skill_names_constants():
    """Each skill exposes SKILL_NAME."""
    assert ikigai_daily.SKILL_NAME == "ikigai-daily"
    assert ikigai_weekly.SKILL_NAME == "ikigai-weekly"
    assert ikigai_monthly.SKILL_NAME == "ikigai-monthly"
    assert ikigai_quarterly.SKILL_NAME == "ikigai-quarterly"
