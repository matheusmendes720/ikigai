"""Heuristics sub-package: 6 deterministic algorithms."""

from ikigai.core.heuristics.cross_priority import (
    compute_weighted_priority,
    rank_tasks,
)
from ikigai.core.heuristics.opportunity_fit import (
    classify_opportunity,
    compute_opportunity_fit,
)
from ikigai.core.heuristics.phase_pivot import (
    PhaseDecision,
    compute_phase,
)
from ikigai.core.heuristics.regime import (
    RegimeDecision,
    apply_hysteresis,
    compute_regime,
)
from ikigai.core.heuristics.skill_velocity import (
    detect_stagnation,
    should_promote_skill,
)
from ikigai.core.heuristics.weight_ucb import (
    recalibrate_all_weights,
    recalibrate_weight_ucb,
)

__all__ = [
    "PhaseDecision",
    "RegimeDecision",
    "apply_hysteresis",
    "classify_opportunity",
    "compute_opportunity_fit",
    "compute_phase",
    "compute_regime",
    "compute_weighted_priority",
    "detect_stagnation",
    "rank_tasks",
    "recalibrate_all_weights",
    "recalibrate_weight_ucb",
    "should_promote_skill",
]
