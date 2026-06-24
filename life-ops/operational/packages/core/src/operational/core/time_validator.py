"""Wake-up time validation with match-case decision tree (PAV §4).

This module implements the **canonical wake-up time validator** of the
``operational`` package. It encodes the PAV §4 decision tree as a
``match`` statement (Python 3.11+ structural pattern matching) and
returns a rich :class:`WakeUpValidation` result for in-range hours
(3-11) or raises a :class:`TimeValidationError` for out-of-range hours
(0-2 and 12+).

Source spec:
    * PAV ``vibe-ops/base/Produtividade Algorítmica Visual.md`` §4
      (lines 192-218) — wake-up hour bucketing and corrective actions.
    * PAV §6 (lines 328-343) — error codes ``ERR_TIME_001`` (wake < 3)
      and ``ERR_TIME_002`` (wake > 12).

Design rules:

* **Pure functions** — no I/O, no state mutation, no logging side effects.
* **mypy --strict** compatible — ``match-case`` patterns are statically
  typed; ``h`` bindings in guards are inferred as ``int``.
* **ruff ALL** compliant — line-length 100, Google docstrings.
* Uses :func:`operational.exceptions.raise_pav_error` to ensure the
  raised exception carries the correct PAV §6 code and severity.
* No imports from :mod:`operational.entities`, :mod:`operational.core.*`
  (sibling), or :mod:`operational.parsers` to avoid circular dependencies.

Public surface
--------------
* :data:`WakeUpStatus` — :class:`typing.Literal` of the 5 status strings.
* :class:`WakeUpValidation` — frozen dataclass returned by
  :func:`validar_horario_acordar`.
* :func:`validar_horario_acordar` — the canonical PAV §4 validator.
* :func:`is_optimal_wake_hour` — quick boolean check for the 3-5am band.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, NoReturn

from operational.constants import DEFAULT
from operational.exceptions import (
    PAVErrorCode,
    Severity,
    TimeValidationError,
    raise_pav_error,
)

__all__ = [
    "WakeUpStatus",
    "WakeUpValidation",
    "is_optimal_wake_hour",
    "validar_horario_acordar",
]


# ---------------------------------------------------------------------------
# Type definitions
# ---------------------------------------------------------------------------

WakeUpStatus = Literal[
    "OPTIMAL",
    "LEVE_DESVIO",
    "DESVIO_MODERADO",
    "CRITICO",
    "IMPOSSIVEL",
]
"""The 5 wake-up validation statuses (PAV §4).

* ``"OPTIMAL"`` — wake-up at 3-5am (gold standard).
* ``"LEVE_DESVIO"`` — wake-up at 6am (1h past max).
* ``"DESVIO_MODERADO"`` — wake-up at 7am (2h past max).
* ``"CRITICO"`` — wake-up at 8-11am (3-6h past max).
* ``"IMPOSSIVEL"`` — wake-up at 0-2am or 12+ (data error or pre-dawn sleep).
"""


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# PAV §4 hour boundaries
_HOUR_MIN: Final[int] = 0
_HOUR_MAX: Final[int] = 23
"""Valid 24h clock range for wake-up hour input."""

# PAV §4 valid wake-up range
_OPTIMAL_MIN: Final[int] = 3
_OPTIMAL_MAX: Final[int] = 5
"""Gold-standard wake-up window (3-5am) — delegated to DEFAULT via is_optimal_wake_hour."""

# PAV §4 status-band cutoffs
_LEVE_CUTOFF: Final[int] = 6  # 1h past max
_MODERADO_CUTOFF: Final[int] = 7  # 2h past max
_CRITICO_LO: Final[int] = 8
_CRITICO_HI: Final[int] = 11
_IMPOSSIVEL_LO: Final[int] = 12
"""The 6 PAV §4 hour-band cutoffs."""

# Deviation minutes per band
_LEVE_DEVIATION_MIN: Final[int] = 60
_MODERADO_DEVIATION_MIN: Final[int] = 120
_CRITICO_BASE_DEVIATION_MIN: Final[int] = 5
"""Deviation-from-5am baselines for the 3 PAV §4 status bands."""

# Hours per minute (for CRITICO deviation formula)
_MINUTES_PER_HOUR: Final[int] = 60


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class WakeUpValidation:
    """Immutable result of validating a wake-up hour (PAV §4).

    Attributes:
        status: One of the 5 :data:`WakeUpStatus` literals.
        message: Human-readable explanation, including the offending hour.
        acao: Recommended corrective action from PAV §4.
        desvio_minutos: Deviation from the 5am boundary in minutes.
            Always ``>= 0`` for returned validations; ``-999`` is reserved
            for impossible hours and never returned (the function raises
            for those).
        is_valid: ``True`` if the schedule is in the acceptable range
            (3-11am, status != IMPOSSIVEL).
    """

    status: WakeUpStatus
    message: str
    acao: str
    desvio_minutos: int
    is_valid: bool


# ---------------------------------------------------------------------------
# Validator (PAV §4)
# ---------------------------------------------------------------------------


def _raise_impossible(hour: int) -> NoReturn:
    """Raise the appropriate PAV §6 error for an impossible wake-up hour.

    The two impossible ranges are:

    * ``0 <= hour <= 2`` → :attr:`PAVErrorCode.TIME_001` (CRITICAL).
    * ``hour >= 12``     → :attr:`PAVErrorCode.TIME_002` (CRITICAL).

    Args:
        hour: The offending wake-up hour.

    Raises:
        TimeValidationError: Always raised, with the correct PAV §6 code
            and severity embedded in the instance. Function never returns
            (``NoReturn``).
    """
    if hour >= _IMPOSSIVEL_LO:
        raise_pav_error(
            PAVErrorCode.TIME_002,
            f"hora_acordou={hour} é impossível (>12)",
        )
    else:
        # hour < _OPTIMAL_MIN
        raise_pav_error(
            PAVErrorCode.TIME_001,
            f"hora_acordou={hour} é impossível (<3)",
        )


def validar_horario_acordar(hora_acordou: int) -> WakeUpValidation:
    """Validate if the wake-up hour is within the PAV §4 gold standard.

    Implements the PAV §4 match-case decision tree. The five status
    bands map to distinct corrective actions:

    ==========  ===========  ===============  ============================
    Hour        Status       Deviation (min)  Action
    ==========  ===========  ===============  ============================
    3, 4, 5     OPTIMAL      0                Continuar rotina normal
    6           LEVE_DESVIO  60               Compensar pausa extra
    7           DESVIO_MODERADO  120          Reduzir pomodoros em 1 round
    8-11        CRITICO      (h-5)*60         Reiniciar ciclo
    0-2, 12+    IMPOSSIVEL   —                :class:`TimeValidationError`
    ==========  ===========  ===============  ============================

    Args:
        hora_acordou: Wake-up hour in 24h format (0-23). Must be ``int``
            (booleans rejected explicitly).

    Returns:
        :class:`WakeUpValidation` for hours 3-11.

    Raises:
        TypeError: If ``hora_acordou`` is not ``int`` (bool rejected).
        TimeValidationError: If ``hora_acordou`` is in 0-2 (TIME_001)
            or 12+ (TIME_002). The exception carries the PAV §6 code
            and severity.
    """
    if isinstance(hora_acordou, bool):
        msg = "hora_acordou must be int, got bool"
        raise TypeError(msg)
    if not isinstance(hora_acordou, int):
        msg = f"hora_acordou must be int, got {type(hora_acordou).__name__}"
        raise TypeError(msg)
    if not _HOUR_MIN <= hora_acordou <= _HOUR_MAX:
        msg = f"hora_acordou must be in [0, 23], got {hora_acordou}"
        raise ValueError(msg)

    match hora_acordou:
        case 3 | 4 | 5:
            return WakeUpValidation(
                status="OPTIMAL",
                message=(
                    f"Horário {hora_acordou}h dentro do padrão ouro (3-5am)"
                ),
                acao="Continuar rotina normal",
                desvio_minutos=0,
                is_valid=True,
            )
        case 6:
            return WakeUpValidation(
                status="LEVE_DESVIO",
                message="1 hora além do limite máximo (5h)",
                acao="Compensar com pausa extra no período 1",
                desvio_minutos=_LEVE_DEVIATION_MIN,
                is_valid=True,
            )
        case 7:
            return WakeUpValidation(
                status="DESVIO_MODERADO",
                message="2 horas além do limite máximo (5h)",
                acao="Reduzir pomodoros do período 1 em 1 round",
                desvio_minutos=_MODERADO_DEVIATION_MIN,
                is_valid=True,
            )
        case h if _CRITICO_LO <= h <= _CRITICO_HI:
            deviation = (h - _OPTIMAL_MAX) * _MINUTES_PER_HOUR
            return WakeUpValidation(
                status="CRITICO",
                message=f"{h - _OPTIMAL_MAX} horas além do limite (5h)",
                acao="Reiniciar ciclo: ajustar horário de dormir hoje",
                desvio_minutos=deviation,
                is_valid=True,
            )
        case h if h >= _IMPOSSIVEL_LO:
            _raise_impossible(h)
        case h if h < _OPTIMAL_MIN:
            _raise_impossible(h)
        case _:  # pragma: no cover — unreachable given the guards above
            invalid_msg = f"Valor inválido: {hora_acordou}"
            raise TimeValidationError(
                invalid_msg,
                code="ERR_TIME_INVALID",
                severity=Severity.CRITICAL,
            )


def is_optimal_wake_hour(hora_acordou: int) -> bool:
    """Quick boolean check: is this hour in the PAV §4 gold band (3-5am)?

    This is a pure delegation to :meth:`PAVConstants.is_valid_wake_hour`
    and never raises. The 3-5am window is the *only* one considered
    "optimal" — even 6am (which returns ``LEVE_DESVIO``) is rejected.

    Args:
        hora_acordou: Wake-up hour in 24h format (0-23).

    Returns:
        ``True`` iff ``DEFAULT.HORARIO_ACORDAR_MIN <= hora_acordou <= DEFAULT.HORARIO_ACORDAR_MAX``.
    """
    return DEFAULT.is_valid_wake_hour(hora_acordou)
