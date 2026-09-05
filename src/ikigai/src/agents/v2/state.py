"""State models for IKIGAi-Maintainer v2.

IKIGAiStateDict is the canonical state shape for the LangGraph agent.
All other modules in this package consume it.

MATH NOTE: compute_meta_vector is guarded in if False: — it is a
FORBIDDEN_FUNCTION per ADR-013 drift detector (compute_meta_vector name
appears in FORBIDDEN_FUNCTIONS). The function body is preserved as a
historical artifact but never executed.
"""

from __future__ import annotations

import operator
from enum import Enum
from typing import Annotated, Any, Literal, NotRequired, TypedDict

# ---------------------------------------------------------------------------
# IKIGAi vector types
# ---------------------------------------------------------------------------

VECTOR_TYPES = Literal["passion", "skill", "market", "revenue", "course"]
REGIME_STATES = Literal["PUSH", "MAINTAIN", "REDUCE", "RECOVER"]
PHASE_STATES = Literal["FUNDAÇÃO", "BUSCA", "HACKATHON", "RECUPERACAO", "OVERCLOCK"]
BALANCER_VERDICTS = Literal["OK", "OVERLOAD", "UNDERLOAD", "RECOVER"]

# ---------------------------------------------------------------------------
# Constants — REMOVED 2026-09-04 (W3.2)
# ---------------------------------------------------------------------------
# All algorithm-tuning constants formerly here have been migrated to the
# prompt-template configuration at:
#     src/ikigai/src/agents/v2/prompts/algorithm_constants.json
# consumed via:
#     src/ikigai/src/agents/v2/prompts/load_constants.py
#
# Per ADR-019 (forthcoming — see dcode-harness-TASKS.md W5.2): algorithm
# tuning happens ONLY by editing algorithm_constants.json. New Python
# DEFAULT_* constants in src/ikigai/src/agents/v2/*.py are FORBIDDEN.
# Drift detector enforces this invariant — see
# src/ikigai/tests/test_canonical_scope.py :: test_no_algorithm_constants_in_agent_code.
#
# Removed (with their old values for reference):
#   DEFAULT_QHE_PUSH                  = 0.85
#   DEFAULT_QHE_RECOVER               = 0.60
#   DEFAULT_WORKLOAD_OVERLOAD_FACTOR  = 1.20
#   DEFAULT_WORKLOAD_UNDERLOAD_FACTOR = 0.50
#   DEFAULT_CAPACITY_HOURS_PER_DAY    = 8.0
#   HYSTERESIS_UPGRADE_DAYS           = 3
#   HYSTERESIS_DOWNGRADE_DAYS         = 2

TIER_DAYS: dict[str, int | None] = {
    "daily": 1,
    "weekly": 7,
    "onda": 45,
    "quarterly": 90,
    "sonho": None,
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
    """Verdict per tier."""

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
    """A corrective signal emitted by heuristics."""

    heuristic: str
    signal_type: str
    description: str
    target_ueid: str | None
    urgency: Literal["low", "medium", "high", "critical"]
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Root state dict
# ---------------------------------------------------------------------------


class IKIGAiStateDict(TypedDict):
    """Canonical state for the IKIGAi-Maintainer LangGraph v2."""

    # ---- Required identity fields ------------------------------
    cycle_id: str
    cycle_start: str
    cycle_end: str
    iteration: int

    # ---- Optional state --------------------------------------
    last_step: NotRequired[str]

    # Regime FSM (H1)
    regime_state: NotRequired[REGIME_STATES]
    q_he_score: NotRequired[float]
    days_in_regime: NotRequired[int]
    is_hysteresis_active: NotRequired[bool]

    # Phase FSM (H2)
    phase: NotRequired[PHASE_STATES]
    phase_iteration: NotRequired[int]
    phase_converged: NotRequired[bool]
    phase_weights: NotRequired[dict[str, float]]

    # IKIGAi 5-vector scores
    vector_scores: NotRequired[dict[VECTOR_TYPES, float]]
    meta_vector_score: NotRequired[float]

    # UEID hierarchy
    active_dream_ueid: NotRequired[str | None]
    active_goal_ueids: NotRequired[list[str]]
    active_objective_ueids: NotRequired[list[str]]
    active_project_ueids: NotRequired[list[str]]
    active_task_ueids: NotRequired[list[str]]

    # Balancer
    workload_estimate: NotRequired[float]
    capacity_estimate: NotRequired[float]
    balancer_verdict: NotRequired[BALANCER_VERDICTS]

    # Prospective channel
    prospective_buffer: NotRequired[Annotated[list[str], operator.add]]

    # Retrospective channel
    retrospective_log: NotRequired[Annotated[list[str], operator.add]]

    # Corrections
    corrections: NotRequired[Annotated[list[CorrectionSignal], operator.add]]

    # Kill switch
    kill_switch_triggered: NotRequired[bool]
    terminated: NotRequired[bool]

    # Error channel
    originating_node: NotRequired[str]
    error_type: NotRequired[str]
    error_message: NotRequired[str]
    traceback_str: NotRequired[str]
    error_traceback: NotRequired[str]
    commit_summary: NotRequired[str]

    # Chat mode
    messages: NotRequired[Annotated[list[dict[str, Any]], operator.add]]
    user_input: NotRequired[str | None]

    # ---- Plan A Task 8 — tag_and_persist -------------------------------
    # Fields populated by upstream planning node and consumed by
    # tag_and_persist_node (src/ikigai/src/agents/v2/nodes/tag_and_persist.py).
    # proposed_entity is a BasePlanContract instance (Sonho/Objetivo/Meta/Projeto/
    # Entrega/Tarefa); vault_path is the relative path under vault/ where it
    # will be written; actor tags the write for the audit log (drift
    # invariant g); persisted is set to True after successful vault_write.
    proposed_entity: NotRequired[Any]  # BasePlanContract — kept Any to avoid import cycle
    vault_path: NotRequired[str]
    actor: NotRequired[Literal["user", "agent", "system"]]
    persisted: NotRequired[bool]

    # ---- surface_intentions output (W3.5) ------------------------------
    # Fields populated by surface_intentions_node after commit completes.
    # user_suggestions is the primary output (3-5 pt-BR suggestion strings).
    user_suggestions: NotRequired[list[str]]
    suggestions_count: NotRequired[int]
    suggestions_language: NotRequired[Literal["pt-BR", "en"]]

    # ---- Sub-agent dispatch (ADR-026 + ADR-027 R5.14) ---------------------
    # dispatch_depth tracks the recursion level for sub-agent fan-out
    # (per ADR-027 R5.14). Parent (root) cycle = 0; child = 1;
    # grandchild = 2; etc. Cap = SUBAGENT_MAX_DISPATCH_DEPTH. Not all
    # skills use dispatch (daily has no children) — field is NotRequired.
    dispatch_depth: NotRequired[int]


# ---------------------------------------------------------------------------
# Plan D — Meta-planner state keys (Task C.1)
# All keys optional (TypedDict NotRequired pattern). Populated by:
#   - observe (intent detection → plan_intent_hint) — Task D.1
#   - classify_intent (→ intent_classification) — Task B.1
#   - fetch_context (→ memory_refs, folder_reads, hierarchy_matches) — Task B.2
#   - generate_proposal (→ proposal, proposal_pending) — Task B.3
#   - proposal_executor (→ execution_report) — Task B.4
# ---------------------------------------------------------------------------


class MetaPlanStateDict(TypedDict, total=False):
    """Subset of IKIGAiStateDict used by the meta-planner subgraph."""

    # Input
    user_request: str
    # Outputs from each node
    plan_intent_hint: str  # populated by observe (Task D.1)
    intent_classification: Any  # IntentClassification — avoid circular import
    memory_refs: list[Any]  # list[MemoryRef]
    folder_reads: list[Any]  # list[FolderReadOp]
    hierarchy_matches: Any  # HierarchyMatch
    proposal: Any  # Proposal — the central artifact
    proposal_pending: bool
    execution_report: Any  # ExecutionReport


# Extend IKIGAiStateDict with the meta-planner keys via inheritance.
# Use a new class to keep backward compatibility for existing consumers.
class IKIGAiStateDictWithMetaPlan(IKIGAiStateDict, MetaPlanStateDict):
    """IKIGAiStateDict extended with meta-planner keys (Plan D)."""


# Alias for cleaner imports
MetaPlanEnabledState = IKIGAiStateDictWithMetaPlan


# ---------------------------------------------------------------------------
# compute_meta_vector — REMOVED from v2 (FORBIDDEN_FUNCTION per ADR-013).
# The stub `_stub_meta_vector` in score_vectors.py provides an inline
# placeholder. Full historical implementation available in the archive at:
# archive/recovered-agentic-2026-09-01/src_ikigai_src_agents/ikigai_maintainer/state.py
# Phase 8.2 replaces with prompt-chain equivalent.
# ---------------------------------------------------------------------------
pass
