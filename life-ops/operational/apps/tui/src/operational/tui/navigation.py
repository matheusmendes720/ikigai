"""Screen routing and state management for PAV TUI."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class ScreenKind(Enum):
    DASHBOARD = "dashboard"
    DAILY_FLOW = "daily_flow"
    POMODORO_TIMER = "pomodoro_timer"
    HABITS = "habits"
    METRICS = "metrics"
    POLICY = "policy"
    JOURNAL = "journal"


@dataclass
class TUIState:
    current_screen: ScreenKind = ScreenKind.DASHBOARD
    selected_date: date = field(default_factory=date.today)
    current_period: str | None = None
    pomodoro_state: str | None = None
    regime: str = "MAINTAIN"


screen_registry: dict[ScreenKind, str] = {
    ScreenKind.DASHBOARD:       "operational.tui.screens.dashboard_screen:DashboardScreen",
    ScreenKind.DAILY_FLOW:       "operational.tui.screens.daily_flow_screen:DailyFlowScreen",
    ScreenKind.POMODORO_TIMER:   "operational.tui.screens.pomodoro_timer_screen:PomodoroTimerScreen",
    ScreenKind.HABITS:           "operational.tui.screens.habits_screen:HabitsScreen",
    ScreenKind.METRICS:          "operational.tui.screens.metrics_screen:MetricsScreen",
    ScreenKind.POLICY:           "operational.tui.screens.policy_screen:PolicyScreen",
    ScreenKind.JOURNAL:          "operational.tui.screens.journal_screen:JournalScreen",
}

_state = TUIState()

def get_state() -> TUIState:
    return _state

def set_state(new_state: TUIState) -> None:
    global _state
    _state = new_state

def navigate_to(screen: ScreenKind) -> None:
    _state.current_screen = screen
