"""Core package: scoring + heuristics + state machines."""

from ikigai.core.scoring.meta_vector import (
    compute_alignment_label,
    meta_vector,
)
from ikigai.core.scoring.qhe import (
    QHEComponent,
    compute_qhe,
    compute_qhe_components,
)
from ikigai.core.scoring.rice import (
    compute_rice_score,
    compute_task_priority,
)
from ikigai.core.scoring.vector_scores import (
    compute_vector_scores,
    score_course,
    score_market,
    score_passion,
    score_revenue,
    score_skill,
)

__all__ = [
    "QHEComponent",
    "compute_alignment_label",
    "compute_qhe",
    "compute_qhe_components",
    "compute_rice_score",
    "compute_task_priority",
    "compute_vector_scores",
    "meta_vector",
    "score_course",
    "score_market",
    "score_passion",
    "score_revenue",
    "score_skill",
]
