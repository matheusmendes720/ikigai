"""H1: Regime decision — PUSH/MAINTAIN/REDUCE/RECOVER with hysteresis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ikigai.constants import NSM
from ikigai.enums import RegimeType


@dataclass(frozen=True)
class RegimeDecision:
    """Result of compute_regime."""

    regime: RegimeType
    rationale: str
    qhe_score: float
    c_comp_score: float
    infractions: int
    sleep_debt_h: float
    raw_score: float  # pre-hysteresis
    hysteresis_applied: bool = False
    hysteresis_reason: str | None = None


def compute_regime(
    qhe_7d_avg: float,
    c_comp_24h: float = 1.0,
    infractions_24h: int = 0,
    sleep_debt_h: float = 0.0,
) -> RegimeDecision:
    """Decide regime from Q_HE, completion, infractions, sleep debt.

    Algorithm (per meta_heuristics.md §1.2):
    1. Hard floor: RECOVER if Q_HE < 0.60 + sleep_debt > 2h
    2. PUSH: Q_HE ≥ 0.85 + c_comp ≥ 0.90 + 0 infractions
    3. MAINTAIN: Q_HE [0.70, 0.85) + c_comp [0.80, 0.90)
    4. REDUCE: Q_HE [0.60, 0.70) OR c_comp [0.70, 0.80)
    5. Default: RECOVER (conservative)
    """
    if not 0 <= qhe_7d_avg <= 1:
        raise ValueError(f"qhe_7d_avg must be in [0, 1], got {qhe_7d_avg}")
    if not 0 <= c_comp_24h <= 1:
        raise ValueError(f"c_comp_24h must be in [0, 1], got {c_comp_24h}")
    if infractions_24h < 0:
        raise ValueError(f"infractions_24h must be >= 0, got {infractions_24h}")
    if sleep_debt_h < 0:
        raise ValueError(f"sleep_debt_h must be >= 0, got {sleep_debt_h}")

    raw_score = (qhe_7d_avg + c_comp_24h) / 2.0

    # 1. Hard floor: RECOVER
    if qhe_7d_avg < NSM.Q_HE_RECOVER and sleep_debt_h > 2.0:
        return RegimeDecision(
            regime=RegimeType.RECOVER,
            rationale=f"Q_HE={qhe_7d_avg:.2f} < {NSM.Q_HE_RECOVER} + sleep_debt={sleep_debt_h:.1f}h > 2h (hard floor)",
            qhe_score=qhe_7d_avg,
            c_comp_score=c_comp_24h,
            infractions=infractions_24h,
            sleep_debt_h=sleep_debt_h,
            raw_score=raw_score,
        )

    # 2. PUSH
    if qhe_7d_avg >= NSM.Q_HE_PUSH and c_comp_24h >= 0.90 and infractions_24h == 0:
        return RegimeDecision(
            regime=RegimeType.PUSH,
            rationale=f"Q_HE={qhe_7d_avg:.2f} ≥ {NSM.Q_HE_PUSH}, c_comp={c_comp_24h:.2f} ≥ 0.90, 0 infractions",
            qhe_score=qhe_7d_avg,
            c_comp_score=c_comp_24h,
            infractions=infractions_24h,
            sleep_debt_h=sleep_debt_h,
            raw_score=raw_score,
        )

    # 3. MAINTAIN
    if 0.70 <= qhe_7d_avg < NSM.Q_HE_PUSH and 0.80 <= c_comp_24h < 0.90:
        return RegimeDecision(
            regime=RegimeType.MAINTAIN,
            rationale=f"Q_HE={qhe_7d_avg:.2f} in [0.70, {NSM.Q_HE_PUSH}), c_comp={c_comp_24h:.2f} in [0.80, 0.90)",
            qhe_score=qhe_7d_avg,
            c_comp_score=c_comp_24h,
            infractions=infractions_24h,
            sleep_debt_h=sleep_debt_h,
            raw_score=raw_score,
        )

    # 4. REDUCE
    if 0.60 <= qhe_7d_avg < 0.70 or 0.70 <= c_comp_24h < 0.80:
        return RegimeDecision(
            regime=RegimeType.REDUCE,
            rationale=f"Q_HE={qhe_7d_avg:.2f} in [0.60, 0.70) OR c_comp={c_comp_24h:.2f} in [0.70, 0.80)",
            qhe_score=qhe_7d_avg,
            c_comp_score=c_comp_24h,
            infractions=infractions_24h,
            sleep_debt_h=sleep_debt_h,
            raw_score=raw_score,
        )

    # 5. Default: RECOVER (conservative)
    return RegimeDecision(
        regime=RegimeType.RECOVER,
        rationale=f"Fallback: Q_HE={qhe_7d_avg:.2f}, c_comp={c_comp_24h:.2f} (conservative default)",
        qhe_score=qhe_7d_avg,
        c_comp_score=c_comp_24h,
        infractions=infractions_24h,
        sleep_debt_h=sleep_debt_h,
        raw_score=raw_score,
    )


def apply_hysteresis(
    current_regime: RegimeType,
    proposed_regime: RegimeType,
    regime_history: list[tuple[datetime, RegimeType]],
    upgrade_days: int = NSM.HYSTERESIS_UPGRADE_DAYS,
    downgrade_days: int = NSM.HYSTERESIS_DOWNGRADE_DAYS,
    now: datetime | None = None,
) -> tuple[RegimeType, bool, str | None]:
    """Apply hysteresis protection against regime oscillation.

    Rules (per meta_heuristics.md §1.3):
    - UPGRADE (REDUCE→MAINTAIN→PUSH): require `upgrade_days` consecutive above threshold
    - DOWNGRADE (PUSH→MAINTAIN→REDUCE): require `downgrade_days` consecutive below
    - RECOVER entry: immediate (1 day)
    - RECOVER exit: 3 days

    Args:
        current_regime: current regime.
        proposed_regime: what compute_regime() just decided.
        regime_history: list of (timestamp, regime) tuples, most recent last.
        upgrade_days: days required for upgrade.
        downgrade_days: days required for downgrade.
        now: current time (for testing).

    Returns:
        (final_regime, hysteresis_applied, reason)
    """
    now = now or datetime.now()

    # RECOVER entry: immediate (special case)
    if proposed_regime == RegimeType.RECOVER and current_regime != RegimeType.RECOVER:
        return (RegimeType.RECOVER, False, None)  # immediate entry, no hysteresis

    # RECOVER exit: 3 days with Q_HE >= 0.65 (simplified: 3 consecutive non-RECOVER)
    if current_regime == RegimeType.RECOVER and proposed_regime != RegimeType.RECOVER:
        consecutive_non_recover = 0
        for ts, reg in reversed(regime_history):
            if reg != RegimeType.RECOVER:
                consecutive_non_recover += 1
            else:
                break
        if consecutive_non_recover < 3:
            return (
                RegimeType.RECOVER,
                True,
                f"RECOVER exit requires 3 consecutive non-RECOVER days, only {consecutive_non_recover}",
            )
        return (proposed_regime, False, None)

    # Same regime: no change
    if proposed_regime == current_regime:
        return (current_regime, False, None)

    # Determine direction (upgrade = more work, downgrade = less work)
    order = [RegimeType.RECOVER, RegimeType.REDUCE, RegimeType.MAINTAIN, RegimeType.PUSH]
    current_idx = order.index(current_regime)
    proposed_idx = order.index(proposed_regime)
    is_upgrade = proposed_idx > current_idx

    required_days = upgrade_days if is_upgrade else downgrade_days

    # Count consecutive same-regime proposals in history
    consecutive = 0
    for ts, reg in reversed(regime_history):
        if reg == proposed_regime:
            consecutive += 1
        else:
            break

    if consecutive < required_days:
        return (
            current_regime,
            True,
            f"{'Upgrade' if is_upgrade else 'Downgrade'} to {proposed_regime.value} requires {required_days} consecutive days, only {consecutive}",
        )

    return (proposed_regime, False, None)


__all__ = ["RegimeDecision", "compute_regime", "apply_hysteresis"]
