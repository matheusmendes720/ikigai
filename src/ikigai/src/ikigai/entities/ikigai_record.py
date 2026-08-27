"""IKIGAiRecord — canonical single root, polymorphic per SPEC D6.

Layer 1 of the unified data model (§1). The discriminated union lives on
`entity_type` (SPEC D6) so downstream adapters (vault serializer, SQLite
mirror, JsonPlusSerializer checkpoint, MCP Gateway) all round-trip the
same shape.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ikigai.entities.correction_signal import CorrectionSignal
from ikigai.entities.drift_state import DriftState
from ikigai.entities.fractal_regime import FractalRegime
from ikigai.entities.override import OverrideRecord
from ikigai.entities.score_value import ScoreUnit, ScoreValue
from ikigai.entities.ueid import UEID


# ──────── Primitive value types ────────

VectorKey = Annotated[str, StringConstraints(min_length=1, max_length=128)]
"""SPEC D3 — fractal vector key (e.g. 'skill', 'skill.python')."""


# ──────── Discriminators (polymorphism per D6) ────────

class EntityType(str, Enum):
    """Polymorphic discriminator (§3.2). Each variant may carry extra
    fields (per SPEC D6 `extra="allow"`) — e.g. `DreamEntity.motivation`,
    `GoalEntity.success_metrics` live in `custom` / extras, NOT here."""

    DREAM = "dream"
    GOAL = "goal"
    OBJECTIVE = "objective"
    PROJECT = "project"
    TASK = "task"
    DELIVERABLE = "deliverable"
    ROUTINE = "routine"
    TIME_BLOCK = "time_block"
    RITUAL = "ritual"
    HABIT = "habit"
    VECTOR = "vector"
    PROFILE = "profile"
    SKILL_NODE = "skill_node"
    OPPORTUNITY = "opportunity"
    REGIME = "regime"
    CYCLE = "cycle"  # derived log entry — is_placeholder=True per D7


class StatusType(str, Enum):
    """§6 — 8 explicit state machines across all entity variants."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ABANDONED = "abandoned"
    FALSIFIED = "falsified"
    PIVOTED = "pivot"


# ──────── THE ROOT ────────

class IKIGAiRecord(BaseModel):
    """Canonical IKIGAi state — single root, polymorphic per SPEC D6.

    Honors: D6 (extra=allow, discriminator, frozen=False), D7 (placeholder),
    D10 (UEID), D12 (override + audit), D13 (fractal regime),
    I3 (percent ∈ [0,100]), I4 (ratio ∈ [0,1]), I6 (slug immutable),
    I7 (phase_weights REMOVED), I11 (phase_iteration ∈ [0,5]),
    D8/I9 (source_md_path REQUIRED), D14 (§8.2 drift).
    """

    model_config = ConfigDict(
        extra="allow",
        discriminator="entity_type",
        frozen=False,
    )

    # ── Identity (D6, D10, §3.1, §3.2)
    ueid: UEID
    entity_type: EntityType
    slug: str = Field(min_length=1, max_length=128)  # I6: immutable post-creation
    parent_ueid: Optional[UEID] = None
    related_ueids: list[UEID] = Field(default_factory=list)
    title: str
    description: Optional[str] = None
    status: StatusType = StatusType.DRAFT

    # ── §3.2 at-creation snapshots (NOT current)
    phase_at_creation: Optional[str] = None
    regime_at_creation: Optional[str] = None
    primary_score: Optional[ScoreValue] = None

    # ── Vector scoring (D2, D3, I3)
    ikigai_vectors: list[VectorKey] = Field(default_factory=list)
    vector_weights_snapshot: dict[VectorKey, float] = Field(default_factory=dict)
    vector_scores: dict[VectorKey, ScoreValue] = Field(default_factory=dict)
    vector_metadata: dict[VectorKey, dict[str, Any]] = Field(default_factory=dict)

    # ── Current meta-vector + Q_HE
    meta_vector_score: Optional[ScoreValue] = None
    q_he_score: Optional[ScoreValue] = None  # I4: unit MUST be 'ratio'

    # ── Fractal regime (D13) — replaces single regime_state field
    regime: Optional[FractalRegime] = None

    # ── Phase state (D11, I11, §3.2)
    phase: Optional[str] = None
    phase_iteration: Optional[int] = Field(default=None, ge=0, le=5)
    phase_converged: Optional[bool] = None
    # NOTE: phase_weights REMOVED — lives on separate PhaseSnapshot (I7)

    # ── Decomposition chain (§3.2)
    active_dream_ueid: Optional[UEID] = None
    active_goal_ueids: list[UEID] = Field(default_factory=list)
    active_objective_ueids: list[UEID] = Field(default_factory=list)
    active_project_ueids: list[UEID] = Field(default_factory=list)
    active_task_ueids: list[UEID] = Field(default_factory=list)
    active_deliverable_ueids: list[UEID] = Field(default_factory=list)

    # ── Balancer / workload (IKIGAiStateDict-shaped)
    workload_estimate: Optional[float] = None
    capacity_estimate: Optional[float] = None
    balancer_verdict: Optional[str] = None  # OK | OVERLOAD | UNDERLOAD | RECOVER

    # ── Buffers + corrections (D12, typed)
    prospective_buffer: list[str] = Field(default_factory=list)
    retrospective_log: list[str] = Field(default_factory=list)
    corrections: list[CorrectionSignal] = Field(default_factory=list)

    # ── Override + audit (D12)
    manual_override: bool = False
    recommendation_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    audit_trail: list[OverrideRecord] = Field(default_factory=list)

    # ── Forward-compat placeholder (D7)
    is_placeholder: bool = False
    placeholder_owner: Optional[str] = None

    # ── Drift detection (§8.2, D14, D8/I9)
    drift_state: DriftState = DriftState.IN_SYNC
    sqlite_mirror_at: Optional[datetime] = None
    last_triaged_at: Optional[datetime] = None

    # ── Audit timestamps (NOT lifecycle; lifecycle lives on StatusType)
    created_at: datetime
    updated_at: datetime
    last_reviewed_at: Optional[datetime] = None

    # ── Canonical source (D8/I9: REQUIRED — markdown wins on drift)
    source_md_path: Path

    # ── Cross-cluster routing (§3.2 forward-compat)
    target_subsystem: Optional[Literal[
        "CLUSTER_PLAN", "life_tatics", "vibe_ops", "taskwarrior",
    ]] = None

    # ── Typed forward-compat (entity-specific fields live here)
    custom: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "EntityType",
    "IKIGAiRecord",
    "ScoreUnit",
    "ScoreValue",
    "StatusType",
    "UEID",
    "VectorKey",
]