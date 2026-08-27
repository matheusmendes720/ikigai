"""State models for PAE-Maintainer.

Uses Pydantic v2 with strict types. State persisted to vibe_ops.db
(pae_state table, added in migration 005).

Source: .omo/plans/agentic-markdown-system.md T9
Linked: ADR-006 (period schema), operational constants (Q_HE + 5x3x3)
"""
from __future__ import annotations

import datetime as _dt
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Import Q_HE + 5x3x3 constants from operational (single source of truth).
# operational.constants provides PAVConstants (QHE thresholds, weights, learning rate).
# operational.enums provides Period (MANHA/TARDE/NOITE) and PolicyState (4-state FSM).
try:
    from operational.constants import PAVConstants as PAEConstants  # type: ignore[attr-defined]
    from operational.enums import (  # type: ignore[attr-defined]
        Period as OperationalPeriod,
        PolicyState,
    )
except ImportError:  # pragma: no cover - operational not on PYTHONPATH
    PAEConstants = None  # type: ignore[assignment]
    OperationalPeriod = None  # type: ignore[assignment]
    PolicyState = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Constants — derived from operational PAVConstants when available, else default.
# These are the canonical names used by the PAE-Maintainer nodes.
# ---------------------------------------------------------------------------

# Default values match PAVConstants.DEFAULT from operational (single source of truth).
DEFAULT_QHE_PUSH_THRESHOLD: float = 0.85
"""QHE threshold above which policy is PUSH (Points_of_premisses §4)."""

DEFAULT_QHE_RECOVER_THRESHOLD: float = 0.60
"""QHE threshold below which policy is RECOVER (Points_of_premisses §4)."""

DEFAULT_POLICY_UPGRADE_DAYS: int = 3
"""Consecutive OK days before policy upgrade (histerese anti-bouncing)."""

DEFAULT_WORKLOAD_OVERLOAD_FACTOR: float = 1.20
"""Multiplier of capacity that triggers OVERLOAD verdict (>=)."""

DEFAULT_WORKLOAD_UNDERLOAD_FACTOR: float = 0.50
"""Multiplier of capacity that triggers UNDERLOAD verdict (<=)."""

DEFAULT_CAPACITY_HOURS_PER_DAY: float = 8.0
"""Baseline capacity in hours/day (PAVConstants ENV-aligned)."""

# Tier-to-day-counts (matches _PERIOD_DAYS in models/period_report.py + sonho extension).
TIER_DAYS: dict[str, int | None] = {
    "daily": 1,
    "weekly": 7,
    "onda": 45,
    "quarterly": 90,
    "sonho": None,  # variable
}


class PlanTier(str, Enum):
    """5-level pyramid (Sonho -> Quarterly -> Onda -> Weekly -> Daily)."""

    SONHO = "sonho"  # 6-12 months, FalsifiableHypothesis
    QUARTERLY = "quarterly"  # 90 days, Test de Fogo
    ONDA = "onda"  # 45 days uteis, Route Correction
    WEEKLY = "weekly"  # 7 days, Policy Adjustment
    DAILY = "daily"  # 1 day, Completion Rate

    @property
    def expected_days(self) -> int | None:
        """Return expected duration of this tier in days (None for sonho)."""
        return TIER_DAYS.get(self.value)


class PlanVerdict(str, Enum):
    """Verdict enums per tier (matches ADR-006 contract).

    Verdict vocabulary differs per tier:
      - DAILY / WEEKLY / QUARTERLY: PASS / PARTIAL / FAIL
      - ONDA: CONTINUE_WAVE / CORRECT_TRAJECTORY / KILL_WAVE
      - SONHO: ACTIVE / VALIDATED / FALSIFIED / PIVOTED / ABANDONED
    """

    # Daily / Weekly / Quarterly
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    # Onda
    CONTINUE_WAVE = "CONTINUE_WAVE"
    CORRECT_TRAJECTORY = "CORRECT_TRAJECTORY"
    KILL_WAVE = "KILL_WAVE"
    # Sonho
    ACTIVE = "ACTIVE"
    VALIDATED = "VALIDATED"
    FALSIFIED = "FALSIFIED"
    PIVOTED = "PIVOTED"
    ABANDONED = "ABANDONED"


class BalancerVerdict(str, Enum):
    """Output verdict of the balance node — drives commit edge guard.

    OK:        within bounds, commit allowed.
    OVERLOAD:  workload > overload factor, kill-switch triggered (no commit).
    UNDERLOAD: workload < underload factor, expansion candidate.
    RECOVER:   Q_HE below recover threshold, mandatory stop.
    """

    OK = "OK"
    OVERLOAD = "OVERLOAD"
    UNDERLOAD = "UNDERLOAD"
    RECOVER = "RECOVER"


class PlanNode(BaseModel):
    """A single node in the PAE hierarchy (templates or filled reports)."""

    model_config = ConfigDict(frozen=False, extra="allow")

    id: str
    tier: PlanTier
    parent_id: str | None = None
    title: str
    verdict: PlanVerdict | None = None
    verdict_score: float = Field(default=0.0, ge=0.0, le=1.0)
    date_start: _dt.date | None = None
    date_end: _dt.date | None = None
    ikigai_vector: Literal["passion", "skill", "market", "revenue"] | None = None
    children: list[str] = Field(default_factory=list)  # IDs of child nodes
    metadata: dict[str, Any] = Field(default_factory=dict)
    updated_at: _dt.datetime = Field(default_factory=lambda: _dt.datetime.utcnow())


class ProspectiveNode(BaseModel):
    """A node in the prospective (forward-drafting) channel."""

    model_config = ConfigDict(frozen=False)

    target_tier: PlanTier
    target_window_days: int
    candidates: list[PlanNode] = Field(default_factory=list)
    drafted_at: _dt.datetime | None = None
    next_action: str | None = None


class RetrospectiveNode(BaseModel):
    """A node in the retrospective (backward-aggregating) channel."""

    model_config = ConfigDict(frozen=False)

    period_start: _dt.date
    period_end: _dt.date
    children_aggregated: list[PlanNode] = Field(default_factory=list)
    aggregate_score: float = Field(default=0.0, ge=0.0, le=1.0)
    aggregate_verdict: PlanVerdict | None = None
    gaps: list[str] = Field(default_factory=list)
    suggested_corrections: list[str] = Field(default_factory=list)


class BalancerState(BaseModel):
    """State snapshot from the balance node — controls commit edge guard.

    Shared between Prospective and Retrospective channels for overload safety.
    """

    model_config = ConfigDict(frozen=False)

    workload_estimate: float = 0.0  # hours / day
    capacity_estimate: float = DEFAULT_CAPACITY_HOURS_PER_DAY  # hours / day
    qhe_score: float = Field(
        default=0.65, ge=0.0, le=1.0
    )  # median policy target
    is_histerese_active: bool = False
    days_in_current_state: int = 1
    state: BalancerVerdict = BalancerVerdict.OK
    reason: str = ""

    # Thresholds (configurable per-instance; defaults come from PAVConstants).
    overload_factor: float = DEFAULT_WORKLOAD_OVERLOAD_FACTOR
    underload_factor: float = DEFAULT_WORKLOAD_UNDERLOAD_FACTOR
    qhe_recover_threshold: float = DEFAULT_QHE_RECOVER_THRESHOLD
    histerese_upgrade_days: int = DEFAULT_POLICY_UPGRADE_DAYS


class PAEState(BaseModel):
    """Root state for the PAE-Maintainer graph.

    Holds the current cycle identity, channel snapshots, balancer, and
    working set of plan nodes. Mutated in-place by nodes; persisted to
    pae_state table in vibe_ops.db via commit_node.
    """

    model_config = ConfigDict(frozen=False, validate_assignment=False)

    # Identity
    cycle_id: str
    cycle_start: _dt.date
    cycle_end: _dt.date

    # Channels
    prospective: ProspectiveNode | None = None
    retrospective: RetrospectiveNode | None = None

    # Balancer (shared by both channels for overload safety)
    balancer: BalancerState = Field(default_factory=BalancerState)

    # Working set
    active_nodes: list[PlanNode] = Field(default_factory=list)
    archive: list[PlanNode] = Field(default_factory=list)

    # Meta
    iteration: int = 0
    last_step: str = "init"
    terminated: bool = False
    kill_switch_triggered: bool = False

    def current_tier(self, today: _dt.date | None = None) -> PlanTier:
        """Infer current planning tier from cycle dates.

        Fractions of cycle progress map to:
          0-5%   -> SONHO (pre-cycle, planning forward)
          5-30%  -> QUARTERLY
          30-65% -> ONDA
          65-95% -> WEEKLY
          95%+   -> DAILY (closeout)
        """
        ref = today or _dt.date.today()
        if ref < self.cycle_start:
            return PlanTier.SONHO
        if ref > self.cycle_end:
            return PlanTier.DAILY  # post-cycle, planning next
        total = (self.cycle_end - self.cycle_start).days
        if total <= 0:
            return PlanTier.DAILY
        elapsed = (ref - self.cycle_start).days
        frac = elapsed / total
        if frac < 0.05:
            return PlanTier.SONHO
        if frac < 0.30:
            return PlanTier.QUARTERLY
        if frac < 0.65:
            return PlanTier.ONDA
        if frac < 0.95:
            return PlanTier.WEEKLY
        return PlanTier.DAILY
