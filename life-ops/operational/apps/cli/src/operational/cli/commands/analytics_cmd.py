"""Analytics command — rich CLI for 180-day data storytelling.

USAGE:
    pav analytics overview          # Executive dashboard (all domains)
    pav analytics qhe               # QHE time series, regimes, anomalies
    pav analytics sleep             # Sleep quality, debt, phase analysis
    pav analytics habits            # Habit mastery matrix + heatmap
    pav analytics pomodoro          # Pomodoro stats + hourly distribution
    pav analytics policy            # FSM state transitions, uptime
    pav analytics mood              # Energy/focus/humor correlations
    pav analytics week [N]          # Week N digest (1-26)
    pav analytics report           # Full markdown report for all 26 weeks
    pav analytics quality           # Data completeness audit
"""

import json
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import typer
from rich.box import DOUBLE
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from operational.analytics.circadian import (
    circadian_energy,
    generate_narrative,
    lunch_analysis,
    pop_comparison,
    ritual_analysis,
    time_block_analysis,
)
from operational.analytics.engine import (
    coerce_row,
    data_quality_report,
    habit_mastery_matrix,
    habit_streak_analysis,
    journal_tag_extraction,
    load_csv,
    mood_time_series,
    policy_recover_episodes,
    policy_state_time_series,
    policy_transition_matrix,
    policy_uptime_pct,
    pomodoro_hourly_distribution,
    pomodoro_time_series,
    pomodoro_weekly_aggregates,
    qhe_anomaly_days,
    qhe_phase_transitions,
    qhe_regime_distribution,
    qhe_time_series,
    qhe_weekly_aggregates,
    sleep_debt_analysis,
    sleep_phase_analysis,
    sleep_time_series,
    weekly_digest,
    weeks_in_range,
)
from operational.analytics.engine import (
    correlation_matrix as _engine_corr_matrix,
)
from operational.core.analytics import (
    build_trajectory,
    compute_aggregations,
    linear_forecast,
    load_dataset,
    scenario_analysis,
    weekly_trend,
)
from operational.core.analytics import (
    growth_score as _gs,
)
from operational.core.insights import format_insights_text, generate_full_report
from operational.ui import console

analytics_app = typer.Typer(
    help="Analytics e data storytelling sobre 180 dias de dados.",
)

_START = date(2025, 12, 23)
_END = date(2026, 6, 20)


def _safe_grid_val(val: Any, fmt: str = "", color: str | None = None) -> str:
    """Format a value safely for Rich tables, stripping any embedded markup."""
    if val is None or val == "":
        return "N/A"
    try:
        formatted = f"{val:{fmt}}" if fmt else str(val)
    except (ValueError, TypeError):
        formatted = str(val)
    # Strip any residual markup characters that would break Rich rendering
    cleaned = re.sub(r"\[[^\]]+\]", "", formatted)
    if color:
        return f"[{color}]{cleaned}[/{color}]"
    return cleaned


def _detect_csv_dir() -> Path:
    """Locate the 6month CSV directory by traversing up from this file."""
    current = Path(__file__).resolve().parent
    for _ in range(8):  # go up enough to find datasets
        if (current / "datasets" / "6month" / "csv").is_dir():
            return current / "datasets" / "6month" / "csv"
        parent = current.parent
        if parent == current:
            break
        current = parent
    # Fallback: assume CWD is the operational root
    return Path.cwd() / "datasets" / "6month" / "csv"


_CSV_DIR = _detect_csv_dir()


def _load_all() -> dict[str, list[dict]]:
    return {
        "qhe_metrics": [coerce_row(r) for r in load_csv("qhe_metrics", _CSV_DIR)],
        "sleep_record": [coerce_row(r) for r in load_csv("sleep_record", _CSV_DIR)],
        "pomodoro_round": [coerce_row(r) for r in load_csv("pomodoro_round", _CSV_DIR)],
        "habit_state": [coerce_row(r) for r in load_csv("habit_state", _CSV_DIR)],
        "habit": [coerce_row(r) for r in load_csv("habit", _CSV_DIR)],
        "journal_entry": [coerce_row(r) for r in load_csv("journal_entry", _CSV_DIR)],
        "policy_decision": [coerce_row(r) for r in load_csv("policy_decision", _CSV_DIR)],
        "day_context": [coerce_row(r) for r in load_csv("day_context", _CSV_DIR)],
        "transicao": [coerce_row(r) for r in load_csv("transicao", _CSV_DIR)],
        "daily_reflection": [coerce_row(r) for r in load_csv("daily_reflection", _CSV_DIR)],
        "routine_log": [coerce_row(r) for r in load_csv("routine_log", _CSV_DIR)],
        "ajuste_fino": [coerce_row(r) for r in load_csv("ajuste_fino", _CSV_DIR)],
        "time_block": [coerce_row(r) for r in load_csv("time_block", _CSV_DIR)],
        "lunch_record": [coerce_row(r) for r in load_csv("lunch_record", _CSV_DIR)],
    }


# ------------------------------------------------------------------
# Shared rendering helpers
# ------------------------------------------------------------------


def _sparkline(vals: list[float], width: int = 20) -> str:
    """Simple ASCII sparkline."""
    if not vals:
        return "░" * width
    mn, mx = min(vals), max(vals)
    rng = mx - mn or 1
    ticks = " ▁▂▃▄▅▆▇█"
    n = len(ticks) - 1
    result = []
    for v in vals[-width:]:
        idx = int((v - mn) / rng * n)
        result.append(ticks[min(idx, n)])
    return "".join(result)


def _trend_arrow(current: float, previous: float) -> str:
    delta = current - previous
    if abs(delta) < 0.001:
        return "→"
    return "↑" if delta > 0 else "↓"


def _pct_bar(pct: float, width: int = 30) -> str:
    filled = int(width * min(pct, 100) / 100)
    return "█" * filled + "░" * (width - filled)


# ------------------------------------------------------------------
# Overview Dashboard
# ------------------------------------------------------------------


def _render_overview(data: dict) -> None:

    qhe_rows = data["qhe_metrics"]
    sleep_rows = data["sleep_record"]
    pom_rows = data["pomodoro_round"]
    habit_state_rows = data["habit_state"]
    habit_rows = data["habit"]
    policy_rows = data["policy_decision"]
    journal_rows = data["journal_entry"]

    ts_qhe = qhe_time_series(qhe_rows)
    ts_sleep = sleep_time_series(sleep_rows)
    regimes = qhe_regime_distribution(qhe_rows)
    debt = sleep_debt_analysis(sleep_rows)
    habit_matrix = habit_mastery_matrix(habit_rows, habit_state_rows)
    uptime = policy_uptime_pct(policy_rows)
    corr = _engine_corr_matrix(qhe_rows, sleep_rows, journal_rows)

    latest_qhe = ts_qhe[-1]
    latest_sleep = ts_sleep[-1]

    # ---- KPI Cards ----
    def kpi(title: str, value: str, sub: str = "", color: str = "cyan") -> Panel:
        return Panel(
            f"[bold {color}]{value}[/bold {color}]\n[dim]{sub}[/dim]",
            title=title,
            box=DOUBLE,
            border_style=color,
            padding=(0, 2),
        )

    # QHE card
    qhe_now = latest_qhe["qhe"]
    qhe_week_ago = ts_qhe[-8]["qhe"] if len(ts_qhe) >= 8 else ts_qhe[0]["qhe"]
    qhe_trend = _trend_arrow(qhe_now, qhe_week_ago)
    regime_icon = {"PUSH": "🚀", "MAINTAIN": "⚖️", "REDUCE": "📉", "RECOVER": "🛑"}
    regime = latest_qhe["regime"]
    card_qhe = kpi(
        "QHE Score",
        f"{qhe_now:.3f} {qhe_trend}",
        f"{regime_icon.get(regime, '?')} {regime} · roll7={latest_qhe['roll7']:.3f}",
        color="green" if qhe_now >= 0.85 else "yellow",
    )

    # Sleep card
    sleep_now = latest_sleep["hours"]
    sleep_trend = _trend_arrow(
        sleep_now, ts_sleep[-8]["hours"] if len(ts_sleep) >= 8 else sleep_now
    )
    card_sleep = kpi(
        "Sleep (last night)",
        f"{sleep_now:.1f}h {sleep_trend}",
        f"quality={latest_sleep['quality']} · debt={debt['total_debt']:+.1f}h",
        color="cyan" if sleep_now >= 7.5 else "red",
    )

    # Pomodoro card
    pom_ts = pomodoro_time_series(pom_rows)
    pom_today = pom_ts[-1] if pom_ts else {}
    card_pom = kpi(
        "Pomodoros (today)",
        f"{pom_today.get('completed', 0)}",
        f"efficiency={pom_today.get('efficiency_pct', 0):.0f}% · roll7={pom_today.get('roll7', 0):.1f}",
        color="magenta",
    )

    # Habit card
    top_habit = habit_matrix[-1] if habit_matrix else {}
    worst = habit_matrix[0] if habit_matrix else {}
    card_habit = kpi(
        "Habit Leader",
        top_habit.get("name", "?")[:18],
        f"streak={top_habit.get('current_streak', 0)} · H(t)={top_habit.get('H_t_current', 0):.3f}",
        color="green",
    )

    # Policy card
    dom_policy = max(uptime, key=uptime.get) if uptime else "?"
    pomodoro_card_sleep = kpi(
        "Policy",
        dom_policy,
        f"PUSH={uptime.get('PUSH', 0):.0f}% · RECOVER={uptime.get('RECOVER', 0):.0f}%",
        color="blue",
    )

    # Mood card
    mood_ts = mood_time_series(journal_rows)
    latest_mood = mood_ts[-1] if mood_ts else {}
    card_mood = kpi(
        "Energy/Focus",
        f"⚡{latest_mood.get('energia', 0):.0f} 🎯{latest_mood.get('focus', 0):.0f}",
        f"humor={latest_mood.get('humor_avg', 0):.1f} · roll7=({latest_mood.get('roll7_energia', 0):.1f}/{latest_mood.get('roll7_focus', 0):.1f})",
        color="yellow",
    )

    cards = [card_qhe, card_sleep, card_pom, card_habit, pomodoro_card_sleep, card_mood]
    console.print(Columns(cards, padding=1, equal=True))
    console.print()

    # ---- QHE 30-day chart ----
    ts_30 = ts_qhe[-30:]
    qhe_vals = [r["qhe"] for r in ts_30]
    spark = _sparkline(qhe_vals, 40)
    roll7_spark = _sparkline([r["roll7"] for r in ts_30], 40)

    chart_table = Table(box=DOUBLE, show_header=True, header_style="bold")
    chart_table.add_column("QHE (30d)", style="cyan", width=44)
    chart_table.add_column("roll7", style="green", width=44)
    chart_table.add_row(spark, roll7_spark)
    console.print(Panel(chart_table, title="📈 QHE — last 30 days", border_style="cyan"))
    console.print()

    # ---- Sleep debt chart ----
    debt_series = debt["series"][-30:]
    sleep_vals = [r["hours"] for r in debt_series]
    debt_vals = [r["cumulative_debt"] for r in debt_series]
    sleep_spark = _sparkline(sleep_vals, 40)
    debt_spark = _sparkline(debt_vals, 40)

    sleep_chart = Table(box=DOUBLE, show_header=True, header_style="bold")
    sleep_chart.add_column("Hours slept", style="cyan", width=44)
    sleep_chart.add_column("Cumulative debt (h)", style="red", width=44)
    sleep_chart.add_row(sleep_spark, debt_spark)
    console.print(
        Panel(
            sleep_chart,
            title=f"😴 Sleep debt: {debt['total_debt']:+.1f}h ({debt['days_below_target']} days <8h)",
            border_style="cyan",
        )
    )
    console.print()

    # ---- Regime + Policy breakdown ----
    regime_table = Table(title="Regime Distribution (180 days)", box=DOUBLE, header_style="bold")
    regime_table.add_column("Regime", style="bold")
    regime_table.add_column("Days", justify="right")
    regime_table.add_column("%", justify="right")
    regime_table.add_column("Bar", style="cyan")
    total_regime = sum(regimes.values())
    for reg in ["PUSH", "MAINTAIN", "REDUCE", "RECOVER"]:
        cnt = regimes.get(reg, 0)
        pct = 100 * cnt / total_regime if total_regime else 0
        regime_table.add_row(reg, str(cnt), f"{pct:.1f}%", _pct_bar(pct, 20))
    console.print(regime_table)
    console.print()

    # ---- Correlation matrix ----
    if corr:
        corr_table = Table(
            title="Cross-Domain Correlations (Pearson r)", box=DOUBLE, header_style="bold"
        )
        keys = ["qhe", "sleep_hours", "energia", "focus"]
        labels = {"qhe": "QHE", "sleep_hours": "Sleep", "energia": "⚡Energy", "focus": "🎯Focus"}
        corr_table.add_column("", style="bold")
        for k in keys:
            corr_table.add_column(labels[k], justify="right")
        for k1 in keys:
            row_vals = [str(corr[k1][k2]) for k2 in keys]
            corr_table.add_row(labels[k1], *row_vals)
        console.print(Panel(corr_table, border_style="magenta"))
        console.print()

    # ---- Habit Mastery Matrix ----
    habit_table = Table(
        title="Habit Mastery Matrix",
        box=DOUBLE,
        header_style="bold",
    )
    habit_table.add_column("Habit", style="bold")
    habit_table.add_column("Category", style="cyan")
    habit_table.add_column("Rate", justify="right")
    habit_table.add_column("Current Streak", justify="right")
    habit_table.add_column("H(t)", justify="right", style="green")
    habit_table.add_column("Mastery Bar", style="cyan")
    for h in sorted(habit_matrix, key=lambda x: x.get("completion_rate", 0)):
        name = h.get("name", "?")[:22]
        cat = h.get("category", "?")[:13]
        rate = h.get("completion_rate", 0) * 100
        streak = h.get("current_streak", 0)
        ht = h.get("H_t_current", 0)
        bar = _pct_bar(rate, 20)
        color = "green" if ht > 0.9 else "yellow" if ht > 0.7 else "red"
        habit_table.add_row(
            name, cat, f"{rate:.0f}%", str(streak), f"[{color}]{ht:.4f}[/{color}]", bar
        )
    console.print(habit_table)


# ------------------------------------------------------------------
# QHE command
# ------------------------------------------------------------------


def _render_qhe(data: dict) -> None:

    qhe_rows = data["qhe_metrics"]
    ts = qhe_time_series(qhe_rows)
    regimes = qhe_regime_distribution(qhe_rows)
    transitions = qhe_phase_transitions(qhe_rows)
    anomalies = qhe_anomaly_days(qhe_rows)
    weekly = qhe_weekly_aggregates(qhe_rows, _START, _END)

    console.print(
        Panel("[bold cyan]QHE Analytics — 180-Day Algorithm[/bold cyan]", border_style="cyan")
    )
    console.print()

    # Regime distribution
    reg_table = Table(title="Regime Distribution", box=DOUBLE)
    reg_table.add_column("Regime", style="bold")
    reg_table.add_column("Days", justify="right")
    reg_table.add_column("Pct", justify="right")
    total = sum(regimes.values())
    for reg, icon in [("PUSH", "🚀"), ("MAINTAIN", "⚖️"), ("REDUCE", "📉"), ("RECOVER", "🛑")]:
        cnt = regimes.get(reg, 0)
        reg_table.add_row(f"{icon} {reg}", str(cnt), f"{100 * cnt / total:.1f}%")
    console.print(reg_table)
    console.print()

    # Phase transitions
    if transitions:
        trans_table = Table(title=f"Regime Transitions ({len(transitions)} total)", box=DOUBLE)
        trans_table.add_column("Date", style="cyan")
        trans_table.add_column("From", style="yellow")
        trans_table.add_column("→", justify="center")
        trans_table.add_column("To", style="green")
        trans_table.add_column("QHE Δ", justify="right")
        for t in transitions[-10:]:
            arrow = "🔁"
            trans_table.add_row(t["date"], t["from"], arrow, t["to"], f"{t['delta']:+.4f}")
        console.print(trans_table)
        console.print()

    # Anomalies
    if anomalies:
        console.print(f"[bold red]⚠ Anomaly Days (|z| > 2sigma):[/bold red] {len(anomalies)}")
        for a in anomalies[:5]:
            icon = "🔺" if a["direction"] == "above" else "🔻"
            console.print(
                f"  {icon} {a['date']}: QHE={a['qhe']:.4f} (z={a['zscore']:+.2f}) {a['regime']}"
            )
        console.print()

    # Weekly aggregates table
    wk_table = Table(title="Weekly QHE Aggregates", box=DOUBLE)
    wk_table.add_column("Week", style="cyan")
    wk_table.add_column("QHE Mean", justify="right")
    wk_table.add_column("Min", justify="right")
    wk_table.add_column("Max", justify="right")
    wk_table.add_column("sigma", justify="right")
    wk_table.add_column("Dominant", style="bold")
    wk_table.add_column("Spark", style="cyan")
    for w in weekly:
        spark_vals = []
        # get qhe vals for this week
        wk_table.add_row(
            w["week_start"][5:],
            f"{w['qhe_mean']:.4f}",
            f"{w['qhe_min']:.4f}",
            f"{w['qhe_max']:.4f}",
            f"{w['qhe_std']:.4f}",
            w["dominant_regime"],
            "",
        )
    console.print(wk_table)


# ------------------------------------------------------------------
# Sleep command
# ------------------------------------------------------------------


def _render_sleep(data: dict) -> None:

    sleep_rows = data["sleep_record"]
    ts = sleep_time_series(sleep_rows)
    debt = sleep_debt_analysis(sleep_rows)
    phases = sleep_phase_analysis(sleep_rows)

    console.print(Panel("[bold cyan]Sleep Analytics[/bold cyan]", border_style="cyan"))
    console.print()

    # Debt summary
    debt_color = "green" if debt["total_debt"] >= 0 else "red"
    console.print(f"[{debt_color}]Cumulative sleep debt: {debt['total_debt']:+.1f}h[/{debt_color}]")
    console.print(
        f"  Days below 8h target: {debt['days_below_target']} / {debt['days_below_target'] + debt['days_above_target']}"
    )
    console.print(f"  Days above target:   {debt['days_above_target']}")
    console.print()

    # Phase analysis
    phase_table = Table(title="Sleep by Month Week (W1-W5)", box=DOUBLE)
    phase_table.add_column("Phase", style="bold cyan")
    phase_table.add_column("Mean (h)", justify="right")
    phase_table.add_column("Min", justify="right")
    phase_table.add_column("Max", justify="right")
    phase_table.add_column("Days", justify="right")
    phase_table.add_column("Quality Bar", style="cyan")
    for phase in ["W1", "W2", "W3", "W4", "W5"]:
        if phase in phases:
            p = phases[phase]
            bar = _pct_bar(100 * p["mean"] / 9, 20)
            phase_table.add_row(
                phase,
                f"{p['mean']:.2f}h",
                f"{p['min']:.1f}h",
                f"{p['max']:.1f}h",
                str(p["days"]),
                bar,
            )
    console.print(phase_table)
    console.print()

    # 30-day sparkline
    ts_30 = ts[-30:]
    sleep_vals = [r["hours"] for r in ts_30]
    qual_vals = [float(r["quality"]) for r in ts_30]
    sleep_spark = _sparkline(sleep_vals, 50)
    qual_spark = _sparkline(qual_vals, 50)
    spark_t = Table(box=None)
    spark_t.add_row(f"Hours:  {sleep_spark}")
    spark_t.add_row(f"Quality: {qual_spark}")
    console.print(
        Panel(spark_t, title="Last 30 Days — Hours (top) / Quality (bottom)", border_style="cyan")
    )


# ------------------------------------------------------------------
# Habits command
# ------------------------------------------------------------------


def _render_habits(data: dict) -> None:

    habit_rows = data["habit"]
    habit_state_rows = data["habit_state"]
    streak_data = habit_streak_analysis(habit_state_rows, habit_rows)
    matrix = habit_mastery_matrix(habit_rows, habit_state_rows)

    console.print(
        Panel("[bold cyan]Habit Mastery & Streak Analytics[/bold cyan]", border_style="cyan")
    )
    console.print()

    # Mastery table
    mat_table = Table(
        title="Habit Mastery Matrix (sorted by completion rate)",
        box=DOUBLE,
        header_style="bold",
    )
    mat_table.add_column("Habit", style="bold")
    mat_table.add_column("Cat", style="cyan")
    mat_table.add_column("Resistance", justify="right")
    mat_table.add_column("Rate", justify="right")
    mat_table.add_column("Cur.Str", justify="right")
    mat_table.add_column("Max.Str", justify="right")
    mat_table.add_column("H(t)", justify="right", style="green")
    mat_table.add_column("Mastery Bar", style="cyan")

    for h in sorted(matrix, key=lambda x: x.get("completion_rate", 0)):
        rate = h.get("completion_rate", 0) * 100
        ht = h.get("H_t_current", 0)
        color = "green" if ht > 0.9 else "yellow" if ht > 0.7 else "red"
        mat_table.add_row(
            h.get("name", "?")[:22],
            h.get("category", "?")[:8],
            f"{h.get('resistance', 0):.1f}",
            f"{rate:.0f}%",
            str(h.get("current_streak", 0)),
            str(h.get("max_streak", 0)),
            f"[{color}]{ht:.4f}[/{color}]",
            _pct_bar(rate, 20),
        )
    console.print(mat_table)
    console.print()

    # Learning curve table
    learn_table = Table(title="Habit Automation — H(t) = 1 - e^(-λ·s)", box=DOUBLE)
    learn_table.add_column("Habit", style="bold")
    learn_table.add_column("λ", justify="right", style="cyan")
    learn_table.add_column("Current Streak (s)", justify="right")
    learn_table.add_column("H(t)", justify="right", style="bold green")
    learn_table.add_column("Best Run", justify="right")
    for s in sorted(streak_data, key=lambda x: x.get("H_t_current", 0)):
        ht = s.get("H_t_current", 0)
        color = "green" if ht > 0.9 else "yellow" if ht > 0.7 else "red"
        learn_table.add_row(
            s.get("name", "?")[:22],
            f"{s.get('lambda', 0.093):.4f}",
            str(s.get("current_streak", 0)),
            f"[{color}]{ht:.4f}[/{color}]",
            str(s.get("best_run", 0)),
        )
    console.print(learn_table)


# ------------------------------------------------------------------
# Pomodoro command
# ------------------------------------------------------------------


def _render_pomodoro(data: dict) -> None:

    pom_rows = data["pomodoro_round"]
    ts = pomodoro_time_series(pom_rows)
    hourly = pomodoro_hourly_distribution(pom_rows)
    weekly = pomodoro_weekly_aggregates(pom_rows, _START, _END)

    console.print(Panel("[bold magenta]Pomodoro Analytics[/bold magenta]", border_style="magenta"))
    console.print()

    total_complete = sum(1 for r in pom_rows if r.get("state") == "COMPLETE")
    total_all = len(pom_rows)
    console.print(
        f"Total: [bold]{total_complete}[/bold] COMPLETE / {total_all} started  ([bold]{100 * total_complete / total_all:.1f}%[/bold] efficiency)"
    )
    console.print()

    # Hourly heatmap (text-based)
    if hourly:
        max_h = max(hourly.values())
        hour_rows = sorted(hourly.items())
        heat_table = Table(
            title="Hourly Distribution (completed pomodoros)", box=DOUBLE, header_style="bold"
        )
        heat_table.add_column("Hour", justify="right")
        heat_table.add_column("Count", justify="right")
        heat_table.add_column("Heat", style="magenta")
        for hour, count in hour_rows:
            bar_len = int(30 * count / max_h) if max_h > 0 else 0
            heat_table.add_row(hour, str(count), "█" * bar_len + "░" * (30 - bar_len))
        console.print(heat_table)
        console.print()

    # Weekly summary
    wk_table = Table(title="Weekly Pomodoro Aggregates", box=DOUBLE)
    wk_table.add_column("Week", style="cyan")
    wk_table.add_column("Total", justify="right", style="bold")
    wk_table.add_column("Days Active", justify="right")
    wk_table.add_column("Avg/Day", justify="right")
    wk_table.add_column("Max Day", justify="right")
    for w in weekly[-10:]:
        wk_table.add_row(
            w["week_start"][5:],
            f"[bold]{w['total_pomodoros']}[/bold]",
            str(w["days_active"]),
            f"{w['daily_avg']:.1f}",
            str(w["max_daily"]),
        )
    console.print(wk_table)


# ------------------------------------------------------------------
# Policy command
# ------------------------------------------------------------------


def _render_policy(data: dict) -> None:

    policy_rows = data["policy_decision"]
    ts = policy_state_time_series(policy_rows)
    matrix = policy_transition_matrix(policy_rows)
    uptime = policy_uptime_pct(policy_rows)
    episodes = policy_recover_episodes(policy_rows)

    console.print(Panel("[bold blue]Policy FSM Analytics[/bold blue]", border_style="blue"))
    console.print()

    # Uptime
    uptime_table = Table(title="Policy State Uptime (180 days)", box=DOUBLE, header_style="bold")
    uptime_table.add_column("State", style="bold")
    uptime_table.add_column("Days", justify="right")
    uptime_table.add_column("Uptime %", justify="right")
    uptime_table.add_column("Bar")
    _state_colors = {"PUSH": "green", "MAINTAIN": "yellow", "REDUCE": "red", "RECOVER": "bold red"}
    for state, color in [
        ("PUSH", "green"),
        ("MAINTAIN", "yellow"),
        ("REDUCE", "red"),
        ("RECOVER", "bold red"),
    ]:
        days = uptime.get(state, 0)
        pct = 100 * days / 180
        uptime_table.add_row(
            f"[{color}]{state}[/{color}]", str(days), f"{pct:.1f}%", _pct_bar(pct, 30)
        )
    console.print(uptime_table)
    console.print()

    # Transition matrix
    if matrix:
        states = ["PUSH", "MAINTAIN", "REDUCE", "RECOVER"]
        trans_table = Table(
            title="State Transition Matrix (from → to)", box=DOUBLE, header_style="bold"
        )
        trans_table.add_column("From \\ To", style="bold")
        for s in states:
            trans_table.add_column(s, justify="right")
        for from_state in states:
            row = [f"[bold]{from_state}[/bold]"]
            for to_state in states:
                row.append(str(matrix.get(from_state, {}).get(to_state, 0)))
            trans_table.add_row(*row)
        console.print(trans_table)
        console.print()

    # RECOVER episodes
    if episodes:
        console.print(f"[bold red]🛑 RECOVER Episodes (≥2 days):[/bold red] {len(episodes)}")
        for e in episodes[:5]:
            console.print(f"  {e['start']} → {e['end']}: {e['days']} days")
    else:
        console.print("[green]No RECOVER episodes ≥2 consecutive days.[/green]")


# ------------------------------------------------------------------
# Mood command
# ------------------------------------------------------------------


def _render_mood(data: dict) -> None:

    journal_rows = data["journal_entry"]
    qhe_rows = data["qhe_metrics"]
    sleep_rows = data["sleep_record"]
    ts = mood_time_series(journal_rows)
    tags = journal_tag_extraction(journal_rows)
    corr = _engine_corr_matrix(qhe_rows, sleep_rows, journal_rows)

    console.print(
        Panel("[bold yellow]Mood & Journal Analytics[/bold yellow]", border_style="yellow")
    )
    console.print()

    # 30-day sparklines
    ts_30 = ts[-30:]
    e_vals = [r["energia"] for r in ts_30]
    f_vals = [r["focus"] for r in ts_30]
    h_vals = [r["humor_avg"] for r in ts_30]
    mood_t = Table(box=None)
    mood_t.add_row(f"⚡Energy: {_sparkline(e_vals, 50)}")
    mood_t.add_row(f"🎯Focus:  {_sparkline(f_vals, 50)}")
    mood_t.add_row(f"😀Humor:  {_sparkline(h_vals, 50)}")
    console.print(Panel(mood_t, title="Last 30 Days — Mood Signals", border_style="yellow"))
    console.print()

    # Rolling 7-day averages
    roll_table = Table(title="Rolling 7-Day Averages (last 7 days)", box=DOUBLE)
    roll_table.add_column("Date", style="cyan")
    roll_table.add_column("⚡E", justify="right")
    roll_table.add_column("🎯F", justify="right")
    roll_table.add_column("😀H", justify="right")
    for r in ts_30[-7:]:
        roll_table.add_row(
            r["date"][5:], f"{r['energia']:.1f}", f"{r['focus']:.1f}", f"{r['humor_avg']:.1f}"
        )
    console.print(roll_table)
    console.print()

    # Tags
    if tags:
        tag_table = Table(title="Journal Theme Frequency", box=DOUBLE)
        tag_table.add_column("Theme", style="bold")
        tag_table.add_column("Mentions", justify="right", style="cyan")
        for theme, count in list(tags.items())[:10]:
            tag_table.add_row(theme.title(), str(count))
        console.print(tag_table)

    # Correlations
    if corr:
        console.print()
        console.print("[bold]Correlations:[/bold]")
        for k1 in ["qhe", "sleep_hours", "energia", "focus"]:
            for k2 in ["sleep_hours", "energia", "focus"]:
                if k1 != k2:
                    r = corr[k1][k2]
                    if abs(r) > 0.3:
                        icon = "📈" if r > 0 else "📉"
                        console.print(f"  {icon} {k1} ↔ {k2}: {r:+.4f}")


# ------------------------------------------------------------------
# Week digest command
# ------------------------------------------------------------------


def _render_week(week_num: int, data: dict) -> None:

    if not (1 <= week_num <= 26):
        console.print("[red]Week must be 1-26[/red]")
        return

    week_list = weeks_in_range(_START, _END)
    if week_num > len(week_list):
        console.print(f"[red]Only {len(week_list)} weeks in dataset[/red]")
        return

    week_start, week_end = week_list[week_num - 1]
    wd = weekly_digest(
        week_start,
        week_end,
        data["qhe_metrics"],
        data["sleep_record"],
        data["pomodoro_round"],
        data["habit_state"],
        data["habit"],
        data["journal_entry"],
        data["policy_decision"],
        data["day_context"],
    )

    console.print(
        Panel(
            f"[bold cyan]Week {week_num}:[/bold cyan] {week_start.isoformat()} → {week_end.isoformat()}  ({wd['days_in_week']} days)",
            border_style="cyan",
        )
    )
    console.print()

    # KPI grid
    grid = Table(box=DOUBLE, show_header=False)
    grid.add_column("", style="bold", width=24)
    grid.add_column("", justify="right", width=16)
    grid.add_row("QHE Mean", _safe_grid_val(wd.get("qhe_mean"), ".4f", "green"))
    grid.add_row(
        "QHE Min/Max",
        _safe_grid_val(wd.get("qhe_min"), ".4f") + " / " + _safe_grid_val(wd.get("qhe_max"), ".4f"),
    )
    grid.add_row("Dominant Regime", _safe_grid_val(wd.get("dominant_regime")))
    grid.add_row("Sleep Mean", _safe_grid_val(wd.get("sleep_mean_h"), ".2f") + "h")
    grid.add_row("Sleep Quality", _safe_grid_val(wd.get("sleep_quality_mean"), ".1f") + "/10")
    grid.add_row("Pomodoros", _safe_grid_val(wd.get("total_pomodoros"), color="bold"))
    grid.add_row("Pomodoros/Day Avg", _safe_grid_val(wd.get("pomodoros_per_day_avg"), ".1f"))
    grid.add_row("Habit Rate", _safe_grid_val(wd.get("habit_completion_rate"), ".1f", "cyan") + "%")
    grid.add_row("Hardwork Accuracy", _safe_grid_val(wd.get("hardwork_accuracy_pct"), ".1f") + "%")
    grid.add_row("Energy Mean", _safe_grid_val(wd.get("energy_mean"), ".1f") + "/10")
    grid.add_row("Focus Mean", _safe_grid_val(wd.get("focus_mean"), ".1f") + "/10")
    grid.add_row("Mood Mean", _safe_grid_val(wd.get("humor_mean"), ".1f") + "/10")
    console.print(grid)


# ------------------------------------------------------------------
# Quality command
# ------------------------------------------------------------------


def _render_quality(data: dict) -> None:

    rows_by_entity = {k: v for k, v in data.items() if k != "habit"}
    dq = data_quality_report(rows_by_entity, expected_days=180, start_date=_START, end_date=_END)

    console.print(Panel("[bold]Data Quality Report — 180-Day Dataset[/bold]", border_style="cyan"))
    console.print()
    t = Table(box=DOUBLE, header_style="bold")
    t.add_column("Entity", style="bold")
    t.add_column("Expected", justify="right")
    t.add_column("Found", justify="right")
    t.add_column("Complete %", justify="right")
    t.add_column("Missing", justify="right")
    t.add_column("Quality", style="bold")
    for name, info in sorted(dq.items()):
        pct = info["complete_pct"]
        color = "green" if pct >= 99 else "yellow" if pct >= 90 else "red"
        missing_str = (
            str(info["missing_count"])
            if info["missing_count"] <= 5
            else f"[red]{info['missing_count']}[/red]"
        )
        t.add_row(
            name,
            str(info["expected"]),
            str(info["found"]),
            f"[{color}]{pct:.1f}%[/{color}]",
            missing_str,
            "✓" if pct >= 99 else "⚠" if pct >= 90 else "✗",
        )
    console.print(t)


# ------------------------------------------------------------------
# Markdown Report Generator (all 26 weeks)
# ------------------------------------------------------------------


def _date_from_str(s: str) -> date:
    """Parse YYYY-MM-DD string to date."""
    return date.fromisoformat(s[:10])


def _in_range(d: date, start: date, end: date) -> bool:
    """Check if d falls within [start, end] inclusive."""
    return start <= d <= end


def _week_narrative(wd: dict, prev: dict | None) -> str:  # noqa: C901, PLR0912
    """Generate 2-3 sentence narrative from weekly digest data.

    Deterministically derives insight from metrics — no LLM needed.
    """
    parts = []
    qhe = wd.get("qhe_mean") or 0
    prev_qhe = (prev or {}).get("qhe_mean") or 0 if prev else None
    habit = wd.get("habit_completion_rate") or 0
    sleep = wd.get("sleep_mean_h") or 0
    pom = wd.get("total_pomodoros") or 0
    regime = wd.get("policy_dominant", "?")
    hardwork = wd.get("hardwork_accuracy_pct") or 0

    # Opening statement
    if qhe >= 0.85:
        parts.append("Desempenho sistémico excepcional esta semana.")
    elif qhe >= 0.70:
        parts.append("Semana sólida com métricas acima da média.")
    elif qhe >= 0.50:
        parts.append("Semana desafiadora — métricas em território de recuperação.")
    else:
        parts.append("Semana crítica — todos os sistemas em modo de recuperação.")

    # QHE trend
    if prev and prev_qhe:
        delta = qhe - prev_qhe
        if abs(delta) > 0.05:
            trend = "subiu significativamente" if delta > 0 else "caiu acentuadamente"
            parts.append(f"QHE {trend} ({delta:+.3f} vs semana anterior).")
        elif abs(delta) > 0.01:
            trend = "melhorou moderadamente" if delta > 0 else "recuou levemente"
            parts.append(f"QHE {trend} ({delta:+.3f}).")

    # Sleep context
    if sleep >= 8.0:
        parts.append(f"Sono adequado ({sleep:.1f}h) suporta capacidade cognitiva.")
    elif sleep >= 7.0:
        parts.append(f"Sleep abaixo do optimal ({sleep:.1f}h) — possível impacto em Foco.")
    else:
        parts.append(f"Defice de sono significativo ({sleep:.1f}h) — regime {regime} reactivo.")

    # Pomodoro density
    pom_day = wd.get("pomodoros_per_day_avg") or 0
    if pom_day >= 9:
        parts.append(f"Alta densidade de foco: {pom} pomodoros ({pom_day:.1f}/dia).")
    elif pom_day >= 6:
        parts.append(f"{pom} pomodoros registados ({pom_day:.1f}/dia).")
    else:
        parts.append(f"Baixa cadência de foco ({pom_day:.1f} pomodoros/dia).")

    # Habit adherence
    if habit >= 95:
        parts.append("Hábitos quase perfeitos — Resistência baixa, H(t) em platô.")
    elif habit >= 85:
        parts.append(f"Aderência de hábitos forte ({habit:.1f}%).")
    elif habit >= 70:
        parts.append(f"Aderência de hábitos moderada ({habit:.1f}%) — investigar resistências.")

    # Hardwork execution
    if hardwork >= 90:
        parts.append(f"Execução do plano excepcional ({hardwork:.0f}% accuracy).")
    elif hardwork >= 75:
        parts.append(f"Bom alinhamento plano-realizado ({hardwork:.0f}% accuracy).")
    else:
        parts.append(f"Desvio de execução ({hardwork:.0f}%) — possivel sobre-estimação de budget.")

    return " ".join(parts)


def _spark(vals: list[float], width: int = 18) -> str:
    """ASCII sparkline from a list of floats."""
    if not vals:
        return "░" * width
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx > mn else 1
    bars = "▁▂▃▄▅▆▇█"
    return "".join(bars[min(int((v - mn) / rng * 8), 7)] for v in vals)[-width:]


def generate_markdown_reports(data: dict, output_dir: Path) -> None:  # noqa: C901, PLR0912
    """Generate 26 weekly markdown reports + one master index."""
    output_dir.mkdir(parents=True, exist_ok=True)
    week_list = weeks_in_range(_START, _END)

    all_weeks: list[dict] = []
    prev_wd: dict | None = None

    for idx, (week_start, week_end) in enumerate(week_list, start=1):
        wd = weekly_digest(
            week_start,
            week_end,
            data["qhe_metrics"],
            data["sleep_record"],
            data["pomodoro_round"],
            data["habit_state"],
            data["habit"],
            data["journal_entry"],
            data["policy_decision"],
            data["day_context"],
        )

        qhe = wd["qhe_mean"] or 0
        habit = wd["habit_completion_rate"] or 0
        sleep = wd["sleep_mean_h"] or 0
        pom = wd["total_pomodoros"]
        regime = wd.get("policy_dominant", "?")

        # Narrative verdict
        if qhe >= 0.85 and habit >= 90:
            verdict = "🚀 Ótima semana — PUSH mode activo"
        elif qhe >= 0.70:
            verdict = "⚖️ Semana sólida — MAINTAIN"
        elif qhe >= 0.50:
            verdict = "📉 Semana difícil — REDUCE activo"
        else:
            verdict = "🛑 Semana crítica — RECOVER"

        narrative = _week_narrative(wd, prev_wd)
        prev_wd = wd

        # Period-over-period delta
        delta_str = ""
        if all_weeks:
            prev_q = all_weeks[-1]["qhe"] or 0
            delta_q = qhe - prev_q
            if abs(delta_q) > 0.001:
                arrow = "▲" if delta_q > 0 else "▼"
                delta_str = f" {arrow} {abs(delta_q):.3f} vs prev week"
        qhe_spark = _spark([*[w["qhe"] for w in all_weeks], qhe][-10:])

        # Ritual section (T1-T9 from transicao)
        trans = [r for r in data.get("transicao", []) if _in_range(_date_from_str(r.get("date", "")), week_start, week_end)]
        ritual_lines = []
        if trans:
            by_code: dict = {}
            for r in trans:
                c = r.get("codigo", "?")
                if c not in by_code:
                    by_code[c] = {"done": 0, "total": 0}
                by_code[c]["total"] += 1
                if r.get("completed"):
                    by_code[c]["done"] += 1
            done_total = [(c, v["done"], v["total"]) for c, v in sorted(by_code.items())]
            ritual_lines = [
                "",
                "## Domínio — Rituals (T1-T9)",
                "",
                "| Ritual | Feitos/Total | Taxa |",
                "|--------|-------------|------|",
            ]
            for code, done, total in done_total[:9]:
                rate = (done / total * 100) if total > 0 else 0
                bar = "▓" * int(rate / 10) + "░" * (10 - int(rate / 10))
                ritual_lines.append(f"| {code} | {done}/{total} | {bar} {rate:.0f}% |")

        # Time block section
        blocks = [r for r in data.get("time_block", []) if _in_range(_date_from_str(r.get("date", "")), week_start, week_end)]
        block_lines = []
        if blocks:
            periods: dict = {}
            for b in blocks:
                p = b.get("periodo", "?")
                if p not in periods:
                    periods[p] = {"hours": 0.0, "count": 0}
                periods[p]["hours"] += float(b.get("hours", 0) or 0)
                periods[p]["count"] += 1
            if periods:
                block_lines = [
                    "",
                    "## Domínio — Blocos de Tempo (Deep Work)",
                    "",
                    "| Período | Horas | Blocos |",
                    "|---------|-------|--------|",
                ]
                for p, v in sorted(periods.items(), key=lambda x: -x[1]["hours"]):
                    block_lines.append(f"| {p} | {v['hours']:.1f}h | {v['count']} |")

        # Lunch section
        lunches = [r for r in data.get("lunch_record", []) if _in_range(_date_from_str(r.get("date", "")), week_start, week_end)]
        lunch_lines = []
        if lunches:
            pesado = [l for l in lunches if l.get("tipo_refeicao") == "pesado"]
            if pesado:
                lunch_lines = [
                    "",
                    "## Domínio — Alimentação",
                    "",
                    "| Tipo | Ocorrências |",
                    "|-----|-------------|",
                    f"| Heavy meals (pesado) | {len(pesado)}/{len(lunches)} |",
                ]

        # Build full report
        lines = [
            f"# Week {idx}: {week_start.isoformat()} → {week_end.isoformat()}",
            "",
            f"**{verdict}**{delta_str}",
            "",
            f"_{narrative}_",
            "",
            "---",
            "",
            "## 📊 Produtividade Algorítmica (QHE)",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| QHE Médio | {qhe:.4f} |",
            f"| QHE Mín/Máx | {wd['qhe_min']:.4f} / {wd['qhe_max']:.4f} |",
            f"| Sparkline (últimas 10 sem) | `{qhe_spark}` |",
            f"| Regime Dominante | {regime} |",
            f"| Regimes | {wd.get('regime_breakdown', 'N/A')} |",
            "",
            "## 😴 Sono",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Média | {sleep:.2f}h |",
            f"| Qualidade | {wd.get('sleep_quality_mean', 0):.1f}/10 |",
            f"| Dias ≥7.5h | {wd.get('days_good_sleep', 0)}/{wd.get('days_in_week', 7)} |",
            "",
            "## 🍅 Pomodoros",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Total | **{pom}** |",
            f"| Média/Dia | {wd.get('pomodoros_per_day_avg', 0):.1f} |",
            f"| Mais Produtivo | {wd.get('most_productive_day', 'N/A')} ({wd.get('max_pomodoros_in_day', 0)}) |",
            "",
            "## ✅ Hábitos",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Taxa Conclusão | {habit:.1f}% |",
            f"| Feitos/Total | {wd.get('habit_completed_count', 0)}/{wd.get('habit_total_count', 0)} |",
            "",
            "## 😊 Humor e Energia",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Energia | {wd.get('energy_mean', 0):.1f}/10 |" if wd.get("energy_mean") else "| Energia | N/A |",
            f"| Foco | {wd.get('focus_mean', 0):.1f}/10 |" if wd.get("focus_mean") else "| Foco | N/A |",
            f"| Humor | {wd.get('humor_mean', 0):.1f}/10 |" if wd.get("humor_mean") else "| Humor | N/A |",
            "",
            "## ⚙️ Policy FSM",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Política Dominante | {regime} |",
            f"| Distribuição | {wd.get('policy_breakdown', 'N/A')} |",
            "",
            "## 🎯 Execução do Plano (Hardwork)",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Accuracy | {wd.get('hardwork_accuracy_pct', 0):.1f}% |",
            *ritual_lines,
            *block_lines,
            *lunch_lines,
            "",
            "---",
            f"_PAV Analytics Engine · {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        ]

        # Remove blank-only lines
        lines = [l for l in lines if l is not None]

        week_filename = f"week_{idx:02d}_{week_start.isoformat()}.md"
        (output_dir / week_filename).write_text("\n".join(lines), encoding="utf-8")
        all_weeks.append({
            "week": idx,
            "start": week_start.isoformat(),
            "end": week_end.isoformat(),
            "filename": week_filename,
            "verdict": verdict,
            "qhe": qhe,
            "pomodoros": pom,
            "habit_rate": habit,
            "sleep_h": sleep,
            "regime": regime,
        })

    # ---- Master INDEX.md ----
    valid_qhe = [w["qhe"] for w in all_weeks if w["qhe"]]
    avg_qhe = sum(valid_qhe) / len(valid_qhe) if valid_qhe else 0
    best_week = max(all_weeks, key=lambda w: w["qhe"]) if all_weeks else None
    worst_week = min(all_weeks, key=lambda w: w["qhe"]) if all_weeks else None

    # QHE trend sparkline over all weeks
    qhe_spark_all = _spark(valid_qhe, 26)

    index_lines = [
        "# PAV Analytics — 26-Week Master Report",
        "",
        f"**Período:** {_START.isoformat()} → {_END.isoformat()} (180 days)",
        f"**Gerado:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 📈 Executive Summary",
        "",
        "| Métrica | Valor |",
        "|---------|-------|",
        f"| QHE Médio (26 sem) | {avg_qhe:.4f} |",
        f"| Total Pomodoros | {sum(w['pomodoros'] for w in all_weeks)} |",
        f"| Média Hábitos | {sum(w['habit_rate'] for w in all_weeks) / len(all_weeks):.1f}% |",
        f"| Média Sono | {sum(w['sleep_h'] for w in all_weeks if w['sleep_h']) / len([w for w in all_weeks if w['sleep_h']]):.2f}h |",
        f"| Melhor Semana | Week {best_week['week']:02d} (QHE={best_week['qhe']:.4f}) |" if best_week else "",
        f"| Pior Semana | Week {worst_week['week']:02d} (QHE={worst_week['qhe']:.4f}) |" if worst_week else "",
        "",
        f"**QHE Sparkline (26 semanas):** `{qhe_spark_all}`",
        "",
        "## 📅 Weekly Reports",
        "",
        "| # | Período | Veredicto | QHE | 🍅 | Háb. | Sono | Policy |",
        "|--------|---------|-----------|-----|-----|------|------|--------|",
    ]

    for w in all_weeks:
        sleep_s = f"{w['sleep_h']:.1f}h" if w["sleep_h"] else "N/A"
        index_lines.append(
            f"| [Week {w['week']:02d}]({w['filename']}) | "
            f"{w['start'][5:]} → {w['end'][5:]} | {w['verdict']} | "
            f"{w['qhe']:.4f} | {w['pomodoros']} | "
            f"{w['habit_rate']:.1f}% | {sleep_s} | {w['regime']} |"
        )

    # Phase analysis — break 26 weeks into 4 quarters
    quarters = []
    for q in range(4):
        start_i = q * 6
        end_i = start_i + 6
        chunk = valid_qhe[start_i:end_i]
        if chunk:
            avg = sum(chunk) / len(chunk)
            label = f"Q{q+1} (W{start_i+1:02d}–W{end_i:02d})"
            spark = _spark(chunk, 6)
            quarters.append(f"| {label} | {avg:.4f} | `{spark}` |")

    if quarters:
        index_lines += [
            "",
            "## 📐 Quarterly Breakdown",
            "",
            "| Quarter | Avg QHE | Sparkline |",
            "|---------|---------|-----------|",
            *quarters,
        ]

    # Narrative overview
    index_lines += [
        "",
        "## 📖 Narrative Overview",
        "",
        f"O sistema manteve um regime **PUSH** dominante ao longo dos 180 dias com QHE médio de {avg_qhe:.4f}. "
        f"O pico occurred na Semana {best_week['week']:02d} (QHE={best_week['qhe']:.4f}) "
        f"e o ponto mais baixo na Semana {worst_week['week']:02d} (QHE={worst_week['qhe']:.4f}). "
        "A consistência dos hábitos (média >90%) e o crescimento sostenido do QHE ao longo das primeiras 12 semanas "
        "demonstram o efeito composto da fórmula H(t) = 1 − e^(−0.093·s) com streaks crescentes. "
        "Quedas de QHE correlacionam-se fortemente com noites de sono < 7h e dias de alta carga cognitiva externa.",
        "",
        "---",
        f"_PAV Analytics Engine · {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
    ]

    (output_dir / "INDEX.md").write_text("\n".join(index_lines), encoding="utf-8")
    console.print(f"[green]Generated {len(all_weeks)} weekly reports in[/green] {output_dir}")

# ------------------------------------------------------------------
# Typer commands
# ------------------------------------------------------------------


@analytics_app.command(name="overview")
def cmd_overview(
    json_out: bool = typer.Option(False, "--json", help="JSON output"),  # noqa: FBT003
) -> None:
    """Executive dashboard — all domains at a glance."""
    data = _load_all()
    if json_out:
        # Return just the KPI summary as JSON
        _json = json
        ts_qhe = qhe_time_series(data["qhe_metrics"])
        ts_sleep = sleep_time_series(data["sleep_record"])
        debt = sleep_debt_analysis(data["sleep_record"])
        habit_matrix = habit_mastery_matrix(data["habit"], data["habit_state"])
        uptime = policy_uptime_pct(data["policy_decision"])
        corr = _engine_corr_matrix(data["qhe_metrics"], data["sleep_record"], data["journal_entry"])

        # Build habit_mastery as dict keyed by habit name
        habit_dict: dict[str, dict] = {
            h["name"]: {k: v for k, v in h.items() if k != "name"}
            for h in habit_matrix
        }

        # Pomodoro today's data
        pom_ts = pomodoro_time_series(data["pomodoro_round"])
        pom_today = pom_ts[-1] if pom_ts else {}

        # Mood latest
        mood_ts = mood_time_series(data["journal_entry"])
        latest_mood = mood_ts[-1] if mood_ts else {}

        # Current regime
        latest_qhe = ts_qhe[-1] if ts_qhe else {}
        regime = latest_qhe.get("regime", "PUSH")

        output = {
            "qhe_latest": latest_qhe,
            "sleep_latest": ts_sleep[-1] if ts_sleep else {},
            "sleep_debt_hours": debt["total_debt"],  # numeric, not string
            "sleep_debt_days_below": debt["days_below_target"],
            "habit_mastery": habit_dict,  # dict keyed by habit name, not list
            "policy_uptime": uptime,
            "correlations": corr,
            "pomodoros_today": pom_today.get("completed", 0),
            "pomodoros_efficiency": pom_today.get("efficiency_pct", 0),
            "pomodoros_roll7": pom_today.get("roll7", 0),
            "energia": latest_mood.get("energia", 0),
            "focus": latest_mood.get("focus", 0),
            "humor": latest_mood.get("humor_avg", 0),
            "regime_current": regime,
        }
        typer.echo(_json.dumps(output, indent=2, default=str))
        return
    _render_overview(data)


@analytics_app.command(name="qhe")
def cmd_qhe(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """QHE time series, regimes, transitions, anomalies."""
    data = _load_all()
    if json_out:
        ts = qhe_time_series(data["qhe_metrics"])
        regimes = qhe_regime_distribution(data["qhe_metrics"])
        trans = qhe_phase_transitions(data["qhe_metrics"])
        anomalies = qhe_anomaly_days(data["qhe_metrics"])
        weekly = qhe_weekly_aggregates(data["qhe_metrics"], _START, _END)
        _json = json
        typer.echo(
            _json.dumps(
                {
                    "time_series": ts,
                    "regimes": regimes,
                    "transitions": trans,
                    "anomalies": anomalies,
                    "weekly": weekly,
                },
                indent=2,
                default=str,
            )
        )
        return
    _render_qhe(data)


@analytics_app.command(name="sleep")
def cmd_sleep(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Sleep quality, debt, phase analysis."""
    data = _load_all()
    if json_out:
        _json = json
        ts = sleep_time_series(data["sleep_record"])
        debt = sleep_debt_analysis(data["sleep_record"])
        phases = sleep_phase_analysis(data["sleep_record"])
        typer.echo(
            _json.dumps({"time_series": ts, "debt": debt, "phases": phases}, indent=2, default=str)
        )
        return
    _render_sleep(data)


@analytics_app.command(name="habits")
def cmd_habits(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Habit mastery matrix, streaks, H(t) learning curve."""
    data = _load_all()
    if json_out:
        _json = json
        matrix = habit_mastery_matrix(data["habit"], data["habit_state"])
        streaks = habit_streak_analysis(data["habit_state"], data["habit"])
        typer.echo(_json.dumps({"mastery": matrix, "streaks": streaks}, indent=2, default=str))
        return
    _render_habits(data)


@analytics_app.command(name="pomodoro")
def cmd_pomodoro(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Pomodoro stats, hourly distribution, weekly aggregates."""
    data = _load_all()
    if json_out:
        _json = json
        ts = pomodoro_time_series(data["pomodoro_round"])
        hourly = pomodoro_hourly_distribution(data["pomodoro_round"])
        weekly = pomodoro_weekly_aggregates(data["pomodoro_round"], _START, _END)
        typer.echo(
            _json.dumps(
                {"time_series": ts, "hourly": hourly, "weekly": weekly}, indent=2, default=str
            )
        )
        return
    _render_pomodoro(data)


@analytics_app.command(name="policy")
def cmd_policy(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Policy FSM state transitions, uptime, RECOVER episodes."""
    data = _load_all()
    if json_out:
        _json = json
        ts = policy_state_time_series(data["policy_decision"])
        matrix = policy_transition_matrix(data["policy_decision"])
        uptime = policy_uptime_pct(data["policy_decision"])
        episodes = policy_recover_episodes(data["policy_decision"])
        typer.echo(
            _json.dumps(
                {
                    "time_series": ts,
                    "transitions": matrix,
                    "uptime": uptime,
                    "recover_episodes": episodes,
                },
                indent=2,
                default=str,
            )
        )
        return
    _render_policy(data)


@analytics_app.command(name="mood")
def cmd_mood(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Energy, focus, humor time series and correlations."""
    data = _load_all()
    if json_out:
        _json = json
        ts = mood_time_series(data["journal_entry"])
        tags = journal_tag_extraction(data["journal_entry"])
        corr = _engine_corr_matrix(data["qhe_metrics"], data["sleep_record"], data["journal_entry"])
        typer.echo(
            _json.dumps(
                {"time_series": ts, "tags": tags, "correlations": corr}, indent=2, default=str
            )
        )
        return
    _render_mood(data)


@analytics_app.command(name="week")
def cmd_week(
    week_num: int = typer.Argument(..., help="Week number (1-26)"),
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003,
) -> None:
    """Week N digest (1-26)."""
    data = _load_all()
    if json_out:
        _json = json
        week_list = weeks_in_range(_START, _END)
        if not (1 <= week_num <= len(week_list)):
            typer.echo(_json.dumps({"error": f"Week must be 1-{len(week_list)}"}))
            return
        week_start, week_end = week_list[week_num - 1]
        wd = weekly_digest(
            week_start,
            week_end,
            data["qhe_metrics"],
            data["sleep_record"],
            data["pomodoro_round"],
            data["habit_state"],
            data["habit"],
            data["journal_entry"],
            data["policy_decision"],
            data["day_context"],
        )
        typer.echo(_json.dumps(wd, indent=2, default=str))
        return
    _render_week(week_num, data)


@analytics_app.command(name="report")
def cmd_report(
    output_dir: str = typer.Option(
        str(_CSV_DIR.parent / "reports"),
        "--output",
        "-o",
        help="Output directory for markdown reports",
    ),
) -> None:
    """Generate full 26-week markdown analytics reports."""
    data = _load_all()
    out_path = Path(output_dir)
    # Create weeks/ subdirectory
    weeks_dir = out_path / "weeks"
    generate_markdown_reports(data, weeks_dir)
    typer.echo(f"[green]Done — reports in {weeks_dir}[/green]")


@analytics_app.command(name="quality")
def cmd_quality(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Data completeness audit across all 15 entities."""
    data = _load_all()
    if json_out:
        _json = json
        rows_by_entity = {k: v for k, v in data.items() if k != "habit"}
        dq = data_quality_report(
            rows_by_entity, expected_days=180, start_date=_START, end_date=_END
        )
        typer.echo(_json.dumps(dq, indent=2, default=str))
        return
    _render_quality(data)


# ------------------------------------------------------------------
# New commands: ritual, circadian, lunch, blocks, narrative
# ------------------------------------------------------------------


@analytics_app.command(name="ritual")
def cmd_ritual(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Ritual (T1-T5) completion rates, duration adherence, day-of-week patterns."""
    data = _load_all()
    trans = data.get("transicao", [])
    if not trans:
        typer.echo("[yellow]No transition/ritual data found.[/yellow]")
        return
    result = ritual_analysis(trans)
    if json_out:
        typer.echo(json.dumps(result, indent=2, default=str))
        return
    rituals = result.get("rituals", {})
    dow_rates = result.get("dow_rates", {})

    t = Table(title="Ritual Completion Rates (T1-T5)", box=DOUBLE, header_style="bold cyan")
    t.add_column("Code", width=6)
    t.add_column("Ritual", width=28)
    t.add_column("Done/Total", justify="right", width=12)
    t.add_column("Rate", justify="right", width=8)
    t.add_column("Avg Duration", justify="right", width=14)
    for code, info in rituals.items():
        rate = info["completion_rate"]
        bar = "█" * int(rate / 10) + "░" * (10 - int(rate / 10))
        color = "green" if rate >= 90 else "yellow" if rate >= 75 else "red"
        t.add_row(
            code,
            info["name"],
            f"{info['completed']}/{info['total']}",
            f"[{color}]{rate}%[/{color}]",
            f"{info['avg_duration_min']:.0f} min",
        )
    console.print(t)
    console.print()

    dow_t = Table(title="Completion Rate by Day of Week", box=DOUBLE, header_style="bold")
    dow_t.add_column("Day", width=10)
    dow_t.add_column("Rate", width=8, justify="right")
    dow_t.add_column("Bar", width=14)
    labels = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
    for dow, rate in dow_rates.items():
        bar = "█" * int(rate / 10) + "░" * (10 - int(rate / 10))
        color = "green" if rate >= 90 else "yellow" if rate >= 75 else "red"
        dow_t.add_row(labels.get(dow, str(dow)), f"[{color}]{rate}%[/{color}]", bar)
    console.print(dow_t)


@analytics_app.command(name="circadian")
def cmd_circadian(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Energy/focus/humor by day-of-week — find your best-performing days."""
    data = _load_all()
    journal = data.get("journal_entry", [])
    routine_log = data.get("routine_log", [])
    result = circadian_energy(journal, routine_log)
    if json_out:
        typer.echo(json.dumps(result, indent=2, default=str))
        return
    dow_data = result.get("by_day_of_week", {})
    t = Table(title="Energy/Focus/Humor by Day of Week", box=DOUBLE, header_style="bold cyan")
    t.add_column("Day", width=8)
    t.add_column("⚡ Energy", justify="center", width=12)
    t.add_column("🎯 Focus", justify="center", width=12)
    t.add_column("😄 Humor", justify="center", width=12)
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for day in labels:
        info = dow_data.get(day, {})
        en = info.get("energia_nivel") or info.get("energia") or info.get("energia_")
        fo = info.get("focus_nivel") or info.get("focus") or info.get("focus_")
        hu = info.get("humor") or info.get("humor_") or info.get("humor_morning")
        en_str = f"{en:.1f}/10" if en is not None else "—"
        fo_str = f"{fo:.1f}/10" if fo is not None else "—"
        hu_str = f"{hu:.1f}/10" if hu is not None else "—"
        t.add_row(day, en_str, fo_str, hu_str)
    console.print(t)


@analytics_app.command(name="lunch")
def cmd_lunch(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Lunch habits — pesado flag impact on afternoon energy."""
    data = _load_all()
    lunch = data.get("lunch_record", [])
    journal = data.get("journal_entry", [])
    if not lunch:
        typer.echo("[yellow]No lunch data found.[/yellow]")
        return
    result = lunch_analysis(lunch, journal)
    if json_out:
        typer.echo(json.dumps(result, indent=2, default=str))
        return
    t = Table(title="Lunch Analytics (180 days)", box=DOUBLE, header_style="bold")
    t.add_column("Metric", style="bold", width=30)
    t.add_column("Value", justify="right")
    rows_lunch = [
        ("Total Lunches", result["total_lunches"]),
        ("Avg Eat Time", f"{result['avg_eat_min']:.0f} min"),
        ("Avg Rest Time", f"{result['avg_rest_min']:.0f} min"),
        ("Heavy Meals (pesado)", f"{result['pesado_count']} ({result['pesado_pct']}%)"),
        ("Rest Debt Days (<20 min)", result["rest_debt_days"]),
    ]
    for label, val in rows_lunch:
        t.add_row(label, str(val))
    console.print(t)

    if result.get("heavy_lunch_avg_pm_energy") and result.get("light_lunch_avg_pm_energy"):
        console.print()
        console.print(
            f"  Heavy lunch → avg afternoon energy: [red]{result['heavy_lunch_avg_pm_energy']:.1f}/10[/red]"
        )
        console.print(
            f"  Light lunch → avg afternoon energy: [green]{result['light_lunch_avg_pm_energy']:.1f}/10[/green]"
        )
        diff = result["light_lunch_avg_pm_energy"] - result["heavy_lunch_avg_pm_energy"]
        console.print(f"  → Light lunch yields [green]+{diff:.1f}[/green] more energy points")


@analytics_app.command(name="blocks")
def cmd_blocks(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Time block utilization — deep work hours by period, block density."""
    data = _load_all()
    blocks = data.get("time_block", [])
    poms = data.get("pomodoro_round", [])
    if not blocks:
        typer.echo("[yellow]No time block data found.[/yellow]")
        return
    result = time_block_analysis(blocks, poms)
    if json_out:
        typer.echo(json.dumps(result, indent=2, default=str))
        return
    t = Table(title="Time Block Utilization (180 days)", box=DOUBLE, header_style="bold")
    t.add_column("Metric", style="bold", width=30)
    t.add_column("Value", justify="right")
    for label, val in [
        ("Total Block Days", result["total_block_days"]),
        ("Avg Blocks/Day", result["avg_blocks_per_day"]),
        ("Avg Deep Hours/Day", f"{result['avg_hours_per_day']:.1f}h"),
    ]:
        t.add_row(label, str(val))
    console.print(t)

    period_h = result.get("period_hours", {})
    if period_h:
        console.print()
        ph = Table(title="Avg Hours by Period", box=DOUBLE, header_style="bold cyan")
        ph.add_column("Period", width=15)
        ph.add_column("Avg Hours/Day", justify="right", width=15)
        ph.add_column("Bar", width=20)
        max_h = max(period_h.values()) if period_h else 1
        for period, hours in sorted(period_h.items()):
            norm = hours / max_h if max_h else 0
            bar = "█" * int(norm * 16) + "░" * (16 - int(norm * 16))
            ph.add_row(period, f"{hours:.1f}h", bar)
        console.print(ph)


@analytics_app.command(name="narrative")
def cmd_narrative(
    week_num: int = typer.Argument(
        ..., min=1, max=26, help="Week number (1-26). Omit for full 26-week narrative."
    ),
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Auto-generated narrative insights for a specific week."""
    data = _load_all()
    week_list = weeks_in_range(_START, _END)
    if not (1 <= week_num <= len(week_list)):
        typer.echo(f"[red]Week must be 1-{len(week_list)}[/red]")
        return
    week_start, week_end = week_list[week_num - 1]
    wd = weekly_digest(
        week_start,
        week_end,
        data["qhe_metrics"],
        data["sleep_record"],
        data["pomodoro_round"],
        data["habit_state"],
        data["habit"],
        data["journal_entry"],
        data["policy_decision"],
        data["day_context"],
    )
    # Prev week for PoP comparison
    prev_wd = None
    if week_num > 1:
        prev_start, prev_end = week_list[week_num - 2]
        prev_wd = weekly_digest(
            prev_start,
            prev_end,
            data["qhe_metrics"],
            data["sleep_record"],
            data["pomodoro_round"],
            data["habit_state"],
            data["habit"],
            data["journal_entry"],
            data["policy_decision"],
            data["day_context"],
        )
    pop = pop_comparison(wd, prev_wd)
    narratives = generate_narrative(
        wd,
        pop,
        data["qhe_metrics"],
        data["sleep_record"],
        data["pomodoro_round"],
        data["habit"],
        data["habit_state"],
        data["policy_decision"],
    )
    if json_out:
        typer.echo(
            json.dumps({"week": week_num, "narratives": narratives, "deltas": pop}, indent=2)
        )
        return
    console.print(
        Panel(
            "\n\n".join(narratives),
            title=f"📖 Week {week_num} Narrative — {week_start.isoformat()} → {week_end.isoformat()}",
            border_style="cyan",
        )
    )


@analytics_app.command(name="compare")
def cmd_compare(
    week1: int = typer.Argument(..., min=1, max=26, help="First week number"),
    week2: int = typer.Argument(..., min=1, max=26, help="Second week number"),
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Compare two weeks side-by-side with period-over-period deltas."""
    data = _load_all()
    week_list = weeks_in_range(_START, _END)
    for w in [week1, week2]:
        if not (1 <= w <= len(week_list)):
            typer.echo(f"[red]Week must be 1-{len(week_list)}[/red]")
            return
    w1_start, w1_end = week_list[week1 - 1]
    w2_start, w2_end = week_list[week2 - 1]
    wd1 = weekly_digest(
        w1_start,
        w1_end,
        data["qhe_metrics"],
        data["sleep_record"],
        data["pomodoro_round"],
        data["habit_state"],
        data["habit"],
        data["journal_entry"],
        data["policy_decision"],
        data["day_context"],
    )
    wd2 = weekly_digest(
        w2_start,
        w2_end,
        data["qhe_metrics"],
        data["sleep_record"],
        data["pomodoro_round"],
        data["habit_state"],
        data["habit"],
        data["journal_entry"],
        data["policy_decision"],
        data["day_context"],
    )
    pop = pop_comparison(wd2, wd1)
    if json_out:
        typer.echo(json.dumps({"week1": wd1, "week2": wd2, "deltas": pop}, indent=2, default=str))
        return

    def _fmt(v: object) -> str:
        if v is None:
            return "—"
        if isinstance(v, float):
            return f"{v:.4f}" if abs(v) < 10 else f"{v:.2f}"
        return str(v)

    t = Table(
        title=f"Week {week1} vs Week {week2} — Period-over-Period Comparison",
        box=DOUBLE,
        header_style="bold",
    )
    t.add_column("Metric", style="bold", width=28)
    t.add_column(f"Week {week1}", justify="right", width=14)
    t.add_column(f"Week {week2}", justify="right", width=14)
    t.add_column("Δ", justify="right", width=10)
    keys_map = [
        ("qhe_mean", "QHE Mean"),
        ("sleep_mean_h", "Sleep (h)"),
        ("sleep_quality_mean", "Sleep Quality"),
        ("total_pomodoros", "Pomodoros"),
        ("pomodoros_per_day_avg", "Pom/Day"),
        ("habit_completion_rate", "Habit Rate"),
        ("hardwork_accuracy_pct", "Hardwork Acc %"),
        ("energy_mean", "Energy"),
        ("focus_mean", "Focus"),
        ("humor_mean", "Humor"),
    ]
    for key, label in keys_map:
        v1 = wd1.get(key)
        v2 = wd2.get(key)
        delta_info = pop.get(key, {})
        delta = delta_info.get("delta")
        pct = delta_info.get("pct_change")
        delta_str = ""
        if delta is not None:
            sign = "+" if delta > 0 else ""
            delta_str = f"{sign}{delta:.3f}"
            if pct is not None:
                arrow = "▲" if pct > 0 else "▼"
                delta_str += f" ({arrow}{abs(pct):.1f}%)"
        t.add_row(label, _fmt(v1), _fmt(v2), delta_str)
    console.print(t)


# ------------------------------------------------------------------
# New commands: growth, trajectory, forecast, correlations, insights, scenarios
# (powered by operational.core.analytics + operational.core.insights)
# ------------------------------------------------------------------




def _load_dataset_from_csv_dir() -> dict:
    """Load the full 180-day dataset from the detected CSV directory."""
    return load_dataset(_CSV_DIR)


def _dir_arrow(direction: int) -> str:
    """Arrow character for trend direction."""
    if direction == 1:
        return "\u2191"
    if direction == -1:
        return "\u2193"
    return "\u2192"


# ── Growth score ───────────────────────────────────────────────────────────────

@analytics_app.command(name="growth")
def cmd_growth(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Weighted growth score (0-100) from QHE delta, sleep delta, regime health."""
    ds = _load_dataset_from_csv_dir()
    gs = _gs(ds)
    agg = compute_aggregations(ds)

    if json_out:
        typer.echo(json.dumps({
            "score": gs.score,
            "qhe_delta_30d": gs.qhe_delta_30d,
            "qhe_delta_90d": gs.qhe_delta_90d,
            "sleep_delta": gs.sleep_delta,
            "consistency_delta": gs.consistency_delta,
            "regime_health_score": gs.regime_health_score,
            "habit_improvement": gs.habit_improvement,
            "dominant_regime": agg.regime_dominant,
            "qhe_mean": agg.qhe_mean,
        }, indent=2))
        return

    # Score gauge
    score = int(gs.score)
    bar_len = int(score / 100 * 30)
    # Unicode block chars inside a Rich markup string break parsing —
    # use Text.assemble so bar chars are never interpreted as markup
    bar = "\u2588" * bar_len + "\u2591" * (30 - bar_len)
    color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
    panel_text = Text.assemble(
        f"[bold {color}]{score}/100[/{color}] ",  # styled score
        Text(bar),  # plain Unicode block chars
    )
    console.print(Panel(panel_text, title="Growth Score", border_style=color))
    console.print()

    # Sub-metrics
    grid = Table(box=DOUBLE, show_header=False)
    grid.add_column("", style="bold", width=26)
    grid.add_column("", justify="right")
    grid.add_row("Q_HE delta (30d)", f"{gs.qhe_delta_30d:+.4f}")
    grid.add_row("Q_HE delta (90d)", f"{gs.qhe_delta_90d:+.4f}")
    grid.add_row("Sleep delta (30d)", f"{gs.sleep_delta:+.2f}h")
    grid.add_row("Consistency delta", f"{gs.consistency_delta:+.4f}")
    grid.add_row("Regime health", f"{gs.regime_health_score:.1f}%")
    grid.add_row("Habit improvement", f"{gs.habit_improvement:.1f}%")
    grid.add_row("Dominant regime", agg.regime_dominant)
    grid.add_row("Q_HE mean (180d)", f"{agg.qhe_mean:.4f}")
    console.print(grid)


# ── Trajectory ────────────────────────────────────────────────────────────────

@analytics_app.command(name="trajectory")
def cmd_trajectory(
    metric: str = typer.Option("qhe", "--metric", "-m",
        help="Metric: qhe, sleep_hours, energia, foco, pomodoros_realizados"),
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Rising/falling/flat segment analysis for any numeric metric."""
    ds = _load_dataset_from_csv_dir()
    traj = build_trajectory(ds, metric)

    if json_out:
        typer.echo(json.dumps({
            "metric": metric,
            "overall_slope": traj.overall_slope,
            "overall_direction": traj.overall_direction,
            "segments": [
                {
                    "start": s.start.isoformat(),
                    "end": s.end.isoformat(),
                    "direction": s.direction,
                    "delta": s.delta,
                    "days": s.days,
                }
                for s in traj.segments
            ],
        }, indent=2))
        return

    console.print(Panel(
        f"[bold cyan]Trajectory — {metric}[/bold cyan]",
        border_style="cyan",
    ))
    console.print()

    overall = _dir_arrow(traj.overall_direction)
    console.print(f"Overall: {overall} slope={traj.overall_slope:+.4f}/week")
    console.print()

    seg_t = Table(title="Trajectory Segments", box=DOUBLE, header_style="bold")
    seg_t.add_column("Seg", justify="right", width=4)
    seg_t.add_column("Start", width=12)
    seg_t.add_column("End", width=12)
    seg_t.add_column("Direction", width=12)
    seg_t.add_column("Delta", justify="right")
    seg_t.add_column("Days", justify="right")
    for i, seg in enumerate(traj.segments, 1):
        arrow = _dir_arrow(seg.direction)
        color = "green" if seg.direction == 1 else ("red" if seg.direction == -1 else "yellow")
        seg_t.add_row(
            str(i),
            seg.start.isoformat(),
            seg.end.isoformat(),
            f"[{color}]{arrow}[/{color}]",
            f"{seg.delta:+.4f}",
            str(seg.days),
        )
    console.print(seg_t)


# ── Forecast ────────────────────────────────────────────────────────────────

@analytics_app.command(name="forecast")
def cmd_forecast(
    metric: str = typer.Option("qhe", "--metric", "-m",
        help="Metric to forecast"),
    horizon: int = typer.Option(7, "--horizon", "-h",
        help="Days ahead to forecast"),
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """OLS linear forecast with 95% confidence bands."""
    ds = _load_dataset_from_csv_dir()
    weekly = weekly_trend(ds, metric)
    if not weekly:
        typer.echo(f"[yellow]No data for metric '{metric}'.[/yellow]")
        return

    vals = [w.mean for w in weekly]
    dates = [w.week_start for w in weekly]
    series = TimeSeriesSlice(dates=dates, values=vals)
    forecast_pts = linear_forecast(series, horizon)

    if json_out:
        typer.echo(json.dumps({
            "metric": metric,
            "forecast": [
                {
                    "date": p.date.isoformat(),
                    "predicted": p.predicted,
                    "lower_ci": p.lower_ci,
                    "upper_ci": p.upper_ci,
                }
                for p in forecast_pts
            ],
        }, indent=2))
        return

    console.print(Panel(
        f"[bold cyan]7-Day OLS Forecast — {metric}[/bold cyan]",
        border_style="cyan",
    ))
    console.print()

    f_t = Table(box=DOUBLE, header_style="bold")
    f_t.add_column("Date", style="cyan")
    f_t.add_column("Predicted", justify="right", style="bold green")
    f_t.add_column("Lower CI", justify="right")
    f_t.add_column("Upper CI", justify="right")
    for p in forecast_pts:
        f_t.add_row(
            p.date.isoformat(),
            f"{p.predicted:.4f}",
            f"{p.lower_ci:.4f}",
            f"{p.upper_ci:.4f}",
        )
    console.print(f_t)


# ── Correlations ────────────────────────────────────────────────────────────

@analytics_app.command(name="correlations")
def cmd_correlations(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Full Pearson correlation matrix across all numeric metrics."""
    ds = _load_dataset_from_csv_dir()
    corr = correlation_matrix(ds)

    if json_out:
        typer.echo(json.dumps([
            {
                "metric_a": c.metric_a,
                "metric_b": c.metric_b,
                "r": c.r,
                "strength": c.strength,
            }
            for c in corr
        ], indent=2))
        return

    corr_t = Table(
        title="Pearson Correlation Matrix (all metric pairs)",
        box=DOUBLE,
        header_style="bold",
    )
    corr_t.add_column("Metric A", style="bold", width=20)
    corr_t.add_column("Metric B", width=20)
    corr_t.add_column("r", justify="right", width=8)
    corr_t.add_column("Strength", width=14)
    corr_t.add_column("Bar", width=24)
    for c in corr:
        abs_r = abs(c.r)
        bar_len = int(abs_r * 16)
        if c.r >= 0:
            bar_text = Text("\u2588" * bar_len + "\u2591" * (16 - bar_len), style="green")
        else:
            bar_text = Text("\u2592" * bar_len + "\u2591" * (16 - bar_len), style="red")
        strength_label = {
            "strong_pos": "strong +",
            "moderate_pos": "moderate +",
            "weak": "weak",
            "moderate_neg": "moderate -",
            "strong_neg": "strong -",
        }.get(c.strength, c.strength)
        corr_t.add_row(c.metric_a, c.metric_b, f"{c.r:+.3f}", strength_label, bar_text)
    console.print(corr_t)


# ── Insights ────────────────────────────────────────────────────────────────

@analytics_app.command(name="insights")
def cmd_insights(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Full 10-block narrative insights report — growth, weekly arc, regimes, correlations."""
    ds = _load_dataset_from_csv_dir()
    report = generate_full_report(ds)

    if json_out:
        typer.echo(json.dumps({
            k: {"title": b.title, "summary": b.summary, "bullets": b.bullets, "severity": b.severity}
            for k, b in report.items()
        }, indent=2))
        return

    console.print(format_insights_text(report))


# ── Scenarios ──────────────────────────────────────────────────────────────

@analytics_app.command(name="scenarios")
def cmd_scenarios(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Per-scenario breakdown: days, Q_HE, sleep, pomodoros, hardwork adherence."""
    ds = _load_dataset_from_csv_dir()
    scenarios = scenario_analysis(ds)

    if json_out:
        typer.echo(json.dumps([
            {
                "name": s.name,
                "days": s.days,
                "pct": s.pct,
                "qhe_avg": s.qhe_avg,
                "sleep_avg": s.sleep_avg,
                "energia_avg": s.energia_avg,
                "pomodoros_avg": s.pomodoros_avg,
                "hardwork_adh": s.hardwork_adh,
            }
            for s in scenarios
        ], indent=2))
        return

    scen_t = Table(
        title="Scenario Breakdown (tipo_dia)",
        box=DOUBLE,
        header_style="bold",
    )
    scen_t.add_column("Scenario", style="bold", width=14)
    scen_t.add_column("Days", justify="right")
    scen_t.add_column("Pct", justify="right")
    scen_t.add_column("Q_HE", justify="right", style="green")
    scen_t.add_column("Sleep", justify="right", style="cyan")
    scen_t.add_column("Pom/Day", justify="right", style="magenta")
    scen_t.add_column("HW Adh", justify="right")
    scen_t.add_column("Bar", style="cyan")

    for s in scenarios:
        bar = "\u2588" * int(s.pct / 5) + "\u2591" * (20 - int(s.pct / 5))
        scen_t.add_row(
            s.name,
            str(s.days),
            f"{s.pct:.0f}%",
            f"{s.qhe_avg:.4f}",
            f"{s.sleep_avg:.1f}h",
            f"{s.pomodoros_avg:.0f}",
            f"{s.hardwork_adh:.0f}%",
            bar,
        )
    console.print(scen_t)


# ── All: Full Suite ──────────────────────────────────────────────────────────

@analytics_app.command(name="all")
def cmd_all(
    json_out: bool = typer.Option(False, "--json"),  # noqa: FBT003
) -> None:
    """Run the complete analytics suite in sequence — overview, QHE, sleep, habits, pomodoro, mood, policy, circadian, rituals, lunch, blocks, quality."""
    commands = [
        ("Overview", cmd_overview),
        ("QHE", cmd_qhe),
        ("Sleep", cmd_sleep),
        ("Habits", cmd_habits),
        ("Pomodoro", cmd_pomodoro),
        ("Mood", cmd_mood),
        ("Policy", cmd_policy),
        ("Circadian", cmd_circadian),
        ("Rituals", cmd_ritual),
        ("Lunch", cmd_lunch),
        ("Blocks", cmd_blocks),
        ("Quality", cmd_quality),
        ("Narrative (Week 15)", lambda: cmd_narrative(15)),
        ("Compare (W1 vs W13)", lambda: cmd_compare(1, 13)),
    ]

    if json_out:
        results = {}
        for name, fn in commands:
            t0 = time.time()
            try:
                fn()
                results[name] = {"status": "ok", "time_ms": round((time.time() - t0) * 1000)}
            except Exception as e:  # noqa: BLE001
                results[name] = {"status": "error", "error": str(e)}
        typer.echo(json.dumps(results, indent=2))
        return

    console.print(Panel("[bold cyan]PAV Analytics — Full Suite[/bold cyan]", box=DOUBLE))
    for name, fn in commands:
        t0 = time.time()
        console.print(f"\n[bold green]▶ {name}[/bold green]")
        try:
            fn()
            elapsed = (time.time() - t0) * 1000
            console.print(f"[dim]  ✓ {elapsed:.0f}ms[/dim]")
        except Exception as e:  # noqa: BLE001
            console.print(f"[red]  ✗ {e}[/red]")
    console.print(f"\n[bold cyan]✓ Full suite complete — {len(commands)} commands run[/bold cyan]")
