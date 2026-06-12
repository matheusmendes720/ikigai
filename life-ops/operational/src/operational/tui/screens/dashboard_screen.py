"""Dashboard Screen for PAV TUI."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from operational.tui.widgets.kpi_card import KPICard
from operational.tui.widgets.pomodoro_grid import PomodoroGrid
from operational.tui.widgets.regime_bar import RegimeBar

if TYPE_CHECKING:
    from textual.app import ComposeResult


class DashboardScreen(Screen):
    """Main dashboard: KPI cards, regime bar, pomodoro grid, next step."""

    CSS = """
    DashboardScreen {
        layout: grid;
        grid-size: 2;
        grid-gutter: 1;
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
        pass
