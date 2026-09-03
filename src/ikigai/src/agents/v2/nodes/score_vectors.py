"""score_vectors node — compute IKIGAi 5-vector scores + meta-vector.

PHASE 8.2: calls 5 vector prompt templates + meta_vector via LLM prompt chain.
Falls back to deterministic stubs in IKIGAI_FAKE_LLM=1 mode.
"""

from __future__ import annotations

from typing import Any

from ..prompts.score_course_observation import render_score_course_observation
from ..prompts.score_market_observation import render_score_market_observation
from ..prompts.score_meta_vector_observation import render_score_meta_vector_observation
from ..prompts.score_passion_observation import render_score_passion_observation
from ..prompts.score_revenue_observation import render_score_revenue_observation
from ..prompts.score_skill_observation import render_score_skill_observation
from ..state import IKIGAiStateDict


def score_vectors_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Compute all 5 IKIGAi vector scores and the meta-vector via prompt chain.

    PHASE 8.2: calls render_*_observation for each vector via LLM.
    Falls back to deterministic stubs when IKIGAI_FAKE_LLM=1.

    Returns vector_scores dict and meta_vector_score.
    """
    vault_root = str(state.get("vault_root", ""))
    prompt_state = {"vault_root": vault_root}

    # Call each vector scorer
    passion_obs = render_score_passion_observation(prompt_state)
    skill_obs = render_score_skill_observation(prompt_state)
    market_obs = render_score_market_observation(prompt_state)
    revenue_obs = render_score_revenue_observation(prompt_state)
    course_obs = render_score_course_observation(prompt_state)
    meta_obs = render_score_meta_vector_observation(prompt_state)

    vector_scores: dict[str, float] = {
        "passion": float(passion_obs.get("passion_score", 65)),
        "skill": float(skill_obs.get("skill_score", 65)),
        "market": float(market_obs.get("market_score", 40)),
        "revenue": float(revenue_obs.get("revenue_score", 30)),
        "course": float(course_obs.get("course_score", 60)),
    }

    meta_vector = float(meta_obs.get("meta_vector_score", 50))

    return {
        "vector_scores": vector_scores,
        "meta_vector_score": meta_vector,
        "last_step": "score_vectors",
    }
