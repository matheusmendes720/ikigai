"""Operational Analytics Engine — 180-day data warehouse.

This module provides pure-computation analytics over the 15-entity CSV dataset.
All functions take raw CSV row lists (loaded by csv.DictReader) and return
typed dicts / dataclasses suitable for rendering by any output layer (Rich,
Markdown, JSON, HTTP, etc.).

Design principles
----------------
* **Pure functions** — no I/O, no side-effects, deterministic.
* **Typed inputs** — list[dict] from csv.DictReader; each loader knows its schema.
* **Hierarchical** — summary → weekly → daily.
* **Gap-aware** — missing days are flagged, not interpolated silently.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TypedDict

# ------------------------------------------------------------------
# Schema TypedDicts
# ------------------------------------------------------------------


class HabitRow(TypedDict):
    id: str
    name: str
    category: str
    resistance: str
    lambda_learning: str
    weight_in_qhe: str
    frequency: str
    created_at: str
    archived: str


class HabitStateRow(TypedDict):
    id: str
    date: str
    cluster: str
    habit_id: str
    completed: str
    streak_current: str
    streak_broken_count: str
    effort_minutes: str


class QHERow(TypedDict):
    id: str
    date: str
    cluster: str
    habit_avg: str
    consistency: str
    streak_bonus: str
    energy_ratio: str
    qhe: str
    regime_predicted: str


class SleepRow(TypedDict):
    id: str
    date: str
    cluster: str
    bedtime: str
    wake_time: str
    sleep_hours: str
    quality_score: str
    deep_sleep_pct: str
    rem_sleep_pct: str
    interruptions: str
    notes: str
    source: str


class PomodoroRow(TypedDict):
    id: str
    date: str
    cluster: str
    round_number: str
    state: str
    started_at: str
    completed_at: str
    paused_duration_seconds: str


class JournalRow(TypedDict):
    id: str
    date: str
    cluster: str
    period: str
    entry_text: str
    energia_nivel: str
    focus_nivel: str
    humor_morning: str
    humor_evening: str
    pomodoros_completos: str
    periods_covered: str
    desvios: str
    licoes_aprendidas: str


class PolicyRow(TypedDict):
    id: str
    date: str
    cluster: str
    state: str
    severity: str
    rationale: str
    days_in_state: str
    previous_state: str
    qhe_input: str
    infraction_count: str
    hardwork_budget_hours: str
    max_pomodoros_per_day: str
    sleep_target_hours: str


class DayContextRow(TypedDict):
    id: str
    date: str
    cluster: str
    tipo_dia: str
    hardwork_orcado_min: str
    hardwork_realizado_min: str
    pomodoros_meta: str
    pomodoros_realizados: str
    tem_curso: str
    tem_deadline: str
    observacoes: str


class TransicaoRow(TypedDict):
    id: str
    date: str
    cluster: str
    codigo: str
    ritual: str
    duracao_min: str
    completed: str
    notas: str


class DailyReflectionRow(TypedDict):
    id: str
    date: str
    cluster: str
    parar_de_fazer: str
    repetir: str
    sempre_fazer: str
    big_win: str
    deu_certo: str
    deu_errado: str
    maior_aprendizado: str
    ajustes_para_amanha: str
    estado_geral: str


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
# CSV Loaders
# ------------------------------------------------------------------


def load_csv(name: str, csv_dir: Path | None = None) -> list[dict]:
    def _default_csv_dir() -> Path:
        """Locate the 6month CSV directory by traversing up from this file."""
        current = Path(__file__).resolve().parent
        for _ in range(10):
            candidate = current / "datasets" / "6month" / "csv"
            if candidate.is_dir():
                return candidate
            if current == current.parent:
                break
            current = current.parent
        return Path(__file__).parent / "datasets" / "6month" / "csv"

    if csv_dir is None:
        csv_dir = _default_csv_dir()
    fpath = csv_dir / f"{name}.csv"
    with fpath.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def date_from_str(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()  # noqa: DTZ007


def parse_bool(s: str | bool) -> bool:  # noqa: FBT001
    if isinstance(s, bool):
        return s
    return s.strip().lower() in ("true", "1", "yes")


# ------------------------------------------------------------------
# Date utilities
# ------------------------------------------------------------------

_DATE_COLS = {"date", "bedtime"}
_BOOL_COLS = {"completed", "tem_curso", "tem_deadline", "pesado"}
_FLOAT_COLS = {
    "sleep_hours",
    "deep_sleep_pct",
    "rem_sleep_pct",
    "habit_avg",
    "consistency",
    "streak_bonus",
    "energy_ratio",
    "qhe",
    "hardwork_orcado_min",
    "hardwork_realizado_min",
    "duracao_min",
    "effort_minutes",
}
_INT_COLS = {
    "streak_current",
    "streak_broken_count",
    "interruptions",
    "round_number",
    "pomodoros_completos",
    "pomodoros_realizados",
    "days_in_state",
    "infraction_count",
    "energia_nivel",
    "focus_nivel",
    "humor_morning",
    "humor_evening",
    "quality_score",
    "eat_min",
    "rest_min",
}
_FLOAT_COLS = {
    "sleep_hours",
    "deep_sleep_pct",
    "rem_sleep_pct",
    "habit_avg",
    "consistency",
    "streak_bonus",
    "energy_ratio",
    "qhe",
    "hardwork_orcado_min",
    "hardwork_realizado_min",
    "duracao_min",
    "effort_minutes",
    "hardwork_budget_hours",
    "max_pomodoros_per_day",
    "sleep_target_hours",
    "pomodoros_meta",
}


def coerce_row(row: dict) -> dict:
    """Coerce string CSV values to their correct types."""
    out = dict(row)
    for col in _BOOL_COLS:
        if col in out:
            out[col] = parse_bool(out[col])
    for col in _FLOAT_COLS:
        if col in out and out[col] != "":
            out[col] = float(out[col])
    for col in _INT_COLS:
        if col in out and out[col] != "":
            out[col] = int(out[col])
    return out


def weeks_in_range(start: date, end: date) -> list[tuple[date, date]]:
    """Return [(week_start, week_end), ...] covering the date range."""
    # ISO week start (Monday)
    current = start - timedelta(days=start.weekday())
    weeks = []
    while current <= end:
        week_end = current + timedelta(days=6)
        weeks.append((current, min(week_end, end)))
        current += timedelta(weeks=1)
    return weeks


# ------------------------------------------------------------------
# 1. QHE Analytics
# ------------------------------------------------------------------


def qhe_time_series(rows: list[QHERow]) -> list[dict]:
    """Chronological QHE with rolling 7-day and 30-day averages."""
    sorted_rows = sorted(rows, key=lambda r: r["date"])
    result = []
    qhe_vals = []
    for r in sorted_rows:
        qhe = float(r["qhe"])
        habit_avg = float(r["habit_avg"])
        consistency = float(r["consistency"])
        streak_bonus = float(r["streak_bonus"])
        energy_ratio = float(r["energy_ratio"])
        qhe_vals.append(qhe)
        roll7 = sum(qhe_vals[-7:]) / min(len(qhe_vals), 7)
        roll30 = sum(qhe_vals[-30:]) / min(len(qhe_vals), 30)
        result.append(
            {
                "date": r["date"],
                "qhe": round(qhe, 4),
                "habit_avg": round(habit_avg, 4),
                "consistency": round(consistency, 4),
                "streak_bonus": round(streak_bonus, 4),
                "energy_ratio": round(energy_ratio, 4),
                "regime": r["regime_predicted"],
                "roll7": round(roll7, 4),
                "roll30": round(roll30, 4),
            }
        )
    return result


def qhe_regime_distribution(rows: list[QHERow]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r["regime_predicted"]] += 1
    return dict(counts)


def qhe_phase_transitions(rows: list[QHERow]) -> list[dict]:
    """Find days where regime changed from previous day."""
    sorted_rows = sorted(rows, key=lambda r: r["date"])
    transitions = []
    for i in range(1, len(sorted_rows)):
        prev = sorted_rows[i - 1]
        curr = sorted_rows[i]
        if prev["regime_predicted"] != curr["regime_predicted"]:
            transitions.append(
                {
                    "date": curr["date"],
                    "from": prev["regime_predicted"],
                    "to": curr["regime_predicted"],
                    "qhe_before": float(prev["qhe"]),
                    "qhe_after": float(curr["qhe"]),
                    "delta": round(float(curr["qhe"]) - float(prev["qhe"]), 4),
                }
            )
    return transitions


def qhe_anomaly_days(rows: list[QHERow], std_threshold: float = 2.0) -> list[dict]:
    """Days where QHE is > std_threshold standard deviations from the mean."""
    sorted_rows = sorted(rows, key=lambda r: r["date"])
    vals = [float(r["qhe"]) for r in sorted_rows]
    mean = sum(vals) / len(vals)
    std = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
    anomalies = []
    for r in sorted_rows:
        qhe = float(r["qhe"])
        zscore = (qhe - mean) / std if std > 0 else 0
        if abs(zscore) > std_threshold:
            anomalies.append(
                {
                    "date": r["date"],
                    "qhe": round(qhe, 4),
                    "zscore": round(zscore, 2),
                    "regime": r["regime_predicted"],
                    "direction": "above" if zscore > 0 else "below",
                }
            )
    return anomalies


def qhe_weekly_aggregates(rows: list[QHERow], start: date, end: date) -> list[dict]:
    """Weekly QHE aggregates."""
    aggregates = []
    for week_start, week_end in weeks_in_range(start, end):
        week_rows = [r for r in rows if week_start <= date_from_str(r["date"]) <= week_end]
        if not week_rows:
            continue
        vals = [float(r["qhe"]) for r in week_rows]
        habit_avgs = [float(r["habit_avg"]) for r in week_rows]
        regimes = [r["regime_predicted"] for r in week_rows]
        regime_counts: dict[str, int] = defaultdict(int)
        for reg in regimes:
            regime_counts[reg] += 1
        aggregates.append(
            {
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "days": len(vals),
                "qhe_mean": round(sum(vals) / len(vals), 4),
                "qhe_min": round(min(vals), 4),
                "qhe_max": round(max(vals), 4),
                "qhe_std": round(
                    math.sqrt(sum((v - sum(vals) / len(vals)) ** 2 for v in vals) / len(vals)), 4
                ),
                "habit_avg_mean": round(sum(habit_avgs) / len(habit_avgs), 4),
                "dominant_regime": max(regime_counts, key=regime_counts.get),
                "regime_breakdown": dict(regime_counts),
            }
        )
    return aggregates


# ------------------------------------------------------------------
# 2. Sleep Analytics
# ------------------------------------------------------------------


def sleep_time_series(rows: list[SleepRow]) -> list[dict]:
    """Sleep data with 7-day rolling average."""
    sorted_rows = sorted(rows, key=lambda r: r["date"])
    result = []
    hours_vals = []
    quality_vals = []
    for r in sorted_rows:
        hours = float(r["sleep_hours"])
        quality = int(r["quality_score"])
        hours_vals.append(hours)
        quality_vals.append(quality)
        result.append(
            {
                "date": r["date"],
                "hours": hours,
                "quality": quality,
                "roll7_hours": round(sum(hours_vals[-7:]) / min(len(hours_vals), 7), 2),
                "roll7_quality": round(sum(quality_vals[-7:]) / min(len(quality_vals), 7), 2),
                "bedtime": r["bedtime"],
                "wake_time": r["wake_time"],
                "deep_sleep_pct": float(r["deep_sleep_pct"]),
                "rem_sleep_pct": float(r["rem_sleep_pct"]),
                "interruptions": int(r["interruptions"]),
                "source": r["source"],
                "notes": r["notes"],
            }
        )
    return result


def sleep_debt_analysis(rows: list[SleepRow], target_hours: float = 8.0) -> dict:
    """Compute cumulative sleep debt over the 180-day period."""
    sorted_rows = sorted(rows, key=lambda r: r["date"])
    cumulative = 0.0
    days_below_target = 0
    days_above_target = 0
    debt_series = []
    for r in sorted_rows:
        hours = float(r["sleep_hours"])
        delta = hours - target_hours
        cumulative += delta
        if delta < 0:
            days_below_target += 1
        else:
            days_above_target += 1
        debt_series.append(
            {
                "date": r["date"],
                "hours": hours,
                "delta": round(delta, 2),
                "cumulative_debt": round(cumulative, 2),
            }
        )
    return {
        "target_hours": target_hours,
        "total_debt": round(cumulative, 2),
        "days_below_target": days_below_target,
        "days_above_target": days_above_target,
        "series": debt_series,
    }


def sleep_phase_analysis(rows: list[SleepRow]) -> dict:
    """Sleep quality and duration by phase (weeks 1-4 of each month)."""
    sorted_rows = sorted(rows, key=lambda r: r["date"])
    by_phase: dict[str, list[float]] = defaultdict(list)
    for r in sorted_rows:
        d = date_from_str(r["date"])
        week_of_month = (d.day - 1) // 7 + 1
        phase = f"W{week_of_month}"
        by_phase[phase].append(float(r["sleep_hours"]))
    return {
        phase: {
            "mean": round(sum(vals) / len(vals), 2),
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
            "days": len(vals),
        }
        for phase, vals in sorted(by_phase.items())
    }


# ------------------------------------------------------------------
# 3. Habit Analytics
# ------------------------------------------------------------------


def habit_mastery_matrix(habit_rows: list[HabitRow], state_rows: list[HabitStateRow]) -> list[dict]:
    """Per-habit completion rate, avg streak, resistance vs completion correlation."""
    # Build date→habit→state lookup
    by_habit_date: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in state_rows:
        by_habit_date[r["habit_id"]][r["date"]] = r

    result = []
    for h in habit_rows:
        hid = h["id"]
        if hid not in by_habit_date:
            continue
        dates_sorted = sorted(by_habit_date[hid].keys())
        states = by_habit_date[hid]
        total = len(dates_sorted)
        completed = sum(1 for d in dates_sorted if parse_bool(states[d]["completed"]))
        streaks = [int(states[d]["streak_current"]) for d in dates_sorted]
        max_streak = max(streaks) if streaks else 0
        avg_streak = sum(streaks) / len(streaks) if streaks else 0
        # Best consecutive run
        best_run = 0
        current_run = 0
        for s in [parse_bool(states[d]["completed"]) for d in dates_sorted]:
            current_run = current_run + 1 if s else 0
            best_run = max(best_run, current_run)
        result.append(
            {
                "habit_id": hid,
                "name": h["name"],
                "category": h["category"],
                "resistance": float(h["resistance"]),
                "weight_in_qhe": float(h["weight_in_qhe"]),
                "total_days": total,
                "completed_days": completed,
                "completion_rate": round(completed / total, 4) if total > 0 else 0,
                "avg_streak": round(avg_streak, 2),
                "max_streak": max_streak,
                "best_consecutive_run": best_run,
            }
        )
    return sorted(result, key=lambda x: x["completion_rate"])


def habit_heatmap(
    state_rows: list[HabitStateRow], start: date, end: date
) -> dict[str, dict[str, bool]]:
    """Grid: {habit_id: {date_str: completed}} for calendar heatmap rendering."""
    by_habit: dict[str, dict[str, bool]] = defaultdict(dict)
    for r in state_rows:
        d = date_from_str(r["date"])
        if start <= d <= end:
            by_habit[r["habit_id"]][r["date"]] = parse_bool(r["completed"])
    return dict(by_habit)


def habit_streak_analysis(
    state_rows: list[HabitStateRow], habit_rows: list[HabitRow]
) -> list[dict]:
    """Analyze streak patterns per habit."""
    habit_map = {h["id"]: h for h in habit_rows}
    by_habit: dict[str, list[dict]] = defaultdict(list)
    for r in state_rows:
        by_habit[r["habit_id"]].append(r)
    result = []
    for hid, rows in sorted(by_habit.items()):
        sorted_rows = sorted(rows, key=lambda r: r["date"])
        streaks = [int(r["streak_current"]) for r in sorted_rows]
        completed = [parse_bool(r["completed"]) for r in sorted_rows]
        broken = [int(r["streak_broken_count"]) for r in sorted_rows]
        # Find longest sustained completion run
        best = 0
        cur = 0
        for s in completed:
            cur = cur + 1 if s else 0
            best = max(best, cur)
        # Learning rate H(t) = 1 - e^(-lam*s)
        lam = float(habit_map[hid]["lambda_learning"]) if hid in habit_map else 0.093
        latest_streak = streaks[-1] if streaks else 0
        h_t = 1.0 - math.exp(-lam * latest_streak)
        result.append(
            {
                "habit_id": hid,
                "name": habit_map.get(hid, {}).get("name", "?"),
                "total_days": len(sorted_rows),
                "current_streak": latest_streak,
                "max_streak": max(streaks) if streaks else 0,
                "best_run": best,
                "total_broken": sum(broken),
                "avg_streak": round(sum(streaks) / len(streaks), 2) if streaks else 0,
                "H_t_current": round(h_t, 4),
                "lambda": lam,
            }
        )
    return sorted(result, key=lambda x: x["H_t_current"])


# ------------------------------------------------------------------
# 4. Pomodoro Analytics
# ------------------------------------------------------------------


def pomodoro_time_series(rows: list[PomodoroRow]) -> list[dict]:
    """Daily pomodoro counts with efficiency (% complete)."""
    by_date: dict[str, dict] = defaultdict(lambda: {"total": 0, "complete": 0, "paused": 0})
    for r in rows:
        d = r["date"]
        by_date[d]["total"] += 1
        if r["state"] == "COMPLETE":
            by_date[d]["complete"] += 1
        paused = int(r.get("paused_duration_seconds") or 0)
        if paused > 0:
            by_date[d]["paused"] += 1
    sorted_dates = sorted(by_date.keys())
    complete_vals = []
    result = []
    for d in sorted_dates:
        c = by_date[d]["complete"]
        t = by_date[d]["total"]
        complete_vals.append(c)
        roll7 = sum(complete_vals[-7:]) / min(len(complete_vals), 7)
        result.append(
            {
                "date": d,
                "completed": c,
                "total": t,
                "efficiency_pct": round(100 * c / t, 1) if t > 0 else 0,
                "paused_rounds": by_date[d]["paused"],
                "roll7": round(roll7, 1),
            }
        )
    return result


def pomodoro_hourly_distribution(rows: list[PomodoroRow]) -> dict[str, int]:
    """When pomodoros are done: hour_of_day → count of COMPLETE rounds."""
    complete = [r for r in rows if r["state"] == "COMPLETE"]
    by_hour: dict[str, int] = defaultdict(int)
    for r in complete:
        hour = r["started_at"].split(":")[0]
        by_hour[f"{hour}:00"] += 1
    return dict(sorted(by_hour.items()))


def pomodoro_weekly_aggregates(rows: list[PomodoroRow], start: date, end: date) -> list[dict]:
    """Weekly pomodoro stats."""
    complete = [r for r in rows if r["state"] == "COMPLETE"]
    aggregates = []
    for week_start, week_end in weeks_in_range(start, end):
        week_complete = [r for r in complete if week_start <= date_from_str(r["date"]) <= week_end]
        if not week_complete:
            continue
        daily: dict[str, int] = defaultdict(int)
        for r in week_complete:
            daily[r["date"]] += 1
        vals = list(daily.values())
        aggregates.append(
            {
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "total_pomodoros": len(week_complete),
                "days_active": len(daily),
                "daily_avg": round(sum(vals) / len(vals), 1),
                "max_daily": max(vals),
                "min_daily": min(vals),
            }
        )
    return aggregates


# ------------------------------------------------------------------
# 5. Policy / FSM Analytics
# ------------------------------------------------------------------


def policy_state_time_series(rows: list[PolicyRow]) -> list[dict]:
    """Chronological policy states with QHE and severity."""
    sorted_rows = sorted(rows, key=lambda r: r["date"])
    return [
        {
            "date": r["date"],
            "state": r["state"],
            "severity": r["severity"],
            "qhe": round(float(r["qhe_input"]), 4),
            "days_in_state": int(r["days_in_state"]),
            "previous_state": r["previous_state"],
            "infraction_count": int(r["infraction_count"]),
            "hardwork_budget_hours": float(r["hardwork_budget_hours"]),
            "sleep_target_hours": float(r["sleep_target_hours"]),
            "max_pomodoros_per_day": int(r["max_pomodoros_per_day"]),
        }
        for r in sorted_rows
    ]


def policy_transition_matrix(rows: list[PolicyRow]) -> dict[str, dict[str, int]]:
    """Count transitions: from_state → {to_state: count}."""
    sorted_rows = sorted(rows, key=lambda r: r["date"])
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for i in range(1, len(sorted_rows)):
        prev = sorted_rows[i - 1]["state"]
        curr = sorted_rows[i]["state"]
        matrix[prev][curr] += 1
    return {k: dict(v) for k, v in sorted(matrix.items())}


def policy_uptime_pct(rows: list[PolicyRow]) -> dict[str, float]:
    """% of days in each policy state."""
    total = len(rows)
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r["state"]] += 1
    return {state: round(100 * count / total, 2) for state, count in counts.items()}


def policy_recover_episodes(rows: list[PolicyRow], min_days: int = 2) -> list[dict]:
    """Find RECOVER episodes of min_days or more consecutive days."""
    sorted_rows = sorted(rows, key=lambda r: r["date"])
    episodes = []
    cur_start = None
    cur_len = 0
    for r in sorted_rows:
        if r["state"] == "RECOVER":
            cur_start = cur_start or r["date"]
            cur_len += 1
        else:
            if cur_len >= min_days and cur_start:
                episodes.append(
                    {
                        "start": cur_start,
                        "end": sorted_rows[
                            sorted_rows.index([x for x in sorted_rows if x["date"] == cur_start][0])
                            - 1
                        ]["date"]
                        if cur_len > 1
                        else cur_start,
                        "days": cur_len,
                    }
                )
            cur_start = None
            cur_len = 0
    if cur_len >= min_days and cur_start:
        episodes.append({"start": cur_start, "end": sorted_rows[-1]["date"], "days": cur_len})
    return episodes


# ------------------------------------------------------------------
# 6. Journal / Mood Analytics
# ------------------------------------------------------------------


def mood_time_series(rows: list[JournalRow]) -> list[dict]:
    """Morning/evening mood, energy, focus by date."""
    by_date: dict[str, dict] = defaultdict(
        lambda: {"energia": [], "focus": [], "humor_am": [], "humor_pm": []}
    )
    for r in rows:
        d = r["date"]
        if r["energia_nivel"]:
            by_date[d]["energia"].append(int(r["energia_nivel"]))
        if r["focus_nivel"]:
            by_date[d]["focus"].append(int(r["focus_nivel"]))
        if r["humor_morning"]:
            by_date[d]["humor_am"].append(int(r["humor_morning"]))
        if r["humor_evening"]:
            by_date[d]["humor_pm"].append(int(r["humor_evening"]))
    sorted_dates = sorted(by_date.keys())
    result = []
    energia_vals = []
    focus_vals = []
    humor_vals = []
    for d in sorted_dates:
        e_vals = by_date[d]["energia"]
        f_vals = by_date[d]["focus"]
        h_vals = by_date[d]["humor_am"] + by_date[d]["humor_pm"]
        energia_vals.append(sum(e_vals) / len(e_vals) if e_vals else 0)
        focus_vals.append(sum(f_vals) / len(f_vals) if f_vals else 0)
        humor_vals.append(sum(h_vals) / len(h_vals) if h_vals else 0)
        roll7_e = sum(energia_vals[-7:]) / min(len(energia_vals), 7)
        roll7_f = sum(focus_vals[-7:]) / min(len(focus_vals), 7)
        roll7_h = sum(humor_vals[-7:]) / min(len(humor_vals), 7)
        result.append(
            {
                "date": d,
                "energia": round(energia_vals[-1], 1),
                "focus": round(focus_vals[-1], 1),
                "humor_avg": round(humor_vals[-1], 1),
                "roll7_energia": round(roll7_e, 2),
                "roll7_focus": round(roll7_f, 2),
                "roll7_humor": round(roll7_h, 2),
            }
        )
    return result


def journal_tag_extraction(rows: list[JournalRow]) -> dict[str, int]:
    """Extract and count topics/themes from journal entries."""
    themes: dict[str, int] = defaultdict(int)
    theme_keywords = {
        "pomodoro": ["pomodoro", "focus", "foco", "deep work", "distração"],
        "sleep": ["sono", "sleep", "dormir", "acordar", "noite"],
        "exercise": ["caminhada", "alongamento", "exercício", "gym", "academia"],
        "learning": ["estudar", "curso", "ler", "aprendizado", "study"],
        "social": ["família", "familia", "amigos", "social", "visita"],
        "food": ["refeição", "comida", "almoço", "jantar", "jejum"],
        "stress": ["stresse", "ansiedade", "overwhelm", "burnout", "pressão"],
        "productivity": ["produtividade", "done", "concluído", "meta", "task"],
    }
    for r in rows:
        text = (r.get("entry_text") or "").lower()
        text += " " + (r.get("licoes_aprendidas") or "").lower()
        for theme, keywords in theme_keywords.items():
            if any(kw in text for kw in keywords):
                themes[theme] += 1
    return dict(sorted(themes.items(), key=lambda x: -x[1]))


# ------------------------------------------------------------------
# 7. Time Block Analytics
# ------------------------------------------------------------------


def time_block_analysis(rows: list[dict], start: date, end: date) -> list[dict]:
    """Hours per period (MANHA/TARDE/NOITE) per week."""
    period_hours: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        d = date_from_str(r["date"])
        if start <= d <= end:
            period = r.get("period", "UNKNOWN")
            start_t = datetime.strptime(r["start"], "%H:%M")  # noqa: DTZ007
            end_t = datetime.strptime(r["end"], "%H:%M")  # noqa: DTZ007
            hours = (end_t - start_t).seconds / 3600
            week_key = d.isocalendar()[1]
            period_hours[week_key][period] = period_hours[week_key].get(period, 0) + hours
    result = []
    for week_num in sorted(period_hours.keys()):
        entry = {"week": week_num}
        entry.update({p: round(h, 2) for p, h in period_hours[week_num].items()})
        entry["total_hours"] = round(sum(period_hours[week_num].values()), 2)
        result.append(entry)
    return result


# ------------------------------------------------------------------
# 8. Day Context / Hardwork Analytics
# ------------------------------------------------------------------


def hardwork_accuracy(rows: list[DayContextRow]) -> list[dict]:
    """Orçado vs realizado hardwork per day, with accuracy %."""
    result = []
    for r in rows:
        orcado = float(r["hardwork_orcado_min"])
        realizado = float(r["hardwork_realizado_min"])
        accuracy = round(100 * realizado / orcado, 1) if orcado > 0 else 0
        result.append(
            {
                "date": r["date"],
                "tipo_dia": r["tipo_dia"],
                "orcado_min": orcado,
                "realizado_min": realizado,
                "delta_min": round(realizado - orcado, 1),
                "accuracy_pct": accuracy,
                "pomodoros_meta": int(r["pomodoros_meta"]),
                "pomodoros_realizados": int(r["pomodoros_realizados"]),
                "pom_meta_accuracy": round(
                    100 * int(r["pomodoros_realizados"]) / int(r["pomodoros_meta"]), 1
                )
                if int(r["pomodoros_meta"]) > 0
                else 0,
            }
        )
    return sorted(result, key=lambda x: x["date"])


# ------------------------------------------------------------------
# 9. Cross-Domain Correlations
# ------------------------------------------------------------------


def correlation_matrix(
    rows_qhe: list[QHERow],
    rows_sleep: list[SleepRow],
    _rows_journal: list[JournalRow],
) -> dict[str, dict[str, float]]:
    """Pearson correlation between QHE, sleep hours, energy, focus, humor.

    Only computes on days where all signals are present.
    """
    # Build aligned date-indexed series
    by_date: dict[str, dict] = defaultdict(dict)
    for r in rows_qhe:
        by_date[r["date"]]["qhe"] = float(r["qhe"])
    for r in rows_sleep:
        by_date[r["date"]]["sleep_hours"] = float(r["sleep_hours"])
    for r in _rows_journal:
        d = r["date"]
        if r["energia_nivel"]:
            by_date[d]["energia"] = int(r["energia_nivel"])
        if r["focus_nivel"]:
            by_date[d]["focus"] = int(r["focus_nivel"])

    keys = ["qhe", "sleep_hours", "energia", "focus"]
    # Only use dates where all are present
    aligned = [v for v in by_date.values() if all(v.get(k) is not None for k in keys)]
    if len(aligned) < 5:
        return {}

    def pearson(xs: list[float], ys: list[float]) -> float:
        n = len(xs)
        mx = sum(xs) / n
        my = sum(ys) / n
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
        sx = math.sqrt(sum((x - mx) ** 2 for x in xs) / n)
        sy = math.sqrt(sum((y - my) ** 2 for y in ys) / n)
        return cov / (sx * sy) if sx > 0 and sy > 0 else 0.0

    matrix = {}
    for k1 in keys:
        matrix[k1] = {}
        xs = [v[k1] for v in aligned]
        for k2 in keys:
            ys = [v[k2] for v in aligned]
            matrix[k1][k2] = round(pearson(xs, ys), 4)
    return matrix


# ------------------------------------------------------------------
# 10. Weekly Digest (all domains)
# ------------------------------------------------------------------


def weekly_digest(
    week_start: date,
    week_end: date,
    rows_qhe: list[QHERow],
    rows_sleep: list[SleepRow],
    rows_pomodoro: list[PomodoroRow],
    rows_habit_state: list[HabitStateRow],
    _rows_habit: list[HabitRow],
    _rows_journal: list[JournalRow],
    rows_policy: list[PolicyRow],
    rows_day_context: list[DayContextRow],
) -> dict:
    """Full-domain weekly digest for a given ISO week."""

    def filter_date(rows: list, col: str = "date") -> list:
        return [r for r in rows if row_start <= date_from_str(r[col]) <= row_end]

    row_start = week_start
    row_end = week_end

    qhe_w = filter_date(rows_qhe)
    sleep_w = filter_date(rows_sleep)
    pom_w = filter_date(rows_pomodoro)
    habit_w = filter_date(rows_habit_state)
    journal_w = filter_date(_rows_journal)
    policy_w = filter_date(rows_policy)
    ctx_w = filter_date(rows_day_context)

    # QHE
    qhe_vals = [float(r["qhe"]) for r in qhe_w]
    regime_counts: dict[str, int] = defaultdict(int)
    for r in qhe_w:
        regime_counts[r["regime_predicted"]] += 1

    # Sleep
    sleep_hours = [float(r["sleep_hours"]) for r in sleep_w]
    quality_vals = [int(r["quality_score"]) for r in sleep_w]

    # Pomodoro
    complete_pom = [r for r in pom_w if r["state"] == "COMPLETE"]
    by_date_pom: dict[str, int] = defaultdict(int)
    for r in complete_pom:
        by_date_pom[r["date"]] += 1

    # Habit completion rate
    habit_completed = sum(1 for r in habit_w if parse_bool(r["completed"]))
    habit_total = len(habit_w)
    habit_rate = round(100 * habit_completed / habit_total, 1) if habit_total > 0 else 0

    # Energy/focus
    energy_vals = [int(r["energia_nivel"]) for r in journal_w if r["energia_nivel"]]
    focus_vals = [int(r["focus_nivel"]) for r in journal_w if r["focus_nivel"]]
    humor_vals = [int(r["humor_morning"]) for r in journal_w if r["humor_morning"]]
    humor_vals += [int(r["humor_evening"]) for r in journal_w if r["humor_evening"]]

    # Policy
    policy_states_w: dict[str, int] = defaultdict(int)
    for r in policy_w:
        policy_states_w[r["state"]] += 1

    # Hardwork accuracy
    hw_vals = [
        (float(r["hardwork_realizado_min"]) / float(r["hardwork_orcado_min"]) * 100)
        for r in ctx_w
        if float(r["hardwork_orcado_min"]) > 0
    ]
    hw_acc = round(sum(hw_vals) / len(hw_vals), 1) if hw_vals else 0

    pom_daily = list(by_date_pom.values())

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "days_in_week": len(set(r["date"] for r in qhe_w)),
        # QHE
        "qhe_mean": round(sum(qhe_vals) / len(qhe_vals), 4) if qhe_vals else None,
        "qhe_min": round(min(qhe_vals), 4) if qhe_vals else None,
        "qhe_max": round(max(qhe_vals), 4) if qhe_vals else None,
        "dominant_regime": max(regime_counts, key=regime_counts.get) if regime_counts else None,
        "regime_breakdown": dict(regime_counts),
        # Sleep
        "sleep_mean_h": round(sum(sleep_hours) / len(sleep_hours), 2) if sleep_hours else None,
        "sleep_quality_mean": round(sum(quality_vals) / len(quality_vals), 1)
        if quality_vals
        else None,
        "days_good_sleep": sum(1 for h in sleep_hours if h >= 7.5),
        # Pomodoro
        "total_pomodoros": len(complete_pom),
        "pomodoros_per_day_avg": round(sum(pom_daily) / len(pom_daily), 1) if pom_daily else 0,
        "most_productive_day": max(by_date_pom, key=lambda d: by_date_pom[d])
        if by_date_pom
        else None,
        "max_pomodoros_in_day": max(pom_daily) if pom_daily else 0,
        # Habits
        "habit_completion_rate": habit_rate,
        "habit_completed_count": habit_completed,
        "habit_total_count": habit_total,
        # Mood
        "energy_mean": round(sum(energy_vals) / len(energy_vals), 1) if energy_vals else None,
        "focus_mean": round(sum(focus_vals) / len(focus_vals), 1) if focus_vals else None,
        "humor_mean": round(sum(humor_vals) / len(humor_vals), 1) if humor_vals else None,
        # Policy
        "policy_dominant": max(policy_states_w, key=lambda s: policy_states_w[s])
        if policy_states_w
        else None,
        "policy_breakdown": dict(policy_states_w),
        # Hardwork
        "hardwork_accuracy_pct": hw_acc,
    }


# ------------------------------------------------------------------
# 11. Monthly Report Data
# ------------------------------------------------------------------


def monthly_report(
    rows_qhe: list[QHERow],
    rows_sleep: list[SleepRow],
    rows_pomodoro: list[PomodoroRow],
    rows_habit_state: list[HabitStateRow],
    _rows_habit: list[HabitRow],
    _rows_journal: list[JournalRow],
    _rows_policy: list[PolicyRow],
) -> list[dict]:
    """Per-month aggregates for all key metrics."""
    by_month: dict[str, dict] = defaultdict(lambda: defaultdict(list))
    for r in rows_qhe:
        d = date_from_str(r["date"])
        key = d.strftime("%Y-%m")
        by_month[key]["qhe"].append(float(r["qhe"]))
    for r in rows_sleep:
        d = date_from_str(r["date"])
        key = d.strftime("%Y-%m")
        by_month[key]["sleep"].append(float(r["sleep_hours"]))
        by_month[key]["quality"].append(int(r["quality_score"]))
    complete_pom = [r for r in rows_pomodoro if r["state"] == "COMPLETE"]
    for r in complete_pom:
        d = date_from_str(r["date"])
        by_month[d.strftime("%Y-%m")]["pomodoros"].append(r["date"])
    for r in rows_habit_state:
        d = date_from_str(r["date"])
        key = d.strftime("%Y-%m")
        by_month[key]["habit_total"].append(r)
        if parse_bool(r["completed"]):
            by_month[key]["habit_done"].append(r)

    months = []
    for ym in sorted(by_month.keys()):
        data = by_month[ym]
        pom_count = len(data.get("pomodoros", []))
        pom_by_day: dict[str, int] = defaultdict(int)
        for d in data.get("pomodoros", []):
            pom_by_day[d] += 1
        habit_done = len(data.get("habit_done", []))
        habit_total = len(data.get("habit_total", []))
        regimes = defaultdict(int)
        for q in data.get("qhe", []):
            # approximate from qhe value
            pass  # need original regime from qhe_metrics
        months.append(
            {
                "month": ym,
                "qhe_mean": round(sum(data["qhe"]) / len(data["qhe"]), 4)
                if data.get("qhe")
                else None,
                "qhe_min": round(min(data["qhe"]), 4) if data.get("qhe") else None,
                "qhe_max": round(max(data["qhe"]), 4) if data.get("qhe") else None,
                "sleep_mean_h": round(sum(data["sleep"]) / len(data["sleep"]), 2)
                if data.get("sleep")
                else None,
                "sleep_quality_mean": round(sum(data["quality"]) / len(data["quality"]), 1)
                if data.get("quality")
                else None,
                "total_pomodoros": pom_count,
                "pomodoros_per_day_avg": round(pom_count / len(pom_by_day), 1) if pom_by_day else 0,
                "habit_completion_rate": round(100 * habit_done / habit_total, 1)
                if habit_total > 0
                else 0,
                "active_days": len(set(r["date"] for r in data.get("habit_total", []))),
            }
        )
    return months


# ------------------------------------------------------------------
# 12. Data Quality Report
# ------------------------------------------------------------------


def data_quality_report(
    rows_by_entity: dict[str, list[dict]],
    expected_days: int = 180,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Check for gaps, missing dates, anomalies across all entities."""
    if start_date is None:
        start_date = date(2025, 12, 23)
    if end_date is None:
        end_date = date(2026, 6, 20)

    expected_dates = set(
        (start_date + timedelta(days=i)).isoformat()
        for i in range((end_date - start_date).days + 1)
    )
    quality = {}
    for name, rows in rows_by_entity.items():
        dates_found = set(r.get("date", "") for r in rows if r.get("date"))
        missing = expected_dates - dates_found
        extra = dates_found - expected_dates
        quality[name] = {
            "expected": expected_days,
            "found": len(dates_found),
            "missing_count": len(missing),
            "missing_dates": sorted(missing) if missing else [],
            "extra_count": len(extra),
            "complete_pct": round(100 * len(dates_found) / expected_days, 2),
        }
    return quality
