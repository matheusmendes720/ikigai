"""PAV-based context switch overhead estimator between periods.

When the user transitions between periods (e.g. MANHÃ → TARDE), there
is an inherent **context-switch overhead** — the time/cost of
shifting gears, re-orienting, warming up to the new period's
context. The PAV defines canonical periods with characteristic
work/break durations; this module estimates the overhead of moving
between them.

**Why this matters:** The break-calculator (see
:mod:`operational.core.break_calculator`) computes the **wall-clock
rest** between blocks. The context-switch overhead is a
**subtraction** from that rest: not all of the rest is "true rest"
— some of it is overhead that the user is *paying* to switch
context. The remaining "net rest" is the actual recovery time.

**No pomodoro in this layer.** This is a coarser-grained
period-to-period estimate, used by the daily/weekly reports.

PAV §3 reference:

* MANHÃ: 3-5am (ritual matinal + Pomodoro S1 3-4 rounds × 50min)
* TARDE: 8-17h (ritual transição + Pomodoro S2 + S3)
* NOITE: 18-21h (rotina de saída + higiene do sono)

The estimated overhead for each transition (in minutes):

* MANHÃ → TARDE: 30min (longer transition; includes full breakfast,
  commute, full context reset)
* TARDE → NOITE: 20min (medium transition; includes shutdown ritual,
  dinner prep)
* MANHÃ → NOITE: 60min (rare; usually means skipping TARDE — high
  overhead)
* Same-period transitions: 5min (within-period context switches
  are cheaper)
* Reverse / non-canonical: 45min (severe context switch)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Final

from operational.enums import Period

__all__ = [
    "ContextSwitchEstimate",
    "ContextSwitchSeverity",
    "context_switch_overhead_minutes",
    "estimate_context_switch",
    "net_rest_minutes",
]


# ---------------------------------------------------------------------------
# Overhead matrix (PAV §3 + PAV §5 transitions)
# ---------------------------------------------------------------------------


# Base overhead per (from_period, to_period) pair in minutes.
# These are the *minimum* overhead estimates; the user can override
# via the ``custom_overrides`` parameter of :func:`estimate_context_switch`.
_BASE_OVERHEAD: Final[dict[tuple[Period, Period], int]] = {
    (Period.MANHA, Period.TARDE): 30,
    (Period.TARDE, Period.NOITE): 20,
    (Period.MANHA, Period.NOITE): 60,
    (Period.TARDE, Period.MANHA): 45,  # backward — high cost
    (Period.NOITE, Period.MANHA): 45,  # backward — high cost
    (Period.NOITE, Period.TARDE): 30,  # backward — medium cost
    (Period.MANHA, Period.MANHA): 5,  # within-period
    (Period.TARDE, Period.TARDE): 5,  # within-period
    (Period.NOITE, Period.NOITE): 5,  # within-period
}


class ContextSwitchSeverity(IntEnum):
    """Severity of a context switch (used for alerts and reports).

    Lower severity = cheaper switch.
    """
    MINIMAL = 1   # within-period
    LOW = 2       # forward canonical
    MEDIUM = 3    # backward canonical
    HIGH = 4      # non-canonical (e.g. MANHA → NOITE)
    SEVERE = 5    # reverse (NOITE → MANHA, requires sleep debt)


@dataclass(frozen=True, slots=True)
class ContextSwitchEstimate:
    """Result of estimating the context-switch overhead for one transition.

    Attributes:
        from_period: The source period.
        to_period: The target period.
        overhead_minutes: Estimated overhead in minutes (≥ 0).
        severity: Categorical severity.
        is_canonical: True if the transition is forward canonical
            (MANHÃ → TARDE → NOITE).
        is_reverse: True if the transition is reverse (e.g. NOITE → MANHA).
    """
    from_period: Period
    to_period: Period
    overhead_minutes: int
    severity: ContextSwitchSeverity
    is_canonical: bool
    is_reverse: bool


def _classify_transition(from_period: Period, to_period: Period) -> ContextSwitchSeverity:
    """Classify a transition by severity."""
    if from_period == to_period:
        return ContextSwitchSeverity.MINIMAL
    if (from_period, to_period) == (Period.MANHA, Period.TARDE):
        return ContextSwitchSeverity.LOW
    if (from_period, to_period) == (Period.TARDE, Period.NOITE):
        return ContextSwitchSeverity.LOW
    if (from_period, to_period) == (Period.TARDE, Period.MANHA):
        return ContextSwitchSeverity.MEDIUM
    if (from_period, to_period) == (Period.NOITE, Period.TARDE):
        return ContextSwitchSeverity.MEDIUM
    if (from_period, to_period) == (Period.MANHA, Period.NOITE):
        return ContextSwitchSeverity.HIGH
    if (from_period, to_period) == (Period.NOITE, Period.MANHA):
        return ContextSwitchSeverity.SEVERE
    return ContextSwitchSeverity.MEDIUM


def _is_canonical(from_period: Period, to_period: Period) -> bool:
    """True if transition is forward canonical (MANHÃ → TARDE → NOITE)."""
    canonical_chain = (Period.MANHA, Period.TARDE, Period.NOITE)
    try:
        from_idx = canonical_chain.index(from_period)
        to_idx = canonical_chain.index(to_period)
        return to_idx == from_idx + 1
    except ValueError:
        return False


def _is_reverse(from_period: Period, to_period: Period) -> bool:
    """True if transition is reverse (NOITE → MANHA, NOITE → TARDE, TARDE → MANHA)."""
    canonical_chain = (Period.MANHA, Period.TARDE, Period.NOITE)
    try:
        from_idx = canonical_chain.index(from_period)
        to_idx = canonical_chain.index(to_period)
        return to_idx < from_idx
    except ValueError:
        return False


def context_switch_overhead_minutes(
    from_period: Period,
    to_period: Period,
    custom_overrides: dict[tuple[Period, Period], int] | None = None,
) -> int:
    """Look up the canonical overhead for a (from_period, to_period) pair.

    Args:
        from_period: The source period.
        to_period: The target period.
        custom_overrides: Optional user-customized overrides for
            specific (from, to) pairs.

    Returns:
        Overhead in minutes (≥ 0).
    """
    if custom_overrides is not None:
        override = custom_overrides.get((from_period, to_period))
        if override is not None:
            if override < 0:
                msg = f"override must be >= 0, got {override}"
                raise ValueError(msg)
            return override
    overhead = _BASE_OVERHEAD.get((from_period, to_period))
    if overhead is None:
        msg = f"Unknown period transition: {from_period.value} → {to_period.value}"
        raise ValueError(msg)
    return overhead


def estimate_context_switch(
    from_period: Period,
    to_period: Period,
    custom_overrides: dict[tuple[Period, Period], int] | None = None,
) -> ContextSwitchEstimate:
    """Estimate the context-switch overhead for a period transition.

    Args:
        from_period: The source period.
        to_period: The target period.
        custom_overrides: Optional user-customized overrides.

    Returns:
        ContextSwitchEstimate with overhead, severity, canonical/reverse flags.
    """
    overhead = context_switch_overhead_minutes(from_period, to_period, custom_overrides)
    return ContextSwitchEstimate(
        from_period=from_period,
        to_period=to_period,
        overhead_minutes=overhead,
        severity=_classify_transition(from_period, to_period),
        is_canonical=_is_canonical(from_period, to_period),
        is_reverse=_is_reverse(from_period, to_period),
    )


def net_rest_minutes(
    gross_break_minutes: float,
    from_period: Period,
    to_period: Period,
    custom_overrides: dict[tuple[Period, Period], int] | None = None,
) -> float:
    """Compute the **net rest** after subtracting context-switch overhead.

    This is the actual recovery time the user got, after the
    cognitive cost of switching context is paid.

    Args:
        gross_break_minutes: Wall-clock break (from break_calculator).
        from_period: Source period.
        to_period: Target period.
        custom_overrides: Optional user-customized overrides.

    Returns:
        Net rest in minutes (≥ 0).
    """
    if gross_break_minutes < 0:
        msg = f"gross_break_minutes must be >= 0, got {gross_break_minutes}"
        raise ValueError(msg)
    overhead = context_switch_overhead_minutes(from_period, to_period, custom_overrides)
    return max(0.0, gross_break_minutes - float(overhead))
