"""Operator TUI — Textual App.

Three-tab dashboard:
  [1] Adapters     — fork adapter registry + storage path liveness
  [2] Backend      — backend process status (mcp_gateway, review_queue_worker)
  [3] Queue        — pending TaskChange events in data/review_queue/

Auto-refresh every 5s. Press `r` to refresh, `q` to quit.
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Static

from interfaces.tui.operator.data import (
    load_adapter_rows,
    load_backend_rows,
    load_queue_rows,
)


class SummaryPanel(Static):
    """Top-of-screen summary banner (one line per metric)."""

    def compose(self) -> ComposeResult:
        yield Static("", id="summary-line", classes="summary-row")


class OperatorApp(App):
    """Operator control-plane dashboard."""

    CSS_PATH = "styles.tcss"
    TITLE = "IKIGAI Operator"
    SUB_TITLE = "Backend control plane"

    BINDINGS = [
        Binding("1", "show_adapters", "Adapters"),
        Binding("2", "show_backend", "Backend"),
        Binding("3", "show_queue", "Queue"),
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
        table.add_columns("Name", "Phase", "Running", "PID", "Description")
        for row in rows:
            running_cell = "✅" if row.running else "⏸"
            pid_cell = str(row.pid) if row.pid is not None else "—"
            table.add_row(
                row.name,
                row.phase,
                running_cell,
                pid_cell,
                row.description,
            )
        content.mount(table)

    def _render_queue(self) -> None:
        content = self.query_one("#content", Container)
        content.remove_children()

        rows = load_queue_rows(limit=100)
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
                f"[dim]Total: {len(rows)} (showing up to 100)[/dim]"
            )

        if not rows:
            return

        table = DataTable(zebra_stripes=True, cursor_type="row")
        table.add_columns("Event ID", "UEID", "Action", "Source Fork", "Status", "Timestamp")
        for row in rows:
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
            )
        content.mount(table)


__all__ = ["OperatorApp", "SummaryPanel"]
