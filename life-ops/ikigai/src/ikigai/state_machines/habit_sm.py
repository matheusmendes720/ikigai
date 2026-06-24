"""Habit state machine: active → paused → archived | mastered."""

from ikigai.state_machines._sm_base import StateMachine, Transition


def habit_state_machine() -> StateMachine:
    sm = StateMachine(initial_state="active", name="habit")
    sm.add_transition(Transition("active", "paused", "pause", audit_message="Habit paused"))
    sm.add_transition(Transition("paused", "active", "resume", audit_message="Habit resumed"))
    sm.add_transition(Transition("active", "archived", "archive", audit_message="Archived"))
    sm.add_transition(Transition("paused", "archived", "archive", audit_message="Archived from pause"))
    sm.add_transition(Transition("active", "mastered", "master", audit_message="Habit mastered"))
    return sm


__all__ = ["habit_state_machine"]
