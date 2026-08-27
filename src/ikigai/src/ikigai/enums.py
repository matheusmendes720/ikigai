"""IKIGAi enums: EntityType, VectorType, RegimeType, Phase, StatusType, ScoreUnit.

All enums are designed for **fractal extension**:
- VectorType: 5 canonical + string-extensible for sub-vectors (e.g., "skill.python")
- EntityType: open enum for forward-compat placeholders
- StatusType: per-entity state machines
"""

from __future__ import annotations

from enum import Enum


class EntityType(str, Enum):
    """Entity types in the IKIGAi plan hierarchy (polymorphic discriminator).

    Forward-compat: 'project', 'task', 'routine', 'habit', 'skill', etc.
    are placeholders that can be claimed by future subsystems (CLUSTER_PROJ,
    CLUSTER_PLAN, etc.).
    """

    # Plan hierarchy (canonical)
    DREAM = "dream"
    GOAL = "goal"
    OBJECTIVE = "objective"
    PROJECT = "project"
    TASK = "task"
    DELIVERABLE = "deliverable"

    # Operational (forward-compat)
    ROUTINE = "routine"
    BLOCK = "block"
    RITUAL = "ritual"
    POMODORO = "pomodoro"
    HABIT = "habit"

    # Study (forward-compat)
    SKILL = "skill"
    TOPIC = "topic"
    MATERIAL = "material"
    SESSION = "session"

    # IKIGAi core
    VECTOR = "vector"
    PROFILE = "profile"

    # Meta
    JOURNAL = "journal"
    NOTE = "note"


class VectorType(str, Enum):
    """The 5 canonical IKIGAi vectors + sub-vector support.

    The 5 canonical vectors (per `ikigai_4_vectors.md`):
    - PASSION: energy, meaning, habits
    - SKILL: torque técnico, study
    - MARKET: tração no mundo, opportunities
    - REVENUE: fluxo de caixa
    - COURSE: 5th contextual (external/obligation)

    Sub-vectors (fractal): use string format like 'skill.python', 'market.freelance'.
    Pydantic validates the prefix matches a canonical vector.
    """

    PASSION = "passion"
    SKILL = "skill"
    MARKET = "market"
    REVENUE = "revenue"
    COURSE = "course"

    @property
    def is_external(self) -> bool:
        """External vectors (course) vs agency vectors (passion/skill/market/revenue)."""
        return self == VectorType.COURSE

    @classmethod
    def canonical_names(cls) -> list[str]:
        return [v.value for v in cls]


class RegimeType(str, Enum):
    """4-state regime FSM (PUSH ↔ MAINTAIN ↔ REDUCE ↔ RECOVER).

    Setpoints (from meta_heuristics.md §1.4):
    - PUSH: hardwork=4h, pause=10min, sleep=7.5h, Q_HE_target=0.85
    - MAINTAIN: hardwork=2.5h, pause=15min, sleep=8h, Q_HE_target=0.65
    - REDUCE: hardwork=1.5h, pause=20min, sleep=8.5h, Q_HE_target=0.45
    - RECOVER: hardwork=0.5h, pause=30min, sleep=9h, Q_HE_target=0.25
    """

    PUSH = "push"
    MAINTAIN = "maintain"
    REDUCE = "reduce"
    RECOVER = "recover"

    @property
    def hardwork_budget_h(self) -> float:
        return {
            RegimeType.PUSH: 4.0,
            RegimeType.MAINTAIN: 2.5,
            RegimeType.REDUCE: 1.5,
            RegimeType.RECOVER: 0.5,
        }[self]

    @property
    def pause_min(self) -> int:
        return {
            RegimeType.PUSH: 10,
            RegimeType.MAINTAIN: 15,
            RegimeType.REDUCE: 20,
            RegimeType.RECOVER: 30,
        }[self]

    @property
    def sleep_target_h(self) -> float:
        return {
            RegimeType.PUSH: 7.5,
            RegimeType.MAINTAIN: 8.0,
            RegimeType.REDUCE: 8.5,
            RegimeType.RECOVER: 9.0,
        }[self]

    @property
    def qhe_target(self) -> float:
        return {
            RegimeType.PUSH: 0.85,
            RegimeType.MAINTAIN: 0.65,
            RegimeType.REDUCE: 0.45,
            RegimeType.RECOVER: 0.25,
        }[self]

    @property
    def c_comp_target(self) -> float:
        return {
            RegimeType.PUSH: 0.90,
            RegimeType.MAINTAIN: 0.85,
            RegimeType.REDUCE: 0.75,
            RegimeType.RECOVER: 0.65,
        }[self]


class Phase(str, Enum):
    """5-phase pivot FSM (FUNDAÇÃO → BUSCA → HACKATHON → RECUPERACAO → OVERCLOCKING)."""

    FUNDACAO = "fundacao"
    BUSCA = "busca"
    HACKATHON = "hackathon"
    RECUPERACAO = "recuperacao"
    OVERCLOCKING = "overclocking"

    @property
    def vector_weights(self) -> dict[str, float]:
        """Default vector weights for this phase (snapshot at phase entry)."""
        return {
            Phase.FUNDACAO: {"passion": 0.15, "skill": 0.40, "market": 0.15, "revenue": 0.10, "course": 0.20},
            Phase.BUSCA: {"passion": 0.10, "skill": 0.15, "market": 0.45, "revenue": 0.20, "course": 0.10},
            Phase.HACKATHON: {"passion": 0.10, "skill": 0.20, "market": 0.20, "revenue": 0.40, "course": 0.10},
            Phase.RECUPERACAO: {"passion": 0.50, "skill": 0.10, "market": 0.05, "revenue": 0.05, "course": 0.30},
            Phase.OVERCLOCKING: {"passion": 0.15, "skill": 0.15, "market": 0.15, "revenue": 0.50, "course": 0.05},
        }[self]


class ClusterType(str, Enum):
    """Cluster (subsystem) types — used for per-cluster regime in fractal regime."""

    PLAN = "plan"
    PROJ = "proj"
    STUDY = "study"
    IKIGAI = "ikigai"
    HABIT = "habit"


class AlignmentLabel(str, Enum):
    """Alignment label derived from meta-vetor score (0-100)."""

    ALIGNED = "aligned"  # >= 75
    CONVERGING = "converging"  # [50, 75)
    MISALIGNED = "misaligned"  # [25, 50)
    CRITICAL = "critical"  # < 25

    @classmethod
    def from_score(cls, score: float) -> "AlignmentLabel":
        if score >= 75:
            return cls.ALIGNED
        if score >= 50:
            return cls.CONVERGING
        if score >= 25:
            return cls.MISALIGNED
        return cls.CRITICAL


class StatusType(str, Enum):
    """Generic status type (per-entity state machines are more specific).

    This is the **base** status set. Entity-specific state machines (Dream,
    Goal, etc.) extend this.
    """

    DRAFT = "draft"
    SEED = "seed"
    PLANNED = "planned"
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    COMPLETED = "completed"
    ACHIEVED = "achieved"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    ABANDONED = "abandoned"
    ARCHIVED = "archived"
    MASTERED = "mastered"


class SourceType(str, Enum):
    """How an entity was created."""

    USER = "user"
    CLI = "cli"
    IMPORTED = "imported"
    PLACEHOLDER = "placeholder"
    MIGRATED = "migrated"


__all__ = [
    "EntityType",
    "VectorType",
    "RegimeType",
    "Phase",
    "ClusterType",
    "AlignmentLabel",
    "StatusType",
    "SourceType",
]
