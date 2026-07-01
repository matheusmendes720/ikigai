"""Journal Screen for PAV TUI — data-bound.

Lists the most recent journal entries with a search input. Reads from
the ``journals`` repo. The ``Input`` widget at the top filters as you
type.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, ClassVar

from operational.cli.state import journals as journals_repo
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

MAX_ENTRIES = 20


class JournalScreen(Screen):
    """Journal entries list with search and filter."""

    BINDINGS: ClassVar = [
        Binding("slash", "focus_search", "Search", show=False),
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
#entries-list {
    width: 100%;
    height: auto;
    padding: 0 2;
    background: $surface;
    border: solid $border;
}
JournalScreen Static.entry {
    width: 100%;
    height: auto;
    padding: 0 2;
    border-bottom: solid $border;
    background: $surface;
    color: $text;
}
"""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Buscar journal...", id="journal-search")
        yield Static(
            "[TODAY] [YESTERDAY] [THIS WEEK] [ALL]   ·   "
            "[MANHA] [TARDE] [NOITE]",
            id="date-filter",
        )
        yield Static(id="period-filter")
        with Vertical(id="entries-list"):
            yield Static(id="empty-msg")
        yield Footer()

    def on_mount(self) -> None:
        self._query = ""
        self._refresh()

    def _refresh(self) -> None:
        # Remove previously rendered entry rows (keep the empty-msg)
        container = self.query_one("#entries-list")
        for child in list(container.children):
            if child.id != "empty-msg":
                child.remove()

        try:
            entries = sorted(
                journals_repo.list(),
                key=lambda e: getattr(e, "date", None) or date.min,
                reverse=True,
            )
        except Exception:
            entries = []

        if self._query:
            q = self._query.lower()
            entries = [
                e for e in entries
                if q in str(getattr(e, "entry_text", "")).lower()
                or q in str(getattr(e, "desvios", "")).lower()
                or q in str(getattr(e, "licoes_aprendidas", "")).lower()
            ]

        entries = entries[:MAX_ENTRIES]

        if not entries:
            empty = self.query_one("#empty-msg", Static)
            if self._query:
                empty.update(f"[dim]Nenhum resultado para '{self._query}'.[/dim]")
            else:
                empty.update(
                    "[dim]Nenhuma entrada de diário ainda.[/dim]\n"
                    "[dim]Adicione com: `pav journal create --text ...`[/dim]"
                )
            return

        self.query_one("#empty-msg", Static).update("")

        for e in entries:
            d = getattr(e, "date", None)
            ts = d.strftime("%H:%M") if d and hasattr(d, "strftime") else "—"
            kind = "CHECK-IN" if getattr(e, "energia_nivel", None) is not None else "JOURNAL"
            text = getattr(e, "entry_text", "")[:80]
            energia = getattr(e, "energia_nivel", None)
            foco = getattr(e, "foco_nivel", None)
            meta = ""
            if energia is not None or foco is not None:
                meta = f"  E:{energia or '-'} F:{foco or '-'}"
            line = f"[{ts}] [{kind:<9}] {text}{meta}"
            self.query_one("#entries-list").mount(Static(line, classes="entry"))

    def on_input_changed(self, event: Input.Changed) -> None:
        self._query = event.value
        self._refresh()

    def action_focus_search(self) -> None:
        self.query_one("#journal-search", Input).focus()

    def action_new_entry(self) -> None:
        self.app.notify(
            "Use `pav journal create --text ...` para nova entrada.",
            title="Nova entrada",
        )

    def action_filter_entries(self) -> None:
        self.app.notify("Filtro em breve.", title="Filtrar")
