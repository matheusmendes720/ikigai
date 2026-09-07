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

from .base import BasePlanContract
from .common import (
    UEID,
    EntityType,
    PaeCyclePhase,
    Period,
    PlanTier,
    Priority,
    RegimeState,
    TimestampMixin,
    VectorKey,
)
from .entrega import Entrega
from .investigation import Investigation, InvestigationStatus
from .meta import Meta
from .metrics import Burndown, ExecutionRate, QHEScore
from .objetivo import Objetivo
from .planning import PlanningCycle, Sprint, VaultEvent, Wave
from .projeto import Projeto
from .sonho import Sonho
from .tarefa import Tarefa
from .task import (
    ChecklistItem,
    Deliverable,
    Milestone,
    Project,
    Subtask,
    Task,
)

# (alphabetical sort would destroy the intentional # common / # plan hierarchy / # metrics groupings)
# Ruff RUF022 cannot apply noqa to `__all__ = [...]` itself, so we suppress at the module level via per-file-ignore.
# See: pyproject.toml [tool.ruff.lint.per-file-ignores] for the canonical suppression.
__all__ = [  # noqa: RUF022 — entries are grouped by domain with comments, not alphabetically sorted
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
