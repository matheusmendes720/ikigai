"""Unit tests for :mod:`operational.core.time_validator`.

Coverage (~50 tests):

* :func:`validar_horario_acordar` — match-case branches (3, 4, 5, 6, 7,
  8-11), raises (0-2 with TIME_001, 12+ with TIME_002).
* :class:`WakeUpValidation` — dataclass shape, frozen, slots, status
  field is one of the 5 :data:`WakeUpStatus` literals.
* :func:`is_optimal_wake_hour` — quick check, edge cases.
* Error-code propagation — the raised :class:`TimeValidationError`
  carries the correct ``code`` (ERR_TIME_001/002) and severity (CRITICAL).
* Parametric tests for every hour in 0-23.
* TypeError for non-int input (bool rejected explicitly).
* ValueError for out-of-range hours (the function pre-validates).
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from operational.core.time_validator import (
    WakeUpStatus,
    WakeUpValidation,
    is_optimal_wake_hour,
    validar_horario_acordar,
)
from operational.exceptions import (
    PAVErrorCode,
    ProductivitySystemError,
    Severity,
    TimeValidationError,
)


# =========================================================================
# Module surface
# =========================================================================


class TestModuleSurface:
    """The module exports the expected public symbols."""

    def test_all_exports_present(self) -> None:
        """__all__ lists the canonical public surface."""
        from operational.core import time_validator

        expected = {
            "WakeUpStatus",
            "WakeUpValidation",
            "is_optimal_wake_hour",
            "validar_horario_acordar",
        }
        assert set(time_validator.__all__) == expected

    def test_wake_up_status_is_literal(self) -> None:
        """WakeUpStatus is a typing.Literal with 5 members."""
        # Verify the literal members via runtime
        valid: WakeUpStatus = "OPTIMAL"
        assert valid in {
            "OPTIMAL",
            "LEVE_DESVIO",
            "DESVIO_MODERADO",
            "CRITICO",
            "IMPOSSIVEL",
        }


# =========================================================================
# WakeUpValidation dataclass
# =========================================================================


class TestWakeUpValidationDataclass:
    """The frozen, slotted dataclass for validation results."""

    def test_is_dataclass(self) -> None:
        """WakeUpValidation is a dataclass."""
        assert is_dataclass(WakeUpValidation)

    def test_construct_minimal(self) -> None:
        """Minimal construction works."""
        v = WakeUpValidation(
            status="OPTIMAL",
            message="3h is gold",
            acao="Continue",
            desvio_minutos=0,
            is_valid=True,
        )
        assert v.status == "OPTIMAL"
        assert v.message == "3h is gold"
        assert v.acao == "Continue"
        assert v.desvio_minutos == 0
        assert v.is_valid is True

    def test_is_frozen(self) -> None:
        """Assignment after construction raises FrozenInstanceError."""
        v = WakeUpValidation(
            status="OPTIMAL",
            message="x",
            acao="x",
            desvio_minutos=0,
            is_valid=True,
        )
        with pytest.raises(FrozenInstanceError):
            v.status = "CRITICO"  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        """Dataclass uses __slots__ — no __dict__, rejects new attrs."""
        v = WakeUpValidation(
            status="OPTIMAL",
            message="x",
            acao="x",
            desvio_minutos=0,
            is_valid=True,
        )
        with pytest.raises(AttributeError):
            v.invalid_attr = "boom"  # type: ignore[attr-defined]

    def test_equality(self) -> None:
        """Two validations with same fields are equal."""
        kwargs = {
            "status": "OPTIMAL",
            "message": "x",
            "acao": "y",
            "desvio_minutos": 0,
            "is_valid": True,
        }
        assert WakeUpValidation(**kwargs) == WakeUpValidation(**kwargs)

    def test_inequality_on_difference(self) -> None:
        """Validations differing in any field are unequal."""
        a = WakeUpValidation(
            status="OPTIMAL", message="x", acao="y",
            desvio_minutos=0, is_valid=True,
        )
        b = WakeUpValidation(
            status="LEVE_DESVIO", message="x", acao="y",
            desvio_minutos=60, is_valid=True,
        )
        assert a != b

    def test_has_5_typed_fields(self) -> None:
        """The dataclass declares exactly 5 fields."""
        from dataclasses import fields

        field_names = {f.name for f in fields(WakeUpValidation)}
        assert field_names == {"status", "message", "acao", "desvio_minutos", "is_valid"}


# =========================================================================
# validar_horario_acordar — OPTIMAL branch
# =========================================================================


class TestValidarOptimal:
    """Hours 3, 4, 5 → OPTIMAL (PAV §4)."""

    @pytest.mark.parametrize("hour", [3, 4, 5])
    def test_optimal(self, hour: int) -> None:
        """3-5am returns OPTIMAL with deviation 0."""
        v = validar_horario_acordar(hour)
        assert v.status == "OPTIMAL"
        assert v.desvio_minutos == 0
        assert v.is_valid is True
        assert v.acao == "Continuar rotina normal"
        assert str(hour) in v.message

    def test_3am_optimal_message_mentions_3am(self) -> None:
        """3am message includes the hour and the gold band."""
        v = validar_horario_acordar(3)
        assert "3h" in v.message
        assert "3-5am" in v.message

    def test_5am_optimal_message_mentions_5am(self) -> None:
        """5am message includes the hour."""
        v = validar_horario_acordar(5)
        assert "5h" in v.message


# =========================================================================
# validar_horario_acordar — LEVE_DESVIO branch
# =========================================================================


class TestValidarLeve:
    """Hour 6 → LEVE_DESVIO (PAV §4)."""

    def test_6am_leve(self) -> None:
        """6am returns LEVE_DESVIO with 60-min deviation."""
        v = validar_horario_acordar(6)
        assert v.status == "LEVE_DESVIO"
        assert v.desvio_minutos == 60
        assert v.is_valid is True
        assert "pomar" not in v.acao  # pomodoros come at 7am
        assert "pausa" in v.acao  # pausa extra at 6am


# =========================================================================
# validar_horario_acordar — DESVIO_MODERADO branch
# =========================================================================


class TestValidarModerado:
    """Hour 7 → DESVIO_MODERADO (PAV §4)."""

    def test_7am_moderado(self) -> None:
        """7am returns DESVIO_MODERADO with 120-min deviation."""
        v = validar_horario_acordar(7)
        assert v.status == "DESVIO_MODERADO"
        assert v.desvio_minutos == 120
        assert v.is_valid is True
        assert "pomodoros" in v.acao.lower() or "pomodor" in v.acao.lower()
        assert "1 round" in v.acao.lower() or "1 round" in v.acao


# =========================================================================
# validar_horario_acordar — CRITICO branch
# =========================================================================


class TestValidarCritico:
    """Hours 8-11 → CRITICO (PAV §4)."""

    @pytest.mark.parametrize("hour", [8, 9, 10, 11])
    def test_8_to_11_critico(self, hour: int) -> None:
        """8-11am returns CRITICO with (h-5)*60 deviation."""
        v = validar_horario_acordar(hour)
        assert v.status == "CRITICO"
        assert v.desvio_minutos == (hour - 5) * 60
        assert v.is_valid is True
        assert "Reiniciar" in v.acao

    @pytest.mark.parametrize("hour", [8, 9, 10, 11])
    def test_critico_deviation_formula(self, hour: int) -> None:
        """Deviation = (hour - 5) * 60 minutes exactly."""
        v = validar_horario_acordar(hour)
        assert v.desvio_minutos == (hour - 5) * 60

    def test_8am_specific(self) -> None:
        """8am specifically: 3 hours past, 180 minutes."""
        v = validar_horario_acordar(8)
        assert v.status == "CRITICO"
        assert v.desvio_minutos == 180
        assert "3 horas" in v.message

    def test_11am_specific(self) -> None:
        """11am: 6 hours past, 360 minutes."""
        v = validar_horario_acordar(11)
        assert v.status == "CRITICO"
        assert v.desvio_minutos == 360
        assert "6 horas" in v.message


# =========================================================================
# validar_horario_acordar — IMPOSSIVEL raises (TIME_001)
# =========================================================================


class TestValidarImpossivel001:
    """Hours 0-2 → TimeValidationError with ERR_TIME_001 (PAV §6)."""

    @pytest.mark.parametrize("hour", [0, 1, 2])
    def test_0_to_2_raises(self, hour: int) -> None:
        """0-2am raises TimeValidationError with TIME_001."""
        with pytest.raises(TimeValidationError) as exc_info:
            validar_horario_acordar(hour)
        assert exc_info.value.code == PAVErrorCode.TIME_001.value
        assert exc_info.value.code == "ERR_TIME_001"

    @pytest.mark.parametrize("hour", [0, 1, 2])
    def test_0_to_2_severity_critical(self, hour: int) -> None:
        """TIME_001 severity is CRITICAL."""
        with pytest.raises(TimeValidationError) as exc_info:
            validar_horario_acordar(hour)
        assert exc_info.value.severity == Severity.CRITICAL

    @pytest.mark.parametrize("hour", [0, 1, 2])
    def test_0_to_2_is_productivity_system_error(self, hour: int) -> None:
        """Exception is catchable as ProductivitySystemError base."""
        with pytest.raises(ProductivitySystemError):
            validar_horario_acordar(hour)

    @pytest.mark.parametrize("hour", [0, 1, 2])
    def test_0_to_2_message_contains_hour(self, hour: int) -> None:
        """Error message mentions the offending hour."""
        with pytest.raises(TimeValidationError) as exc_info:
            validar_horario_acordar(hour)
        assert f"hora_acordou={hour}" in exc_info.value.args[0]


# =========================================================================
# validar_horario_acordar — IMPOSSIVEL raises (TIME_002)
# =========================================================================


class TestValidarImpossivel002:
    """Hours 12+ → TimeValidationError with ERR_TIME_002 (PAV §6)."""

    @pytest.mark.parametrize("hour", [12, 13, 15, 18, 20, 23])
    def test_12_plus_raises(self, hour: int) -> None:
        """12-23 raises TimeValidationError with TIME_002."""
        with pytest.raises(TimeValidationError) as exc_info:
            validar_horario_acordar(hour)
        assert exc_info.value.code == PAVErrorCode.TIME_002.value
        assert exc_info.value.code == "ERR_TIME_002"

    @pytest.mark.parametrize("hour", [12, 13, 15, 18, 20, 23])
    def test_12_plus_severity_critical(self, hour: int) -> None:
        """TIME_002 severity is CRITICAL."""
        with pytest.raises(TimeValidationError) as exc_info:
            validar_horario_acordar(hour)
        assert exc_info.value.severity == Severity.CRITICAL

    def test_18_specific(self) -> None:
        """18 (the 6pm case) raises TIME_002."""
        with pytest.raises(TimeValidationError) as exc_info:
            validar_horario_acordar(18)
        assert exc_info.value.code == "ERR_TIME_002"
        assert "hora_acordou=18" in exc_info.value.args[0]

    def test_23_specific(self) -> None:
        """23 (the 11pm case) raises TIME_002."""
        with pytest.raises(TimeValidationError) as exc_info:
            validar_horario_acordar(23)
        assert exc_info.value.code == "ERR_TIME_002"


# =========================================================================
# validar_horario_acordar — type validation
# =========================================================================


class TestValidarTypeErrors:
    """Type-validation: non-int input raises TypeError."""

    @pytest.mark.parametrize("bad_input", [3.5, "3", None, [3], {"h": 3}, 3.0])
    def test_non_int_raises_type_error(self, bad_input: object) -> None:
        """Non-int input raises TypeError."""
        with pytest.raises(TypeError):
            validar_horario_acordar(bad_input)  # type: ignore[arg-type]

    def test_bool_raises_type_error(self) -> None:
        """Bool is rejected explicitly (PEP 285)."""
        with pytest.raises(TypeError, match="bool"):
            validar_horario_acordar(True)  # type: ignore[arg-type]

    def test_bool_false_raises_type_error(self) -> None:
        """False is also a bool — rejected."""
        with pytest.raises(TypeError, match="bool"):
            validar_horario_acordar(False)  # type: ignore[arg-type]

    @pytest.mark.parametrize("hour", [-1, -10, 24, 25, 100])
    def test_out_of_range_int_raises_value_error(self, hour: int) -> None:
        """Out-of-range int raises ValueError (not a PAV error)."""
        with pytest.raises(ValueError, match=r"\[0, 23\]"):
            validar_horario_acordar(hour)


# =========================================================================
# Full 24-hour parametric coverage
# =========================================================================


EXPECTED_BY_HOUR: dict[int, str] = {
    0: "ERR_TIME_001",
    1: "ERR_TIME_001",
    2: "ERR_TIME_001",
    3: "OPTIMAL",
    4: "OPTIMAL",
    5: "OPTIMAL",
    6: "LEVE_DESVIO",
    7: "DESVIO_MODERADO",
    8: "CRITICO",
    9: "CRITICO",
    10: "CRITICO",
    11: "CRITICO",
    12: "ERR_TIME_002",
    13: "ERR_TIME_002",
    14: "ERR_TIME_002",
    15: "ERR_TIME_002",
    16: "ERR_TIME_002",
    17: "ERR_TIME_002",
    18: "ERR_TIME_002",
    19: "ERR_TIME_002",
    20: "ERR_TIME_002",
    21: "ERR_TIME_002",
    22: "ERR_TIME_002",
    23: "ERR_TIME_002",
}
"""Expected status or PAV error code for every hour 0-23."""


class TestValidarFullDayParametric:
    """Parametric verification of every hour 0-23."""

    @pytest.mark.parametrize("hour", list(range(24)))
    def test_hour_status_or_error(self, hour: int) -> None:
        """Every hour 0-23 yields the expected status or PAV error code."""
        expected = EXPECTED_BY_HOUR[hour]
        if expected.startswith("ERR_"):
            with pytest.raises(TimeValidationError) as exc_info:
                validar_horario_acordar(hour)
            assert exc_info.value.code == expected
        else:
            v = validar_horario_acordar(hour)
            assert v.status == expected


# =========================================================================
# is_optimal_wake_hour
# =========================================================================


class TestIsOptimalWakeHour:
    """The quick 3-5am boolean check."""

    @pytest.mark.parametrize("hour", [3, 4, 5])
    def test_optimal_true(self, hour: int) -> None:
        """3, 4, 5am are optimal."""
        assert is_optimal_wake_hour(hour) is True

    @pytest.mark.parametrize("hour", [0, 1, 2, 6, 7, 8, 9, 10, 11, 12, 18, 23])
    def test_non_optimal_false(self, hour: int) -> None:
        """Any other hour is not optimal."""
        assert is_optimal_wake_hour(hour) is False

    def test_does_not_raise(self) -> None:
        """The check never raises — it returns False for any non-3-5."""
        for hour in range(24):
            # should not raise
            is_optimal_wake_hour(hour)

    def test_consistent_with_validar(self) -> None:
        """is_optimal_wake_hour agrees with validar_horario_acordar for 3-5."""
        for hour in [3, 4, 5]:
            v = validar_horario_acordar(hour)
            assert is_optimal_wake_hour(hour) is True
            assert v.status == "OPTIMAL"


# =========================================================================
# PAV error code propagation
# =========================================================================


class TestPAVErrorCodePropagation:
    """The raised TimeValidationError carries the PAV §6 code + severity."""

    def test_time_001_propagated(self) -> None:
        """TIME_001 is propagated to the exception's .code attribute."""
        with pytest.raises(TimeValidationError) as exc_info:
            validar_horario_acordar(0)
        assert exc_info.value.code == "ERR_TIME_001"
        assert exc_info.value.severity == Severity.CRITICAL

    def test_time_002_propagated(self) -> None:
        """TIME_002 is propagated to the exception's .code attribute."""
        with pytest.raises(TimeValidationError) as exc_info:
            validar_horario_acordar(15)
        assert exc_info.value.code == "ERR_TIME_002"
        assert exc_info.value.severity == Severity.CRITICAL

    def test_message_preserved(self) -> None:
        """The user-supplied-style message is preserved."""
        with pytest.raises(TimeValidationError) as exc_info:
            validar_horario_acordar(0)
        assert "hora_acordou=0" in exc_info.value.args[0]
        assert "<3" in exc_info.value.args[0]

    def test_exception_is_time_validation_error(self) -> None:
        """The raised exception is exactly TimeValidationError (not subclass)."""
        with pytest.raises(TimeValidationError) as exc_info:
            validar_horario_acordar(2)
        assert type(exc_info.value) is TimeValidationError

    def test_caught_as_productivity_system_error(self) -> None:
        """Liskov: catchable as ProductivitySystemError."""
        with pytest.raises(ProductivitySystemError):
            validar_horario_acordar(0)
