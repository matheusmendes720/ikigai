"""Metrics Screen for PAV TUI."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from operational.tui.widgets.sparkline_chart import PlotextChart

if TYPE_CHECKING:
    from textual.app import ComposeResult


class MetricsScreen(Screen):
    """Historical charts: sleep, energy, focus over 7d/30d."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("[7d] [30d]", id="period-toggle")
        yield Static("Sono (horas)", id="sleep-label")
        yield PlotextChart(id="sleep-chart")
        yield Static("Energia (1-10)", id="energy-label")
        yield PlotextChart(id="energy-chart")
        yield Static("Foco (1-10)", id="focus-label")
        yield PlotextChart(id="focus-chart")
        yield Static("Sono déficit: -1.5h esta semana", id="sleep-debt")
        yield Footer()

    def on_mount(self) -> None:
        pass
