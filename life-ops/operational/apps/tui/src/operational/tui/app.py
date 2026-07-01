"""PAV TUI Application — main Textual app with 7 screens."""
from __future__ import annotations

from typing import ClassVar, Never

from operational.tui.screens.analytics_screen import AnalyticsScreen
from operational.tui.screens.daily_flow_screen import DailyFlowScreen
from operational.tui.screens.dashboard_screen import DashboardScreen
from operational.tui.screens.habits_screen import HabitsScreen
from operational.tui.screens.help_screen import HelpScreen
from operational.tui.screens.journal_screen import JournalScreen
from operational.tui.screens.metrics_screen import MetricsScreen
from operational.tui.screens.policy_screen import PolicyScreen
from operational.tui.screens.pomodoro_timer_screen import PomodoroTimerScreen
from operational.tui.theme import get_tui_theme
from textual import events
from textual.app import App
from textual.binding import Binding

BINDINGS = [
    Binding("q", "quit", "Quit", priority=True),
    Binding("ctrl+h", "show_help", "Help"),
    Binding("escape", "go_back", "Back", priority=True),
    Binding("1", "switch_dashboard", "Dashboard", priority=True),
    Binding("2", "switch_daily_flow", "Daily Flow", priority=True),
    Binding("3", "switch_pomodoro_timer", "Pomodoro", priority=True),
    Binding("4", "switch_habits", "Habits", priority=True),
    Binding("5", "switch_metrics", "Metrics", priority=True),
    Binding("6", "switch_policy", "Policy", priority=True),
    Binding("7", "switch_journal", "Journal", priority=True),
    Binding("8", "switch_analytics", "Analytics", priority=True),
]


def _load_dataset(name: str) -> None:
    """Load (or switch) dataset at TUI startup time.

    Uses the public state API so the JSON files in ~/.time-tasker/
    get overwritten with the loaded CSV data.
    """
    from operational.cli.state import load_dataset
    try:
        counts = load_dataset(name, clear_first=True)
        total = sum(counts.values())
        import sys
        print(f"[PAV] Loaded {name}: {total} entities → {counts}", file=sys.stderr)
    except Exception as exc:
        import sys
        print(f"[PAV] Warning: could not load {name}: {exc}", file=sys.stderr)


class PAVApp(App[Never]):
    """Main PAV-OS TUI application with 7 screens."""

    TITLE = "PAV-OS"
    BINDINGS = BINDINGS  # type: ignore[assignment]

    SCREENS: ClassVar = {
        "dashboard":      DashboardScreen,
        "daily_flow":     DailyFlowScreen,
        "pomodoro_timer": PomodoroTimerScreen,
        "habits":         HabitsScreen,
        "metrics":        MetricsScreen,
        "policy":         PolicyScreen,
        "journal":        JournalScreen,
        "analytics":      AnalyticsScreen,
        "help":           HelpScreen,
    }

    def __init__(
        self,
        initial_screen: str | None = None,
        data_file: str | None = None,
        golden: bool = False,
        synthetic: bool = False,
        **kwargs: Never,
    ) -> None:
        super().__init__(**kwargs)
        self._initial_screen = initial_screen or "dashboard"
        self._data_file = data_file
        self._golden = golden
        self._synthetic = synthetic

    def on_mount(self) -> None:
        # Load mock dataset before any screen mounts and reads from repos.
        # --golden    → docs/golden.csv      (7 canonical PAV days)
        # --synthetic → docs/synthetic.csv  (30+ days with edge cases)
        if self._golden:
            _load_dataset("golden")
        elif self._synthetic:
            _load_dataset("synthetic")

        theme = get_tui_theme()
        self.register_theme(theme)
        self.theme = theme.name
        self.push_screen(self._initial_screen)

    async def on_event(self, event: events.Event) -> None:
        """Intercept global keys (q, ctrl+h) before Input widgets steal them."""
        if isinstance(event, events.Key):
            if event.key == "q":
                self.exit()
                return None
            if event.key == "ctrl+h":
                self.push_screen("help")
                return None
        return await super().on_event(event)

    def action_switch_dashboard(self) -> None:
        self.switch_screen("dashboard")

    def action_switch_daily_flow(self) -> None:
        self.switch_screen("daily_flow")

    def action_switch_pomodoro_timer(self) -> None:
        self.switch_screen("pomodoro_timer")

    def action_switch_habits(self) -> None:
        self.switch_screen("habits")

    def action_switch_metrics(self) -> None:
        self.switch_screen("metrics")

    def action_switch_policy(self) -> None:
        self.switch_screen("policy")

    def action_switch_journal(self) -> None:
        self.switch_screen("journal")

    def action_switch_analytics(self) -> None:
        self.switch_screen("analytics")

    def action_show_help(self) -> None:
        self.push_screen("help")

    def action_go_back(self) -> None:
        if len(self.screen_stack) > 1:
            self.pop_screen()
