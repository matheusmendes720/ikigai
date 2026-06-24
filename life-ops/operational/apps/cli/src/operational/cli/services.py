"""Core data services — pure functions, zero Rich/Typer dependencies.

Each function here returns a plain Python dict/dataclass that the UI
layer can then format. This separation makes the data layer
testable in isolation and keeps the UI layer free of business rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from typing import Any

from operational.cli.state import (
    ajustes_finos,
    daily_reflections,
    day_contexts,
    journals,
    lunch_records,
    pomodoros,
    routine_logs,
    routines,
    sleep_records,
    time_blocks,
    transicoes,
)
from operational.core.budget import (
    budget_for_date,
    classify_quadrant,
    efficiency_pct,
    productivity_pct,
)
from operational.core.exceptions import (
    DataInvalidaError,
    FaltaDadosError,
    LimitePomodoroExcedidoError,
    RepositorioVazioError,
    ValorForaRangeError,
)
from operational.enums import (
    Period,
    TipoDia,
)

# ---------------------------------------------------------------------------
# Plain data containers (UI receives these; no Pydantic leakage)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SleepSnapshot:
    bedtime: time | None
    wake_time: time | None
    duration_hours: float | None
    quality: int | None
    notes: str = ""


@dataclass(frozen=True)
class DaySnapshot:
    """One day of operational data, normalized for UI."""

    date: date
    tipo_dia: TipoDia
    sleep: SleepSnapshot
    wake_hour: int | None
    sleep_hour: int | None
    workout_done: bool
    workout_minutes: int
    meditacao_done: bool
    meditacao_minutes: int
    lunch_eat_min: int
    lunch_rest_min: int
    lunch_pesado: bool
    jantar_antes_18: bool
    luz_azul_apos_18: bool
    n_transicoes_completas: int
    n_transicoes_total: int
    n_blocks: int
    total_block_minutes: int
    hardwork_orcado_min: int
    hardwork_realizado_min: int
    pomodoros_meta: int
    pomodoros_done: int
    n_pomodoros: int
    energia: int | None
    foco: int | None
    humor_morning: int | None
    humor_evening: int | None
    desvios: list[str] = field(default_factory=list)
    licoes: list[str] = field(default_factory=list)
    ajustes: list[str] = field(default_factory=list)
    big_win: str = ""
    parar_de_fazer: list[str] = field(default_factory=list)
    repetir: list[str] = field(default_factory=list)
    deu_certo: list[str] = field(default_factory=list)
    deu_errado: list[str] = field(default_factory=list)
    maior_aprendizado: str = ""


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _to_period(period_value: Any) -> Period | None:
    if isinstance(period_value, Period):
        return period_value
    if isinstance(period_value, str):
        try:
            return Period(period_value)
        except ValueError:
            return None
    return None


def _to_tipo_dia(value: Any) -> TipoDia:
    if isinstance(value, TipoDia):
        return value
    if isinstance(value, str):
        try:
            return TipoDia(value)
        except ValueError:
            return TipoDia.CURSO
    return TipoDia.CURSO


def get_day_snapshot(d: date) -> DaySnapshot:
    """Build a complete DaySnapshot for a given date.

    Pure data: returns a frozen dataclass. No Rich. No console.
    """
    # Sleep
    sleep_obj = next((s for s in sleep_records.list() if s.date == d), None)
    sleep = SleepSnapshot(
        bedtime=sleep_obj.bedtime if sleep_obj else None,
        wake_time=sleep_obj.wake_time if sleep_obj else None,
        duration_hours=sleep_obj.duration_hours if sleep_obj else None,
        quality=sleep_obj.quality_score if sleep_obj else None,
        notes=sleep_obj.notes if sleep_obj else "",
    )

    # DayContext (or inferred)
    ctx = next((c for c in day_contexts.list() if c.date == d), None)
    if ctx:
        tipo_dia = ctx.tipo_dia
        orcado = ctx.hardwork_orcado_min
        pomodoros_meta = ctx.pomodoros_meta
    else:
        tipo_dia = _to_tipo_dia(_infer_tipo_dia(d))
        orcado = budget_for_date(d, tipo_dia)
        pomodoros_meta = 0

    # Blocks / pomodoros for the day
    blocks_today = [b for b in time_blocks.list() if b.start.date() == d]
    total_block_minutes = sum(
        int((b.end - b.start).total_seconds() // 60) for b in blocks_today
    )
    day_pomodoros = [p for p in pomodoros.list() if p.started_at.date() == d]
    n_pomodoros = sum(
        1 for p in day_pomodoros if getattr(p, "state", None) and "COMPLETE" in str(p.state)
    )
    n_transicoes = len([t for t in transicoes.list() if t.date == d and t.completed])

    # Routine logs for workout/meditation detection
    day_logs = [l for l in routine_logs.list() if l.date == d]
    routines_by_id = {str(r.id): r for r in routines.list()}

    workout_done = False
    workout_minutes = 0
    meditacao_done = False
    meditacao_minutes = 0
    for log in day_logs:
        r = routines_by_id.get(str(log.routine_id))
        if r is None:
            continue
        name = (r.name or "").lower()
        if "workout" in name or "academia" in name or "corrida" in name or "treino" in name or "calistenia" in name:
            workout_done = True
            # rough estimate
            try:
                dur = int((r.end_time.hour - r.start_time.hour) * 60 + (r.end_time.minute - r.start_time.minute))
                workout_minutes = max(workout_minutes, dur)
            except Exception:
                pass
        if "medita" in name:
            meditacao_done = True
            try:
                dur = int((r.end_time.hour - r.start_time.hour) * 60 + (r.end_time.minute - r.start_time.minute))
                meditacao_minutes = max(meditacao_minutes, dur)
            except Exception:
                pass

    # Lunch
    lunch_obj = next((l for l in lunch_records.list() if l.date == d), None)
    if lunch_obj:
        lunch_eat, lunch_rest, lunch_pesado = lunch_obj.eat_min, lunch_obj.rest_min, lunch_obj.pesado
    else:
        lunch_eat, lunch_rest, lunch_pesado = 5, 30, False

    # Journal
    j = next((jj for jj in journals.list() if jj.date == d), None)
    if j:
        energia = j.energia_nivel
        foco = j.foco_nivel
        humor_morning = j.humor_morning
        humor_evening = j.humor_evening
        desvios = list(j.desvios)
        licoes = list(j.licoes_aprendidas)
    else:
        energia = foco = humor_morning = humor_evening = None
        desvios = []
        licoes = []

    # Adjustments
    ajustes = [a.reason for a in ajustes_finos.list() if a.date == d]

    # Reflection
    rfl = next((r for r in daily_reflections.list() if r.date == d), None)
    if rfl:
        big_win = rfl.big_win
        parar = list(rfl.parar_de_fazer)
        repetir_l = list(rfl.repetir)
        deu_certo_l = list(rfl.deu_certo)
        deu_errado_l = list(rfl.deu_errado)
        maior_aprendizado = rfl.maior_aprendizado
    else:
        big_win = ""
        parar = []
        repetir_l = []
        deu_certo_l = []
        deu_errado_l = []
        maior_aprendizado = ""

    return DaySnapshot(
        date=d,
        tipo_dia=tipo_dia,
        sleep=sleep,
        wake_hour=sleep.wake_time.hour if sleep.wake_time else None,
        sleep_hour=sleep.bedtime.hour if sleep.bedtime else None,
        workout_done=workout_done,
        workout_minutes=workout_minutes,
        meditacao_done=meditacao_done,
        meditacao_minutes=meditacao_minutes,
        lunch_eat_min=lunch_eat,
        lunch_rest_min=lunch_rest,
        lunch_pesado=lunch_pesado,
        jantar_antes_18=False,  # not modeled yet
        luz_azul_apos_18=False,
        n_transicoes_completas=n_transicoes,
        n_transicoes_total=9,
        n_blocks=len(blocks_today),
        total_block_minutes=total_block_minutes,
        hardwork_orcado_min=orcado,
        hardwork_realizado_min=total_block_minutes,
        pomodoros_meta=pomodoros_meta,
        pomodoros_done=n_pomodoros,
        n_pomodoros=n_pomodoros,
        energia=energia,
        foco=foco,
        humor_morning=humor_morning,
        humor_evening=humor_evening,
        desvios=desvios,
        licoes=licoes,
        ajustes=ajustes,
        big_win=big_win,
        parar_de_fazer=parar,
        repetir=repetir_l,
        deu_certo=deu_certo_l,
        deu_errado=deu_errado_l,
        maior_aprendizado=maior_aprendizado,
    )


def _infer_tipo_dia(d: date) -> TipoDia:
    """Infer TipoDia from weekday if no DayContext exists."""
    if d.weekday() < 5:
        return TipoDia.CURSO
    return TipoDia.LIVRE


# ---------------------------------------------------------------------------
# Validators (raise domain exceptions)
# ---------------------------------------------------------------------------


def validate_pomodoro_count(n: int, *, max_limite: int = 24) -> int:
    """Validate a pomodoro count, raising a domain exception if absurd.

    Args:
        n: Number of pomodoros to validate.
        max_limite: Physiological maximum per day (default 24).

    Returns:
        The validated count (same as input).

    Raises:
        ValorForaRangeError: If n is negative.
        LimitePomodoroExcedidoError: If n > max_limite.
    """
    if n < 0:
        raise ValorForaRangeError(
            campo="pomodoros", valor=n, minimo=0, maximo=max_limite,
        )
    if n > max_limite:
        raise LimitePomodoroExcedidoError(quantidade=n, max_limite=max_limite)
    return n


def parse_iso_date(date_str: str) -> date:
    """Parse a YYYY-MM-DD string, raising a clean domain error on failure.

    Raises:
        DataInvalidaError: If the string is not a valid ISO date.
    """
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError) as exc:
        raise DataInvalidaError(
            data_fornecida=str(date_str),
            motivo="formato deve ser AAAA-MM-DD",
        ) from exc


def require_sleep_record(d: date):
    """Return the sleep record for a date, or raise RepositorioVazioError.

    Raises:
        RepositorioVazioError: If no sleep record exists for that date.
    """
    sleep_obj = next((s for s in sleep_records.list() if s.date == d), None)
    if sleep_obj is None:
        raise RepositorioVazioError(entidade="sleep_record", data=d)
    return sleep_obj


def require_day_context(d: date):
    """Return the DayContext for a date, or raise RepositorioVazioError.

    Raises:
        RepositorioVazioError: If no DayContext exists.
    """
    ctx = next((c for c in day_contexts.list() if c.date == d), None)
    if ctx is None:
        raise RepositorioVazioError(entidade="day_context", data=d)
    return ctx


def validate_required_fields(dados: dict, required: list[str], contexto: str = "") -> None:
    """Validate that a dict has all required fields.

    Raises:
        FaltaDadosError: If any required field is missing.
    """
    ausentes = [k for k in required if k not in dados or dados.get(k) is None]
    if ausentes:
        raise FaltaDadosError(campos_ausentes=ausentes, contexto=contexto)


def distribute_pomodoros_across_sessions(total: int) -> tuple[int, int, int]:
    """Distribute total pomodoros across 3 sessions (max 4 each)."""
    s1 = min(4, total)
    remaining = total - s1
    s2 = min(4, remaining)
    s3 = max(0, min(4, remaining - s2))
    return s1, s2, s3


def compute_day_quadrant(snap: DaySnapshot) -> tuple[str, float, float]:
    """Return (quadrant_code, x, y) for the day's Cartesian position."""
    x = productivity_pct(snap.hardwork_realizado_min, snap.hardwork_orcado_min)
    y = efficiency_pct(snap.hardwork_realizado_min, snap.hardwork_realizado_min + 60)
    code, _, _ = classify_quadrant(x, y)
    return code, x, y


__all__ = [
    "DaySnapshot",
    "SleepSnapshot",
    "compute_day_quadrant",
    "distribute_pomodoros_across_sessions",
    "get_day_snapshot",
    "parse_iso_date",
    "require_day_context",
    "require_sleep_record",
    "validate_pomodoro_count",
    "validate_required_fields",
]
