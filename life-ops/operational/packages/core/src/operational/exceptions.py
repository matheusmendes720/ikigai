"""Exception hierarchy for the ``operational`` package (PAV §6).

All custom exceptions inherit from :class:`ProductivitySystemError`, which
extends the stdlib :class:`Exception` with two attributes:

* ``code`` (str) — PAV §6 error code, e.g. ``"ERR_TIME_001"``.
* ``severity`` (:class:`Severity`) — INFO / LOW / MEDIUM / HIGH / CRITICAL.

The 10 PAV error codes are declared as :class:`PAVErrorCode` enum members and
catalogued in :data:`PAV_ERROR_REGISTRY`. Helpers :func:`get_pav_error_spec`
and :func:`raise_pav_error` provide look-up and raise-on-demand ergonomics.

Source: ``vibe-ops/base/Produtividade Algorítmica Visual.md`` §6 (lines 328-343)
and ``vibe-ops/planning/PRD-02-habit-tracker.md``.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, NoReturn

__all__ = [
    "PAV_ERROR_REGISTRY",
    "BlueLightWarning",
    "MealTimingWarning",
    "PAVErrorCode",
    "PAVErrorLookupError",
    "PAVErrorSpec",
    "PomodoroSessionError",
    "ProductivitySystemError",
    "RoutineCompletionError",
    "Severity",
    "SleepTrackingError",
    "TimeValidationError",
    "get_pav_error_spec",
    "raise_pav_error",
]


class Severity(StrEnum):
    """Operational severity level for a :class:`ProductivitySystemError`.

    PAV §6 distinguishes 3 actionable levels (``MEDIUM``/``HIGH``/``CRITICAL``);
    the two extra levels (``INFO``/``LOW``) are provided for internal use
    (logging, lookups, soft warnings) without inflating the PAV surface.
    """

    INFO = "INFO"
    """Informational; no user action required (e.g. code look-up miss)."""

    LOW = "LOW"
    """Minor deviation; log only."""

    MEDIUM = "MEDIUM"
    """Recoverable warning (PAV §6: 🟢 Medium). Triggers gentle adjustments."""

    HIGH = "HIGH"
    """Actionable warning (PAV §6: 🟡 High). Requires user awareness."""

    CRITICAL = "CRITICAL"
    """Hard violation (PAV §6: 🔴 Critical). Data integrity at risk."""


class ProductivitySystemError(Exception):
    """Base exception for the entire ``operational`` system.

    All custom exceptions in this package inherit from this class. It exposes
    two structured attributes (``code`` and ``severity``) on top of the
    stdlib ``Exception`` interface (``args``, ``__str__``, ``__repr__``).

    Attributes:
        code: PAV §6 error code string (e.g. ``"ERR_TIME_001"``). Defaults
            to ``"ERR_UNKNOWN"`` for ad-hoc raises.
        severity: Operational severity level. Defaults to :attr:`Severity.INFO`.
    """

    code: str = "ERR_UNKNOWN"
    """Default error code (class-level). Overridden per-instance by ``__init__``."""

    severity: Severity = Severity.INFO
    """Default severity (class-level). Overridden per-instance by ``__init__``."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        severity: Severity | None = None,
    ) -> None:
        """Initialize a ``ProductivitySystemError``.

        Args:
            message: Human-readable description of the error.
            code: PAV error code override. If ``None``, the class-level
                ``code`` is used.
            severity: Severity override. If ``None``, the class-level
                ``severity`` is used.
        """
        super().__init__(message)
        if code is not None:
            self.code = code
        if severity is not None:
            self.severity = severity

    def __str__(self) -> str:
        """Return ``"[CODE] message"`` for unambiguous log lines."""
        return f"[{self.code}] {self.args[0]}"


# --- Domain-specific subclasses (one per PAV §6 family) -------------------


class TimeValidationError(ProductivitySystemError):
    """Errors from PAV §6 — wake/sleep time validation (ERR_TIME_*)."""

    severity: Severity = Severity.CRITICAL


class SleepTrackingError(ProductivitySystemError):
    """Errors from PAV §6 — sleep duration tracking (ERR_SLEEP_*)."""

    severity: Severity = Severity.CRITICAL


class MealTimingWarning(ProductivitySystemError):  # noqa: N818
    """Warnings from PAV §6 — late-meal detection (ERR_MEAL_*)."""

    severity: Severity = Severity.HIGH


class BlueLightWarning(ProductivitySystemError):  # noqa: N818
    """Warnings from PAV §6 — blue-light exposure (ERR_LIGHT_*)."""

    severity: Severity = Severity.HIGH


class PomodoroSessionError(ProductivitySystemError):
    """Warnings from PAV §6 — pomodoro session state (ERR_POMO_*)."""

    severity: Severity = Severity.MEDIUM


class RoutineCompletionError(ProductivitySystemError):
    """Warnings from PAV §6 — routine completion (ERR_ROUTINE_001)."""

    severity: Severity = Severity.MEDIUM


class PAVErrorLookupError(ProductivitySystemError):
    """Raised when an unknown PAV error code is requested via lookup.

    This is a developer-facing error, not a user-facing PAV §6 condition, so
    severity is :attr:`Severity.INFO` and code is ``"ERR_PAV_LOOKUP"``.
    """

    code: str = "ERR_PAV_LOOKUP"
    severity: Severity = Severity.INFO


# --- 10 PAV error codes as StrEnum ----------------------------------------


class PAVErrorCode(StrEnum):
    """The 10 PAV §6 error codes.

    Each member is the canonical string from PAV §6, e.g.
    ``PAVErrorCode.TIME_001 == "ERR_TIME_001"``.
    """

    TIME_001 = "ERR_TIME_001"
    """``hora_acordou < 3`` — wake hour below 3 am. 🔴 Critical. PAV §6 row 1."""

    TIME_002 = "ERR_TIME_002"
    """``hora_acordou > 12`` — wake hour after noon (likely PM/AM confusion)."""

    TIME_003 = "ERR_TIME_003"
    """``hora_acordou > 5`` — wake hour above 5 am. 🟡 High. PAV §6 row 3."""

    SLEEP_001 = "ERR_SLEEP_001"
    """``horas_sono < 4`` — sleep under 4 h. 🔴 Critical. PAV §6 row 4."""

    SLEEP_002 = "ERR_SLEEP_002"
    """``horas_sono > 12`` — sleep over 12 h (likely data entry error)."""

    MEAL_001 = "ERR_MEAL_001"
    """``refeicao_apos_18h`` — last meal after 18 h. 🟡 High. PAV §6 row 6."""

    LIGHT_001 = "ERR_LIGHT_001"
    """``luz_azul_apos_18h`` — blue-light exposure after 18 h. PAV §6 row 7."""

    POMO_001 = "ERR_POMO_001"
    """``rounds < 3`` — pomodoro session below 3 rounds. PAV §6 row 8."""

    POMO_002 = "ERR_POMO_002"
    """``break < 5min`` — pomodoro break too short. PAV §6 row 9."""

    ROUTINE_001 = "ERR_ROUTINE_001"
    """``rotina_incompleta`` — daily routine incomplete. PAV §6 row 10."""


# --- Registry mapping codes to exception classes ---------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class PAVErrorSpec:
    """Immutable specification of a single PAV §6 error.

    Attributes:
        code: Canonical PAV error code.
        severity: Operational severity.
        exception_class: Concrete exception class to raise.
        condition: Human-readable condition that triggers the error.
        action: Recommended action from PAV §6 (e.g. ``"Raise + Log"``).
    """

    code: PAVErrorCode
    severity: Severity
    exception_class: type[ProductivitySystemError]
    condition: str
    action: str


PAV_ERROR_REGISTRY: Final[tuple[PAVErrorSpec, ...]] = (
    PAVErrorSpec(
        code=PAVErrorCode.TIME_001,
        severity=Severity.CRITICAL,
        exception_class=TimeValidationError,
        condition="hora_acordou < 3",
        action="Raise + Log",
    ),
    PAVErrorSpec(
        code=PAVErrorCode.TIME_002,
        severity=Severity.CRITICAL,
        exception_class=TimeValidationError,
        condition="hora_acordou > 12",
        action="Raise + Log",
    ),
    PAVErrorSpec(
        code=PAVErrorCode.TIME_003,
        severity=Severity.HIGH,
        exception_class=TimeValidationError,
        condition="hora_acordou > 5",
        action="Warn + Adjust",
    ),
    PAVErrorSpec(
        code=PAVErrorCode.SLEEP_001,
        severity=Severity.CRITICAL,
        exception_class=SleepTrackingError,
        condition="horas_sono < 4",
        action="Raise + Alert",
    ),
    PAVErrorSpec(
        code=PAVErrorCode.SLEEP_002,
        severity=Severity.CRITICAL,
        exception_class=SleepTrackingError,
        condition="horas_sono > 12",
        action="Raise + Log",
    ),
    PAVErrorSpec(
        code=PAVErrorCode.MEAL_001,
        severity=Severity.HIGH,
        exception_class=MealTimingWarning,
        condition="refeicao_apos_18h",
        action="Warn + Track",
    ),
    PAVErrorSpec(
        code=PAVErrorCode.LIGHT_001,
        severity=Severity.HIGH,
        exception_class=BlueLightWarning,
        condition="luz_azul_apos_18h",
        action="Warn + Notify",
    ),
    PAVErrorSpec(
        code=PAVErrorCode.POMO_001,
        severity=Severity.MEDIUM,
        exception_class=PomodoroSessionError,
        condition="rounds < 3",
        action="Warn + Recover",
    ),
    PAVErrorSpec(
        code=PAVErrorCode.POMO_002,
        severity=Severity.MEDIUM,
        exception_class=PomodoroSessionError,
        condition="break < 5min",
        action="Warn + Force",
    ),
    PAVErrorSpec(
        code=PAVErrorCode.ROUTINE_001,
        severity=Severity.MEDIUM,
        exception_class=RoutineCompletionError,
        condition="rotina_incompleta",
        action="Warn + Schedule",
    ),
)
"""The 10 PAV §6 error specifications, ordered by PAV source row."""


# --- Lookup & raise helpers ------------------------------------------------


def get_pav_error_spec(code: PAVErrorCode | str) -> PAVErrorSpec:
    """Look up a :class:`PAVErrorSpec` by code.

    Args:
        code: A :class:`PAVErrorCode` member or its string value
            (e.g. ``"ERR_TIME_001"``).

    Returns:
        The matching :class:`PAVErrorSpec`.

    Raises:
        PAVErrorLookupError: If ``code`` is not registered.
    """
    if not isinstance(code, PAVErrorCode):
        try:
            code = PAVErrorCode(code)
        except ValueError as exc:
            msg = f"Unknown PAV error code: {code!r}"
            raise PAVErrorLookupError(
                msg,
                code="ERR_PAV_LOOKUP",
                severity=Severity.INFO,
            ) from exc
    # PAVErrorCode is a closed enum; every member is in PAV_ERROR_REGISTRY.
    # The next() default branch is therefore unreachable in practice.
    try:
        return next(spec for spec in PAV_ERROR_REGISTRY if spec.code == code)
    except StopIteration as exc:  # pragma: no cover
        msg = f"PAV error code not in registry: {code!r}"
        raise PAVErrorLookupError(
            msg,
            code="ERR_PAV_LOOKUP",
            severity=Severity.INFO,
        ) from exc


def raise_pav_error(code: PAVErrorCode | str, message: str) -> NoReturn:
    """Raise the matching PAV exception for a given code.

    This is the canonical entry point for emitting PAV §6 errors from
    business logic. It looks up the code, instantiates the right exception
    class with the correct ``code``/``severity``, and raises it.

    Args:
        code: A :class:`PAVErrorCode` member or its string value.
        message: Human-readable error message.

    Raises:
        PAVErrorLookupError: If ``code`` is not registered.
        ProductivitySystemError: Subclass matching ``code`` (always raised,
            this function returns ``NoReturn``).
    """
    spec = get_pav_error_spec(code)
    raise spec.exception_class(
        message,
        code=spec.code.value,
        severity=spec.severity,
    )
