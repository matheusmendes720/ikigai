"""Help Screen — modal overlay with full keybinding reference."""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Key


class HelpScreen(ModalScreen):
    """Full keybinding reference — triggered by Ctrl+H."""

    CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-panel {
        width: 70;
        height: auto;
        background: $overlay;
        border: solid $primary;
        padding: 1 2;
    }
    .section-header {
        text-style: bold;
        color: $primary;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar = [
        Binding("escape", "dismiss", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Compose the help overlay."""
        with Container(id="help-panel"):
            yield Static("⌨  PAV-OS KEYBINDINGS", id="help-title")
            yield Static("L0 — Universal", classes="section-header")
            yield Static("[q]  Quit   [Ctrl+H]  This help   [Esc]  Back / Dismiss")
            yield Static("L1 — Navigation", classes="section-header")
            yield Static("[1] Dashboard  [2] Daily  [3] Timer  [4] Habits")
            yield Static("[5] Metrics   [6] Policy [7] Journal")
            yield Static("L2 — Screen Actions (shown in footer)", classes="section-header")
            yield Static("Dashboard: [q] [ctrl+h] [1-7]")
            yield Static("Daily Flow: [←/→] period  [t] tab  [1-7]")
            yield Static("Pomodoro:   [s] start  [p] pause  [.] skip  [a] abort  [1-7]")
            yield Static("Habits:     [a] add  [e] edit  [d] delete  [f] filter  [1-7]")
            yield Static("Metrics:    [7d/30d] toggle  [1-7]")
            yield Static("Policy:     [h] history  [s] setpoints  [1-7]")
            yield Static("Journal:    [/] search  [n] new  [f] filter  [1-7]")
            yield Static("L3 — Power", classes="section-header")
            yield Static("[:]  Command mode   [g]  Go to dashboard")
            yield Button("Close [Esc]", id="btn-close", variant="primary")

    def action_dismiss(self) -> None:
        """Dismiss the help overlay."""
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:  # noqa: ARG002
        """Handle button press to dismiss."""
        self.dismiss()

    def on_key(self, event: Key) -> None:
        """Handle Ctrl+H for dismiss (works even when app-level binding intercepts)."""
        if getattr(event, "key", None) == "ctrl+h":
            self.dismiss()
