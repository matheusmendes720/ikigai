"""Project state machine: draft → planned → backlog → active → paused → completed | cancelled."""

from ikigai.state_machines._sm_base import StateMachine, Transition


def project_state_machine() -> StateMachine:
    sm = StateMachine(initial_state="draft", name="project")
    sm.add_transition(Transition("draft", "planned", "plan", audit_message="Project planned"))
    sm.add_transition(Transition("planned", "backlog", "queue", audit_message="Added to backlog"))
    sm.add_transition(Transition("backlog", "active", "start", audit_message="Project started"))
    sm.add_transition(Transition("active", "paused", "pause", audit_message="Project paused"))
    sm.add_transition(Transition("paused", "active", "resume", audit_message="Project resumed"))
    sm.add_transition(Transition("active", "completed", "complete", audit_message="Project completed"))
    sm.add_transition(Transition("active", "blocked", "block", audit_message="Project blocked"))
    sm.add_transition(Transition("blocked", "active", "unblock", audit_message="Project unblocked"))
    sm.add_transition(Transition("active", "cancelled", "cancel", audit_message="Project cancelled"))
    sm.add_transition(Transition("paused", "cancelled", "cancel", audit_message="Cancelled from pause"))
    return sm


__all__ = ["project_state_machine"]
