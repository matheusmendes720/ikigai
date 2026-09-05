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

from .common import UEID, Period, Priority, EntityType, RegimeState, TimestampMixin  # noqa: F403
from .common import PaeCyclePhase, PlanTier, VectorKey  # noqa: F403
from .base import BasePlanContract  # noqa: F403
from .sonho import Sonho  # noqa: F403
from .objetivo import Objetivo  # noqa: F403
from .meta import Meta  # noqa: F403
from .projeto import Projeto  # noqa: F403
from .entrega import Entrega  # noqa: F403
from .tarefa import Tarefa  # noqa: F403
from .task import Task, Subtask, ChecklistItem, Project, Milestone, Deliverable  # noqa: F403
from .planning import PlanningCycle, Wave, Sprint, VaultEvent  # noqa: F403
from .metrics import Burndown, ExecutionRate, QHEScore  # noqa: F403
from .investigation import Investigation, InvestigationStatus  # noqa: F403

__all__ = [
    # common
    "UEID",
    "Period",
    "Priority",
    "EntityType",
    "RegimeState",
    "TimestampMixin",
    # new enums
    "PaeCyclePhase",
    "PlanTier",
    "VectorKey",
    # base
    "BasePlanContract",
    # plan hierarchy
    "Sonho",
    "Objetivo",
    "Meta",
    "Projeto",
    "Entrega",
    "Tarefa",
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
    # investigation
    "Investigation",
    "InvestigationStatus",
]
