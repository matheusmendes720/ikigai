"""Task state machine: draft/todo → in_progress → blocked → done | cancelled."""

from ikigai.state_machines._sm_base import StateMachine, Transition


def task_state_machine() -> StateMachine:
    sm = StateMachine(initial_state="todo", name="task")
    sm.add_transition(Transition("todo", "in_progress", "start", audit_message="Task started"))
    sm.add_transition(Transition("in_progress", "blocked", "block", audit_message="Task blocked"))
    sm.add_transition(Transition("blocked", "in_progress", "unblock", audit_message="Task unblocked"))
    sm.add_transition(Transition("in_progress", "done", "complete", audit_message="Task done"))
    sm.add_transition(Transition("todo", "cancelled", "cancel", audit_message="Task cancelled"))
    sm.add_transition(Transition("in_progress", "cancelled", "cancel", audit_message="Task cancelled"))
    sm.add_transition(Transition("blocked", "cancelled", "cancel", audit_message="Task cancelled"))
    return sm


__all__ = ["task_state_machine"]
