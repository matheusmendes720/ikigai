"""Tests for ikigai.state_machines — all 8 FSMs via factory functions."""

from __future__ import annotations

import pytest
from ikigai.state_machines import StateMachine, Transition
from ikigai.state_machines import (
    dream_state_machine,
    goal_state_machine,
    objective_state_machine,
    project_state_machine,
    task_state_machine,
    deliverable_state_machine,
    routine_state_machine,
    habit_state_machine,
)
from ikigai.enums import RegimeType


class TestStateMachineBasics:
    """Shared StateMachine behavior tests."""

    def test_initial_state_is_set(self) -> None:
        """StateMachine must start in its initial state."""
        sm = StateMachine(initial_state="idle")
        assert sm.current_state == "idle"

    def test_invalid_initial_state_raises(self) -> None:
        """Invalid initial state name must raise ValueError."""
        with pytest.raises(ValueError):
            StateMachine(initial_state="ghost")

    def test_add_transition_and_transition(self) -> None:
        """add_transition + transition_to must work."""
        sm = StateMachine(initial_state="idle")
        sm.add_transition("idle", "active", "begin")
        sm.transition_to("active")
        assert sm.current_state == "active"

    def test_transition_to_invalid_state_raises(self) -> None:
        """Invalid state name must raise ValueError."""
        sm = StateMachine(initial_state="idle")
        with pytest.raises(ValueError):
            sm.transition_to("ghost")

    def test_guard_blocks_transition(self) -> None:
        """Guard returning False must block the transition."""
        sm = StateMachine(initial_state="idle")
        sm.add_transition("idle", "done", "finish", guard=lambda ctx: ctx.get("allowed", False))
        sm.context["allowed"] = False
        with pytest.raises(Exception):
            sm.transition_to("done")
        assert sm.current_state == "idle"

    def test_guard_allows_transition(self) -> None:
        """Guard returning True must allow the transition."""
        sm = StateMachine(initial_state="idle")
        sm.add_transition("idle", "active", "activate", guard=lambda ctx: ctx.get("allowed", False))
        sm.context["allowed"] = True
        sm.transition_to("active")
        assert sm.current_state == "active"

    def test_audit_log_records_transitions(self) -> None:
        """Each transition must be recorded in audit_log."""
        sm = StateMachine(initial_state="idle")
        sm.add_transition("idle", "active", "begin")
        sm.transition_to("active")
        assert len(sm.audit_log) == 1
        assert sm.audit_log[0].from_state == "idle"
        assert sm.audit_log[0].to_state == "active"

    def test_can_transition_to_property(self) -> None:
        """can_transition_to property must work."""
        sm = StateMachine(initial_state="idle")
        sm.add_transition("idle", "active", "begin")
        assert sm.can_transition_to("active") is True
        assert sm.can_transition_to("done") is False


class TestDreamSM:
    """Dream state machine: seed → active → fulfilled/abandoned/archived."""

    def test_initial_is_seed(self) -> None:
        sm = dream_state_machine()
        assert sm.current_state == "seed"

    def test_seed_to_active(self) -> None:
        sm = dream_state_machine()
        sm.transition_to("active")
        assert sm.current_state == "active"

    def test_active_to_fulfilled(self) -> None:
        sm = dream_state_machine()
        sm.transition_to("active")
        sm.transition_to("fulfilled")
        assert sm.current_state == "fulfilled"

    def test_active_to_abandoned(self) -> None:
        sm = dream_state_machine()
        sm.transition_to("active")
        sm.transition_to("abandoned")
        assert sm.current_state == "abandoned"


class TestGoalSM:
    """Goal state machine: draft → active → achieved/abandoned/paused/archived."""

    def test_initial_is_draft(self) -> None:
        sm = goal_state_machine()
        assert sm.current_state == "draft"

    def test_draft_to_active(self) -> None:
        sm = goal_state_machine()
        sm.transition_to("active")
        assert sm.current_state == "active"

    def test_active_to_achieved(self) -> None:
        sm = goal_state_machine()
        sm.transition_to("active")
        sm.transition_to("achieved")
        assert sm.current_state == "achieved"


class TestObjectiveSM:
    """Objective state machine: draft → planned → active → done/blocked/abandoned."""

    def test_initial_is_draft(self) -> None:
        sm = objective_state_machine()
        assert sm.current_state == "draft"

    def test_draft_to_planned(self) -> None:
        sm = objective_state_machine()
        sm.transition_to("planned")
        assert sm.current_state == "planned"

    def test_planned_to_active(self) -> None:
        sm = objective_state_machine()
        sm.transition_to("planned")
        sm.transition_to("active")
        assert sm.current_state == "active"

    def test_active_to_done(self) -> None:
        sm = objective_state_machine()
        sm.transition_to("planned")
        sm.transition_to("active")
        sm.transition_to("done")
        assert sm.current_state == "done"


class TestProjectSM:
    """Project state machine: draft → planned → backlog → active → paused → completed/cancelled."""

    def test_initial_is_draft(self) -> None:
        sm = project_state_machine()
        assert sm.current_state == "draft"

    def test_draft_to_planned(self) -> None:
        sm = project_state_machine()
        sm.transition_to("planned")
        assert sm.current_state == "planned"

    def test_planned_to_backlog(self) -> None:
        sm = project_state_machine()
        sm.transition_to("planned")
        sm.transition_to("backlog")
        assert sm.current_state == "backlog"

    def test_backlog_to_active(self) -> None:
        sm = project_state_machine()
        sm.transition_to("planned")
        sm.transition_to("backlog")
        sm.transition_to("active")
        assert sm.current_state == "active"


class TestTaskSM:
    """Task state machine: todo → in_progress → blocked → done | cancelled."""

    def test_initial_is_todo(self) -> None:
        sm = task_state_machine()
        assert sm.current_state == "todo"

    def test_todo_to_in_progress(self) -> None:
        sm = task_state_machine()
        sm.transition_to("in_progress")
        assert sm.current_state == "in_progress"

    def test_in_progress_to_blocked(self) -> None:
        sm = task_state_machine()
        sm.transition_to("in_progress")
        sm.transition_to("blocked")
        assert sm.current_state == "blocked"

    def test_in_progress_to_done(self) -> None:
        sm = task_state_machine()
        sm.transition_to("in_progress")
        sm.transition_to("done")
        assert sm.current_state == "done"

    def test_todo_to_cancelled(self) -> None:
        sm = task_state_machine()
        sm.transition_to("cancelled")
        assert sm.current_state == "cancelled"


class TestDeliverableSM:
    """Deliverable state machine: draft → planned → in_progress → done/cancelled."""

    def test_initial_is_draft(self) -> None:
        sm = deliverable_state_machine()
        assert sm.current_state == "draft"

    def test_draft_to_planned(self) -> None:
        sm = deliverable_state_machine()
        sm.transition_to("planned")
        assert sm.current_state == "planned"

    def test_planned_to_in_progress(self) -> None:
        sm = deliverable_state_machine()
        sm.transition_to("planned")
        sm.transition_to("in_progress")
        assert sm.current_state == "in_progress"


class TestRoutineSM:
    """Routine state machine: draft → active → paused → archived."""

    def test_initial_is_draft(self) -> None:
        sm = routine_state_machine()
        assert sm.current_state == "draft"

    def test_draft_to_active(self) -> None:
        sm = routine_state_machine()
        sm.transition_to("active")
        assert sm.current_state == "active"

    def test_active_to_paused(self) -> None:
        sm = routine_state_machine()
        sm.transition_to("active")
        sm.transition_to("paused")
        assert sm.current_state == "paused"


class TestHabitSM:
    """Habit state machine: active → paused → archived | mastered."""

    def test_initial_is_active(self) -> None:
        sm = habit_state_machine()
        assert sm.current_state == "active"

    def test_active_to_paused(self) -> None:
        sm = habit_state_machine()
        sm.transition_to("paused")
        assert sm.current_state == "paused"

    def test_active_to_mastered(self) -> None:
        sm = habit_state_machine()
        sm.transition_to("mastered")
        assert sm.current_state == "mastered"
