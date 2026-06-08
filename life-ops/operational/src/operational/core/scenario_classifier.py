"""Daily scenario classifier (PAV §8).

Pure decision function: given a day's metrics, classify it as one of
the three PAV §8 scenarios and emit a list of recommended
adjustments. No I/O, no persistence, no logging.

The three scenarios (PAV §8):

* **PERFEITO** (Padrão Ouro) — all metrics nominal. Maintain the
  routine and keep tracking.
* **DESVIADO** (Desvio Leve) — minor deviations (5-7 h sleep, < 70 %
  pomodoros, or ``>= 1`` infraction). Suggest compensations (extra
  5 min breaks, reduce S3, sleep earlier tomorrow).
* **HARDCORE** (4 h sleep emergency) — critical condition
  (``< 5 h`` sleep **or** ``>= 3`` infractions). Suggest power nap,
  cancel S3, focus on CRITICAL tasks, recovery sleep.
  **Max 2x per month** — see :func:`is_hardcore_alert`.

Decision rules (PAV §8, in priority order):

1. **HARDCORE** if ``horas_sono < 5`` **or** ``infraction_count >= 3``.
2. **DESVIADO** if ``5 <= horas_sono < 7`` **or**
   ``pomodoros_completos / pomodoros_planejados < 0.7`` **or**
   ``infraction_count >= 1``.
3. **PERFEITO** otherwise.

Optional 1-10 self-reports (energy, focus) boost the confidence of
**DESVIADO** classifications by ``+5`` when they fall below ``5``.

The classifier is the canonical entry point used by the daily
orchestrator (Sprint 3C) to decide which adjustments to inject into
the daily report.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

__all__ = [
    "HARDCORE_MAX_PER_MONTH",
    "Scenario",
    "ScenarioClassification",
    "classificar_dia",
    "is_hardcore_alert",
]


# ---------------------------------------------------------------------------
# Public enum: Scenario
# ---------------------------------------------------------------------------


class Scenario(StrEnum):
    """The 3 daily scenarios defined in PAV §8.

    Values are lowercase strings for natural JSON / YAML
    serialization. Members are ordered by load (PERFEITO < DESVIADO <
    HARDCORE) — this matches the conventional reporting order in
    the daily report.

    Attributes:
        PERFEITO: Padrão Ouro — all metrics nominal.
        DESVIADO: Desvio Leve — minor deviations; suggest
            compensations.
        HARDCORE: 4 h sleep emergency — critical condition.
            Max :data:`HARDCORE_MAX_PER_MONTH` per month.
    """

    PERFEITO = "perfeito"
    DESVIADO = "desviado"
    HARDCORE = "hardcore"


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ScenarioClassification:
    """Immutable result of :func:`classificar_dia`.

    Attributes:
        scenario: The classified :class:`Scenario`.
        confidence: Confidence score in ``[0.0, 100.0]``. Higher means
            the classifier is more certain. Capped at ``95.0`` so
            PERFEITO classifications do not over-commit to "perfect".
        reasons: Tuple of human-readable reasons that contributed to
            the classification. Empty only on degenerate input.
        recommended_adjustments: Tuple of adjustment strings ready for
            the daily report. Order is stable: the most important
            adjustment is first.
    """

    scenario: Scenario
    confidence: float
    reasons: tuple[str, ...]
    recommended_adjustments: tuple[str, ...]


# ---------------------------------------------------------------------------
# Module-level constants (from PAV §8)
# ---------------------------------------------------------------------------

# Sleep-duration thresholds (hours)
_SONO_HARDCORE_MAX_H: Final[float] = 5.0
_SONO_DEVIADO_MAX_H: Final[float] = 7.0

# Pomodoro completion threshold (fraction of planned)
_POMODORO_DEVIATION_THRESHOLD: Final[float] = 0.7

# Hardcore monthly cap
HARDCORE_MAX_PER_MONTH: Final[int] = 2
"""Maximum number of HARDCORE days allowed per calendar month (PAV §8)."""

# Confidence scores (0-100 scale)
_HARDCORE_SONO_CONFIDENCE: Final[float] = 95.0
_HARDCORE_INFRACTION_CONFIDENCE: Final[float] = 90.0
_DESVIADO_SONO_CONFIDENCE: Final[float] = 80.0
_DESVIADO_INFRACTION_CONFIDENCE: Final[float] = 70.0
_DESVIADO_POMODORO_CONFIDENCE: Final[float] = 75.0
_PERFEITO_CONFIDENCE: Final[float] = 95.0

# Optional-signal thresholds (1-10 self-report scale)
_LOW_SELF_REPORT_THRESHOLD: Final[int] = 5
_SELF_REPORT_MIN: Final[int] = 1
_SELF_REPORT_MAX: Final[int] = 10

# Hardcore infraction threshold (PAV §8)
_HARDCORE_INFRACTION_THRESHOLD: Final[int] = 3

# Optional-signal boost (applied to DESVIADO confidence when energy
# or focus self-reports fall below 5/10)
_CONFIDENCE_BOOST: Final[float] = 5.0
_CONFIDENCE_CAP: Final[float] = 95.0

# Recommended adjustment strings — kept as module-level constants so
# they can be re-used in tests, docstrings, and the CLI formatter.
_ADJ_HARDCORE_POWER_NAP: Final[str] = "Power nap 13-14h (20min)"
_ADJ_HARDCORE_CANCEL_S3: Final[str] = "Cancelar Pomodoro S3"
_ADJ_HARDCORE_FOCO_CRITICAS: Final[str] = "Foco apenas em tarefas CRÍTICAS"
_ADJ_HARDCORE_RECUPERACAO: Final[str] = "Recuperação: noite seguinte dormir 18h"
_ADJ_HARDCORE_REINICIAR: Final[str] = "Reiniciar ciclo completo"
_ADJ_HARDCORE_REVISAR_ROTINAS: Final[str] = "Revisar rotinas"
_ADJ_DESVIADO_PAUSA_EXTRA: Final[str] = "Pausa extra de 5min entre rounds"
_ADJ_DESVIADO_REDUZIR_S3: Final[str] = "Reduzir S3 para 2 rounds"
_ADJ_DESVIADO_CRITICAS: Final[str] = "Priorizar tarefas CRÍTICAS"
_ADJ_DESVIADO_COMPENSAR_SONO: Final[str] = "Compensar dormindo 1h mais cedo amanhã"
_ADJ_DESVIADO_REVISAR_ROTINAS: Final[str] = "Revisar e ajustar rotinas"
_ADJ_DESVIADO_INVESTIGAR: Final[str] = "Investigar bloqueios"
_ADJ_PERFEITO_MANTER: Final[str] = "Manter rotina"
_ADJ_PERFEITO_CONTINUAR: Final[str] = "Continuar tracking"

# Misc
_LIMIT_HARDCORE_FMT: Final[str] = "\u26a0\ufe0f Limite: máximo {n}x por mês"
"""Warning prefix used in the hardcore limit reminder.

Encoded as ``"\u26a0\ufe0f"`` (``⚠️``) to keep this source file
emoji-free while still surfacing the canonical emoji in the
runtime adjustment string.
"""


# ---------------------------------------------------------------------------
# Public function: classificar_dia
# ---------------------------------------------------------------------------


def classificar_dia(  # noqa: PLR0913  (decision function takes many metrics)
    horas_sono: float,
    pomodoros_planejados: int,
    pomodoros_completos: int,
    infraction_count: int = 0,
    energia_nivel: int | None = None,
    foco_nivel: int | None = None,
) -> ScenarioClassification:
    """Classify the daily scenario from PAV §8 metrics.

    The decision tree is:

    1. ``horas_sono < 5`` **or** ``infraction_count >= 3`` →
       :attr:`Scenario.HARDCORE` (confidence ``95`` / ``90``).
    2. ``5 <= horas_sono < 7`` **or**
       ``pomodoros_completos / pomodoros_planejados < 0.7`` **or**
       ``infraction_count >= 1`` → :attr:`Scenario.DESVIADO`
       (confidence ``80`` / ``70`` / ``75``).
    3. Otherwise → :attr:`Scenario.PERFEITO` (confidence ``95``).

    Optional 1-10 self-reports (``energia_nivel``, ``foco_nivel``)
    boost the confidence of a **DESVIADO** classification by
    ``+5`` each when they fall below ``5`` (capped at ``95``).

    Args:
        horas_sono: Sleep duration in hours. Must be ``>= 0``.
        pomodoros_planejados: Pomodoros planned for the day
            (typically ``12``). Must be ``>= 0``.
        pomodoros_completos: Pomodoros actually completed. Must be
            ``>= 0`` and at most ``pomodoros_planejados``.
        infraction_count: Number of routine infractions (e.g. woke
            up late, missed a ritual). Defaults to ``0``. Must be
            ``>= 0``.
        energia_nivel: Self-reported energy level in ``[1, 10]``, or
            ``None`` to skip the optional boost. Defaults to
            ``None``.
        foco_nivel: Self-reported focus level in ``[1, 10]``, or
            ``None`` to skip. Defaults to ``None``.

    Returns:
        A :class:`ScenarioClassification` with the scenario, a
        confidence score, the contributing reasons, and a tuple of
        recommended adjustments.

    Raises:
        ValueError: If any numeric argument is negative, if
            ``pomodoros_completos > pomodoros_planejados`` (data
            error), or if an optional 1-10 level is out of range.
    """
    _validate_inputs(
        horas_sono=horas_sono,
        pomodoros_planejados=pomodoros_planejados,
        pomodoros_completos=pomodoros_completos,
        infraction_count=infraction_count,
        energia_nivel=energia_nivel,
        foco_nivel=foco_nivel,
    )

    reasons: list[str] = []
    adjustments: list[str] = []

    # --- HARDCORE branch (priority 1) -------------------------------------
    if horas_sono < _SONO_HARDCORE_MAX_H:
        reasons.append(f"Sono crítico: {horas_sono}h (<5h)")
        adjustments.extend(
            (
                _ADJ_HARDCORE_POWER_NAP,
                _ADJ_HARDCORE_CANCEL_S3,
                _ADJ_HARDCORE_FOCO_CRITICAS,
                _ADJ_HARDCORE_RECUPERACAO,
                _LIMIT_HARDCORE_FMT.format(n=HARDCORE_MAX_PER_MONTH),
            )
        )
        return ScenarioClassification(
            scenario=Scenario.HARDCORE,
            confidence=_HARDCORE_SONO_CONFIDENCE,
            reasons=tuple(reasons),
            recommended_adjustments=tuple(adjustments),
        )
    if infraction_count >= _HARDCORE_INFRACTION_THRESHOLD:
        reasons.append(f"Infrações graves: {infraction_count} (>=3)")
        return ScenarioClassification(
            scenario=Scenario.HARDCORE,
            confidence=_HARDCORE_INFRACTION_CONFIDENCE,
            reasons=tuple(reasons),
            recommended_adjustments=(_ADJ_HARDCORE_REINICIAR, _ADJ_HARDCORE_REVISAR_ROTINAS),
        )

    # --- DESVIADO branch (priority 2) -------------------------------------
    confidence: float
    if horas_sono < _SONO_DEVIADO_MAX_H:
        reasons.append(f"Sono reduzido: {horas_sono}h (<7h)")
        adjustments.extend(
            (
                _ADJ_DESVIADO_PAUSA_EXTRA,
                _ADJ_DESVIADO_REDUZIR_S3,
                _ADJ_DESVIADO_CRITICAS,
                _ADJ_DESVIADO_COMPENSAR_SONO,
            )
        )
        confidence = _DESVIADO_SONO_CONFIDENCE
    elif infraction_count >= 1:
        reasons.append(f"{infraction_count} infração(ões) de rotina")
        adjustments.append(_ADJ_DESVIADO_REVISAR_ROTINAS)
        confidence = _DESVIADO_INFRACTION_CONFIDENCE
    elif pomodoros_planejados > 0:
        completion_ratio = pomodoros_completos / pomodoros_planejados
        if completion_ratio < _POMODORO_DEVIATION_THRESHOLD:
            reasons.append(
                f"Baixa execução: {pomodoros_completos}/{pomodoros_planejados} "
                f"pomodoros ({completion_ratio * 100:.0f}% < "
                f"{_POMODORO_DEVIATION_THRESHOLD * 100:.0f}%)"
            )
            adjustments.append(_ADJ_DESVIADO_INVESTIGAR)
            confidence = _DESVIADO_POMODORO_CONFIDENCE
        else:
            # --- PERFEITO (high execution) ---------------------------------
            return _perfeito_result(
                completion_ratio=completion_ratio,
                energia_nivel=energia_nivel,
                foco_nivel=foco_nivel,
            )
    else:
        # --- PERFEITO (no pomodoros planned) -----------------------------
        return _perfeito_result(
            completion_ratio=None,
            energia_nivel=energia_nivel,
            foco_nivel=foco_nivel,
        )

    # --- Optional confidence boosts (DESVIADO only) -----------------------
    if energia_nivel is not None and energia_nivel < _LOW_SELF_REPORT_THRESHOLD:
        reasons.append(f"Energia baixa: {energia_nivel}/10")
        confidence = min(_CONFIDENCE_CAP, confidence + _CONFIDENCE_BOOST)
    if foco_nivel is not None and foco_nivel < _LOW_SELF_REPORT_THRESHOLD:
        reasons.append(f"Foco baixo: {foco_nivel}/10")
        confidence = min(_CONFIDENCE_CAP, confidence + _CONFIDENCE_BOOST)

    return ScenarioClassification(
        scenario=Scenario.DESVIADO,
        confidence=confidence,
        reasons=tuple(reasons),
        recommended_adjustments=tuple(adjustments),
    )


# ---------------------------------------------------------------------------
# Public function: is_hardcore_alert
# ---------------------------------------------------------------------------


def is_hardcore_alert(hardcore_count_this_month: int) -> bool:
    """Return ``True`` when the user has reached the monthly hardcore cap.

    PAV §8 caps hardcore days at :data:`HARDCORE_MAX_PER_MONTH` (2)
    per calendar month. Callers can use this helper to surface a
    warning (e.g. ``"⚠️ Limite atingido"``) in the daily report.

    Args:
        hardcore_count_this_month: Number of :attr:`Scenario.HARDCORE`
            days already accumulated in the current calendar month.
            Must be ``>= 0``.

    Returns:
        ``True`` when ``hardcore_count_this_month >= 2``; ``False``
        otherwise.

    Raises:
        ValueError: If ``hardcore_count_this_month`` is negative.
    """
    if hardcore_count_this_month < 0:
        msg = f"hardcore_count_this_month must be >= 0, got {hardcore_count_this_month}"
        raise ValueError(msg)
    return hardcore_count_this_month >= HARDCORE_MAX_PER_MONTH


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_inputs(  # noqa: PLR0913  (mirrors classificar_dia signature)
    *,
    horas_sono: float,
    pomodoros_planejados: int,
    pomodoros_completos: int,
    infraction_count: int,
    energia_nivel: int | None,
    foco_nivel: int | None,
) -> None:
    """Validate :func:`classificar_dia` inputs.

    Raises:
        ValueError: If any constraint is violated. Messages name the
            offending argument and its bad value for easy debugging.
    """
    if horas_sono < 0:
        msg = f"horas_sono must be >= 0, got {horas_sono}"
        raise ValueError(msg)
    if pomodoros_planejados < 0:
        msg = f"pomodoros_planejados must be >= 0, got {pomodoros_planejados}"
        raise ValueError(msg)
    if pomodoros_completos < 0:
        msg = f"pomodoros_completos must be >= 0, got {pomodoros_completos}"
        raise ValueError(msg)
    if pomodoros_planejados > 0 and pomodoros_completos > pomodoros_planejados:
        msg = (
            f"pomodoros_completos ({pomodoros_completos}) must be <= "
            f"pomodoros_planejados ({pomodoros_planejados})"
        )
        raise ValueError(msg)
    if infraction_count < 0:
        msg = f"infraction_count must be >= 0, got {infraction_count}"
        raise ValueError(msg)
    if energia_nivel is not None and not _SELF_REPORT_MIN <= energia_nivel <= _SELF_REPORT_MAX:
        msg = f"energia_nivel must be in [1, 10], got {energia_nivel}"
        raise ValueError(msg)
    if foco_nivel is not None and not _SELF_REPORT_MIN <= foco_nivel <= _SELF_REPORT_MAX:
        msg = f"foco_nivel must be in [1, 10], got {foco_nivel}"
        raise ValueError(msg)


def _perfeito_result(
    *,
    completion_ratio: float | None,
    energia_nivel: int | None,
    foco_nivel: int | None,
) -> ScenarioClassification:
    """Build a :attr:`Scenario.PERFEITO` :class:`ScenarioClassification`.

    Used by :func:`classificar_dia` for both the "high execution"
    and "no pomodoros planned" branches.

    Args:
        completion_ratio: Optional ``pomodoros_completos /
            pomodoros_planejados`` ratio, formatted into the reasons
            when provided.
        energia_nivel: Optional energy level (only contributes to
            reasons when ``< 5``).
        foco_nivel: Optional focus level (only contributes to
            reasons when ``< 5``).

    Returns:
        A PERFEITO classification with confidence ``95`` and the
        canonical ``("Manter rotina", "Continuar tracking")``
        adjustments.
    """
    reasons: list[str] = ["Sono adequado"]
    if completion_ratio is not None:
        reasons.append(f"Execução {completion_ratio * 100:.0f}%")
    else:
        reasons.append("Sem infrações")
    if energia_nivel is not None and energia_nivel < _LOW_SELF_REPORT_THRESHOLD:
        reasons.append(f"Energia baixa: {energia_nivel}/10")
    if foco_nivel is not None and foco_nivel < _LOW_SELF_REPORT_THRESHOLD:
        reasons.append(f"Foco baixo: {foco_nivel}/10")

    return ScenarioClassification(
        scenario=Scenario.PERFEITO,
        confidence=_PERFEITO_CONFIDENCE,
        reasons=tuple(reasons),
        recommended_adjustments=(_ADJ_PERFEITO_MANTER, _ADJ_PERFEITO_CONTINUAR),
    )
