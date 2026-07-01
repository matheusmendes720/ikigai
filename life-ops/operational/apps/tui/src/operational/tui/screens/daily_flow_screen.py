"""Daily Flow Screen for PAV TUI — data-bound.

Shows the time blocks for the selected period (MANHA/TARDE/NOITE) for
the selected date. Reads from the ``time_blocks`` repo via
``operational.cli.state``. Tab navigation switches periods.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, ClassVar

from operational.cli.state import journals as journals_repo
from operational.cli.state import sleep_records as sleep_repo
from operational.cli.state import time_blocks as tb_repo
from operational.tui.widgets.time_block import TimeBlockDisplay
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, Tab, Tabs

if TYPE_CHECKING:
    from textual.app import ComposeResult


def _latest_data_date() -> date | None:
    """Return the latest date that has sleep or journal data, or None."""
    dates: set[date] = set()
    try:
        for s in sleep_repo.list():
            d = getattr(s, "date", None)
            if d is not None:
                dates.add(d)
    except Exception:
        pass
    try:
        for j in journals_repo.list():
            d = getattr(j, "date", None)
            if d is not None:
                dates.add(d)
    except Exception:
        pass
    return max(dates) if dates else None


def _classify_status(block) -> str:
    """Return one of "OK", "WARN", "PEND", "ACTIVE" for a time block."""
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
        """Mount TimeBlockDisplay widgets for the blocks of this period.

        Anchors to the latest data date (not date.today()) so blocks
        are shown even when the dataset is from a past period.
        """
        for w in self.query(TimeBlockDisplay):
            w.remove()

        content = self.query_one("#period-content", Static)
        empty = self.query_one("#empty-msg", Static)

        effective_today = _latest_data_date() or date.today()
        period_value = period.upper()
        try:
            all_blocks = list(tb_repo.list())
        except Exception:
            all_blocks = []
        blocks_for_period = [
            b for b in all_blocks
            if getattr(b, "start", None) and b.start.date() == effective_today
            and getattr(b.period, "value", str(b.period)).upper() == period_value
        ]

        if not blocks_for_period:
            content.update("")
            empty.update(
                f"[dim]Nenhum bloco para {period} em {effective_today.isoformat()}.[/dim]\n"
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
            lines.append(f"  {_status_glyph(status)}  [{period}]  {label}  {start}→{end}")
        content.update("\n".join(lines))

    def action_prev_period(self) -> None:
        tabs = self.query_one("Tabs", Tabs)
        tabs.action_previous()

    def action_next_period(self) -> None:
        tabs = self.query_one("Tabs", Tabs)
        tabs.action_next()

    def action_toggle_tab(self) -> None:
        tabs = self.query_one("Tabs", Tabs)
        tabs.action_next()

    def on_tabActivated(self, event: Tabs.TabActivated) -> None:  # noqa: N802
        """Switch period view when user clicks a tab."""
        tab_id = event.tab.id or ""
        period_map = {"tab-manha": "MANHA", "tab-tarde": "TARDE", "tab-noite": "NOITE"}
        if tab_id in period_map:
            self._show_period(period_map[tab_id])


def _status_glyph(status: str) -> str:
    """Return a Rich markup glyph for a block status."""
    return {
        "OK":    "[bold green]✓[/bold green]",
        "WARN":  "[bold yellow]⚠[/bold yellow]",
        "ACTIVE": "[bold cyan]▶[/bold cyan]",
        "PEND":  "[dim]○[/dim]",
    }.get(status, "[dim]?[/dim]")
