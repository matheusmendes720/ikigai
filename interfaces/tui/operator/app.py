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
    load_skill_rows,
    load_task_rows,
)

# W5.3 — KillSwitch consumer UX (5th tab + persistent banner)
from interfaces.tui.operator._kill_switch_tab import (
    KillSwitchTab,
    banner_widget,
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
        Binding("5", "show_kill_switch", "KillSwitch"),
        Binding("6", "show_skills", "Skills"),
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

    # W5.3 — 5th tab (KillSwitch) action
    def action_show_kill_switch(self) -> None:
        self.active_tab = "kill_switch"
        self._render_kill_switch()

    # T-9.3 — 6th tab (Skills) action
    def action_show_skills(self) -> None:
        self.active_tab = "skills"
        self._render_skills()

    def _non_task_refresh(self) -> None:
        """Refresh non-task tabs (called every 5s)."""
        if self.active_tab == "adapters":
            self._render_adapters()
        elif self.active_tab == "backend":
            self._render_backend()
        elif self.active_tab == "queue":
            self._render_queue()
        elif self.active_tab == "kill_switch":
            self._render_kill_switch()
        elif self.active_tab == "skills":
            self._render_skills()

        # W5.3 — banner must update whenever the auto-refresh fires,
        # regardless of which tab is showing (per design §4.4).
        self._update_killswitch_banner()

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
        self.push_screen(QueueDetailScreen(event_id=row.event_id, payload=row.payload))

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

            label = _dt.datetime.fromtimestamp(self._tasks_watcher_mtime).strftime(
                "%H:%M:%S"
            )
        status_widget.update(f"Live: watching data/tasks.jsonl (mtime: {label})")

    # ---- Render helpers ----

    def _render_tasks(self) -> None:
        content = self.query_one("#content", Container)
        content.remove_children()
        # W5.3 — banner (active-only)
        self._mount_banner(content)

        rows = load_task_rows()

        summary = SummaryPanel()
        content.mount(summary)
        if not rows:
            summary.update(
                "[bold]Tasks[/bold]  ·  [dim]No tasks in data/tasks.jsonl[/dim]"
            )
        else:
            summary.update(f"[bold]Tasks[/bold]  ·  [green]{len(rows)} task(s)[/green]")

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
        # W5.3 — banner (active-only)
        self._mount_banner(content)

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
        # W5.3 — banner (active-only)
        self._mount_banner(content)

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
                "—" if row.started_at is None else _format_started_at(row.started_at)
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
        # W5.3 — banner (active-only)
        self._mount_banner(content)

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
        table.add_columns(
            "Event ID", "UEID", "Action", "Source Fork", "Status", "Timestamp"
        )
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

    # === W5.3 — 5th tab + persistent status banner ===

    def _mount_banner(self, content) -> None:
        """Mount the kill-switch status banner (if active) at top of `content`.

        Per design doc §4.4: banner is read-only — no `p` / `r` keys
        without `shift+` prefix. The actual recovery keys live on
        `KillSwitchTab` (this tab itself).
        """
        banner = banner_widget()
        if banner is not None:
            content.mount(banner)

    def _update_killswitch_banner(self) -> None:
        """Refresh an existing banner widget (auto-refresh hook)."""
        try:
            existing = self.query_one("#killswitch-banner", Static)
        except Exception:
            return  # banner not mounted — that's fine
        fresh = banner_widget()
        if fresh is None:
            existing.remove()
            return
        # Re-render in place
        from sys_ikigai.security.kill_switch import (
            check_kill_switch,
            _recovery_path_for_reason,  # type: ignore[attr-defined]  # noqa: PGH003
        )

        from interfaces.tui.operator._kill_switch_tab import (
            _count_recent_kill_switch_events,
            _last_kill_switch_trigger,
            VAULT_ROOT as _VR,
            DATA_ROOT as _DR,
        )

        status = check_kill_switch(_VR, _DR)
        if not status.is_active:
            existing.remove()
            return
        in_1h = _count_recent_kill_switch_events()
        last = _last_kill_switch_trigger()
        lines = [
            "[bold red]KILL SWITCH ACTIVE[/bold red] — "
            f"reason: [yellow]{status.active_reason}[/yellow]",
            f"events in last 1h: {in_1h}  ·  last trigger: {last or '—'}",
            f"recovery: {_recovery_path_for_reason(status.active_reason)}",
        ]
        existing.update("\n".join(lines))

    def _render_kill_switch(self) -> None:
        """Render the 5th tab — KillSwitch state + recovery path.

        The widget itself is the single child of `#content`; refreshes
        happen via `KillSwitchTab.on_mount` (called once) and from
        `_non_task_refresh` (every 5s while this tab is active).
        """
        content = self.query_one("#content", Container)
        content.remove_children()
        # Banner first (per design §4.4 — visible on every tab when active)
        self._mount_banner(content)
        tab = KillSwitchTab(id="killswitch-tab")
        content.mount(tab)

    def _render_skills(self) -> None:
        """Render the 6th tab — read-only skill manifest viewer.

        Displays name, entry_point, description, actor, outputs, and file_path
        for the 4 canonical planning-cycle skills (daily/weekly/monthly/quarterly).
        Per CLAUDE.md dual-layer architecture: TUI is observer-only (no writes).
        """
        content = self.query_one("#content", Container)
        content.remove_children()
        self._mount_banner(content)

        rows = load_skill_rows()

        summary = SummaryPanel()
        content.mount(summary)
        if not rows:
            summary.update(
                "[bold]Skills[/bold]  ·  "
                "[dim]No skill manifests found[/dim]"
            )
        else:
            summary.update(
                f"[bold]Skills[/bold]  ·  "
                f"[green]{len(rows)} skill(s)[/green]  ·  "
                f"[dim]observer-only (per dual-layer architecture)[/dim]"
            )

        if not rows:
            return

        table = DataTable(zebra_stripes=True, cursor_type="row")
        table.add_columns("Name", "Entry Point", "Description", "Actor", "Outputs", "File Path")
        for row in rows:
            if not row.outputs:
                outputs_cell = "—"
            else:
                outputs_cell = ", ".join(str(o) for o in row.outputs)
            actor_cell = f"[cyan]{row.actor}[/cyan]"
            table.add_row(
                row.name,
                row.entry_point,
                row.description,
                actor_cell,
                outputs_cell,
                row.file_path,
                key=row.name,
            )
        content.mount(table)


def _format_started_at(mtime: float) -> str:
    """Format pidfile mtime as a short ISO-like timestamp (HH:MM:SS)."""
    import datetime as _dt

    return _dt.datetime.fromtimestamp(mtime).strftime("%H:%M:%S")


__all__ = ["OperatorApp", "SummaryPanel", "QueueDetailScreen"]
