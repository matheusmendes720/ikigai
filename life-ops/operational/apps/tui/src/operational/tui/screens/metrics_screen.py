"""Metrics Screen for PAV TUI — data-bound.

Historical charts: sleep, energy, focus over 7d / 30d. Reads from the
``sleep_records``, ``journals`` (for energy/focus) repos.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from operational.cli.state import journals as journals_repo
from operational.cli.state import sleep_records as sleep_repo
from operational.tui.widgets.sparkline_chart import ChartColors, PlotextChart
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


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


def _data_date_range(period: str) -> tuple[list[date], list[str]]:
    """Return (dates, labels) for the window that has data.

    Instead of anchoring to date.today(), we anchor to the actual data.
    If data spans N days, we show the last N days (up to 7d/30d limit).
    If no data at all, falls back to the last 7/30 days from today so
    the screen still renders the "no data" message.
    """
    days = 7 if period == "7d" else 30
    today = date.today()

    # Collect all unique dates from sleep_records and journals
    data_dates: set[date] = set()
    try:
        for s in sleep_repo.list():
            d = getattr(s, "date", None)
            if d is not None:
                data_dates.add(d)
    except Exception:
        pass
    try:
        for j in journals_repo.list():
            d = getattr(j, "date", None)
            if d is not None:
                data_dates.add(d)
    except Exception:
        pass

    if data_dates:
        sorted_dates = sorted(data_dates)
        # Use the latest N days that have data (or all available if fewer)
        window = sorted_dates[-days:] if len(sorted_dates) > days else sorted_dates
        labels = [d.strftime("%d/%m") for d in window]
        return window, labels

    # No data at all — fall back to standard today-anchored window
    dates_list = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    labels = [d.strftime("%d/%m") for d in dates_list]
    return dates_list, labels


class MetricsScreen(Screen):
    """Historical charts: sleep, energy, focus over 7d/30d."""

    CSS = """
MetricsScreen {
    background: $panel;
    layout: vertical;
}
#period-toggle {
    height: 3;
    width: 100%;
    padding: 1 2;
    background: $surface;
}
#btn-7d, #btn-30d {
    margin: 0 1;
}
#sleep-label, #energy-label, #focus-label {
    height: 3;
    width: 100%;
    padding: 1 2;
    color: $text;
    text-style: bold;
}
#sleep-label {
    color: #00CED1;
}
#energy-label {
    color: #00FF00;
}
#focus-label {
    color: #FF69B4;
}
PlotextChart {
    height: 10;
    width: 100%;
    padding: 0 2;
}
#sleep-debt {
    height: 3;
    width: 100%;
    padding: 1 2;
    color: $warning;
}
#combo-label {
    height: 3;
    width: 100%;
    padding: 1 2;
    color: $text;
    text-style: bold;
}
"""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Button("[ 7d ]", id="btn-7d", variant="primary")
        yield Button("[ 30d ]", id="btn-30d", variant="default")
        yield Static("Sono (horas)", id="sleep-label")
        yield PlotextChart(id="sleep-chart")
        yield Static("Energia (1-10)", id="energy-label")
        yield PlotextChart(id="energy-chart")
        yield Static("Foco (1-10)", id="focus-label")
        yield PlotextChart(id="focus-chart")
        yield Static("Sono + Foco sobrepostos (dual-axis)", id="combo-label")
        yield PlotextChart(id="combo-chart")
        yield Static(id="sleep-debt")
        yield Footer()

    def _render_charts(self, period: str = "7d") -> None:
        # Use the data-anchored date range instead of fixed today-anchored window.
        # This ensures charts show data regardless of when the dataset was recorded.
        dates, labels = _data_date_range(period)
        days = len(dates)
        sleep_vals = [_sleep_for(d) for d in dates]
        energy_vals = [_energy_for(d) for d in dates]
        focus_vals = [_focus_for(d) for d in dates]

        # Replace None with the series mean so the chart doesn't have gaps
        def fill(series: list[float | None]) -> list[float]:
            nums = [v for v in series if v is not None]
            if not nums:
                return [0.0] * len(series)
            mean = sum(nums) / len(nums)
            return [v if v is not None else mean for v in series]

        sleep_filled = fill(sleep_vals)
        energy_filled = fill(energy_vals)
        focus_filled = fill(focus_vals)

        # ── Sleep sparkline
        self.query_one("#sleep-chart", PlotextChart).sparkline(
            sleep_filled,
            color=ChartColors.SLEEP["primary"],
            fill=True,
            fill_opacity=0.15,
            line_style="solid",
            point_type="dot",
            marker_size=1.2,
            line_width=1.0,
            y_label="h",
            title=f"Sono  {period}",
            hide_x_axis=True,
            hide_grid=True,
        )
        # ── Energy bars
        self.query_one("#energy-chart", PlotextChart).bar_chart(
            labels, energy_filled,
            color=ChartColors.ENERGY["primary"],
            orientation="v",
            bar_width=0.5,
            max_value=10,
            y_label="pts",
            title=f"Energia  {period}",
            hide_grid=True,
        )
        # ── Focus sparkline
        self.query_one("#focus-chart", PlotextChart).sparkline(
            focus_filled,
            color=ChartColors.FOCUS["primary"],
            fill=True,
            fill_opacity=0.15,
            line_style="solid",
            point_type="dot",
            marker_size=1.2,
            line_width=1.0,
            y_label="pts",
            title=f"Foco  {period}",
            hide_x_axis=True,
            hide_grid=True,
        )
        # ── Combo dual-axis
        x_vals = [float(i) for i in range(1, days + 1)]
        self.query_one("#combo-chart", PlotextChart).dual_axis(
            x=x_vals,
            y1=sleep_filled,
            y2=focus_filled,
            color1=ChartColors.SLEEP["primary"],
            color2=ChartColors.FOCUS["primary"],
            label1="Sono (h)",
            label2="Foco (pts)",
            kind1="line",
            kind2="line",
            line_width=1.0,
            marker_size=1.0,
            title="Sono + Foco dual-axis",
            hide_grid=True,
        )

        # ── Sleep debt summary
        nums = [v for v in sleep_vals if v is not None]
        if nums:
            mean = sum(nums) / len(nums)
            debt = 8.0 - mean
            self.query_one("#sleep-debt", Static).update(
                f"Sono déficit (média {mean:.1f}h vs meta 8.0h): {debt:+.1f}h esta janela"
            )
        else:
            self.query_one("#sleep-debt", Static).update(
                "[dim]Sem dados de sono nesta janela — registre com `pav metric sleep`.[/dim]"
            )

    def on_mount(self) -> None:
        self._render_charts("7d")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id in ("btn-7d", "btn-30d"):
            self._render_charts("7d" if btn_id == "btn-7d" else "30d")
