"""Hybrid meta-vetor (geo + harmonic) + alignment label."""

from __future__ import annotations

import math
from typing import Mapping

from ikigai.constants import NSM
from ikigai.enums import AlignmentLabel, VectorType
from ikigai.types import ScoreValue


def meta_vector(
    scores: Mapping[VectorType, ScoreValue],
    weights: Mapping[VectorType, float],
    w_geo: float = NSM.META_VETOR_W_GEO,
    w_harm: float = NSM.META_VETOR_W_HARM,
) -> ScoreValue:
    """Hybrid meta-vetor: 60% geometric mean + 40% harmonic mean.

    Properties:
    - Forgiving (geo mean) but with low-vec floor (harmonic).
    - All-zero returns 0 explicitly (no NaN).
    - log(0) clamped to log(0.01) to avoid math errors.

    Args:
        scores: vector → ScoreValue (percent or ratio).
        weights: vector → weight (typically summing to ~1.0, but not required).
        w_geo: geometric mean weight (default 0.6).
        w_harm: harmonic mean weight (default 0.4).

    Returns:
        ScoreValue in [0, 100] (percent).
    """
    if not 0 <= w_geo <= 1:
        raise ValueError(f"w_geo must be in [0, 1], got {w_geo}")
    if not 0 <= w_harm <= 1:
        raise ValueError(f"w_harm must be in [0, 1], got {w_harm}")
    if abs(w_geo + w_harm - 1.0) > 1e-6:
        raise ValueError(f"w_geo + w_harm must equal 1.0, got {w_geo + w_harm}")

    # Normalize scores to ratio [0, 1]
    active: dict[VectorType, float] = {}
    for vec, sv in scores.items():
        v = sv.value
        if sv.unit == "percent":
            v = v / 100.0
        elif sv.unit == "ratio":
            pass  # already ratio
        elif sv.unit == "index":
            pass  # assume already ratio
        else:
            continue  # skip non-numeric units
        if v > 0:
            active[vec] = v

    if not active:
        return ScoreValue(value=0.0, unit="percent")

    # Normalize weights
    total_weight = sum(weights.get(k, 0.0) for k in active)
    if total_weight <= 0:
        # No weights provided: uniform
        n = len(active)
        w_norm = {k: 1.0 / n for k in active}
    else:
        w_norm = {k: weights.get(k, 0.0) / total_weight for k in active}

    # Weighted geometric mean: exp(Σ w_i · log(x_i))
    log_sum = sum(w_norm[k] * math.log(max(v, 0.01)) for k, v in active.items())
    geo = math.exp(log_sum)

    # Weighted harmonic mean: 1 / Σ(w_i / x_i)
    harm = 1.0 / sum(w_norm[k] / max(v, 0.01) for k, v in active.items())

    # Hybrid blend
    final_ratio = w_geo * geo + w_harm * harm
    final_pct = min(100.0, max(0.0, final_ratio * 100.0))
    return ScoreValue(value=round(final_pct, 2), unit="percent")


def compute_alignment_label(score: float | ScoreValue) -> AlignmentLabel:
    """Compute alignment label from meta-vetor score.

    Thresholds (per ikigai_4_vectors.md §2):
    - >= 75: ALIGNED
    - [50, 75): CONVERGING
    - [25, 50): MISALIGNED
    - < 25: CRITICAL
    """
    if isinstance(score, ScoreValue):
        score = score.value
    if score < 0:
        raise ValueError(f"Score must be >= 0, got {score}")
    return AlignmentLabel.from_score(score)


__all__ = ["meta_vector", "compute_alignment_label"]
