"""Re-export all 8 state machines as a single import point.

Uses deferred imports to avoid circular import:
  __init__ -> _registry -> *_sm.py -> __init__ (StateMachine not yet in module)

Fix: re-export factory functions only; StateMachine is imported inside each *_sm.py
at runtime via a lazy import to avoid the cycle.
"""

# Deferred re-exports — each submodule imports StateMachine/Transition internally
# to break the import cycle (dream_sm.py imports at call time, not at module load).
# Also expose StateMachine and Transition directly for consumers
# Import these lazily to avoid cycle
import importlib

from sys_ikigai.state_machines._registry import (
    deliverable_state_machine,
    dream_state_machine,
    goal_state_machine,
    habit_state_machine,
    objective_state_machine,
    project_state_machine,
    routine_state_machine,
    task_state_machine,
)
from sys_ikigai.state_machines._registry import (
    deliverable_state_machine as deliverable_sm,
)
from sys_ikigai.state_machines._registry import (
    dream_state_machine as dream_sm,
)
from sys_ikigai.state_machines._registry import (
    goal_state_machine as goal_sm,
)
from sys_ikigai.state_machines._registry import (
    habit_state_machine as habit_sm,
)
from sys_ikigai.state_machines._registry import (
    objective_state_machine as objective_sm,
)
from sys_ikigai.state_machines._registry import (
    project_state_machine as project_sm,
)
from sys_ikigai.state_machines._registry import (
    routine_state_machine as routine_sm,
)
from sys_ikigai.state_machines._registry import (
    task_state_machine as task_sm,
)


def __getattr__(name: str):
    if name in ("StateMachine", "Transition"):
        mod = importlib.import_module("ikigai.state_machines._sm_base")
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "deliverable_sm",
    "deliverable_state_machine",
    "dream_sm",
    "dream_state_machine",
    "goal_sm",
    "goal_state_machine",
    "habit_sm",
    "habit_state_machine",
    "objective_sm",
    "objective_state_machine",
    "project_sm",
    "project_state_machine",
    "routine_sm",
    "routine_state_machine",
    "task_sm",
    "task_state_machine",
]
