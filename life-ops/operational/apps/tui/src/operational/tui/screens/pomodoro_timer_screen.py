"""Pomodoro Timer Screen for PAV TUI."""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Digits, Footer, Header, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class PomodoroTimerScreen(Screen):
    """Active pomodoro timer with state machine visualization."""

    BINDINGS: ClassVar = [
        Binding("s", "start_timer", "Start", show=False),
        Binding("p", "pause_timer", "Pause", show=False),
        Binding("period", "skip_break", "Skip", show=False),
        Binding("a", "abort_timer", "Abort", show=False),
    ]

    CSS = """
PomodoroTimerScreen {
    background: $panel;
    layout: vertical;
    align: center middle;
}
#pomo-title {
    height: 3;
    width: 100%;
    padding: 1 2;
    background: $surface;
    color: $text;
    text-style: bold;
}
#pomo-timer {
    height: 7;
    width: 100%;
    padding: 1 2;
    content-align: center middle;
    color: $error;
    text-style: bold;
}
#pomo-status, #fsm-diagram, #state-label {
    height: 3;
    width: 100%;
    padding: 0 2;
    color: $text-muted;
}
#btn-start, #btn-pause, #btn-skip, #btn-abort {
    width: 100%;
    margin: 0 1;
}
"""

    def compose(self) -> ComposeResult:
        """Compose the pomodoro timer screen widgets."""
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
        """Initialize timer state on mount."""
        self._state = "IDLE"
        self._time_left = 25 * 60
        self._update_ui()

    def _update_ui(self) -> None:
        mins, secs = divmod(self._time_left, 60)
        self.query_one("#pomo-timer", Digits).update(f"{mins:02d}:{secs:02d}")
        self.query_one("#state-label", Static).update(f"State: {self._state}")
        self.query_one("#btn-start", Button).disabled = self._state != "IDLE"
        self.query_one("#btn-pause", Button).disabled = self._state != "WORK"
        self.query_one("#btn-skip", Button).disabled = self._state not in ("WORK", "BREAK")
        self.query_one("#btn-abort", Button).disabled = self._state == "IDLE"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events for timer control."""
        btn_id = event.button.id or ""
        if btn_id == "btn-start":
            self._state = "WORK"
            self._time_left = 25 * 60
        elif btn_id == "btn-pause":
            self._state = "BREAK"
            self._time_left = 5 * 60
        elif btn_id == "btn-skip":
            self._state = "WORK"
            self._time_left = 25 * 60
        elif btn_id == "btn-abort":
            self._state = "IDLE"
            self._time_left = 25 * 60
        self._update_ui()