"""Operator TUI — Textual App.

Three-tab dashboard:
  [1] Adapters     — fork adapter registry + storage path liveness
  [2] Backend      — backend process status (mcp_gateway, review_queue_worker)
  [3] Queue        — pending TaskChange events in data/review_queue/

Tier 2 additions:
  - Backend tab: Started + Uptime columns (from pidfile mtime)
  - Queue tab:  press `d` to drill down on a row (shows full JSON payload)

Auto-refresh every 5s. Press `r` to refresh, `q` to quit.
"""

from __future__ import annotations

import json as _json

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Static

from interfaces.tui.operator.data import (
    format_uptime,
    load_adapter_rows,
    load_backend_rows,
    load_queue_rows,
)


class SummaryPanel(Static):
    """Top-of-screen summary banner (one line per metric)."""

    def compose(self) -> ComposeResult:
        yield Static("", id="summary-line", classes="summary-row")


class QueueDetailScreen(ModalScreen[None]):
    """Read-only modal showing the full JSON payload for a queue row.

    Press `escape` or `q` to dismiss. Read-only by design — operator
    TUI MUST NOT mutate state (dual-layer architecture invariant).
    """

    BINDINGS = [
        Binding("escape", "dismiss_detail", "Close"),
        Binding("q", "dismiss_detail", "Close"),
    ]

    def __init__(self, event_id: str, payload: dict[str, object]) -> None:
        super().__init__()
        self._event_id = event_id
        self._payload = payload

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(
            f"[bold]Event {self._event_id}[/bold]\n\n"
            f"```json\n{_json.dumps(self._payload, indent=2, ensure_ascii=False)}\n```",
            id="payload-body",
        )
        yield Footer()

    def action_dismiss_detail(self) -> None:
        self.dismiss(None)


class OperatorApp(App):
    """Operator control-plane dashboard."""

    CSS_PATH = "styles.tcss"
    TITLE = "IKIGAI Operator"
    SUB_TITLE = "Backend control plane"

    BINDINGS = [
        Binding("1", "show_adapters", "Adapters"),
        Binding("2", "show_backend", "Backend"),
        Binding("3", "show_queue", "Queue"),
        Binding("d", "drilldown_queue", "Detail"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    active_tab: reactive[str] = reactive("adapters")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(id="content")
        yield Footer()

    def on_mount(self) -> None:
        """Initial render."""
        self.action_show_adapters()
        # Auto-refresh every 5s
        self.set_interval(5.0, self.action_refresh)

    # ---- Tab actions ----

    def action_show_adapters(self) -> None:
        self.active_tab = "adapters"
        self._render_adapters()

    def action_show_backend(self) -> None:
        self.active_tab = "backend"
        self._render_backend()

    def action_show_queue(self) -> None:
        self.active_tab = "queue"
        self._render_queue()

    def action_refresh(self) -> None:
        if self.active_tab == "adapters":
            self._render_adapters()
        elif self.active_tab == "backend":
            self._render_backend()
        elif self.active_tab == "queue":
            self._render_queue()

    def action_drilldown_queue(self) -> None:
        """Open modal with the full payload of the highlighted queue row."""
        if self.active_tab != "queue":
            return
        table = self.query_one("#content DataTable", DataTable)
        if table.row_count == 0:
            return
        cursor_row = table.cursor_row
        if cursor_row is None or cursor_row < 0:
            return
        try:
            row_key = table.coordinate_to_cell_key((cursor_row, 0)).row_key
        except Exception:
            return
        # Pull the cached row payload from the table's row index
        rows = self._current_queue_rows
        if not rows:
            return
        try:
            index = int(row_key.value)
        except (ValueError, AttributeError):
            return
        if index < 0 or index >= len(rows):
            return
        row = rows[index]
        self.push_screen(
            QueueDetailScreen(event_id=row.event_id, payload=row.payload)
        )

    # ---- Render helpers ----

    def _render_adapters(self) -> None:
        content = self.query_one("#content", Container)
        content.remove_children()

        rows = load_adapter_rows()
        ok_count = sum(1 for r in rows if r.exists)
        missing_count = len(rows) - ok_count

        summary = SummaryPanel()
        content.mount(summary)
        summary.update(
            f"[bold]Fork Adapters[/bold]  ·  "
            f"[green]{ok_count} online[/green]  ·  "
            f"[red]{missing_count} missing[/red]  ·  "
            f"[dim]Total: {len(rows)}[/dim]"
        )

        table = DataTable(zebra_stripes=True, cursor_type="row")
        table.add_columns("Name", "Slice Type", "Exists", "Storage Path")
        for row in rows:
            exists_cell = "✅" if row.exists else "❌"
            table.add_row(
                row.name,
                row.slice_type,
                exists_cell,
                row.storage_path,
            )
        content.mount(table)

    def _render_backend(self) -> None:
        content = self.query_one("#content", Container)
        content.remove_children()

        rows = load_backend_rows()
        running_count = sum(1 for r in rows if r.running)
        stopped_count = len(rows) - running_count

        summary = SummaryPanel()
        content.mount(summary)
        summary.update(
            f"[bold]Backend Processes[/bold]  ·  "
            f"[green]{running_count} running[/green]  ·  "
            f"[yellow]{stopped_count} stopped[/yellow]  ·  "
            f"[dim]Total: {len(rows)}[/dim]"
        )

        table = DataTable(zebra_stripes=True, cursor_type="row")
        table.add_columns(
            "Name", "Phase", "Running", "PID", "Started", "Uptime", "Description"
        )
        for row in rows:
            running_cell = "✅" if row.running else "⏸"
            pid_cell = str(row.pid) if row.pid is not None else "—"
            started_cell = (
                "—" if row.started_at is None
                else _format_started_at(row.started_at)
            )
            uptime_cell = format_uptime(row.started_at)
            table.add_row(
                row.name,
                row.phase,
                running_cell,
                pid_cell,
                started_cell,
                uptime_cell,
                row.description,
            )
        content.mount(table)

    def _render_queue(self) -> None:
        content = self.query_one("#content", Container)
        content.remove_children()

        rows = load_queue_rows(limit=100)
        self._current_queue_rows = rows  # cache for drilldown
        pending_count = sum(1 for r in rows if r.status == "pending")

        summary = SummaryPanel()
        content.mount(summary)
        if not rows:
            summary.update(
                "[bold]Review Queue[/bold]  ·  "
                "[dim]No events in data/review_queue/[/dim]"
            )
        else:
            summary.update(
                f"[bold]Review Queue[/bold]  ·  "
                f"[yellow]{pending_count} pending[/yellow]  ·  "
                f"[dim]Total: {len(rows)} (showing up to 100)  ·  "
                f"[bold]Press `d` to drill down[/bold][/dim]"
            )

        if not rows:
            return

        table = DataTable(zebra_stripes=True, cursor_type="row")
        table.add_columns("Event ID", "UEID", "Action", "Source Fork", "Status", "Timestamp")
        for index, row in enumerate(rows):
            status_cell = (
                "[yellow]⏳ pending[/yellow]"
                if row.status == "pending"
                else f"[green]{row.status}[/green]"
            )
            table.add_row(
                row.event_id,
                row.ueid,
                row.action,
                row.source_fork,
                status_cell,
                row.timestamp,
                key=str(index),
            )
        content.mount(table)


def _format_started_at(mtime: float) -> str:
    """Format pidfile mtime as a short ISO-like timestamp (HH:MM:SS)."""
    import datetime as _dt

    return _dt.datetime.fromtimestamp(mtime).strftime("%H:%M:%S")


__all__ = ["OperatorApp", "SummaryPanel", "QueueDetailScreen"]
