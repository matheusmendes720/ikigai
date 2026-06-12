"""Tests for operational.tui.screens (import smoke tests)."""
from __future__ import annotations

from operational.tui.screens.dashboard_screen import DashboardScreen
from operational.tui.screens.daily_flow_screen import DailyFlowScreen
from operational.tui.screens.pomodoro_timer_screen import PomodoroTimerScreen
from operational.tui.screens.habits_screen import HabitsScreen
from operational.tui.screens.metrics_screen import MetricsScreen
from operational.tui.screens.policy_screen import PolicyScreen
from operational.tui.screens.journal_screen import JournalScreen


def test_dashboard_screen_import() -> None:
    assert DashboardScreen is not None


def test_daily_flow_screen_import() -> None:
    assert DailyFlowScreen is not None


def test_pomodoro_timer_screen_import() -> None:
    assert PomodoroTimerScreen is not None


def test_habits_screen_import() -> None:
    assert HabitsScreen is not None


def test_metrics_screen_import() -> None:
    assert MetricsScreen is not None


def test_policy_screen_import() -> None:
    assert PolicyScreen is not None


def test_journal_screen_import() -> None:
    assert JournalScreen is not None