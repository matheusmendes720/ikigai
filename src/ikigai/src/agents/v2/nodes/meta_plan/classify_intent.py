"""TEMPORARY classify_intent stub (Plan D Task D.1).

Plan D B.1 will replace this with the full intent classifier. Until B.1
ships, this stub recognises a small set of PT-BR / EN planning keywords
so that D.1's hint-on-detect test cases can pass.

Returns IntentClassification(level="high"|"low", score=int) for any input.
- "high" if user_input contains any HIGH_INTENT_KEYWORDS
- "low"  otherwise
"""

from __future__ import annotations

from dataclasses import dataclass

HIGH_INTENT_KEYWORDS: tuple[str, ...] = (
    "focar",
    "semana",
    "plano",
    "planejar",
    "objetivo",
    "meta",
    "plan",
    "goal",
    "focus",
    "weekly",
    "week",
)


@dataclass(frozen=True)
class IntentClassification:
    """Lightweight intent classification result (stub schema)."""

    level: str  # "high" | "medium" | "low"
    score: int  # 0..N — kept int for stub simplicity


def classify_intent(user_input: str) -> IntentClassification:
    """Return IntentClassification for user_input.

    TEMPORARY stub: keyword match only. B.1 will replace with prompt-chain
    classifier per `docs/superpowers/specs/2026-09-04-meta-planner-design.md`.
    """
    text = (user_input or "").lower()
    if any(kw in text for kw in HIGH_INTENT_KEYWORDS):
        return IntentClassification(level="high", score=1)
    return IntentClassification(level="low", score=0)
