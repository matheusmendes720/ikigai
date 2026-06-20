"""Routine logger — manage natural-language logs at boundaries.

This module is the **NL boundary layer** of the operational package.
It complements the numerical time-blocks layer (TimeBlock +
break_calculator + context_switch) by capturing:

* **RoutineLog** — NL descriptions of routine executions
  (entry/exit/core/transitions)
* **AjusteFino** — structured micro-adjustments between blocks

Per the user's clarification (2026-06-07), the package captures
**both numerical records and natural language** at both:

* **Entry routines** (e.g. "Acordar 4h, energia 9/10, prontíssimo")
* **Exit routines** (e.g. "Comi salada e preparei 2 marmitas")
* **Between blocks** (desvios, ajuste finos, deviations)

All operations are pure functions (no I/O, no state).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from operational.entities.ajuste_fino import AjusteFino
from operational.entities.routine import RoutineLog

if TYPE_CHECKING:
    from collections.abc import Iterable

    from operational.enums import Period, RoutineType

__all__ = [
    "RoutineLogger",
    "build_ajuste_fino",
    "build_routine_log",
    "filter_ajustes_finos_by_date",
    "filter_ajustes_finos_by_period",
    "filter_routine_logs_by_date",
    "filter_routine_logs_by_period",
    "total_ajuste_minutos",
]


def build_routine_log(
    routine_log_id: str,
    routine_id: str,
    date_: date,
    period: Period,
    routine_type: RoutineType,
    text: str,
    block_id: str | None = None,
    energia_nivel: int | None = None,
    foco_nivel: int | None = None,
    humor: int | None = None,
    from_pav_defaults: bool = True,
) -> RoutineLog:
    """Factory: create a RoutineLog with sensible defaults.

    Args:
        routine_log_id: UEID for the new log.
        routine_id: Reference to the Routine.
        date_: Date of the routine execution.
        period: The Period enum value.
        routine_type: The RoutineType enum value.
        text: NL description of the routine execution.
        block_id: Optional reference to the TimeBlock.
        energia_nivel: Optional 1-10 energy level.
        foco_nivel: Optional 1-10 focus level.
        humor: Optional 1-5 mood.
        from_pav_defaults: Whether to set created_at to now (UTC) vs caller-supplied.

    Returns:
        A new RoutineLog entity.
    """
    from datetime import UTC, datetime
    if not text or not text.strip():
        msg = "text cannot be empty"
        raise ValueError(msg)
    kwargs: dict[str, object] = {
        "id": routine_log_id,
        "routine_id": routine_id,
        "block_id": block_id,
        "date": date_,
        "period": period,
        "routine_type": routine_type,
        "text": text.strip(),
        "energia_nivel": energia_nivel,
        "foco_nivel": foco_nivel,
        "humor": humor,
    }
    if from_pav_defaults:
        kwargs["created_at"] = datetime.now(UTC)
    return RoutineLog(**kwargs)


def build_ajuste_fino(
    ajuste_fino_id: str,
    date_: date,
    period: Period,
    minutos: int,
    reason: str,
    block_id_before: str | None = None,
    block_id_after: str | None = None,
    from_pav_defaults: bool = True,
) -> AjusteFino:
    """Factory: create an AjusteFino with sensible defaults.

    Args:
        ajuste_fino_id: UEID for the new adjustment.
        date_: Date of the adjustment.
        period: The Period enum value.
        minutos: Signed adjustment in minutes.
        reason: NL explanation.
        block_id_before: Optional reference to the preceding TimeBlock.
        block_id_after: Optional reference to the following TimeBlock.
        from_pav_defaults: Whether to set created_at to now (UTC) vs caller-supplied.

    Returns:
        A new AjusteFino entity.
    """
    from datetime import UTC, datetime
    if not reason or not reason.strip():
        msg = "reason cannot be empty"
        raise ValueError(msg)
    kwargs: dict[str, object] = {
        "id": ajuste_fino_id,
        "date": date_,
        "period": period,
        "minutos": minutos,
        "reason": reason.strip(),
        "block_id_before": block_id_before,
        "block_id_after": block_id_after,
    }
    if from_pav_defaults:
        kwargs["created_at"] = datetime.now(UTC)
    return AjusteFino(**kwargs)


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def filter_routine_logs_by_date(
    logs: Iterable[RoutineLog],
    target_date: date,
) -> list[RoutineLog]:
    """Filter RoutineLog entries to a specific date."""
    return sorted(
        (log for log in logs if log.date == target_date),
        key=lambda log: (log.period.default_start_hour, log.created_at),
    )


def filter_routine_logs_by_period(
    logs: Iterable[RoutineLog],
    period: Period,
) -> list[RoutineLog]:
    """Filter RoutineLog entries to a specific period."""
    return sorted(
        (log for log in logs if log.period == period),
        key=lambda log: (log.date, log.created_at),
    )


def filter_ajustes_finos_by_date(
    ajustes: Iterable[AjusteFino],
    target_date: date,
) -> list[AjusteFino]:
    """Filter AjusteFino entries to a specific date."""
    return sorted(
        (a for a in ajustes if a.date == target_date),
        key=lambda a: (a.period.default_start_hour, a.created_at),
    )


def filter_ajustes_finos_by_period(
    ajustes: Iterable[AjusteFino],
    period: Period,
) -> list[AjusteFino]:
    """Filter AjusteFino entries to a specific period."""
    return sorted(
        (a for a in ajustes if a.period == period),
        key=lambda a: (a.date, a.created_at),
    )


def total_ajuste_minutos(ajustes: Iterable[AjusteFino]) -> int:
    """Sum the signed minutos of all AjusteFino entries.

    Used by the break_calculator to integrate adjustments:
        adjusted_net_rest = net_rest + total_ajuste_minutos
    """
    return sum(a.minutos for a in ajustes)


# ---------------------------------------------------------------------------
# Stateful container
# ---------------------------------------------------------------------------


@dataclass
class RoutineLogger:
    """Stateless facade for routine logging operations.

    Holds collections of RoutineLog + AjusteFino + related
    TimeBlocks (or UEIDs) and exposes query helpers.
    """

    routine_logs: list[RoutineLog]
    ajustes_finos: list[AjusteFino]

    def logs_on(self, target_date: date) -> list[RoutineLog]:
        """All RoutineLog entries on a given date."""
        return filter_routine_logs_by_date(self.routine_logs, target_date)

    def logs_in(self, period: Period) -> list[RoutineLog]:
        """All RoutineLog entries in a given period."""
        return filter_routine_logs_by_period(self.routine_logs, period)

    def ajustes_on(self, target_date: date) -> list[AjusteFino]:
        """All AjusteFino entries on a given date."""
        return filter_ajustes_finos_by_date(self.ajustes_finos, target_date)

    def ajustes_in(self, period: Period) -> list[AjusteFino]:
        """All AjusteFino entries in a given period."""
        return filter_ajustes_finos_by_period(self.ajustes_finos, period)

    def net_adjustment_for_period(self, period: Period) -> int:
        """Sum of all AjusteFino.minutos in a given period.

        Returns the net adjustment (positive = added time, negative = removed).
        """
        return total_ajuste_minutos(self.ajustes_in(period))
