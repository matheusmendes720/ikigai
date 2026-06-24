"""Deliverable state machine: draft → planned → in_progress → done | cancelled."""

from ikigai.state_machines._sm_base import StateMachine, Transition


def deliverable_state_machine() -> StateMachine:
    sm = StateMachine(initial_state="draft", name="deliverable")
    sm.add_transition(Transition("draft", "planned", "plan", audit_message="Planned"))
    sm.add_transition(Transition("planned", "in_progress", "start", audit_message="Work started"))
    sm.add_transition(Transition("in_progress", "done", "deliver", audit_message="Delivered"))
    sm.add_transition(Transition("draft", "cancelled", "cancel", audit_message="Cancelled"))
    sm.add_transition(Transition("planned", "cancelled", "cancel", audit_message="Cancelled"))
    sm.add_transition(Transition("in_progress", "cancelled", "cancel", audit_message="Cancelled"))
    return sm


__all__ = ["deliverable_state_machine"]
