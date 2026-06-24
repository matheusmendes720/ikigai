"""Analytics Screen for PAV TUI — 180-day data storytelling.

Shows:
- Growth score gauge
- Weekly arc sparkline (Q_HE over 26 weeks)
- Regime timeline bar
- Correlation highlights
- Top scenarios
- 7-day OLS forecast

Data comes from operational.core.analytics + operational.core.insights.
No LLM — pure arithmetic.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.widgets import Footer, Header, Static
from rich.text import Text

from operational.core.analytics import (
    build_trajectory,
    compute_aggregations,
    correlation_matrix,
    growth_score,
    linear_forecast,
    load_dataset,
    regime_timeline,
    scenario_analysis,
    weekly_trend,
)
from operational.tui.theme import get_tui_theme

_SCORE_SUCCESS = 80.0
_SCORE_WARNING = 60.0

if TYPE_CHECKING:
    from textual.app import ComposeResult

REFRESH_INTERVAL = 60.0  # long interval — data is static


# ── CSV directory detection ───────────────────────────────────────────────────────

def _detect_csv_dir() -> Path:
    """Find the 6month CSV directory relative to this file."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        p = current / "datasets" / "6month" / "csv"
        if p.is_dir():
            return p
        parent = current.parent
        if parent == current:
            break
        current = parent
    return Path.cwd() / "datasets" / "6month" / "csv"


# ── Text rendering helpers ───────────────────────────────────────────────────────

def _spark8(vals: list[float], width: int = 20) -> str:
    """ASCII sparkline from a list of floats (last N values)."""
    if not vals:
        return "░" * width
    mn, mx = min(vals), max(vals)
    rng = mx - mn or 1.0
    ticks = " ▁▂▃▄▅▆▇█"
    n = len(ticks) - 1
    out = []
    for v in vals[-width:]:
        idx = int((v - mn) / rng * n)
        out.append(ticks[min(idx, n)])
    return "".join(out)


def _score_bar(score: float, width: int = 30) -> str:
    filled = int(width * min(score, 100) / 100)
    return "█" * filled + "░" * (width - filled)


def _pct_bar(pct: float, width: int = 20) -> str:
    filled = int(width * min(pct, 100) / 100)
    return "█" * filled + "░" * (width - filled)


def _regime_timeline_bar(timeline: list[tuple[date, str]], width: int = 40) -> Text:
    """Compact one-line regime timeline showing dominant regime per period.

    Returns a Rich ``Text`` so it can safely be rendered in a Textual widget.
    """
    if not timeline:
        return Text("N/A", style="dim")

    n = len(timeline)
    chunk_size = max(1, n // width)
    text = Text()

    regime_color_map: dict[str, str] = {
        "PUSH": "green",
        "MAINTAIN": "yellow",
        "REDUCE": "red",
        "RECOVER": "magenta",
    }

    for i in range(0, n, chunk_size):
        chunk = timeline[i : i + chunk_size]
        dominant = Counter(s for _, s in chunk).most_common(1)[0][0]
        color = regime_color_map.get(dominant, "white")
        text.append("█", style=color)

    return text


def _render_correlation_text(corr: list, top_n: int = 5) -> str:
    """Render top correlations as plain text lines."""
    lines = []
    for c in corr[:top_n]:
        arrow = "+" if c.r > 0 else "-"
        strength = {
            "strong_pos": "strong+", "moderate_pos": "mod+",
            "weak": "weak", "moderate_neg": "mod-", "strong_neg": "strong-",
        }.get(c.strength, c.strength)
        lines.append(
            f"  {c.metric_a} {arrow} {c.metric_b}: r={c.r:+.3f} ({strength})"
        )
    return "\n".join(lines) if lines else "  No data"


def _render_scenario_text(scenarios: list) -> str:
    """Render scenarios as plain text."""
    lines = []
    for s in scenarios[:5]:
        bar = "█" * int(s.pct / 5) + "░" * (20 - int(s.pct / 5))
        lines.append(
            f"  {s.name:<10} {s.days:>3}d {s.pct:>5.1f}% "
            f"QHE={s.qhe_avg:.3f} sleep={s.sleep_avg:.1f}h "
            f"[{bar}]"
        )
    return "\n".join(lines) if lines else "  No data"


def _render_forecast_text(forecast_pts: list) -> str:
    """Render 7-day forecast as plain text."""
    lines = []
    for p in forecast_pts:
        lines.append(
            f"  {p.date.isoformat()}: pred={p.predicted:.4f} "
            f"[{p.lower_ci:.4f} -- {p.upper_ci:.4f}]"
        )
    return "\n".join(lines) if lines else "  Not enough data"


# ── Analytics screen ─────────────────────────────────────────────────────────────

class AnalyticsScreen(Screen):
    """Full 180-day analytics storytelling screen."""

    CSS = """
    AnalyticsScreen {
        background: $panel;
        layout: vertical;
    }
    #header-static {
        width: 100%;
        height: 3;
        margin: 0 1;
        color: $text-muted;
        background: $surface;
    }
    #growth-panel, #arc-panel, #regime-panel {
        width: 100%;
        margin: 1 1;
        border: solid $border;
        background: $surface;
        height: auto;
    }
    #corr-panel, #scen-panel, #forecast-panel {
        width: 100%;
        margin: 1 1;
        border: solid $border;
        background: $surface;
        height: auto;
    }
    .panel-label {
        width: 100%;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="header-static")
        yield Static("", id="growth-panel")
        yield Static("", id="arc-panel")
        yield Static("", id="regime-panel")
        yield Static("", id="corr-panel")
        yield Static("", id="scen-panel")
        yield Static("", id="forecast-panel")
        yield Footer()

    def on_mount(self) -> None:
        self.call_after_refresh(self._refresh)
        self.call_after_refresh(
            lambda: self.set_interval(REFRESH_INTERVAL, self._refresh)
        )

    def _refresh(self) -> None:
        """Load data and render all panels."""
        try:
            csv_dir = _detect_csv_dir()
            ds = load_dataset(csv_dir)
        except Exception:  # noqa: BLE001
            self._render_error()
            return

        # ── Header ────────────────────────────────────────────────────────────
        agg = compute_aggregations(ds)
        self.query_one("#header-static", Static).update(Text.from_markup(
            f"[bold]PAV Analytics[/bold]  |  "
            f"180 days  |  "
            f"Q_HE {agg.qhe_mean:.4f}  |  "
            f"Regime: {agg.regime_dominant}  |  "
            f"PUSH {agg.regime_distribution.get('PUSH', 0)}d"
        ))

        # ── Growth score ───────────────────────────────────────────────────────
        gs = growth_score(ds)
        score = gs.score
        bar = _score_bar(score)
        color = "success" if score >= 80 else "warning" if score >= 60 else "error"
        color_map = {"success": "#00cc66", "warning": "#ffaa00", "error": "#ff4444"}
        col = color_map.get(color, "#ffffff")
        growth_text = Text.from_markup(
            f"[bold {col}]Growth Score: {score:.0f}/100[/]\n"
            f"{bar}\n"
            f"  Q_HE 90d delta: {gs.qhe_delta_90d:+.4f}\n"
            f"  Regime health: {gs.regime_health_score:.1f}%\n"
            f"  Habit completion: {gs.habit_improvement:.1f}%"
        )
        self.query_one("#growth-panel", Static).update(growth_text)

        # ── Weekly arc ─────────────────────────────────────────────────────────
        weekly = weekly_trend(ds, "qhe")
        if weekly:
            week_means = [w.mean for w in weekly]
            spark = _spark8(week_means, 40)
            first_w = weekly[0]
            last_w = weekly[-1]
            delta = last_w.mean - first_w.mean
            direction = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
            arc_text = Text.from_markup(
                f"[bold]Weekly Q_HE Arc[/bold]\n"
                f"  Sparkline (26w): {spark}\n"
                f"  Week 1: {first_w.mean:.4f}  →  Last week: {last_w.mean:.4f}  {direction}\n"
                f"  Best: W{last_w.week} ({last_w.mean:.4f})  "
                f"Worst: W{weekly[0].week} ({weekly[0].mean:.4f})"
            )
        else:
            arc_text = Text.from_markup("[bold]Weekly Q_HE Arc[/bold]\n  No data")
        self.query_one("#arc-panel", Static).update(arc_text)

        # ── Regime timeline ────────────────────────────────────────────────────
        timeline = regime_timeline(ds)
        # regime_analysis result is available but not used — extend if needed later
        regime_bar = _regime_timeline_bar(timeline, 60)
        push_days = sum(1 for _, s in timeline if s == "PUSH")
        recover_days = sum(1 for _, s in timeline if s == "RECOVER")
        maintain_days = sum(1 for _, s in timeline if s == "MAINTAIN")
        reduce_days = sum(1 for _, s in timeline if s == "REDUCE")
        total = len(timeline) or 1

        # Build the Text with plain segments + the rich regime_bar segment
        regime_text = Text()
        regime_text.append("Regime Distribution\n  ")
        regime_text.append(regime_bar)  # Rich Text segment — append() preserves styles
        regime_text.append(
            f"\n  PUSH: {push_days}d ({push_days/total*100:.0f}%)  |  "
            f"RECOVER: {recover_days}d ({recover_days/total*100:.0f}%)  |  "
            f"MAINTAIN: {maintain_days}d  |  "
            f"REDUCE: {reduce_days}d",
            style="white",
        )
        self.query_one("#regime-panel", Static).update(regime_text)

        # ── Correlations ──────────────────────────────────────────────────────
        corr = correlation_matrix(ds)
        corr_text = Text.from_markup(
            f"[bold]Key Correlations (Pearson r)[/bold]\n"
            f"{_render_correlation_text(corr, 6)}"
        )
        self.query_one("#corr-panel", Static).update(corr_text)

        # ── Scenarios ────────────────────────────────────────────────────────
        scenarios = scenario_analysis(ds)
        scen_text = Text.from_markup(
            f"[bold]Top Scenarios (tipo_dia)[/bold]\n"
            f"{_render_scenario_text(scenarios)}"
        )
        self.query_one("#scen-panel", Static).update(scen_text)

        # ── Forecast ─────────────────────────────────────────────────────────
        traj = build_trajectory(ds, "qhe")
        forecast_pts = linear_forecast(traj.full_series, 7)
        if forecast_pts:
            last_actual = traj.full_series.values[-1] if traj.full_series.values else 0
            forecast_text = Text.from_markup(
                f"[bold]7-Day OLS Forecast[/bold]\n"
                f"  Today: {last_actual:.4f}\n"
                f"{_render_forecast_text(forecast_pts)}"
            )
        else:
            forecast_text = Text.from_markup("[bold]7-Day OLS Forecast[/bold]\n  Not enough data")
        self.query_one("#forecast-panel", Static).update(forecast_text)

    def _render_error(self) -> None:
        msg = Text.from_markup("[error]Could not load analytics data.[/error]\nIs the 6-month dataset present?")
        for sid in ("growth-panel", "arc-panel", "regime-panel",
                    "corr-panel", "scen-panel", "forecast-panel"):
            self.query_one(f"#{sid}", Static).update(msg)
