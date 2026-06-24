"""Budget & scenario classifier (PAV V3 §3 — Orcamento vs Realizacao).

Computes the orcado (planned) vs realizado (actual) hardwork minutes
for a given day type, classifies the day, and produces the
X-coordinate (produtividade) of the Cartesian plane.

Anti-fragile: the budget is recomputed from the canonical PAVConstants,
so any window change propagates automatically.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from operational.enums import TipoDia

if TYPE_CHECKING:
    from datetime import date


def budget_for_day_type(tipo: TipoDia) -> int:
    """Return the orçado (planned) hardwork minutes for a day type.

    Args:
        tipo: Day type.

    Returns:
        int: Planned minutes. Defaults to the enum's
        :attr:`TipoDia.orcado_min_padrao` if the type is unknown.
    """
    return tipo.orcado_min_padrao


def budget_for_date(d: date, tipo: TipoDia | None = None) -> int:
    """Compute the orçado for a specific date.

    Args:
        d: Calendar date.
        tipo: Optional day type. If None, falls back to
            :attr:`TipoDia.CURSO` (seg-sex) or :attr:`TipoDia.LIVRE`
            (sab-dom) heuristic.

    Returns:
        int: Planned hardwork minutes.
    """
    if tipo is None:
        weekday = d.weekday()  # 0=mon, 6=sun
        tipo = TipoDia.CURSO if weekday < 5 else TipoDia.LIVRE
    return budget_for_day_type(tipo)


def classify_infracao(realizado_min: int, orcado_min: int) -> tuple[str, int]:
    """Classify the severity of a deviation and return (label, delta).

    Args:
        realizado_min: Actual minutes.
        orcado_min: Planned minutes.

    Returns:
        tuple[str, int]: (label, delta_minutos). The label is one of:
            ``"MUITO_ACIMA"``, ``"ACIMA"``, ``"DENTRO"``, ``"ABAIXO"``,
            ``"MUITO_ABAIXO"``. delta = realizado - orcado.
    """
    delta = realizado_min - orcado_min
    if delta > 60:
        return "MUITO_ACIMA", delta
    if delta > 20:
        return "ACIMA", delta
    if delta >= -20:
        return "DENTRO", delta
    if delta >= -60:
        return "ABAIXO", delta
    return "MUITO_ABAIXO", delta


def productivity_pct(realizado: int, orcado: int) -> float:
    """X-axis of the Cartesian plane: realizado / orçado × 100.

    Args:
        realizado: Actual minutes.
        orcado: Planned minutes.

    Returns:
        float: Productivity percentage in [0, 100+].
    """
    if orcado <= 0:
        return 0.0
    return min(100.0, (realizado / orcado) * 100.0)


def efficiency_pct(foco_min: int, total_min: int) -> float:
    """Y-axis of the Cartesian plane: foco / total × 100.

    Args:
        foco_min: Focused (deep work) minutes.
        total_min: Total tracked minutes for the period.

    Returns:
        float: Efficiency percentage in [0, 100].
    """
    if total_min <= 0:
        return 0.0
    return min(100.0, (foco_min / total_min) * 100.0)


def classify_quadrant(x: float, y: float) -> tuple[str, str, str]:
    """Classify the (X, Y) point in the Cartesian plane.

    Args:
        x: Productivity (0-100).
        y: Efficiency (0-100).

    Returns:
        tuple[str, str, str]: (quadrant_code, label_pt, action_pt).
            Codes: ``"Q1"`` (Excelente), ``"Q2"`` (Otimizado/Pouco),
            ``"Q3"`` (Crítico), ``"Q4"`` (Produtivo/Desotimizado).
    """
    if x >= 50 and y >= 50:
        if x >= 80 and y >= 80:
            return "Q1", "Excelente — manter ritmo, monitorar fadiga", "Manter"
        return "Q1", "Bom — manter ritmo", "Manter"
    if x < 50 and y >= 50:
        return "Q2", "Otimizado mas pouco output", "Aumentar volume de trabalho"
    if x < 50 and y < 50:
        return "Q3", "Crítico — revisar sistema, identificar bloqueios", "Revisão urgente"
    return "Q4", "Produtivo mas precisa otimizar", "Reduzir distrações"


def infer_tipo_dia(d: date, has_school_workout: bool = False) -> TipoDia:
    """Infer the day type from date and context (simple heuristic).

    Args:
        d: Calendar date.
        has_school_workout: Whether the day had a SENAI workout/commitment.

    Returns:
        TipoDia: Inferred type.
    """
    if has_school_workout:
        return TipoDia.CURSO
    weekday = d.weekday()
    return TipoDia.CURSO if weekday < 5 else TipoDia.LIVRE
