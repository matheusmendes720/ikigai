"""H3: UCB weight recalibration (quarterly, PHASE_END)."""

from __future__ import annotations

import math

from ikigai.enums import VectorType


def recalibrate_weight_ucb(
    w_i: float,
    delta_score_i: float,
    sigma_i: float,
    n_i: int,
    all_n: dict[VectorType, int],
    alpha: float = 0.05,
    beta: float = 0.02,
    c: float = 0.05,
    max_weight: float = 1.5,
) -> float:
    """UCB weight recalibration: w_i(t+1) = w_i(t) + α·(Δ/max) - β·σ + c·sqrt(ln(N)/n_i).

    Args:
        w_i: current weight.
        delta_score_i: change in score over last 7d (0-100).
        sigma_i: std-dev of historical score.
        n_i: number of events for this vector.
        all_n: dict of all vectors → n.
        alpha: weight of improvement (default 0.05).
        beta: penalty for variance (default 0.02).
        c: UCB exploration bonus (default 0.05).
        max_weight: upper clamp (default 1.5).
    """
    if not 0 <= w_i <= max_weight:
        raise ValueError(f"w_i must be in [0, {max_weight}], got {w_i}")
    if not -100 <= delta_score_i <= 100:
        raise ValueError(f"delta_score_i must be in [-100, 100], got {delta_score_i}")
    if sigma_i < 0:
        raise ValueError(f"sigma_i must be >= 0, got {sigma_i}")
    if n_i < 0:
        raise ValueError(f"n_i must be >= 0, got {n_i}")

    N = sum(all_n.values())
    ucb_bonus = c * math.sqrt(math.log(N + 1) / max(n_i, 1))

    delta_weight = alpha * (delta_score_i / 100.0) - beta * sigma_i + ucb_bonus
    new_weight = max(0.0, min(max_weight, w_i + delta_weight))
    return round(new_weight, 4)


def recalibrate_all_weights(
    current_weights: dict[VectorType, float],
    delta_scores: dict[VectorType, float],
    sigmas: dict[VectorType, float],
    event_counts: dict[VectorType, int],
) -> dict[VectorType, float]:
    """Recalibrate all 5 vector weights."""
    new_weights: dict[VectorType, float] = {}
    for vec in current_weights:
        new_weights[vec] = recalibrate_weight_ucb(
            w_i=current_weights[vec],
            delta_score_i=delta_scores.get(vec, 0.0),
            sigma_i=sigmas.get(vec, 0.0),
            n_i=event_counts.get(vec, 0),
            all_n=event_counts,
        )
    return new_weights


__all__ = ["recalibrate_weight_ucb", "recalibrate_all_weights"]
