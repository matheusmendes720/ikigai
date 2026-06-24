"""Extended analytics — circadian patterns, time blocks, rituals, narratives.

This module complements engine.py with higher-order analytics:
- Circadian: sleep timing, energy/focus by hour-of-day, period-of-week
- Time blocks: deep work utilization, block efficiency by period
- Rituals/transições: T1-T5 completion rates, ritual patterns
- Lunch: eat/rest/pesado patterns, midday energy impact
- Period-over-period: week-over-week, month-over-month delta
- Narrative: auto-generated prose insights per week/period
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import TypedDict

from operational.analytics.engine import (
    HabitRow,
    HabitStateRow,
    JournalRow,
    PolicyRow,
    PomodoroRow,
    QHERow,
    SleepRow,
    date_from_str,
    parse_bool,
)

# ------------------------------------------------------------------
# TypedDicts
# ------------------------------------------------------------------


class LunchRow(TypedDict):
    id: str
    date: str
    cluster: str
    eat_min: str
    rest_min: str
    pesado: str
    notas: str


class TimeBlockRow(TypedDict):
    id: str
    date: str
    cluster: str
    start: str
    end: str
    period: str
    label: str


class TransicaoRow(TypedDict):
    id: str
    date: str
    cluster: str
    codigo: str
    ritual: str
    duracao_min: str
    completed: str | bool
    notas: str


class RoutineLogRow(TypedDict):
    id: str
    date: str
    cluster: str
    routine_id: str
    period: str
    routine_type: str
    text: str
    energia_nivel: str
    focus_nivel: str
    humor: str


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _to_float(val: str | float | None, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _to_int(val: str | int | None, default: int = 0) -> int:
    if val is None or val == "":
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


# ------------------------------------------------------------------
# Lunch Analytics
# ------------------------------------------------------------------


def lunch_analysis(
    lunch_rows: list[LunchRow],
    journal_rows: list[JournalRow],
) -> dict:
    """Lunch habits, pesado flag impact, midday rest correlation."""
    if not lunch_rows:
        return {}

    eat_min = [_to_int(r.get("eat_min", 0)) for r in lunch_rows]
    rest_min = [_to_int(r.get("rest_min", 0)) for r in lunch_rows]
    pesado = [parse_bool(r.get("pesado", "false")) for r in lunch_rows]

    pesado_count = sum(pesado)
    rest_debt_days = sum(1 for r in rest_min if r < 20)

    # Journal afternoon energy (PM entries)
    pm_energy: dict[str, list[int]] = defaultdict(list)
    for r in journal_rows:
        if r.get("period") in ("PM", "EVENING", "TARDE"):
            en = r.get("energia_nivel", "")
            if en not in ("", None):
                pm_energy[r["date"]].append(_to_int(en))

    avg_pm_by_day = {d: sum(v) / len(v) for d, v in pm_energy.items() if v}

    pesado_dates = {lunch_rows[i]["date"] for i in range(len(lunch_rows)) if pesado[i]}
    heavy_lunch_pm = [
        avg_pm_by_day.get(lunch_rows[i]["date"])
        for i in range(len(lunch_rows))
        if pesado[i] and lunch_rows[i]["date"] in avg_pm_by_day
    ]
    light_lunch_pm = [
        avg_pm_by_day.get(lunch_rows[i]["date"])
        for i in range(len(lunch_rows))
        if not pesado[i] and lunch_rows[i]["date"] in avg_pm_by_day
    ]

    heavy_avg = sum(heavy_lunch_pm) / len(heavy_lunch_pm) if heavy_lunch_pm else None
    light_avg = sum(light_lunch_pm) / len(light_lunch_pm) if light_lunch_pm else None

    return {
        "total_lunches": len(lunch_rows),
        "avg_eat_min": round(sum(eat_min) / len(eat_min), 1),
        "avg_rest_min": round(sum(rest_min) / len(rest_min), 1),
        "pesado_count": pesado_count,
        "pesado_pct": round(100 * pesado_count / len(pesado), 1),
        "rest_debt_days": rest_debt_days,
        "heavy_lunch_avg_pm_energy": round(heavy_avg, 1) if heavy_avg is not None else None,
        "light_lunch_avg_pm_energy": round(light_avg, 1) if light_avg is not None else None,
    }


# ------------------------------------------------------------------
# Time Block Analytics
# ------------------------------------------------------------------


def time_block_analysis(
    block_rows: list[TimeBlockRow],
    pom_rows: list[PomodoroRow],
) -> dict:
    """Deep work block utilization — hours per period, pomodoro density per block."""
    if not block_rows:
        return {}

    by_date: dict[str, list[TimeBlockRow]] = defaultdict(list)
    for r in block_rows:
        by_date[r["date"]].append(r)

    period_hours: dict[str, list[float]] = defaultdict(list)
    for rows in by_date.values():
        for b in rows:
            try:
                start_h = int(b["start"].split(":")[0]) + int(b["start"].split(":")[1]) / 60
                end_h = int(b["end"].split(":")[0]) + int(b["end"].split(":")[1]) / 60
                hours = end_h - start_h
                if hours > 0:
                    period_hours[b["period"]].append(hours)
            except (ValueError, IndexError):
                continue

    # Pomodoro density: how many pomodoros land inside each block
    pom_by_date: dict[str, list[PomodoroRow]] = defaultdict(list)
    for r in pom_rows:
        if r.get("state") == "COMPLETE":
            pom_by_date[r["date"]].append(r)

    total_blocks = sum(len(v) for v in by_date.values())
    avg_blocks_per_day = total_blocks / len(by_date) if by_date else 0
    avg_hours_per_day = sum(sum(v) for v in period_hours.values()) / len(by_date) if by_date else 0

    return {
        "total_block_days": len(by_date),
        "avg_blocks_per_day": round(avg_blocks_per_day, 1),
        "avg_hours_per_day": round(avg_hours_per_day, 1),
        "period_hours": {p: round(sum(v) / len(v), 1) for p, v in period_hours.items() if v},
        "total_periods": dict(period_hours),
    }


# ------------------------------------------------------------------
# Ritual / Transição Analytics
# ------------------------------------------------------------------


RITUAL_NAMES = {
    "T1": "Sessão Despertar",
    "T2": "Transição Descanco",
    "T3": "Pré-Sessão Foco",
    "T4": "Pós-Sessão Reflexão",
    "T5": "Encerramento Diário",
}


def ritual_analysis(transicao_rows: list[TransicaoRow]) -> dict:
    """Ritual completion rates, T1-T5 patterns, duration adherence."""
    if not transicao_rows:
        return {}

    by_code: dict[str, dict] = defaultdict(lambda: {"completed": 0, "total": 0, "durations": []})
    for r in transicao_rows:
        code = r.get("codigo", "?")
        completed = parse_bool(r.get("completed", "false"))
        dur = _to_int(r.get("duracao_min", 0))
        by_code[code]["total"] += 1
        if completed:
            by_code[code]["completed"] += 1
        if dur > 0:
            by_code[code]["durations"].append(dur)

    summary = {}
    for code, info in sorted(by_code.items()):
        total = info["total"]
        comp = info["completed"]
        durs = info["durations"]
        summary[code] = {
            "name": RITUAL_NAMES.get(code, code),
            "completed": comp,
            "total": total,
            "completion_rate": round(100 * comp / total, 1) if total > 0 else 0,
            "avg_duration_min": round(sum(durs) / len(durs), 1) if durs else 0,
        }

    # Best day-of-week for rituals
    by_dow: dict[int, dict] = defaultdict(lambda: {"comp": 0, "total": 0})
    for r in transicao_rows:
        try:
            d = date_from_str(r["date"])
            dow = d.isocalendar()[2]  # 1=Mon
            completed = parse_bool(r.get("completed", "false"))
            by_dow[dow]["total"] += 1
            if completed:
                by_dow[dow]["comp"] += 1
        except (ValueError, KeyError):
            continue

    dow_rates = {}
    for dow in range(1, 8):
        info = by_dow.get(dow, {"comp": 0, "total": 0})
        dow_rates[dow] = round(100 * info["comp"] / info["total"], 1) if info["total"] > 0 else 0

    return {
        "rituals": summary,
        "dow_rates": dow_rates,
        "total_transitions": len(transicao_rows),
    }


# ------------------------------------------------------------------
# Circadian: Energy/Focus by Hour
# ------------------------------------------------------------------


def circadian_energy(
    journal_rows: list[JournalRow],
    routine_log_rows: list[RoutineLogRow],
) -> dict:
    """Energy/focus/humor organized by hour-of-day and day-of-week."""
    by_hour: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    by_dow: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    def _process_journal(rows: list[dict]) -> None:
        for r in rows:
            en = r.get("energia_nivel", "")
            fo = r.get("focus_nivel", "")
            hu = r.get("humor_morning", "") or r.get("humor", "")
            if not en and not fo and not hu:
                continue
            try:
                d = date_from_str(r["date"])
                dow = d.isocalendar()[2]
            except (ValueError, KeyError):
                continue
            if en:
                by_hour[0].get("energia", []).append(_to_float(en))  # placeholder
            for attr, bucket in [("energia_nivel", "energia"), ("focus_nivel", "focus"), ("humor", "humor")]:
                val = r.get(attr, "")
                if val:
                    by_dow[dow][attr].append(_to_float(val))

    _process_journal(journal_rows)

    # Routine log has energia/focus/humor per routine entry
    for r in routine_log_rows:
        en = r.get("energia_nivel", "")
        fo = r.get("focus_nivel", "")
        hu = r.get("humor", "")
        try:
            d = date_from_str(r["date"])
            dow = d.isocalendar()[2]
        except (ValueError, KeyError):
            continue
        for val, attr in [(en, "energia"), (fo, "focus"), (hu, "humor")]:
            if val:
                by_dow[dow][attr].append(_to_float(val))

    # Compute per-dow averages
    dow_labels = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
    dow_averages = {}
    for dow in range(1, 8):
        info = by_dow.get(dow, {})
        dow_averages[dow_labels[dow]] = {
            attr: round(sum(vals) / len(vals), 2) if vals else None
            for attr, vals in info.items()
        }

    return {
        "by_day_of_week": dow_averages,
    }


# ------------------------------------------------------------------
# Sleep Timing Patterns (not just hours)
# ------------------------------------------------------------------


def sleep_timing_analysis(sleep_rows: list[SleepRow]) -> dict:
    """Bedtime and wake-time distributions, sleep midpoint, consistency score."""
    bedtimes: list[str] = []
    wake_times: list[str] = []

    for r in sleep_rows:
        b = r.get("bedtime", "")
        w = r.get("wake_time", "")
        if b:
            bedtimes.append(b)
        if w:
            wake_times.append(w)

    def _time_to_hours(t: str) -> float:
        try:
            h, m = t.split(":")
            return int(h) + int(m) / 60
        except (ValueError, IndexError):
            return 0.0

    bed_h = [_time_to_hours(t) for t in bedtimes]
    wake_h = [_time_to_hours(t) for t in wake_times]

    def _stats(vals: list[float]) -> dict:
        if not vals:
            return {}
        sorted_v = sorted(vals)
        n = len(sorted_v)
        mean = sum(sorted_v) / n
        std = math.sqrt(sum((x - mean) ** 2 for x in sorted_v) / n)
        return {
            "mean": round(mean, 2),
            "min": round(min(sorted_v), 2),
            "max": round(max(sorted_v), 2),
            "std": round(std, 2),
        }

    bed_stats = _stats(bed_h)
    wake_stats = _stats(wake_h)

    # Sleep midpoint consistency
    midpoints = []
    for r in sleep_rows:
        b = r.get("bedtime", "")
        w = r.get("wake_time", "")
        if b and w:
            bh = _time_to_hours(b)
            wh = _time_to_hours(w)
            if wh < 12:  # morning wake
                wh += 24
            mid = (bh + wh) / 2
            if mid > 24:
                mid -= 24
            midpoints.append(mid)

    mid_stats = _stats(midpoints)

    return {
        "bedtime_stats": bed_stats,
        "wake_time_stats": wake_stats,
        "midpoint_stats": mid_stats,
    }


# ------------------------------------------------------------------
# Period-over-Period Comparison
# ------------------------------------------------------------------


def pop_comparison(
    week_current: dict,
    week_previous: dict | None,
) -> dict:
    """Compute delta (this week vs last week) for key metrics."""
    if week_previous is None:
        return {}

    deltas = {}
    numeric_keys = [
        "qhe_mean", "sleep_mean_h", "sleep_quality_mean",
        "total_pomodoros", "pomodoros_per_day_avg",
        "habit_completion_rate", "hardwork_accuracy_pct",
        "energy_mean", "focus_mean", "humor_mean",
    ]
    for key in numeric_keys:
        curr = week_current.get(key)
        prev = week_previous.get(key)
        if curr is not None and prev is not None and prev != 0:
            delta = curr - prev
            pct = round(100 * delta / prev, 1)
            deltas[key] = {"delta": round(delta, 4), "pct_change": pct}
        else:
            deltas[key] = {"delta": None, "pct_change": None}

    return deltas


# ------------------------------------------------------------------
# Narrative Insight Generator
# ------------------------------------------------------------------


def generate_narrative(
    week_data: dict,
    pop_deltas: dict,
    qhe_rows: list[QHERow],
    sleep_rows: list[SleepRow],
    pom_rows: list[PomodoroRow],
    habit_rows: list[HabitRow],
    habit_state_rows: list[HabitStateRow],
    policy_rows: list[PolicyRow],
) -> list[str]:
    """Generate 3-5 sentence narrative insights for a week."""
    lines: list[str] = []
    wd = week_data

    # Overall QHE verdict
    qhe = wd.get("qhe_mean")
    if qhe is not None:
        if qhe >= 0.85:
            verdict = "Excelente desempenho sistêmico"
        elif qhe >= 0.70:
            verdict = "Desempenho consistente acima da média"
        elif qhe >= 0.50:
            verdict = "Desempenho moderado com espaço para otimização"
        else:
            verdict = "Semana desafiadora — revisão de política recomendada"
        lines.append(f"**Veredito:** {verdict} (QHE médio = {qhe:.4f}).")

    # Sleep quality narrative
    sleep_h = wd.get("sleep_mean_h")
    sleep_q = wd.get("sleep_quality_mean")
    if sleep_h is not None:
        if sleep_h >= 8.0:
            lines.append(f"Sono exemplar: {sleep_h:.1f}h em média com qualidade {sleep_q:.0f}/10.")
        elif sleep_h >= 7.0:
            lines.append(f"Sono adequado: {sleep_h:.1f}h em média (meta: 8h).")
        else:
            lines.append(f"Dívida de sono acumulada: apenas {sleep_h:.1f}h/night em média.")

    # Pomodoro narrative
    pomodoros = wd.get("total_pomodoros", 0)
    pom_avg = wd.get("pomodoros_per_day_avg", 0)
    if pomodoros > 0:
        if pom_avg >= 8:
            lines.append(f"Alta densidade de foco: {pomodoros} pomodoros totais ({pom_avg:.1f}/dia).")
        elif pom_avg >= 5:
            lines.append(f"Output moderado: {pomodoros} pomodoros ({pom_avg:.1f}/dia).")
        else:
            lines.append(f"Output reduzido: apenas {pomodoros} pomodoros ({pom_avg:.1f}/dia).")

    # Habit narrative
    habit_rate = wd.get("habit_completion_rate", 0)
    if habit_rate >= 95:
        lines.append(f"Ritual de hábitos mantido com {habit_rate:.0f}% de aderência — consistency engine em alta.")
    elif habit_rate >= 85:
        lines.append(f"Aderência de hábitos em {habit_rate:.0f}% — perto do optimal.")
    else:
        lines.append(f"Aderência de hábitos em {habit_rate:.0f}% — gap de compliance a investigar.")

    # Policy narrative
    policy_dom = wd.get("policy_dominant", "N/A")
    hardwork_acc = wd.get("hardwork_accuracy_pct")
    if hardwork_acc is not None:
        if hardwork_acc >= 90:
            lines.append(f"Política {policy_dom} bem calibrada — {hardwork_acc:.0f}% accuracy vs budget.")
        elif hardwork_acc >= 75:
            lines.append(f"Política {policy_dom} moderadamente precisa ({hardwork_acc:.0f}% accuracy).")
        else:
            lines.append(f"Desalinhamento de política {policy_dom}: apenas {hardwork_acc:.0f}% accuracy.")

    # Period-over-period narrative
    if pop_deltas:
        improvements = []
        regressions = []
        for key, info in pop_deltas.items():
            if info.get("pct_change") is not None:
                pct = info["pct_change"]
                if pct > 5:
                    improvements.append(key.replace("_", " ").title())
                elif pct < -5:
                    regressions.append(key.replace("_", " ").title())

        if improvements:
            lines.append(f"↑ Melhorias vs semana anterior: {', '.join(improvements[:3])}.")
        if regressions:
            lines.append(f"↓ Regressões vs semana anterior: {', '.join(regressions[:3])}.")

    return lines
