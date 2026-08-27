"""Heuristics sub-package: 6 deterministic algorithms."""

from ikigai.core.heuristics.regime import (
    compute_regime,
    RegimeDecision,
    apply_hysteresis,
)
from ikigai.core.heuristics.phase_pivot import (
    compute_phase,
    PhaseDecision,
)
from ikigai.core.heuristics.weight_ucb import (
    recalibrate_weight_ucb,
    recalibrate_all_weights,
)
from ikigai.core.heuristics.opportunity_fit import (
    compute_opportunity_fit,
    classify_opportunity,
)
from ikigai.core.heuristics.skill_velocity import (
    should_promote_skill,
    detect_stagnation,
)
from ikigai.core.heuristics.cross_priority import (
    compute_weighted_priority,
    rank_tasks,
)

__all__ = [
    "compute_regime",
    "RegimeDecision",
    "apply_hysteresis",
    "compute_phase",
    "PhaseDecision",
    "recalibrate_weight_ucb",
    "recalibrate_all_weights",
    "compute_opportunity_fit",
    "classify_opportunity",
    "should_promote_skill",
    "detect_stagnation",
    "compute_weighted_priority",
    "rank_tasks",
]
