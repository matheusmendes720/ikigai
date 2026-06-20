"""Metrics Screen for PAV TUI — maximum plotext data viz."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from operational.tui.widgets.sparkline_chart import ChartColors, PlotextChart

if TYPE_CHECKING:
    from textual.app import ComposeResult


# Mock data — CSV-only (no SQLite yet)
SLEEP_DATA_7D   = [7.5, 8.0, 7.0, 8.5, 8.0, 7.5, 8.0]
ENERGY_DATA_7D  = [7.0, 8.0, 6.0, 9.0, 7.0, 8.0, 7.0]
FOCUS_DATA_7D  = [6.5, 7.0, 8.0, 7.5, 8.5, 7.0, 8.0]
SLEEP_DATA_30D  = [7.5, 8.0, 7.0, 8.5, 8.0, 7.5, 8.0,
                   7.0, 8.5, 7.5, 8.0, 7.0, 8.5, 8.0,
                   7.5, 8.0, 7.0, 8.5, 8.0, 7.5, 8.0,
                   7.0, 8.0, 7.5, 8.0, 7.0, 8.5, 8.0]
ENERGY_DATA_30D = [7.0, 8.0, 6.0, 9.0, 7.0, 8.0, 7.0,
                   6.0, 9.0, 8.0, 7.0, 6.0, 9.0, 8.0,
                   7.0, 6.0, 9.0, 8.0, 7.0, 6.0, 9.0,
                   8.0, 7.0, 6.0, 9.0, 8.0, 7.0, 6.0]
FOCUS_DATA_30D  = [6.5, 7.0, 8.0, 7.5, 8.5, 7.0, 8.0,
                   6.0, 8.5, 7.5, 8.0, 6.5, 8.5, 7.5,
                   8.0, 6.5, 8.0, 7.5, 8.5, 6.0, 8.0,
                   7.0, 8.5, 6.5, 8.0, 7.5, 8.0, 6.5]
DAYS_7D  = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAYS_30D = [f"D{i+1}" for i in range(30)]


class MetricsScreen(Screen[None]):
    """Historical charts: sleep, energy, focus over 7d/30d.

    Uses maximum plotext features:
    - Filled sparklines with period-aware colors
    - Styled bar charts with grid disabled
    - Dual-axis for sleep+focus overlay
    - Subplot grid for 30d overview
    """

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
        """Compose the metrics screen with header, period toggle, charts, and footer."""
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
        yield Static("Sono déficit: -1.5h esta semana", id="sleep-debt")
        yield Footer()

    def _render_charts(self, period: str = "7d") -> None:
        if period == "7d":
            sleep_vals = SLEEP_DATA_7D
            energy_vals = ENERGY_DATA_7D
            focus_vals = FOCUS_DATA_7D
            labels = DAYS_7D
        else:
            sleep_vals = SLEEP_DATA_30D
            energy_vals = ENERGY_DATA_30D
            focus_vals = FOCUS_DATA_30D
            labels = DAYS_30D

        # ── Sleep: filled sparkline, cyan period color ──────────────────
        sleep_chart = self.query_one("#sleep-chart", PlotextChart)
        sleep_chart.sparkline(
            sleep_vals,
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

        # ── Energy: styled bar chart, green period color ──────────────────
        energy_chart = self.query_one("#energy-chart", PlotextChart)
        energy_chart.bar_chart(
            labels,
            energy_vals,
            color=ChartColors.ENERGY["primary"],
            orientation="v",
            bar_width=0.5,
            max_value=10,
            y_label="pts",
            title=f"Energia  {period}",
            hide_grid=True,
        )

        # ── Focus: filled sparkline, magenta period color ──────────────────
        focus_chart = self.query_one("#focus-chart", PlotextChart)
        focus_chart.sparkline(
            focus_vals,
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

        # ── Combo: dual-axis sleep + focus overlay ────────────────────────
        combo_chart = self.query_one("#combo-chart", PlotextChart)
        x_vals = [float(i) for i in range(1, len(sleep_vals) + 1)]
        combo_chart.dual_axis(
            x=x_vals,
            y1=sleep_vals,
            y2=focus_vals,
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

    def on_mount(self) -> None:
        """Initialize charts with 7-day data on screen mount."""
        self._render_charts("7d")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle period toggle button presses (7d / 30d)."""
        btn_id = event.button.id or ""
        if btn_id in ("btn-7d", "btn-30d"):
            self._render_charts("7d" if btn_id == "btn-7d" else "30d")
