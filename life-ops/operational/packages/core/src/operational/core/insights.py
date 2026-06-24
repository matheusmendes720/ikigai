r"""PAV Insights Engine -- narrative generation from pure analytics data.

All insights are computed from analytics.py output -- no LLM, no I/O here.
Each function returns a structured dict (not a string) so CLI/TUI can
format as they wish.

Usage:
    from operational.core.insights import generate_full_report
    insights = generate_full_report(data, agg, traj, corr, gs)
    for k, v in insights.items():
        print(f"## {k}\n{v['summary']}\n")
"""
from __future__ import annotations

from dataclasses import dataclass

from operational.core.analytics import (
    Aggregations,
    CorrelationPair,
    Dataset,
    GrowthScore,
    HabitStats,
    RegimeStats,
    ScenarioStats,
    Trajectory,
    WeeklyTrend,
    build_trajectory,
    compute_aggregations,
    correlation_matrix,
    float_col,
    growth_score,
    habit_analytics,
    linear_forecast,
    regime_analysis,
    regime_timeline,
    scenario_analysis,
    weekly_trend,
)

# ── Threshold constants ─────────────────────────────────────────────────────────
_THRESHOLD_SCORE_OUTSTANDING = 80.0
_THRESHOLD_SCORE_SOLID = 60.0
_THRESHOLD_SCORE_FLAT = 40.0
_THRESHOLD_PUSH_PCT_HEALTHY = 70.0
_THRESHOLD_PUSH_PCT_MIXED = 50.0
_THRESHOLD_CORR_STRONG = 0.8
_THRESHOLD_CORR_MODERATE = 0.5
_THRESHOLD_HABIT_EXCELLENT = 0.85
_THRESHOLD_HABIT_DECENT = 0.65
_THRESHOLD_POM_EXCELLENT = 9.0
_THRESHOLD_POM_DECENT = 6.0
_THRESHOLD_SLEEP_GAP_MILD = 0.5
_SLOPE_FLAT = 0.001
_SLEEP_TARGET = 8.0
_RANK_GOLD = 1
_RANK_SILVER = 2
_EMOJI_GOLD = "\U0001f947"
_EMOJI_SILVER = "\U0001f948"

# ── Insight containers ─────────────────────────────────────────────────────────

@dataclass
class InsightBlock:
    """A single insight block with title, summary, bullets, and severity."""

    title: str
    summary: str
    bullets: list[str]
    severity: str  # "info" | "positive" | "warning" | "critical"


FullReport = dict[str, InsightBlock]


# ── Naming helpers ─────────────────────────────────────────────────────────────

_ARROW_UP = "\u2191"
_ARROW_DOWN = "\u2193"
_ARROW_FLAT = "\u2192"


def _dir_arrow(direction: int) -> str:
    if direction == 1:
        return _ARROW_UP
    if direction == -1:
        return _ARROW_DOWN
    return _ARROW_FLAT


def _pct_piece(val: float) -> str:
    return f"{val:.1f}%"


def _sev_emoji(sev: str) -> str:
    return {
        "positive": "\u2705",
        "warning": "\u26a0\ufe0f",
        "critical": "\ud83d\udea8",
        "info": "\u2139\ufe0f",
    }.get(sev, "")


# ── Insight generators ──────────────────────────────────────────────────────────

def _growth_story(gs: GrowthScore, agg: Aggregations) -> InsightBlock:
    score = gs.score
    if score >= _THRESHOLD_SCORE_OUTSTANDING:
        verdict = "Outstanding trajectory"
        sev = "positive"
        bullets = [
            f"Q_HE +{gs.qhe_delta_90d:+.4f} over 90 days -- momentum is real",
            f"Sleep delta: {gs.sleep_delta:+.1f}h vs prior 30-day window",
            f"Regime health: {gs.regime_health_score:.0f}% of days in PUSH/MAINTAIN",
            f"Habit completion: {gs.habit_improvement:.0f}% across all tracked habits",
        ]
    elif score >= _THRESHOLD_SCORE_SOLID:
        verdict = "Solid growth"
        sev = "positive"
        bullets = [
            f"Q_HE {gs.qhe_delta_90d:+.4f} over 90 days -- moving in the right direction",
            f"Sleep delta: {gs.sleep_delta:+.1f}h vs prior window",
            f"Regime health: {gs.regime_health_score:.0f}% in productive regimes",
            f"Consistency delta: {gs.consistency_delta:+.4f}",
        ]
    elif score >= _THRESHOLD_SCORE_FLAT:
        verdict = "Flat -- strategic adjustment needed"
        sev = "warning"
        bullets = [
            f"Q_HE barely moved: {gs.qhe_delta_90d:+.4f} in 90 days",
            f"Regime health: {gs.regime_health_score:.0f}% -- too much RECOVER time",
            "Consider tightening sleep window to push consistency",
        ]
    else:
        verdict = "Struggling -- full reset required"
        sev = "critical"
        bullets = [
            f"Q_HE fell {gs.qhe_delta_90d:+.4f} over 90 days",
            f"Regime health only {gs.regime_health_score:.0f}%",
            "Back to RECOVER -- rebuild from habit fundamentals",
        ]

    dom_pct = agg.regime_distribution.get(agg.regime_dominant, 0) / agg.n_days * 100
    summary = (
        f"{verdict}. Growth score {score:.0f}/100. "
        f"Current regime dominant: {agg.regime_dominant} "
        f"({_pct_piece(dom_pct)} of {agg.n_days} days). "
        f"Average Q_HE: {agg.qhe_mean:.4f} +/- {agg.qhe_std:.4f}, "
        f"range [{agg.qhe_min:.4f}--{agg.qhe_max:.4f}]."
    )
    return InsightBlock(title="Growth Story (180d)", summary=summary, bullets=bullets, severity=sev)


def _weekly_arc(traj: list[WeeklyTrend]) -> InsightBlock:
    if not traj:
        return InsightBlock(
            title="Weekly Arc", summary="Insufficient data.", bullets=[], severity="info"
        )

    first = traj[0]
    last = traj[-1]
    arc = last.mean - first.mean
    arc_pct = (arc / first.mean * 100) if first.mean != 0 else 0
    direction = _dir_arrow(1 if arc > _SLOPE_FLAT else (-1 if arc < -_SLOPE_FLAT else 0))

    best = max(traj, key=lambda w: w.mean)
    worst = min(traj, key=lambda w: w.mean)

    improving_streak = 0
    max_streak = 0
    for w in traj:
        if w.trend == 1:
            improving_streak += 1
            max_streak = max(max_streak, improving_streak)
        else:
            improving_streak = 0

    arc_label = f"{direction} {abs(arc_pct):.1f}% from week 1 to week {len(traj)}"
    summary = (
        f"Week 1 average Q_HE: {first.mean:.4f} | "
        f"Last week ({last.week}): {last.mean:.4f}. "
        f"{arc_label}. "
        f"Best week: W{best.week} ({best.mean:.4f}). "
        f"Worst week: W{worst.week} ({worst.mean:.4f}). "
        f"Peak improving streak: {max_streak} consecutive weeks."
    )

    bullets = [
        f"Start: {first.week_start} -> End: {last.week_end}",
        f"First-week mean: {first.mean:.4f} (std={first.std:.4f})",
        f"Last-week mean: {last.mean:.4f} (std={last.std:.4f})",
        f"Best: W{best.week} {best.week_start}--{best.week_end} -> {best.mean:.4f}",
        f"Worst: W{worst.week} {worst.week_start}--{worst.week_end} -> {worst.mean:.4f}",
        f"Consecutive improving weeks (max): {max_streak}",
    ]
    sev = "positive" if arc > 0 else "warning"
    return InsightBlock(title="Weekly Arc", summary=summary, bullets=bullets, severity=sev)


def _regime_transitions(regimes: list[RegimeStats], ds: Dataset) -> InsightBlock:
    if not regimes:
        return InsightBlock(
            title="Regime Analysis", summary="No regime data.", bullets=[], severity="info"
        )

    timeline = regime_timeline(ds)
    push_days = sum(1 for _, s in timeline if s == "PUSH")
    recover_days = sum(1 for _, s in timeline if s == "RECOVER")
    total = len(timeline) or 1

    transitions = []
    prev_s = ""
    for d, s in timeline:
        if prev_s and s != prev_s:
            transitions.append((prev_s, s, d))
        prev_s = s

    push_pct = push_days / total * 100
    if push_pct >= _THRESHOLD_PUSH_PCT_HEALTHY:
        sev = "positive"
        summary = (
            f"Healthy regime mix. PUSH dominates {push_pct:.0f}% of the time "
            f"({push_days}/{total} days). RECOVER only {recover_days}d "
            f"({recover_days / total * 100:.0f}%). "
            f"{len(transitions)} regime transitions observed."
        )
    elif push_pct >= _THRESHOLD_PUSH_PCT_MIXED:
        sev = "warning"
        summary = (
            f"Mixed regime performance. PUSH {push_pct:.0f}% ({push_days}d), "
            f"RECOVER {recover_days}d ({recover_days / total * 100:.0f}%). "
            "Consider whether RECOVER days are too frequent."
        )
    else:
        sev = "critical"
        summary = (
            f"Too much recovery time. PUSH only {push_pct:.0f}% ({push_days}d), "
            f"RECOVER {recover_days}d ({recover_days / total * 100:.0f}%). "
            "System is under-powered -- revisit fundamentals."
        )

    bullets = [
        f"PUSH days: {push_days}/{total} ({push_pct:.0f}%)",
        f"RECOVER days: {recover_days}/{total} ({recover_days / total * 100:.0f}%)",
        f"Total transitions: {len(transitions)}",
    ]
    for from_s, to_s, d in transitions[-5:]:
        bullets.append(f"  {from_s} -> {to_s} on {d}")

    return InsightBlock(title="Regime Analysis", summary=summary, bullets=bullets, severity=sev)


def _correlation_narrative(corr: list[CorrelationPair]) -> InsightBlock:
    if not corr:
        return InsightBlock(
            title="Key Correlations", summary="Insufficient data.", bullets=[], severity="info"
        )

    strong_pos = [c for c in corr if c.strength == "strong_pos"]
    strong_neg = [c for c in corr if c.strength == "strong_neg"]
    moderate = [c for c in corr if "moderate" in c.strength]

    top = corr[0]
    if abs(top.r) >= _THRESHOLD_CORR_STRONG:
        sev = "positive"
        insight = (
            f"Strong positive link between **{top.metric_a}** and **{top.metric_b}** "
            f"(r={top.r:.3f}). Improving one directly lifts the other."
        )
    elif abs(top.r) >= _THRESHOLD_CORR_MODERATE:
        sev = "positive"
        insight = f"Moderate correlation {top.metric_a} <-> {top.metric_b} (r={top.r:.3f})."
    else:
        sev = "info"
        insight = f"Weakest signals: {top.metric_a} <-> {top.metric_b} (r={top.r:.3f})."

    pos_bullets = [
        f"  {c.metric_a} <-> {c.metric_b}: r={c.r:.3f} (strong positive)"
        for c in strong_pos[:3]
    ]
    neg_bullets = [
        f"  {c.metric_a} <-> {c.metric_b}: r={c.r:.3f} (strong negative)"
        for c in strong_neg[:3]
    ]
    bullets = pos_bullets + neg_bullets
    if moderate:
        bullets.append(f"  + {len(moderate)} moderate correlations (0.4 <= |r| < 0.7)")

    return InsightBlock(title="Key Correlations", summary=insight, bullets=bullets, severity=sev)


def _scenario_narrative(scenarios: list[ScenarioStats]) -> InsightBlock:
    if not scenarios:
        return InsightBlock(
            title="Scenario Analysis", summary="No scenario data.", bullets=[], severity="info"
        )

    top = scenarios[0]
    summary = (
        f"'{top.name}' is the dominant day type: {top.days} days ({top.pct:.0f}%). "
        f"In those days: Q_HE avg {top.qhe_avg:.4f}, sleep {top.sleep_avg:.1f}h, "
        f"pomodoros {top.pomodoros_avg:.0f}, hardwork adherence {top.hardwork_adh:.0f}%."
    )

    bullets = []
    for s in scenarios[:6]:
        if s.rank <= _RANK_GOLD:
            rank_emoji = _EMOJI_GOLD
        elif s.rank <= _RANK_SILVER:
            rank_emoji = _EMOJI_SILVER
        else:
            rank_emoji = ""
        bullets.append(
            f"  {rank_emoji} {s.name}: {s.days}d ({s.pct:.0f}%) | "
            f"Q_HE={s.qhe_avg:.3f} | sleep={s.sleep_avg:.1f}h | "
            f"pom={s.pomodoros_avg:.0f} | adh={s.hardwork_adh:.0f}%"
        )
        s.rank = getattr(s, "rank", 0)

    return InsightBlock(
        title="Scenario Analysis", summary=summary, bullets=bullets, severity="info"
    )


def _habit_narrative(habits: list[HabitStats]) -> InsightBlock:
    if not habits:
        return InsightBlock(
            title="Habit Performance", summary="No habit data.", bullets=[], severity="info"
        )

    top = habits[0]
    lagging = sorted(habits, key=lambda h: h.completion_rate)[0]
    avg_rate = sum(h.completion_rate for h in habits) / len(habits)

    if avg_rate >= _THRESHOLD_HABIT_EXCELLENT:
        sev = "positive"
        verdict = "Excellent habit consistency"
    elif avg_rate >= _THRESHOLD_HABIT_DECENT:
        sev = "warning"
        verdict = "Room to improve"
    else:
        sev = "critical"
        verdict = "Habit foundation needs work"

    summary = (
        f"{verdict}. {len(habits)} habits tracked. "
        f"Top performer: **{top.habit_name}** ({top.completion_rate * 100:.0f}% completion, "
        f"{top.current_streak}d streak). "
        f"Lagging: **{lagging.habit_name}** ({lagging.completion_rate * 100:.0f}% completion). "
        f"Team average: {avg_rate * 100:.0f}%."
    )

    bullets = []
    for h in habits[:6]:
        bar = "\u2588" * int(h.completion_rate * 10) + "\u2591" * (10 - int(h.completion_rate * 10))
        bullets.append(
            f"  {h.habit_name} [{bar}] {h.completion_rate * 100:.0f}% "
            f"(streak={h.current_streak}d, effort={h.avg_effort_minutes:.0f}min)"
        )

    return InsightBlock(title="Habit Performance", summary=summary, bullets=bullets, severity=sev)


def _trajectory_segments(traj: Trajectory) -> InsightBlock:
    if not traj.segments:
        return InsightBlock(
            title="Trajectory Segments",
            summary="Insufficient data for segmentation.",
            bullets=[],
            severity="info",
        )

    segments = traj.segments
    rising = [s for s in segments if s.direction == 1]
    falling = [s for s in segments if s.direction == -1]

    summary = (
        f"{len(rising)} rising segment(s), {len(falling)} falling, "
        f"{len(segments) - len(rising) - len(falling)} flat. "
        f"Overall direction: {_dir_arrow(traj.overall_direction)} "
        f"(slope {traj.overall_slope:+.4f}/week). "
        f"Total span: {segments[0].start} -> {segments[-1].end}."
    )

    bullets = []
    for i, seg in enumerate(segments, 1):
        arrow = _dir_arrow(seg.direction)
        bullets.append(
            f"  Seg {i}: {seg.start}--{seg.end} "
            f"{arrow} {seg.delta:+.4f} ({seg.days}d) "
            f"[{seg.start_val:.4f} -> {seg.end_val:.4f}]"
        )

    sev = "positive" if rising else "warning"
    return InsightBlock(title="Trajectory Segments", summary=summary, bullets=bullets, severity=sev)


def _sleep_analysis(ds: Dataset, agg: Aggregations) -> InsightBlock:
    sleep_rows = ds.get("sleep_record", [])
    if not sleep_rows:
        return InsightBlock(
            title="Sleep Analysis", summary="No sleep data.", bullets=[], severity="info"
        )

    _, quality_vals = float_col(sleep_rows, "date", "quality_score")

    avg_h = agg.sleep_mean
    avg_q = sum(quality_vals) / len(quality_vals) if quality_vals else 0
    deficit_h = _SLEEP_TARGET - avg_h

    if deficit_h <= 0:
        sev = "positive"
        summary = f"Sleep is on target: {avg_h:.1f}h/night (avg quality {avg_q:.1f}/10). "
    elif deficit_h <= _THRESHOLD_SLEEP_GAP_MILD:
        sev = "warning"
        summary = (
            f"Mild sleep deficit: {avg_h:.1f}h/night "
            f"(target 8.0h, gap {deficit_h:+.1f}h). "
        )
    else:
        sev = "critical"
        summary = (
            f"Sleep debt accumulating: {avg_h:.1f}h/night "
            f"(target 8.0h, gap {deficit_h:+.1f}h). "
        )

    summary += (
        f"Sleep variability (std): {agg.sleep_std:.2f}h. "
        "Regime health is closely tied to this."
    )

    bullets = [
        f"Average: {avg_h:.2f}h/night (target: 8.0h, deficit: {deficit_h:+.2f}h)",
        f"Quality avg: {avg_q:.1f}/10",
        f"Variability (std): {agg.sleep_std:.2f}h -- lower is better",
        f"Min night: {agg.sleep_min:.1f}h, Max night: {agg.sleep_max:.1f}h",
    ]

    return InsightBlock(title="Sleep Analysis", summary=summary, bullets=bullets, severity=sev)


def _forecast_narrative(forecast_pts: list, traj: Trajectory) -> InsightBlock:
    if not forecast_pts:
        return InsightBlock(
            title="7-Day Forecast",
            summary="Not enough data for forecast.",
            bullets=[],
            severity="info",
        )

    last_actual = traj.full_series.values[-1] if traj.full_series.values else 0
    first_pred = forecast_pts[0].predicted
    last_pred = forecast_pts[-1].predicted
    direction = _dir_arrow(1 if last_pred > first_pred else (-1 if last_pred < first_pred else 0))

    if direction == _ARROW_UP:
        sev = "positive"
        summary = (
            f"Q_HE forecast to {direction} to {last_pred:.4f} in 7 days "
            f"(from {last_actual:.4f} today). Momentum maintained."
        )
    elif direction == _ARROW_DOWN:
        sev = "warning"
        summary = (
            f"Q_HE forecast to {direction} to {last_pred:.4f} in 7 days "
            f"(from {last_actual:.4f} today). Watch closely."
        )
    else:
        sev = "info"
        summary = f"Q_HE forecast to stay flat at ~{last_pred:.4f}."

    bullets = [f"Today (actual): {last_actual:.4f}"]
    forecast_lines = [
        f"  {p.date}: {p.predicted:.4f} [{p.lower_ci:.4f} -- {p.upper_ci:.4f}]"
        for p in forecast_pts
    ]
    bullets.extend(forecast_lines)

    return InsightBlock(title="7-Day Forecast", summary=summary, bullets=bullets, severity=sev)


def _pomodoros_story(agg: Aggregations) -> InsightBlock:
    pom_avg = agg.pomodoros_mean
    pom_total = agg.pomodoros_total

    if pom_avg >= _THRESHOLD_POM_EXCELLENT:
        sev = "positive"
        summary = (
            f"Excellent focus output: {pom_avg:.1f} pomodoros/day average, "
            f"{pom_total:.0f} total over {agg.n_days} days."
        )
    elif pom_avg >= _THRESHOLD_POM_DECENT:
        sev = "warning"
        summary = (
            f"Decent focus: {pom_avg:.1f} pomodoros/day average. "
            "Room to improve toward 9+."
        )
    else:
        sev = "critical"
        summary = (
            f"Low focus output: {pom_avg:.1f} pomodoros/day average. "
            "Need to protect deep-work blocks."
        )

    bullets = [
        f"Average pomodoros/day: {pom_avg:.1f}",
        f"Total (180 days): {pom_total:.0f}",
        f"Hardwork budget adherence: {agg.hardwork_adherence_pct:.0f}%",
        f"Budget: {agg.hardwork_budget_mean:.0f}min/day avg | "
        f"Actual: {agg.hardwork_actual_mean:.0f}min/day avg",
    ]

    return InsightBlock(title="Pomodoro Story", summary=summary, bullets=bullets, severity=sev)


# ── Master dispatcher ──────────────────────────────────────────────────────────

def generate_full_report(ds: Dataset) -> FullReport:
    """Generate all insights from a loaded dataset."""
    agg = compute_aggregations(ds)
    traj = build_trajectory(ds, "qhe")
    corr = correlation_matrix(ds)
    gs = growth_score(ds)
    habits = habit_analytics(ds)
    scenarios = scenario_analysis(ds)
    regimes = regime_analysis(ds)
    weekly = weekly_trend(ds, "qhe")

    # Attach sleep_min/sleep_max from raw series
    sleep_rows = ds.get("sleep_record", [])
    _, sleep_hours = float_col(sleep_rows, "date", "sleep_hours")
    agg.sleep_min = min(sleep_hours) if sleep_hours else 0.0
    agg.sleep_max = max(sleep_hours) if sleep_hours else 0.0

    forecast_pts = linear_forecast(traj.full_series, 7)

    # Annotate rank on scenarios for bullet display
    for i, s in enumerate(scenarios):
        s.rank = i + 1

    return {
        "growth": _growth_story(gs, agg),
        "weekly_arc": _weekly_arc(weekly),
        "regime": _regime_transitions(regimes, ds),
        "correlations": _correlation_narrative(corr),
        "scenarios": _scenario_narrative(scenarios),
        "habits": _habit_narrative(habits),
        "trajectory": _trajectory_segments(traj),
        "sleep": _sleep_analysis(ds, agg),
        "forecast": _forecast_narrative(forecast_pts, traj),
        "pomodoros": _pomodoros_story(agg),
    }


def format_insights_text(report: FullReport) -> str:
    """Render a FullReport as a formatted plain-text string."""
    lines = []
    for block in report.values():
        emoji = _sev_emoji(block.severity)
        lines.append(f"\n{'=' * 60}")
        lines.append(f"  {emoji} {block.title.upper()}")
        lines.append(f"{'=' * 60}")
        lines.append(f"\n{block.summary}\n")
        lines.extend(f"  * {b}" for b in block.bullets)
    return "\n".join(lines)
