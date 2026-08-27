"""IKIGAi-Maintainer — dual-channel LangGraph agent for the IKIGAi meta-brain."""

from .state import (
    IKIGAiStateDict,
    CorrectionSignal,
    TIER_DAYS,
    PlanTier,
    PlanVerdict,
    BalancerVerdict,
    compute_meta_vector,
    REGIME_STATES,
    PHASE_STATES,
    BALANCER_VERDICTS,
    VECTOR_TYPES,
    DEFAULT_QHE_PUSH,
    DEFAULT_QHE_RECOVER,
    DEFAULT_WORKLOAD_OVERLOAD_FACTOR,
    DEFAULT_WORKLOAD_UNDERLOAD_FACTOR,
    DEFAULT_CAPACITY_HOURS_PER_DAY,
    HYSTERESIS_UPGRADE_DAYS,
    HYSTERESIS_DOWNGRADE_DAYS,
)
from .graph import make_ikigai_graph

__all__ = [
    # State
    "IKIGAiStateDict",
    "CorrectionSignal",
    "TIER_DAYS",
    "PlanTier",
    "PlanVerdict",
    "BalancerVerdict",
    "compute_meta_vector",
    # Type aliases
    "REGIME_STATES",
    "PHASE_STATES",
    "BALANCER_VERDICTS",
    "VECTOR_TYPES",
    # Constants
    "DEFAULT_QHE_PUSH",
    "DEFAULT_QHE_RECOVER",
    "DEFAULT_WORKLOAD_OVERLOAD_FACTOR",
    "DEFAULT_WORKLOAD_UNDERLOAD_FACTOR",
    "DEFAULT_CAPACITY_HOURS_PER_DAY",
    "HYSTERESIS_UPGRADE_DAYS",
    "HYSTERESIS_DOWNGRADE_DAYS",
    # Graph
    "make_ikigai_graph",
]
