"""TUI widgets."""
from __future__ import annotations

from operational.tui.widgets.habit_streak import HabitStreakDisplay
from operational.tui.widgets.kpi_card import KPICard
from operational.tui.widgets.pomodoro_grid import PomodoroGrid
from operational.tui.widgets.regime_bar import RegimeBar
from operational.tui.widgets.sparkline_chart import PlotextChart
from operational.tui.widgets.time_block import TimeBlockDisplay

__all__ = [
    "HabitStreakDisplay",
    "KPICard",
    "PlotextChart",
    "PomodoroGrid",
    "RegimeBar",
    "TimeBlockDisplay",
]
