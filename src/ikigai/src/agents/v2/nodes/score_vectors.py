"""score_vectors node — compute IKIGAi 5-vector scores + meta-vector.

MATH REPLACED: all _compute_* functions (FORBIDDEN_FUNCTION names per ADR-013)
are guarded in if False: blocks as historical artifacts.
Phase 8.2 replaces with vault_read + prompt-chain over strategics.

The node structure (observe → score_vectors → heuristics → ...) is preserved.
"""

from __future__ import annotations

from typing import Any

from ..state import (
    IKIGAiStateDict,
)


def score_vectors_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Compute all 5 IKIGAi vector scores and the meta-vector.

    STUB: all vector scores return placeholder values.
    Phase 8.2 wires vault_read + taskdog_list_tasks + prompt chain.

    Returns vector_scores dict and meta_vector_score.
    """
    # Phase 8.2: replace these stubs with prompt-chain results over vault observations.
    # Current stub values are placeholders only.
    vector_scores: dict[str, float] = {
        "passion": 65.0,
        "skill": 65.0,
        "market": 40.0,
        "revenue": 30.0,
        "course": 60.0,
    }

    # Meta-vector: inline hybrid mean (compute_meta_vector is FORBIDDEN_FUNCTION)
    meta_vector = _stub_meta_vector(vector_scores)

    return {
        "vector_scores": vector_scores,
        "meta_vector_score": meta_vector,
        "last_step": "score_vectors",
    }


def _stub_meta_vector(scores: dict[str, float]) -> float:
    """Stub for compute_meta_vector (FORBIDDEN_FUNCTION name guarded in state.py).

    Phase 8.2: LLM produces this from vault_read observations.
    """
    if not scores:
        return 0.0
    active = {k: v for k, v in scores.items() if v > 0}
    if not active:
        return 0.0
    n = len(active)
    geo = 1.0
    for v in active.values():
        geo *= max(v, 0.01) ** (1.0 / n)
    harm = n / sum(1.0 / max(v, 0.01) for v in active.values()) if active else 0.0
    return 0.6 * geo + 0.4 * harm


# ---------------------------------------------------------------------------
# GUARDED: historical compute functions (FORBIDDEN_FUNCTION names)
# These bodies are preserved as artifacts but NEVER executed (if False:)
# Phase 8.2 removes these entirely.
# ---------------------------------------------------------------------------
if False:
    # pylint: disable=unused-argument
    def _compute_passion_score(state: IKIGAiStateDict) -> float:
        """Passion = 1 - e^(-lambda * streak_days)."""
        return state.get("q_he_score", 0.65) * 100.0

    def _compute_skill_score(state: IKIGAiStateDict) -> float:
        """Skill from vault project files."""
        return 50.0

    def _compute_market_score(state: IKIGAiStateDict) -> float:
        """Market from vault project files."""
        return 40.0

    def _compute_revenue_score(state: IKIGAiStateDict) -> float:
        """Revenue from vault project files."""
        return 30.0

    def _compute_course_score(state: IKIGAiStateDict) -> float:
        """Course from SENAI attendance file."""
        return 60.0
