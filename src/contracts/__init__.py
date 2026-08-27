"""Shared Pydantic v2 contracts for the Algorithmic Life OS.

This package contains canonical Pydantic v2 models that are shared across
ALL layers (agent, interface, data). These are the ONLY contracts
between layers.

Design rules:
- frozen=True, extra="forbid" on all models
- UEID as primary identifier type
- No business logic — pure data containers with invariants
- Enums live here too (shared across layers)

Layers:
    - vault/      → markdown source of truth (no Python)
    - src/contracts/ → canonical Pydantic contracts (THIS PACKAGE)
    - src/operational/ → consumer: full domain models (imports from contracts/)
    - src/ikigai/  → consumer: deep agent reads/writes vault, uses contracts
    - data/        → runtime: SQLite, chroma, JSON (consumed via contracts)
    - interfaces/  → consumer: reads data/, writes user feedback
"""

from __future__ import annotations

from contracts.common import *  # noqa: F403
from contracts.task import *   # noqa: F403
from contracts.planning import *  # noqa: F403
from contracts.metrics import *  # noqa: F403

__all__ = [
    # common
    "UEID",
    "Period",
    "Priority",
    "EntityType",
    # task
    "Task",
    "Subtask",
    "ChecklistItem",
    "Project",
    "Milestone",
    "Deliverable",
    # planning
    "PlanningCycle",
    "Wave",
    "Sprint",
    "VaultEvent",
    # metrics
    "Burndown",
    "ExecutionRate",
    "QHEScore",
]
