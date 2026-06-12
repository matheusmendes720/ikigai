"""Pomodoro Timer Screen for PAV TUI."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.widgets import Button, Digits, Footer, Header, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class PomodoroTimerScreen(Screen):
    """Active pomodoro timer with state machine visualization."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("🍅 POMODORO", id="pomo-title")
        yield Digits("25:00", id="pomo-timer")
        yield Static("Round 1/4  |  S1 manha  |  IDLE", id="pomo-status")
        yield Static("IDLE → WORK → BREAK → WORK → LONG_BREAK → IDLE", id="fsm-diagram")
        yield Static("State: IDLE", id="state-label")
        yield Button("Start", id="btn-start")
        yield Button("Pause", id="btn-pause", disabled=True)
        yield Button("Skip Break", id="btn-skip", disabled=True)
        yield Button("Abort", id="btn-abort", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        pass
