"""Daily summary report generator (PAV §10 dashboard).

Produces a markdown-formatted end-of-day summary following the PAV §10
template with sleep, workout, hardwork, pomodoros, meals, transitions,
Cartesian plane, and deviations sections.
"""
from __future__ import annotations

from datetime import date, datetime

__all__ = [
    "calculate_efficiency",
    "generate_daily_summary",
    "render_cartesian_ascii",
]


# ---------------------------------------------------------------------------
# Core report generator
# ---------------------------------------------------------------------------


def generate_daily_summary(
    *,
    report_date: date,
    wake_hour: int | None = None,
    wake_minute: int | None = None,
    sleep_hour: int | None = None,
    sleep_minute: int | None = None,
    sleep_hours: float | None = None,
    sleep_quality: str | None = None,
    workout_done: bool | None = None,
    workout_minutes: int | None = None,
    meditation_done: bool | None = None,
    meditation_minutes: int | None = None,
    energia: int | None = None,
    day_type: str = "normal",
    hardwork_budget_minutes: int = 0,
    hardwork_actual_minutes: int = 0,
    pomodoros_completed: int = 0,
    pomodoros_budget: int = 0,
    lunch_eat_minutes: int = 5,
    lunch_rest_minutes: int = 30,
    dinner_before_18: bool | None = None,
    transitions_completed: int = 0,
    transitions_total: int = 9,
    desvios: list[str] | None = None,
    licoes: list[str] | None = None,
    ajustes: list[str] | None = None,
) -> str:
    """Generate a daily summary markdown report.

    Args:
        report_date: The date of the report.
        wake_hour: Hour of waking (0-23).
        wake_minute: Minute of waking (0-59).
        sleep_hour: Hour of sleeping (0-23).
        sleep_minute: Minute of sleeping (0-59).
        sleep_hours: Total sleep duration in hours.
        sleep_quality: Quality label (``excelente``, ``bom``, ``regular``, ``ruim``).
        workout_done: Whether workout was completed.
        workout_minutes: Workout duration in minutes.
        meditation_done: Whether meditation was completed.
        meditation_minutes: Meditation duration in minutes.
        energia: Energy level (1-10).
        day_type: ``"curso"``, ``"sem_curso"``, ``"hardcore"``, or ``"normal"``.
        hardwork_budget_minutes: Budgeted hardwork minutes.
        hardwork_actual_minutes: Actual hardwork minutes.
        pomodoros_completed: Number of pomodoro rounds completed.
        pomodoros_budget: Budgeted pomodoro rounds.
        lunch_eat_minutes: Minutes spent eating lunch.
        lunch_rest_minutes: Minutes spent resting after lunch.
        dinner_before_18: Whether dinner was before 18h.
        transitions_completed: Number of transitions completed.
        transitions_total: Total expected transitions (default 9).
        desvios: List of deviation descriptions.
        licoes: List of lessons learned.
        ajustes: List of fine adjustments.

    Returns:
        Markdown-formatted daily summary.
    """
    lines: list[str] = []
    date_str = report_date.isoformat()

    # Header
    lines.extend([
        "---",
        "type: daily_summary",
        f"date: {date_str}",
        f"generated_at: {datetime.now().isoformat()}",
        "---",
        "",
        f"# {chr(128200)} Daily Summary — {date_str}",
        "",
    ])

    # 1. Time
    lines.extend([
        f"## {chr(9200)} Time",
        "| Metric | Value |",
        "|:-------|:-----:|",
    ])
    if wake_hour is not None:
        lines.append(f"| Wake | {wake_hour:02d}:{wake_minute or 0:02d} |")
    if sleep_hour is not None:
        lines.append(f"| Sleep | {sleep_hour:02d}:{sleep_minute or 0:02d} |")
    if sleep_hours is not None:
        lines.append(f"| Sleep duration | {sleep_hours:.1f}h |")
    if sleep_quality:
        lines.append(f"| Sleep quality | {sleep_quality} |")

    # 2. Health
    lines.extend([
        "",
        f"## {chr(127939)} Health & Routines",
        "| Metric | Value |",
        "|:-------|:-----:|",
    ])
    if workout_done is not None:
        status = "Done" if workout_done else "Not done" if workout_done is False else ""
        dur = f" ({workout_minutes}min)" if workout_minutes else ""
        lines.append(f"| Workout | {status}{dur} |")
    if meditation_done is not None:
        status = "Done" if meditation_done else "Not done"
        dur = f" ({meditation_minutes}min)" if meditation_minutes else ""
        lines.append(f"| Meditation | {status}{dur} |")
    if energia is not None:
        bar = _ascii_bar(energia, 10)
        lines.append(f"| Energy | {energia}/10 {bar} |")

    # 3. Hardwork
    lines.extend([
        "",
        f"## {chr(128187)} Hardwork",
        "| Metric | Value |",
        "|:-------|:-----:|",
    ])
    day_type_labels = {"curso": "Course day", "sem_curso": "No-course day",
                       "hardcore": "Hardcore", "normal": "Normal"}
    lines.append(f"| Day type | {day_type_labels.get(day_type, day_type)} |")

    efficiency_pct = calculate_efficiency(hardwork_budget_minutes, hardwork_actual_minutes)
    lines.append(f"| Budget | {hardwork_budget_minutes}min |")
    lines.append(f"| Actual | {hardwork_actual_minutes}min |")
    lines.append(f"| Efficiency | {efficiency_pct:.0f}% |")
    lines.append(f"| Pomodoros | {pomodoros_completed}/{pomodoros_budget} rounds |")

    # 4. Cartesian plane
    prod_x = calculate_efficiency(hardwork_budget_minutes, hardwork_actual_minutes)
    lines.extend([
        "",
        f"## {chr(128200)} Cartesian Analysis",
        f"**Productivity (X):** {prod_x:.0f}%  —  **Efficiency (Y):** {efficiency_pct:.0f}%",
        "",
    ])
    lines.append(render_cartesian_ascii(prod_x, efficiency_pct))

    # 5. Meals & transitions
    lines.extend([
        "",
        f"## {chr(127869)} Meals & Transitions",
        "| Metric | Value |",
        "|:-------|:-----:|",
    ])
    lines.append(f"| Lunch eat | {lunch_eat_minutes}min |")
    lines.append(f"| Lunch rest | {lunch_rest_minutes}min |")
    if dinner_before_18 is not None:
        lines.append(f"| Dinner before 18h | {'Yes' if dinner_before_18 else 'No'} |")
    lines.append(f"| Transitions | {transitions_completed}/{transitions_total} |")

    # 6. Deviations & lessons
    if desvios:
        lines.extend([
            "",
            f"## {chr(9888)} Deviations",
        ])
        for d in desvios:
            lines.append(f"- {d}")

    if ajustes:
        lines.extend([
            "",
            f"## {chr(128295)} Fine Adjustments",
        ])
        for a in ajustes:
            lines.append(f"- {a}")

    if licoes:
        lines.extend([
            "",
            f"## {chr(128218)} Lessons Learned",
        ])
        for l in licoes:
            lines.append(f"- {l}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cartesian plane
# ---------------------------------------------------------------------------


def render_cartesian_ascii(produtividade_x: float, eficiencia_y: float) -> str:
    """Render a 10x10 ASCII Cartesian plane with the given point.

    Args:
        produtividade_x: X axis value (0-100).
        eficiencia_y: Y axis value (0-100).

    Returns:
        A 16-line ASCII grid with the point plotted.
    """
    x = max(0, min(100, produtividade_x))
    y = max(0, min(100, eficiencia_y))
    px = round(x / 10)
    py = round(y / 10)

    lines: list[str] = []
    lines.append("```")
    lines.append("  Y (Efficiency %)")
    lines.append("  \u2191")

    for row in range(10, -1, -1):
        label = f"{row * 10:3d}% " if row % 2 == 0 or row == 10 else "    |"
        line_chars: list[str] = []
        for col in range(11):
            is_point = (col == px and row == py)
            is_origin = (col == 0 and row == 0)
            is_axis = (col == 0 or row == 0)
            if is_point and not is_origin:
                line_chars.append("\u2022")
            elif is_origin:
                line_chars.append("+")
            elif col == 0:
                line_chars.append("|")
            elif row == 0:
                line_chars.append("-")
            else:
                line_chars.append(" ")
        lines.append(f"{label} {''.join(line_chars)}")

    lines.append("     0%---+----+----+----+----+----+----+----+----+----+---> X")
    lines.append("     0%  10%  20%  30%  40%  50%  60%  70%  80%  90% 100%")
    lines.append(f"     (X={produtividade_x:.0f}%, Y={eficiencia_y:.0f}%)")
    lines.append("```")

    # Quadrant classification
    if x >= 50 and y >= 50:
        if x >= 80 and y >= 80:
            quad = "Q1 (Excellent — maintain pace, monitor fatigue)"
        else:
            quad = "Q1 (Good — keep rhythm)"
    elif x < 50 and y >= 50:
        quad = "Q2 (Optimized but low output — increase volume)"
    elif x < 50 and y < 50:
        quad = "Q3 (Critical — review system, identify blockers)"
    else:
        quad = "Q4 (Productive but needs optimization — reduce distractions)"

    lines.append(f"  **Quadrant:** {quad}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def calculate_efficiency(budget: int, actual: int) -> float:
    """Calculate efficiency as percentage of budget achieved.

    Args:
        budget: Planned minutes.
        actual: Actual minutes.

    Returns:
        Percentage (0-100). Returns 0 if budget is 0.
    """
    if budget <= 0:
        return 0.0
    return min(100.0, (actual / budget) * 100.0)


def _ascii_bar(value: int, total: int = 10) -> str:
    """Render an ASCII bar like ``"[####......]"``."""
    filled = max(0, min(total, value))
    empty = total - filled
    return "[" + "#" * filled + "." * empty + "]"
