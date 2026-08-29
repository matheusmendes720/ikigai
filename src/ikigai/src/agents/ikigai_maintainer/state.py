"""State models for IKIGAi-Maintainer.

IKIGAiStateDict is the canonical state shape for the LangGraph agent.
All other modules in this package consume it.

Imports Q_HE and policy constants from the operational core.
"""
from __future__ import annotations

import datetime as dt
import math
import operator
from enum import Enum
from typing import Annotated, Literal, TypedDict

# ---------------------------------------------------------------------------
# IKIGAi vector types
# ---------------------------------------------------------------------------

VECTOR_TYPES = Literal["passion", "skill", "market", "revenue", "course"]
REGIME_STATES = Literal["PUSH", "MAINTAIN", "REDUCE", "RECOVER"]
PHASE_STATES = Literal["FUNDAÇÃO", "BUSCA", "HACKATHON", "RECUPERACAO", "OVERCLOCK"]
BALANCER_VERDICTS = Literal["OK", "OVERLOAD", "UNDERLOAD", "RECOVER"]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Threshold constants — hardcoded here; wire to vibe-ops metrics or vault feedback when available
DEFAULT_QHE_PUSH = 0.85
DEFAULT_QHE_RECOVER = 0.60
DEFAULT_WORKLOAD_OVERLOAD_FACTOR = 1.20
DEFAULT_WORKLOAD_UNDERLOAD_FACTOR = 0.50
DEFAULT_CAPACITY_HOURS_PER_DAY = 8.0
HYSTERESIS_UPGRADE_DAYS = 3
HYSTERESIS_DOWNGRADE_DAYS = 2

# Tier durations in days
TIER_DAYS: dict[str, int | None] = {
    "daily": 1,
    "weekly": 7,
    "onda": 45,
    "quarterly": 90,
    "sonho": None,  # variable
}


class PlanTier(str, Enum):
    """5-level pyramid (Sonho → Quarterly → Onda → Weekly → Daily)."""

    SONHO = "sonho"
    QUARTERLY = "quarterly"
    ONDA = "onda"
    WEEKLY = "weekly"
    DAILY = "daily"

    @property
    def expected_days(self) -> int | None:
        return TIER_DAYS.get(self.value)


class PlanVerdict(str, Enum):
    """Verdict per tier (matches ADR-006 contract)."""

    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    CONTINUE_WAVE = "CONTINUE_WAVE"
    CORRECT_TRAJECTORY = "CORRECT_TRAJECTORY"
    KILL_WAVE = "KILL_WAVE"
    ACTIVE = "ACTIVE"
    VALIDATED = "VALIDATED"
    FALSIFIED = "FALSIFIED"
    PIVOTED = "PIVOTED"
    ABANDONED = "ABANDONED"


class BalancerVerdict(str, Enum):
    """Balancer output — drives commit edge guard."""

    OK = "OK"
    OVERLOAD = "OVERLOAD"
    UNDERLOAD = "UNDERLOAD"
    RECOVER = "RECOVER"


class CorrectionSignal(TypedDict):
    """A corrective signal emitted by H1-H6 heuristics.

    Each signal has a heuristic of origin, a description, and an optional UEID
    target (for entity-level corrections).
    """

    heuristic: str  # e.g. "H1", "H3"
    signal_type: str  # e.g. "regime_change", "skill_promote", "task_prioritize"
    description: str
    target_ueid: str | None  # None = system-level
    urgency: Literal["low", "medium", "high", "critical"]
    metadata: dict


# ---------------------------------------------------------------------------
# Root state dict
# ---------------------------------------------------------------------------


class IKIGAiStateDict(TypedDict, total=False):
    """Canonical state for the IKIGAi-Maintainer LangGraph.

    This TypedDict is the single source of state shape for all nodes.
    Annotated fields use `operator.add` to accumulate values across iterations.

    LangGraph ephemeral state: held in working memory during graph execution.
    Checkpointed to SQLite at node boundaries via SqliteSaver.
    """

    # Identity
    cycle_id: str
    cycle_start: str  # ISO date
    cycle_end: str  # ISO date
    iteration: int
    last_step: str

    # Regime FSM (H1)
    regime_state: REGIME_STATES
    q_he_score: float
    days_in_regime: int
    is_hysteresis_active: bool

    # Phase FSM (H2)
    phase: PHASE_STATES
    phase_iteration: int
    phase_converged: bool
    phase_weights: dict[str, float]

    # IKIGAi 5-vector scores
    vector_scores: dict[VECTOR_TYPES, float]
    meta_vector_score: float

    # UEID hierarchy (Dream → Goal → Objective → Project → Task)
    active_dream_ueid: str | None
    active_goal_ueids: list[str]
    active_objective_ueids: list[str]
    active_project_ueids: list[str]
    active_task_ueids: list[str]

    # Balancer (shared between channels)
    workload_estimate: float
    capacity_estimate: float
    balancer_verdict: BALANCER_VERDICTS

    # Prospective channel — forward-drafting
    prospective_buffer: Annotated[list[str], operator.add]

    # Retrospective channel — backward-aggregation
    retrospective_log: Annotated[list[str], operator.add]

    # Corrections emitted by H1-H6
    corrections: Annotated[list[CorrectionSignal], operator.add]

    # Kill switch — halts graph if True
    kill_switch_triggered: bool
    terminated: bool

    # Error channel (B5.1-F3) — populated when a wrapped node raises;
    # error_node consumes these to produce a failed commit_summary.
    originating_node: str
    error_type: str
    error_message: str
    traceback_str: str
    error_traceback: str  # written by error_node
    commit_summary: str  # written by commit_node on success, error_node on failure

    # Chat mode — message history accumulated across turns
    messages: Annotated[list[dict], operator.add]  # [{"role": "user"|"agent", "content": str}]
    user_input: str | None  # scratchpad for current turn input


# ---------------------------------------------------------------------------
# Helper: compute meta-vector (hybrid mean)
# ---------------------------------------------------------------------------


def compute_meta_vector(
    scores: dict[VECTOR_TYPES, float],
    weights: dict[VECTOR_TYPES, float] | None = None,
    w_geo: float = 0.6,
    w_harm: float = 0.4,
) -> float:
    """Compute IKIGAi meta-vector using hybrid mean.

    60% geometric mean (balances vectors) + 40% harmonic mean (penalizes lows).
    """
    if not scores:
        return 0.0

    active = {k: v for k, v in scores.items() if v > 0}
    if not active:
        return 0.0

    # Normalize weights
    _weights = weights or {k: 1.0 for k in active}
    # Guard against string values leaking in (langgraph state merge quirk)
    _weights = {k: float(v) if isinstance(v, (int, str)) else v for k, v in _weights.items()}
    total_w = sum(_weights.values())
    w_norm = {k: _weights.get(k, 1.0) / total_w for k in active}

    # Geometric mean
    log_sum = sum(w_norm[k] * math.log(max(v, 0.01)) for k, v in active.items())
    geo = math.exp(log_sum)

    # Harmonic mean
    harm_sum = sum(w_norm[k] / max(v, 0.01) for k, v in active.items())
    harm = 1.0 / harm_sum if harm_sum > 0 else 0.0

    return w_geo * geo + w_harm * harm
