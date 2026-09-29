"""Tests for M161 — taskdog-triage skill."""
from __future__ import annotations

from datetime import date

import pytest

from agents.v2.skills import taskdog_triage


# ---------------------------------------------------------------------------
# detect_changes: deadline logic
# ---------------------------------------------------------------------------


def test_deadline_within_2_days_bumps_priority():
    """Task with deadline in 2 days and not done → priority bumped to 1."""
    today = date(2026, 9, 29)
    tasks = [
        {"ueid": "tsk:1:abc:1111", "status": "planned", "priority": 5,
         "deadline": "2026-10-01", "description": "this is long enough"}
    ]
    changes = taskdog_triage.detect_changes(tasks, today=today)
    assert len(changes) == 1
    assert changes[0]["action"] == "UPDATE"
    assert changes[0]["fields"] == {"priority": 1}


def test_deadline_today_also_bumps():
    """Deadline today (0 days) also bumps priority."""
    today = date(2026, 9, 29)
    tasks = [
        {"ueid": "tsk:1:abc:1111", "status": "planned", "priority": 5,
         "deadline": "2026-09-29", "description": "this is long enough"}
    ]
    changes = taskdog_triage.detect_changes(tasks, today=today)
    assert len(changes) == 1
    assert changes[0]["fields"]["priority"] == 1


def test_deadline_far_in_future_no_change():
    """Deadline > 2 days out → no priority bump."""
    today = date(2026, 9, 29)
    tasks = [
        {"ueid": "tsk:1:abc:1111", "status": "planned", "priority": 5,
         "deadline": "2026-10-15", "description": "this is long enough"}
    ]
    changes = taskdog_triage.detect_changes(tasks, today=today)
    assert changes == []


def test_done_tasks_with_near_deadline_ignored():
    """Tasks already 'done' are not bumped even if deadline is near."""
    today = date(2026, 9, 29)
    tasks = [
        {"ueid": "tsk:1:abc:1111", "status": "done", "priority": 5,
         "deadline": "2026-09-29", "description": "this is long enough"}
    ]
    changes = taskdog_triage.detect_changes(tasks, today=today)
    assert changes == []


def test_priority_already_1_not_bumped_again():
    """If priority is already 1, no duplicate bump suggestion."""
    today = date(2026, 9, 29)
    tasks = [
        {"ueid": "tsk:1:abc:1111", "status": "planned", "priority": 1,
         "deadline": "2026-09-29", "description": "this is long enough"}
    ]
    changes = taskdog_triage.detect_changes(tasks, today=today)
    assert changes == []


# ---------------------------------------------------------------------------
# detect_changes: overdue logic
# ---------------------------------------------------------------------------


def test_overdue_planned_start_becomes_in_progress():
    """planned_start in past and status='planned' → suggest in_progress."""
    today = date(2026, 9, 29)
    tasks = [
        {"ueid": "tsk:1:abc:1111", "status": "planned",
         "planned_start": "2026-09-25", "description": "this is long enough"}
    ]
    changes = taskdog_triage.detect_changes(tasks, today=today)
    assert len(changes) == 1
    assert changes[0]["fields"] == {"status": "in_progress"}


def test_in_progress_with_past_planned_start_no_change():
    """If status already advanced, no auto-suggest."""
    today = date(2026, 9, 29)
    tasks = [
        {"ueid": "tsk:1:abc:1111", "status": "in_progress",
         "planned_start": "2026-09-25", "description": "this is long enough"}
    ]
    changes = taskdog_triage.detect_changes(tasks, today=today)
    assert changes == []


# ---------------------------------------------------------------------------
# detect_changes: description
# ---------------------------------------------------------------------------


def test_missing_description_flagged():
    """Empty description → flag."""
    today = date(2026, 9, 29)
    tasks = [
        {"ueid": "tsk:1:abc:1111", "status": "planned",
         "description": ""}
    ]
    changes = taskdog_triage.detect_changes(tasks, today=today)
    assert len(changes) == 1
    assert "auto-flagged" in changes[0]["fields"]["description"]


def test_short_description_flagged():
    """Description < 10 chars → flag."""
    today = date(2026, 9, 29)
    tasks = [
        {"ueid": "tsk:1:abc:1111", "status": "planned",
         "description": "short"}
    ]
    changes = taskdog_triage.detect_changes(tasks, today=today)
    assert len(changes) == 1


def test_long_description_not_flagged():
    """Description ≥ 10 chars → no flag."""
    today = date(2026, 9, 29)
    tasks = [
        {"ueid": "tsk:1:abc:1111", "status": "planned",
         "description": "this is long enough"}
    ]
    changes = taskdog_triage.detect_changes(tasks, today=today)
    assert changes == []


# ---------------------------------------------------------------------------
# detect_changes: combined
# ---------------------------------------------------------------------------


def test_task_with_all_3_issues_yields_3_changes():
    """Task with deadline-soon + overdue + missing desc → 3 changes."""
    today = date(2026, 9, 29)
    tasks = [
        {"ueid": "tsk:1:abc:1111", "status": "planned", "priority": 5,
         "deadline": "2026-09-30", "planned_start": "2026-09-20",
         "description": ""}
    ]
    changes = taskdog_triage.detect_changes(tasks, today=today)
    assert len(changes) == 3


def test_empty_task_list_no_changes():
    """Empty list → empty changes."""
    today = date(2026, 9, 29)
    assert taskdog_triage.detect_changes([], today=today) == []


def test_task_without_ueid_skipped():
    """Tasks missing ueid are silently skipped."""
    today = date(2026, 9, 29)
    tasks = [{"status": "planned", "deadline": "2026-09-30"}]
    assert taskdog_triage.detect_changes(tasks, today=today) == []


def test_invalid_date_format_does_not_crash():
    """Garbage in date fields doesn't raise."""
    today = date(2026, 9, 29)
    tasks = [
        {"ueid": "tsk:1:abc:1111", "status": "planned",
         "deadline": "not-a-date", "planned_start": "garbage"}
    ]
    changes = taskdog_triage.detect_changes(tasks, today=today)
    # Just shouldn't crash; may or may not have changes
    assert isinstance(changes, list)


# ---------------------------------------------------------------------------
# propose: builds Proposal correctly
# ---------------------------------------------------------------------------


def test_propose_returns_pending_proposal():
    """propose() returns a Proposal with state='pending'."""
    today = date(2026, 9, 29)
    tasks = [
        {"ueid": "tsk:1:abc:1111", "status": "planned",
         "deadline": "2026-09-30", "description": "this is long enough"}
    ]
    p = taskdog_triage.propose(tasks, today=today)
    assert p.approval_state == "pending"
    assert p.skill == "taskdog-triage"
    assert len(p.changes) >= 1
    assert p.proposal_id  # auto-generated
    assert p.created_at  # auto-set


def test_propose_with_no_tasks():
    """propose() with no tasks → empty proposal, but still valid."""
    today = date(2026, 9, 29)
    p = taskdog_triage.propose([], today=today)
    assert p.approval_state == "pending"
    assert p.changes == []
    assert p.validate() == ["proposal has no changes"]


def test_run_skill_no_args():
    """run_skill() with no tasks → empty proposal."""
    p = taskdog_triage.run_skill()
    assert p.skill == "taskdog-triage"
    assert p.changes == []
