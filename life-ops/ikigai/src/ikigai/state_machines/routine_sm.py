"""Routine state machine: draft → active → paused → archived."""

from ikigai.state_machines._sm_base import StateMachine, Transition


def routine_state_machine() -> StateMachine:
    sm = StateMachine(initial_state="draft", name="routine")
    sm.add_transition(Transition("draft", "active", "activate", audit_message="Routine activated"))
    sm.add_transition(Transition("active", "paused", "pause", audit_message="Routine paused"))
    sm.add_transition(Transition("paused", "active", "resume", audit_message="Routine resumed"))
    sm.add_transition(Transition("active", "archived", "archive", audit_message="Archived"))
    sm.add_transition(Transition("paused", "archived", "archive", audit_message="Archived from pause"))
    return sm


__all__ = ["routine_state_machine"]
