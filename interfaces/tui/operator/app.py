"""Operator TUI — Textual App.

Four-tab dashboard:
  [1] Tasks        — live view of data/tasks.jsonl (Deep Agent output)
  [2] Adapters     — fork adapter registry + storage path liveness
  [3] Backend      — backend process status (mcp_gateway, review_queue_worker)
  [4] Queue        — pending TaskChange events in data/review_queue/

Tier 2 additions:
  - Backend tab: Started + Uptime columns (from pidfile mtime)
  - Queue tab:  press `d` to drill down on a row (shows full JSON payload)

Tasks tab auto-refreshes every 2s via filesystem poll on data/tasks.jsonl.
Press `r` to refresh, `q` to quit.
"""

from __future__ import annotations

import json as _json
import os
from textwrap import shorten

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Static

from interfaces.tui.operator.data import (
    TASKS_JSONL,
    format_uptime,
    load_adapter_rows,
    load_backend_rows,
    load_queue_rows,
    load_task_rows,
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
        Binding("1", "show_tasks", "Tasks"),
        Binding("2", "show_adapters", "Adapters"),
        Binding("3", "show_backend", "Backend"),
        Binding("4", "show_queue", "Queue"),
        Binding("d", "drilldown_queue", "Detail"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    active_tab: reactive[str] = reactive("tasks")
    _watcher_mtime: reactive[float | None] = reactive(None)
    _tasks_watcher_mtime: float | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(id="content")
        yield Footer()

    def on_mount(self) -> None:
        """Initial render."""
        self.action_show_tasks()
        # Auto-refresh every 5s for non-task tabs
        self.set_interval(5.0, self._non_task_refresh)
        # Live filesystem watcher on data/tasks.jsonl (2s poll)
        self._start_tasks_watcher()

    # ---- Tab actions ----

    def action_show_tasks(self) -> None:
        self.active_tab = "tasks"
        self._render_tasks()

    def action_show_adapters(self) -> None:
        self.active_tab = "adapters"
        self._render_adapters()

    def action_show_backend(self) -> None:
        self.active_tab = "backend"
        self._render_backend()

    def action_show_queue(self) -> None:
        self.active_tab = "queue"
        self._render_queue()

    def _non_task_refresh(self) -> None:
        """Refresh non-task tabs (called every 5s)."""
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

    # ---- Live filesystem watcher ----

    def _start_tasks_watcher(self) -> None:
        """Poll data/tasks.jsonl every 2s; reload Tasks tab on mtime change."""
        self.set_interval(2.0, self._poll_tasks_file)

    def _poll_tasks_file(self) -> None:
        """Called on the worker thread every 2s. Bumps _watcher_mtime on change."""
        if not TASKS_JSONL.exists():
            mtime: float | None = None
        else:
            try:
                mtime = os.path.getmtime(str(TASKS_JSONL))
            except OSError:
                mtime = None
        # Update reactive on main thread
        self.call_from_thread(self._set_watcher_mtime, mtime)

    def _set_watcher_mtime(self, mtime: float | None) -> None:
        """Set mtime and trigger Tasks tab reload when file changes."""
        if mtime != self._tasks_watcher_mtime:
            self._tasks_watcher_mtime = mtime
            self._watcher_mtime = mtime
            if self.active_tab == "tasks":
                self._render_tasks()
            self._update_watcher_status()

    def _update_watcher_status(self) -> None:
        """Refresh the status bar line. Safe to call before first render."""
        try:
            status_widget = self.query_one("#status-line", Static)
        except Exception:
            return  # widget not yet mounted
        if self._tasks_watcher_mtime is None:
            label = "(no tasks yet)"
        else:
            import datetime as _dt
            label = _dt.datetime.fromtimestamp(self._tasks_watcher_mtime).strftime("%H:%M:%S")
        status_widget.update(f"Live: watching data/tasks.jsonl (mtime: {label})")

    # ---- Render helpers ----

    def _render_tasks(self) -> None:
        content = self.query_one("#content", Container)
        content.remove_children()

        rows = load_task_rows()

        summary = SummaryPanel()
        content.mount(summary)
        if not rows:
            summary.update(
                "[bold]Tasks[/bold]  ·  "
                "[dim]No tasks in data/tasks.jsonl[/dim]"
            )
        else:
            summary.update(
                f"[bold]Tasks[/bold]  ·  "
                f"[green]{len(rows)} task(s)[/green]"
            )

        status_line = Static(
            f"Live: watching data/tasks.jsonl (mtime: {self._tasks_watcher_mtime})",
            id="status-line",
        )
        content.mount(status_line)

        if not rows:
            return

        table = DataTable(zebra_stripes=True, cursor_type="row")
        table.add_columns("UEID", "Title", "Due", "Priority", "Source Fork")
        for row in rows:
            title_cell = shorten(row.title, width=40, placeholder="...")
            table.add_row(
                row.ueid,
                title_cell,
                row.due or "—",
                row.priority,
                row.source_fork,
            )
        content.mount(table)

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
