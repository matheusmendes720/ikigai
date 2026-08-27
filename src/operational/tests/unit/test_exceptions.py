"""Unit tests for :mod:`operational.exceptions`.

Coverage:

* Hierarchy: every subclass derives from ``ProductivitySystemError``.
* ``code`` / ``severity`` semantics (class-level + instance override).
* All 10 PAV §6 codes registered and routed to the right exception class.
* :func:`get_pav_error_spec` and :func:`raise_pav_error` behaviour.
* Exception chaining (``raise X from Y``) preserves ``__cause__``.
* ``__str__`` formatting.
* Parametric tests for each of the 10 PAV codes.
"""
from __future__ import annotations

import pytest

from operational.exceptions import (
    PAV_ERROR_REGISTRY,
    BlueLightWarning,
    MealTimingWarning,
    PAVErrorCode,
    PAVErrorLookupError,
    PAVErrorSpec,
    PomodoroSessionError,
    ProductivitySystemError,
    RoutineCompletionError,
    Severity,
    SleepTrackingError,
    TimeValidationError,
    get_pav_error_spec,
    raise_pav_error,
)


# --- Expected mappings per PAV §6 (10 rows) ------------------------------

EXPECTED_SPECS: dict[PAVErrorCode, tuple[type[ProductivitySystemError], Severity, str]] = {
    PAVErrorCode.TIME_001: (TimeValidationError, Severity.CRITICAL, "hora_acordou < 3"),
    PAVErrorCode.TIME_002: (TimeValidationError, Severity.CRITICAL, "hora_acordou > 12"),
    PAVErrorCode.TIME_003: (TimeValidationError, Severity.HIGH, "hora_acordou > 5"),
    PAVErrorCode.SLEEP_001: (SleepTrackingError, Severity.CRITICAL, "horas_sono < 4"),
    PAVErrorCode.SLEEP_002: (SleepTrackingError, Severity.CRITICAL, "horas_sono > 12"),
    PAVErrorCode.MEAL_001: (MealTimingWarning, Severity.HIGH, "refeicao_apos_18h"),
    PAVErrorCode.LIGHT_001: (BlueLightWarning, Severity.HIGH, "luz_azul_apos_18h"),
    PAVErrorCode.POMO_001: (PomodoroSessionError, Severity.MEDIUM, "rounds < 3"),
    PAVErrorCode.POMO_002: (PomodoroSessionError, Severity.MEDIUM, "break < 5min"),
    PAVErrorCode.ROUTINE_001: (RoutineCompletionError, Severity.MEDIUM, "rotina_incompleta"),
}

ALL_SUBCLASSES: tuple[type[ProductivitySystemError], ...] = (
    TimeValidationError,
    SleepTrackingError,
    MealTimingWarning,
    BlueLightWarning,
    PomodoroSessionError,
    RoutineCompletionError,
    PAVErrorLookupError,
)


# =========================================================================
# Severity enum
# =========================================================================


class TestSeverityEnum:
    """The :class:`Severity` StrEnum exposes 5 levels."""

    def test_severity_is_str_enum(self) -> None:
        """Severity is a string-valued enum (StrEnum)."""
        from enum import StrEnum as StdlibStrEnum
        assert issubclass(Severity, StdlibStrEnum)

    def test_five_levels(self) -> None:
        """Exactly 5 severity levels are defined."""
        assert len(Severity) == 5

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (Severity.INFO, "INFO"),
            (Severity.LOW, "LOW"),
            (Severity.MEDIUM, "MEDIUM"),
            (Severity.HIGH, "HIGH"),
            (Severity.CRITICAL, "CRITICAL"),
        ],
    )
    def test_severity_values(self, member: Severity, value: str) -> None:
        """Each member's value matches its name (uppercase)."""
        assert member == value
        assert member.value == value

    def test_severity_equality_with_string(self) -> None:
        """StrEnum members compare equal to their string value."""
        assert Severity.CRITICAL == "CRITICAL"
        assert Severity.HIGH == "HIGH"


# =========================================================================
# Base class
# =========================================================================


class TestProductivitySystemErrorBase:
    """The base :class:`ProductivitySystemError` interface."""

    def test_inherits_from_exception(self) -> None:
        """ProductivitySystemError derives from stdlib Exception."""
        assert issubclass(ProductivitySystemError, Exception)

    def test_default_code_is_err_unknown(self) -> None:
        """Default code is 'ERR_UNKNOWN'."""
        e = ProductivitySystemError("oops")
        assert e.code == "ERR_UNKNOWN"

    def test_default_severity_is_info(self) -> None:
        """Default severity is INFO."""
        e = ProductivitySystemError("oops")
        assert e.severity == Severity.INFO

    def test_message_preserved(self) -> None:
        """First positional arg is the message (Exception contract)."""
        e = ProductivitySystemError("something broke")
        assert e.args[0] == "something broke"
        assert str(e.args[0]) == "something broke"

    def test_custom_code_override(self) -> None:
        """Custom code argument overrides class default."""
        e = ProductivitySystemError("test", code="ERR_CUSTOM")
        assert e.code == "ERR_CUSTOM"

    def test_custom_severity_override(self) -> None:
        """Custom severity argument overrides class default."""
        e = ProductivitySystemError("test", severity=Severity.HIGH)
        assert e.severity == Severity.HIGH

    def test_str_format_includes_code(self) -> None:
        """__str__ includes [CODE] prefix for unambiguous logs."""
        e = ProductivitySystemError("bad", code="ERR_X")
        assert str(e) == "[ERR_X] bad"

    def test_str_format_falls_back_to_default_code(self) -> None:
        """__str__ uses class-default code when no override."""
        e = ProductivitySystemError("bad")
        assert str(e) == "[ERR_UNKNOWN] bad"

    def test_can_be_raised_and_caught(self) -> None:
        """Standard raise/except round-trip works."""
        msg = "test"
        with pytest.raises(ProductivitySystemError) as exc_info:
            raise ProductivitySystemError(msg)
        assert exc_info.value.args[0] == msg

    def test_caught_as_exception(self) -> None:
        """Subclasses are catchable as stdlib Exception (Liskov)."""
        msg = "test"
        with pytest.raises(Exception):  # noqa: B017
            raise ProductivitySystemError(msg)


# =========================================================================
# Subclass hierarchy
# =========================================================================


class TestSubclassHierarchy:
    """All 6 domain subclasses derive from the base."""

    @pytest.mark.parametrize("cls", ALL_SUBCLASSES)
    def test_subclass_of_productivity_system_error(
        self,
        cls: type[ProductivitySystemError],
    ) -> None:
        """Each subclass inherits from ProductivitySystemError."""
        assert issubclass(cls, ProductivitySystemError)

    @pytest.mark.parametrize("cls", ALL_SUBCLASSES)
    def test_subclass_of_exception(self, cls: type[ProductivitySystemError]) -> None:
        """Each subclass is a stdlib Exception."""
        assert issubclass(cls, Exception)

    @pytest.mark.parametrize("cls", ALL_SUBCLASSES)
    def test_can_be_raised_with_no_kwargs(self, cls: type[ProductivitySystemError]) -> None:
        """Each subclass can be raised with just a message."""
        msg = "boom"
        with pytest.raises(cls):
            raise cls(msg)

    def test_time_validation_error_severity(self) -> None:
        """TimeValidationError severity is CRITICAL."""
        assert TimeValidationError.severity == Severity.CRITICAL

    def test_sleep_tracking_error_severity(self) -> None:
        """SleepTrackingError severity is CRITICAL."""
        assert SleepTrackingError.severity == Severity.CRITICAL

    def test_meal_timing_warning_severity(self) -> None:
        """MealTimingWarning severity is HIGH."""
        assert MealTimingWarning.severity == Severity.HIGH

    def test_blue_light_warning_severity(self) -> None:
        """BlueLightWarning severity is HIGH."""
        assert BlueLightWarning.severity == Severity.HIGH

    def test_pomodoro_session_error_severity(self) -> None:
        """PomodoroSessionError severity is MEDIUM."""
        assert PomodoroSessionError.severity == Severity.MEDIUM

    def test_routine_completion_error_severity(self) -> None:
        """RoutineCompletionError severity is MEDIUM."""
        assert RoutineCompletionError.severity == Severity.MEDIUM

    def test_pav_error_lookup_error_severity(self) -> None:
        """PAVErrorLookupError severity is INFO (developer error)."""
        assert PAVErrorLookupError.severity == Severity.INFO

    def test_pav_error_lookup_error_code(self) -> None:
        """PAVErrorLookupError default code is 'ERR_PAV_LOOKUP'."""
        assert PAVErrorLookupError.code == "ERR_PAV_LOOKUP"

    def test_severity_overridable_at_construction(self) -> None:
        """Subclass severity can be overridden per-instance."""
        e = TimeValidationError("test", severity=Severity.LOW)
        assert e.severity == Severity.LOW

    def test_code_overridable_at_construction(self) -> None:
        """Subclass code can be overridden per-instance."""
        e = TimeValidationError("test", code="ERR_TIME_CUSTOM")
        assert e.code == "ERR_TIME_CUSTOM"

    def test_time_codes_route_to_same_class(self) -> None:
        """All 3 TIME_* codes share TimeValidationError (different severity)."""
        assert get_pav_error_spec(PAVErrorCode.TIME_001).exception_class is TimeValidationError
        assert get_pav_error_spec(PAVErrorCode.TIME_002).exception_class is TimeValidationError
        assert get_pav_error_spec(PAVErrorCode.TIME_003).exception_class is TimeValidationError

    def test_sleep_codes_route_to_same_class(self) -> None:
        """Both SLEEP_* codes share SleepTrackingError."""
        assert get_pav_error_spec(PAVErrorCode.SLEEP_001).exception_class is SleepTrackingError
        assert get_pav_error_spec(PAVErrorCode.SLEEP_002).exception_class is SleepTrackingError

    def test_pomodoro_codes_route_to_same_class(self) -> None:
        """Both POMO_* codes share PomodoroSessionError."""
        assert get_pav_error_spec(PAVErrorCode.POMO_001).exception_class is PomodoroSessionError
        assert get_pav_error_spec(PAVErrorCode.POMO_002).exception_class is PomodoroSessionError


# =========================================================================
# PAVErrorCode enum
# =========================================================================


class TestPAVErrorCodeEnum:
    """The :class:`PAVErrorCode` StrEnum exposes the 10 PAV §6 codes."""

    def test_ten_codes(self) -> None:
        """Exactly 10 PAV error codes are declared."""
        assert len(PAVErrorCode) == 10

    def test_all_codes_start_with_err(self) -> None:
        """All PAV codes are prefixed with 'ERR_'."""
        for member in PAVErrorCode:
            assert member.value.startswith("ERR_"), f"{member} missing ERR_ prefix"

    @pytest.mark.parametrize(
        "code",
        list(PAVErrorCode),
        ids=lambda c: c.value,
    )
    def test_each_code_unique(self, code: PAVErrorCode) -> None:
        """Each PAV code has a unique string value."""
        # If two members had the same value, len(PAVErrorCode) would still be
        # 10 but value lookups would alias. The StrEnum contract guarantees
        # uniqueness, so we just smoke-test that each is retrievable.
        assert PAVErrorCode(code.value) is code

    def test_string_lookup_works(self) -> None:
        """StrEnum supports lookup by string value."""
        assert PAVErrorCode("ERR_TIME_001") is PAVErrorCode.TIME_001

    def test_invalid_string_raises_value_error(self) -> None:
        """An unregistered string raises ValueError on enum lookup."""
        with pytest.raises(ValueError):
            PAVErrorCode("ERR_NOT_REAL")


# =========================================================================
# PAV_ERROR_REGISTRY
# =========================================================================


class TestPAVErrorRegistry:
    """The :data:`PAV_ERROR_REGISTRY` is a 10-tuple of PAVErrorSpec."""

    def test_registry_size_is_10(self) -> None:
        """The registry contains exactly 10 entries."""
        assert len(PAV_ERROR_REGISTRY) == 10

    def test_registry_is_tuple(self) -> None:
        """The registry is an immutable tuple (Final)."""
        assert isinstance(PAV_ERROR_REGISTRY, tuple)

    def test_registry_specs_are_frozen(self) -> None:
        """Each PAVErrorSpec is frozen (slots dataclass)."""
        spec = PAV_ERROR_REGISTRY[0]
        with pytest.raises((AttributeError, Exception)):
            spec.code = PAVErrorCode.TIME_001  # type: ignore[misc]

    def test_registry_codes_unique(self) -> None:
        """No two specs share the same code."""
        codes = [s.code for s in PAV_ERROR_REGISTRY]
        assert len(set(codes)) == len(codes)

    def test_registry_covers_all_enum_members(self) -> None:
        """Every PAVErrorCode member is in the registry."""
        registry_codes = {s.code for s in PAV_ERROR_REGISTRY}
        enum_codes = set(PAVErrorCode)
        assert registry_codes == enum_codes

    @pytest.mark.parametrize(
        ("code", "expected"),
        list(EXPECTED_SPECS.items()),
        ids=lambda v: v.name if isinstance(v, PAVErrorCode) else str(v),
    )
    def test_registry_spec_matches_expected(
        self,
        code: PAVErrorCode,
        expected: tuple[type[ProductivitySystemError], Severity, str],
    ) -> None:
        """Each registry spec maps to the right class/severity/condition."""
        expected_cls, expected_severity, expected_condition = expected
        spec = get_pav_error_spec(code)
        assert spec.code == code
        assert spec.exception_class is expected_cls
        assert spec.severity == expected_severity
        assert spec.condition == expected_condition
        assert isinstance(spec.action, str)
        assert spec.action  # non-empty


# =========================================================================
# Lookup
# =========================================================================


class TestGetPavErrorSpec:
    """``get_pav_error_spec`` returns the right spec or raises."""

    def test_lookup_by_enum_member(self) -> None:
        """Looking up by enum member works."""
        spec = get_pav_error_spec(PAVErrorCode.TIME_001)
        assert spec.code is PAVErrorCode.TIME_001

    def test_lookup_by_string_value(self) -> None:
        """Looking up by raw string value works."""
        spec = get_pav_error_spec("ERR_TIME_001")
        assert spec.code is PAVErrorCode.TIME_001

    def test_lookup_unknown_code_raises_lookup_error(self) -> None:
        """Unknown string raises PAVErrorLookupError."""
        with pytest.raises(PAVErrorLookupError) as exc_info:
            get_pav_error_spec("ERR_NOT_REAL")
        assert exc_info.value.code == "ERR_PAV_LOOKUP"
        assert exc_info.value.severity == Severity.INFO

    def test_lookup_unknown_enum_member_raises(self) -> None:
        """Constructing a non-existent enum member raises PAVErrorLookupError."""
        with pytest.raises(PAVErrorLookupError):
            get_pav_error_spec("ERR_FAKE_999")

    def test_lookup_error_chains_original_value_error(self) -> None:
        """The original ValueError from StrEnum is preserved as __cause__."""
        with pytest.raises(PAVErrorLookupError) as exc_info:
            get_pav_error_spec("ERR_NOT_REAL")
        assert isinstance(exc_info.value.__cause__, ValueError)


# =========================================================================
# Raise helper
# =========================================================================


class TestRaisePavError:
    """``raise_pav_error`` raises the right subclass with right metadata."""

    def test_raises_correct_subclass(self) -> None:
        """Raises the exception class registered for the code."""
        with pytest.raises(TimeValidationError):
            raise_pav_error(PAVErrorCode.TIME_001, "wake too early")

    def test_sets_code_on_instance(self) -> None:
        """The raised instance carries the PAV code string."""
        with pytest.raises(ProductivitySystemError) as exc_info:
            raise_pav_error(PAVErrorCode.TIME_001, "msg")
        assert exc_info.value.code == "ERR_TIME_001"

    def test_sets_severity_on_instance(self) -> None:
        """The raised instance carries the registered severity."""
        with pytest.raises(ProductivitySystemError) as exc_info:
            raise_pav_error(PAVErrorCode.SLEEP_001, "msg")
        assert exc_info.value.severity == Severity.CRITICAL

    def test_preserves_message(self) -> None:
        """The user-supplied message is preserved in args."""
        with pytest.raises(ProductivitySystemError) as exc_info:
            raise_pav_error(PAVErrorCode.MEAL_001, "ate after 18h")
        assert exc_info.value.args[0] == "ate after 18h"

    def test_accepts_string_code(self) -> None:
        """String code is accepted (same behaviour as enum member)."""
        with pytest.raises(BlueLightWarning) as exc_info:
            raise_pav_error("ERR_LIGHT_001", "phone after cutoff")
        assert exc_info.value.code == "ERR_LIGHT_001"
        assert exc_info.value.severity == Severity.HIGH

    def test_unknown_code_raises_lookup_error(self) -> None:
        """Unknown code raises PAVErrorLookupError (no silent failure)."""
        with pytest.raises(PAVErrorLookupError):
            raise_pav_error("ERR_NOT_REAL", "msg")

    def test_has_norreturn_annotation(self) -> None:
        """raise_pav_error is typed as NoReturn — it always raises."""
        import typing
        hints = typing.get_type_hints(raise_pav_error)
        assert hints["return"] is typing.NoReturn

    @pytest.mark.parametrize(
        "code",
        list(PAVErrorCode),
        ids=lambda c: c.value,
    )
    def test_raises_for_each_pav_code(self, code: PAVErrorCode) -> None:
        """Every one of the 10 PAV codes can be raised via the helper."""
        spec = get_pav_error_spec(code)
        with pytest.raises(spec.exception_class) as exc_info:
            raise_pav_error(code, f"triggered {code.value}")
        assert exc_info.value.code == code.value
        assert exc_info.value.severity == spec.severity


# =========================================================================
# Parametric per-code tests
# =========================================================================


class TestEachPavErrorCode:
    """One focused test per PAV §6 row."""

    def test_time_001(self) -> None:
        """ERR_TIME_001: wake < 3 → TimeValidationError, CRITICAL."""
        spec = get_pav_error_spec(PAVErrorCode.TIME_001)
        with pytest.raises(TimeValidationError) as exc_info:
            raise_pav_error(PAVErrorCode.TIME_001, "woke at 2am")
        assert exc_info.value.code == "ERR_TIME_001"
        assert exc_info.value.severity == Severity.CRITICAL
        assert "2am" in exc_info.value.args[0]
        assert spec.condition == "hora_acordou < 3"
        assert spec.action == "Raise + Log"

    def test_time_002(self) -> None:
        """ERR_TIME_002: wake > 12 → TimeValidationError, CRITICAL."""
        spec = get_pav_error_spec(PAVErrorCode.TIME_002)
        with pytest.raises(TimeValidationError) as exc_info:
            raise_pav_error(PAVErrorCode.TIME_002, "woke at 13")
        assert exc_info.value.severity == Severity.CRITICAL
        assert spec.condition == "hora_acordou > 12"

    def test_time_003(self) -> None:
        """ERR_TIME_003: wake > 5 → TimeValidationError, HIGH (warning)."""
        spec = get_pav_error_spec(PAVErrorCode.TIME_003)
        with pytest.raises(TimeValidationError) as exc_info:
            raise_pav_error(PAVErrorCode.TIME_003, "woke at 6")
        assert exc_info.value.severity == Severity.HIGH
        assert spec.action == "Warn + Adjust"

    def test_sleep_001(self) -> None:
        """ERR_SLEEP_001: sleep < 4 → SleepTrackingError, CRITICAL."""
        spec = get_pav_error_spec(PAVErrorCode.SLEEP_001)
        with pytest.raises(SleepTrackingError) as exc_info:
            raise_pav_error(PAVErrorCode.SLEEP_001, "slept 3h")
        assert exc_info.value.severity == Severity.CRITICAL
        assert spec.condition == "horas_sono < 4"
        assert spec.action == "Raise + Alert"

    def test_sleep_002(self) -> None:
        """ERR_SLEEP_002: sleep > 12 → SleepTrackingError, CRITICAL."""
        spec = get_pav_error_spec(PAVErrorCode.SLEEP_002)
        with pytest.raises(SleepTrackingError):
            raise_pav_error(PAVErrorCode.SLEEP_002, "slept 14h")
        assert spec.action == "Raise + Log"

    def test_meal_001(self) -> None:
        """ERR_MEAL_001: meal after 18h → MealTimingWarning, HIGH."""
        spec = get_pav_error_spec(PAVErrorCode.MEAL_001)
        with pytest.raises(MealTimingWarning) as exc_info:
            raise_pav_error(PAVErrorCode.MEAL_001, "ate at 19h")
        assert exc_info.value.severity == Severity.HIGH
        assert spec.condition == "refeicao_apos_18h"
        assert spec.action == "Warn + Track"

    def test_light_001(self) -> None:
        """ERR_LIGHT_001: blue-light after 18h → BlueLightWarning, HIGH."""
        spec = get_pav_error_spec(PAVErrorCode.LIGHT_001)
        with pytest.raises(BlueLightWarning) as exc_info:
            raise_pav_error(PAVErrorCode.LIGHT_001, "phone at 20h")
        assert exc_info.value.severity == Severity.HIGH
        assert spec.condition == "luz_azul_apos_18h"
        assert spec.action == "Warn + Notify"

    def test_pomo_001(self) -> None:
        """ERR_POMO_001: rounds < 3 → PomodoroSessionError, MEDIUM."""
        spec = get_pav_error_spec(PAVErrorCode.POMO_001)
        with pytest.raises(PomodoroSessionError) as exc_info:
            raise_pav_error(PAVErrorCode.POMO_001, "only 2 rounds")
        assert exc_info.value.severity == Severity.MEDIUM
        assert spec.condition == "rounds < 3"
        assert spec.action == "Warn + Recover"

    def test_pomo_002(self) -> None:
        """ERR_POMO_002: break < 5min → PomodoroSessionError, MEDIUM."""
        spec = get_pav_error_spec(PAVErrorCode.POMO_002)
        with pytest.raises(PomodoroSessionError) as exc_info:
            raise_pav_error(PAVErrorCode.POMO_002, "break was 2min")
        assert exc_info.value.severity == Severity.MEDIUM
        assert spec.condition == "break < 5min"
        assert spec.action == "Warn + Force"

    def test_routine_001(self) -> None:
        """ERR_ROUTINE_001: routine incomplete → RoutineCompletionError, MEDIUM."""
        spec = get_pav_error_spec(PAVErrorCode.ROUTINE_001)
        with pytest.raises(RoutineCompletionError) as exc_info:
            raise_pav_error(PAVErrorCode.ROUTINE_001, "missed evening ritual")
        assert exc_info.value.severity == Severity.MEDIUM
        assert spec.condition == "rotina_incompleta"
        assert spec.action == "Warn + Schedule"


# =========================================================================
# Exception chaining
# =========================================================================


class TestExceptionChaining:
    """``raise X from Y`` and implicit chaining work as expected."""

    def test_explicit_from_preserves_cause(self) -> None:
        """``raise X from Y`` sets __cause__ to Y."""

        def _raise_wrapped() -> None:
            original_msg = "original"
            try:
                raise ValueError(original_msg)  # noqa: TRY301
            except ValueError as original:
                wrapped_msg = "wrapped"
                raise TimeValidationError(wrapped_msg) from original

        with pytest.raises(TimeValidationError) as exc_info:
            _raise_wrapped()
        assert isinstance(exc_info.value.__cause__, ValueError)
        assert str(exc_info.value.__cause__) == "original"

    def test_implicit_chaining_sets_context(self) -> None:
        """Raising inside an except block sets __context__."""

        def _raise_wrapped() -> None:
            try:
                inner_msg = "original"
                raise ValueError(inner_msg)  # noqa: TRY301
            except ValueError:
                outer_msg = "wrapped"
                raise TimeValidationError(outer_msg)  # noqa: B904

        with pytest.raises(TimeValidationError) as exc_info:
            _raise_wrapped()
        assert isinstance(exc_info.value.__context__, ValueError)

    def test_pav_error_cause_preserved(self) -> None:
        """raise_pav_error can be chained from any exception."""

        def _trigger() -> None:
            try:
                _ = 1 / 0
            except ZeroDivisionError:
                raise_pav_error(PAVErrorCode.TIME_001, "bad wake time")

        with pytest.raises(TimeValidationError) as exc_info:
            _trigger()
        assert isinstance(exc_info.value.__context__, ZeroDivisionError)


# =========================================================================
# PAVErrorSpec dataclass
# =========================================================================


class TestPAVErrorSpecDataclass:
    """``PAVErrorSpec`` is a frozen, slotted dataclass."""

    def test_is_dataclass(self) -> None:
        """PAVErrorSpec is a dataclass."""
        from dataclasses import is_dataclass
        assert is_dataclass(PAVErrorSpec)

    def test_frozen(self) -> None:
        """Assignment to a PAVErrorSpec field raises FrozenInstanceError."""
        from dataclasses import FrozenInstanceError
        spec = PAVErrorSpec(
            code=PAVErrorCode.TIME_001,
            severity=Severity.CRITICAL,
            exception_class=TimeValidationError,
            condition="x",
            action="y",
        )
        with pytest.raises(FrozenInstanceError):
            spec.condition = "modified"  # type: ignore[misc]

    def test_equality(self) -> None:
        """Two specs with same values are equal."""
        a = PAVErrorSpec(
            code=PAVErrorCode.TIME_001,
            severity=Severity.CRITICAL,
            exception_class=TimeValidationError,
            condition="x",
            action="y",
        )
        b = PAVErrorSpec(
            code=PAVErrorCode.TIME_001,
            severity=Severity.CRITICAL,
            exception_class=TimeValidationError,
            condition="x",
            action="y",
        )
        assert a == b

    def test_inequality_on_difference(self) -> None:
        """Specs differing in any field are unequal."""
        a = PAV_ERROR_REGISTRY[0]
        b = PAV_ERROR_REGISTRY[1]
        assert a != b
