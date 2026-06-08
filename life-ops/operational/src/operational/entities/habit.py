r"""Habit domain entities (PRD-02 §2-3, PAV §6, Points_of_premisses §X).

This module defines the **leaf Pydantic models** that power the habit
engine. Three entities are exposed:

* :class:`Habit` — the static definition of a habit (resistance,
  learning rate, weight, frequency).
* :class:`HabitState` — the daily state of a single habit (streak,
  completion, effort) plus the computed :data:`habit_level`,
  :data:`energy_required` and :data:`efficiency_ratio`.
* :class:`QHEMetrics` — the daily quality-habit-effectiveness snapshot
  (Q_HE formula + predicted regime).

All three are part of the ``operational.entities`` package and are
intentionally **leaves** of the import graph — no other operational
module imports from them, and they import only from
``operational.constants``, ``operational.enums`` and
``operational.types``.

Source documents:

* **PRD-02 §2** — :class:`Habit` and :class:`HabitState` shape, fields,
  and constraints.
* **PRD-02 §3** — :class:`QHEMetrics` formula and thresholding.
* **PAV §6** — the four-state policy FSM and the regime-prediction rule
  derived from Q_HE.
* **Points_of_premisses §X** — Q_HE formula and weights, regime bands.
* **ADR-003 / time-lengths §9.2** — ``lambda = 0.093`` (default learning
  rate) → :data:`operational.constants.DEFAULT.LAMBDA_LEARNING_DEFAULT`.

Formulas (verbatim from the source specs):

* :math:`H(t) = 1 - e^{-\lambda \cdot s}` — habit consolidation level.
* :math:`E_{req} = R \cdot (1 - H(t))` — energy required to perform.
* :math:`Q_{HE} = (\sum_i w_i H_i / \sum_i w_i) \cdot (E/E_{max})
  \cdot (1 + \eta \cdot S_{bonus})` — quality-habit-effectiveness.

Conventions:

* Pydantic v2 strict mode (``frozen`` / ``extra="forbid"`` /
  ``validate_assignment``).
* Google-style docstrings, line-length 100, ``__all__`` explicit.
* No business logic — pure data containers with invariants.
"""
from __future__ import annotations

import math
from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from operational.constants import DEFAULT
from operational.enums import HabitCategory, PolicyState
from operational.types import UEID  # noqa: TC001  (used as Pydantic field type at runtime)

# Local aliases to disambiguate ``date`` from the ``HabitState.date`` and
# ``QHEMetrics.date`` model fields. Without these aliases, mypy (with
# ``from __future__ import annotations``) resolves the bare ``date``
# type to the enclosing class field rather than the stdlib class.
DateT = date

__all__ = ["Habit", "HabitState", "QHEMetrics"]


# ---------------------------------------------------------------------------
# Module-level validation constants
# ---------------------------------------------------------------------------

#: Default resistance placeholder for :class:`HabitState` computed fields
#: when the parent :class:`Habit` is not available. Equal to the
#: midpoint of the [0, 10] range.
_HABIT_RESISTANCE_PLACEHOLDER: float = 5.0

#: Maximum length of a habit name (PRD-02 §2).
_HABIT_NAME_MAX: int = 100

#: Maximum length of a habit description (PRD-02 §2).
_HABIT_DESCRIPTION_MAX: int = 500


# ---------------------------------------------------------------------------
# Habit
# ---------------------------------------------------------------------------


class Habit(BaseModel):
    r"""A habit to be tracked (PRD-02 §2, PAV §6).

    A :class:`Habit` is the **static definition** of a behaviour loop.
    It captures the resistance (``R``), the learning rate (``λ``) and
    the relative weight (``w_i``) used by the QHE aggregator.

    This model is **frozen** — once defined, a habit is immutable. To
    "edit" a habit, archive the old one and create a new one. (The
    ``archived`` flag is the *only* mutable bit, but it is not exposed
    for in-place mutation: archiving is a domain operation handled by
    the persistence layer, not by the entity.)

    Attributes:
        id: Universal Entity ID (:data:`UEID`). Convention:
            ``"hab_<slug>"`` (e.g. ``"hab_sleep_8h"``).
        name: Human-readable name. 1-100 chars.
        category: One of :class:`HabitCategory` — drives balance analysis.
        resistance: ``R`` in :math:`E_{req} = R \cdot (1 - H(t))`.
            Range: 0 (effortless) to 10 (extremely hard).
        lambda_learning: ``λ`` in :math:`H(t) = 1 - e^{-\lambda s}`.
            Range: 0 to 1. Default: :data:`DEFAULT.LAMBDA_LEARNING_DEFAULT`
            (= 0.093 from ADR-003).
        weight_in_qhe: ``w_i`` in the QHE aggregator. Range: 0 to 1.
            The sum of all weights across all habits **must** equal 1.0
            for the formula to be a true convex combination. This entity
            does not enforce the cross-entity sum (a single habit may
            have ``weight=0.3``); the aggregator enforces it.
        frequency: One of ``"DAILY"`` / ``"WEEKLY"`` / ``"WAVE"``.
            ``WAVE`` is a 15-day cycle used by the original PAV
            schedule.
        target_streak: Optional target streak. Used by the report
            layer to colour the streak bar.
        description: Free-form notes. Max 500 chars.
        created_at: Wall-clock timestamp at construction. Required.
        archived: ``True`` if the habit is no longer active. Default
            ``False``. The field is **not** mutated in place; the
            domain layer is expected to copy the model with the new
            flag value.

    Raises:
        ValidationError: If any constraint is violated.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    id: UEID
    name: Annotated[str, Field(min_length=1, max_length=_HABIT_NAME_MAX)]
    category: HabitCategory
    resistance: Annotated[float, Field(ge=0.0, le=10.0)]
    lambda_learning: Annotated[float, Field(ge=0.0, le=1.0)] = (
        DEFAULT.LAMBDA_LEARNING_DEFAULT
    )
    weight_in_qhe: Annotated[float, Field(ge=0.0, le=1.0)]
    frequency: Literal["DAILY", "WEEKLY", "WAVE"] = "DAILY"
    target_streak: Annotated[int, Field(ge=0)] | None = None
    description: Annotated[str, Field(default="", max_length=_HABIT_DESCRIPTION_MAX)]
    created_at: datetime
    archived: bool = False

    @field_validator("name")
    @classmethod
    def _validate_name_not_blank(cls, value: str) -> str:
        """Reject blank or whitespace-only names.

        ``min_length=1`` already rejects empty strings, but allows a
        string of pure whitespace, which is not a useful name. This
        validator normalises and rejects whitespace-only inputs.

        Args:
            value: The name supplied by the caller.

        Returns:
            The stripped name.

        Raises:
            ValueError: If the name is empty after stripping.
        """
        stripped = value.strip()
        if not stripped:
            msg = "Habit.name must contain at least one non-whitespace character"
            raise ValueError(msg)
        return stripped

    @classmethod
    def from_pav_defaults(
        cls,
        name: str,
        category: HabitCategory,
        resistance: float,
        weight_in_qhe: float,
        **overrides: Any,  # noqa: ANN401
    ) -> Habit:
        """Factory: build a :class:`Habit` from PAV defaults.

        The factory pre-fills:

        * ``id`` → ``"hab_<12 hex chars>"`` (deterministic-enough
          for unit tests, not cryptographically unique).
        * ``lambda_learning`` →
          :data:`DEFAULT.LAMBDA_LEARNING_DEFAULT`.
        * ``created_at`` → ``datetime.now(tz=UTC)``.
        * ``archived`` → ``False``.

        The caller can override any of those (or add new fields such as
        ``frequency``, ``description``, ``target_streak``) through
        ``**overrides``.

        Args:
            name: Human-readable habit name.
            category: :class:`HabitCategory` value.
            resistance: ``R`` in [0.0, 10.0].
            weight_in_qhe: ``w_i`` in [0.0, 1.0].
            **overrides: Additional keyword arguments forwarded to the
                :class:`Habit` constructor. ``id``, ``lambda_learning``,
                ``created_at`` and ``archived`` are sensible overrides.

        Returns:
            A fully-validated :class:`Habit` instance.

        Raises:
            ValidationError: If any constraint is violated.
        """
        defaults: dict[str, Any] = {
            "id": f"hab_{uuid4().hex[:12]}",
            "name": name,
            "category": category,
            "resistance": resistance,
            "lambda_learning": DEFAULT.LAMBDA_LEARNING_DEFAULT,
            "weight_in_qhe": weight_in_qhe,
            "created_at": datetime.now(tz=UTC),
            "archived": False,
        }
        defaults.update(overrides)
        return cls(**defaults)


# ---------------------------------------------------------------------------
# HabitState
# ---------------------------------------------------------------------------


class HabitState(BaseModel):
    r"""Daily state of a single habit (PRD-02 §2).

    A :class:`HabitState` records the completion, current streak, and
    effort spent on a :class:`Habit` for a single date. It also exposes
    three **computed fields** that drive the QHE aggregator:

    * :data:`habit_level` — :math:`H(t) = 1 - e^{-\lambda s}` in [0, 1].
    * :data:`energy_required` — :math:`E_{req} = R \cdot (1 - H(t))`.
    * :data:`efficiency_ratio` — :math:`H(t) / (1 + E_{req})`.

    This model is **frozen** — daily states are immutable records.

    .. note::

        The computed fields depend on the parent :class:`Habit`'s
        ``lambda_learning`` (``λ``) and ``resistance`` (``R``).
        Since :class:`HabitState` is intentionally a leaf entity (no
        cross-entity reference), we use the **canonical defaults** from
        :mod:`operational.constants`:

        * ``λ = DEFAULT.LAMBDA_LEARNING_DEFAULT`` (= 0.093).
        * ``R = 5.0`` (midpoint placeholder).

        The aggregator at the application layer is expected to
        override these via a service-level composition that knows the
        parent :class:`Habit`. The computed fields are useful for
        ad-hoc reporting and tests even with the placeholder values.

    Attributes:
        id: Universal Entity ID (:data:`UEID`). Convention:
            ``"hst_<habit>_<date>"``.
        habit_id: :data:`UEID` of the parent :class:`Habit`.
        date: Calendar date the state refers to (local time).
        completed: ``True`` if the habit was completed on this date.
        streak_current: Current consecutive-days streak. 0+.
        streak_broken_count: Lifetime count of broken streaks. 0+.
        effort_minutes: Actual minutes spent on the habit. 0+.

    Raises:
        ValidationError: If any constraint is violated.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    id: UEID
    habit_id: UEID
    date: date
    completed: bool
    streak_current: Annotated[int, Field(ge=0)] = 0
    streak_broken_count: Annotated[int, Field(ge=0)] = 0
    effort_minutes: Annotated[int, Field(ge=0)] = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def habit_level(self) -> float:
        r"""Habit consolidation level :math:`H(t) = 1 - e^{-\lambda s}`.

        Uses the canonical default learning rate
        (:data:`DEFAULT.LAMBDA_LEARNING_DEFAULT`) since the parent
        :class:`Habit` is not in scope. The aggregator can recompute
        the value with the parent habit's actual ``lambda_learning``.

        Returns:
            ``float`` in :math:`[0.0, 1.0]`. ``0.0`` at streak 0, tending
            to ``1.0`` as the streak grows.
        """
        lam: float = DEFAULT.LAMBDA_LEARNING_DEFAULT
        return 1.0 - math.exp(-lam * self.streak_current)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def energy_required(self) -> float:
        r"""Energy required to perform :math:`E_{req} = R \cdot (1 - H(t))`.

        Uses a placeholder ``R = 5.0`` (midpoint of the [0, 10] range)
        since the parent :class:`Habit` is not in scope. The aggregator
        can recompute the value with the parent habit's actual
        ``resistance``.

        Returns:
            ``float`` in :math:`[0.0, 10.0]`. Higher when the habit is
            new (``H(t) ≈ 0``) and lower once the habit is consolidated.
        """
        return _HABIT_RESISTANCE_PLACEHOLDER * (1.0 - self.habit_level)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def efficiency_ratio(self) -> float:
        """Efficiency ratio :math:`H(t) / (1 + E_{req})`.

        Returns:
            ``float`` ≥ 0. The ratio is in :math:`[0, 1]` for typical
            values of ``H(t)`` and :math:`E_{req}`.
        """
        return self.habit_level / (1.0 + self.energy_required)

    @classmethod
    def for_completed(
        cls,
        habit_id: UEID,
        on_date: DateT,
        *,
        streak_current: int = 1,
        effort_minutes: int = 0,
    ) -> HabitState:
        """Factory: a completed :class:`HabitState` for ``on_date``.

        Convenience for tests and ad-hoc scaffolding. Generates a
        deterministic ``id`` of the form ``"hst_<habit>_<yyyymmdd>"``.

        Args:
            habit_id: :data:`UEID` of the parent :class:`Habit`.
            on_date: Calendar date.
            streak_current: Current streak. Default 1.
            effort_minutes: Actual effort. Default 0.

        Returns:
            A fully-validated :class:`HabitState` with
            ``completed=True``.
        """
        date_slug: str = on_date.strftime("%Y%m%d")
        return cls(
            id=f"hst_{habit_id}_{date_slug}",
            habit_id=habit_id,
            date=on_date,
            completed=True,
            streak_current=streak_current,
            streak_broken_count=0,
            effort_minutes=effort_minutes,
        )

    @classmethod
    def for_missed(
        cls,
        habit_id: UEID,
        on_date: DateT,
        *,
        streak_current: int = 0,
        streak_broken_count: int = 0,
    ) -> HabitState:
        """Factory: a missed :class:`HabitState` for ``on_date``.

        Args:
            habit_id: :data:`UEID` of the parent :class:`Habit`.
            on_date: Calendar date.
            streak_current: Current streak (typically 0 after a miss).
            streak_broken_count: Lifetime broken-streak count. Default 0.

        Returns:
            A fully-validated :class:`HabitState` with
            ``completed=False``.
        """
        date_slug: str = on_date.strftime("%Y%m%d")
        return cls(
            id=f"hst_{habit_id}_{date_slug}",
            habit_id=habit_id,
            date=on_date,
            completed=False,
            streak_current=streak_current,
            streak_broken_count=streak_broken_count,
            effort_minutes=0,
        )


# ---------------------------------------------------------------------------
# QHEMetrics
# ---------------------------------------------------------------------------


class QHEMetrics(BaseModel):
    r"""Quality-Habit-Effectiveness daily snapshot (PRD-02 §3).

    Captures the four inputs of the QHE formula and exposes two
    **computed fields** — the QHE value itself and the predicted
    operational regime.

    The QHE formula is:

    .. math::

        Q_{HE} = \left(\frac{\sum_i w_i \cdot H_i}{\sum_i w_i}\right)
                  \cdot \left(\frac{E(t)}{E_{max}}\right)
                  \cdot \left(1 + \eta \cdot S_{bonus}\right)

    The regime is predicted by the same thresholds the policy FSM uses
    (:data:`DEFAULT.QHE_PUSH_THRESHOLD` and
    :data:`DEFAULT.QHE_RECOVER_THRESHOLD`).

    This model is **frozen** — daily metrics are immutable records.

    Attributes:
        id: Universal Entity ID (:data:`UEID`). Convention:
            ``"qhe_<date>"``.
        date: Calendar date the snapshot refers to.
        habit_avg: Weighted habit-consolidation level in [0, 1].
        consistency: Fraction of habits completed on this date in [0, 1].
        streak_bonus: Normalised streak bonus in [0, 1]
            (e.g. ``avg_streak / max_streak``).
        energy_ratio: Current energy / max energy in [0, 1].
        eta: Streak-bonus multiplier in [0, 1]. Default 0.5.

    Raises:
        ValidationError: If any constraint is violated.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    id: UEID
    date: date
    habit_avg: Annotated[float, Field(ge=0.0, le=1.0)]
    consistency: Annotated[float, Field(ge=0.0, le=1.0)]
    streak_bonus: Annotated[float, Field(ge=0.0, le=1.0)]
    energy_ratio: Annotated[float, Field(ge=0.0, le=1.0)]
    eta: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5

    @computed_field  # type: ignore[prop-decorator]
    @property
    def qhe(self) -> float:
        r"""Quality-Habit-Effectiveness value.

        :math:`Q_{HE} = habit\_avg \cdot energy\_ratio
        \cdot (1 + \eta \cdot streak\_bonus)`.

        Returns:
            ``float`` ≥ 0. The product is naturally in [0, 2] but
            typical operational values stay in [0, 1].
        """
        return self.habit_avg * self.energy_ratio * (1.0 + self.eta * self.streak_bonus)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def regime_predicted(self) -> PolicyState:
        """Predict the operational regime from :data:`qhe`.

        * ``QHE >= DEFAULT.QHE_PUSH_THRESHOLD`` → :attr:`PolicyState.PUSH`.
        * ``QHE < DEFAULT.QHE_RECOVER_THRESHOLD`` →
          :attr:`PolicyState.RECOVER`.
        * Otherwise → :attr:`PolicyState.MAINTAIN`.

        The 4th policy state, :attr:`PolicyState.REDUCE`, is not
        produced by the QHE predictor — it is reached only by explicit
        domain logic (e.g. sustained sleep deficit) and never by the
        snapshot alone.

        Returns:
            The :class:`PolicyState` the FSM should adopt.
        """
        if self.qhe >= DEFAULT.QHE_PUSH_THRESHOLD:
            return PolicyState.PUSH
        if self.qhe < DEFAULT.QHE_RECOVER_THRESHOLD:
            return PolicyState.RECOVER
        return PolicyState.MAINTAIN

    @classmethod
    def for_perfect_day(cls, on_date: DateT) -> QHEMetrics:
        """Factory: a perfect-day :class:`QHEMetrics` (all inputs = 1.0).

        Useful for tests and for upper-bound sanity checks.

        Args:
            on_date: Calendar date.

        Returns:
            A :class:`QHEMetrics` with all inputs = 1.0 and ``eta = 0.5``.
        """
        date_slug: str = on_date.strftime("%Y%m%d")
        return cls(
            id=f"qhe_{date_slug}",
            date=on_date,
            habit_avg=1.0,
            consistency=1.0,
            streak_bonus=1.0,
            energy_ratio=1.0,
            eta=0.5,
        )

    @classmethod
    def for_zero_day(cls, on_date: DateT) -> QHEMetrics:
        """Factory: a zero-day :class:`QHEMetrics` (all inputs = 0.0).

        Args:
            on_date: Calendar date.

        Returns:
            A :class:`QHEMetrics` with all inputs = 0.0.
        """
        date_slug: str = on_date.strftime("%Y%m%d")
        return cls(
            id=f"qhe_{date_slug}",
            date=on_date,
            habit_avg=0.0,
            consistency=0.0,
            streak_bonus=0.0,
            energy_ratio=0.0,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable :class:`dict` view of the model.

        Computed fields (``qhe`` and ``regime_predicted``) are
        included in the output, so downstream consumers do not need to
        recompute them.

        Returns:
            Plain :class:`dict` ready for ``json.dumps``.
        """
        return self.model_dump(mode="json")
