"""Dashboard Screen for PAV TUI — data-bound.

Reads the current :class:`DaySnapshot` from ``operational.cli.services``
and refreshes every widget every ``REFRESH_INTERVAL`` seconds. Shows:
- 4 KPIs (sleep, pomodoros, energy, focus)
- 3 mini 7-day sparklines (sleep, energy, focus)
- Current regime bar
- Pomodoro grid for today
- Next-step advisory (computed from data)
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from typing import TYPE_CHECKING

from operational.cli.state import journals as journals_repo
from operational.cli.state import sleep_records as sleep_repo
from operational.core.next_step import compute_next_step, get_current_regime
from operational.tui.widgets.kpi_card import KPICard
from operational.tui.widgets.pomodoro_grid import PomodoroGrid
from operational.tui.widgets.regime_bar import RegimeBar
from operational.tui.widgets.sparkline_chart import ChartColors, PlotextChart
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

REFRESH_INTERVAL = 2.0  # seconds
SPARKLINE_DAYS = 7  # last N days for mini sparklines


def _format_delta(curr: float | None, baseline: float | None = None) -> str:
    """Format a KPI delta as a short trend string."""
    if curr is None:
        return "—"
    if baseline is None:
        return ""
    d = curr - baseline
    sign = "+" if d >= 0 else ""
    return f"{sign}{d:.1f}"


def _classify_sleep_severity(sleep_h: float | None) -> str:
    if sleep_h is None:
        return "muted"
    if sleep_h >= 7.5:
        return "success"
    if sleep_h >= 6.5:
        return "warning"
    return "danger"


def _classify_focus_severity(foco: int | None) -> str:
    if foco is None:
        return "muted"
    if foco >= 7:
        return "success"
    if foco >= 5:
        return "warning"
    return "danger"


def _sleep_for(d: date) -> float | None:
    """Return sleep duration in hours for a date, or None if not logged."""
    try:
        for s in sleep_repo.list():
            if getattr(s, "date", None) == d:
                h = getattr(s, "duration_hours", None)
                return float(h) if h is not None else None
    except Exception:
        pass
    return None


def _energy_for(d: date) -> int | None:
    """Return energy level 1-10 for a date, or None."""
    try:
        for j in journals_repo.list():
            if getattr(j, "date", None) == d:
                v = getattr(j, "energia_nivel", None)
                return int(v) if v is not None else None
    except Exception:
        pass
    return None


def _focus_for(d: date) -> int | None:
    """Return focus level 1-10 for a date, or None."""
    try:
        for j in journals_repo.list():
            if getattr(j, "date", None) == d:
                v = getattr(j, "foco_nivel", None)
                return int(v) if v is not None else None
    except Exception:
        pass
    return None


def _fill_missing(series: Sequence[float | None]) -> list[float]:
    """Replace None entries with the series mean so the chart has no gaps.

    Returns a zero-filled list when no real values are present so plotext
    still renders something instead of raising.
    """
    nums = [v for v in series if v is not None]
    if not nums:
        return [0.0] * len(series)
    mean = sum(nums) / len(nums)
    return [v if v is not None else mean for v in series]


def _has_any(series: Sequence[float | None]) -> bool:
    """Return True if at least one value in the series is non-None."""
    return any(v is not None for v in series)


def _latest_data_date() -> date | None:
    """Return the latest date that has sleep or journal data, or None."""
    dates: set[date] = set()
    try:
        for s in sleep_repo.list():
            d = getattr(s, "date", None)
            if d is not None:
                dates.add(d)
    except Exception:
        pass
    try:
        for j in journals_repo.list():
            d = getattr(j, "date", None)
            if d is not None:
                dates.add(d)
    except Exception:
        pass
    return max(dates) if dates else None


class DashboardScreen(Screen):  # type: ignore[type-arg]
    """Main dashboard — 4 KPIs, regime bar, pomodoro grid, next step."""

    CSS = """
DashboardScreen {
    background: $panel;
    layout: vertical;
}
#kpi-sono, #kpi-pomo, #kpi-energia, #kpi-foco {
    width: 100%;
    height: 3;
    margin: 0 1;
    border: solid $border;
    background: $surface;
}
#chart-row {
    height: 8;
    width: 100%;
    margin: 1 1;
}
#sleep-spark, #energy-spark, #focus-spark {
    width: 1fr;
    height: 100%;
    border: solid $border;
    background: $surface;
    padding: 0 1;
}
#regime-bar {
    width: 100%;
    height: 3;
    margin: 1 1;
    border: solid $border;
    background: $surface;
}
#pomo-grid {
    width: 100%;
    height: auto;
    margin: 1 1;
    border: solid $border;
    background: $surface;
}
#next-step {
    width: 100%;
    height: auto;
    margin: 1 1;
    padding: 0 2;
    color: $text-muted;
}
"""

    def compose(self) -> ComposeResult:
        yield Header()
        yield KPICard(id="kpi-sono", label="Sono",       icon="😴")
        yield KPICard(id="kpi-pomo", label="Pomodoros",  icon="🍅")
        yield KPICard(id="kpi-energia", label="Energia", icon="⚡")
        yield KPICard(id="kpi-foco", label="Foco",       icon="🎯")
        with Horizontal(id="chart-row"):
            yield PlotextChart(id="sleep-spark")
            yield PlotextChart(id="energy-spark")
            yield PlotextChart(id="focus-spark")
        yield RegimeBar(id="regime-bar")
        yield PomodoroGrid(id="pomo-grid")
        yield Static(id="next-step")
        yield Footer()

    def on_mount(self) -> None:
        # Defer initial refresh until the widget tree is fully attached.
        self.call_after_refresh(self._refresh)
        # Periodic refresh — but only after the first tick so we don't
        # race with Textual's own _on_mount signal subscription.
        self.call_after_refresh(
            lambda: self.set_interval(REFRESH_INTERVAL, self._refresh)
        )

    def _refresh(self) -> None:
        """Pull a fresh snapshot and update every widget.

        Anchors to the latest date that has data (not date.today()) so
        the dashboard shows meaningful content even when the loaded
        dataset is from a past period.
        """
        effective_today = _latest_data_date() or date.today()
        try:
            from operational.cli.services import get_day_snapshot
            snap = get_day_snapshot(effective_today)
        except Exception:
            snap = None

        if snap is None:
            self._render_empty()
            return

        self._render_sparklines()

        # Sleep
        sleep_h = snap.sleep.duration_hours
        self.query_one("#kpi-sono", KPICard).update(
            value=f"{sleep_h:.1f}h" if sleep_h is not None else "—",
            severity=_classify_sleep_severity(sleep_h),
        )
        # Pomodoros
        pomo_done = snap.n_pomodoros
        pomo_meta = snap.pomodoros_meta or 0
        pomo_pct = (pomo_done / pomo_meta * 100) if pomo_meta else 0
        self.query_one("#kpi-pomo", KPICard).update(
            value=f"{pomo_done}/{pomo_meta}" if pomo_meta else f"{pomo_done}",
            delta=f"{pomo_pct:.0f}% da meta" if pomo_meta else "",
            severity=(
                "success" if pomo_pct >= 80
                else "warning" if pomo_pct >= 50
                else "danger" if pomo_meta else "muted"
            ),
        )
        # Energy
        energia = snap.energia
        self.query_one("#kpi-energia", KPICard).update(
            value=f"{energia}/10" if energia is not None else "—",
            severity=(
                "success" if (energia or 0) >= 7
                else "warning" if (energia or 0) >= 4
                else "danger" if energia is not None
                else "muted"
            ),
        )
        # Focus
        foco = snap.foco
        self.query_one("#kpi-foco", KPICard).update(
            value=f"{foco}/10" if foco is not None else "—",
            severity=_classify_focus_severity(foco),
        )
        # Regime
        self.query_one("#regime-bar", RegimeBar).current = get_current_regime(snap)
        # Pomodoro grid (split the day's pomodoros into S1/S2/S3)
        s1, s2, s3 = _split_pomodoros_into_sessions(pomo_done)
        self.query_one("#pomo-grid", PomodoroGrid).update(
            sessions=[
                _round_to_glyphs(s1),
                _round_to_glyphs(s2),
                _round_to_glyphs(s3),
            ],
            focus_scores=[
                _score_for_session(snap, "S1"),
                _score_for_session(snap, "S2"),
                _score_for_session(snap, "S3"),
            ],
        )
        # Next step
        step = compute_next_step(snap)
        self.query_one("#next-step", Static).update(
            f"[bold]OBSERVAÇÃO:[/bold] {step.observation}\n"
            f"[bold]AÇÃO:[/bold]       {step.action}"
        )

    def _render_empty(self) -> None:
        """Render an empty-state dashboard when no data exists for today."""
        self.query_one("#kpi-sono", KPICard).update(value="—", severity="muted")
        self.query_one("#kpi-pomo", KPICard).update(value="0/0", severity="muted")
        self.query_one("#kpi-energia", KPICard).update(value="—", severity="muted")
        self.query_one("#kpi-foco", KPICard).update(value="—", severity="muted")
        # Empty sparklines — graceful "No data" message instead of a real chart
        empty_msg = "[dim]Sem dados (7d)[/dim]"
        self.query_one("#sleep-spark", PlotextChart).update(empty_msg)
        self.query_one("#energy-spark", PlotextChart).update(empty_msg)
        self.query_one("#focus-spark", PlotextChart).update(empty_msg)
        self.query_one("#next-step", Static).update(
            "[dim]Sem dados para hoje — rode `pav demo seed` ou `pav metric sleep` para começar.[/dim]"
        )

    def _render_sparklines(self) -> None:
        """Render the 7-day sparklines for sleep / energy / focus.

        Anchors the window to the latest data date (not date.today()) so
        the sparklines show data regardless of when the dataset was recorded.
        """
        effective_today = _latest_data_date() or date.today()
        dates = [effective_today - timedelta(days=i) for i in range(SPARKLINE_DAYS - 1, -1, -1)]

        sleep_vals = [_sleep_for(d) for d in dates]
        energy_vals = [_energy_for(d) for d in dates]
        focus_vals = [_focus_for(d) for d in dates]

        empty_msg = "[dim]Sem dados (7d)[/dim]"

        # ── Sleep sparkline
        sleep_chart = self.query_one("#sleep-spark", PlotextChart)
        if _has_any(sleep_vals):
            sleep_chart.sparkline(
                _fill_missing(sleep_vals),
                color=ChartColors.SLEEP["primary"],
                fill=True,
                fill_opacity=0.15,
                line_style="solid",
                point_type="dot",
                marker_size=1.2,
                line_width=1.0,
                y_label="h",
                title="Sono 7d",
                hide_x_axis=True,
                hide_grid=True,
            )
        else:
            sleep_chart.update(empty_msg)

        # ── Energy sparkline
        energy_chart = self.query_one("#energy-spark", PlotextChart)
        if _has_any(energy_vals):
            energy_chart.sparkline(
                _fill_missing(energy_vals),
                color=ChartColors.ENERGY["primary"],
                fill=True,
                fill_opacity=0.15,
                line_style="solid",
                point_type="dot",
                marker_size=1.2,
                line_width=1.0,
                y_label="pts",
                title="Energia 7d",
                hide_x_axis=True,
                hide_grid=True,
            )
        else:
            energy_chart.update(empty_msg)

        # ── Focus sparkline
        focus_chart = self.query_one("#focus-spark", PlotextChart)
        if _has_any(focus_vals):
            focus_chart.sparkline(
                _fill_missing(focus_vals),
                color=ChartColors.FOCUS["primary"],
                fill=True,
                fill_opacity=0.15,
                line_style="solid",
                point_type="dot",
                marker_size=1.2,
                line_width=1.0,
                y_label="pts",
                title="Foco 7d",
                hide_x_axis=True,
                hide_grid=True,
            )
        else:
            focus_chart.update(empty_msg)


def _split_pomodoros_into_sessions(total: int) -> tuple[int, int, int]:
    """Distribute N completed pomodoros across 3 sessions of max 4 each.

    Returns (S1_done, S2_done, S3_done). Used to fill the grid glyphs.
    """
    s1 = min(4, total)
    remaining = total - s1
    s2 = min(4, remaining)
    s3 = max(0, min(4, remaining - s2))
    return s1, s2, s3


def _round_to_glyphs(done: int) -> list[str]:
    """Convert a session-done count (0-4) to a list of glyph strings.

    ``done = 3`` → ``["done", "done", "done", "skip"]``.
    """
    return ["done" if i < done else "skip" for i in range(4)]


def _score_for_session(snap: object, session: str) -> int:
    """Return the focus score (0-10) for a given session, or 0 if unknown.

    Currently a rough heuristic: split the day's average focus across
    sessions based on completion ratios. Future improvement: read from
    per-session PomodoroRound entities when those are populated.
    """
    foco = getattr(snap, "foco", None)
    if foco is None:
        return 0
    # Naive split: same score for each session as a placeholder.
    return int(foco)
