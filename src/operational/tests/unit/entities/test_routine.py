"""Unit tests for :mod:`operational.entities.routine`.

Coverage:

* Construction happy paths for :class:`Routine`, :class:`Ritual`,
  :class:`Transition`.
* Frozen / extra-forbid / validation guards.
* Field-level constraints (length, weekday set, time ordering).
* Cross-field invariants (end > start, periods differ).
* Computed properties (``duration_minutes``, ``active_on_weekend``,
  ``default_period``, ``triggers_routine``, ``is_ritual_heavy``).
* Factory semantics for ``VALID_WEEKDAYS`` / ``Weekday``.
* JSON roundtrip for every entity.
"""
from __future__ import annotations

import json
from copy import copy, deepcopy
from datetime import datetime, time
from typing import Any

import pytest
from pydantic import ValidationError

from operational.entities.routine import (
    VALID_WEEKDAYS,
    Ritual,
    Routine,
    Transition,
)
from operational.enums import Period, RitualType, RoutineType

from tests.unit.entities._roundtrip import roundtrip

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TS: datetime = datetime(2026, 6, 7, 12, 0, 0)
"""A fixed timestamp used for ``created_at`` across the suite."""


def _make_routine(**overrides: Any) -> Routine:
    """Return a minimal but valid :class:`Routine` with optional overrides."""
    base: dict[str, Any] = {
        "id": "rou_morning_wake",
        "name": "Acordar 3-5am",
        "period": Period.MANHA,
        "routine_type": RoutineType.ENTRY,
        "start_time": time(3, 0),
        "end_time": time(5, 0),
        "created_at": TS,
    }
    base.update(overrides)
    return Routine(**base)


def _make_ritual(**overrides: Any) -> Ritual:
    """Return a minimal but valid :class:`Ritual` with optional overrides."""
    base: dict[str, Any] = {
        "id": "rit_hydration_am",
        "name": "Hidratação matinal",
        "ritual_type": RitualType.HYDRATION,
        "duration_minutes": 5,
        "created_at": TS,
    }
    base.update(overrides)
    return Ritual(**base)


def _make_transition(**overrides: Any) -> Transition:
    """Return a minimal but valid :class:`Transition` with optional overrides."""
    base: dict[str, Any] = {
        "id": "trn_manha_tarde",
        "name": "Transição manhã→tarde",
        "from_period": Period.MANHA,
        "to_period": Period.TARDE,
        "duration_minutes": 15,
        "created_at": TS,
    }
    base.update(overrides)
    return Transition(**base)


# ---------------------------------------------------------------------------
# Module surface
# ---------------------------------------------------------------------------


class TestModuleSurface:
    """The ``routine`` module exposes a stable public API."""

    def test_all_is_complete(self) -> None:
        import operational.entities.routine as mod

        expected = {"Routine", "Ritual", "Transition", "Weekday", "VALID_WEEKDAYS"}
        assert expected.issubset(set(mod.__all__))

    def test_all_names_importable(self) -> None:
        import operational.entities.routine as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"Missing export: {name}"

    def test_valid_weekdays_is_complete(self) -> None:
        """``VALID_WEEKDAYS`` is the canonical {0,1,2,3,4,5,6} set."""
        assert VALID_WEEKDAYS == frozenset({0, 1, 2, 3, 4, 5, 6})


# ---------------------------------------------------------------------------
# Routine — construction
# ---------------------------------------------------------------------------


class TestRoutineConstruction:
    """Happy-path construction of :class:`Routine`."""

    def test_create_minimal_routine(self) -> None:
        r = _make_routine()
        assert r.id == "rou_morning_wake"
        assert r.name == "Acordar 3-5am"
        assert r.period is Period.MANHA
        assert r.routine_type is RoutineType.ENTRY
        assert r.start_time == time(3, 0)
        assert r.end_time == time(5, 0)
        assert r.description == ""
        assert r.mandatory is True
        assert r.days_of_week == {0, 1, 2, 3, 4, 5, 6}
        assert r.archived is False
        assert r.created_at == TS

    def test_default_days_of_week_is_all_seven(self) -> None:
        r = _make_routine()
        assert r.days_of_week == {0, 1, 2, 3, 4, 5, 6}

    def test_routine_with_explicit_days_of_week(self) -> None:
        r = _make_routine(days_of_week={0, 1, 2, 3, 4})
        assert r.days_of_week == {0, 1, 2, 3, 4}

    def test_routine_with_description_and_archived(self) -> None:
        r = _make_routine(
            description="Detailed morning checklist",
            archived=True,
            mandatory=False,
        )
        assert r.description == "Detailed morning checklist"
        assert r.archived is True
        assert r.mandatory is False

    def test_routine_strips_whitespace_in_name(self) -> None:
        r = _make_routine(name="  Spaced Name  ")
        assert r.name == "Spaced Name"

    @pytest.mark.parametrize("period", list(Period))
    def test_routine_period_assignment(self, period: Period) -> None:
        r = _make_routine(period=period)
        assert r.period is period

    @pytest.mark.parametrize("rt", list(RoutineType))
    def test_routine_type_assignment(self, rt: RoutineType) -> None:
        r = _make_routine(routine_type=rt)
        assert r.routine_type is rt


# ---------------------------------------------------------------------------
# Routine — model_config guards
# ---------------------------------------------------------------------------


class TestRoutineFrozen:
    """Routine is frozen and rejects unknown fields."""

    def test_routine_frozen(self) -> None:
        r = _make_routine()
        with pytest.raises(ValidationError):
            r.name = "Mutated"  # type: ignore[misc]

    def test_routine_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Routine(
                id="rou_test",
                name="Test",
                period=Period.MANHA,
                routine_type=RoutineType.CORE,
                start_time=time(3, 0),
                end_time=time(4, 0),
                created_at=TS,
                bogus_field="not-allowed",  # type: ignore[call-arg]
            )
        assert "bogus_field" in str(exc.value)

    def test_routine_rejects_empty_name(self) -> None:
        with pytest.raises(ValidationError):
            _make_routine(name="")

    def test_routine_rejects_oversized_name(self) -> None:
        with pytest.raises(ValidationError):
            _make_routine(name="x" * 101)

    def test_routine_rejects_oversized_description(self) -> None:
        with pytest.raises(ValidationError):
            _make_routine(description="x" * 501)

    def test_routine_accepts_underscored_ueid(self) -> None:
        r = _make_routine(id="rou_morning_wake_v2")
        assert r.id == "rou_morning_wake_v2"

    @pytest.mark.parametrize(
        "bad_id",
        [
            "ab_x",        # prefix too short
            "abcdefg_x",   # prefix too long
            "ROU_x",       # uppercase
            "rou_",        # empty slug
            "rou",         # no separator
            "rou-X",       # hyphen in slug
        ],
    )
    def test_routine_rejects_bad_ueid(self, bad_id: str) -> None:
        with pytest.raises(ValidationError):
            _make_routine(id=bad_id)


# ---------------------------------------------------------------------------
# Routine — validators
# ---------------------------------------------------------------------------


class TestRoutineValidators:
    """Custom validators for :class:`Routine`."""

    def test_routine_validates_days_of_week(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _make_routine(days_of_week={0, 1, 7})  # 7 is invalid
        assert "days_of_week" in str(exc.value)

    @pytest.mark.parametrize("bad", [{7}, {0, -1}, {10}, {-5, 0}])
    def test_routine_rejects_out_of_range_weekdays(self, bad: set[int]) -> None:
        with pytest.raises(ValidationError):
            _make_routine(days_of_week=bad)

    def test_routine_accepts_single_day(self) -> None:
        r = _make_routine(days_of_week={0})
        assert r.days_of_week == {0}

    def test_routine_validates_times(self) -> None:
        """end_time must be strictly after start_time."""
        with pytest.raises(ValidationError) as exc:
            _make_routine(start_time=time(5, 0), end_time=time(3, 0))
        assert "end_time" in str(exc.value)

    def test_routine_rejects_equal_times(self) -> None:
        """end_time == start_time is forbidden (zero-duration routine)."""
        with pytest.raises(ValidationError):
            _make_routine(start_time=time(4, 0), end_time=time(4, 0))

    def test_routine_rejects_overnight_crossing(self) -> None:
        """Overnight routines (end_time < start_time on the same day) are forbidden."""
        with pytest.raises(ValidationError):
            _make_routine(start_time=time(23, 0), end_time=time(1, 0))

    def test_routine_accepts_minute_precision(self) -> None:
        r = _make_routine(start_time=time(3, 30), end_time=time(5, 15))
        assert r.start_time.minute == 30
        assert r.end_time.minute == 15


# ---------------------------------------------------------------------------
# Routine — computed fields
# ---------------------------------------------------------------------------


class TestRoutineComputedFields:
    """Computed properties on :class:`Routine`."""

    def test_routine_computed_duration_minutes(self) -> None:
        r = _make_routine(start_time=time(3, 0), end_time=time(5, 0))
        assert r.duration_minutes == 120

    def test_duration_handles_partial_hours(self) -> None:
        r = _make_routine(start_time=time(3, 15), end_time=time(5, 45))
        # 2h30m = 150 minutes
        assert r.duration_minutes == 150

    def test_duration_minutes_appears_in_model_dump(self) -> None:
        r = _make_routine()
        data = r.model_dump()
        assert data["duration_minutes"] == 120

    def test_active_on_weekend_true_for_full_week(self) -> None:
        r = _make_routine()  # all 7 days
        assert r.active_on_weekend is True

    def test_active_on_weekend_true_for_saturday_only(self) -> None:
        r = _make_routine(days_of_week={0, 1, 2, 3, 4, 5})
        assert r.active_on_weekend is True

    def test_active_on_weekend_true_for_sunday_only(self) -> None:
        r = _make_routine(days_of_week={0, 1, 2, 3, 4, 6})
        assert r.active_on_weekend is True

    def test_active_on_weekend_false_for_weekdays_only(self) -> None:
        r = _make_routine(days_of_week={0, 1, 2, 3, 4})
        assert r.active_on_weekend is False


# ---------------------------------------------------------------------------
# Routine — JSON roundtrip
# ---------------------------------------------------------------------------


class TestRoutineJsonRoundtrip:
    """JSON encode/decode preserves the entity."""

    def test_json_roundtrip_preserves_all_fields(self) -> None:
        r = _make_routine(
            description="With notes",
            days_of_week={0, 1, 2, 3, 4, 5},
        )
        decoded: Routine = roundtrip(r)
        assert decoded == r
        assert decoded.duration_minutes == r.duration_minutes

    def test_json_contains_ueid_as_string(self) -> None:
        r = _make_routine()
        payload = json.loads(r.model_dump_json())
        assert payload["id"] == "rou_morning_wake"
        assert payload["period"] == "MANHA"
        assert payload["routine_type"] == "ENTRY"

    def test_json_roundtrip_preserves_days_of_week_set(self) -> None:
        r = _make_routine(days_of_week={0, 2, 4, 6})
        payload = json.loads(r.model_dump_json())
        # Pydantic serialises set -> list
        assert isinstance(payload["days_of_week"], list)
        assert set(payload["days_of_week"]) == {0, 2, 4, 6}
        decoded: Routine = roundtrip(r)
        assert decoded.days_of_week == {0, 2, 4, 6}


# ---------------------------------------------------------------------------
# Ritual — construction
# ---------------------------------------------------------------------------


class TestRitualConstruction:
    """Happy-path construction of :class:`Ritual`."""

    def test_ritual_creation(self) -> None:
        r = _make_ritual()
        assert r.id == "rit_hydration_am"
        assert r.name == "Hidratação matinal"
        assert r.ritual_type is RitualType.HYDRATION
        assert r.duration_minutes == 5
        assert r.triggers_routine_id is None
        assert r.created_at == TS

    def test_ritual_with_trigger(self) -> None:
        r = _make_ritual(
            ritual_type=RitualType.MORNING,
            duration_minutes=10,
            triggers_routine_id="rou_morning_wake",
        )
        assert r.triggers_routine_id == "rou_morning_wake"

    @pytest.mark.parametrize("rt", list(RitualType))
    def test_ritual_type_assignment(self, rt: RitualType) -> None:
        r = _make_ritual(ritual_type=rt)
        assert r.ritual_type is rt

    def test_ritual_frozen(self) -> None:
        r = _make_ritual()
        with pytest.raises(ValidationError):
            r.duration_minutes = 99  # type: ignore[misc]

    def test_ritual_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            _make_ritual(bogus="x")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Ritual — duration bounds
# ---------------------------------------------------------------------------


class TestRitualDurationBounds:
    """``duration_minutes`` is clamped to ``[1, 60]``."""

    def test_ritual_accepts_minimum_duration(self) -> None:
        r = _make_ritual(duration_minutes=1)
        assert r.duration_minutes == 1

    def test_ritual_accepts_maximum_duration(self) -> None:
        r = _make_ritual(duration_minutes=60)
        assert r.duration_minutes == 60

    @pytest.mark.parametrize("value", [0, -1, -100, 61, 100, 9999])
    def test_ritual_rejects_out_of_bounds_duration(self, value: int) -> None:
        with pytest.raises(ValidationError):
            _make_ritual(duration_minutes=value)


# ---------------------------------------------------------------------------
# Ritual — computed fields
# ---------------------------------------------------------------------------


class TestRitualComputedFields:
    """Computed properties on :class:`Ritual`."""

    def test_default_period_for_morning_ritual(self) -> None:
        r = _make_ritual(ritual_type=RitualType.MORNING)
        assert r.default_period is Period.MANHA

    def test_default_period_for_shutdown_ritual(self) -> None:
        r = _make_ritual(ritual_type=RitualType.SHUTDOWN)
        assert r.default_period is Period.NOITE

    def test_default_period_for_hydration_is_none(self) -> None:
        r = _make_ritual(ritual_type=RitualType.HYDRATION)
        assert r.default_period is None

    def test_triggers_routine_false_when_no_link(self) -> None:
        r = _make_ritual()
        assert r.triggers_routine is False

    def test_triggers_routine_true_when_linked(self) -> None:
        r = _make_ritual(triggers_routine_id="rou_morning_wake")
        assert r.triggers_routine is True

    def test_default_period_appears_in_model_dump(self) -> None:
        r = _make_ritual(ritual_type=RitualType.MEDITATION)
        data = r.model_dump()
        assert data["default_period"] == "MANHA"


# ---------------------------------------------------------------------------
# Ritual — JSON roundtrip
# ---------------------------------------------------------------------------


class TestRitualJsonRoundtrip:
    """JSON encode/decode preserves the entity."""

    def test_json_roundtrip(self) -> None:
        r = _make_ritual(
            triggers_routine_id="rou_morning_wake",
        )
        decoded: Ritual = roundtrip(r)
        assert decoded == r
        assert decoded.triggers_routine_id == "rou_morning_wake"

    def test_json_contains_ritual_type_as_string(self) -> None:
        r = _make_ritual(ritual_type=RitualType.MORNING)
        payload = json.loads(r.model_dump_json())
        assert payload["ritual_type"] == "MORNING"


# ---------------------------------------------------------------------------
# Transition — construction
# ---------------------------------------------------------------------------


class TestTransitionConstruction:
    """Happy-path construction of :class:`Transition`."""

    def test_transition_basic(self) -> None:
        t = _make_transition()
        assert t.id == "trn_manha_tarde"
        assert t.name == "Transição manhã→tarde"
        assert t.from_period is Period.MANHA
        assert t.to_period is Period.TARDE
        assert t.rituals == []
        assert t.duration_minutes == 15

    def test_transition_with_rituals(self) -> None:
        t = _make_transition(
            rituals=["rit_hydration_am", "rit_meditation"],
        )
        assert t.rituals == ["rit_hydration_am", "rit_meditation"]

    def test_transition_rituals_optional(self) -> None:
        t = _make_transition(rituals=[])
        assert t.rituals == []

    def test_transition_frozen(self) -> None:
        t = _make_transition()
        with pytest.raises(ValidationError):
            t.duration_minutes = 99  # type: ignore[misc]

    def test_transition_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            _make_transition(bogus="x")  # type: ignore[call-arg]

    @pytest.mark.parametrize(
        "period",
        [(Period.MANHA, Period.TARDE), (Period.TARDE, Period.NOITE),
         (Period.NOITE, Period.MANHA)],
    )
    def test_transition_accepts_all_period_pairs(
        self, period: tuple[Period, Period],
    ) -> None:
        src, dst = period
        t = _make_transition(from_period=src, to_period=dst)
        assert t.from_period is src
        assert t.to_period is dst


# ---------------------------------------------------------------------------
# Transition — validators
# ---------------------------------------------------------------------------


class TestTransitionValidators:
    """Cross-field invariants on :class:`Transition`."""

    @pytest.mark.parametrize(
        "period",
        [Period.MANHA, Period.TARDE, Period.NOITE],
    )
    def test_transition_periods_must_differ(self, period: Period) -> None:
        with pytest.raises(ValidationError) as exc:
            _make_transition(from_period=period, to_period=period)
        assert "differ" in str(exc.value).lower()

    def test_transition_duration_zero_allowed(self) -> None:
        """Instantaneous transitions (duration=0) are allowed."""
        t = _make_transition(duration_minutes=0)
        assert t.duration_minutes == 0

    def test_transition_duration_max(self) -> None:
        t = _make_transition(duration_minutes=120)
        assert t.duration_minutes == 120

    @pytest.mark.parametrize("value", [-1, 121, 9999])
    def test_transition_rejects_out_of_bounds_duration(self, value: int) -> None:
        with pytest.raises(ValidationError):
            _make_transition(duration_minutes=value)


# ---------------------------------------------------------------------------
# Transition — computed fields
# ---------------------------------------------------------------------------


class TestTransitionComputedFields:
    """Computed properties on :class:`Transition`."""

    def test_is_ritual_heavy_false_for_no_rituals(self) -> None:
        t = _make_transition()
        assert t.is_ritual_heavy is False

    def test_is_ritual_heavy_false_for_one_ritual(self) -> None:
        t = _make_transition(rituals=["rit_hydration_am"])
        assert t.is_ritual_heavy is False

    def test_is_ritual_heavy_true_for_two_rituals(self) -> None:
        t = _make_transition(rituals=["rit_a", "rit_b"])
        assert t.is_ritual_heavy is True

    def test_is_ritual_heavy_true_for_three_rituals(self) -> None:
        t = _make_transition(rituals=["rit_a", "rit_b", "rit_c"])
        assert t.is_ritual_heavy is True


# ---------------------------------------------------------------------------
# Transition — JSON roundtrip
# ---------------------------------------------------------------------------


class TestTransitionJsonRoundtrip:
    """JSON encode/decode preserves the entity."""

    def test_json_roundtrip(self) -> None:
        t = _make_transition(rituals=["rit_a", "rit_b"])
        decoded: Transition = roundtrip(t)
        assert decoded == t
        assert decoded.rituals == ["rit_a", "rit_b"]

    def test_json_periods_as_strings(self) -> None:
        t = _make_transition()
        payload = json.loads(t.model_dump_json())
        assert payload["from_period"] == "MANHA"
        assert payload["to_period"] == "TARDE"


# ---------------------------------------------------------------------------
# Immutability deep dive
# ---------------------------------------------------------------------------


class TestImmutability:
    """Frozen guarantees survive deep copies and dataclass-y scenarios."""

    def test_routine_cannot_be_mutated_in_place(self) -> None:
        """``frozen=True`` blocks attribute assignment, the standard mutation path.

        ``model_copy(update=...)`` is the **legitimate** way to derive a
        modified model from an immutable one and must not raise.
        """
        r = _make_routine()
        with pytest.raises(ValidationError):
            r.name = "New"  # type: ignore[misc]
        # model_copy succeeds — it returns a new instance, not a mutation
        clone = r.model_copy(update={"name": "New"})
        assert clone.name == "New"
        assert r.name == "Acordar 3-5am"

    def test_routine_deepcopy_preserves_data(self) -> None:
        r = _make_routine()
        clone = deepcopy(r)
        assert clone == r
        assert clone.duration_minutes == r.duration_minutes

    def test_ritual_copy_preserves_data(self) -> None:
        r = _make_ritual()
        clone = copy(r)
        assert clone == r

    def test_transition_deepcopy_preserves_data(self) -> None:
        t = _make_transition(rituals=["rit_a"])
        clone = deepcopy(t)
        assert clone == t
        assert clone.rituals == ["rit_a"]


# ---------------------------------------------------------------------------
# Weekday annotation
# ---------------------------------------------------------------------------


class TestWeekdayTypeAlias:
    """``Weekday`` is a branded integer in ``[0, 6]``."""

    def test_weekday_accepts_zero(self) -> None:
        """Used indirectly via ``set[Weekday]`` field; verify 0 works."""
        r = _make_routine(days_of_week={0})
        assert 0 in r.days_of_week

    def test_weekday_accepts_six(self) -> None:
        r = _make_routine(days_of_week={6})
        assert 6 in r.days_of_week

    def test_weekday_rejects_seven(self) -> None:
        with pytest.raises(ValidationError):
            _make_routine(days_of_week={7})
