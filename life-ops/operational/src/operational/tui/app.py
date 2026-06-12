"""PAV TUI Application — main Textual app with 7 screens."""
from __future__ import annotations

from typing import Never

from textual.app import App
from textual.screen import Screen

from operational.tui.navigation import ScreenKind, navigate_to
from operational.tui.screens.daily_flow_screen import DailyFlowScreen
from operational.tui.screens.dashboard_screen import DashboardScreen
from operational.tui.screens.habits_screen import HabitsScreen
from operational.tui.screens.journal_screen import JournalScreen
from operational.tui.screens.metrics_screen import MetricsScreen
from operational.tui.screens.policy_screen import PolicyScreen
from operational.tui.screens.pomodoro_timer_screen import PomodoroTimerScreen
from operational.tui.theme import get_tui_theme

SCREEN_MAP: dict[ScreenKind, type[Screen[Never]]] = {
    ScreenKind.DASHBOARD: DashboardScreen,
    ScreenKind.DAILY_FLOW: DailyFlowScreen,
    ScreenKind.POMODORO_TIMER: PomodoroTimerScreen,
    ScreenKind.HABITS: HabitsScreen,
    ScreenKind.METRICS: MetricsScreen,
    ScreenKind.POLICY: PolicyScreen,
    ScreenKind.JOURNAL: JournalScreen,
}

BINDINGS: tuple[tuple[str, str, str], ...] = (
    ("q", "quit", "Quit"),
    ("1", "switch(dashboard)", "Dashboard"),
    ("2", "switch(daily_flow)", "Daily Flow"),
    ("3", "switch(pomodoro_timer)", "Pomodoro"),
    ("4", "switch(habits)", "Habits"),
    ("5", "switch(metrics)", "Metrics"),
    ("6", "switch(policy)", "Policy"),
    ("7", "switch(journal)", "Journal"),
)


class PAVApp(App[Never]):
    """Main PAV TUI application with 7 screens."""

    TITLE = "PAV-OS"
    BINDINGS = BINDINGS  # type: ignore[assignment]

    def on_mount(self) -> None:
        self.theme = get_tui_theme()
        self.push_screen(Screen())

    def action_switch(self, screen_name: str) -> None:
        for kind, cls in SCREEN_MAP.items():
            if kind.name.lower() == screen_name.lower():
                navigate_to(kind)
                self.push_screen(cls())
                break
