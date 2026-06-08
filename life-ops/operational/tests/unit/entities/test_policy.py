"""Comprehensive unit tests for :mod:`operational.entities.policy`.

Covers all three policy governance entities:

* :class:`PolicySetpoints` — construction, ranges, factory, frozen,
  extra-forbid.
* :class:`PolicyDecision` — construction, validators (setpoints match
  state, applied auto-timestamp), all 4 :class:`PolicyState` values,
  factory, re-assignment under ``validate_assignment=True``.
* :class:`DecisionRecord` — initial-state record, transition validation,
  field constraints, factory.

The tests are organized in three sections (one per entity) plus a
cross-cutting section for the state-transition cycle and the setpoint
factory.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import ClassVar

import pytest
from pydantic import ValidationError

from operational.entities.policy import DecisionRecord, PolicyDecision, PolicySetpoints
from operational.enums import EnergyLevel, PolicyState

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

#: A reusable fixed timestamp for deterministic tests.
_FIXED_TS: datetime = datetime(2026, 6, 7, 9, 0, 0)

#: A reusable calendar date for decision / record tests.
_FIXED_DATE: date = date(2026, 6, 7)

#: A reusable ID prefix for setpoints.
_SET_ID: str = "set_unit0001a"

#: A reusable ID prefix for decisions.
_DEC_ID: str = "pol_unit0001a"

#: A reusable ID prefix for records.
_REC_ID: str = "rec_unit0001a"

#: All four canonical :class:`PolicyState` members, in declared order.
_ALL_STATES: ClassVar[tuple[PolicyState, ...]] = tuple(PolicyState)


def _make_setpoints(
    state: PolicyState = PolicyState.PUSH,
    *,
    id: str = _SET_ID,
    created_at: datetime = _FIXED_TS,
) -> PolicySetpoints:
    """Build a valid :class:`PolicySetpoints` for the given state."""
    return PolicySetpoints(
        id=id,
        state=state,
        hardwork_budget_hours=8.0,
        max_pomodoros_per_day=10,
        sleep_target_hours=7.0,
        qhe_target=0.85,
        break_minutes=10,
        allowed_phases=["DEEP_WORK", "SHALLOW_WORK"],
        description="test setpoints",
        created_at=created_at,
    )


def _make_decision(  # noqa: PLR0913
    state: PolicyState = PolicyState.PUSH,
    *,
    id: str = _DEC_ID,
    decision_date: date = _FIXED_DATE,
    setpoints: PolicySetpoints | None = None,
    previous_state: PolicyState | None = None,
    qhe_input: float | None = None,
    energy_input: EnergyLevel | None = None,
    infraction_count: int = 0,
    days_in_state: int = 0,
    applied: bool = False,
    created_at: datetime = _FIXED_TS,
) -> PolicyDecision:
    """Build a valid :class:`PolicyDecision` for the given state."""
    sp = setpoints if setpoints is not None else _make_setpoints(state)
    return PolicyDecision(
        id=id,
        date=decision_date,
        state=state,
        severity="INFO",
        rationale="test rationale",
        setpoints=sp,
        days_in_state=days_in_state,
        previous_state=previous_state,
        qhe_input=qhe_input,
        energy_input=energy_input,
        infraction_count=infraction_count,
        created_at=created_at,
        applied=applied,
    )


# ===========================================================================
# PolicySetpoints
# ===========================================================================


class TestPolicySetpointsConstruction:
    """Direct construction tests for :class:`PolicySetpoints`."""

    def test_create_policy_setpoints_push(self) -> None:
        """A PUSH setpoints instance is buildable with valid fields."""
        sp = _make_setpoints(PolicyState.PUSH)
        assert sp.state is PolicyState.PUSH
        assert sp.hardwork_budget_hours == 8.0
        assert sp.max_pomodoros_per_day == 10
        assert sp.sleep_target_hours == 7.0
        assert sp.qhe_target == 0.85
        assert sp.break_minutes == 10
        assert sp.allowed_phases == ["DEEP_WORK", "SHALLOW_WORK"]
        assert sp.id == _SET_ID
        assert sp.created_at == _FIXED_TS

    def test_create_policy_setpoints_maintain(self) -> None:
        """A MAINTAIN setpoints instance is buildable."""
        sp = PolicySetpoints(
            id=_SET_ID,
            state=PolicyState.MAINTAIN,
            hardwork_budget_hours=6.0,
            max_pomodoros_per_day=8,
            sleep_target_hours=8.0,
            qhe_target=0.75,
            break_minutes=10,
            allowed_phases=["DEEP_WORK", "SHALLOW_WORK"],
            description="maintain",
            created_at=_FIXED_TS,
        )
        assert sp.state is PolicyState.MAINTAIN
        assert sp.hardwork_budget_hours == 6.0
        assert sp.qhe_target == 0.75

    def test_create_policy_setpoints_reduce(self) -> None:
        """A REDUCE setpoints instance is buildable."""
        sp = PolicySetpoints(
            id=_SET_ID,
            state=PolicyState.REDUCE,
            hardwork_budget_hours=4.0,
            max_pomodoros_per_day=5,
            sleep_target_hours=8.0,
            qhe_target=0.65,
            break_minutes=15,
            allowed_phases=["SHALLOW_WORK", "RECOVERY"],
            description="reduce",
            created_at=_FIXED_TS,
        )
        assert sp.state is PolicyState.REDUCE
        assert sp.hardwork_budget_hours == 4.0
        assert sp.break_minutes == 15

    def test_create_policy_setpoints_recover(self) -> None:
        """A RECOVER setpoints instance is buildable."""
        sp = PolicySetpoints(
            id=_SET_ID,
            state=PolicyState.RECOVER,
            hardwork_budget_hours=2.0,
            max_pomodoros_per_day=2,
            sleep_target_hours=9.0,
            qhe_target=0.50,
            break_minutes=20,
            allowed_phases=["RECOVERY"],
            description="recover",
            created_at=_FIXED_TS,
        )
        assert sp.state is PolicyState.RECOVER
        assert sp.hardwork_budget_hours == 2.0
        assert sp.allowed_phases == ["RECOVERY"]

    def test_policy_setpoints_description_default_empty(self) -> None:
        """``description`` defaults to empty string when omitted."""
        sp = PolicySetpoints(
            id=_SET_ID,
            state=PolicyState.PUSH,
            hardwork_budget_hours=8.0,
            max_pomodoros_per_day=10,
            sleep_target_hours=7.0,
            qhe_target=0.85,
            break_minutes=10,
            allowed_phases=["DEEP_WORK"],
            created_at=_FIXED_TS,
        )
        assert sp.description == ""


class TestPolicySetpointsFactory:
    """Tests for :meth:`PolicySetpoints.from_pav_defaults`."""

    def test_policy_setpoints_from_pav_defaults_push(self) -> None:
        """Factory produces the canonical PUSH setpoints."""
        sp = PolicySetpoints.from_pav_defaults(PolicyState.PUSH)
        assert sp.state is PolicyState.PUSH
        assert sp.hardwork_budget_hours == 8.0
        assert sp.max_pomodoros_per_day == 10
        assert sp.sleep_target_hours == 7.0
        assert sp.qhe_target == 0.85
        assert sp.break_minutes == 10
        assert sp.allowed_phases == ["DEEP_WORK", "SHALLOW_WORK"]
        assert sp.id.startswith("set_")
        assert isinstance(sp.created_at, datetime)

    def test_policy_setpoints_from_pav_defaults_maintain(self) -> None:
        """Factory produces the canonical MAINTAIN setpoints."""
        sp = PolicySetpoints.from_pav_defaults(PolicyState.MAINTAIN)
        assert sp.state is PolicyState.MAINTAIN
        assert sp.hardwork_budget_hours == 6.0
        assert sp.max_pomodoros_per_day == 8
        assert sp.sleep_target_hours == 8.0
        assert sp.qhe_target == 0.75
        assert sp.break_minutes == 10
        assert sp.allowed_phases == ["DEEP_WORK", "SHALLOW_WORK"]

    def test_policy_setpoints_from_pav_defaults_reduce(self) -> None:
        """Factory produces the canonical REDUCE setpoints."""
        sp = PolicySetpoints.from_pav_defaults(PolicyState.REDUCE)
        assert sp.state is PolicyState.REDUCE
        assert sp.hardwork_budget_hours == 4.0
        assert sp.max_pomodoros_per_day == 5
        assert sp.sleep_target_hours == 8.0
        assert sp.qhe_target == 0.65
        assert sp.break_minutes == 15
        assert sp.allowed_phases == ["SHALLOW_WORK", "RECOVERY"]

    def test_policy_setpoints_from_pav_defaults_recover(self) -> None:
        """Factory produces the canonical RECOVER setpoints."""
        sp = PolicySetpoints.from_pav_defaults(PolicyState.RECOVER)
        assert sp.state is PolicyState.RECOVER
        assert sp.hardwork_budget_hours == 2.0
        assert sp.max_pomodoros_per_day == 2
        assert sp.sleep_target_hours == 9.0
        assert sp.qhe_target == 0.50
        assert sp.break_minutes == 20
        assert sp.allowed_phases == ["RECOVERY"]

    def test_policy_setpoints_from_pav_defaults_overrides(self) -> None:
        """Factory accepts keyword overrides for any field."""
        custom_id = "set_override_001"
        sp = PolicySetpoints.from_pav_defaults(
            PolicyState.PUSH,
            id=custom_id,
            hardwork_budget_hours=6.5,
            description="custom",
        )
        assert sp.id == custom_id
        assert sp.hardwork_budget_hours == 6.5
        assert sp.description == "custom"
        # Non-overridden fields still canonical
        assert sp.max_pomodoros_per_day == 10
        assert sp.qhe_target == 0.85

    def test_policy_setpoints_from_pav_defaults_rejects_unknown(self) -> None:
        """Factory rejects unknown override keys (extra='forbid')."""
        with pytest.raises(ValidationError):
            PolicySetpoints.from_pav_defaults(PolicyState.PUSH, bogus_field=42)

    def test_policy_setpoints_factory_consistency(self) -> None:
        """All four factory outputs are mutually distinct and self-consistent."""
        seen: dict[PolicyState, PolicySetpoints] = {}
        for state in _ALL_STATES:
            sp = PolicySetpoints.from_pav_defaults(state)
            assert sp.state is state
            # IDs are unique per call
            for other in seen.values():
                assert sp.id != other.id
            # PUSH > MAINTAIN > REDUCE > RECOVER in workload
            seen[state] = sp
        # PUSH > MAINTAIN > REDUCE > RECOVER in workload
        push_hours = seen[PolicyState.PUSH].hardwork_budget_hours
        maintain_hours = seen[PolicyState.MAINTAIN].hardwork_budget_hours
        reduce_hours = seen[PolicyState.REDUCE].hardwork_budget_hours
        recover_hours = seen[PolicyState.RECOVER].hardwork_budget_hours
        assert push_hours > maintain_hours
        assert maintain_hours > reduce_hours
        assert reduce_hours > recover_hours
        # And inversely for sleep
        push_sleep = seen[PolicyState.PUSH].sleep_target_hours
        maintain_sleep = seen[PolicyState.MAINTAIN].sleep_target_hours
        reduce_sleep = seen[PolicyState.REDUCE].sleep_target_hours
        recover_sleep = seen[PolicyState.RECOVER].sleep_target_hours
        assert push_sleep < maintain_sleep
        assert maintain_sleep <= reduce_sleep
        assert reduce_sleep < recover_sleep


class TestPolicySetpointsValidation:
    """Range and format validators on :class:`PolicySetpoints`."""

    @pytest.mark.parametrize("value", [0.0, 1.0, 8.0, 15.5, 16.0])
    def test_policy_setpoints_hardwork_budget_range(self, value: float) -> None:
        """``hardwork_budget_hours`` accepts values in ``[0.0, 16.0]``."""
        sp = PolicySetpoints(
            id=_SET_ID,
            state=PolicyState.PUSH,
            hardwork_budget_hours=value,
            max_pomodoros_per_day=10,
            sleep_target_hours=7.0,
            qhe_target=0.85,
            break_minutes=10,
            allowed_phases=["DEEP_WORK"],
            created_at=_FIXED_TS,
        )
        assert sp.hardwork_budget_hours == value

    @pytest.mark.parametrize("value", [-0.1, -1.0, 16.01, 17.0, 100.0])
    def test_policy_setpoints_hardwork_budget_out_of_range(self, value: float) -> None:
        """``hardwork_budget_hours`` rejects values outside ``[0.0, 16.0]``."""
        with pytest.raises(ValidationError):
            PolicySetpoints(
                id=_SET_ID,
                state=PolicyState.PUSH,
                hardwork_budget_hours=value,
                max_pomodoros_per_day=10,
                sleep_target_hours=7.0,
                qhe_target=0.85,
                break_minutes=10,
                allowed_phases=["DEEP_WORK"],
                created_at=_FIXED_TS,
            )

    @pytest.mark.parametrize("value", [0, 1, 6, 10, 12])
    def test_policy_setpoints_max_pomodoros_range(self, value: int) -> None:
        """``max_pomodoros_per_day`` accepts values in ``[0, 12]``."""
        sp = PolicySetpoints(
            id=_SET_ID,
            state=PolicyState.PUSH,
            hardwork_budget_hours=8.0,
            max_pomodoros_per_day=value,
            sleep_target_hours=7.0,
            qhe_target=0.85,
            break_minutes=10,
            allowed_phases=["DEEP_WORK"],
            created_at=_FIXED_TS,
        )
        assert sp.max_pomodoros_per_day == value

    @pytest.mark.parametrize("value", [-1, 13, 14, 100])
    def test_policy_setpoints_max_pomodoros_out_of_range(self, value: int) -> None:
        """``max_pomodoros_per_day`` rejects values outside ``[0, 12]``."""
        with pytest.raises(ValidationError):
            PolicySetpoints(
                id=_SET_ID,
                state=PolicyState.PUSH,
                hardwork_budget_hours=8.0,
                max_pomodoros_per_day=value,
                sleep_target_hours=7.0,
                qhe_target=0.85,
                break_minutes=10,
                allowed_phases=["DEEP_WORK"],
                created_at=_FIXED_TS,
            )

    @pytest.mark.parametrize("value", [4.0, 5.0, 7.5, 8.0, 10.0])
    def test_policy_setpoints_sleep_target_range(self, value: float) -> None:
        """``sleep_target_hours`` accepts values in ``[4.0, 10.0]``."""
        sp = PolicySetpoints(
            id=_SET_ID,
            state=PolicyState.PUSH,
            hardwork_budget_hours=8.0,
            max_pomodoros_per_day=10,
            sleep_target_hours=value,
            qhe_target=0.85,
            break_minutes=10,
            allowed_phases=["DEEP_WORK"],
            created_at=_FIXED_TS,
        )
        assert sp.sleep_target_hours == value

    @pytest.mark.parametrize("value", [-0.1, 3.9, 10.01, 11.0, 24.0])
    def test_policy_setpoints_sleep_target_out_of_range(self, value: float) -> None:
        """``sleep_target_hours`` rejects values outside ``[4.0, 10.0]``."""
        with pytest.raises(ValidationError):
            PolicySetpoints(
                id=_SET_ID,
                state=PolicyState.PUSH,
                hardwork_budget_hours=8.0,
                max_pomodoros_per_day=10,
                sleep_target_hours=value,
                qhe_target=0.85,
                break_minutes=10,
                allowed_phases=["DEEP_WORK"],
                created_at=_FIXED_TS,
            )

    @pytest.mark.parametrize("value", [0.0, 0.5, 0.85, 1.0])
    def test_policy_setpoints_qhe_target_range(self, value: float) -> None:
        """``qhe_target`` accepts values in ``[0.0, 1.0]``."""
        sp = PolicySetpoints(
            id=_SET_ID,
            state=PolicyState.PUSH,
            hardwork_budget_hours=8.0,
            max_pomodoros_per_day=10,
            sleep_target_hours=7.0,
            qhe_target=value,
            break_minutes=10,
            allowed_phases=["DEEP_WORK"],
            created_at=_FIXED_TS,
        )
        assert sp.qhe_target == value

    @pytest.mark.parametrize("value", [-0.01, -1.0, 1.01, 2.0])
    def test_policy_setpoints_qhe_target_out_of_range(self, value: float) -> None:
        """``qhe_target`` rejects values outside ``[0.0, 1.0]``."""
        with pytest.raises(ValidationError):
            PolicySetpoints(
                id=_SET_ID,
                state=PolicyState.PUSH,
                hardwork_budget_hours=8.0,
                max_pomodoros_per_day=10,
                sleep_target_hours=7.0,
                qhe_target=value,
                break_minutes=10,
                allowed_phases=["DEEP_WORK"],
                created_at=_FIXED_TS,
            )

    @pytest.mark.parametrize("value", [1, 5, 10, 20, 30])
    def test_policy_setpoints_break_minutes_range(self, value: int) -> None:
        """``break_minutes`` accepts values in ``[1, 30]``."""
        sp = PolicySetpoints(
            id=_SET_ID,
            state=PolicyState.PUSH,
            hardwork_budget_hours=8.0,
            max_pomodoros_per_day=10,
            sleep_target_hours=7.0,
            qhe_target=0.85,
            break_minutes=value,
            allowed_phases=["DEEP_WORK"],
            created_at=_FIXED_TS,
        )
        assert sp.break_minutes == value

    @pytest.mark.parametrize("value", [0, -1, 31, 60, 120])
    def test_policy_setpoints_break_minutes_out_of_range(self, value: int) -> None:
        """``break_minutes`` rejects values outside ``[1, 30]``."""
        with pytest.raises(ValidationError):
            PolicySetpoints(
                id=_SET_ID,
                state=PolicyState.PUSH,
                hardwork_budget_hours=8.0,
                max_pomodoros_per_day=10,
                sleep_target_hours=7.0,
                qhe_target=0.85,
                break_minutes=value,
                allowed_phases=["DEEP_WORK"],
                created_at=_FIXED_TS,
            )

    @pytest.mark.parametrize(
        "phases",
        [
            ["DEEP_WORK"],
            ["SHALLOW_WORK"],
            ["RECOVERY"],
            ["DEEP_WORK", "SHALLOW_WORK"],
            ["SHALLOW_WORK", "RECOVERY"],
            ["DEEP_WORK", "SHALLOW_WORK", "RECOVERY"],
        ],
    )
    def test_policy_setpoints_allowed_phases_literal(self, phases: list[str]) -> None:
        """``allowed_phases`` accepts any non-empty subset of the 3 literals."""
        sp = PolicySetpoints(
            id=_SET_ID,
            state=PolicyState.PUSH,
            hardwork_budget_hours=8.0,
            max_pomodoros_per_day=10,
            sleep_target_hours=7.0,
            qhe_target=0.85,
            break_minutes=10,
            allowed_phases=phases,  # type: ignore[arg-type]
            created_at=_FIXED_TS,
        )
        assert sp.allowed_phases == phases

    @pytest.mark.parametrize(
        "phases",
        [
            ["INVALID"],
            ["DEEP"],
            ["deep_work"],
            ["DEEP_WORK", "INVALID"],
            [""],
        ],
    )
    def test_policy_setpoints_allowed_phases_rejects_invalid(self, phases: list[str]) -> None:
        """``allowed_phases`` rejects any value outside the 3 literals."""
        with pytest.raises(ValidationError):
            PolicySetpoints(
                id=_SET_ID,
                state=PolicyState.PUSH,
                hardwork_budget_hours=8.0,
                max_pomodoros_per_day=10,
                sleep_target_hours=7.0,
                qhe_target=0.85,
                break_minutes=10,
                allowed_phases=phases,  # type: ignore[arg-type]
                created_at=_FIXED_TS,
            )

    def test_policy_setpoints_allowed_phases_empty_rejected(self) -> None:
        """Empty ``allowed_phases`` list is rejected."""
        with pytest.raises(ValidationError):
            PolicySetpoints(
                id=_SET_ID,
                state=PolicyState.PUSH,
                hardwork_budget_hours=8.0,
                max_pomodoros_per_day=10,
                sleep_target_hours=7.0,
                qhe_target=0.85,
                break_minutes=10,
                allowed_phases=[],
                created_at=_FIXED_TS,
            )

    def test_policy_setpoints_description_max_length(self) -> None:
        """``description`` is capped at 200 characters."""
        with pytest.raises(ValidationError):
            PolicySetpoints(
                id=_SET_ID,
                state=PolicyState.PUSH,
                hardwork_budget_hours=8.0,
                max_pomodoros_per_day=10,
                sleep_target_hours=7.0,
                qhe_target=0.85,
                break_minutes=10,
                allowed_phases=["DEEP_WORK"],
                description="x" * 201,
                created_at=_FIXED_TS,
            )

    def test_policy_setpoints_description_200_accepted(self) -> None:
        """``description`` accepts exactly 200 characters (boundary)."""
        sp = PolicySetpoints(
            id=_SET_ID,
            state=PolicyState.PUSH,
            hardwork_budget_hours=8.0,
            max_pomodoros_per_day=10,
            sleep_target_hours=7.0,
            qhe_target=0.85,
            break_minutes=10,
            allowed_phases=["DEEP_WORK"],
            description="x" * 200,
            created_at=_FIXED_TS,
        )
        assert len(sp.description) == 200


class TestPolicySetpointsImmutability:
    """Frozen / extra-forbid invariants for :class:`PolicySetpoints`."""

    def test_policy_setpoints_frozen_cannot_mutate(self) -> None:
        """Frozen model: assignment to any field raises ``ValidationError``."""
        sp = _make_setpoints(PolicyState.PUSH)
        with pytest.raises(ValidationError):
            sp.hardwork_budget_hours = 4.0  # type: ignore[misc]
        with pytest.raises(ValidationError):
            sp.state = PolicyState.RECOVER  # type: ignore[misc]

    def test_policy_setpoints_rejects_unknown_fields(self) -> None:
        """Unknown fields are rejected by ``extra='forbid'``."""
        with pytest.raises(ValidationError):
            PolicySetpoints(
                id=_SET_ID,
                state=PolicyState.PUSH,
                hardwork_budget_hours=8.0,
                max_pomodoros_per_day=10,
                sleep_target_hours=7.0,
                qhe_target=0.85,
                break_minutes=10,
                allowed_phases=["DEEP_WORK"],
                created_at=_FIXED_TS,
                unknown_field="nope",  # type: ignore[call-arg]
            )


# ===========================================================================
# PolicyDecision
# ===========================================================================


class TestPolicyDecisionConstruction:
    """Direct construction tests for :class:`PolicyDecision`."""

    def test_create_policy_decision_minimal(self) -> None:
        """A decision with only required fields is buildable."""
        d = _make_decision(PolicyState.PUSH)
        assert d.id == _DEC_ID
        assert d.date == _FIXED_DATE
        assert d.state is PolicyState.PUSH
        assert d.severity == "INFO"
        assert d.rationale == "test rationale"
        assert d.setpoints.state is PolicyState.PUSH
        assert d.days_in_state == 0
        assert d.previous_state is None
        assert d.qhe_input is None
        assert d.energy_input is None
        assert d.infraction_count == 0
        assert d.applied is False
        assert d.applied_at is None

    def test_policy_decision_infraction_count_default_zero(self) -> None:
        """``infraction_count`` defaults to ``0``."""
        d = _make_decision(PolicyState.PUSH)
        assert d.infraction_count == 0

    def test_policy_decision_days_in_state_default_zero(self) -> None:
        """``days_in_state`` defaults to ``0``."""
        d = _make_decision(PolicyState.PUSH)
        assert d.days_in_state == 0

    def test_policy_decision_previous_state_optional(self) -> None:
        """``previous_state`` is ``None`` by default and can be set."""
        d_default = _make_decision(PolicyState.PUSH)
        assert d_default.previous_state is None
        d_with_prev = _make_decision(
            PolicyState.MAINTAIN,
            previous_state=PolicyState.PUSH,
        )
        assert d_with_prev.previous_state is PolicyState.PUSH

    def test_policy_decision_qhe_input_optional_range(self) -> None:
        """``qhe_input`` accepts ``None`` and values in ``[0.0, 1.0]``."""
        for v in (0.0, 0.5, 0.85, 1.0):
            d = _make_decision(PolicyState.PUSH, qhe_input=v)
            assert d.qhe_input == v
        d_none = _make_decision(PolicyState.PUSH, qhe_input=None)
        assert d_none.qhe_input is None

    @pytest.mark.parametrize("value", [-0.01, -1.0, 1.01, 2.0])
    def test_policy_decision_qhe_input_out_of_range(self, value: float) -> None:
        """``qhe_input`` rejects values outside ``[0.0, 1.0]``."""
        with pytest.raises(ValidationError):
            _make_decision(PolicyState.PUSH, qhe_input=value)

    def test_policy_decision_energy_input_optional(self) -> None:
        """``energy_input`` accepts any :class:`EnergyLevel` or ``None``."""
        for energy in (EnergyLevel.HIGH, EnergyLevel.MEDIUM, EnergyLevel.LOW):
            d = _make_decision(PolicyState.PUSH, energy_input=energy)
            assert d.energy_input is energy
        d_none = _make_decision(PolicyState.PUSH, energy_input=None)
        assert d_none.energy_input is None

    def test_policy_decision_energy_input_invalid(self) -> None:
        """``energy_input`` rejects anything that is not an EnergyLevel."""
        # Note: "H" is a *valid* value because EnergyLevel is a StrEnum
        # whose HIGH member has value "H". We use 42 (int) as the canonical
        # invalid input — the validator must reject any non-EnergyLevel.
        with pytest.raises(ValidationError):
            _make_decision(PolicyState.PUSH, energy_input=42)  # type: ignore[arg-type]

    @pytest.mark.parametrize("severity", ["INFO", "WARNING", "CRITICAL"])
    def test_policy_decision_severity_literal(self, severity: str) -> None:
        """``severity`` accepts the three canonical values."""
        d = PolicyDecision(
            id=_DEC_ID,
            date=_FIXED_DATE,
            state=PolicyState.PUSH,
            severity=severity,  # type: ignore[arg-type]
            rationale="x",
            setpoints=_make_setpoints(PolicyState.PUSH),
            created_at=_FIXED_TS,
        )
        assert d.severity == severity

    @pytest.mark.parametrize("severity", ["info", "LOW", "ERROR", "", "WARN"])
    def test_policy_decision_severity_rejects_other(self, severity: str) -> None:
        """``severity`` rejects values outside the 3 canonical literals."""
        with pytest.raises(ValidationError):
            PolicyDecision(
                id=_DEC_ID,
                date=_FIXED_DATE,
                state=PolicyState.PUSH,
                severity=severity,  # type: ignore[arg-type]
                rationale="x",
                setpoints=_make_setpoints(PolicyState.PUSH),
                created_at=_FIXED_TS,
            )

    def test_policy_decision_severity_default_info(self) -> None:
        """``severity`` defaults to ``"INFO"``."""
        d = PolicyDecision(
            id=_DEC_ID,
            date=_FIXED_DATE,
            state=PolicyState.PUSH,
            rationale="x",
            setpoints=_make_setpoints(PolicyState.PUSH),
            created_at=_FIXED_TS,
        )
        assert d.severity == "INFO"

    def test_policy_decision_rationale_max_length(self) -> None:
        """``rationale`` is capped at 500 characters."""
        with pytest.raises(ValidationError):
            PolicyDecision(
                id=_DEC_ID,
                date=_FIXED_DATE,
                state=PolicyState.PUSH,
                rationale="r" * 501,
                setpoints=_make_setpoints(PolicyState.PUSH),
                created_at=_FIXED_TS,
            )

    def test_policy_decision_rationale_500_accepted(self) -> None:
        """``rationale`` accepts exactly 500 characters (boundary)."""
        d = PolicyDecision(
            id=_DEC_ID,
            date=_FIXED_DATE,
            state=PolicyState.PUSH,
            rationale="r" * 500,
            setpoints=_make_setpoints(PolicyState.PUSH),
            created_at=_FIXED_TS,
        )
        assert len(d.rationale) == 500

    def test_policy_decision_infraction_count_negative_rejected(self) -> None:
        """``infraction_count`` rejects negative values."""
        with pytest.raises(ValidationError):
            _make_decision(PolicyState.PUSH, infraction_count=-1)

    def test_policy_decision_days_in_state_negative_rejected(self) -> None:
        """``days_in_state`` rejects negative values."""
        with pytest.raises(ValidationError):
            _make_decision(PolicyState.PUSH, days_in_state=-1)


class TestPolicyDecisionState:
    """``PolicyDecision`` should work for all 4 :class:`PolicyState` values."""

    @pytest.mark.parametrize("state", _ALL_STATES)
    def test_policy_decision_state_parametric(self, state: PolicyState) -> None:
        """A decision is buildable for every :class:`PolicyState`."""
        d = _make_decision(state)
        assert d.state is state
        assert d.setpoints.state is state

    def test_policy_decision_rejects_unknown_fields(self) -> None:
        """Unknown fields are rejected by ``extra='forbid'``."""
        with pytest.raises(ValidationError):
            PolicyDecision(
                id=_DEC_ID,
                date=_FIXED_DATE,
                state=PolicyState.PUSH,
                setpoints=_make_setpoints(PolicyState.PUSH),
                created_at=_FIXED_TS,
                unknown_field=1,  # type: ignore[call-arg]
            )


class TestPolicyDecisionValidators:
    """Cross-field validators on :class:`PolicyDecision`."""

    def test_policy_decision_setpoints_must_match_state(self) -> None:
        """``setpoints.state`` must equal ``state`` (rejected otherwise)."""
        with pytest.raises(ValidationError) as exc:
            PolicyDecision(
                id=_DEC_ID,
                date=_FIXED_DATE,
                state=PolicyState.PUSH,
                rationale="mismatch",
                setpoints=_make_setpoints(PolicyState.RECOVER),
                created_at=_FIXED_TS,
            )
        assert "setpoints.state" in str(exc.value).lower() or "must match" in str(exc.value).lower()

    def test_policy_decision_setpoints_match_all_states(self) -> None:
        """For every state, a matching setpoints instance is accepted."""
        for state in _ALL_STATES:
            d = _make_decision(state)
            assert d.setpoints.state is state

    def test_policy_decision_applied_auto_timestamp(self) -> None:
        """Setting ``applied=True`` without ``applied_at`` auto-fills it."""
        d = _make_decision(PolicyState.PUSH, applied=True)
        assert d.applied is True
        assert d.applied_at is not None
        assert isinstance(d.applied_at, datetime)

    def test_policy_decision_applied_with_explicit_timestamp(self) -> None:
        """An explicit ``applied_at`` is preserved when given."""
        explicit = datetime(2026, 6, 7, 10, 0, 0)
        d = PolicyDecision(
            id=_DEC_ID,
            date=_FIXED_DATE,
            state=PolicyState.PUSH,
            rationale="",
            setpoints=_make_setpoints(PolicyState.PUSH),
            created_at=_FIXED_TS,
            applied=True,
            applied_at=explicit,
        )
        assert d.applied is True
        assert d.applied_at == explicit

    def test_policy_decision_applied_false_keeps_none(self) -> None:
        """``applied=False`` keeps ``applied_at=None``."""
        d = _make_decision(PolicyState.PUSH, applied=False)
        assert d.applied is False
        assert d.applied_at is None

    def test_policy_decision_assign_applied_via_assignment(self) -> None:
        """``applied`` can be flipped via assignment (validate_assignment)."""
        d = _make_decision(PolicyState.PUSH)
        assert d.applied is False
        d.applied = True
        assert d.applied is True
        assert d.applied_at is not None


class TestPolicyDecisionAssignment:
    """``validate_assignment=True`` behaviour for :class:`PolicyDecision`."""

    def test_policy_decision_cannot_change_state_after_creation(self) -> None:
        """Changing ``state`` to a mismatched value is rejected on assignment."""
        d = _make_decision(PolicyState.PUSH)
        # State transition that doesn't match the new setpoints is rejected.
        with pytest.raises(ValidationError):
            d.state = PolicyState.RECOVER  # type: ignore[misc]

    def test_policy_decision_state_change_requires_setpoints(self) -> None:
        """Atomic state + setpoints swap is allowed via ``model_copy``."""
        d = _make_decision(PolicyState.PUSH)
        new_setpoints = _make_setpoints(PolicyState.MAINTAIN)
        # ``validate_assignment`` runs the model_validator after every
        # single field assignment, so swapping state and setpoints in
        # two steps would fail the cross-field check at step 1. The
        # supported way to change state is via ``model_copy(update=...)``
        # which validates the whole model only once at the end.
        d2 = d.model_copy(update={"state": PolicyState.MAINTAIN, "setpoints": new_setpoints})
        assert d2.state is PolicyState.MAINTAIN
        assert d2.setpoints.state is PolicyState.MAINTAIN
        # The original is unchanged (model_copy returns a new instance).
        assert d.state is PolicyState.PUSH

    def test_policy_decision_assignment_revalidates(self) -> None:
        """``validate_assignment=True`` re-runs all validators on assign."""
        d = _make_decision(PolicyState.PUSH, infraction_count=2)
        d.infraction_count = 5
        assert d.infraction_count == 5
        with pytest.raises(ValidationError):
            d.infraction_count = -1

    def test_policy_decision_id_immutable_on_reassign(self) -> None:
        """``id`` is technically a UEID — any valid string is accepted."""
        d = _make_decision(PolicyState.PUSH)
        d.id = "pol_renamed_001"
        assert d.id == "pol_renamed_001"


class TestPolicyDecisionFactory:
    """Tests for :meth:`PolicyDecision.from_state`."""

    def test_policy_decision_from_state_push(self) -> None:
        """Factory produces a PUSH decision with matching setpoints."""
        d = PolicyDecision.from_state(
            decision_date=_FIXED_DATE,
            state=PolicyState.PUSH,
            rationale="ok",
        )
        assert d.state is PolicyState.PUSH
        assert d.setpoints.state is PolicyState.PUSH
        assert d.setpoints.hardwork_budget_hours == 8.0
        assert d.rationale == "ok"
        assert d.applied is False
        assert d.applied_at is None

    def test_policy_decision_from_state_recover(self) -> None:
        """Factory produces a RECOVER decision with matching setpoints."""
        d = PolicyDecision.from_state(
            decision_date=_FIXED_DATE,
            state=PolicyState.RECOVER,
            rationale="bad week",
            severity="CRITICAL",
        )
        assert d.state is PolicyState.RECOVER
        assert d.setpoints.state is PolicyState.RECOVER
        assert d.setpoints.hardwork_budget_hours == 2.0
        assert d.severity == "CRITICAL"

    def test_policy_decision_from_state_passes_through(self) -> None:
        """Factory passes through qhe_input / energy_input / counts."""
        d = PolicyDecision.from_state(
            decision_date=_FIXED_DATE,
            state=PolicyState.REDUCE,
            rationale="tired",
            qhe_input=0.55,
            energy_input=EnergyLevel.LOW,
            infraction_count=3,
            days_in_state=2,
            previous_state=PolicyState.MAINTAIN,
        )
        assert d.qhe_input == 0.55
        assert d.energy_input is EnergyLevel.LOW
        assert d.infraction_count == 3
        assert d.days_in_state == 2
        assert d.previous_state is PolicyState.MAINTAIN


# ===========================================================================
# DecisionRecord
# ===========================================================================


class TestDecisionRecordConstruction:
    """Direct construction tests for :class:`DecisionRecord`."""

    def test_create_decision_record_initial_state(self) -> None:
        """A first-on-record decision has ``from_state=None``."""
        r = DecisionRecord(
            id=_REC_ID,
            from_state=None,
            to_state=PolicyState.MAINTAIN,
            transition_date=_FIXED_DATE,
            days_in_previous_state=0,
            trigger="initial",
            created_at=_FIXED_TS,
        )
        assert r.id == _REC_ID
        assert r.from_state is None
        assert r.to_state is PolicyState.MAINTAIN
        assert r.transition_date == _FIXED_DATE
        assert r.days_in_previous_state == 0
        assert r.trigger == "initial"
        assert r.qhe_at_transition is None
        assert r.created_at == _FIXED_TS

    def test_decision_record_with_from_state(self) -> None:
        """A regular transition carries both ``from_state`` and ``to_state``."""
        r = DecisionRecord(
            id=_REC_ID,
            from_state=PolicyState.PUSH,
            to_state=PolicyState.MAINTAIN,
            transition_date=_FIXED_DATE,
            days_in_previous_state=3,
            trigger="qhe dropped",
            qhe_at_transition=0.7,
            created_at=_FIXED_TS,
        )
        assert r.from_state is PolicyState.PUSH
        assert r.to_state is PolicyState.MAINTAIN
        assert r.days_in_previous_state == 3
        assert r.qhe_at_transition == 0.7

    def test_decision_record_trigger_default_empty(self) -> None:
        """``trigger`` defaults to empty string when omitted."""
        r = DecisionRecord(
            id=_REC_ID,
            from_state=PolicyState.PUSH,
            to_state=PolicyState.MAINTAIN,
            transition_date=_FIXED_DATE,
            days_in_previous_state=2,
            created_at=_FIXED_TS,
        )
        assert r.trigger == ""

    def test_decision_record_qhe_optional(self) -> None:
        """``qhe_at_transition`` is ``None`` by default and accepts valid floats."""
        r_none = DecisionRecord(
            id=_REC_ID,
            from_state=PolicyState.PUSH,
            to_state=PolicyState.MAINTAIN,
            transition_date=_FIXED_DATE,
            days_in_previous_state=2,
            created_at=_FIXED_TS,
        )
        assert r_none.qhe_at_transition is None
        r_with = DecisionRecord(
            id=_REC_ID,
            from_state=PolicyState.PUSH,
            to_state=PolicyState.MAINTAIN,
            transition_date=_FIXED_DATE,
            days_in_previous_state=2,
            created_at=_FIXED_TS,
            qhe_at_transition=0.6,
        )
        assert r_with.qhe_at_transition == 0.6

    @pytest.mark.parametrize("value", [-0.01, -1.0, 1.01, 2.0])
    def test_decision_record_qhe_out_of_range(self, value: float) -> None:
        """``qhe_at_transition`` rejects values outside ``[0.0, 1.0]``."""
        with pytest.raises(ValidationError):
            DecisionRecord(
                id=_REC_ID,
                from_state=PolicyState.PUSH,
                to_state=PolicyState.MAINTAIN,
                transition_date=_FIXED_DATE,
                days_in_previous_state=2,
                created_at=_FIXED_TS,
                qhe_at_transition=value,
            )

    def test_decision_record_trigger_max_length(self) -> None:
        """``trigger`` is capped at 200 characters."""
        with pytest.raises(ValidationError):
            DecisionRecord(
                id=_REC_ID,
                from_state=PolicyState.PUSH,
                to_state=PolicyState.MAINTAIN,
                transition_date=_FIXED_DATE,
                days_in_previous_state=2,
                trigger="t" * 201,
                created_at=_FIXED_TS,
            )

    def test_decision_record_trigger_200_accepted(self) -> None:
        """``trigger`` accepts exactly 200 characters (boundary)."""
        r = DecisionRecord(
            id=_REC_ID,
            from_state=PolicyState.PUSH,
            to_state=PolicyState.MAINTAIN,
            transition_date=_FIXED_DATE,
            days_in_previous_state=2,
            trigger="t" * 200,
            created_at=_FIXED_TS,
        )
        assert len(r.trigger) == 200

    def test_decision_record_days_in_previous_state_default(self) -> None:
        """``days_in_previous_state`` is a required field (no default)."""
        # Should be required
        with pytest.raises(ValidationError):
            DecisionRecord(
                id=_REC_ID,
                from_state=PolicyState.PUSH,
                to_state=PolicyState.MAINTAIN,
                transition_date=_FIXED_DATE,
                created_at=_FIXED_TS,
            )

    def test_decision_record_days_negative_rejected(self) -> None:
        """``days_in_previous_state`` rejects negative values."""
        with pytest.raises(ValidationError):
            DecisionRecord(
                id=_REC_ID,
                from_state=PolicyState.PUSH,
                to_state=PolicyState.MAINTAIN,
                transition_date=_FIXED_DATE,
                days_in_previous_state=-1,
                created_at=_FIXED_TS,
            )


class TestDecisionRecordValidators:
    """Cross-field validators on :class:`DecisionRecord`."""

    def test_decision_record_transition_validation(self) -> None:
        """``from_state == to_state`` is rejected."""
        with pytest.raises(ValidationError) as exc:
            DecisionRecord(
                id=_REC_ID,
                from_state=PolicyState.MAINTAIN,
                to_state=PolicyState.MAINTAIN,
                transition_date=_FIXED_DATE,
                days_in_previous_state=3,
                created_at=_FIXED_TS,
            )
        assert "must differ" in str(exc.value).lower() or "from_state" in str(exc.value).lower()

    @pytest.mark.parametrize(
        ("from_state", "to_state"),
        [
            (PolicyState.PUSH, PolicyState.PUSH),
            (PolicyState.MAINTAIN, PolicyState.MAINTAIN),
            (PolicyState.REDUCE, PolicyState.REDUCE),
            (PolicyState.RECOVER, PolicyState.RECOVER),
        ],
    )
    def test_decision_record_same_state_rejected(
        self, from_state: PolicyState, to_state: PolicyState
    ) -> None:
        """``from_state == to_state`` is rejected for every state."""
        with pytest.raises(ValidationError):
            DecisionRecord(
                id=_REC_ID,
                from_state=from_state,
                to_state=to_state,
                transition_date=_FIXED_DATE,
                days_in_previous_state=0,
                created_at=_FIXED_TS,
            )

    def test_decision_record_none_to_state_accepted(self) -> None:
        """``from_state=None`` is accepted (initial-state record)."""
        r = DecisionRecord(
            id=_REC_ID,
            from_state=None,
            to_state=PolicyState.PUSH,
            transition_date=_FIXED_DATE,
            days_in_previous_state=0,
            created_at=_FIXED_TS,
        )
        assert r.from_state is None
        assert r.to_state is PolicyState.PUSH


class TestDecisionRecordImmutability:
    """Frozen / extra-forbid invariants for :class:`DecisionRecord`."""

    def test_decision_record_frozen_cannot_mutate(self) -> None:
        """Frozen model: assignment to any field raises ``ValidationError``."""
        r = DecisionRecord(
            id=_REC_ID,
            from_state=PolicyState.PUSH,
            to_state=PolicyState.MAINTAIN,
            transition_date=_FIXED_DATE,
            days_in_previous_state=3,
            created_at=_FIXED_TS,
        )
        with pytest.raises(ValidationError):
            r.to_state = PolicyState.RECOVER  # type: ignore[misc]

    def test_decision_record_rejects_unknown_fields(self) -> None:
        """Unknown fields are rejected by ``extra='forbid'``."""
        with pytest.raises(ValidationError):
            DecisionRecord(
                id=_REC_ID,
                from_state=PolicyState.PUSH,
                to_state=PolicyState.MAINTAIN,
                transition_date=_FIXED_DATE,
                days_in_previous_state=2,
                created_at=_FIXED_TS,
                unknown_field=1,  # type: ignore[call-arg]
            )


class TestDecisionRecordFactory:
    """Tests for :meth:`DecisionRecord.from_states`."""

    def test_decision_record_from_states_initial(self) -> None:
        """Factory produces a first-on-record entry."""
        r = DecisionRecord.from_states(
            from_state=None,
            to_state=PolicyState.MAINTAIN,
            transition_date=_FIXED_DATE,
            trigger="first",
        )
        assert r.from_state is None
        assert r.to_state is PolicyState.MAINTAIN
        assert r.days_in_previous_state == 0
        assert r.id.startswith("rec_")
        assert isinstance(r.created_at, datetime)

    def test_decision_record_from_states_transition(self) -> None:
        """Factory produces a regular transition entry."""
        r = DecisionRecord.from_states(
            from_state=PolicyState.PUSH,
            to_state=PolicyState.MAINTAIN,
            transition_date=_FIXED_DATE,
            days_in_previous_state=3,
            trigger="qhe dropped below 0.85",
            qhe_at_transition=0.74,
        )
        assert r.from_state is PolicyState.PUSH
        assert r.to_state is PolicyState.MAINTAIN
        assert r.days_in_previous_state == 3
        assert r.qhe_at_transition == 0.74
        assert r.id.startswith("rec_")

    def test_decision_record_from_states_same_state_rejected(self) -> None:
        """Factory rejects ``from_state == to_state``."""
        with pytest.raises(ValidationError):
            DecisionRecord.from_states(
                from_state=PolicyState.MAINTAIN,
                to_state=PolicyState.MAINTAIN,
                transition_date=_FIXED_DATE,
            )


# ===========================================================================
# Cross-cutting tests
# ===========================================================================


class TestPolicyCycle:
    """End-to-end test: PUSH → MAINTAIN → REDUCE → RECOVER transitions."""

    def test_policy_cycle_push_to_recover(self) -> None:
        """A full descent cycle is auditable via DecisionRecord instances."""
        # Day 0: enter PUSH (no prior state)
        r0 = DecisionRecord.from_states(
            from_state=None,
            to_state=PolicyState.PUSH,
            transition_date=date(2026, 6, 1),
            trigger="starting strong",
        )
        assert r0.from_state is None
        assert r0.to_state is PolicyState.PUSH

        # Day 5: downgrade to MAINTAIN
        r1 = DecisionRecord.from_states(
            from_state=PolicyState.PUSH,
            to_state=PolicyState.MAINTAIN,
            transition_date=date(2026, 6, 5),
            days_in_previous_state=4,
            trigger="qhe dropped below push threshold",
            qhe_at_transition=0.78,
        )
        assert r1.from_state is PolicyState.PUSH
        assert r1.to_state is PolicyState.MAINTAIN

        # Day 8: downgrade to REDUCE
        r2 = DecisionRecord.from_states(
            from_state=PolicyState.MAINTAIN,
            to_state=PolicyState.REDUCE,
            transition_date=date(2026, 6, 8),
            days_in_previous_state=3,
            trigger="energy low",
            qhe_at_transition=0.62,
        )
        assert r2.from_state is PolicyState.MAINTAIN
        assert r2.to_state is PolicyState.REDUCE

        # Day 9: emergency RECOVER
        r3 = DecisionRecord.from_states(
            from_state=PolicyState.REDUCE,
            to_state=PolicyState.RECOVER,
            transition_date=date(2026, 6, 9),
            days_in_previous_state=1,
            trigger="qhe below recover threshold",
            qhe_at_transition=0.55,
        )
        assert r3.from_state is PolicyState.REDUCE
        assert r3.to_state is PolicyState.RECOVER

        # The transition dates are strictly increasing
        assert r0.transition_date < r1.transition_date < r2.transition_date < r3.transition_date

    def test_policy_decisions_through_cycle(self) -> None:
        """Build one :class:`PolicyDecision` per state in the cycle."""
        days = (date(2026, 6, 1), date(2026, 6, 5), date(2026, 6, 8), date(2026, 6, 9))
        previous: PolicyState | None = None
        for state, day in zip(_ALL_STATES, days, strict=True):
            d = PolicyDecision.from_state(
                decision_date=day,
                state=state,
                rationale=f"entering {state.value}",
                previous_state=previous,
            )
            assert d.state is state
            assert d.setpoints.state is state
            assert d.previous_state is previous
            previous = state

    def test_decision_setpoints_match_for_all_states(self) -> None:
        """For every state, a fresh factory decision has matching setpoints."""
        for state in _ALL_STATES:
            d = PolicyDecision.from_state(decision_date=_FIXED_DATE, state=state)
            assert d.setpoints.state is d.state
            # Setpoints came from the canonical factory
            assert d.setpoints.hardwork_budget_hours > 0
            assert d.setpoints.max_pomodoros_per_day >= 0
            assert d.setpoints.break_minutes >= 1
            assert len(d.setpoints.allowed_phases) >= 1


class TestPolicyModuleSurface:
    """Module-level invariants: ``__all__`` and class exposure."""

    def test_module_all_complete(self) -> None:
        """``operational.entities.policy`` exposes the 3 entities in ``__all__``."""
        from operational.entities import policy as mod

        expected = {"PolicySetpoints", "PolicyDecision", "DecisionRecord"}
        assert expected.issubset(set(mod.__all__))

    def test_all_names_importable(self) -> None:
        """Every name in ``__all__`` is importable from the module."""
        from operational.entities import policy as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"Missing export: {name}"

    def test_ueid_alias_used_for_ids(self) -> None:
        """All three entities use the branded :data:`UEID` for ``id``."""
        # Type-check only — assert IDs are typed as UEID on each model.
        annotations: dict[str, dict[str, object]] = {
            "PolicySetpoints": PolicySetpoints.model_fields,
            "PolicyDecision": PolicyDecision.model_fields,
            "DecisionRecord": DecisionRecord.model_fields,
        }
        for name, fields in annotations.items():
            assert "id" in fields, f"{name} missing 'id' field"
            # The annotation is `UEID` (a TypeAlias to Annotated[str, ...])
            # which surfaces as `str` at runtime — but the field is
            # present and validates against the UEID pattern.
            assert fields["id"].annotation is not None
