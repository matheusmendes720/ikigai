"""Daily Flow Screen for PAV TUI."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.widgets import Footer, Header, Static, Tab, Tabs

from operational.tui.widgets.time_block import TimeBlockDisplay

if TYPE_CHECKING:
    from textual.app import ComposeResult


class DailyFlowScreen(Screen):
    """Morning/Tarde/Noite period view with routines."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Tabs(
            Tab("MANHA", id="tab-manha"),
            Tab("TARDE", id="tab-tarde"),
            Tab("NOITE", id="tab-noite"),
        )
        yield Static("Morning routines appear here", id="period-content")
        yield TimeBlockDisplay(label="Acordar", start="06:00", end="06:30", status="OK", period="MANHA")
        yield TimeBlockDisplay(label="Meditar", start="06:30", end="07:00", status="OK", period="MANHA")
        yield TimeBlockDisplay(label="Exercitar", start="07:00", end="08:00", status="WARN", period="MANHA")
        yield Footer()

    def on_mount(self) -> None:
        pass
