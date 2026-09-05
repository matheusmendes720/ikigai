"""classify_intent node — pure keyword classifier for meta-planner (Plan D Task B.1).

No LLM call. ~50 LOC. Matches user_request against PT-BR + EN planning
keywords to detect intent level: high / medium / low.

The classifier is intentionally simple: a more sophisticated LLM-based
classifier would violate the data-first methodology (ADR-007) and add
unbounded latency. The keyword list lives here, NOT in algorithm_constants.json,
because these are NLU-style heuristics not algorithm tuning constants
(ADR-030 R6 does not apply).
"""

from __future__ import annotations

from typing import Literal

from src.ikigai.contracts.proposal import IntentClassification

PLANNING_KEYWORDS: dict[str, list[str]] = {
    "high": [
        "quero focar",
        "me ajuda a organizar",
        "decomponha",
        "esta semana",
        "esse mês",
        "objetivo",
        "meta",
        "projeto",
        "tarefas",
        "planejamento",
        "i want to focus",
        "help me organize",
        "decompose",
        "this week",
        "this month",
        "goal",
        "project",
    ],
    "medium": [
        "como posso",
        "qual seria",
        "sugestão",
        "recomendação",
        "próximo passo",
        "agenda",
        "schedule",
        "how can i",
        "what would",
        "suggestion",
        "recommendation",
        "next step",
    ],
}


def classify_intent(user_request: str) -> IntentClassification:
    """Classify user_request as high / medium / low planning intent.

    High: ≥1 high keyword.
    Medium: ≥1 medium keyword AND 0 high keywords.
    Low: zero matches.

    Returns IntentClassification(level, score) — score is total keyword hits
    across all tiers.
    """
    text = user_request.lower().strip()
    scores = {"high": 0, "medium": 0}
    for tier, keywords in PLANNING_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[tier] += 1

    total_score = scores["high"] + scores["medium"]
    level: Literal["high", "medium", "low"]
    if scores["high"] >= 1:
        level = "high"
    elif scores["medium"] >= 1:
        level = "medium"
    else:
        level = "low"

    return IntentClassification(level=level, score=total_score)
