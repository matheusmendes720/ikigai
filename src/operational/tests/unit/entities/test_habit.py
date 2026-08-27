"""Comprehensive unit tests for ``operational.entities.habit``.

Covers:

* :class:`Habit` — construction, field ranges, frequency literal,
  ``from_pav_defaults`` factory, ``archived`` default, immutability,
  JSON roundtrip.
* :class:`HabitState` — construction, field ranges, computed fields
  (``habit_level``, ``energy_required``, ``efficiency_ratio``),
  ``for_completed`` / ``for_missed`` factories, immutability,
  JSON roundtrip.
* :class:`QHEMetrics` — construction, field ranges, ``eta`` default,
  ``qhe`` formula (parametric), ``regime_predicted`` mapping for
  PUSH / RECOVER / MAINTAIN, ``for_perfect_day`` / ``for_zero_day``
  factories, immutability, JSON roundtrip.

All math is verified against the source formulas from PRD-02 §2-3 and
PAV §6.
"""
from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from operational.constants import DEFAULT
from operational.entities.habit import Habit, HabitState, QHEMetrics
from operational.enums import HabitCategory, PolicyState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_habit_kwargs(**overrides: Any) -> dict[str, Any]:
    """Return a baseline :class:`Habit` kwargs dict.

    Args:
        **overrides: Field-level overrides merged on top of the
            baseline.

    Returns:
        :class:`dict` ready to splat into ``Habit(**kwargs)``.
    """
    base: dict[str, Any] = {
        "id": "hab_morning_meditation",
        "name": "Morning meditation",
        "category": HabitCategory.RITUAL,
        "resistance": 4.0,
        "weight_in_qhe": 0.2,
        "created_at": datetime(2026, 6, 7, 5, 0, 0),
    }
    base.update(overrides)
    return base


def _base_state_kwargs(**overrides: Any) -> dict[str, Any]:
    """Return a baseline :class:`HabitState` kwargs dict.

    Args:
        **overrides: Field-level overrides merged on top of the
            baseline.

    Returns:
        :class:`dict` ready to splat into ``HabitState(**kwargs)``.
    """
    base: dict[str, Any] = {
        "id": "hst_hab_morning_meditation_20260607",
        "habit_id": "hab_morning_meditation",
        "date": date(2026, 6, 7),
        "completed": True,
        "streak_current": 5,
        "streak_broken_count": 1,
        "effort_minutes": 15,
    }
    base.update(overrides)
    return base


def _base_qhe_kwargs(**overrides: Any) -> dict[str, Any]:
    """Return a baseline :class:`QHEMetrics` kwargs dict.

    Args:
        **overrides: Field-level overrides merged on top of the
            baseline.

    Returns:
        :class:`dict` ready to splat into ``QHEMetrics(**kwargs)``.
    """
    base: dict[str, Any] = {
        "id": "qhe_20260607",
        "date": date(2026, 6, 7),
        "habit_avg": 0.6,
        "consistency": 0.7,
        "streak_bonus": 0.5,
        "energy_ratio": 0.8,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Habit — construction & ranges
# ---------------------------------------------------------------------------


class TestHabitConstruction:
    """Build a :class:`Habit` from valid kwargs."""

    def test_create_habit_minimal(self) -> None:
        """A minimal habit (only required fields) is valid."""
        h = Habit(**_base_habit_kwargs())
        assert h.id == "hab_morning_meditation"
        assert h.name == "Morning meditation"
        assert h.category == HabitCategory.RITUAL
        assert h.resistance == 4.0
        assert h.weight_in_qhe == 0.2
        assert h.lambda_learning == DEFAULT.LAMBDA_LEARNING_DEFAULT
        assert h.frequency == "DAILY"
        assert h.target_streak is None
        assert h.description == ""
        assert h.archived is False

    @pytest.mark.parametrize("resistance", [0.0, 5.0, 10.0])
    def test_habit_resistance_range(self, resistance: float) -> None:
        """``resistance`` accepts 0.0, 5.0, 10.0 (boundaries)."""
        h = Habit(**_base_habit_kwargs(resistance=resistance))
        assert h.resistance == resistance

    @pytest.mark.parametrize("resistance", [-0.1, 10.1, 100.0, -100.0])
    def test_habit_resistance_out_of_range(self, resistance: float) -> None:
        """``resistance`` rejects values outside [0, 10]."""
        with pytest.raises(ValidationError):
            Habit(**_base_habit_kwargs(resistance=resistance))

    def test_habit_lambda_learning_default(self) -> None:
        """Default ``lambda_learning`` is 0.093 (from ``DEFAULT``)."""
        h = Habit(**_base_habit_kwargs())
        assert h.lambda_learning == 0.093
        assert h.lambda_learning == DEFAULT.LAMBDA_LEARNING_DEFAULT

    @pytest.mark.parametrize("lam", [0.0, 0.093, 0.5, 1.0])
    def test_habit_lambda_learning_range(self, lam: float) -> None:
        """``lambda_learning`` accepts 0.0, 0.093, 0.5, 1.0."""
        h = Habit(**_base_habit_kwargs(lambda_learning=lam))
        assert h.lambda_learning == lam

    @pytest.mark.parametrize("lam", [-0.1, 1.1, 2.0])
    def test_habit_lambda_learning_out_of_range(self, lam: float) -> None:
        """``lambda_learning`` rejects values outside [0, 1]."""
        with pytest.raises(ValidationError):
            Habit(**_base_habit_kwargs(lambda_learning=lam))

    @pytest.mark.parametrize("weight", [0.0, 0.2, 1.0])
    def test_habit_weight_in_qhe_range(self, weight: float) -> None:
        """``weight_in_qhe`` accepts 0.0, 0.2, 1.0."""
        h = Habit(**_base_habit_kwargs(weight_in_qhe=weight))
        assert h.weight_in_qhe == weight

    @pytest.mark.parametrize("weight", [-0.1, 1.1, 5.0])
    def test_habit_weight_in_qhe_out_of_range(self, weight: float) -> None:
        """``weight_in_qhe`` rejects values outside [0, 1]."""
        with pytest.raises(ValidationError):
            Habit(**_base_habit_kwargs(weight_in_qhe=weight))

    @pytest.mark.parametrize("frequency", ["DAILY", "WEEKLY", "WAVE"])
    def test_habit_frequency_literal(self, frequency: str) -> None:
        """``frequency`` accepts the 3 literal values."""
        h = Habit(**_base_habit_kwargs(frequency=frequency))  # type: ignore[arg-type]
        assert h.frequency == frequency

    @pytest.mark.parametrize("frequency", ["MONTHLY", "HOURLY", "daily", ""])
    def test_habit_frequency_invalid_rejected(self, frequency: str) -> None:
        """``frequency`` rejects non-literal values."""
        with pytest.raises(ValidationError):
            Habit(**_base_habit_kwargs(frequency=frequency))  # type: ignore[arg-type]

    def test_habit_name_required(self) -> None:
        """A blank name raises :class:`ValidationError`."""
        with pytest.raises(ValidationError):
            Habit(**_base_habit_kwargs(name=""))

    def test_habit_name_whitespace_only_rejected(self) -> None:
        """A whitespace-only name raises :class:`ValidationError`."""
        with pytest.raises(ValidationError) as exc_info:
            Habit(**_base_habit_kwargs(name="   "))
        assert "name" in str(exc_info.value).lower()

    def test_habit_name_max_length(self) -> None:
        """A name of 100 chars is accepted; 101 is not."""
        h = Habit(**_base_habit_kwargs(name="x" * 100))
        assert len(h.name) == 100
        with pytest.raises(ValidationError):
            Habit(**_base_habit_kwargs(name="x" * 101))

    def test_habit_description_max_length(self) -> None:
        """A description of 500 chars is accepted; 501 is not."""
        h = Habit(**_base_habit_kwargs(description="x" * 500))
        assert len(h.description) == 500
        with pytest.raises(ValidationError):
            Habit(**_base_habit_kwargs(description="x" * 501))

    def test_habit_archived_default_false(self) -> None:
        """``archived`` defaults to ``False``."""
        h = Habit(**_base_habit_kwargs())
        assert h.archived is False

    def test_habit_target_streak_optional(self) -> None:
        """``target_streak`` is optional and accepts 0+."""
        h1 = Habit(**_base_habit_kwargs())
        h2 = Habit(**_base_habit_kwargs(target_streak=30))
        h3 = Habit(**_base_habit_kwargs(target_streak=0))
        assert h1.target_streak is None
        assert h2.target_streak == 30
        assert h3.target_streak == 0

    def test_habit_target_streak_negative_rejected(self) -> None:
        """``target_streak`` rejects negatives."""
        with pytest.raises(ValidationError):
            Habit(**_base_habit_kwargs(target_streak=-1))

    def test_habit_rejects_unknown_fields(self) -> None:
        """``extra="forbid"`` rejects unknown field names."""
        with pytest.raises(ValidationError) as exc_info:
            Habit(**_base_habit_kwargs(unknown_field="boom"))
        assert "unknown_field" in str(exc_info.value)

    def test_habit_id_pattern_enforced(self) -> None:
        """``id`` must match the :data:`UEID` pattern."""
        with pytest.raises(ValidationError):
            Habit(**_base_habit_kwargs(id="BadID"))


# ---------------------------------------------------------------------------
# Habit — factory
# ---------------------------------------------------------------------------


class TestHabitFactory:
    """The :meth:`Habit.from_pav_defaults` factory."""

    def test_habit_from_pav_defaults_factory(self) -> None:
        """Factory produces a valid :class:`Habit` from minimal kwargs."""
        h = Habit.from_pav_defaults(
            name="Drink water",
            category=HabitCategory.PHYSIOLOGICAL,
            resistance=2.0,
            weight_in_qhe=0.1,
        )
        assert h.id.startswith("hab_")
        assert h.name == "Drink water"
        assert h.category == HabitCategory.PHYSIOLOGICAL
        assert h.resistance == 2.0
        assert h.weight_in_qhe == 0.1
        assert h.lambda_learning == DEFAULT.LAMBDA_LEARNING_DEFAULT
        assert h.archived is False
        assert h.frequency == "DAILY"
        assert h.target_streak is None
        assert h.description == ""

    def test_habit_from_pav_defaults_overrides(self) -> None:
        """Factory accepts overrides for any field."""
        h = Habit.from_pav_defaults(
            name="Run 5km",
            category=HabitCategory.PHYSIOLOGICAL,
            resistance=7.0,
            weight_in_qhe=0.3,
            frequency="WAVE",
            target_streak=10,
            description="morning run",
        )
        assert h.frequency == "WAVE"
        assert h.target_streak == 10
        assert h.description == "morning run"

    def test_habit_from_pav_defaults_id_unique(self) -> None:
        """Two factory calls produce two different ``id`` values."""
        h1 = Habit.from_pav_defaults(
            name="A",
            category=HabitCategory.COGNITIVE,
            resistance=3.0,
            weight_in_qhe=0.1,
        )
        h2 = Habit.from_pav_defaults(
            name="A",
            category=HabitCategory.COGNITIVE,
            resistance=3.0,
            weight_in_qhe=0.1,
        )
        assert h1.id != h2.id

    def test_habit_from_pav_defaults_created_at_recent(self) -> None:
        """Factory ``created_at`` is within ~5 seconds of ``datetime.now()``."""
        before = datetime.now(tz=UTC) - timedelta(seconds=5)
        h = Habit.from_pav_defaults(
            name="X",
            category=HabitCategory.COGNITIVE,
            resistance=3.0,
            weight_in_qhe=0.1,
        )
        after = datetime.now(tz=UTC) + timedelta(seconds=5)
        assert before <= h.created_at <= after


# ---------------------------------------------------------------------------
# Habit — immutability and JSON
# ---------------------------------------------------------------------------


class TestHabitImmutabilityAndJson:
    """A :class:`Habit` is frozen and JSON-serialisable."""

    def test_habit_is_frozen(self) -> None:
        """A :class:`Habit` cannot be mutated in place."""
        h = Habit(**_base_habit_kwargs())
        with pytest.raises(ValidationError):
            h.name = "Other"  # type: ignore[misc]

    def test_habit_json_roundtrip(self) -> None:
        """``model_dump_json()`` → ``model_validate_json()`` is lossless."""
        original = Habit(**_base_habit_kwargs())
        payload = original.model_dump_json()
        restored = Habit.model_validate_json(payload)
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.category == original.category
        assert restored.resistance == original.resistance
        assert restored.lambda_learning == original.lambda_learning
        assert restored.weight_in_qhe == original.weight_in_qhe
        assert restored.frequency == original.frequency
        assert restored.target_streak == original.target_streak
        assert restored.description == original.description
        assert restored.archived == original.archived


# ---------------------------------------------------------------------------
# HabitState — construction & ranges
# ---------------------------------------------------------------------------


class TestHabitStateConstruction:
    """Build a :class:`HabitState` from valid kwargs."""

    def test_create_habit_state_minimal(self) -> None:
        """A minimal :class:`HabitState` is valid (only required fields)."""
        s = HabitState(
            id="hst_hab_morning_meditation_20260607",
            habit_id="hab_morning_meditation",
            date=date(2026, 6, 7),
            completed=False,
        )
        assert s.streak_current == 0
        assert s.streak_broken_count == 0
        assert s.effort_minutes == 0

    def test_habit_state_completed_flag(self) -> None:
        """``completed`` is stored verbatim."""
        s_done = HabitState(**_base_state_kwargs(completed=True))
        s_skip = HabitState(**_base_state_kwargs(completed=False))
        assert s_done.completed is True
        assert s_skip.completed is False

    @pytest.mark.parametrize("streak", [0, 1, 30, 365, 10_000])
    def test_habit_state_streak_validation_accepts(self, streak: int) -> None:
        """``streak_current`` accepts 0 and any non-negative int."""
        s = HabitState(**_base_state_kwargs(streak_current=streak))
        assert s.streak_current == streak

    @pytest.mark.parametrize("streak", [-1, -100, -10_000])
    def test_habit_state_streak_validation_rejects(self, streak: int) -> None:
        """``streak_current`` rejects negatives."""
        with pytest.raises(ValidationError):
            HabitState(**_base_state_kwargs(streak_current=streak))

    def test_habit_state_streak_broken_count_default(self) -> None:
        """``streak_broken_count`` defaults to 0."""
        s = HabitState(
            id="hst_x_20260607",
            habit_id="hab_x",
            date=date(2026, 6, 7),
            completed=True,
        )
        assert s.streak_broken_count == 0

    def test_habit_state_effort_minutes_default(self) -> None:
        """``effort_minutes`` defaults to 0."""
        s = HabitState(
            id="hst_x_20260607",
            habit_id="hab_x",
            date=date(2026, 6, 7),
            completed=True,
        )
        assert s.effort_minutes == 0

    def test_habit_state_rejects_unknown_fields(self) -> None:
        """``extra="forbid"`` rejects unknown field names."""
        with pytest.raises(ValidationError) as exc_info:
            HabitState(**_base_state_kwargs(unknown_field="boom"))
        assert "unknown_field" in str(exc_info.value)

    def test_habit_state_is_frozen(self) -> None:
        """A :class:`HabitState` is frozen."""
        s = HabitState(**_base_state_kwargs())
        with pytest.raises(ValidationError):
            s.completed = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# HabitState — computed fields
# ---------------------------------------------------------------------------


class TestHabitStateComputedFields:
    """Computed fields ``habit_level``, ``energy_required``, ``efficiency_ratio``."""

    def test_habit_state_habit_level_at_streak_zero(self) -> None:
        """``habit_level`` = 0.0 at streak 0 (1 - e^0 = 0)."""
        s = HabitState(**_base_state_kwargs(streak_current=0))
        assert s.habit_level == pytest.approx(0.0, abs=1e-12)

    def test_habit_state_habit_level_formula(self) -> None:
        """``habit_level`` = 1 - exp(-lambda * streak)."""
        streak = 10
        s = HabitState(**_base_state_kwargs(streak_current=streak))
        expected: float = 1.0 - math.exp(-DEFAULT.LAMBDA_LEARNING_DEFAULT * streak)
        assert s.habit_level == pytest.approx(expected)

    @pytest.mark.parametrize("streak", [0, 1, 5, 30, 100, 365])
    def test_habit_state_habit_level_in_range(self, streak: int) -> None:
        """``habit_level`` is always in [0, 1]."""
        s = HabitState(**_base_state_kwargs(streak_current=streak))
        assert 0.0 <= s.habit_level <= 1.0

    def test_habit_state_habit_level_tends_to_one(self) -> None:
        """``habit_level`` → 1.0 as streak → infinity."""
        s = HabitState(**_base_state_kwargs(streak_current=10_000))
        assert s.habit_level == pytest.approx(1.0, abs=1e-6)

    def test_habit_state_energy_required_formula(self) -> None:
        """``energy_required`` = 5.0 * (1 - habit_level)."""
        s = HabitState(**_base_state_kwargs(streak_current=10))
        expected: float = 5.0 * (1.0 - s.habit_level)
        assert s.energy_required == pytest.approx(expected)

    def test_habit_state_energy_required_at_streak_zero(self) -> None:
        """``energy_required`` = 5.0 at streak 0 (no consolidation)."""
        s = HabitState(**_base_state_kwargs(streak_current=0))
        assert s.energy_required == pytest.approx(5.0)

    def test_habit_state_energy_required_tends_to_zero(self) -> None:
        """``energy_required`` → 0 as streak → infinity (full consolidation)."""
        s = HabitState(**_base_state_kwargs(streak_current=10_000))
        assert s.energy_required == pytest.approx(0.0, abs=1e-6)

    def test_habit_state_efficiency_ratio_formula(self) -> None:
        """``efficiency_ratio`` = habit_level / (1 + energy_required)."""
        s = HabitState(**_base_state_kwargs(streak_current=10))
        expected: float = s.habit_level / (1.0 + s.energy_required)
        assert s.efficiency_ratio == pytest.approx(expected)

    def test_habit_state_efficiency_at_streak_zero(self) -> None:
        """``efficiency_ratio`` = 0.0 at streak 0."""
        s = HabitState(**_base_state_kwargs(streak_current=0))
        assert s.efficiency_ratio == pytest.approx(0.0)

    def test_habit_state_efficiency_increases_with_streak(self) -> None:
        """``efficiency_ratio`` is monotonically non-decreasing in streak."""
        prev = -1.0
        for streak in [0, 1, 5, 10, 30, 100]:
            s = HabitState(**_base_state_kwargs(streak_current=streak))
            assert s.efficiency_ratio >= prev
            prev = s.efficiency_ratio


# ---------------------------------------------------------------------------
# HabitState — factories
# ---------------------------------------------------------------------------


class TestHabitStateFactories:
    """The ``for_completed`` / ``for_missed`` classmethod factories."""

    def test_habit_state_for_completed(self) -> None:
        """``for_completed`` returns a completed state."""
        s = HabitState.for_completed(
            habit_id="hab_morning_meditation",
            on_date=date(2026, 6, 7),
            streak_current=7,
            effort_minutes=20,
        )
        assert s.completed is True
        assert s.streak_current == 7
        assert s.effort_minutes == 20
        assert s.streak_broken_count == 0
        assert s.id == "hst_hab_morning_meditation_20260607"
        assert s.habit_id == "hab_morning_meditation"
        assert s.date == date(2026, 6, 7)

    def test_habit_state_for_completed_defaults(self) -> None:
        """``for_completed`` defaults: streak=1, effort=0."""
        s = HabitState.for_completed(
            habit_id="hab_x",
            on_date=date(2026, 6, 7),
        )
        assert s.streak_current == 1
        assert s.effort_minutes == 0

    def test_habit_state_for_missed(self) -> None:
        """``for_missed`` returns a missed state with streak=0 by default."""
        s = HabitState.for_missed(
            habit_id="hab_morning_meditation",
            on_date=date(2026, 6, 7),
        )
        assert s.completed is False
        assert s.streak_current == 0
        assert s.streak_broken_count == 0
        assert s.effort_minutes == 0
        assert s.id == "hst_hab_morning_meditation_20260607"

    def test_habit_state_for_missed_with_broken_streak(self) -> None:
        """``for_missed`` accepts a custom ``streak_broken_count``."""
        s = HabitState.for_missed(
            habit_id="hab_x",
            on_date=date(2026, 6, 7),
            streak_broken_count=3,
        )
        assert s.streak_broken_count == 3


# ---------------------------------------------------------------------------
# HabitState — JSON
# ---------------------------------------------------------------------------


class TestHabitStateJson:
    """JSON serialization roundtrip for :class:`HabitState`."""

    def test_habit_state_json_roundtrip(self) -> None:
        """JSON dump → load is lossless.

        Computed fields are excluded from the dump to satisfy
        ``extra="forbid"``.
        """
        original = HabitState(**_base_state_kwargs())
        payload = original.model_dump_json(
            exclude={"habit_level", "energy_required", "efficiency_ratio"},
        )
        restored = HabitState.model_validate_json(payload)
        assert restored.id == original.id
        assert restored.habit_id == original.habit_id
        assert restored.date == original.date
        assert restored.completed == original.completed
        assert restored.streak_current == original.streak_current
        assert restored.streak_broken_count == original.streak_broken_count
        assert restored.effort_minutes == original.effort_minutes
        # Computed fields are still derivable from the restored model.
        assert restored.habit_level == pytest.approx(original.habit_level)
        assert restored.energy_required == pytest.approx(original.energy_required)
        assert restored.efficiency_ratio == pytest.approx(original.efficiency_ratio)

    def test_habit_state_json_includes_computed(self) -> None:
        """Computed fields appear in the full JSON dump (not excluded)."""
        s = HabitState(**_base_state_kwargs())
        payload = s.model_dump_json()
        decoded: dict[str, Any] = json.loads(payload)
        assert "habit_level" in decoded
        assert "energy_required" in decoded
        assert "efficiency_ratio" in decoded


# ---------------------------------------------------------------------------
# QHEMetrics — construction & ranges
# ---------------------------------------------------------------------------


class TestQHEMetricsConstruction:
    """Build a :class:`QHEMetrics` from valid kwargs."""

    def test_create_qhe_metrics_minimal(self) -> None:
        """A minimal :class:`QHEMetrics` is valid (eta defaults)."""
        m = QHEMetrics(**_base_qhe_kwargs())
        assert m.eta == 0.5
        assert m.habit_avg == 0.6
        assert m.consistency == 0.7
        assert m.streak_bonus == 0.5
        assert m.energy_ratio == 0.8

    @pytest.mark.parametrize(
        "field_name",
        ["habit_avg", "consistency", "streak_bonus", "energy_ratio"],
    )
    @pytest.mark.parametrize("value", [0.0, 0.5, 1.0])
    def test_qhe_metrics_field_ranges(self, field_name: str, value: float) -> None:
        """All 4 input fields accept 0.0, 0.5, 1.0 (boundaries)."""
        m = QHEMetrics(**_base_qhe_kwargs(**{field_name: value}))
        assert getattr(m, field_name) == value

    @pytest.mark.parametrize(
        "field_name",
        ["habit_avg", "consistency", "streak_bonus", "energy_ratio"],
    )
    @pytest.mark.parametrize("value", [-0.1, 1.1, 2.0, -1.0])
    def test_qhe_metrics_field_out_of_range(self, field_name: str, value: float) -> None:
        """All 4 input fields reject out-of-range values."""
        with pytest.raises(ValidationError):
            QHEMetrics(**_base_qhe_kwargs(**{field_name: value}))

    def test_qhe_metrics_eta_default(self) -> None:
        """``eta`` defaults to 0.5."""
        m = QHEMetrics(**_base_qhe_kwargs())
        assert m.eta == 0.5

    @pytest.mark.parametrize("eta", [0.0, 0.5, 1.0])
    def test_qhe_metrics_eta_range(self, eta: float) -> None:
        """``eta`` accepts 0.0, 0.5, 1.0."""
        m = QHEMetrics(**_base_qhe_kwargs(eta=eta))
        assert m.eta == eta

    def test_qhe_metrics_eta_out_of_range(self) -> None:
        """``eta`` rejects out-of-range values."""
        with pytest.raises(ValidationError):
            QHEMetrics(**_base_qhe_kwargs(eta=1.1))
        with pytest.raises(ValidationError):
            QHEMetrics(**_base_qhe_kwargs(eta=-0.1))

    def test_qhe_metrics_rejects_unknown_fields(self) -> None:
        """``extra="forbid"`` rejects unknown field names."""
        with pytest.raises(ValidationError) as exc_info:
            QHEMetrics(**_base_qhe_kwargs(unknown_field="boom"))
        assert "unknown_field" in str(exc_info.value)

    def test_qhe_metrics_is_frozen(self) -> None:
        """A :class:`QHEMetrics` is frozen."""
        m = QHEMetrics(**_base_qhe_kwargs())
        with pytest.raises(ValidationError):
            m.habit_avg = 0.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# QHEMetrics — qhe formula
# ---------------------------------------------------------------------------


class TestQHEMetricsQheFormula:
    """The QHE formula and its parametric correctness."""

    def test_qhe_metrics_qhe_zero(self) -> None:
        """QHE is 0 when any of the 4 inputs is 0."""
        m = QHEMetrics.for_zero_day(date(2026, 6, 7))
        assert m.qhe == pytest.approx(0.0)

    def test_qhe_metrics_qhe_perfect_day(self) -> None:
        """QHE = 1.0 * 1.0 * (1 + 0.5 * 1.0) = 1.5 at perfect day."""
        m = QHEMetrics.for_perfect_day(date(2026, 6, 7))
        assert m.qhe == pytest.approx(1.5)

    def test_qhe_metrics_qhe_formula(self) -> None:
        """QHE = habit_avg * energy_ratio * (1 + eta * streak_bonus)."""
        m = QHEMetrics(**_base_qhe_kwargs())
        expected: float = m.habit_avg * m.energy_ratio * (1.0 + m.eta * m.streak_bonus)
        assert m.qhe == pytest.approx(expected)

    @pytest.mark.parametrize(
        ("habit_avg", "streak_bonus", "energy_ratio", "eta", "expected"),
        [
            (0.5, 0.5, 0.5, 0.5, 0.5 * 0.5 * (1 + 0.5 * 0.5)),
            (1.0, 0.0, 1.0, 0.5, 1.0 * 1.0 * 1.0),
            (0.0, 0.5, 0.5, 0.5, 0.0),
            (0.8, 0.7, 0.6, 0.3, 0.8 * 0.6 * (1 + 0.3 * 0.7)),
            (0.2, 0.4, 0.5, 1.0, 0.2 * 0.5 * (1 + 1.0 * 0.4)),
        ],
    )
    def test_qhe_metrics_qhe_formula_parametric(
        self,
        habit_avg: float,
        streak_bonus: float,
        energy_ratio: float,
        eta: float,
        expected: float,
    ) -> None:
        """The QHE formula is verified for several input combinations."""
        m = QHEMetrics(
            id="qhe_test",
            date=date(2026, 6, 7),
            habit_avg=habit_avg,
            consistency=0.5,
            streak_bonus=streak_bonus,
            energy_ratio=energy_ratio,
            eta=eta,
        )
        assert m.qhe == pytest.approx(expected)


# ---------------------------------------------------------------------------
# QHEMetrics — regime prediction
# ---------------------------------------------------------------------------


class TestQHEMetricsRegimePredicted:
    """The QHE → :class:`PolicyState` mapping."""

    def test_qhe_metrics_regime_predicted_push(self) -> None:
        """QHE >= 0.85 → PUSH."""
        m = QHEMetrics.for_perfect_day(date(2026, 6, 7))
        assert m.qhe >= DEFAULT.QHE_PUSH_THRESHOLD
        assert m.regime_predicted == PolicyState.PUSH

    def test_qhe_metrics_regime_predicted_push_at_threshold(self) -> None:
        """QHE exactly at 0.85 → PUSH (≥ boundary)."""
        m = QHEMetrics(
            id="qhe_threshold",
            date=date(2026, 6, 7),
            habit_avg=0.85,
            consistency=0.85,
            streak_bonus=0.0,
            energy_ratio=1.0,
            eta=0.0,
        )
        assert m.qhe == pytest.approx(0.85)
        assert m.regime_predicted == PolicyState.PUSH

    def test_qhe_metrics_regime_predicted_recover(self) -> None:
        """QHE < 0.60 → RECOVER."""
        m = QHEMetrics(
            id="qhe_low",
            date=date(2026, 6, 7),
            habit_avg=0.3,
            consistency=0.3,
            streak_bonus=0.1,
            energy_ratio=0.4,
        )
        assert m.qhe < DEFAULT.QHE_RECOVER_THRESHOLD
        assert m.regime_predicted == PolicyState.RECOVER

    def test_qhe_metrics_regime_predicted_maintain(self) -> None:
        """0.60 <= QHE < 0.85 → MAINTAIN."""
        m = QHEMetrics(
            id="qhe_mid",
            date=date(2026, 6, 7),
            habit_avg=0.7,
            consistency=0.7,
            streak_bonus=0.5,
            energy_ratio=0.9,
            eta=0.5,
        )
        qhe_val = m.qhe
        assert DEFAULT.QHE_RECOVER_THRESHOLD <= qhe_val < DEFAULT.QHE_PUSH_THRESHOLD
        assert m.regime_predicted == PolicyState.MAINTAIN

    def test_qhe_metrics_regime_predicted_maintain_at_recover_threshold(self) -> None:
        """QHE exactly at 0.60 → MAINTAIN (not RECOVER, since < 0.60)."""
        m = QHEMetrics(
            id="qhe_at_recover",
            date=date(2026, 6, 7),
            habit_avg=0.6,
            consistency=0.6,
            streak_bonus=0.0,
            energy_ratio=1.0,
            eta=0.0,
        )
        assert m.qhe == pytest.approx(0.6)
        assert m.regime_predicted == PolicyState.MAINTAIN

    def test_qhe_metrics_regime_zero_day_is_recover(self) -> None:
        """A zero-day :class:`QHEMetrics` predicts RECOVER."""
        m = QHEMetrics.for_zero_day(date(2026, 6, 7))
        assert m.qhe == pytest.approx(0.0)
        assert m.regime_predicted == PolicyState.RECOVER

    def test_qhe_metrics_regime_perfect_day_is_push(self) -> None:
        """A perfect-day :class:`QHEMetrics` predicts PUSH."""
        m = QHEMetrics.for_perfect_day(date(2026, 6, 7))
        assert m.regime_predicted == PolicyState.PUSH


# ---------------------------------------------------------------------------
# QHEMetrics — factories and JSON
# ---------------------------------------------------------------------------


class TestQHEMetricsFactoriesAndJson:
    """``for_perfect_day`` / ``for_zero_day`` factories + JSON roundtrip."""

    def test_qhe_metrics_for_perfect_day(self) -> None:
        """``for_perfect_day`` returns QHE=1.5 / PUSH."""
        m = QHEMetrics.for_perfect_day(date(2026, 6, 7))
        assert m.habit_avg == 1.0
        assert m.consistency == 1.0
        assert m.streak_bonus == 1.0
        assert m.energy_ratio == 1.0
        assert m.eta == 0.5
        assert m.id == "qhe_20260607"
        assert m.date == date(2026, 6, 7)

    def test_qhe_metrics_for_zero_day(self) -> None:
        """``for_zero_day`` returns QHE=0.0 / RECOVER."""
        m = QHEMetrics.for_zero_day(date(2026, 6, 7))
        assert m.habit_avg == 0.0
        assert m.consistency == 0.0
        assert m.streak_bonus == 0.0
        assert m.energy_ratio == 0.0
        assert m.eta == 0.5  # default
        assert m.id == "qhe_20260607"

    def test_qhe_metrics_to_dict(self) -> None:
        """``to_dict()`` is JSON-serialisable and includes computed fields."""
        m = QHEMetrics(**_base_qhe_kwargs())
        out = m.to_dict()
        encoded = json.dumps(out)
        decoded = json.loads(encoded)
        assert "qhe" in decoded
        assert "regime_predicted" in decoded
        assert decoded["habit_avg"] == m.habit_avg
        assert decoded["qhe"] == pytest.approx(m.qhe)

    def test_qhe_metrics_json_roundtrip(self) -> None:
        """``model_dump_json()`` → ``model_validate_json()`` is lossless.

        Computed fields are excluded from the dump to satisfy
        ``extra="forbid"``.
        """
        original = QHEMetrics(**_base_qhe_kwargs())
        payload = original.model_dump_json(
            exclude={"qhe", "regime_predicted"},
        )
        restored = QHEMetrics.model_validate_json(payload)
        assert restored.id == original.id
        assert restored.date == original.date
        assert restored.habit_avg == original.habit_avg
        assert restored.consistency == original.consistency
        assert restored.streak_bonus == original.streak_bonus
        assert restored.energy_ratio == original.energy_ratio
        assert restored.eta == original.eta
        # Computed fields are still derivable from the restored model.
        assert restored.qhe == pytest.approx(original.qhe)
        assert restored.regime_predicted == original.regime_predicted
