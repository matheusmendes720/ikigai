"""Daily Flow Screen for PAV TUI — data-bound.

Shows the time blocks for the selected period (MANHA/TARDE/NOITE) for
the selected date. Reads from the ``time_blocks`` repo via
``operational.cli.state``. Tab navigation switches periods.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, ClassVar

from operational.cli.state import time_blocks as tb_repo
from operational.tui.widgets.time_block import TimeBlockDisplay
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, Tab, Tabs

if TYPE_CHECKING:
    from textual.app import ComposeResult


def _classify_status(block) -> str:
    """Return one of "OK", "WARN", "PEND", "ACTIVE" for a time block."""
    # Placeholder heuristic. Future: read from completion state of the
    # underlying routine / pomodoro that owns this block.
    if getattr(block, "completed", False):
        return "OK"
    return "PEND"


class DailyFlowScreen(Screen):
    """Morning/Tarde/Noite period view — reads time_blocks repo."""

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
#empty-msg {
    padding: 2 4;
    color: $text-muted;
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
        yield Header()
        yield Tabs(
            Tab("MANHA", id="tab-manha"),
            Tab("TARDE", id="tab-tarde"),
            Tab("NOITE", id="tab-noite"),
        )
        yield Static(id="period-content")
        yield Static(id="empty-msg")
        yield Footer()

    def on_mount(self) -> None:
        self._show_period("MANHA")

    def _show_period(self, period: str) -> None:
        """Mount TimeBlockDisplay widgets for the blocks of this period."""
        # Remove previously-rendered blocks
        for w in self.query(TimeBlockDisplay):
            w.remove()

        content = self.query_one("#period-content", Static)
        empty = self.query_one("#empty-msg", Static)

        today = date.today()
        period_value = period.upper()
        try:
            all_blocks = list(tb_repo.list())
        except Exception:
            all_blocks = []
        blocks_for_period = [
            b for b in all_blocks
            if getattr(b, "start", None) and b.start.date() == today
            and getattr(b.period, "value", str(b.period)).upper() == period_value
        ]

        if not blocks_for_period:
            content.update("")
            empty.update(
                f"[dim]Nenhum bloco para {period} em {today.isoformat()}.[/dim]\n"
                f"[dim]Adicione com: `pav block create {period_value} --label ...`[/dim]"
            )
            return

        empty.update("")
        lines: list[str] = []
        for b in blocks_for_period:
            label = getattr(b, "label", "Bloco")
            start = b.start.strftime("%H:%M") if getattr(b, "start", None) else "—"
            end = b.end.strftime("%H:%M") if getattr(b, "end", None) else "—"
            status = _classify_status(b)
            # _status_glyph returns Rich markup like "[bold green]✓[/bold green]".
            # We embed it directly — do NOT wrap in another `[…]`.
            lines.append(f"  {_status_glyph(status)}  [{period}]  {label}  {start}→{end}")
        content.update("\n".join(lines))

    def on_tabs_tab_changed(self, event: Tabs.TabChanged) -> None:
        period = event.tab.id.replace("tab-", "").upper() if event.tab.id else "MANHA"
        self._show_period(period)

    def action_prev_period(self) -> None:
        order = ["MANHA", "TARDE", "NOITE"]
        tabs = self.query_one(Tabs)
        current = tabs.active_tab.id.replace("tab-", "").upper() if tabs.active_tab else "MANHA"
        idx = order.index(current) if current in order else 0
        new = order[(idx - 1) % 3]
        self.query_one(f"#tab-{new.lower()}", Tab).activate()

    def action_next_period(self) -> None:
        order = ["MANHA", "TARDE", "NOITE"]
        tabs = self.query_one(Tabs)
        current = tabs.active_tab.id.replace("tab-", "").upper() if tabs.active_tab else "MANHA"
        idx = order.index(current) if current in order else 0
        new = order[(idx + 1) % 3]
        self.query_one(f"#tab-{new.lower()}", Tab).activate()

    def action_toggle_tab(self) -> None:
        self.action_next_period()


def _status_glyph(status: str) -> str:
    return {
        "OK": "[bold green]✓[/bold green]",
        "WARN": "[bold yellow]⚠[/bold yellow]",
        "PEND": "[dim]◌[/dim]",
        "ACTIVE": "[bold cyan]●[/bold cyan]",
        "CRIT": "[bold red]✗[/bold red]",
    }.get(status, "[dim]○[/dim]")
