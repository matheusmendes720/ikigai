"""Objective state machine (OKR-style): draft → planned → active → done | blocked | abandoned."""

from ikigai.state_machines._sm_base import StateMachine, Transition


def objective_state_machine() -> StateMachine:
    sm = StateMachine(initial_state="draft", name="objective")
    sm.add_transition(Transition("draft", "planned", "plan", audit_message="Objective planned"))
    sm.add_transition(Transition("planned", "active", "start", audit_message="Objective activated"))
    sm.add_transition(Transition("active", "done", "complete", audit_message="All key results done"))
    sm.add_transition(Transition("active", "blocked", "block", audit_message="Blocked on dependency"))
    sm.add_transition(Transition("blocked", "active", "unblock", audit_message="Unblocked"))
    sm.add_transition(Transition("active", "abandoned", "abandon", audit_message="Objective abandoned"))
    sm.add_transition(Transition("planned", "abandoned", "abandon", audit_message="Abandoned before start"))
    return sm


__all__ = ["objective_state_machine"]
