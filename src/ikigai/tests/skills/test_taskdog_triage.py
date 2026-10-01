"""Tests for the M161 taskdog-triage skill.

The skill ships in two layers:
  - `agents.v2.skills.taskdog_triage` — pure-Python detection + proposal builder
  - `.claude/skills/taskdog-triage/SKILL.md` — Claude Code skill description

These tests cover the pure-Python layer (detection rules, idempotency, proposal
shape) and the review-queue integration (approved proposal → TaskChange lands
in `data/review_queue/`).

Run::

    cd src/ikigai && uv run pytest tests/skills/test_taskdog_triage.py -v
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


# The skills module imports agents.v2.proposals.Proposal — that import chain
# requires src/ on sys.path, which conftest.py already arranges. We still
# import lazily inside fixtures / tests so collection-time errors surface
# as test failures rather than import-time crashes.

_FIXED_TODAY = date(2026, 10, 1)


def _task(
    ueid: str = "work:task:11112222:33334444",
    *,
    status: str = "planned",
    priority: int | None = 3,
    deadline: str | None = None,
    planned_start: str | None = None,
    description: str = "a meaningful task description",
    blocked_since: str | None = None,
    paused_since: str | None = None,
) -> dict[str, Any]:
    """Build a taskdog-shaped task dict for fixtures."""
    return {
        "ueid": ueid,
        "status": status,
        "priority": priority,
        "deadline": deadline,
        "planned_start": planned_start,
        "description": description,
        "blocked_since": blocked_since,
        "paused_since": paused_since,
    }


@pytest.fixture
def skill():
    """Import the skill module fresh per test."""
    from agents.v2.skills import taskdog_triage

    return taskdog_triage


@pytest.fixture
def proposal_cls():
    from agents.v2.proposals import Proposal

    return Proposal


# ---------------------------------------------------------------------------
# detect_changes: pure detection rules
# ---------------------------------------------------------------------------


class TestDeadlineSoon:
    def test_within_48h_bumps_priority(self, skill: Any) -> None:
        tasks = [_task(deadline=(_FIXED_TODAY + timedelta(days=1)).isoformat())]
        changes = skill.detect_changes(tasks, today=_FIXED_TODAY)
        assert len(changes) == 1
        assert changes[0]["fields"] == {"priority": 1}
        assert "deadline in 1 day(s)" in changes[0]["rationale"]

    def test_48h_boundary_inclusive(self, skill: Any) -> None:
        tasks = [_task(deadline=(_FIXED_TODAY + timedelta(days=2)).isoformat())]
        changes = skill.detect_changes(tasks, today=_FIXED_TODAY)
        assert any(c["fields"].get("priority") == 1 for c in changes)

    def test_done_status_skips_bump(self, skill: Any) -> None:
        tasks = [
            _task(
                deadline=(_FIXED_TODAY + timedelta(days=1)).isoformat(),
                status="done",
            )
        ]
        changes = skill.detect_changes(tasks, today=_FIXED_TODAY)
        assert all(c["fields"].get("priority") != 1 for c in changes)

    def test_already_priority_1_skipped(self, skill: Any) -> None:
        tasks = [
            _task(
                deadline=(_FIXED_TODAY + timedelta(days=1)).isoformat(),
                priority=1,
            )
        ]
        changes = skill.detect_changes(tasks, today=_FIXED_TODAY)
        assert all(c["fields"].get("priority") != 1 for c in changes)

    def test_9_days_out_not_flagged(self, skill: Any) -> None:
        tasks = [_task(deadline=(_FIXED_TODAY + timedelta(days=9)).isoformat())]
        changes = skill.detect_changes(tasks, today=_FIXED_TODAY)
        assert all(c["fields"].get("priority") != 1 for c in changes)


class TestOverdue:
    def test_past_planned_start_moves_to_in_progress(self, skill: Any) -> None:
        tasks = [_task(planned_start=(_FIXED_TODAY - timedelta(days=3)).isoformat())]
        changes = skill.detect_changes(tasks, today=_FIXED_TODAY)
        assert any(
            c["fields"] == {"status": "in_progress"} for c in changes
        ), f"expected status=in_progress change, got {changes}"

    def test_in_progress_status_not_re_flagged(self, skill: Any) -> None:
        tasks = [
            _task(
                planned_start=(_FIXED_TODAY - timedelta(days=3)).isoformat(),
                status="in_progress",
            )
        ]
        changes = skill.detect_changes(tasks, today=_FIXED_TODAY)
        assert all(c["fields"].get("status") != "in_progress" for c in changes)


class TestMissingDescription:
    def test_empty_description_flagged(self, skill: Any) -> None:
        tasks = [_task(description="")]
        changes = skill.detect_changes(tasks, today=_FIXED_TODAY)
        assert any("description" in c["fields"] for c in changes)
        flagged = next(c for c in changes if "description" in c["fields"])
        assert "auto-flagged" in flagged["fields"]["description"]
        assert _FIXED_TODAY.isoformat() in flagged["fields"]["description"]

    def test_short_description_flagged(self, skill: Any) -> None:
        tasks = [_task(description="todo")]
        changes = skill.detect_changes(tasks, today=_FIXED_TODAY)
        assert any(
            "description" in c["fields"] and "auto-flagged" in c["fields"]["description"]
            for c in changes
        )

    def test_long_description_skipped(self, skill: Any) -> None:
        tasks = [_task(description="x" * 50)]
        changes = skill.detect_changes(tasks, today=_FIXED_TODAY)
        assert all(
            not (c["fields"].get("description", "").startswith("(auto-flagged"))
            for c in changes
        )


class TestTaskFiltering:
    def test_task_without_ueid_skipped(self, skill: Any) -> None:
        tasks = [{"status": "planned", "priority": 5}]
        changes = skill.detect_changes(tasks, today=_FIXED_TODAY)
        assert changes == []

    def test_malformed_date_treated_as_none(self, skill: Any) -> None:
        tasks = [_task(deadline="not-a-date", planned_start="also-not-a-date")]
        changes = skill.detect_changes(tasks, today=_FIXED_TODAY)
        # No false-positive from bad date strings
        assert all(c["fields"].get("priority") != 1 for c in changes)
        assert all(c["fields"].get("status") != "in_progress" for c in changes)


# ---------------------------------------------------------------------------
# propose(): Proposal shape and idempotency
# ---------------------------------------------------------------------------


class TestPropose:
    def test_builds_valid_proposal(self, skill: Any, proposal_cls: Any) -> None:
        tasks = [_task(deadline=(_FIXED_TODAY + timedelta(days=1)).isoformat())]
        proposal = skill.propose(tasks, today=_FIXED_TODAY)
        assert isinstance(proposal, proposal_cls)
        assert proposal.skill == "taskdog-triage"
        assert proposal.approval_state == "pending"
        errors = proposal.validate()
        assert errors == [], f"unexpected validation errors: {errors}"

    def test_empty_tasks_empty_proposal(self, skill: Any) -> None:
        proposal = skill.propose([], today=_FIXED_TODAY)
        assert proposal.changes == []
        assert "0 candidate" in proposal.reasoning

    def test_idempotent(self, skill: Any) -> None:
        """Running twice on the same inputs produces identical proposals."""
        tasks = [
            _task(
                ueid="work:task:11112222:33334444",
                deadline=(_FIXED_TODAY + timedelta(days=1)).isoformat(),
                planned_start=(_FIXED_TODAY - timedelta(days=1)).isoformat(),
                description="",
            ),
            _task(
                ueid="work:task:aaaa1111:bbbb2222",
                deadline=(_FIXED_TODAY + timedelta(days=2)).isoformat(),
                description="proper description here",
            ),
        ]
        p1 = skill.propose(tasks, today=_FIXED_TODAY)
        p2 = skill.propose(tasks, today=_FIXED_TODAY)
        # Compare deterministic content only — created_at / proposal_id /
        # vault_log_path differ per call and are not part of the contract.
        assert p1.skill == p2.skill
        assert p1.reasoning == p2.reasoning
        assert p1.changes == p2.changes
        assert p1.approval_state == p2.approval_state

    def test_each_change_has_action_ueid(self, skill: Any) -> None:
        tasks = [_task(deadline=(_FIXED_TODAY + timedelta(days=1)).isoformat())]
        proposal = skill.propose(tasks, today=_FIXED_TODAY)
        for c in proposal.changes:
            assert "action" in c
            assert "ueid" in c
            assert "fields" in c

    def test_run_skill_entry_point(self, skill: Any) -> None:
        """run_skill is the canonical entry for /skill taskdog-triage."""
        tasks = [_task(deadline=(_FIXED_TODAY + timedelta(days=1)).isoformat())]
        proposal = skill.run_skill(tasks=tasks)
        assert proposal.skill == "taskdog-triage"
        assert len(proposal.changes) >= 1


# ---------------------------------------------------------------------------
# Review-queue integration: approved proposal lands as TaskChange
# ---------------------------------------------------------------------------


class TestReviewQueueIntegration:
    def test_approved_proposal_creates_taskchange(
        self, skill: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the user --approves, the proposal's changes must convert into
        TaskChange events and end up in data/review_queue/."""
        # Redirect QUEUE_DIR to a tmp dir so the test never writes to real queue
        from src.mesh import queue as queue_mod

        monkeypatch.setattr(queue_mod, "QUEUE_DIR", tmp_path)

        from contracts.task_change import TaskAction, TaskChange

        tasks = [_task(deadline=(_FIXED_TODAY + timedelta(days=1)).isoformat())]
        proposal = skill.propose(tasks, today=_FIXED_TODAY)

        # Simulate the chat loop converting an approved proposal into a
        # TaskChange and enqueueing it. The SKILL.md spec is the contract —
        # we mirror the loop here.
        assert proposal.approval_state == "pending"
        proposal.approval_state = "approved"

        for c in proposal.changes:
            tc = TaskChange(
                event_id=uuid.uuid4().hex,
                ueid=c["ueid"],
                action=TaskAction.UPDATE,
                fields=c["fields"],
                source_fork=f"td_chat:{skill.SKILL_NAME}",
                timestamp=datetime.now(timezone.utc),
            )
            event_id = queue_mod.enqueue(tc)
            assert event_id == tc.event_id

        # Verify the file landed in the queue dir
        queue_files = list(tmp_path.glob("*.json"))
        assert len(queue_files) == len(proposal.changes)
        for fp in queue_files:
            payload = json.loads(fp.read_text(encoding="utf-8"))
            assert payload["action"] == "update"
            assert payload["source_fork"] == f"td_chat:{skill.SKILL_NAME}"

    def test_meta_plan_format_for_audit(self, skill: Any) -> None:
        """meta_plan proposals must include rationale + source attribution."""
        tasks = [_task(deadline=(_FIXED_TODAY + timedelta(days=1)).isoformat())]
        proposal = skill.propose(tasks, today=_FIXED_TODAY)
        for c in proposal.changes:
            assert "rationale" in c
            assert isinstance(c["rationale"], str)
            assert len(c["rationale"]) > 0


# ---------------------------------------------------------------------------
# Adapter failure: graceful degradation
# ---------------------------------------------------------------------------


class TestAdapterFailure:
    def test_run_skill_with_none_returns_empty_proposal(self, skill: Any) -> None:
        """run_skill(tasks=None) is the documented contract for the chat loop
        when the adapter is unavailable. It should not crash."""
        proposal = skill.run_skill(tasks=None)
        assert proposal.skill == "taskdog-triage"
        assert proposal.changes == []

    def test_propose_does_not_call_adapter(self, skill: Any) -> None:
        """Pure-function contract: propose() must NEVER touch the TaskdogAdapter
        or the filesystem. This is the test that locks the dependency-free
        boundary in SKILL.md."""
        with patch("src.mesh.adapters.taskdog.TaskdogAdapter") as mock_adapter:
            skill.propose([_task()], today=_FIXED_TODAY)
            mock_adapter.assert_not_called()


# ---------------------------------------------------------------------------
# Drift guard: SKILL_NAME stability
# ---------------------------------------------------------------------------


def test_skill_name_is_stable(skill: Any) -> None:
    """SKILL_NAME is referenced by the cron + slash handler — must not drift."""
    assert skill.SKILL_NAME == "taskdog-triage"


def test_run_skill_idempotent_across_calls(skill: Any) -> None:
    """Repeated run_skill invocations on the same tasks must produce byte-
    identical proposals (ignoring created_at / proposal_id which are
    timestamp-derived)."""
    tasks = [_task(deadline=(_FIXED_TODAY + timedelta(days=1)).isoformat())]
    p1 = skill.run_skill(tasks=tasks)
    p2 = skill.run_skill(tasks=tasks)
    # Compare the deterministic content only
    assert p1.skill == p2.skill
    assert p1.reasoning == p2.reasoning
    assert p1.changes == p2.changes
