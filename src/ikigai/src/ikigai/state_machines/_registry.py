"""All 8 entity state machines (Dream → Deliverable + Routine + Habit)."""

from ikigai.state_machines.dream_sm import dream_state_machine
from ikigai.state_machines.goal_sm import goal_state_machine
from ikigai.state_machines.objective_sm import objective_state_machine
from ikigai.state_machines.project_sm import project_state_machine
from ikigai.state_machines.task_sm import task_state_machine
from ikigai.state_machines.routine_sm import routine_state_machine
from ikigai.state_machines.habit_sm import habit_state_machine
from ikigai.state_machines.deliverable_sm import deliverable_state_machine

__all__ = [
    "dream_state_machine",
    "goal_state_machine",
    "objective_state_machine",
    "project_state_machine",
    "task_state_machine",
    "routine_state_machine",
    "habit_state_machine",
    "deliverable_state_machine",
]
