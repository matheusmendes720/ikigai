"""Goal state machine: draft → active → achieved | abandoned | paused | archived."""

from ikigai.state_machines._sm_base import StateMachine, Transition


def goal_state_machine() -> StateMachine:
    sm = StateMachine(initial_state="draft", name="goal")
    sm.add_transition(Transition("draft", "active", "start", audit_message="Goal activated"))
    sm.add_transition(Transition("active", "achieved", "achieve", audit_message="Goal achieved"))
    sm.add_transition(Transition("active", "abandoned", "abandon", audit_message="Goal abandoned"))
    sm.add_transition(Transition("active", "paused", "pause", audit_message="Goal paused"))
    sm.add_transition(Transition("paused", "active", "resume", audit_message="Goal resumed"))
    sm.add_transition(Transition("paused", "abandoned", "abandon", audit_message="Abandoned from pause"))
    sm.add_transition(Transition("abandoned", "archived", "archive", audit_message="Archived"))
    sm.add_transition(Transition("achieved", "archived", "archive", audit_message="Archived"))
    return sm


__all__ = ["goal_state_machine"]
