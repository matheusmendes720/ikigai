"""Q_HE (Quociente de Eficiência Habitual) — habit consistency model.

Formula (per Points_of_premisses-task-habits.md §3):
    Q_HE = w_sono · H_sono + w_med · H_med + w_workout · H_workout + w_lunch · H_lunch + η · S_streak

Default weights:
    H_sono:     0.35
    H_med:      0.20
    H_workout:  0.25
    H_lunch:    0.10
    S_streak:   0.15 (η)

All H_i ∈ [0, 1]; Q_HE ∈ [0, 1].
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ikigai.constants import NSM


@dataclass(frozen=True)
class QHEComponent:
    """Individual Q_HE component with its weight and score."""

    name: str
    weight: float
    score: float  # [0, 1]


def compute_qhe_components(
    h_sono: float,
    h_med: float,
    h_workout: float,
    h_lunch: float,
    s_streak: float,
) -> list[QHEComponent]:
    """Return list of 5 Q_HE components."""
    for name, v in [("h_sono", h_sono), ("h_med", h_med), ("h_workout", h_workout), ("h_lunch", h_lunch), ("s_streak", s_streak)]:
        if not 0 <= v <= 1:
            raise ValueError(f"{name} must be in [0, 1], got {v}")

    return [
        QHEComponent(name="sono", weight=0.35, score=h_sono),
        QHEComponent(name="med", weight=0.20, score=h_med),
        QHEComponent(name="workout", weight=0.25, score=h_workout),
        QHEComponent(name="lunch", weight=0.10, score=h_lunch),
        QHEComponent(name="streak", weight=0.15, score=s_streak),
    ]


def compute_qhe(
    h_sono: float,
    h_med: float,
    h_workout: float,
    h_lunch: float,
    s_streak: float,
    weights: dict[str, float] | None = None,
) -> float:
    """Compute Q_HE = weighted sum of components.

    Args:
        h_sono, h_med, h_workout, h_lunch, s_streak: each in [0, 1].
        weights: optional override for component weights (must sum to 1.0).

    Returns:
        Q_HE ∈ [0, 1].
    """
    components = compute_qhe_components(h_sono, h_med, h_workout, h_lunch, s_streak)

    if weights is None:
        return sum(c.weight * c.score for c in components)

    if abs(sum(weights.values()) - 1.0) > 1e-6:
        raise ValueError(f"weights must sum to 1.0, got {sum(weights.values())}")

    return sum(weights[c.name] * c.score for c in components)


def h_from_streak(streak_days: float, lambda_rate: float = NSM.LAMBDA) -> float:
    """Habit consistency H(t) = 1 - e^(-λ · t), in [0, 1]."""
    if streak_days < 0:
        raise ValueError(f"streak_days must be >= 0, got {streak_days}")
    return 1.0 - math.exp(-lambda_rate * streak_days)


__all__ = ["QHEComponent", "compute_qhe_components", "compute_qhe", "h_from_streak"]
