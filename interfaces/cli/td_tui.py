"""M165 — Live taskdog TUI dashboard (Textual). 3 modes (Tab to cycle):
dashboard (counts+table+activity), timeline (one bar per task),
gantt (boxes + blocked_by arrows). Keys: q/r/tab/+/d/t//.
Replaces the one-shot Rich `cmd_tui` in src/mesh/taskdog_cli.py."""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Static

# -- Constants ------------------------------------------------------------

MODE_DASHBOARD, MODE_TIMELINE, MODE_GANTT = "dashboard", "timeline", "gantt"
MODES: tuple[str, ...] = (MODE_DASHBOARD, MODE_TIMELINE, MODE_GANTT)

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKDOG_DB = REPO_ROOT / "data" / "taskdog" / "tasks.db"
UPI_DB = REPO_ROOT / "data" / "solverforge_calendar" / "unified_planning.db"
REVIEW_QUEUE_DIR = REPO_ROOT / "data" / "review_queue"

KNOWN_STATUSES: tuple[str, ...] = ("planned", "in_progress", "done", "cancelled")
REFRESH_SECONDS: float = 5.0
MAX_ACTIVITY_ROWS: int = 10
MAX_TASKS_TABLE: int = 50

_TASKDOG_SCHEMA = ("CREATE TABLE IF NOT EXISTS tasks ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "ueid TEXT UNIQUE, name TEXT, status TEXT, priority INTEGER,"
    "planned_start TEXT, planned_end TEXT, deadline TEXT, created_at TEXT)")
_UPI_SCHEMA = ("CREATE TABLE IF NOT EXISTS unified_planning_items ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, ueid TEXT, status TEXT,"
    "start_at TEXT, end_at TEXT, blocked_by TEXT, tags TEXT,"
    "ikigai TEXT, provenance TEXT)")


# -- Data loaders (defensive) ---------------------------------------------


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {s: 0 for s in KNOWN_STATUSES}
    for r in rows:
        s = str(r.get("status") or "")
        counts[s] = counts.get(s, 0) + 1
    return counts


def _apply_filter(rows: list[dict[str, Any]], pattern: str | None) -> list[dict[str, Any]]:
    if not pattern:
        return rows
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error:
        return []
    return [
        r for r in rows
        if rx.search(str(r.get("name") or ""))
        or rx.search(str(r.get("status") or ""))
    ]


def _load_taskdog_rows(db_path: Path = TASKDOG_DB) -> list[dict[str, Any]]:
    """Read all task slices from taskdog SQLite + attach blocked_by (best-effort)."""
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.Error:
        return []
    rows: list[dict[str, Any]] = []
    try:
        conn.executescript(_TASKDOG_SCHEMA)
        cur = conn.execute(
            "SELECT ueid, name, status, priority, planned_start, "
            "planned_end, deadline, created_at FROM tasks"
        )
        rows = [
            {
                "ueid": r[0], "name": r[1], "status": r[2], "priority": r[3],
                "planned_start": r[4], "planned_end": r[5], "deadline": r[6],
                "created_at": r[7], "blocked_by": [],
            }
            for r in cur.fetchall()
        ]
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    if not rows or not UPI_DB.exists():
        return rows
    try:
        conn2 = sqlite3.connect(str(UPI_DB))
        try:
            conn2.executescript(_UPI_SCHEMA)
            blocked_map: dict[str, list[str]] = {}
            for ueid, blocked_by in conn2.execute(
                "SELECT ueid, blocked_by FROM unified_planning_items"
            ).fetchall():
                if not ueid:
                    continue
                parsed: list[str] = []
                if blocked_by:
                    try:
                        loaded = json.loads(blocked_by)
                        if isinstance(loaded, list):
                            parsed = [str(x) for x in loaded]
                    except (json.JSONDecodeError, TypeError):
                        parsed = []
                blocked_map[str(ueid)] = parsed
            for r in rows:
                r["blocked_by"] = blocked_map.get(r["ueid"], [])
        finally:
            conn2.close()
    except sqlite3.Error:
        pass
    return rows


def _load_activity_rows(
    queue_dir: Path = REVIEW_QUEUE_DIR, limit: int = MAX_ACTIVITY_ROWS
) -> list[dict[str, str]]:
    """Read most recent TaskChange events from data/review_queue/ (newest mtime first)."""
    if not queue_dir.is_dir():
        return []
    files = [f for f in queue_dir.glob("*.json") if f.is_file()]
    # Sort by mtime newest-first (pathlib's str compare gives wrong order for
    # uuid-named files like "ev-old" vs "ev-new").
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[dict[str, str]] = []
    for f in files[:limit]:
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        out.append(
            {
                "event_id": str(payload.get("event_id", f.stem)),
                "ueid": str(payload.get("ueid", "—")),
                "action": str(payload.get("action", "—")),
                "source_fork": str(payload.get("source_fork", "—")),
                "timestamp": str(payload.get("timestamp", "—")),
                "status": str(payload.get("status", "pending")),
            }
        )
    return out


def _spawn_subprocess(cmd: list[str]) -> int:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        print(f"[td_tui] subprocess not found: {exc}", file=sys.stderr)
        return 127
    if result.returncode != 0 and result.stderr:
        sys.stderr.write(result.stderr)
    return int(result.returncode)


def _mark_done(ueid: str) -> int:
    return _spawn_subprocess(
        [sys.executable, "-m", "src.mesh.taskdog_cli", "done", ueid]
    )


def _ts_to_epoch(ts: str) -> float:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except ValueError:
        try:
            return datetime.strptime(ts[:10], "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ).timestamp()
        except ValueError:
            raise ValueError(f"bad timestamp: {ts!r}")


def _clamp_index(ts: str, min_ts: str, max_ts: str, width: int) -> int:
    t = _ts_to_epoch(ts)
    lo, hi = _ts_to_epoch(min_ts), _ts_to_epoch(max_ts)
    total = hi - lo
    if total <= 0:
        return 0
    idx = int(((t - lo) / total) * (width - 1))
    return max(0, min(width - 1, idx))


# -- Screens --------------------------------------------------------------


class DashboardScreen(Screen[None]):
    BINDINGS = [
        Binding("d", "mark_done", "Done"),
        Binding("slash", "focus_filter", "Filter"),
    ]

    def __init__(self, app: "TaskdogTUI") -> None:
        super().__init__()
        self._app_ref = app

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="dash-root"):
            yield Static("", id="dash-header")
            yield Static("", id="dash-summary")
            yield DataTable(id="dash-table", zebra_stripes=True, cursor_type="row")
            yield Static("", id="dash-activity-title")
            yield Static("", id="dash-activity")
        yield Footer()

    def refresh_data(self) -> None:
        rows = self._app_ref.filtered_rows()
        counts = self._app_ref.last_counts()
        all_rows = self._app_ref.all_rows()
        try:
            header = self.query_one("#dash-header", Static)
            summary = self.query_one("#dash-summary", Static)
            table = self.query_one("#dash-table", DataTable)
            at = self.query_one("#dash-activity-title", Static)
            ab = self.query_one("#dash-activity", Static)
        except Exception:
            return

        c = counts
        header.update(
            f"[bold]taskdog dashboard[/bold]  ·  total=[green]{len(all_rows)}[/green]  ·  "
            f"planned=[cyan]{c.get('planned', 0)}[/cyan]  "
            f"in_progress=[yellow]{c.get('in_progress', 0)}[/yellow]  "
            f"done=[green]{c.get('done', 0)}[/green]  "
            f"cancelled=[dim]{c.get('cancelled', 0)}[/dim]"
        )
        flt = (
            f"  ·  filter=[magenta]{self._app_ref.filter_pattern}[/magenta]"
            if self._app_ref.filter_pattern
            else ""
        )
        summary.update(
            f"[dim]Showing {len(rows)} task(s) (max {MAX_TASKS_TABLE}){flt}[/dim]"
        )
        table.clear(columns=True)
        table.add_columns("UEID", "Name", "Status", "Priority", "Due")
        for r in rows[:MAX_TASKS_TABLE]:
            table.add_row(
                _truncate(str(r.get("ueid") or ""), 30),
                _truncate(str(r.get("name") or "(no name)"), 40),
                str(r.get("status") or ""),
                str(r.get("priority") or "—"),
                str(r.get("deadline") or "—"),
            )
        act = self._app_ref.last_activity()
        at.update(f"[bold]Recent activity[/bold]  ·  [dim]last {len(act)} event(s)[/dim]")
        if not act:
            ab.update("[dim](no events in data/review_queue/)[/dim]")
        else:
            ab.update(
                "\n".join(
                    f"  {a['timestamp'][-19:]}  [{a['status']}] {a['action']}  "
                    f"{_truncate(a['ueid'], 30)}"
                    for a in act
                )
            )

    def action_mark_done(self) -> None:
        try:
            table = self.query_one("#dash-table", DataTable)
        except Exception:
            return
        if table.row_count == 0:
            return
        cursor_row = table.cursor_row
        if cursor_row is None or cursor_row < 0:
            return
        try:
            row_key = table.coordinate_to_cell_key((cursor_row, 0)).row_key
            index = int(row_key.value)
        except Exception:
            return
        rows = self._app_ref.filtered_rows()
        if 0 <= index < len(rows):
            ueid = str(rows[index].get("ueid") or "")
            if ueid:
                _mark_done(ueid)

    def action_focus_filter(self) -> None:
        self._app_ref.push_screen(FilterModal(self._app_ref))


class TimelineScreen(Screen[None]):
    BINDINGS = [Binding("slash", "focus_filter", "Filter")]

    def __init__(self, app: "TaskdogTUI") -> None:
        super().__init__()
        self._app_ref = app

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="timeline-root"):
            yield Static("", id="timeline-header")
            yield Static("", id="timeline-body")
        yield Footer()

    def refresh_data(self) -> None:
        rows = self._app_ref.filtered_rows()
        try:
            header = self.query_one("#timeline-header", Static)
            body = self.query_one("#timeline-body", Static)
        except Exception:
            return

        header.update(
            f"[bold]timeline[/bold]  ·  [dim]{len(rows)} task(s) plotted by date[/dim]"
        )
        dated = [
            (
                str(r.get("planned_start") or ""),
                str(r.get("planned_end") or r.get("deadline") or ""),
                str(r.get("name") or "(no name)"),
                str(r.get("status") or ""),
            )
            for r in rows
        ]
        dated = [(s, e, n, st) for s, e, n, st in dated if s or e]
        if not dated:
            body.update("[dim](no tasks with planned_start or deadline)[/dim]")
            return
        starts = [d[0] for d in dated if d[0]]
        ends = [d[1] for d in dated if d[1]]
        if not starts or not ends:
            body.update("[dim](no datable tasks)[/dim]")
            return
        min_ts, max_ts = min(starts), max(ends)
        width_chars = 60
        lines = [
            f"window: {min_ts[:10]} → {max_ts[:10]}    (each █ ≈ one day slot)",
            "-" * (width_chars + 16),
        ]
        for start, end, name, status in dated[:MAX_TASKS_TABLE]:
            try:
                s_idx = _clamp_index(start, min_ts, max_ts, width_chars)
                e_idx = _clamp_index(end, min_ts, max_ts, width_chars)
            except ValueError:
                continue
            bar_width = max(1, e_idx - s_idx + 1)
            label = _truncate(name, 30)
            lines.append(f"{label:<32} | {'█' * bar_width:<{width_chars}} | {status}")
        if len(dated) > MAX_TASKS_TABLE:
            lines.append(f"[dim](+{len(dated) - MAX_TASKS_TABLE} more)[/dim]")
        body.update("\n".join(lines))

    def action_focus_filter(self) -> None:
        self._app_ref.push_screen(FilterModal(self._app_ref))


class GanttScreen(Screen[None]):
    BINDINGS = [Binding("slash", "focus_filter", "Filter")]

    def __init__(self, app: "TaskdogTUI") -> None:
        super().__init__()
        self._app_ref = app

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="gantt-root"):
            yield Static("", id="gantt-header")
            yield Static("", id="gantt-body")
        yield Footer()

    def refresh_data(self) -> None:
        rows = self._app_ref.filtered_rows()
        try:
            header = self.query_one("#gantt-header", Static)
            body = self.query_one("#gantt-body", Static)
        except Exception:
            return

        dependents: dict[str, list[str]] = {}
        for r in rows:
            for dep in r.get("blocked_by") or []:
                dependents.setdefault(dep, []).append(str(r.get("ueid") or ""))
        roots = [r for r in rows if not (r.get("blocked_by") or [])]
        with_deps = sum(1 for r in rows if r.get("blocked_by"))
        header.update(
            f"[bold]gantt / deps[/bold]  ·  [dim]{len(rows)} task(s), "
            f"{with_deps} with deps, {len(roots)} root(s)[/dim]"
        )

        lines: list[str] = []
        for r in rows[:MAX_TASKS_TABLE]:
            ueid = str(r.get("ueid") or "?")
            name = _truncate(str(r.get("name") or "(no name)"), 28)
            status = str(r.get("status") or "")
            deps = r.get("blocked_by") or []
            box = f"[{status or '—'}]  {name}"
            lines.append(f"┌─ {ueid:<24}  {box}")
            if deps:
                lines.append(
                    "│   depends on: "
                    + ", ".join(_truncate(d, 20) for d in deps)
                )
            children = dependents.get(ueid, [])
            if children:
                lines.append(
                    "│   blocks:     "
                    + ", ".join(_truncate(c, 20) for c in children)
                )
            lines.append("└" + "─" * 60)
        if not rows:
            lines.append("[dim](no tasks to render)[/dim]")
        elif len(rows) > MAX_TASKS_TABLE:
            lines.append(f"[dim](+{len(rows) - MAX_TASKS_TABLE} more)[/dim]")
        body.update("\n".join(lines))

    def action_focus_filter(self) -> None:
        self._app_ref.push_screen(FilterModal(self._app_ref))


class FilterModal(Screen[None]):
    BINDINGS = [
        Binding("escape", "dismiss_modal", "Cancel"),
        Binding("enter", "submit", "Apply"),
    ]

    def __init__(self, app: "TaskdogTUI") -> None:
        super().__init__()
        self._app_ref = app

    def compose(self) -> ComposeResult:
        with Vertical(id="filter-modal"):
            yield Static("[bold]Filter[/bold]  ·  regex on name or status")
            yield Input(value=self._app_ref.filter_pattern or "", id="filter-input")
            yield Static("[dim]Enter to apply, Escape to cancel[/dim]")

    def on_mount(self) -> None:
        self.query_one("#filter-input", Input).focus()

    def action_submit(self) -> None:
        self._app_ref.filter_pattern = self.query_one(
            "#filter-input", Input
        ).value.strip()
        self.dismiss(None)

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)


# -- App ------------------------------------------------------------------


class TaskdogTUI(App[None]):
    """Live taskdog dashboard — Textual app with 3 modes."""

    TITLE = "taskdog TUI"
    SUB_TITLE = "live dashboard"

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh_now", "Refresh"),
        Binding("tab", "cycle_mode", "Mode", priority=True),
        Binding("plus", "open_add", "Add"),
        Binding("d", "mark_done_global", "Done"),
        Binding("t", "open_tag", "Tag"),
        Binding("slash", "focus_filter", "Filter"),
    ]

    active_mode: reactive[str] = reactive(MODE_DASHBOARD)
    filter_pattern: reactive[str] = reactive("")

    def __init__(
        self,
        taskdog_db: Path | None = None,
        upi_db: Path | None = None,
        queue_dir: Path | None = None,
    ) -> None:
        super().__init__()
        self._taskdog_db = taskdog_db or TASKDOG_DB
        self._upi_db = upi_db or UPI_DB
        self._queue_dir = queue_dir or REVIEW_QUEUE_DIR
        self._all_rows: list[dict[str, Any]] = []
        self._counts: dict[str, int] = _status_counts([])
        self._activity: list[dict[str, str]] = []

    def all_rows(self) -> list[dict[str, Any]]:
        return list(self._all_rows)

    def filtered_rows(self) -> list[dict[str, Any]]:
        return _apply_filter(self._all_rows, self.filter_pattern)

    def last_counts(self) -> dict[str, int]:
        return dict(self._counts)

    def last_activity(self) -> list[dict[str, str]]:
        return list(self._activity)

    def compose(self) -> ComposeResult:
        yield Container(id="screen-host")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_data()
        self._show_mode(self.active_mode)
        self.set_interval(REFRESH_SECONDS, self.refresh_data)

    def refresh_data(self) -> None:
        """Reload taskdog rows + activity. Cheap; runs on the main thread."""
        self._all_rows = _load_taskdog_rows(self._taskdog_db)
        self._counts = _status_counts(self._all_rows)
        self._activity = _load_activity_rows(self._queue_dir)
        screen = self.screen
        if hasattr(screen, "refresh_data"):
            try:
                screen.refresh_data()
            except Exception:
                pass

    def _show_mode(self, mode: str) -> None:
        try:
            host = self.query_one("#screen-host", Container)
            host.remove_children()
        except Exception:
            pass
        screen_cls: type[Screen[None]]
        if mode == MODE_TIMELINE:
            screen_cls = TimelineScreen
        elif mode == MODE_GANTT:
            screen_cls = GanttScreen
        else:
            screen_cls = DashboardScreen
        self.push_screen(screen_cls(self))

    def action_cycle_mode(self) -> None:
        idx = MODES.index(self.active_mode) if self.active_mode in MODES else 0
        self.active_mode = MODES[(idx + 1) % len(MODES)]
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self._show_mode(self.active_mode)

    def action_refresh_now(self) -> None:
        self.refresh_data()

    def action_open_add(self) -> None:
        _spawn_subprocess(
            [sys.executable, "-m", "src.mesh.taskdog_cli", "add", "--help"]
        )

    def action_open_tag(self) -> None:
        _spawn_subprocess(
            [sys.executable, "-m", "src.mesh.taskdog_cli", "update", "--help"]
        )

    def action_mark_done_global(self) -> None:
        screen = self.screen
        if hasattr(screen, "action_mark_done"):
            try:
                screen.action_mark_done()
            except Exception:
                pass

    def action_focus_filter(self) -> None:
        self.push_screen(FilterModal(self))


def main(argv: list[str] | None = None) -> int:
    """Run the live TUI. Returns 0 on clean exit, non-zero on bootstrap err."""
    app = TaskdogTUI()
    try:
        app.run()
    except Exception as exc:  # noqa: BLE001
        print(f"[td_tui] failed to start: {exc}", file=sys.stderr)
        return 1
    return 0


__all__ = [
    "TaskdogTUI",
    "DashboardScreen",
    "TimelineScreen",
    "GanttScreen",
    "FilterModal",
    "MODES",
    "main",
    "_load_taskdog_rows",
    "_load_activity_rows",
    "_apply_filter",
]