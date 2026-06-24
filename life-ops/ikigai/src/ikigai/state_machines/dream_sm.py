"""Dream state machine: seed → active → fulfilled | abandoned | archived."""

from ikigai.state_machines._sm_base import StateMachine, Transition


def dream_state_machine() -> StateMachine:
    sm = StateMachine(initial_state="seed", name="dream")
    sm.add_transition(Transition("seed", "active", "begin", audit_message="Dream activated"))
    sm.add_transition(Transition("active", "fulfilled", "achieve", audit_message="Dream fulfilled"))
    sm.add_transition(Transition("active", "abandoned", "abandon", audit_message="Dream abandoned"))
    sm.add_transition(Transition("active", "archived", "archive", audit_message="Dream archived"))
    sm.add_transition(Transition("abandoned", "archived", "archive", audit_message="Archived after abandonment"))
    sm.add_transition(Transition("fulfilled", "archived", "archive", audit_message="Archived after fulfillment"))
    return sm


__all__ = ["dream_state_machine"]
