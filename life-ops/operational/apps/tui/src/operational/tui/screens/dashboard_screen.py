"""Dashboard Screen for PAV TUI."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.widgets import Header, Footer, Static

from operational.tui.widgets.kpi_card import KPICard
from operational.tui.widgets.pomodoro_grid import PomodoroGrid
from operational.tui.widgets.regime_bar import RegimeBar

if TYPE_CHECKING:
    from textual.app import ComposeResult


class DashboardScreen(Screen):
    """Main dashboard: KPI cards, regime bar, pomodoro grid, next step."""

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
    height: 3;
    margin: 1 1;
    color: $text-muted;
}
"""

    def compose(self) -> ComposeResult:
        yield Header()
        yield KPICard(label="Sono", value="8.0h", delta="+0.5h 7d", icon="😴", id="kpi-sono")
        yield KPICard(label="Pomodoros", value="12", delta="+3 today", icon="🍅", id="kpi-pomo")
        yield KPICard(label="Energia", value="7/10", delta="-1", icon="⚡", id="kpi-energia")
        yield KPICard(label="Foco", value="8/10", delta="+2", icon="🎯", id="kpi-foco")
        yield RegimeBar(current="MAINTAIN", id="regime-bar")
        yield PomodoroGrid(id="pomo-grid")
        yield Static("Próximo: Deep Work Session (14:00-16:00)", id="next-step")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#kpi-sono", KPICard).value = "8.0h"
        self.query_one("#kpi-sono", KPICard).delta = "+0.5h 7d"
        self.query_one("#kpi-pomo", KPICard).value = "12"
        self.query_one("#kpi-pomo", KPICard).delta = "+3 today"
        self.query_one("#kpi-energia", KPICard).value = "7/10"
        self.query_one("#kpi-energia", KPICard).delta = "-1"
        self.query_one("#kpi-foco", KPICard).value = "8/10"
        self.query_one("#kpi-foco", KPICard).delta = "+2"
        self.query_one("#regime-bar", RegimeBar).current = "MAINTAIN"
        self.query_one("#next-step", Static).update("Próximo: Deep Work Session (14:00-16:00)")