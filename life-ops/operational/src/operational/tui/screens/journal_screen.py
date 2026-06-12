"""Journal Screen for PAV TUI."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class JournalScreen(Screen):
    """Journal entries list with search, filter, and entry expansion."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Buscarjournal...", id="journal-search")
        yield Static("[TODAY] [YESTERDAY] [THIS WEEK] [ALL]", id="date-filter")
        yield Static("[MANHA] [TARDE] [NOITE]", id="period-filter")
        yield Static("[17:07] [CHECK-IN] Energia: 7, Foco: 8 (chk_20260609_170706)", id="entry-1")
        yield Static("[17:07] [ROUTINE] Start: Hardwork Dev (CORE)", id="entry-2")
        yield Static("[14:30] [POMODORO] Completed S2 tarde - 4 rounds", id="entry-3")
        yield Footer()

    def on_mount(self) -> None:
        pass
