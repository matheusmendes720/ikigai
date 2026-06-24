"""H2: Phase pivot — FUNDAÇÃO → BUSCA → HACKATHON → RECUPERACAO → OVERCLOCKING.

Iterative convergence (max 5 iters) to break the cycle:
- Phase weights → IKIGAi score
- IKIGAi score → phase decision
- Phase decision → new weights

Snapshot weights within phase (deterministic, no cycle during phase).
"""

from __future__ import annotations

from dataclasses import dataclass

from ikigai.constants import NSM
from ikigai.enums import Phase, VectorType


@dataclass(frozen=True)
class PhaseDecision:
    """Result of compute_phase."""

    phase: Phase
    weights: dict[VectorType, float]
    ikigai_score: float
    momentum: float
    iterations: int
    converged: bool
    rationale: str


def _compute_momentum(ikigai_score: float, revenue_actual: float, revenue_target: float) -> float:
    """momentum = 0.4 · ikigai_score + 0.6 · (revenue_actual/target · 100)."""
    revenue_pct = revenue_actual / max(revenue_target, 1.0)
    return 0.4 * ikigai_score + 0.6 * (revenue_pct * 100)


def _classify_phase(
    ikigai_score: float,
    momentum: float,
    opportunities_pursuing: int,
    cognitive_debt: float,
) -> Phase:
    """Classify phase from inputs (per meta_heuristics.md §2.2)."""
    # OVERCLOCKING: emergência
    if cognitive_debt > 5.0 or ikigai_score < 30:
        return Phase.OVERCLOCKING

    # HACKATHON: pronto para entregar
    if momentum > 70 and opportunities_pursuing >= 2:
        return Phase.HACKATHON

    # BUSCA: mercado aquecido
    if momentum > 50 and opportunities_pursuing >= 3:
        return Phase.BUSCA

    # FUNDAÇÃO: foco em skill (cognitive_debt > 1 OR ikigai_score < 60)
    if cognitive_debt > 1.0 or ikigai_score < 60:
        return Phase.FUNDACAO

    # RECUPERACAO: baixa energia (note: spec says ikigai_score < 40)
    if ikigai_score < 40:
        return Phase.RECUPERACAO

    # Default: FUNDAÇÃO
    return Phase.FUNDACAO


def compute_phase(
    ikigai_score: float,
    revenue_actual_30d: float,
    revenue_target: float,
    opportunities_pursuing: int = 0,
    cognitive_debt: float = 0.0,
    proposed_weights: dict[VectorType, float] | None = None,
    max_iters: int = NSM.PHASE_MAX_ITERS,
    convergence_threshold: float = NSM.PHASE_CONVERGENCE_THRESHOLD,
) -> PhaseDecision:
    """Compute phase with iterative convergence.

    Algorithm:
    1. Start with proposed_weights (or phase defaults for FUNDACAO).
    2. For each iter:
       a. Compute meta-vetor score (skipped here, use ikigai_score param).
       b. Classify phase.
       c. Get phase weights.
       d. Check convergence.
    3. Return best-effort after max_iters.

    Args:
        ikigai_score: meta-vetor score 0-100.
        revenue_actual_30d: BRL.
        revenue_target: BRL.
        opportunities_pursuing: count.
        cognitive_debt: 0-10+.
        proposed_weights: starting weights (defaults to FUNDACAO).
        max_iters: max iterations.
        convergence_threshold: weight delta for convergence.
    """
    if not 0 <= ikigai_score <= 100:
        raise ValueError(f"ikigai_score must be in [0, 100], got {ikigai_score}")
    if revenue_actual_30d < 0:
        raise ValueError(f"revenue_actual_30d must be >= 0, got {revenue_actual_30d}")
    if revenue_target < 0:
        raise ValueError(f"revenue_target must be >= 0, got {revenue_target}")
    if opportunities_pursuing < 0:
        raise ValueError(f"opportunities_pursuing must be >= 0, got {opportunities_pursuing}")

    # Initial weights
    weights = proposed_weights or Phase.FUNDACAO.vector_weights.copy()
    weights = {VectorType(k): float(v) for k, v in weights.items()}

    momentum = _compute_momentum(ikigai_score, revenue_actual_30d, revenue_target)
    converged = False
    final_phase = Phase.FUNDACAO
    iterations = 0

    for i in range(max_iters):
        iterations = i + 1
        phase = _classify_phase(ikigai_score, momentum, opportunities_pursuing, cognitive_debt)
        new_weights = {VectorType(k): float(v) for k, v in phase.vector_weights.items()}

        # Convergence check
        max_delta = max(abs(new_weights.get(k, 0) - weights.get(k, 0)) for k in set(new_weights) | set(weights))
        weights = new_weights
        final_phase = phase

        if max_delta < convergence_threshold:
            converged = True
            break

    return PhaseDecision(
        phase=final_phase,
        weights=weights,
        ikigai_score=ikigai_score,
        momentum=momentum,
        iterations=iterations,
        converged=converged,
        rationale=f"Phase={final_phase.value} after {iterations} iters (converged={converged})",
    )


__all__ = ["PhaseDecision", "compute_phase"]
