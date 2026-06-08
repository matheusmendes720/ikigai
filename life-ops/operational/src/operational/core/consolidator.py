"""Daily consolidation (PRD-05 §4-§5).

This module computes the **overall daily score** for a
:class:`operational.entities.metric.DailyLog` and bundles it with
the auto-generated alerts and recommendations into a
:class:`operational.entities.consolidation.DailyConsolidation`.

The module exposes:

* :func:`consolidate_daily` — pure top-level entry point that
  orchestrates the four sub-scores and the alert / recommendation
  generators.
* :func:`compute_energy_score`,
  :func:`compute_productivity_score`,
  :func:`compute_health_score`,
  :func:`compute_overall_score` — the four sub-scores.
* :func:`compute_sleep_debt` — sleep-debt helper in hours.
* :func:`generate_alerts` — the three-metric alert generator
  (sleep debt, habit compliance, productivity score) per PRD-05 §5.
* :func:`generate_recommendations` — short-prose recommendations
  derived from the four scores.
* :class:`Consolidator` — namespace class that delegates to the
  module-level functions, mirroring the
  :class:`operational.core.sleep_calculator.SleepQuality` pattern.

Source documents:

* **PRD-05 §4** — composite-score formulas (energy / productivity /
  health with weights 0.3 / 0.4 / 0.3) and the
  ``energy_map = {H: 100, M: 60, L: 30}`` constant.
* **PRD-05 §5** — alert thresholds (sleep debt, 7-day energy
  average, habit compliance, productivity score).
* **ADR-004** — composite-score weighting (0.3 / 0.4 / 0.3).

Design rules:

* **Pure functions** for every sub-score and every alert / reco
  generator. The only stateful wrapper is the trivial
  :class:`Consolidator` namespace.
* All four sub-scores are clamped to ``[0.0, 100.0]`` before being
  passed to the overall formula (defensive — the formulas themselves
  naturally cap in ``[0, 100]`` for non-pathological inputs).
* Alerts are sorted by severity (CRITICAL first) for stable
  downstream rendering; the implementation uses an explicit
  if/elif/elif chain that already produces that ordering.
* :class:`Consolidator` is a namespace class with all
  ``@staticmethod`` methods — it has no instance state, mirroring
  :class:`operational.core.sleep_calculator.SleepQuality`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Final
from uuid import uuid4

from operational.entities.consolidation import DailyConsolidation, MetricAlert
from operational.entities.metric import DailyLog  # noqa: TC001
from operational.enums import AlertLevel

__all__ = [
    "Consolidator",
    "DailyConsolidationResult",
    "compute_energy_score",
    "compute_health_score",
    "compute_overall_score",
    "compute_productivity_score",
    "compute_sleep_debt",
    "consolidate_daily",
    "generate_alerts",
    "generate_recommendations",
]


# ---------------------------------------------------------------------------
# Module-level constants (PRD-05 §4-§5; ruff PLR2004)
# ---------------------------------------------------------------------------

#: Energy-level mapping (PRD-05 §4). Keys match
#: :class:`operational.enums.EnergyLevel` string values.
_ENERGY_MAP: Final[dict[str, float]] = {"H": 100.0, "M": 60.0, "L": 30.0}

#: Target nightly sleep duration, in hours (PRD-05 §4 — sleep penalty).
_TARGET_SLEEP_HOURS: Final[float] = 8.0

#: Maximum time-tracked hours for a full productivity time-bonus (PRD-05 §4).
_MAX_PRODUCTIVE_HOURS: Final[float] = 8.0

#: Maximum pomodoros for a full productivity focus-bonus (PRD-05 §4).
_MAX_POMODOROS: Final[float] = 8.0

#: Target water glasses per day (PRD-05 §4).
_TARGET_WATER_GLASSES: Final[float] = 8.0

#: Sleep debt threshold for a WARNING alert, in hours (PRD-05 §5).
_SLEEP_DEBT_WARN: Final[float] = 4.0

#: Sleep debt threshold for a CRITICAL alert, in hours (PRD-05 §5).
_SLEEP_DEBT_CRITICAL: Final[float] = 8.0

#: Habit-compliance threshold for a WARNING alert, in percent (PRD-05 §5).
_HABIT_COMPLIANCE_WARN: Final[float] = 60.0

#: Habit-compliance threshold for a CRITICAL alert, in percent (PRD-05 §5).
_HABIT_COMPLIANCE_CRITICAL: Final[float] = 40.0

#: Productivity-score threshold for a WARNING alert (PRD-05 §5).
_PRODUCTIVITY_WARN: Final[float] = 40.0

#: Productivity-score threshold for a CRITICAL alert (PRD-05 §5).
_PRODUCTIVITY_CRITICAL: Final[float] = 25.0

#: Energy-score floor that triggers a low-energy recommendation.
_ENERGY_RECO_FLOOR: Final[float] = 50.0

#: Productivity-score floor that triggers a low-productivity recommendation.
_PRODUCTIVITY_RECO_FLOOR: Final[float] = 40.0

#: Health-score floor that triggers a low-health recommendation.
_HEALTH_RECO_FLOOR: Final[float] = 50.0

#: Overall-score threshold for the "excelente" recommendation.
_OVERALL_EXCELENTE: Final[float] = 85.0

#: Overall-score threshold for the "recovery" recommendation.
_OVERALL_RECOVERY: Final[float] = 30.0

#: Sleep-debt multiplier: ``(target - hours) * factor`` (PRD-05 §4).
_SLEEP_PENALTY_FACTOR: Final[float] = 10.0

#: Health-component weight for the sleep-quality sub-score (PRD-05 §4).
_SLEEP_HEALTH_WEIGHT: Final[float] = 0.5

#: Flat exercise bonus (PRD-05 §4).
_EXERCISE_BONUS: Final[float] = 25.0

#: Maximum water-score contribution to health (PRD-05 §4).
_WATER_MAX: Final[float] = 15.0

#: Overall-score weights (ADR-004 / PRD-05 §4).
_WEIGHT_ENERGY: Final[float] = 0.3
_WEIGHT_PRODUCTIVITY: Final[float] = 0.4
_WEIGHT_HEALTH: Final[float] = 0.3

#: ID prefix for consolidator-generated MetricAlerts.
_ALERT_ID_PREFIX: Final[str] = "alt_"

#: ID prefix for consolidator-generated DailyConsolidations.
_CONSOLIDATION_ID_PREFIX: Final[str] = "cnl_"

#: UUID hex-truncation length.
_UEID_HEX_LEN: Final[int] = 12

#: Lower bound of the score space (clamp).
_SCORE_MIN: Final[float] = 0.0

#: Upper bound of the score space (clamp).
_SCORE_MAX: Final[float] = 100.0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DailyConsolidationResult:
    """In-memory result of a daily consolidation (without a :class:`DailyConsolidation`).

    The class is used by callers that need access to the four
    sub-scores, the sleep-debt hours, the alert list and the
    recommendations **without** the overhead of constructing a
    fully-validated :class:`DailyConsolidation` Pydantic model. It
    is purely a value object — no methods, no I/O.

    Attributes:
        energy_score: Energy composite in ``[0.0, 100.0]``.
        productivity_score: Productivity composite in ``[0.0, 100.0]``.
        health_score: Health composite in ``[0.0, 100.0]``.
        overall_score: Weighted overall score in ``[0.0, 100.0]``.
        sleep_debt_hours: Sleep debt in hours, ``>= 0``.
        alerts: Tuple of auto-generated :class:`MetricAlert` entities.
        recommendations: Tuple of recommendation strings (each ``<= 200`` chars).
    """

    energy_score: float
    productivity_score: float
    health_score: float
    overall_score: float
    sleep_debt_hours: float
    alerts: tuple[MetricAlert, ...]
    recommendations: tuple[str, ...]


# ---------------------------------------------------------------------------
# Sub-score formulas (PRD-05 §4)
# ---------------------------------------------------------------------------


def compute_energy_score(daily_log: DailyLog) -> float:
    r"""Compute the **energy score** in ``[0.0, 100.0]`` (PRD-05 §4).

    Formula::

        energy_map   = {H: 100, M: 60, L: 30}
        energy_score = mean(energy_map[r.level] for r in energy_readings)
        sleep_pen    = max(0, (8 - sleep.duration_hours) * 10)
        energy_score = max(0, energy_score - sleep_pen)

    The function returns ``0.0`` when the day has no energy readings
    (matches the convention used by :meth:`DailyLog.daily_score`).
    When the day has no :class:`SleepRecord`, no sleep penalty is
    applied — the energy score is the raw mean of the readings.

    Args:
        daily_log: The source :class:`DailyLog`.

    Returns:
        Energy score in ``[0.0, 100.0]``.
    """
    if not daily_log.energy_readings:
        return _SCORE_MIN
    avg = sum(
        _ENERGY_MAP[r.level.value] for r in daily_log.energy_readings
    ) / len(daily_log.energy_readings)
    if daily_log.sleep is not None:
        penalty = max(
            _SCORE_MIN,
            (_TARGET_SLEEP_HOURS - daily_log.sleep.duration_hours)
            * _SLEEP_PENALTY_FACTOR,
        )
        return max(_SCORE_MIN, avg - penalty)
    return max(_SCORE_MIN, avg)


def compute_productivity_score(daily_log: DailyLog) -> float:
    r"""Compute the **productivity score** in ``[0.0, 100.0]`` (PRD-05 §4).

    Formula::

        base       = (tasks_completed / max(tasks_created, 1)) * 60
        time_bonus = min(time_tracked_hours / 8, 1) * 25
        focus_bonus= min(pomodoros / 8, 1) * 15
        productivity_score = base + time_bonus + focus_bonus

    The ``base`` term is naturally bounded above by ``60`` (when
    completion rate ``= 1``); the two bonuses each add at most
    ``25`` and ``15`` respectively. The maximum productivity score
    is therefore ``100``.

    Args:
        daily_log: The source :class:`DailyLog`.

    Returns:
        Productivity score in ``[0.0, 100.0]``.
    """
    base = (daily_log.tasks_completed / max(daily_log.tasks_created, 1)) * 60.0
    time_bonus = min(daily_log.time_tracked_hours / _MAX_PRODUCTIVE_HOURS, 1.0) * 25.0
    focus_bonus = min(daily_log.pomodoros / _MAX_POMODOROS, 1.0) * 15.0
    return base + time_bonus + focus_bonus


def compute_health_score(daily_log: DailyLog) -> float:
    r"""Compute the **health score** in ``[0.0, 100.0]`` (PRD-05 §4).

    Formula::

        sleep_score    = sleep.quality_score * 10     (0 if no sleep)
        exercise_score = 25                            (0 if not exercised)
        water_score    = min(water_glasses / 8, 1) * 15
        health_score   = sleep_score * 0.5 + exercise_score + water_score

    The maximum is ``50 (sleep) + 25 (exercise) + 15 (water) = 90``.
    The minimum is ``0`` (no sleep + no exercise + no water).

    Args:
        daily_log: The source :class:`DailyLog`.

    Returns:
        Health score in ``[0.0, 100.0]``.
    """
    sleep_score = daily_log.sleep.quality_score * 10.0 if daily_log.sleep else 0.0
    exercise_score = _EXERCISE_BONUS if daily_log.exercise_done else 0.0
    water_score = min(daily_log.water_glasses / _TARGET_WATER_GLASSES, 1.0) * _WATER_MAX
    return (sleep_score * _SLEEP_HEALTH_WEIGHT) + exercise_score + water_score


def compute_overall_score(energy: float, productivity: float, health: float) -> float:
    r"""Compute the **overall weighted score** in ``[0.0, 100.0]`` (ADR-004).

    Formula (PRD-05 §4)::

        overall = energy * 0.3 + productivity * 0.4 + health * 0.3

    The inputs are clamped to ``[0.0, 100.0]`` defensively; the
    formula is linear and would not produce values outside that
    range for the well-formed sub-scores returned by
    :func:`compute_energy_score`, :func:`compute_productivity_score`,
    and :func:`compute_health_score`.

    Args:
        energy: Energy sub-score in ``[0.0, 100.0]``.
        productivity: Productivity sub-score in ``[0.0, 100.0]``.
        health: Health sub-score in ``[0.0, 100.0]``.

    Returns:
        Overall weighted score in ``[0.0, 100.0]``.
    """
    e = max(_SCORE_MIN, min(_SCORE_MAX, energy))
    p = max(_SCORE_MIN, min(_SCORE_MAX, productivity))
    h = max(_SCORE_MIN, min(_SCORE_MAX, health))
    return e * _WEIGHT_ENERGY + p * _WEIGHT_PRODUCTIVITY + h * _WEIGHT_HEALTH


def compute_sleep_debt(daily_log: DailyLog) -> float:
    r"""Compute the **sleep debt** in hours (PRD-05 §4).

    Formula::

        sleep_debt = 0                  if sleep.duration_hours >= 8
                    = 8 - hours          if sleep.duration_hours <  8
                    = 8                  if no sleep record

    Args:
        daily_log: The source :class:`DailyLog`.

    Returns:
        Sleep debt in hours, ``>= 0``. ``8.0`` when no sleep record.
    """
    if daily_log.sleep is None:
        return _TARGET_SLEEP_HOURS
    return max(_SCORE_MIN, _TARGET_SLEEP_HOURS - daily_log.sleep.duration_hours)


# ---------------------------------------------------------------------------
# Alert generator (PRD-05 §5)
# ---------------------------------------------------------------------------


def _new_alert_id() -> str:
    """Generate a fresh :class:`MetricAlert` id with the standard prefix."""
    return f"{_ALERT_ID_PREFIX}{uuid4().hex[:_UEID_HEX_LEN]}"


def generate_alerts(
    sleep_debt_hours: float,
    habit_compliance_pct: float,
    productivity_score: float,
    *,
    now: datetime | None = None,
) -> list[MetricAlert]:
    """Generate :class:`MetricAlert` entities per PRD-05 §5 thresholds.

    The function evaluates three independent alert families and
    returns a list with zero to three entries, ordered by
    **severity** (CRITICAL before WARNING). The alert ID, the
    ``created_at`` timestamp, and the human-readable message are
    auto-generated; the ``resolved`` flag defaults to ``False``.

    The alert families and thresholds are:

    * **Sleep debt** — ``WARNING`` above ``4.0h``, ``CRITICAL`` above
      ``8.0h``.
    * **Habit compliance** — ``WARNING`` below ``60%``,
      ``CRITICAL`` below ``40%``.
    * **Productivity score** — ``WARNING`` below ``40.0``,
      ``CRITICAL`` below ``25.0``.

    Args:
        sleep_debt_hours: Sleep debt in hours (``>= 0``).
        habit_compliance_pct: Habit compliance in percent
            (``[0.0, 100.0]``).
        productivity_score: Productivity score (``[0.0, 100.0]``).
        now: Optional explicit timestamp for the ``created_at``
            field. Defaults to :func:`datetime.now` (naive UTC) when
            ``None``; tests pass an explicit value for determinism.

    Returns:
        A list of :class:`MetricAlert` entities (may be empty).
    """
    alerts: list[MetricAlert] = []
    timestamp = now if now is not None else datetime.now()  # noqa: DTZ005

    # Sleep-debt alerts (CRITICAL first, then WARNING).
    if sleep_debt_hours > _SLEEP_DEBT_CRITICAL:
        alerts.append(
            MetricAlert(
                id=_new_alert_id(),
                level=AlertLevel.CRITICAL,
                metric="sleep_debt_hours",
                message=(
                    f"Sleep debt {sleep_debt_hours:.1f}h exceeds "
                    f"{_SLEEP_DEBT_CRITICAL:.0f}h threshold"
                ),
                value=sleep_debt_hours,
                threshold=_SLEEP_DEBT_CRITICAL,
                created_at=timestamp,
            )
        )
    elif sleep_debt_hours > _SLEEP_DEBT_WARN:
        alerts.append(
            MetricAlert(
                id=_new_alert_id(),
                level=AlertLevel.WARNING,
                metric="sleep_debt_hours",
                message=(
                    f"Sleep debt {sleep_debt_hours:.1f}h exceeds "
                    f"{_SLEEP_DEBT_WARN:.0f}h threshold"
                ),
                value=sleep_debt_hours,
                threshold=_SLEEP_DEBT_WARN,
                created_at=timestamp,
            )
        )

    # Habit-compliance alerts (CRITICAL first, then WARNING).
    if habit_compliance_pct < _HABIT_COMPLIANCE_CRITICAL:
        alerts.append(
            MetricAlert(
                id=_new_alert_id(),
                level=AlertLevel.CRITICAL,
                metric="habit_compliance_pct",
                message=(
                    f"Habit compliance {habit_compliance_pct:.0f}% below "
                    f"{_HABIT_COMPLIANCE_CRITICAL:.0f}%"
                ),
                value=habit_compliance_pct,
                threshold=_HABIT_COMPLIANCE_CRITICAL,
                created_at=timestamp,
            )
        )
    elif habit_compliance_pct < _HABIT_COMPLIANCE_WARN:
        alerts.append(
            MetricAlert(
                id=_new_alert_id(),
                level=AlertLevel.WARNING,
                metric="habit_compliance_pct",
                message=(
                    f"Habit compliance {habit_compliance_pct:.0f}% below "
                    f"{_HABIT_COMPLIANCE_WARN:.0f}%"
                ),
                value=habit_compliance_pct,
                threshold=_HABIT_COMPLIANCE_WARN,
                created_at=timestamp,
            )
        )

    # Productivity alerts (CRITICAL first, then WARNING).
    if productivity_score < _PRODUCTIVITY_CRITICAL:
        alerts.append(
            MetricAlert(
                id=_new_alert_id(),
                level=AlertLevel.CRITICAL,
                metric="productivity_score",
                message=(
                    f"Productivity score {productivity_score:.1f} below "
                    f"{_PRODUCTIVITY_CRITICAL:.0f}"
                ),
                value=productivity_score,
                threshold=_PRODUCTIVITY_CRITICAL,
                created_at=timestamp,
            )
        )
    elif productivity_score < _PRODUCTIVITY_WARN:
        alerts.append(
            MetricAlert(
                id=_new_alert_id(),
                level=AlertLevel.WARNING,
                metric="productivity_score",
                message=(
                    f"Productivity score {productivity_score:.1f} below "
                    f"{_PRODUCTIVITY_WARN:.0f}"
                ),
                value=productivity_score,
                threshold=_PRODUCTIVITY_WARN,
                created_at=timestamp,
            )
        )

    return alerts


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def generate_recommendations(
    energy_score: float,
    productivity_score: float,
    health_score: float,
    overall_score: float,
) -> list[str]:
    """Generate a list of short recommendation strings (PRD-05 §4).

    The function emits a recommendation for every sub-score below
    its corresponding recovery floor (``50`` for energy and health,
    ``40`` for productivity) and one extra recommendation for
    exceptional overall scores (above ``85`` = "excelente", below
    ``30`` = "recovery day").

    The recommendations are returned in a fixed order: low energy
    → low productivity → low health → excellent → recovery. Callers
    that need a different ordering can sort the list themselves.

    Args:
        energy_score: Energy sub-score in ``[0.0, 100.0]``.
        productivity_score: Productivity sub-score in ``[0.0, 100.0]``.
        health_score: Health sub-score in ``[0.0, 100.0]``.
        overall_score: Overall weighted score in ``[0.0, 100.0]``.

    Returns:
        A list of recommendation strings (may be empty). Each
        string is at most 200 characters.
    """
    recs: list[str] = []
    if energy_score < _ENERGY_RECO_FLOOR:
        recs.append("Considere dormir mais cedo hoje")
    if productivity_score < _PRODUCTIVITY_RECO_FLOOR:
        recs.append("Investigar bloqueios de produtividade")
    if health_score < _HEALTH_RECO_FLOOR:
        recs.append("Revisar habitos de saude (agua, exercicio, sono)")
    if overall_score >= _OVERALL_EXCELENTE:
        recs.append("Excelente! Manter a rotina")
    elif overall_score < _OVERALL_RECOVERY:
        recs.append("Considerar dia de recuperacao")
    return recs


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def consolidate_daily(
    daily_log: DailyLog,
    on_date: date | None = None,
    *,
    now: datetime | None = None,
) -> DailyConsolidation:
    """Consolidate a :class:`DailyLog` into a :class:`DailyConsolidation` (PRD-05 §4-§5).

    The function is the canonical entry point for the consolidator
    layer. It:

    1. Computes the four sub-scores (:func:`compute_energy_score`,
       :func:`compute_productivity_score`,
       :func:`compute_health_score`,
       :func:`compute_overall_score`).
    2. Computes the sleep debt (:func:`compute_sleep_debt`).
    3. Generates the alert list (:func:`generate_alerts`).
    4. Generates the recommendation list (:func:`generate_recommendations`).
    5. Bundles everything into a fully-validated
       :class:`DailyConsolidation` (Pydantic v2 strict mode).

    The trend fields (``productivity_trend``, ``energy_trend``) are
    left at their default ``None`` values — the 7-day rolling
    window is the responsibility of the weekly aggregator
    (out of scope for this module).

    Args:
        daily_log: The source :class:`DailyLog`.
        on_date: Date the consolidation refers to. Defaults to
            :attr:`DailyLog.date`.
        now: Optional explicit timestamp for the ``created_at``
            field of the consolidation and its alerts. Defaults to
            :func:`datetime.now` (naive UTC) when ``None``; tests
            pass an explicit value for determinism.

    Returns:
        A fully-validated :class:`DailyConsolidation` with the
        four sub-scores, the overall score, the sleep debt, the
        auto-generated alerts and recommendations, and a
        reference back to ``daily_log.id``.
    """
    energy = compute_energy_score(daily_log)
    productivity = compute_productivity_score(daily_log)
    health = compute_health_score(daily_log)
    overall = compute_overall_score(energy, productivity, health)
    sleep_debt = compute_sleep_debt(daily_log)
    alerts = generate_alerts(
        sleep_debt,
        daily_log.habit_compliance_pct,
        productivity,
        now=now,
    )
    recs = generate_recommendations(energy, productivity, health, overall)
    timestamp = now if now is not None else datetime.now()  # noqa: DTZ005

    return DailyConsolidation(
        id=f"{_CONSOLIDATION_ID_PREFIX}{uuid4().hex[:_UEID_HEX_LEN]}",
        date=on_date if on_date is not None else daily_log.date,
        daily_log_id=daily_log.id,
        energy_score=energy,
        productivity_score=productivity,
        health_score=health,
        sleep_debt_hours=sleep_debt,
        productivity_trend=None,
        energy_trend=None,
        alerts=alerts,
        recommendations=recs,
        created_at=timestamp,
    )


# ---------------------------------------------------------------------------
# Namespace class
# ---------------------------------------------------------------------------


class Consolidator:
    """Namespace class for the daily-consolidation service.

    The class has no instance state — every method is a
    ``@staticmethod`` that delegates to the module-level functions.
    It is provided as the canonical API surface for callers that
    prefer the class-method form (``Consolidator.consolidate(log)``)
    over the module-level form (``consolidate_daily(log)``).

    The class form mirrors the convention established by
    :class:`operational.core.sleep_calculator.SleepQuality` and is
    exposed through ``operational.__init__`` for ergonomic imports.
    """

    @staticmethod
    def consolidate(
        daily_log: DailyLog,
        on_date: date | None = None,
        *,
        now: datetime | None = None,
    ) -> DailyConsolidation:
        """Consolidate a daily log. Delegates to :func:`consolidate_daily`.

        Args:
            daily_log: The source :class:`DailyLog`.
            on_date: Date the consolidation refers to. Defaults to
                :attr:`DailyLog.date`.
            now: Optional explicit timestamp for deterministic tests.

        Returns:
            A fully-validated :class:`DailyConsolidation`.
        """
        return consolidate_daily(daily_log, on_date, now=now)

    @staticmethod
    def compute_energy(daily_log: DailyLog) -> float:
        """Delegate to :func:`compute_energy_score`."""
        return compute_energy_score(daily_log)

    @staticmethod
    def compute_productivity(daily_log: DailyLog) -> float:
        """Delegate to :func:`compute_productivity_score`."""
        return compute_productivity_score(daily_log)

    @staticmethod
    def compute_health(daily_log: DailyLog) -> float:
        """Delegate to :func:`compute_health_score`."""
        return compute_health_score(daily_log)

    @staticmethod
    def compute_overall(energy: float, productivity: float, health: float) -> float:
        """Delegate to :func:`compute_overall_score`."""
        return compute_overall_score(energy, productivity, health)

    @staticmethod
    def compute_sleep_debt(daily_log: DailyLog) -> float:
        """Delegate to :func:`compute_sleep_debt`."""
        return compute_sleep_debt(daily_log)
