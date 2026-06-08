"""Weekly report generator (PAV 🔟 — dashboard semanal & reports).

Aggregates 7 days of daily summaries into a markdown weekly report.
Includes sleep averages, health routine adherence, hardwork totals,
Cartesian plane quadrant distribution, and reflection prompts.
"""
from __future__ import annotations

from datetime import date, datetime

from operational.reports.daily_summary import calculate_efficiency, render_cartesian_ascii

__all__ = ["generate_weekly_report"]


# ---------------------------------------------------------------------------
# Weekly report
# ---------------------------------------------------------------------------


def generate_weekly_report(
    *,
    week_start: date,
    week_end: date,
    days_with_course: int = 0,
    days_without_course: int = 0,
    hardwork_total_minutes: int = 0,
    hardwork_budget_minutes: int = 1980,  # 33h default
    pomodoros_total: int = 0,
    pomodoros_budget: int = 0,
    sleep_hours_list: list[float] | None = None,
    sleep_quality_list: list[str | None] | None = None,
    workout_days: int = 0,
    meditation_days: int = 0,
    dinner_before_18_days: int = 0,
    no_blue_light_days: int = 0,
    daily_quadrants: list[tuple[float, float]] | None = None,
    reflections: list[str] | None = None,
) -> str:
    """Generate a weekly report in markdown format.

    Args:
        week_start: Monday of the week.
        week_end: Sunday of the week.
        days_with_course: Number of course days.
        days_without_course: Number of days without course.
        hardwork_total_minutes: Total hardwork minutes for the week.
        hardwork_budget_minutes: Total budgeted hardwork minutes.
        pomodoros_total: Total pomodoro rounds completed.
        pomodoros_budget: Total budgeted pomodoro rounds.
        sleep_hours_list: List of sleep hours per day (max 7).
        sleep_quality_list: List of sleep quality labels per day.
        workout_days: Number of days workout was completed.
        meditation_days: Number of days meditation was completed.
        dinner_before_18_days: Number of days dinner was before 18h.
        no_blue_light_days: Number of days with no blue light after 18h.
        daily_quadrants: List of (X, Y) tuples for each day's Cartesian position.
        reflections: Free-form reflection notes.

    Returns:
        Markdown-formatted weekly report.
    """
    lines: list[str] = []
    week_label = f"{week_start.isoformat()} to {week_end.isoformat()}"

    # Header
    lines.extend([
        "---",
        "type: weekly_report",
        f"week: {week_label}",
        f"generated_at: {datetime.now().isoformat()}",
        "---",
        "",
        f"# {chr(128200)} Weekly Report — {week_label}",
        "",
    ])

    # 1. General metrics
    lines.extend([
        f"## {chr(128200)} General Metrics",
        "| Metric | Value |",
        "|:-------|:-----:|",
    ])
    lines.append(f"| Course days | {days_with_course} / 7 |")
    lines.append(f"| Free days | {days_without_course} / 7 |")
    efficiency = calculate_efficiency(hardwork_budget_minutes, hardwork_total_minutes)
    lines.append(f"| Hardwork total | {hardwork_total_minutes}min ({hardwork_total_minutes // 60}h {hardwork_total_minutes % 60}m) |")
    lines.append(f"| Hardwork budget | {hardwork_budget_minutes}min ({hardwork_budget_minutes // 60}h {hardwork_budget_minutes % 60}m) |")
    lines.append(f"| Budget achieved | {efficiency:.0f}% |")
    lines.append(f"| Pomodoros | {pomodoros_total} / {pomodoros_budget} rounds |")

    # 2. Sleep
    sleep_hours_list = sleep_hours_list or []
    if sleep_hours_list:
        valid = [h for h in sleep_hours_list if h is not None and h > 0]
        avg_sleep = sum(valid) / len(valid) if valid else 0.0
        min_sleep = min(valid) if valid else 0.0
        max_sleep = max(valid) if valid else 0.0
        below_6 = sum(1 for h in valid if h < 6)
        healthy = sum(1 for h in valid if 7 <= h <= 9)
        above_9 = sum(1 for h in valid if h > 9)

        lines.extend([
            "",
            f"## {chr(128164)} Sleep (7 days)",
            "| Metric | Value |",
            "|:-------|:-----:|",
        ])
        lines.append(f"| Average | {avg_sleep:.1f}h |")
        lines.append(f"| Minimum | {min_sleep:.1f}h |")
        lines.append(f"| Maximum | {max_sleep:.1f}h |")
        lines.append(f"| Days < 6h | {below_6} |")
        lines.append(f"| Days 7-9h | {healthy} |")
        lines.append(f"| Days > 9h | {above_9} |")

    # 3. Health routines
    lines.extend([
        "",
        f"## {chr(127939)} Health Routines",
        "| Metric | Value |",
        "|:-------|:-----:|",
    ])
    lines.append(f"| Workout | {workout_days} / 7 days |")
    lines.append(f"| Meditation | {meditation_days} / 7 days |")
    lines.append(f"| Dinner before 18h | {dinner_before_18_days} / 7 days |")
    lines.append(f"| No blue light 18h+ | {no_blue_light_days} / 7 days |")

    # 4. Cartesian plane — weekly position
    prod_x = efficiency
    lines.extend([
        "",
        f"## {chr(128200)} Cartesian Plane — Weekly Position",
        f"**Average Productivity (X):** {prod_x:.0f}%",
        "",
    ])
    lines.append(render_cartesian_ascii(prod_x, _avg_y(daily_quadrants)))

    # Quadrant distribution
    if daily_quadrants:
        q1 = q2 = q3 = q4 = 0
        for x, y in daily_quadrants:
            if x >= 50 and y >= 50:
                q1 += 1
            elif x < 50 and y >= 50:
                q2 += 1
            elif x < 50 and y < 50:
                q3 += 1
            else:
                q4 += 1
        lines.extend([
            "",
            "### Quadrant Distribution",
            "| Q1 | Q2 | Q3 | Q4 |",
            "|:--:|:--:|:--:|:--:|",
            f"| {q1}d | {q2}d | {q3}d | {q4}d |",
        ])

    # 5. Weekly deliverables
    lines.extend([
        "",
        f"## {chr(127919)} Deliverables",
        "",
        "_(Add your completed tasks here)_",
        "",
        "| # | Task | Status |",
        "|:--:|:-----|:------:|",
        "| 1 | _ | _ |",
        "| 2 | _ | _ |",
        "| 3 | _ | _ |",
        "| 4 | _ | _ |",
        "| 5 | _ | _ |",
    ])

    # 6. Weekly reflection
    lines.extend([
        "",
        f"## {chr(128221)} Weekly Reflection",
        "",
    ])

    if reflections:
        for r in reflections:
            lines.append(f"- {r}")
    else:
        lines.extend([
            "**What worked well?**",
            "",
            "_",
            "",
            "**What needs improvement?**",
            "",
            "_",
            "",
            "**Adjustments for next week:**",
            "",
            "_",
        ])

    lines.append("")
    return "\n".join(lines)


def _avg_y(quadrants: list[tuple[float, float]] | None) -> float:
    """Average Y value from a list of (X, Y) tuples."""
    if not quadrants:
        return 50.0
    return sum(y for _, y in quadrants) / len(quadrants)
