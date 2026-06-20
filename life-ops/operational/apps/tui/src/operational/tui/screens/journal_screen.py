"""Journal Screen for PAV TUI."""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class JournalScreen(Screen):
    """Journal entries list with search, filter, and entry expansion."""

    BINDINGS: ClassVar = [
        Binding("/", "focus_search", "Search", show=False),
        Binding("n", "new_entry", "New", show=False),
        Binding("f", "filter_entries", "Filter", show=False),
    ]

    CSS = """
JournalScreen {
    background: $panel;
    layout: vertical;
}
#journal-search {
    width: 100%;
    margin: 1 0;
    background: $surface;
}
#date-filter, #period-filter {
    height: 3;
    width: 100%;
    padding: 1 2;
    background: $surface;
    color: $text-muted;
}
#entry-1, #entry-2, #entry-3 {
    width: 100%;
    height: 3;
    padding: 0 2;
    border-bottom: solid $border;
    background: $surface;
    color: $text;
}
"""

    def compose(self) -> ComposeResult:
        """Compose the journal screen widgets."""
        yield Header()
        yield Input(placeholder="Buscar journal...", id="journal-search")
        yield Static("[TODAY] [YESTERDAY] [THIS WEEK] [ALL]", id="date-filter")
        yield Static("[MANHA] [TARDE] [NOITE]", id="period-filter")
        yield Static("[17:07] [CHECK-IN] Energia: 7, Foco: 8 (chk_20260609_170706)", id="entry-1")
        yield Static("[17:07] [ROUTINE] Start: Hardwork Dev (CORE)", id="entry-2")
        yield Static("[14:30] [POMODORO] Completed S2 tarde - 4 rounds", id="entry-3")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize journal entries on mount."""
        entries = [
            ("[17:07] [CHECK-IN]  Energia: 7, Foco: 8  (chk_20260612_170706)",),
            ("[17:07] [ROUTINE]   Start: Hardwork Dev (CORE)",),
            ("[14:30] [POMODORO]  Completed S2 tarde - 4 rounds",),
            ("[09:00] [CHECK-IN]  Energia: 8, Foco: 9  (chk_20260611_090012)",),
            ("[20:00] [ROUTINE]  Evening shutdown + journal",),
        ]
        for i, (entry_text,) in enumerate(entries, start=1):
            try:
                w = self.query_one(f"#entry-{i}", Static)
                w.update(entry_text)
            except Exception:  # noqa: BLE001, S110
                pass
