"""Fork adapters — cross-fork task view + bidirectional sync via IKIGAI mesh.

Each adapter implements the ForkAdapter Protocol:
  - name (str)
  - read(ueid) -> dict | None
  - apply_change(event: PropagationEvent) -> None
  - supports_field(field_name) -> bool

v1 scope: only CREATE actions are wired. UPDATE/DELETE/DONE return early
(per Phase 3 v1 design — full scope gated on 5+ SONHO logs).
"""

from src.mesh.adapters.base import ForkAdapter
from src.mesh.adapters.cli import CliAdapter
from src.mesh.adapters.taskdog import TaskdogAdapter
from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter

__all__ = [
    "ForkAdapter",
    "CliAdapter",
    "TaskdogAdapter",
    "SolverforgeCalendarAdapter",
]
