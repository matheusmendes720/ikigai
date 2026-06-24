r"""Habit arithmetic engine (PRD-02 §3, Points_of_premisses §4, PAV §6).

This module is the **canonical arithmetic core** of the habit subsystem.
It exposes the four formulas from the source specs as pure functions
and bundles them behind a thin, stateless :class:`HabitEngine` class
for callers that prefer object-oriented ergonomics.

Source spec:

* **PRD-02** ``vibe-ops/planning/PRD-02-habit-tracker.md`` §3 — Q_HE
  formula, weighted habit average, regime prediction thresholds.
* **Points_of_premisses**
  ``life-ops/planner/Points_of_premisses-task-habits.md`` §4 — QHE
  thresholds and the four-state policy bands.
* **PAV** ``vibe-ops/base/Produtividade Algorítmica Visual.md`` §6 —
  the habit-consolidation formula :math:`H(t) = 1 - e^{-\\lambda s}`
  and the energy model :math:`E_{req} = R \\cdot (1 - H(t))`.
* **ADR-003 / time-lengths §9.2** — :math:`\\lambda = 0.093` (default
  learning rate).

Formulas (verbatim from the source specs):

* :math:`H(t) = 1 - e^{-\\lambda s}` — habit consolidation level.
* :math:`E_{req} = R \\cdot (1 - H(t))` — energy required to perform.
* :math:`\\text{eff} = H(t) / (1 + E_{req})` — efficiency ratio.
* :math:`H_{avg} = \\sum_i w_i H_i / \\sum_i w_i` — weighted average.
* :math:`C = \\text{completed} / \\text{total}` — consistency in [0, 1].
* :math:`S_{bonus} = \\min(s_{cur} / s_{max}, 1.0)` — streak bonus.
* :math:`Q_{HE} = H_{avg} \\cdot (E/E_{max}) \\cdot (1 + \\eta S_{bonus})`
  — Quality-Habit-Effectiveness daily snapshot.

Regime prediction bands (Points_of_premisses §4):

* :math:`Q_{HE} \\geq 0.85` → :attr:`PolicyState.PUSH`
* :math:`0.60 \\leq Q_{HE} < 0.85` → :attr:`PolicyState.MAINTAIN`
* :math:`Q_{HE} < 0.60` → :attr:`PolicyState.RECOVER`

The fourth state, :attr:`PolicyState.REDUCE`, is **never** produced
by the QHE predictor alone — it requires multi-signal logic (e.g.
sustained sleep deficit) that lives outside this module.

Design rules:

* **Pure functions** — no I/O, no state mutation, no logging side
  effects. The :class:`HabitEngine` class is also stateless apart
  from its two configuration parameters (``eta`` and ``max_streak``).
* **mypy --strict** compatible — every parameter and return type is
  annotated.
* **ruff ALL** compliant — line-length 100, Google docstrings, no
  emojis in code.
* No imports from :mod:`operational.entities` siblings (metric,
  consolidation, etc.) or from :mod:`operational.core.*` to avoid
  circular dependencies. Imports flow:
  ``core`` → ``entities`` → ``constants`` / ``enums`` / ``types``.
* All magic numbers are extracted to ``_CONSTANT`` ``Final`` vars.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Final
from uuid import uuid4

from operational.constants import DEFAULT
from operational.entities.habit import Habit, HabitState, QHEMetrics
from operational.enums import EnergyLevel, PolicyState

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "ETA_DEFAULT",
    "STREAK_MAX_DEFAULT",
    "HabitComputation",
    "HabitEngine",
    "compute_consistency",
    "compute_efficiency_ratio",
    "compute_energy_required",
    "compute_habit_avg",
    "compute_habit_level",
    "compute_qhe",
    "compute_streak_bonus",
    "predict_regime_from_qhe",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Streak lower bound (inclusive). Streaks of 0 are a valid, meaningful
#: value — the formula must accept it without error.
_STREAK_MIN: Final[int] = 0

#: Default maximum streak for the streak-bonus normalisation (PRD-02 §3
#: + the standard "90 days to form a habit" heuristic).
STREAK_MAX_DEFAULT: Final[int] = 90

#: Default streak-bonus multiplier (:math:`\\eta` in the QHE formula).
#: Mirrors :attr:`QHEMetrics.eta` default value.
ETA_DEFAULT: Final[float] = 0.5

#: Energy-level → ratio mapping. High = full energy, Medium = 60 %,
#: Low = 30 %. Used when the caller passes an :class:`EnergyLevel`
#: instead of an explicit ratio.
_ENERGY_RATIO_HIGH: Final[float] = 1.0
_ENERGY_RATIO_MEDIUM: Final[float] = 0.6
_ENERGY_RATIO_LOW: Final[float] = 0.3

#: Default ratio when the caller provides neither an energy level nor
#: an explicit ratio. Midpoint of the [0, 1] range.
_ENERGY_DEFAULT: Final[float] = 0.5

#: Theoretical upper bound of the QHE value. Achieved when
#: ``habit_avg = energy_ratio = streak_bonus = 1.0`` and ``eta = 1.0``:
#: :math:`1.0 \\cdot 1.0 \\cdot (1 + 1.0 \\cdot 1.0) = 2.0`.
_QHE_THEORETICAL_MAX: Final[float] = 2.0

#: QHE value below which :func:`predict_regime_from_qhe` rejects
#: inputs. The formula cannot produce negative values, so this is a
#: sanity guard against corrupted inputs.
_QHE_LOWER_BOUND: Final[float] = 0.0

#: Resistance upper bound (inclusive) per the :class:`Habit` entity
#: spec (``resistance: Field(ge=0.0, le=10.0)``).
_RESISTANCE_MAX: Final[float] = 10.0

#: Habit-level upper bound (inclusive). :math:`H(t)` is in [0, 1).
_HABIT_LEVEL_MAX: Final[float] = 1.0

#: Energy-ratio lower bound (inclusive).
_ENERGY_MIN: Final[float] = 0.0

#: Energy-ratio upper bound (inclusive).
_ENERGY_MAX: Final[float] = 1.0

#: Map of :class:`EnergyLevel` → ratio in [0, 1]. Used by
#: :meth:`HabitEngine.compute_qhe` when the caller passes a tier
#: rather than an explicit ratio.
_ENERGY_MAP: Final[dict[EnergyLevel, float]] = {
    EnergyLevel.HIGH: _ENERGY_RATIO_HIGH,
    EnergyLevel.MEDIUM: _ENERGY_RATIO_MEDIUM,
    EnergyLevel.LOW: _ENERGY_RATIO_LOW,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _today_utc() -> date:
    """Return today's date in UTC (timezone-aware helper).

    The :class:`datetime.date.today` builtin returns a naive local
    date which triggers ``DTZ011``. The convention in this package
    is to anchor dates to UTC for consistency with the naive-UTC
    datetime pattern used throughout the entities layer.
    """
    return datetime.now(tz=UTC).date()


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HabitComputation:
    r"""Immutable result of computing metrics for a single habit.

    Returned by :meth:`HabitEngine.compute_habit` and convenient as a
    one-shot per-habit snapshot (level + required energy + efficiency)
    for a given streak.

    Attributes:
        habit_id: Universal Entity ID of the parent :class:`Habit`.
        habit_level: :math:`H(t) = 1 - e^{-\lambda s}` in [0, 1).
        energy_required: :math:`E_{req} = R \cdot (1 - H(t))` in
            ``[0, 10]``.
        efficiency_ratio: :math:`H(t) / (1 + E_{req})` in ``[0, 1]``.
        streak_current: The streak that was used for the computation.
    """

    habit_id: str
    habit_level: float
    energy_required: float
    efficiency_ratio: float
    streak_current: int


# ---------------------------------------------------------------------------
# Per-habit arithmetic
# ---------------------------------------------------------------------------


def compute_habit_level(lambda_learning: float, streak: int) -> float:
    r"""Compute the habit consolidation level :math:`H(t)`.

    Formula (PAV §6, PRD-02 §2):

    .. math::

        H(t) = 1 - e^{-\lambda \cdot s}

    where :math:`\lambda` is the learning rate (``lambda_learning``)
    and :math:`s` is the consecutive-day streak.

    Args:
        lambda_learning: Learning rate in :math:`D^{-1}`. Must be
            :math:`\geq 0`. Typical value: 0.093 (from
            :data:`DEFAULT.LAMBDA_LEARNING_DEFAULT`).
        streak: Consecutive days of completion. Must be
            :math:`\geq 0`.

    Returns:
        Habit level in :math:`[0.0, 1.0)`. Approaches 1.0 as the
        streak grows large. Returns exactly 0.0 when
        ``lambda_learning == 0`` (degenerate case).

    Raises:
        ValueError: If ``lambda_learning < 0`` or ``streak < 0``.
            Both are programming errors, not runtime data.
    """
    if lambda_learning < 0.0:
        msg = f"lambda_learning must be >= 0, got {lambda_learning}"
        raise ValueError(msg)
    if streak < _STREAK_MIN:
        msg = f"streak must be >= 0, got {streak}"
        raise ValueError(msg)
    if lambda_learning == 0.0:
        return 0.0
    return 1.0 - math.exp(-lambda_learning * streak)


def compute_energy_required(resistance: float, habit_level: float) -> float:
    r"""Compute the energy required to perform a habit (PAV §6).

    Formula:

    .. math::

        E_{req} = R \cdot (1 - H(t))

    A high-resistance, unconsolidated habit costs close to ``R`` in
    energy; a fully-consolidated habit costs close to 0.

    Args:
        resistance: Habit resistance, in ``[0.0, 10.0]``. 0 = effortless,
            10 = extremely hard.
        habit_level: Current habit consolidation level, in
            ``[0.0, 1.0]``.

    Returns:
        Energy required in :math:`[0.0, 10.0]`. ``0.0`` for a fully
        consolidated habit; ``R`` for a habit at streak 0.

    Raises:
        ValueError: If ``resistance`` is outside ``[0, 10]`` or
            ``habit_level`` is outside ``[0, 1]``. Both are
            programming errors.
    """
    if not 0.0 <= resistance <= _RESISTANCE_MAX:
        msg = f"resistance must be in [0, 10], got {resistance}"
        raise ValueError(msg)
    if not 0.0 <= habit_level <= _HABIT_LEVEL_MAX:
        msg = f"habit_level must be in [0, 1], got {habit_level}"
        raise ValueError(msg)
    return resistance * (1.0 - habit_level)


def compute_efficiency_ratio(habit_level: float, energy_required: float) -> float:
    r"""Compute the efficiency ratio (PAV §6).

    Formula:

    .. math::

        \text{efficiency} = \frac{H(t)}{1 + E_{req}}

    The ``1 +`` term keeps the ratio bounded by ``1 / (1 + R)`` for
    habits at streak 0 (worst case) and ``1.0`` for fully consolidated
    habits with zero required energy.

    Args:
        habit_level: Current habit level :math:`H(t)` in ``[0.0, 1.0]``.
        energy_required: Energy required :math:`E_{req}` in
            ``[0.0, 10.0]``.

    Returns:
        Efficiency ratio in ``[0.0, 1.0]``. ``0.0`` at streak 0 with
        any non-zero resistance; ``1.0`` only at full consolidation
        with zero required energy.

    Raises:
        ValueError: If ``habit_level`` is outside ``[0, 1]`` or
            ``energy_required < 0``. Both are programming errors.
    """
    if not 0.0 <= habit_level <= _HABIT_LEVEL_MAX:
        msg = f"habit_level must be in [0, 1], got {habit_level}"
        raise ValueError(msg)
    if energy_required < 0.0:
        msg = f"energy_required must be >= 0, got {energy_required}"
        raise ValueError(msg)
    return habit_level / (1.0 + energy_required)


# ---------------------------------------------------------------------------
# Aggregations across habits
# ---------------------------------------------------------------------------


def compute_habit_avg(
    habit_states: Sequence[HabitState],
    habits: Sequence[Habit],
) -> float:
    r"""Compute the weighted average habit level :math:`H_{avg}`.

    Formula (PRD-02 §3):

    .. math::

        H_{avg} = \frac{\sum_i w_i \cdot H_i}{\sum_i w_i}

    Each contributing state is looked up in the ``habits`` collection
    by ``habit_id``. Three classes of states are **silently
    skipped** (contribute neither to the numerator nor the
    denominator):

    * States whose ``habit_id`` is not present in ``habits``.
    * Habits with ``archived = True``.
    * States where the parent habit has ``weight_in_qhe == 0``.

    Args:
        habit_states: Daily :class:`HabitState` records.
        habits: All :class:`Habit` definitions (used to look up
            ``lambda_learning`` and ``weight_in_qhe``).

    Returns:
        Weighted average habit level in :math:`[0.0, 1.0]`. Returns
        ``0.0`` if there are no contributing states or if the total
        weight sums to zero.
    """
    if not habit_states or not habits:
        return 0.0
    habit_map: dict[str, Habit] = {h.id: h for h in habits}
    weighted_sum: float = 0.0
    weight_total: float = 0.0
    for state in habit_states:
        habit = habit_map.get(state.habit_id)
        if habit is None or habit.archived:
            continue
        if habit.weight_in_qhe == 0.0:
            continue
        h_t = compute_habit_level(habit.lambda_learning, state.streak_current)
        weighted_sum += h_t * habit.weight_in_qhe
        weight_total += habit.weight_in_qhe
    if weight_total == 0.0:
        return 0.0
    return weighted_sum / weight_total


def compute_consistency(habit_states: Sequence[HabitState]) -> float:
    r"""Compute the consistency ratio for a set of habit states.

    Formula (PRD-02 §3):

    .. math::

        \text{Consistency} = \frac{\text{completed}}{\text{total}}

    Args:
        habit_states: Daily :class:`HabitState` records.

    Returns:
        Consistency in :math:`[0.0, 1.0]`. Returns ``0.0`` for an
        empty sequence (no scheduled habits is treated as trivially
        inconsistent — callers may override by passing a non-empty
        list of all-missed states).
    """
    if not habit_states:
        return 0.0
    completed = sum(1 for s in habit_states if s.completed)
    return completed / len(habit_states)


def compute_streak_bonus(
    current_streak: int,
    max_streak: int = STREAK_MAX_DEFAULT,
) -> float:
    r"""Compute the normalised streak bonus :math:`S_{bonus}`.

    Formula (PRD-02 §3):

    .. math::

        S_{bonus} = \min\!\left(\frac{s_{cur}}{s_{max}},\, 1.0\right)

    The result is capped at 1.0 to prevent bonuses exceeding 100 %
    even for very long streaks.

    Args:
        current_streak: Current consecutive-day streak. Must be
            :math:`\geq 0`.
        max_streak: Maximum streak for normalisation. Must be
            :math:`> 0`. Default :data:`STREAK_MAX_DEFAULT` (90 days).

    Returns:
        Streak bonus in :math:`[0.0, 1.0]`.

    Raises:
        ValueError: If ``current_streak < 0`` or ``max_streak <= 0``.
    """
    if current_streak < _STREAK_MIN:
        msg = f"current_streak must be >= 0, got {current_streak}"
        raise ValueError(msg)
    if max_streak <= 0:
        msg = f"max_streak must be > 0, got {max_streak}"
        raise ValueError(msg)
    return min(current_streak / max_streak, 1.0)


# ---------------------------------------------------------------------------
# QHE (Quality Habit Effectiveness)
# ---------------------------------------------------------------------------


def compute_qhe(  # noqa: PLR0913 — 6 distinct semantic parameters
    habit_states: Sequence[HabitState],
    habits: Sequence[Habit],
    energy_ratio: float,
    current_streak: int,
    eta: float = ETA_DEFAULT,
    max_streak: int = STREAK_MAX_DEFAULT,
) -> QHEMetrics:
    r"""Compute the Q_HE (Quality Habit Effectiveness) daily snapshot.

    Formula (PRD-02 §3):

    .. math::

        Q_{HE} = H_{avg} \cdot \frac{E(t)}{E_{max}}
                 \cdot (1 + \eta \cdot S_{bonus})

    The four input components (:math:`H_{avg}`, Consistency,
    :math:`S_{bonus}`, :math:`E(t)/E_{max}`) are derived from the
    arguments and stored in the returned :class:`QHEMetrics`. The
    actual QHE value is exposed via the model's computed field
    :attr:`QHEMetrics.qhe`.

    Args:
        habit_states: Daily :class:`HabitState` records.
        habits: All :class:`Habit` definitions (for weight lookup).
        energy_ratio: Current energy ratio :math:`E(t)/E_{max}` in
            ``[0.0, 1.0]``.
        current_streak: Current consecutive-day streak, used for the
            streak-bonus term.
        eta: Streak-bonus multiplier in ``[0.0, 1.0]``. Default
            :data:`ETA_DEFAULT` (0.5).
        max_streak: Maximum streak for normalisation. Default
            :data:`STREAK_MAX_DEFAULT` (90).

    Returns:
        A fully-populated :class:`QHEMetrics` snapshot. The ``id``
        is auto-generated (``qhe_<12 hex chars>``) and the ``date``
        is set to today; callers that need a different id or date
        should use :meth:`QHEMetrics.model_copy`.

    Raises:
        ValueError: If ``energy_ratio`` is outside ``[0, 1]`` or
            ``eta`` is outside ``[0, 1]``.
    """
    if not _ENERGY_MIN <= energy_ratio <= _ENERGY_MAX:
        msg = f"energy_ratio must be in [0, 1], got {energy_ratio}"
        raise ValueError(msg)
    if not 0.0 <= eta <= 1.0:
        msg = f"eta must be in [0, 1], got {eta}"
        raise ValueError(msg)
    habit_avg = compute_habit_avg(habit_states, habits)
    consistency = compute_consistency(habit_states)
    streak_bonus = compute_streak_bonus(current_streak, max_streak)
    return QHEMetrics(
        id=f"qhe_{uuid4().hex[:12]}",
        date=_today_utc(),
        habit_avg=habit_avg,
        consistency=consistency,
        streak_bonus=streak_bonus,
        energy_ratio=energy_ratio,
        eta=eta,
    )


def predict_regime_from_qhe(qhe_value: float) -> PolicyState:
    r"""Predict the operational regime from a QHE value.

    Bands (Points_of_premisses §4, PRD-02 §3):

    * :math:`Q_{HE} \geq \text{QHE\_PUSH\_THRESHOLD}` (0.85) →
      :attr:`PolicyState.PUSH`.
    * :math:`Q_{HE} < \text{QHE\_RECOVER\_THRESHOLD}` (0.60) →
      :attr:`PolicyState.RECOVER`.
    * Otherwise → :attr:`PolicyState.MAINTAIN`.

    .. note::

        :attr:`PolicyState.REDUCE` is **never** produced by the QHE
        predictor — it requires multi-signal logic (e.g. sustained
        sleep deficit) handled at the policy-FSM layer.

    Args:
        qhe_value: Computed QHE value. Valid range is
            ``[0.0, 2.0]`` (theoretical max:
            ``1.0 * 1.0 * (1 + 1.0 * 1.0) = 2.0``).

    Returns:
        The :class:`PolicyState` the regime should adopt.

    Raises:
        ValueError: If ``qhe_value`` is outside ``[0.0, 2.0]``. The
            range accommodates the streak-bonus term
            ``(1 + eta * streak_bonus)`` which can push the value
            above 1.0.
    """
    if qhe_value < _QHE_LOWER_BOUND or qhe_value > _QHE_THEORETICAL_MAX:
        msg = (
            f"qhe must be in [0, 2.0] (theoretical max with "
            f"streak_bonus), got {qhe_value}"
        )
        raise ValueError(msg)
    if qhe_value >= DEFAULT.QHE_PUSH_THRESHOLD:
        return PolicyState.PUSH
    if qhe_value < DEFAULT.QHE_RECOVER_THRESHOLD:
        return PolicyState.RECOVER
    return PolicyState.MAINTAIN


# ---------------------------------------------------------------------------
# HabitEngine — stateless OO wrapper
# ---------------------------------------------------------------------------


class HabitEngine:
    r"""Stateless habit arithmetic engine.

    The engine is a **thin OO wrapper** around the module-level
    functions. It holds two configuration parameters (``eta`` and
    ``max_streak``) that are passed through to
    :func:`compute_qhe` so the caller does not have to repeat them
    on every call. All numeric computation remains in the pure
    functions; the engine never mutates its own state after
    construction.

    Attributes:
        eta: Streak-bonus multiplier in ``[0.0, 1.0]``.
        max_streak: Maximum streak for streak-bonus normalisation.
    """

    def __init__(
        self,
        eta: float = ETA_DEFAULT,
        max_streak: int = STREAK_MAX_DEFAULT,
    ) -> None:
        """Initialise the engine with configurable QHE parameters.

        Args:
            eta: Streak-bonus multiplier in ``[0.0, 1.0]``. Default
                :data:`ETA_DEFAULT` (0.5).
            max_streak: Maximum streak for streak-bonus normalisation.
                Must be ``> 0``. Default :data:`STREAK_MAX_DEFAULT` (90).

        Raises:
            ValueError: If ``eta`` is outside ``[0, 1]`` or
                ``max_streak <= 0``.
        """
        if not 0.0 <= eta <= 1.0:
            msg = f"eta must be in [0, 1], got {eta}"
            raise ValueError(msg)
        if max_streak <= 0:
            msg = f"max_streak must be > 0, got {max_streak}"
            raise ValueError(msg)
        self._eta: float = eta
        self._max_streak: int = max_streak

    @property
    def eta(self) -> float:
        r"""Return the configured :math:`\eta` multiplier."""
        return self._eta

    @property
    def max_streak(self) -> int:
        """Return the configured maximum streak."""
        return self._max_streak

    def compute_habit(self, habit: Habit, streak: int) -> HabitComputation:
        """Compute :math:`H(t)`, :math:`E_{req}`, and efficiency for a habit.

        Args:
            habit: The :class:`Habit` definition (carries
                ``lambda_learning`` and ``resistance``).
            streak: Current consecutive-day streak for the habit.

        Returns:
            A :class:`HabitComputation` snapshot for the given
            streak. Independent of the engine's ``eta``/``max_streak``
            configuration — those only affect QHE aggregation.
        """
        h_t = compute_habit_level(habit.lambda_learning, streak)
        e_req = compute_energy_required(habit.resistance, h_t)
        eff = compute_efficiency_ratio(h_t, e_req)
        return HabitComputation(
            habit_id=habit.id,
            habit_level=h_t,
            energy_required=e_req,
            efficiency_ratio=eff,
            streak_current=streak,
        )

    def compute_qhe(
        self,
        habit_states: Sequence[HabitState],
        habits: Sequence[Habit],
        energy_level: EnergyLevel | None = None,
        energy_ratio: float | None = None,
        current_streak: int = 0,
    ) -> QHEMetrics:
        """Compute QHE with the engine's configured ``eta`` and ``max_streak``.

        Exactly one of ``energy_level`` and ``energy_ratio`` may be
        provided. If both are ``None``, the engine uses
        :data:`_ENERGY_DEFAULT` (0.5). If both are provided,
        ``energy_ratio`` wins (the explicit value takes precedence
        over the tier).

        Args:
            habit_states: Daily :class:`HabitState` records.
            habits: All :class:`Habit` definitions.
            energy_level: Optional :class:`EnergyLevel` — mapped to a
                ratio via :data:`_ENERGY_MAP`.
            energy_ratio: Optional explicit ratio in ``[0.0, 1.0]``.
                Takes precedence over ``energy_level``.
            current_streak: Current consecutive-day streak, used for
                the streak-bonus term. Default 0.

        Returns:
            A :class:`QHEMetrics` snapshot. The actual QHE value is
            exposed via the model's :attr:`QHEMetrics.qhe` computed
            field.

        Raises:
            ValueError: If both ``energy_level`` and ``energy_ratio``
                are invalid (propagated from :func:`compute_qhe`).
        """
        if energy_ratio is not None:
            ratio: float = energy_ratio
        elif energy_level is not None:
            ratio = _ENERGY_MAP[energy_level]
        else:
            ratio = _ENERGY_DEFAULT
        return compute_qhe(
            habit_states=habit_states,
            habits=habits,
            energy_ratio=ratio,
            current_streak=current_streak,
            eta=self._eta,
            max_streak=self._max_streak,
        )
