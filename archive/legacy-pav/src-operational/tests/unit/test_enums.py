"""Comprehensive unit tests for ``operational.enums``.

Covers all 10 StrEnum classes defined in the module. Tests are organized
as a single class per enum to keep failure attribution clear. Parametric
serialization roundtrip is exercised for every enum.
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import ClassVar

import pytest

from operational.enums import (
    AlertLevel,
    EnergyLevel,
    HabitCategory,
    Period,
    PolicyState,
    PomodoroState,
    QualityLabel,
    RitualType,
    RoutineType,
    WeekLabel,
)

ALL_ENUMS: ClassVar[tuple[type[StrEnum], ...]] = (
    Period,
    RoutineType,
    RitualType,
    HabitCategory,
    EnergyLevel,
    QualityLabel,
    PomodoroState,
    PolicyState,
    WeekLabel,
    AlertLevel,
)


# ---------------------------------------------------------------------------
# Generic, parametric tests applied to every enum
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("enum_cls", ALL_ENUMS, ids=lambda c: c.__name__)
class TestEnumBase:
    """Generic invariants all enums must satisfy."""

    def test_enum_is_str_enum(self, enum_cls: type[StrEnum]) -> None:
        """Every enum must inherit from ``enum.StrEnum``."""
        assert issubclass(enum_cls, StrEnum)

    def test_enum_values_unique(self, enum_cls: type[StrEnum]) -> None:
        """All member values must be unique within the enum."""
        values = [member.value for member in enum_cls]
        assert len(values) == len(set(values))

    def test_enum_has_members(self, enum_cls: type[StrEnum]) -> None:
        """Every enum must declare at least one member."""
        assert len(list(enum_cls)) > 0

    def test_enum_string_equality(self, enum_cls: type[StrEnum]) -> None:
        """First member equals its string value."""
        first_member = next(iter(enum_cls))
        assert first_member == first_member.value
        assert first_member.value == str(first_member)

    def test_enum_iteration(self, enum_cls: type[StrEnum]) -> None:
        """Iteration yields exactly the declared members."""
        members = list(enum_cls)
        assert len(members) >= 1
        assert all(isinstance(m, enum_cls) for m in members)

    def test_roundtrip_by_value(self, enum_cls: type[StrEnum]) -> None:
        """``Enum(value)`` must round-trip for every member."""
        for member in enum_cls:
            assert enum_cls(member.value) is member

    def test_json_roundtrip(self, enum_cls: type[StrEnum]) -> None:
        """Each member survives a JSON round-trip as a string."""
        for member in enum_cls:
            payload = json.dumps(member.value)
            assert json.loads(payload) == member.value

    def test_members_are_singletons(self, enum_cls: type[StrEnum]) -> None:
        """All members are singletons — same value yields same object."""
        for member in enum_cls:
            assert enum_cls(member.value) is member
            assert enum_cls[member.name] is member

    def test_unknown_value_raises(self, enum_cls: type[StrEnum]) -> None:
        """Constructing from an unknown value must raise ``ValueError``."""
        with pytest.raises(ValueError):
            enum_cls("__definitely_not_a_valid_value__")


# ---------------------------------------------------------------------------
# Period
# ---------------------------------------------------------------------------


class TestPeriod:
    """Specific tests for :class:`Period`."""

    def test_period_chronological_order(self) -> None:
        """MANHA starts earliest, TARDE in the middle, NOITE last."""
        assert Period.MANHA.default_start_hour < Period.TARDE.default_start_hour
        assert Period.TARDE.default_start_hour < Period.NOITE.default_start_hour
        assert Period.MANHA.default_end_hour < Period.TARDE.default_end_hour
        assert Period.TARDE.default_end_hour < Period.NOITE.default_end_hour

    def test_default_start_hour(self) -> None:
        """Each period exposes the canonical start hour from PAV §3."""
        assert Period.MANHA.default_start_hour == 3
        assert Period.TARDE.default_start_hour == 8
        assert Period.NOITE.default_start_hour == 18

    def test_default_end_hour(self) -> None:
        """Each period exposes the canonical end hour from PAV §3."""
        assert Period.MANHA.default_end_hour == 5
        assert Period.TARDE.default_end_hour == 17
        assert Period.NOITE.default_end_hour == 21

    def test_is_work_period(self) -> None:
        """Only TARDE is the work period."""
        assert Period.TARDE.is_work_period is True
        assert Period.MANHA.is_work_period is False
        assert Period.NOITE.is_work_period is False

    def test_member_count(self) -> None:
        """Exactly 3 periods are defined."""
        assert len(list(Period)) == 3


# ---------------------------------------------------------------------------
# RoutineType
# ---------------------------------------------------------------------------


class TestRoutineType:
    """Specific tests for :class:`RoutineType`."""

    def test_member_count(self) -> None:
        """Exactly 4 routine types are defined."""
        assert len(list(RoutineType)) == 4

    def test_is_ritual(self) -> None:
        """ENTRY, TRANSITION, EXIT are rituals; CORE is not."""
        assert RoutineType.ENTRY.is_ritual is True
        assert RoutineType.TRANSITION.is_ritual is True
        assert RoutineType.EXIT.is_ritual is True
        assert RoutineType.CORE.is_ritual is False

    def test_is_boundary(self) -> None:
        """ENTRY and EXIT are boundary rituals."""
        assert RoutineType.ENTRY.is_boundary is True
        assert RoutineType.EXIT.is_boundary is True
        assert RoutineType.CORE.is_boundary is False
        assert RoutineType.TRANSITION.is_boundary is False


# ---------------------------------------------------------------------------
# RitualType
# ---------------------------------------------------------------------------


class TestRitualType:
    """Specific tests for :class:`RitualType`."""

    def test_member_count(self) -> None:
        """Exactly 6 ritual types are defined."""
        assert len(list(RitualType)) == 6

    def test_default_period_mapping(self) -> None:
        """Each ritual maps to its canonical period (or None)."""
        assert RitualType.MORNING.default_period is Period.MANHA
        assert RitualType.MEDITATION.default_period is Period.MANHA
        assert RitualType.SHUTDOWN.default_period is Period.NOITE
        assert RitualType.REVIEW.default_period is Period.NOITE
        assert RitualType.EVENING.default_period is Period.NOITE
        assert RitualType.HYDRATION.default_period is None

    def test_is_evening(self) -> None:
        """SHUTDOWN, REVIEW, EVENING are evening rituals."""
        assert RitualType.SHUTDOWN.is_evening is True
        assert RitualType.REVIEW.is_evening is True
        assert RitualType.EVENING.is_evening is True
        assert RitualType.MORNING.is_evening is False
        assert RitualType.MEDITATION.is_evening is False
        assert RitualType.HYDRATION.is_evening is False


# ---------------------------------------------------------------------------
# HabitCategory
# ---------------------------------------------------------------------------


class TestHabitCategory:
    """Specific tests for :class:`HabitCategory`."""

    def test_member_count(self) -> None:
        """Exactly 5 habit categories are defined."""
        assert len(list(HabitCategory)) == 5

    def test_is_body(self) -> None:
        """Only PHYSIOLOGICAL targets the body."""
        assert HabitCategory.PHYSIOLOGICAL.is_body is True
        for cat in HabitCategory:
            if cat is HabitCategory.PHYSIOLOGICAL:
                continue
            assert cat.is_body is False

    def test_is_mind(self) -> None:
        """COGNITIVE and CREATIVE target the mind."""
        assert HabitCategory.COGNITIVE.is_mind is True
        assert HabitCategory.CREATIVE.is_mind is True
        assert HabitCategory.PHYSIOLOGICAL.is_mind is False
        assert HabitCategory.SOCIAL.is_mind is False
        assert HabitCategory.RITUAL.is_mind is False

    def test_values_are_lowercase(self) -> None:
        """PRD-02 mandates lowercase values for habit categories."""
        for member in HabitCategory:
            assert member.value == member.value.lower()
            assert "_" not in member.value


# ---------------------------------------------------------------------------
# EnergyLevel
# ---------------------------------------------------------------------------


class TestEnergyLevel:
    """Specific tests for :class:`EnergyLevel`."""

    def test_member_count(self) -> None:
        """Exactly 3 energy levels are defined."""
        assert len(list(EnergyLevel)) == 3

    def test_numeric_values(self) -> None:
        """Numeric values follow H=2, M=1, L=0."""
        assert EnergyLevel.HIGH.numeric == 2
        assert EnergyLevel.MEDIUM.numeric == 1
        assert EnergyLevel.LOW.numeric == 0

    def test_label(self) -> None:
        """Human labels are properly capitalized."""
        assert EnergyLevel.HIGH.label == "High"
        assert EnergyLevel.MEDIUM.label == "Medium"
        assert EnergyLevel.LOW.label == "Low"

    def test_ordering(self) -> None:
        """LOW < MEDIUM < HIGH."""
        assert EnergyLevel.LOW < EnergyLevel.MEDIUM
        assert EnergyLevel.MEDIUM < EnergyLevel.HIGH
        assert EnergyLevel.LOW < EnergyLevel.HIGH
        assert EnergyLevel.HIGH > EnergyLevel.LOW
        assert EnergyLevel.HIGH >= EnergyLevel.HIGH
        assert EnergyLevel.LOW <= EnergyLevel.LOW

    def test_ordering_with_non_energy(self) -> None:
        """Comparing with a non-EnergyLevel raises ``TypeError``."""
        sentinel = object()
        with pytest.raises(TypeError):
            _ = EnergyLevel.HIGH < sentinel  # type: ignore[operator]
        with pytest.raises(TypeError):
            _ = EnergyLevel.HIGH <= sentinel  # type: ignore[operator]
        with pytest.raises(TypeError):
            _ = EnergyLevel.HIGH > sentinel  # type: ignore[operator]
        with pytest.raises(TypeError):
            _ = EnergyLevel.HIGH >= sentinel  # type: ignore[operator]
        # And the reflected comparisons from the other side
        with pytest.raises(TypeError):
            _ = sentinel < EnergyLevel.HIGH  # type: ignore[operator]


# ---------------------------------------------------------------------------
# QualityLabel
# ---------------------------------------------------------------------------


class TestQualityLabel:
    """Specific tests for :class:`QualityLabel`."""

    def test_member_count(self) -> None:
        """Exactly 5 quality labels are defined."""
        assert len(list(QualityLabel)) == 5

    def test_min_hours(self) -> None:
        """Each label exposes its lower bound in hours."""
        assert QualityLabel.EXCELENTE.min_hours == 9.0
        assert QualityLabel.BOM.min_hours == 8.0
        assert QualityLabel.ACEITAVEL.min_hours == 7.0
        assert QualityLabel.HARDCORE.min_hours == 4.0
        assert QualityLabel.CRITICO.min_hours == 0.0

    @pytest.mark.parametrize(
        ("hours", "expected"),
        [
            (10.0, QualityLabel.EXCELENTE),
            (9.0, QualityLabel.EXCELENTE),
            (9.5, QualityLabel.EXCELENTE),
            (8.5, QualityLabel.BOM),
            (8.0, QualityLabel.BOM),
            (7.5, QualityLabel.ACEITAVEL),
            (7.0, QualityLabel.ACEITAVEL),
            (6.0, QualityLabel.HARDCORE),
            (4.0, QualityLabel.HARDCORE),
            (4.5, QualityLabel.HARDCORE),
            (3.9, QualityLabel.CRITICO),
            (0.0, QualityLabel.CRITICO),
            (-1.0, QualityLabel.CRITICO),
        ],
    )
    def test_from_hours(self, hours: float, expected: QualityLabel) -> None:
        """``from_hours`` classifies boundaries correctly."""
        assert QualityLabel.from_hours(hours) is expected


# ---------------------------------------------------------------------------
# PomodoroState
# ---------------------------------------------------------------------------


class TestPomodoroState:
    """Specific tests for :class:`PomodoroState`."""

    def test_state_count(self) -> None:
        """Exactly 7 pomodoro states are defined."""
        assert len(list(PomodoroState)) == 7

    def test_terminal_states(self) -> None:
        """IDLE, SKIPPED, COMPLETE are terminal."""
        assert PomodoroState.IDLE.is_terminal is True
        assert PomodoroState.SKIPPED.is_terminal is True
        assert PomodoroState.COMPLETE.is_terminal is True
        assert PomodoroState.WORK.is_terminal is False
        assert PomodoroState.BREAK.is_terminal is False
        assert PomodoroState.LONG_BREAK.is_terminal is False
        assert PomodoroState.PAUSED.is_terminal is False

    def test_active_states(self) -> None:
        """WORK, BREAK, LONG_BREAK are active (timer running)."""
        assert PomodoroState.WORK.is_active is True
        assert PomodoroState.BREAK.is_active is True
        assert PomodoroState.LONG_BREAK.is_active is True
        assert PomodoroState.IDLE.is_active is False
        assert PomodoroState.PAUSED.is_active is False
        assert PomodoroState.SKIPPED.is_active is False
        assert PomodoroState.COMPLETE.is_active is False

    def test_paused_state(self) -> None:
        """Only PAUSED reports ``is_paused``."""
        assert PomodoroState.PAUSED.is_paused is True
        for state in PomodoroState:
            if state is PomodoroState.PAUSED:
                continue
            assert state.is_paused is False

    @pytest.mark.parametrize(
        ("source", "target", "expected"),
        [
            (PomodoroState.IDLE, PomodoroState.WORK, True),
            (PomodoroState.WORK, PomodoroState.BREAK, True),
            (PomodoroState.WORK, PomodoroState.SKIPPED, True),
            (PomodoroState.BREAK, PomodoroState.WORK, True),
            (PomodoroState.BREAK, PomodoroState.LONG_BREAK, True),
            (PomodoroState.LONG_BREAK, PomodoroState.COMPLETE, True),
            (PomodoroState.WORK, PomodoroState.PAUSED, True),
            (PomodoroState.PAUSED, PomodoroState.WORK, True),
            (PomodoroState.SKIPPED, PomodoroState.IDLE, True),
            (PomodoroState.COMPLETE, PomodoroState.IDLE, True),
            (PomodoroState.IDLE, PomodoroState.BREAK, False),
            (PomodoroState.WORK, PomodoroState.IDLE, False),
            (PomodoroState.IDLE, PomodoroState.COMPLETE, False),
            (PomodoroState.WORK, PomodoroState.LONG_BREAK, False),
            (PomodoroState.SKIPPED, PomodoroState.WORK, False),
        ],
    )
    def test_can_transition_to(
        self, source: PomodoroState, target: PomodoroState, expected: bool
    ) -> None:
        """Each transition is allowed or rejected as documented."""
        assert source.can_transition_to(target) is expected


# ---------------------------------------------------------------------------
# PolicyState
# ---------------------------------------------------------------------------


class TestPolicyState:
    """Specific tests for :class:`PolicyState`."""

    def test_state_count(self) -> None:
        """Exactly 4 policy states are defined."""
        assert len(list(PolicyState)) == 4

    def test_state_order(self) -> None:
        """PUSH < MAINTAIN < REDUCE < RECOVER (by load)."""
        assert PolicyState.PUSH.ordinal < PolicyState.MAINTAIN.ordinal
        assert PolicyState.MAINTAIN.ordinal < PolicyState.REDUCE.ordinal
        assert PolicyState.REDUCE.ordinal < PolicyState.RECOVER.ordinal
        # Operators too
        assert PolicyState.PUSH < PolicyState.MAINTAIN
        assert PolicyState.MAINTAIN < PolicyState.REDUCE
        assert PolicyState.REDUCE < PolicyState.RECOVER
        assert PolicyState.PUSH <= PolicyState.PUSH
        assert PolicyState.RECOVER >= PolicyState.RECOVER
        assert PolicyState.RECOVER > PolicyState.PUSH

    def test_is_protective(self) -> None:
        """REDUCE and RECOVER are protective."""
        assert PolicyState.REDUCE.is_protective is True
        assert PolicyState.RECOVER.is_protective is True
        assert PolicyState.PUSH.is_protective is False
        assert PolicyState.MAINTAIN.is_protective is False

    def test_is_productive(self) -> None:
        """PUSH and MAINTAIN are productive."""
        assert PolicyState.PUSH.is_productive is True
        assert PolicyState.MAINTAIN.is_productive is True
        assert PolicyState.REDUCE.is_productive is False
        assert PolicyState.RECOVER.is_productive is False

    def test_is_critical(self) -> None:
        """Only RECOVER is critical."""
        assert PolicyState.RECOVER.is_critical is True
        assert PolicyState.PUSH.is_critical is False
        assert PolicyState.MAINTAIN.is_critical is False
        assert PolicyState.REDUCE.is_critical is False

    @pytest.mark.parametrize(
        ("source", "target", "expected"),
        [
            (PolicyState.PUSH, PolicyState.MAINTAIN, True),
            (PolicyState.MAINTAIN, PolicyState.PUSH, True),
            (PolicyState.MAINTAIN, PolicyState.REDUCE, True),
            (PolicyState.REDUCE, PolicyState.MAINTAIN, True),
            (PolicyState.REDUCE, PolicyState.RECOVER, True),
            (PolicyState.RECOVER, PolicyState.REDUCE, True),
            (PolicyState.PUSH, PolicyState.REDUCE, False),
            (PolicyState.PUSH, PolicyState.RECOVER, False),
            (PolicyState.MAINTAIN, PolicyState.RECOVER, False),
            (PolicyState.RECOVER, PolicyState.PUSH, False),
            (PolicyState.PUSH, PolicyState.PUSH, False),
        ],
    )
    def test_can_step_to(self, source: PolicyState, target: PolicyState, expected: bool) -> None:
        """Hysteresis allows only one-step transitions."""
        assert source.can_step_to(target) is expected

    def test_ordering_with_non_policy(self) -> None:
        """Comparing with a non-PolicyState raises ``TypeError``."""
        sentinel = object()
        with pytest.raises(TypeError):
            _ = PolicyState.PUSH < sentinel  # type: ignore[operator]
        with pytest.raises(TypeError):
            _ = PolicyState.PUSH <= sentinel  # type: ignore[operator]
        with pytest.raises(TypeError):
            _ = PolicyState.PUSH > sentinel  # type: ignore[operator]
        with pytest.raises(TypeError):
            _ = PolicyState.PUSH >= sentinel  # type: ignore[operator]


# ---------------------------------------------------------------------------
# WeekLabel
# ---------------------------------------------------------------------------


class TestWeekLabel:
    """Specific tests for :class:`WeekLabel`."""

    def test_member_count(self) -> None:
        """Exactly 5 weekly labels are defined."""
        assert len(list(WeekLabel)) == 5

    def test_min_score(self) -> None:
        """Each label exposes its lower bound in normalized score."""
        assert WeekLabel.EXCELENTE.min_score == 0.9
        assert WeekLabel.BOM.min_score == 0.75
        assert WeekLabel.MEDIO.min_score == 0.6
        assert WeekLabel.RUIM.min_score == 0.4
        assert WeekLabel.RECUPERACAO.min_score == 0.0

    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (1.0, WeekLabel.EXCELENTE),
            (0.95, WeekLabel.EXCELENTE),
            (0.9, WeekLabel.EXCELENTE),
            (0.89, WeekLabel.BOM),
            (0.75, WeekLabel.BOM),
            (0.74, WeekLabel.MEDIO),
            (0.6, WeekLabel.MEDIO),
            (0.59, WeekLabel.RUIM),
            (0.4, WeekLabel.RUIM),
            (0.39, WeekLabel.RECUPERACAO),
            (0.0, WeekLabel.RECUPERACAO),
            (1.5, WeekLabel.EXCELENTE),
            (-0.1, WeekLabel.RECUPERACAO),
        ],
    )
    def test_from_score(self, score: float, expected: WeekLabel) -> None:
        """``from_score`` classifies boundaries correctly and clamps outliers."""
        assert WeekLabel.from_score(score) is expected


# ---------------------------------------------------------------------------
# AlertLevel
# ---------------------------------------------------------------------------


class TestAlertLevel:
    """Specific tests for :class:`AlertLevel`."""

    def test_member_count(self) -> None:
        """Exactly 3 alert levels are defined."""
        assert len(list(AlertLevel)) == 3

    def test_severity(self) -> None:
        """Severity ordinals are 0/1/2."""
        assert AlertLevel.INFO.severity == 0
        assert AlertLevel.WARNING.severity == 1
        assert AlertLevel.CRITICAL.severity == 2

    def test_requires_action(self) -> None:
        """INFO does not require action; WARNING and CRITICAL do."""
        assert AlertLevel.INFO.requires_action is False
        assert AlertLevel.WARNING.requires_action is True
        assert AlertLevel.CRITICAL.requires_action is True

    def test_ordering(self) -> None:
        """INFO < WARNING < CRITICAL."""
        assert AlertLevel.INFO < AlertLevel.WARNING
        assert AlertLevel.WARNING < AlertLevel.CRITICAL
        assert AlertLevel.INFO <= AlertLevel.INFO
        assert AlertLevel.CRITICAL >= AlertLevel.CRITICAL
        assert AlertLevel.CRITICAL > AlertLevel.INFO

    def test_ordering_with_non_alert(self) -> None:
        """Comparing with a non-AlertLevel raises ``TypeError``."""
        sentinel = object()
        with pytest.raises(TypeError):
            _ = AlertLevel.INFO < sentinel  # type: ignore[operator]
        with pytest.raises(TypeError):
            _ = AlertLevel.INFO <= sentinel  # type: ignore[operator]
        with pytest.raises(TypeError):
            _ = AlertLevel.INFO > sentinel  # type: ignore[operator]
        with pytest.raises(TypeError):
            _ = AlertLevel.INFO >= sentinel  # type: ignore[operator]


# ---------------------------------------------------------------------------
# Cross-enum
# ---------------------------------------------------------------------------


class TestEnumCrossCutting:
    """Cross-cutting invariants across all enums."""

    def test_module_all_complete(self) -> None:
        """The module exposes all 10 enums in its ``__all__``."""
        import operational.enums as mod

        expected = {
            "Period",
            "RoutineType",
            "RitualType",
            "HabitCategory",
            "EnergyLevel",
            "QualityLabel",
            "PomodoroState",
            "PolicyState",
            "WeekLabel",
            "AlertLevel",
        }
        assert expected.issubset(set(mod.__all__))

    @pytest.mark.parametrize("enum_cls", ALL_ENUMS, ids=lambda c: c.__name__)
    def test_all_members_have_string_value(self, enum_cls: type[StrEnum]) -> None:
        """All values are non-empty strings."""
        for member in enum_cls:
            assert isinstance(member.value, str)
            assert member.value != ""

    @pytest.mark.parametrize("enum_cls", ALL_ENUMS, ids=lambda c: c.__name__)
    def test_str_returns_value(self, enum_cls: type[StrEnum]) -> None:
        """``str(member)`` returns the underlying string value."""
        for member in enum_cls:
            assert str(member) == member.value
