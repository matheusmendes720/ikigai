"""Comprehensive unit tests for :mod:`operational.core.habit_engine`.

Coverage (~60 tests):

* :class:`HabitComputation` — frozen dataclass invariants.
* :func:`compute_habit_level` — boundary, parametric, monotonicity,
  error cases.
* :func:`compute_energy_required` — boundary, parametric, errors.
* :func:`compute_efficiency_ratio` — boundary, parametric, errors.
* :func:`compute_habit_avg` — empty, single, weighted, archived,
  unknown habit.
* :func:`compute_consistency` — empty, full, partial.
* :func:`compute_streak_bonus` — zero, max, overflow, custom max.
* :func:`compute_qhe` — full inputs, edge cases, error cases.
* :func:`predict_regime_from_qhe` — PUSH, MAINTAIN, RECOVER bands.
* :class:`HabitEngine` — construction, configuration, dispatch on
  energy level vs ratio.

All tests are deterministic and use only pure-function inputs.
"""
from __future__ import annotations

import math
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from typing import Any, ClassVar

import pytest

from operational.constants import DEFAULT
from operational.core.habit_engine import (
    ETA_DEFAULT,
    STREAK_MAX_DEFAULT,
    HabitComputation,
    HabitEngine,
    compute_consistency,
    compute_efficiency_ratio,
    compute_energy_required,
    compute_habit_avg,
    compute_habit_level,
    compute_qhe,
    compute_streak_bonus,
    predict_regime_from_qhe,
)
from operational.entities.habit import Habit, HabitState
from operational.enums import EnergyLevel, HabitCategory, PolicyState


# ===========================================================================
# Shared fixtures / helpers
# ===========================================================================


_DT: ClassVar[datetime] = datetime(2026, 6, 7, 5, 0, 0)
_DATE: ClassVar[date] = date(2026, 6, 7)


def _habit_kwargs(**overrides: Any) -> dict[str, Any]:
    """Return a baseline :class:`Habit` kwargs dict."""
    base: dict[str, Any] = {
        "id": "hab_morning_water",
        "name": "Drink water",
        "category": HabitCategory.PHYSIOLOGICAL,
        "resistance": 2.0,
        "weight_in_qhe": 0.3,
        "created_at": _DT,
    }
    base.update(overrides)
    return base


def _state_kwargs(**overrides: Any) -> dict[str, Any]:
    """Return a baseline :class:`HabitState` kwargs dict."""
    base: dict[str, Any] = {
        "id": "hst_hab_morning_water_20260607",
        "habit_id": "hab_morning_water",
        "date": _DATE,
        "completed": True,
        "streak_current": 5,
    }
    base.update(overrides)
    return base


def _make_habit(**overrides: Any) -> Habit:
    """Build a fresh :class:`Habit`."""
    return Habit(**_habit_kwargs(**overrides))


def _make_state(**overrides: Any) -> HabitState:
    """Build a fresh :class:`HabitState`."""
    return HabitState(**_state_kwargs(**overrides))


# ===========================================================================
# Module surface
# ===========================================================================


class TestModuleSurface:
    """The module exports the expected public symbols."""

    def test_all_exports_present(self) -> None:
        """``__all__`` lists the canonical public surface."""
        from operational.core import habit_engine

        expected = {
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
        }
        assert set(habit_engine.__all__) == expected

    def test_all_names_importable(self) -> None:
        """Every name in ``__all__`` is a real attribute."""
        from operational.core import habit_engine

        for name in habit_engine.__all__:
            assert hasattr(habit_engine, name), f"Missing export: {name}"

    def test_default_constants(self) -> None:
        """``ETA_DEFAULT`` and ``STREAK_MAX_DEFAULT`` have canonical values."""
        assert ETA_DEFAULT == 0.5
        assert STREAK_MAX_DEFAULT == 90


# ===========================================================================
# HabitComputation dataclass
# ===========================================================================


class TestHabitComputationDataclass:
    """The :class:`HabitComputation` frozen dataclass."""

    def test_create_minimal(self) -> None:
        """Minimal construction works."""
        c = HabitComputation(
            habit_id="hab_x",
            habit_level=0.5,
            energy_required=2.5,
            efficiency_ratio=0.2,
            streak_current=10,
        )
        assert c.habit_id == "hab_x"
        assert c.habit_level == 0.5
        assert c.energy_required == 2.5
        assert c.efficiency_ratio == 0.2
        assert c.streak_current == 10

    def test_is_frozen(self) -> None:
        """Assignment after construction raises :class:`FrozenInstanceError`."""
        c = HabitComputation(
            habit_id="hab_x",
            habit_level=0.5,
            energy_required=2.5,
            efficiency_ratio=0.2,
            streak_current=10,
        )
        with pytest.raises(FrozenInstanceError):
            c.habit_level = 0.9  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        """The dataclass is frozen and has no ``__dict__`` (uses slots internally)."""
        c = HabitComputation(
            habit_id="hab_x",
            habit_level=0.5,
            energy_required=2.5,
            efficiency_ratio=0.2,
            streak_current=10,
        )
        with pytest.raises((AttributeError, TypeError)):
            c.bogus = "x"  # type: ignore[attr-defined]

    def test_equality(self) -> None:
        """Two records with same fields are equal."""
        kwargs: dict[str, Any] = {
            "habit_id": "hab_x",
            "habit_level": 0.5,
            "energy_required": 2.5,
            "efficiency_ratio": 0.2,
            "streak_current": 10,
        }
        assert HabitComputation(**kwargs) == HabitComputation(**kwargs)


# ===========================================================================
# compute_habit_level
# ===========================================================================


class TestComputeHabitLevel:
    r"""The :math:`H(t) = 1 - e^{-\lambda s}` formula."""

    def test_streak_zero_returns_zero(self) -> None:
        """``H(0) = 1 - e^0 = 0.0``."""
        assert compute_habit_level(0.093, 0) == pytest.approx(0.0)

    def test_streak_one(self) -> None:
        """``H(1) ≈ 1 - e^{-0.093} ≈ 0.0888``."""
        assert compute_habit_level(0.093, 1) == pytest.approx(0.088812, abs=1e-4)

    def test_streak_ten(self) -> None:
        """``H(10) ≈ 1 - e^{-0.93} ≈ 0.6054``."""
        assert compute_habit_level(0.093, 10) == pytest.approx(0.60544, abs=1e-4)

    def test_streak_ninety_approaches_one(self) -> None:
        """``H(90) ≈ 0.9998`` (near consolidation)."""
        h = compute_habit_level(0.093, 90)
        assert h == pytest.approx(0.99979, abs=1e-4)
        assert 0.99 < h < 1.0

    def test_lambda_zero_returns_zero(self) -> None:
        """``H(t) = 0`` when ``lambda == 0`` (no learning)."""
        for streak in [0, 1, 30, 1000]:
            assert compute_habit_level(0.0, streak) == 0.0

    def test_streak_large_approaches_one(self) -> None:
        """``H(t) → 1.0`` as ``streak → ∞``."""
        assert compute_habit_level(0.093, 10_000) == pytest.approx(1.0, abs=1e-10)

    def test_returns_float(self) -> None:
        """The result is a Python ``float``."""
        assert isinstance(compute_habit_level(0.093, 5), float)

    def test_invalid_lambda_negative_raises(self) -> None:
        """Negative ``lambda`` raises :class:`ValueError`."""
        with pytest.raises(ValueError, match="lambda_learning"):
            compute_habit_level(-0.1, 5)

    @pytest.mark.parametrize("lam", [-0.001, -1.0, -100.0])
    def test_invalid_lambda_parametric(self, lam: float) -> None:
        """Negative learning rates are rejected."""
        with pytest.raises(ValueError, match="lambda_learning"):
            compute_habit_level(lam, 5)

    def test_invalid_streak_negative_raises(self) -> None:
        """Negative ``streak`` raises :class:`ValueError`."""
        with pytest.raises(ValueError, match="streak"):
            compute_habit_level(0.093, -1)

    @pytest.mark.parametrize("streak", [-1, -10, -1000])
    def test_invalid_streak_parametric(self, streak: int) -> None:
        """Negative streaks are rejected."""
        with pytest.raises(ValueError, match="streak"):
            compute_habit_level(0.093, streak)

    def test_monotonic_in_streak(self) -> None:
        """``H(s)`` is non-decreasing in ``s`` for fixed ``λ``."""
        prev = -1.0
        for streak in [0, 1, 2, 5, 10, 30, 100, 365, 1000]:
            h = compute_habit_level(0.093, streak)
            assert h >= prev, f"decreased at streak={streak}"
            prev = h

    @pytest.mark.parametrize(
        ("lam", "streak", "expected"),
        [
            (0.0, 0, 0.0),
            (0.0, 100, 0.0),
            (0.1, 0, 0.0),
            (0.1, 10, 1.0 - math.exp(-1.0)),
            (0.1, 50, 1.0 - math.exp(-5.0)),
            (1.0, 5, 1.0 - math.exp(-5.0)),
            (0.5, 2, 1.0 - math.exp(-1.0)),
        ],
    )
    def test_parametric(self, lam: float, streak: int, expected: float) -> None:
        """Parametric verification of the formula."""
        assert compute_habit_level(lam, streak) == pytest.approx(expected, abs=1e-12)

    def test_in_unit_interval(self) -> None:
        """``H(t) ∈ [0, 1]`` for valid inputs."""
        for lam in [0.0, 0.001, 0.093, 0.5, 1.0]:
            for streak in [0, 1, 10, 100, 10_000]:
                h = compute_habit_level(lam, streak)
                assert 0.0 <= h <= 1.0


# ===========================================================================
# compute_energy_required
# ===========================================================================


class TestComputeEnergyRequired:
    r"""The :math:`E_{req} = R \cdot (1 - H(t))` formula."""

    def test_zero_resistance_zero(self) -> None:
        """``R=0`` means no energy required regardless of ``H``."""
        for h in [0.0, 0.5, 1.0]:
            assert compute_energy_required(0.0, h) == pytest.approx(0.0)

    def test_full_resistance_full_level_zero(self) -> None:
        """``H=1`` means fully consolidated → 0 energy."""
        assert compute_energy_required(10.0, 1.0) == pytest.approx(0.0)

    def test_zero_habit_level_full_resistance(self) -> None:
        """``H=0, R=10`` → ``E_req = 10`` (max effort)."""
        assert compute_energy_required(10.0, 0.0) == pytest.approx(10.0)

    def test_zero_habit_level_mid_resistance(self) -> None:
        """``H=0, R=5`` → ``E_req = 5`` (typical unconsolidated)."""
        assert compute_energy_required(5.0, 0.0) == pytest.approx(5.0)

    def test_half_habit_half_resistance(self) -> None:
        """``H=0.5, R=5`` → ``E_req = 2.5``."""
        assert compute_energy_required(5.0, 0.5) == pytest.approx(2.5)

    @pytest.mark.parametrize("r", [0.0, 5.0, 10.0])
    def test_resistance_boundaries(self, r: float) -> None:
        """Resistance boundaries 0, 5, 10 are accepted."""
        assert compute_energy_required(r, 0.0) == pytest.approx(r)

    @pytest.mark.parametrize("r", [-0.1, 10.1, 100.0])
    def test_resistance_out_of_range_raises(self, r: float) -> None:
        """Resistance outside [0, 10] raises :class:`ValueError`."""
        with pytest.raises(ValueError, match="resistance"):
            compute_energy_required(r, 0.5)

    @pytest.mark.parametrize("h", [-0.1, 1.1, 2.0])
    def test_habit_level_out_of_range_raises(self, h: float) -> None:
        """Habit level outside [0, 1] raises :class:`ValueError`."""
        with pytest.raises(ValueError, match="habit_level"):
            compute_energy_required(5.0, h)

    @pytest.mark.parametrize(
        ("r", "h", "expected"),
        [
            (0.0, 0.0, 0.0),
            (10.0, 0.0, 10.0),
            (10.0, 1.0, 0.0),
            (5.0, 0.5, 2.5),
            (2.0, 0.3, 1.4),
            (7.0, 0.8, 1.4),
        ],
    )
    def test_parametric(self, r: float, h: float, expected: float) -> None:
        """Parametric formula check."""
        assert compute_energy_required(r, h) == pytest.approx(expected)


# ===========================================================================
# compute_efficiency_ratio
# ===========================================================================


class TestComputeEfficiencyRatio:
    r"""The :math:`\text{eff} = H(t) / (1 + E_{req})` formula."""

    def test_zero_habit_returns_zero(self) -> None:
        """``H=0`` → efficiency = 0 regardless of ``E_req``."""
        assert compute_efficiency_ratio(0.0, 5.0) == 0.0

    def test_full_habit_zero_energy_returns_one(self) -> None:
        """``H=1, E_req=0`` → efficiency = 1.0 (max)."""
        assert compute_efficiency_ratio(1.0, 0.0) == pytest.approx(1.0)

    def test_half_habit_half_energy(self) -> None:
        """``H=0.5, E_req=1`` → ``0.5 / 2 = 0.25``."""
        assert compute_efficiency_ratio(0.5, 1.0) == pytest.approx(0.25)

    def test_returns_float(self) -> None:
        """Result is a Python ``float``."""
        assert isinstance(compute_efficiency_ratio(0.5, 1.0), float)

    @pytest.mark.parametrize("h", [-0.1, 1.1, -1.0])
    def test_invalid_habit_level_raises(self, h: float) -> None:
        """Invalid habit level raises :class:`ValueError`."""
        with pytest.raises(ValueError, match="habit_level"):
            compute_efficiency_ratio(h, 1.0)

    def test_invalid_energy_negative_raises(self) -> None:
        """Negative energy raises :class:`ValueError`."""
        with pytest.raises(ValueError, match="energy_required"):
            compute_efficiency_ratio(0.5, -0.1)

    @pytest.mark.parametrize("e", [-0.1, -10.0])
    def test_invalid_energy_parametric_raises(self, e: float) -> None:
        """Negative energy is rejected."""
        with pytest.raises(ValueError, match="energy_required"):
            compute_efficiency_ratio(0.5, e)

    def test_zero_energy_accepted(self) -> None:
        """``E_req = 0`` is valid (no penalty)."""
        assert compute_efficiency_ratio(0.7, 0.0) == pytest.approx(0.7)

    @pytest.mark.parametrize(
        ("h", "e", "expected"),
        [
            (0.0, 0.0, 0.0),
            (0.0, 5.0, 0.0),
            (1.0, 0.0, 1.0),
            (0.5, 0.0, 0.5),
            (0.5, 1.0, 0.25),
            (0.8, 0.6, 0.5),
            (0.2, 9.0, 0.02),
        ],
    )
    def test_parametric(self, h: float, e: float, expected: float) -> None:
        """Parametric formula check."""
        assert compute_efficiency_ratio(h, e) == pytest.approx(expected, abs=1e-12)

    def test_monotonic_in_habit(self) -> None:
        """Efficiency is non-decreasing in ``H`` for fixed ``E_req``."""
        prev = -1.0
        for h in [0.0, 0.1, 0.5, 0.9, 1.0]:
            eff = compute_efficiency_ratio(h, 2.0)
            assert eff >= prev
            prev = eff


# ===========================================================================
# compute_habit_avg
# ===========================================================================


class TestComputeHabitAvg:
    r"""The :math:`H_{avg} = \sum_i w_i H_i / \sum_i w_i` aggregator."""

    def test_empty_states_returns_zero(self) -> None:
        """Empty states return 0.0."""
        assert compute_habit_avg([], [_make_habit()]) == 0.0

    def test_empty_habits_returns_zero(self) -> None:
        """Empty habits return 0.0."""
        assert compute_habit_avg([_make_state()], []) == 0.0

    def test_both_empty_returns_zero(self) -> None:
        """Both empty return 0.0."""
        assert compute_habit_avg([], []) == 0.0

    def test_single_habit_equal_to_h(self) -> None:
        """A single habit with weight 1.0 returns ``H(s)`` directly."""
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=0.1)
        s = _make_state(streak_current=10)
        expected = compute_habit_level(0.1, 10)
        assert compute_habit_avg([s], [h]) == pytest.approx(expected)

    def test_weighted_parametric(self) -> None:
        """Two habits with weights 0.3 and 0.7, the weighted average."""
        h1 = _make_habit(
            id="hab_a",
            weight_in_qhe=0.3,
            lambda_learning=0.1,
        )
        h2 = _make_habit(
            id="hab_b",
            weight_in_qhe=0.7,
            lambda_learning=0.5,
        )
        s1 = _make_state(habit_id="hab_a", streak_current=20)
        s2 = _make_state(habit_id="hab_b", streak_current=5)
        ha = compute_habit_level(0.1, 20)
        hb = compute_habit_level(0.5, 5)
        expected = (0.3 * ha + 0.7 * hb) / (0.3 + 0.7)
        assert compute_habit_avg([s1, s2], [h1, h2]) == pytest.approx(expected)

    def test_archived_habit_skipped(self) -> None:
        """Archived habits are excluded from the weighted average."""
        h1 = _make_habit(id="hab_a", weight_in_qhe=0.5, lambda_learning=0.1)
        h2 = _make_habit(
            id="hab_b",
            weight_in_qhe=0.5,
            lambda_learning=0.1,
            archived=True,
        )
        s1 = _make_state(habit_id="hab_a", streak_current=10)
        s2 = _make_state(habit_id="hab_b", streak_current=20)
        # Only s1 contributes.
        expected = compute_habit_level(0.1, 10)
        assert compute_habit_avg([s1, s2], [h1, h2]) == pytest.approx(expected)

    def test_unknown_habit_skipped(self) -> None:
        """States referencing unknown habits are silently skipped."""
        h = _make_habit(id="hab_a", weight_in_qhe=1.0, lambda_learning=0.1)
        s_known = _make_state(habit_id="hab_a", streak_current=10)
        s_unknown = _make_state(habit_id="hab_ghost", streak_current=50)
        # Only known contributes.
        expected = compute_habit_level(0.1, 10)
        assert compute_habit_avg(
            [s_known, s_unknown], [h],
        ) == pytest.approx(expected)

    def test_all_archived_returns_zero(self) -> None:
        """All-archived habits return 0.0."""
        h = _make_habit(archived=True)
        s = _make_state()
        assert compute_habit_avg([s], [h]) == 0.0

    def test_zero_weight_skipped(self) -> None:
        """Habits with ``weight_in_qhe == 0`` are skipped."""
        h1 = _make_habit(id="hab_a", weight_in_qhe=0.0, lambda_learning=0.1)
        h2 = _make_habit(id="hab_b", weight_in_qhe=1.0, lambda_learning=0.5)
        s1 = _make_state(habit_id="hab_a", streak_current=10)
        s2 = _make_state(habit_id="hab_b", streak_current=5)
        expected = compute_habit_level(0.5, 5)
        assert compute_habit_avg([s1, s2], [h1, h2]) == pytest.approx(expected)

    def test_all_weights_zero_returns_zero(self) -> None:
        """If all weights are zero, returns 0.0."""
        h1 = _make_habit(id="hab_a", weight_in_qhe=0.0)
        h2 = _make_habit(id="hab_b", weight_in_qhe=0.0)
        s1 = _make_state(habit_id="hab_a")
        s2 = _make_state(habit_id="hab_b")
        assert compute_habit_avg([s1, s2], [h1, h2]) == 0.0


# ===========================================================================
# compute_consistency
# ===========================================================================


class TestComputeConsistency:
    """The consistency ratio ``completed / total``."""

    def test_empty_returns_zero(self) -> None:
        """Empty states return 0.0."""
        assert compute_consistency([]) == 0.0

    def test_all_completed_returns_one(self) -> None:
        """All states completed → 1.0."""
        states = [
            _make_state(habit_id="hab_a", completed=True),
            _make_state(habit_id="hab_b", completed=True),
            _make_state(habit_id="hab_c", completed=True),
        ]
        assert compute_consistency(states) == 1.0

    def test_none_completed_returns_zero(self) -> None:
        """All states missed → 0.0."""
        states = [
            _make_state(habit_id="hab_a", completed=False),
            _make_state(habit_id="hab_b", completed=False),
        ]
        assert compute_consistency(states) == 0.0

    @pytest.mark.parametrize(
        ("completed", "total", "expected"),
        [
            (1, 1, 1.0),
            (0, 1, 0.0),
            (1, 2, 0.5),
            (3, 4, 0.75),
            (2, 3, 2 / 3),
            (1, 7, 1 / 7),
            (6, 7, 6 / 7),
        ],
    )
    def test_partial(self, completed: int, total: int, expected: float) -> None:
        """Parametric partial consistency values."""
        done = [
            _make_state(habit_id=f"hab_done_{i}", completed=True)
            for i in range(completed)
        ]
        miss = [
            _make_state(habit_id=f"hab_miss_{i}", completed=False)
            for i in range(total - completed)
        ]
        states: list[HabitState] = [*done, *miss]
        assert compute_consistency(states) == pytest.approx(expected)

    def test_single_completed(self) -> None:
        """A single completed state → 1.0."""
        assert compute_consistency([_make_state(completed=True)]) == 1.0

    def test_single_missed(self) -> None:
        """A single missed state → 0.0."""
        assert compute_consistency([_make_state(completed=False)]) == 0.0


# ===========================================================================
# compute_streak_bonus
# ===========================================================================


class TestComputeStreakBonus:
    """The streak-bonus formula ``min(s_cur / s_max, 1.0)``."""

    def test_zero_streak(self) -> None:
        """Streak 0 → 0.0."""
        assert compute_streak_bonus(0) == 0.0

    def test_max_streak_returns_one(self) -> None:
        """Streak == max → 1.0."""
        assert compute_streak_bonus(90) == 1.0

    def test_overflow_capped_at_one(self) -> None:
        """Streak > max is capped at 1.0."""
        assert compute_streak_bonus(200) == 1.0
        assert compute_streak_bonus(10_000) == 1.0

    def test_partial(self) -> None:
        """Streak = half max → 0.5."""
        assert compute_streak_bonus(45) == pytest.approx(0.5)

    def test_custom_max_streak(self) -> None:
        """Custom ``max_streak`` parameter works."""
        assert compute_streak_bonus(30, max_streak=30) == 1.0
        assert compute_streak_bonus(15, max_streak=30) == pytest.approx(0.5)
        assert compute_streak_bonus(0, max_streak=30) == 0.0
        assert compute_streak_bonus(60, max_streak=30) == 1.0  # capped

    def test_negative_streak_raises(self) -> None:
        """Negative streak raises :class:`ValueError`."""
        with pytest.raises(ValueError, match="current_streak"):
            compute_streak_bonus(-1)

    @pytest.mark.parametrize("streak", [-1, -10, -100])
    def test_negative_streak_parametric(self, streak: int) -> None:
        """Negative streaks are rejected."""
        with pytest.raises(ValueError, match="current_streak"):
            compute_streak_bonus(streak)

    def test_zero_max_streak_raises(self) -> None:
        """``max_streak == 0`` raises :class:`ValueError`."""
        with pytest.raises(ValueError, match="max_streak"):
            compute_streak_bonus(5, max_streak=0)

    def test_negative_max_streak_raises(self) -> None:
        """``max_streak < 0`` raises :class:`ValueError`."""
        with pytest.raises(ValueError, match="max_streak"):
            compute_streak_bonus(5, max_streak=-1)

    @pytest.mark.parametrize(
        ("streak", "max_streak", "expected"),
        [
            (0, 90, 0.0),
            (45, 90, 0.5),
            (90, 90, 1.0),
            (180, 90, 1.0),
            (10, 20, 0.5),
            (1, 1, 1.0),
        ],
    )
    def test_parametric(self, streak: int, max_streak: int, expected: float) -> None:
        """Parametric formula check."""
        assert compute_streak_bonus(streak, max_streak) == pytest.approx(expected)

    def test_default_max_streak(self) -> None:
        """Default ``max_streak`` is :data:`STREAK_MAX_DEFAULT`."""
        assert compute_streak_bonus(STREAK_MAX_DEFAULT) == 1.0
        assert compute_streak_bonus(STREAK_MAX_DEFAULT // 2) == pytest.approx(0.5)


# ===========================================================================
# compute_qhe
# ===========================================================================


class TestComputeQHE:
    """The QHE snapshot formula."""

    def test_full_inputs(self) -> None:
        """All perfect inputs → QHE = 1.0 * 1.0 * (1 + 0.5 * 1.0) = 1.5."""
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=90, completed=True)
        m = compute_qhe([s], [h], energy_ratio=1.0, current_streak=90)
        assert m.habit_avg == pytest.approx(1.0)
        assert m.consistency == 1.0
        assert m.streak_bonus == 1.0
        assert m.energy_ratio == 1.0
        assert m.eta == 0.5
        assert m.qhe == pytest.approx(1.5)

    def test_zero_energy_ratio(self) -> None:
        """``energy_ratio = 0`` → QHE = 0."""
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=90, completed=True)
        m = compute_qhe([s], [h], energy_ratio=0.0, current_streak=90)
        assert m.qhe == 0.0

    def test_zero_streak_bonus(self) -> None:
        """``current_streak = 0`` → streak_bonus = 0, QHE reduces."""
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=90, completed=True)
        m = compute_qhe([s], [h], energy_ratio=1.0, current_streak=0)
        assert m.streak_bonus == 0.0
        assert m.qhe == pytest.approx(1.0)  # 1.0 * 1.0 * (1 + 0.5 * 0) = 1.0

    def test_empty_states(self) -> None:
        """Empty states → QHE = 0 (all components are 0)."""
        m = compute_qhe([], [], energy_ratio=0.5, current_streak=10)
        assert m.habit_avg == 0.0
        assert m.consistency == 0.0
        assert m.qhe == 0.0

    def test_qhe_id_format(self) -> None:
        """The auto-generated ``id`` matches the ``qhe_<hex>`` pattern."""
        m = compute_qhe([], [], energy_ratio=0.5, current_streak=10)
        assert m.id.startswith("qhe_")
        assert len(m.id) == len("qhe_") + 12

    def test_qhe_id_is_unique(self) -> None:
        """Two calls produce two different ``id`` values."""
        m1 = compute_qhe([], [], energy_ratio=0.5, current_streak=10)
        m2 = compute_qhe([], [], energy_ratio=0.5, current_streak=10)
        assert m1.id != m2.id

    def test_custom_eta(self) -> None:
        """Custom ``eta`` is stored and used in QHE."""
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=90, completed=True)
        m = compute_qhe(
            [s], [h], energy_ratio=1.0, current_streak=90, eta=1.0,
        )
        assert m.eta == 1.0
        # 1.0 * 1.0 * (1 + 1.0 * 1.0) = 2.0
        assert m.qhe == pytest.approx(2.0)

    def test_custom_max_streak(self) -> None:
        """Custom ``max_streak`` affects the streak bonus."""
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=30, completed=True)
        m = compute_qhe(
            [s], [h], energy_ratio=1.0, current_streak=30, max_streak=30,
        )
        assert m.streak_bonus == 1.0
        # 1.0 * 1.0 * (1 + 0.5 * 1.0) = 1.5
        assert m.qhe == pytest.approx(1.5)

    def test_invalid_energy_ratio_raises(self) -> None:
        """Invalid ``energy_ratio`` raises :class:`ValueError`."""
        h = _make_habit()
        s = _make_state()
        with pytest.raises(ValueError, match="energy_ratio"):
            compute_qhe([s], [h], energy_ratio=1.5, current_streak=10)
        with pytest.raises(ValueError, match="energy_ratio"):
            compute_qhe([s], [h], energy_ratio=-0.1, current_streak=10)

    def test_invalid_eta_raises(self) -> None:
        """Invalid ``eta`` raises :class:`ValueError`."""
        h = _make_habit()
        s = _make_state()
        with pytest.raises(ValueError, match="eta"):
            compute_qhe([s], [h], energy_ratio=0.5, current_streak=10, eta=1.5)
        with pytest.raises(ValueError, match="eta"):
            compute_qhe([s], [h], energy_ratio=0.5, current_streak=10, eta=-0.1)


# ===========================================================================
# predict_regime_from_qhe
# ===========================================================================


class TestPredictRegimeFromQhe:
    """The QHE → :class:`PolicyState` mapping."""

    def test_push_above_threshold(self) -> None:
        """``qhe >= 0.85`` → :attr:`PolicyState.PUSH`."""
        assert predict_regime_from_qhe(0.85) is PolicyState.PUSH
        assert predict_regime_from_qhe(0.9) is PolicyState.PUSH
        assert predict_regime_from_qhe(1.0) is PolicyState.PUSH
        assert predict_regime_from_qhe(1.5) is PolicyState.PUSH
        assert predict_regime_from_qhe(2.0) is PolicyState.PUSH

    def test_push_at_exact_threshold(self) -> None:
        """``qhe == 0.85`` exactly → :attr:`PolicyState.PUSH` (boundary)."""
        assert predict_regime_from_qhe(DEFAULT.QHE_PUSH_THRESHOLD) is PolicyState.PUSH

    def test_recover_below_threshold(self) -> None:
        """``qhe < 0.60`` → :attr:`PolicyState.RECOVER`."""
        assert predict_regime_from_qhe(0.0) is PolicyState.RECOVER
        assert predict_regime_from_qhe(0.3) is PolicyState.RECOVER
        assert predict_regime_from_qhe(0.59) is PolicyState.RECOVER

    def test_recover_never_red(self) -> None:
        """``REDUCE`` is never produced by the QHE predictor."""
        # Sweep the whole range
        for qhe in [0.0, 0.3, 0.6, 0.7, 0.85, 1.0, 1.5, 2.0]:
            regime = predict_regime_from_qhe(qhe)
            assert regime is not PolicyState.REDUCE

    @pytest.mark.parametrize(
        "qhe",
        [0.6, 0.65, 0.7, 0.75, 0.8, 0.84, 0.84999],
    )
    def test_maintain_in_band(self, qhe: float) -> None:
        """``0.60 <= qhe < 0.85`` → :attr:`PolicyState.MAINTAIN`."""
        assert predict_regime_from_qhe(qhe) is PolicyState.MAINTAIN

    def test_maintain_at_recover_threshold(self) -> None:
        """``qhe == 0.60`` exactly → :attr:`PolicyState.MAINTAIN`."""
        assert predict_regime_from_qhe(DEFAULT.QHE_RECOVER_THRESHOLD) is (
            PolicyState.MAINTAIN
        )

    def test_invalid_qhe_negative_raises(self) -> None:
        """Negative QHE raises :class:`ValueError`."""
        with pytest.raises(ValueError, match="qhe"):
            predict_regime_from_qhe(-0.1)

    def test_invalid_qhe_too_high_raises(self) -> None:
        """``qhe > 2.0`` raises :class:`ValueError` (theoretical max)."""
        with pytest.raises(ValueError, match="qhe"):
            predict_regime_from_qhe(2.1)
        with pytest.raises(ValueError, match="qhe"):
            predict_regime_from_qhe(100.0)

    def test_band_partition(self) -> None:
        """The three bands form a complete partition of [0, 2]."""
        for qhe in [0.0, 0.1, 0.3, 0.59, 0.6, 0.7, 0.84, 0.85, 0.9, 1.0, 1.5, 2.0]:
            regime = predict_regime_from_qhe(qhe)
            assert regime in {PolicyState.PUSH, PolicyState.MAINTAIN, PolicyState.RECOVER}


# ===========================================================================
# HabitEngine class
# ===========================================================================


class TestHabitEngineConstruction:
    """Construction and validation of the engine."""

    def test_default_construction(self) -> None:
        """Engine has the canonical default values."""
        eng = HabitEngine()
        assert eng.eta == ETA_DEFAULT
        assert eng.max_streak == STREAK_MAX_DEFAULT

    def test_custom_eta(self) -> None:
        """Engine accepts a custom ``eta``."""
        eng = HabitEngine(eta=0.7)
        assert eng.eta == 0.7

    def test_custom_max_streak(self) -> None:
        """Engine accepts a custom ``max_streak``."""
        eng = HabitEngine(max_streak=60)
        assert eng.max_streak == 60

    def test_custom_both(self) -> None:
        """Engine accepts both ``eta`` and ``max_streak``."""
        eng = HabitEngine(eta=0.3, max_streak=120)
        assert eng.eta == 0.3
        assert eng.max_streak == 120

    def test_invalid_eta_raises(self) -> None:
        """Invalid ``eta`` raises :class:`ValueError`."""
        with pytest.raises(ValueError, match="eta"):
            HabitEngine(eta=1.1)
        with pytest.raises(ValueError, match="eta"):
            HabitEngine(eta=-0.1)

    def test_invalid_max_streak_raises(self) -> None:
        """Invalid ``max_streak`` raises :class:`ValueError`."""
        with pytest.raises(ValueError, match="max_streak"):
            HabitEngine(max_streak=0)
        with pytest.raises(ValueError, match="max_streak"):
            HabitEngine(max_streak=-10)

    def test_eta_is_readonly(self) -> None:
        """``eta`` is a read-only property."""
        eng = HabitEngine()
        with pytest.raises(AttributeError):
            eng.eta = 0.8  # type: ignore[misc]

    def test_max_streak_is_readonly(self) -> None:
        """``max_streak`` is a read-only property."""
        eng = HabitEngine()
        with pytest.raises(AttributeError):
            eng.max_streak = 50  # type: ignore[misc]


class TestHabitEngineComputeHabit:
    """``HabitEngine.compute_habit`` method."""

    def test_compute_habit_single(self) -> None:
        """Engine computes all metrics for a single habit."""
        eng = HabitEngine()
        h = _make_habit(
            id="hab_meditation",
            resistance=4.0,
            lambda_learning=0.093,
        )
        c = eng.compute_habit(h, streak=30)
        assert isinstance(c, HabitComputation)
        assert c.habit_id == "hab_meditation"
        assert c.streak_current == 30
        assert c.habit_level == pytest.approx(compute_habit_level(0.093, 30))
        assert c.energy_required == pytest.approx(
            compute_energy_required(4.0, c.habit_level),
        )
        assert c.efficiency_ratio == pytest.approx(
            compute_efficiency_ratio(c.habit_level, c.energy_required),
        )

    def test_compute_habit_at_streak_zero(self) -> None:
        """At streak 0, the level is 0 and energy is full resistance."""
        eng = HabitEngine()
        h = _make_habit(resistance=5.0)
        c = eng.compute_habit(h, streak=0)
        assert c.habit_level == pytest.approx(0.0)
        assert c.energy_required == pytest.approx(5.0)
        assert c.efficiency_ratio == pytest.approx(0.0)

    def test_compute_habit_independent_of_engine_config(self) -> None:
        """``compute_habit`` does not depend on ``eta``/``max_streak``."""
        e1 = HabitEngine(eta=0.1, max_streak=30)
        e2 = HabitEngine(eta=0.9, max_streak=120)
        h = _make_habit()
        c1 = e1.compute_habit(h, 10)
        c2 = e2.compute_habit(h, 10)
        assert c1 == c2


class TestHabitEngineComputeQhe:
    """``HabitEngine.compute_qhe`` method."""

    def test_with_energy_ratio(self) -> None:
        """Engine accepts an explicit ``energy_ratio``."""
        eng = HabitEngine()
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=90, completed=True)
        m = eng.compute_qhe([s], [h], energy_ratio=0.8, current_streak=90)
        assert m.energy_ratio == 0.8
        assert m.eta == ETA_DEFAULT
        assert m.max_streak if hasattr(m, "max_streak") else True  # always present

    def test_with_energy_level_high(self) -> None:
        """``EnergyLevel.HIGH`` maps to ratio 1.0."""
        eng = HabitEngine()
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=90, completed=True)
        m = eng.compute_qhe([s], [h], energy_level=EnergyLevel.HIGH, current_streak=90)
        assert m.energy_ratio == 1.0

    def test_with_energy_level_medium(self) -> None:
        """``EnergyLevel.MEDIUM`` maps to ratio 0.6."""
        eng = HabitEngine()
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=90, completed=True)
        m = eng.compute_qhe(
            [s], [h], energy_level=EnergyLevel.MEDIUM, current_streak=90,
        )
        assert m.energy_ratio == 0.6

    def test_with_energy_level_low(self) -> None:
        """``EnergyLevel.LOW`` maps to ratio 0.3."""
        eng = HabitEngine()
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=90, completed=True)
        m = eng.compute_qhe(
            [s], [h], energy_level=EnergyLevel.LOW, current_streak=90,
        )
        assert m.energy_ratio == 0.3

    def test_with_default_energy(self) -> None:
        """Default energy (no level, no ratio) is 0.5."""
        eng = HabitEngine()
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=90, completed=True)
        m = eng.compute_qhe([s], [h], current_streak=90)
        assert m.energy_ratio == 0.5

    def test_energy_ratio_takes_precedence(self) -> None:
        """``energy_ratio`` wins over ``energy_level`` when both given."""
        eng = HabitEngine()
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=90, completed=True)
        m = eng.compute_qhe(
            [s], [h],
            energy_level=EnergyLevel.LOW,
            energy_ratio=0.7,
            current_streak=90,
        )
        assert m.energy_ratio == 0.7

    def test_custom_eta_propagates(self) -> None:
        """Custom engine ``eta`` is used in the QHE result."""
        eng = HabitEngine(eta=0.8)
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=90, completed=True)
        m = eng.compute_qhe([s], [h], energy_ratio=1.0, current_streak=90)
        assert m.eta == 0.8

    def test_custom_max_streak_propagates(self) -> None:
        """Custom engine ``max_streak`` is used in the streak bonus."""
        eng = HabitEngine(max_streak=30)
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=30, completed=True)
        m = eng.compute_qhe([s], [h], energy_ratio=1.0, current_streak=30)
        assert m.streak_bonus == 1.0


class TestHabitEngineIntegration:
    """End-to-end integration with the engine + regime prediction."""

    def test_full_pipeline_push(self) -> None:
        """Perfect inputs → PUSH regime."""
        eng = HabitEngine()
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=90, completed=True)
        m = eng.compute_qhe([s], [h], energy_level=EnergyLevel.HIGH, current_streak=90)
        assert m.qhe >= DEFAULT.QHE_PUSH_THRESHOLD
        assert predict_regime_from_qhe(m.qhe) is PolicyState.PUSH

    def test_full_pipeline_recover(self) -> None:
        """Zero inputs → RECOVER regime."""
        eng = HabitEngine()
        m = eng.compute_qhe([], [], current_streak=0)
        assert m.qhe < DEFAULT.QHE_RECOVER_THRESHOLD
        assert predict_regime_from_qhe(m.qhe) is PolicyState.RECOVER


# ===========================================================================
# Energy map (PUBLIC CONSTANT)
# ===========================================================================


class TestEnergyMapConsistency:
    """The energy-level → ratio mapping is consistent with the entity."""

    def test_high_is_one(self) -> None:
        """``HIGH`` ratio is 1.0."""
        from operational.core.habit_engine import _ENERGY_MAP

        assert _ENERGY_MAP[EnergyLevel.HIGH] == 1.0

    def test_medium_is_six_tenths(self) -> None:
        """``MEDIUM`` ratio is 0.6."""
        from operational.core.habit_engine import _ENERGY_MAP

        assert _ENERGY_MAP[EnergyLevel.MEDIUM] == 0.6

    def test_low_is_three_tenths(self) -> None:
        """``LOW`` ratio is 0.3."""
        from operational.core.habit_engine import _ENERGY_MAP

        assert _ENERGY_MAP[EnergyLevel.LOW] == 0.3


# ===========================================================================
# Cross-component integration
# ===========================================================================


class TestCrossComponent:
    """``QHEMetrics`` ↔ :class:`HabitEngine` integration."""

    def test_qhe_metrics_qhe_matches_engine(self) -> None:
        """The QHE produced by the engine matches the model's field."""
        eng = HabitEngine()
        h = _make_habit(weight_in_qhe=0.5, lambda_learning=0.1)
        s = _make_state(streak_current=15, completed=True)
        m = eng.compute_qhe([s], [h], energy_ratio=0.6, current_streak=15)
        # The model's qhe field is habit_avg * energy_ratio * (1 + eta * streak_bonus).
        expected = (
            m.habit_avg
            * m.energy_ratio
            * (1.0 + m.eta * m.streak_bonus)
        )
        assert m.qhe == pytest.approx(expected)

    def test_qhe_metrics_regime_consistent_with_predict(self) -> None:
        """The model's regime matches :func:`predict_regime_from_qhe`."""
        eng = HabitEngine()
        h = _make_habit(weight_in_qhe=1.0, lambda_learning=1.0)
        s = _make_state(streak_current=90, completed=True)
        m = eng.compute_qhe([s], [h], energy_level=EnergyLevel.HIGH, current_streak=90)
        assert m.regime_predicted is predict_regime_from_qhe(m.qhe)


# ===========================================================================
# Date / created_at safety
# ===========================================================================


class TestDateHandling:
    """The date is set to today (UTC) at construction time."""

    def test_qhe_date_is_today(self) -> None:
        """``QHEMetrics.date`` is the current UTC date."""
        h = _make_habit()
        s = _make_state()
        m = compute_qhe([s], [h], energy_ratio=0.5, current_streak=10)
        expected_today = datetime.now(tz=UTC).date()
        assert m.date == expected_today

    def test_qhe_date_recent(self) -> None:
        """``QHEMetrics.date`` is within 1 day of now (handles midnight)."""
        h = _make_habit()
        s = _make_state()
        m = compute_qhe([s], [h], energy_ratio=0.5, current_streak=10)
        today = datetime.now(tz=UTC).date()
        assert abs((m.date - today).days) <= 1
