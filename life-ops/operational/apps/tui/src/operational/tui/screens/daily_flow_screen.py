"""Daily Flow Screen for PAV TUI."""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, Tab, Tabs

from operational.tui.widgets.time_block import STATUS_INDICATORS, TimeBlockDisplay

if TYPE_CHECKING:
    from textual.app import ComposeResult


class DailyFlowScreen(Screen):
    """Morning/Tarde/Noite period view with routines."""

    BINDINGS: ClassVar = [
        Binding("left", "prev_period", "Prev", show=False),
        Binding("right", "next_period", "Next", show=False),
        Binding("t", "toggle_tab", "Tab", show=False),
    ]

    CSS = """
DailyFlowScreen {
    background: $panel;
    layout: vertical;
}
#tab-manha, #tab-tarde, #tab-noite {
    width: 100%;
}
#period-content {
    width: 100%;
    height: auto;
    padding: 1 2;
    background: $surface;
    color: $text;
}
TimeBlockDisplay {
    width: 100%;
    height: 3;
    margin: 0 1;
    border-bottom: solid $border;
    background: $surface;
}
"""

    def compose(self) -> ComposeResult:
        """Compose the daily flow screen widgets."""
        yield Header()
        yield Tabs(
            Tab("MANHA", id="tab-manha"),
            Tab("TARDE", id="tab-tarde"),
            Tab("NOITE", id="tab-noite"),
        )
        yield Static("Morning routines appear here", id="period-content")
        yield TimeBlockDisplay(label="Acordar", start="06:00", end="06:30",
                              status="OK", period="MANHA")
        yield TimeBlockDisplay(label="Meditar", start="06:30", end="07:00",
                              status="OK", period="MANHA")
        yield TimeBlockDisplay(label="Exercitar", start="07:00", end="08:00",
                              status="WARN", period="MANHA")
        yield Footer()

    def on_mount(self) -> None:
        """Set up the screen on mount."""
        self._show_period("MANHA")

    def _show_period(self, period: str) -> None:
        blocks = {
            "MANHA": [
                ("Acordar",   "06:00", "06:30", "OK"),
                ("Meditar",   "06:30", "07:00", "OK"),
                ("Exercitar", "07:00", "08:00", "WARN"),
            ],
            "TARDE": [
                ("Deep Work",  "09:00", "12:00", "OK"),
                ("Almoço",     "12:00", "13:00", "OK"),
                ("Deep Work",  "13:00", "17:00", "PEND"),
            ],
            "NOITE": [
                ("Review",    "18:00", "19:00", "OK"),
                ("Journal",   "21:00", "22:00", "OK"),
                ("Dormir",    "22:30", "06:00", "PEND"),
            ],
        }
        content = self.query_one("#period-content", Static)
        lines = "\n".join(
            f"  {STATUS_INDICATORS[s]}  [{period}]  {lbl}  {st}→{en}"
            for lbl, st, en, s in blocks.get(period, [])
        )
        content.update(lines or "Nenhum bloco para este período.")

    def on_tabs_tab_changed(self, event: Tabs.TabChanged) -> None:
        """Handle tab change events."""
        period = event.tab.id.replace("tab-", "").upper()
        self._show_period(period)
