"""ikigai-taskdog TUI — Textual-based taskdog manager.

UX 2026-09-10: User needed a TUI equivalent to upstream `taskdog tui`
but without the HTTP server requirement. This is a Textual app that
reads/writes the taskdog SQLite directly via TaskdogAdapter.

Layout:
  +-------------------+-------------------+
  |  Task List (table)  | Detail (panel)     |
  |  [ueid]  name     |  field1: value    |
  |  [ueid]  name     |  field2: value    |
  |  ...               |  ...              |
  +-------------------+-------------------+
  [a]dd  [e]dit  [d]elete  [r]efresh  [q]uit

No server. No upstream dependency. Just SQLite + Textual.
"""

from __future__ import annotations

import argparse
import json as _json
import sqlite3
import sys
from pathlib import Path

# Bootstrap sys.path for entry-point shells.
_SCRIPT_DIR = Path(__file__).resolve()
_WORKTREE_SRC = _SCRIPT_DIR.parents[2]
for _p in (str(_WORKTREE_SRC.parent), str(_WORKTREE_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def cmd_tui(args: argparse.Namespace) -> int:
    """Launch the Textual TUI."""
    from src.mesh.adapters.taskdog import TaskdogAdapter, TASKDOG_DB

    if not TASKDOG_DB.exists():
        print(f"taskdog DB not found at {TASKDOG_DB}", file=sys.stderr)
        return 1

    # Lazy-import Textual to keep CLI fast on `list`/`add`/`show`
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical
    from textual.reactive import reactive
    from textual.widgets import DataTable, Footer, Header, Input, Static

    class TaskdogTui(App):
        """Two-pane Textual app: task list on left, detail on right."""

        CSS = """
        #left { width: 50%; border-right: solid $accent; }
        #right { width: 50%; padding: 1; }
        #status { dock: bottom; height: 1; background: $boost; color: $text; }
        """

        BINDINGS = [
            Binding("a", "add_task", "Add"),
            Binding("e", "edit_status", "Edit status"),
            Binding("d", "delete_task", "Delete"),
            Binding("r", "refresh", "Refresh"),
            Binding("q", "quit", "Quit"),
        ]

        selected_ueid: reactive[str | None] = reactive(None)

        def __init__(self, adapter: TaskdogAdapter):
            super().__init__()
            self.adapter = adapter

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Horizontal():
                with Vertical(id="left"):
                    yield DataTable(id="task-table", cursor_type="row", zebra_stripes=True)
                with Vertical(id="right"):
                    yield Static("Select a task to see details.", id="detail")
            yield Static("", id="status")
            yield Footer()

        def on_mount(self) -> None:
            table = self.query_one("#task-table", DataTable)
            table.add_columns("UEID", "Name", "Status", "Priority", "Deadline")
            self.refresh()

        def action_refresh(self) -> None:
            """Reload all tasks from SQLite into the table."""
            self.refresh()

        def refresh(self) -> None:
            table = self.query_one("#task-table", DataTable)
            table.clear()
            tasks = self.adapter.list_all()
            tasks = [t for t in tasks if t.get("status") != "archived"]
            for t in tasks:
                table.add_row(
                    str(t.get("ueid", ""))[:24],
                    str(t.get("name", ""))[:40],
                    str(t.get("status", "")),
                    str(t.get("priority", "")),
                    str(t.get("deadline", "")),
                    key=str(t.get("ueid", "")),
                )
            self._set_status(f"{len(tasks)} task(s) loaded.")

        def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
            """Show task details when user highlights a row."""
            if event.row_key is None or event.row_key.value is None:
                return
            ueid = str(event.row_key.value)
            self.selected_ueid = ueid
            self._show_detail(ueid)

        def _show_detail(self, ueid: str) -> None:
            from src.contracts.common import UEID
            try:
                parsed = UEID(ueid)
            except ValueError:
                self.query_one("#detail", Static).update(f"Invalid UEID: {ueid}")
                return
            task = self.adapter.read(parsed)
            if task is None:
                self.query_one("#detail", Static).update(f"Task not found: {ueid}")
                return
            lines = [f"[bold cyan]{task.get('name', '')}[/bold cyan]", ""]
            for k, v in task.items():
                lines.append(f"  [dim]{k}:[/dim] {v}")
            self.query_one("#detail", Static).update("\n".join(lines))

        def _set_status(self, msg: str) -> None:
            self.query_one("#status", Static).update(msg)

        def action_add_task(self) -> None:
            """Add a new task via the TaskdogAdapter. Uses timestamp + random slug for UEID."""
            import uuid
            from datetime import datetime, UTC
            from src.contracts.common import UEID
            from src.contracts.task_change import TaskAction, PropagationEvent, TaskChange

            name = "New task " + datetime.now(UTC).strftime("%H%M%S")
            short_id = uuid.uuid4().hex[:16]
            slug = "new-task-" + short_id[:8]
            ueid_str = f"tsk:{slug}:{short_id[:8]}:{short_id[8:]}"
            try:
                parsed = UEID(ueid_str)
            except ValueError as e:
                self._set_status(f"[red]Invalid UEID: {e}[/red]")
                return

            event = TaskChange(
                event_id=f"tui-{short_id}",
                ueid=parsed,
                action=TaskAction.CREATE,
                fields={"title": name, "priority": "medium", "due": ""},
                source_fork="ikigai-taskdog-tui",
                timestamp=datetime.now(UTC).replace(tzinfo=None),
            )
            try:
                self.adapter.apply_change(event)
            except Exception as e:
                self._set_status(f"[red]Add failed: {e}[/red]")
                return
            self.refresh()
            self._set_status(f"[green]Added: {ueid_str}[/green]")

        def action_edit_status(self) -> None:
            """Mark the selected task as done (no full editor in v1)."""
            if self.selected_ueid is None:
                self._set_status("[red]No task selected[/red]")
                return
            from src.contracts.common import UEID
            try:
                parsed = UEID(self.selected_ueid)
            except ValueError:
                self._set_status("[red]Invalid UEID[/red]")
                return
            # v1 TaskdogAdapter only supports create. Simulate "done" status by
            # removing the row (re-insert with status='done' is no-op for v1).
            # Practical v1: just delete the row to mark done. Show user a hint.
            self._set_status(
                f"[yellow]v1 TaskdogAdapter only supports create. "
                f"To mark {self.selected_ueid} done, delete + re-add. "
                f"Press 'd' to delete.[/yellow]"
            )

        def action_delete_task(self) -> None:
            """Delete the selected task (raw SQL, since adapter only supports create)."""
            if self.selected_ueid is None:
                self._set_status("[red]No task selected[/red]")
                return
            from src.contracts.common import UEID
            try:
                parsed = UEID(self.selected_ueid)
            except ValueError:
                self._set_status("[red]Invalid UEID[/red]")
                return
            # Raw SQL delete (v1 adapter doesn't support delete; v2 will).
            from src.mesh.adapters.taskdog import TASKDOG_DB
            try:
                conn = sqlite3.connect(TASKDOG_DB)
                conn.execute("DELETE FROM tasks WHERE ueid = ?", (str(parsed),))
                conn.commit()
                conn.close()
            except Exception as e:
                self._set_status(f"[red]Delete failed: {e}[/red]")
                return
            self.refresh()
            self._set_status(f"[green]Deleted: {parsed}[/green]")

    TaskdogTui(adapter=TaskdogAdapter()).run()
    return 0
