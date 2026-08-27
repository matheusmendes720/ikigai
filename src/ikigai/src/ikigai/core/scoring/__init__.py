"""Scoring sub-package: vector scores, meta-vetor, Q_HE, RICE."""

from ikigai.core.scoring.vector_scores import (
    score_passion,
    score_skill,
    score_market,
    score_revenue,
    score_course,
    compute_vector_scores,
)
from ikigai.core.scoring.meta_vector import (
    meta_vector,
    compute_alignment_label,
)
from ikigai.core.scoring.qhe import (
    compute_qhe,
    compute_qhe_components,
    QHEComponent,
)
from ikigai.core.scoring.rice import (
    compute_rice_score,
    compute_task_priority,
)

__all__ = [
    "score_passion",
    "score_skill",
    "score_market",
    "score_revenue",
    "score_course",
    "compute_vector_scores",
    "meta_vector",
    "compute_alignment_label",
    "compute_qhe",
    "compute_qhe_components",
    "QHEComponent",
    "compute_rice_score",
    "compute_task_priority",
]
