"""Interface CLI — reads structured tasks from data/tasks.jsonl and renders them.

This is a pure consumer: reads only, never writes to the vault.
User marks tasks done, and the CLI writes feedback to data/feedback.jsonl.

Usage:
    python read_tasks.py                    # today's tasks
    python read_tasks.py --horizon this_week
    python read_tasks.py --done False      # pending only
    python read_tasks.py --json            # machine-readable
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Read and manage tasks from data/tasks.jsonl")
console = Console()


def _tasks_path() -> Path:
    repo_root = Path(__file__).parent.parent.parent  # interfaces/cli/ → life/
    return repo_root / "data" / "tasks.jsonl"


def _feedback_path() -> Path:
    repo_root = Path(__file__).parent.parent.parent
    return repo_root / "data" / "feedback.jsonl"


def _read_tasks(
    horizon: str | None = None,
    done: bool | None = None,
) -> list[dict]:
    path = _tasks_path()
    if not path.exists():
        return []

    results = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    task = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if horizon is not None and task.get("horizon") != horizon:
                    continue
                if done is not None and task.get("done") != done:
                    continue
                results.append(task)
    except OSError:
        return []
    return results


@app.command()
def list(
    horizon: str | None = typer.Option(None, "--horizon", "-h",
                                         help="Filter by horizon (today, this_week, onda, sprint, etc.)"),
    done: bool | None = typer.Option(None, "--done", "-d",
                                      help="Filter by done status"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max tasks to show"),
) -> None:
    """List tasks from data/tasks.jsonl."""
    tasks = _read_tasks(horizon=horizon, done=done)

    if json_output:
        console.print_json(json.dumps(tasks[:limit]))
        return

    if not tasks:
        console.print("[dim]No tasks found.[/dim]")
        return

    table = Table(title=f"Tasks — {horizon or 'all horizons'}")
    table.add_column("Done", style="green", width=5)
    table.add_column("Title", style="white")
    table.add_column("Horizon", style="cyan", width=12)
    table.add_column("Priority", style="yellow", width=9)
    table.add_column("Project", style="magenta", width=20)

    for t in tasks[:limit]:
        mark = "✅" if t.get("done") else "⬜"
        title = t.get("title", "?")[:50]
        hzn = t.get("horizon", "?")
        prio = t.get("priority", "medium")
        proj = t.get("project_id", "")[:20] or "-"
        table.add_row(mark, title, hzn, prio, proj)

    console.print(table)
    console.print(f"\n[dim]{len(tasks)} total[/dim]")


@app.command()
def done(
    task_id: str = typer.Argument(..., help="Task ID (first 8 chars of the record uuid)"),
) -> None:
    """Mark a task as done and append feedback to data/feedback.jsonl."""
    path = _tasks_path()
    if not path.exists():
        console.print("[red]No tasks found.[/red]")
        raise typer.Exit(1)

    # Find and update the task
    updated_lines: list[str] = []
    found = False
    today = date.today().isoformat()

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                task = json.loads(line)
            except json.JSONDecodeError:
                updated_lines.append(line)
                continue
            if task.get("id", "")[:8] == task_id:
                task["done"] = True
                task["done_at"] = today
                found = True
            updated_lines.append(json.dumps(task, ensure_ascii=False))

    if not found:
        console.print(f"[red]Task {task_id} not found.[/red]")
        raise typer.Exit(1)

    path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")

    # Append to feedback
    fb_path = _feedback_path()
    fb_path.parent.mkdir(parents=True, exist_ok=True)
    feedback = {
        "id": task_id,
        "action": "done",
        "date": today,
        "source": "interface_cli",
    }
    with fb_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(feedback, ensure_ascii=False) + "\n")

    console.print(f"[green]✅ Task {task_id} marked done.[/green]")


@app.command()
def stats() -> None:
    """Show task statistics from data/tasks.jsonl."""
    path = _tasks_path()
    if not path.exists():
        console.print("[dim]No tasks yet.[/dim]")
        return

    total = 0
    done_count = 0
    by_horizon: dict[str, int] = {}
    by_priority: dict[str, int] = {}

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                task = json.loads(line)
            except json.JSONDecodeError:
                continue
            total += 1
            if task.get("done"):
                done_count += 1
            hzn = task.get("horizon", "?")
            prio = task.get("priority", "?")
            by_horizon[hzn] = by_horizon.get(hzn, 0) + 1
            by_priority[prio] = by_priority.get(prio, 0) + 1

    table = Table(title="Task Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Total tasks", str(total))
    table.add_row("Done", str(done_count))
    table.add_row("Pending", str(total - done_count))
    table.add_row("Completion %", f"{done_count/max(total,1)*100:.0f}%")
    console.print(table)

    console.print("\n[bold]By Horizon:[/bold]")
    for h, c in sorted(by_horizon.items()):
        console.print(f"  {h:12s}: {c}")

    console.print("\n[bold]By Priority:[/bold]")
    for p, c in sorted(by_priority.items()):
        console.print(f"  {p:12s}: {c}")


# === Phase 3: mesh show + task_add commands ===

import uuid as uuid_lib
import re
from datetime import datetime, timezone

from src.contracts.common import UEID
from src.contracts.task_change import TaskChange, PropagationEvent, TaskAction
from src.mesh.adapters.cli import CliAdapter
from src.mesh.adapters.taskdog import TaskdogAdapter
from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter
from src.mesh import queue


def show_mesh(ueid: str) -> dict:
    """Show cross-fork view for one UEID. Returns status matrix + slices."""
    parsed_ueid = UEID(ueid)  # validates format

    adapters = {
        "cli": CliAdapter(),
        "taskdog": TaskdogAdapter(),
        "solverforge_calendar": SolverforgeCalendarAdapter(),
    }

    view = {}
    for name, adapter in adapters.items():
        try:
            view[name] = adapter.read(parsed_ueid)
        except Exception as e:
            view[name] = {"error": str(e)}

    # Detect mismatches
    statuses = [v.get("status") for v in view.values() if isinstance(v, dict) and "status" in v]
    mismatches = []
    if len(set(statuses)) > 1:
        mismatches.append(f"Status differs across forks: {statuses}")

    return {"ueid": str(parsed_ueid), "view": view, "mismatches": mismatches}


@app.command()
def mesh_show(ueid: str):
    """Show cross-fork view for one UEID."""
    result = show_mesh(ueid)
    console.print_json(json.dumps(result, default=str))


def _slugify(title: str, max_len: int = 50) -> str:
    """Sanitize a title into a UEID slug segment.

    UEID regex requires [a-z0-9-]+ in the slug segment. We:
      - lowercase
      - collapse any non-allowed run into a single hyphen
      - strip edge hyphens
      - truncate to max_len
      - fall back to "task" if title was entirely non-allowed (e.g. !!!)
    """
    slug = re.sub(r"[^a-z0-9-]+", "-", title.lower()).strip("-")[:max_len]
    return slug or "task"


def generate_ueid(title: str) -> UEID:
    """Generate 5-part UEID from a title: tsk:<sanitized-slug>:uuid:hash.

    Defense-in-depth: sanitizes the title internally so callers don't have to.
    """
    slug = _slugify(title)
    short_uuid = str(uuid_lib.uuid4())
    short_hash = uuid_lib.uuid4().hex[:16]
    return UEID(f"tsk:{slug}:{short_uuid}:{short_hash}")


def do_task_add(title: str, due: str | None, priority: str) -> dict:
    """Add a new task — writes to interfaces/cli slice + emits to review queue.

    Returns a dict describing the new task (ueid, event_id, status, message).
    Separated from the Typer command so tests can call it without going
    through Click/Typer's option-resolution path (which wraps defaults in
    OptionInfo objects in Typer 0.25+).
    """
    ueid = generate_ueid(title)

    # 1. Write to interfaces/cli slice
    cli_adapter = CliAdapter()
    event = TaskChange(
        event_id=f"evt_{uuid_lib.uuid4().hex[:12]}",
        ueid=ueid,
        action=TaskAction.CREATE,
        fields={"title": title, "due": due, "priority": priority},
        source_fork="interfaces/cli",
        timestamp=datetime.now(timezone.utc),
    )
    cli_adapter.apply_change(PropagationEvent(
        event_id=event.event_id,
        ueid=event.ueid,
        action=event.action,
        fields=event.fields,
        approved_at=event.timestamp,
        source_fork=event.source_fork,
    ))

    # 2. Emit event to review queue
    queue.enqueue(event)

    return {
        "ueid": str(ueid),
        "event_id": event.event_id,
        "status": "pending",
        "message": "Task added to interfaces/cli; awaiting agent review for propagation to other forks.",
    }


@app.command()
def task_add(
    title: str = typer.Option(..., "--title", "-t", help="Task title"),
    due: str = typer.Option(None, "--due", "-d", help="Due date YYYY-MM-DD"),
    priority: str = typer.Option("medium", "--priority", "-p", help="high/medium/low"),
):
    """Add a new task. Writes to interfaces/cli slice + emits to review queue."""
    result = do_task_add(title=title, due=due, priority=priority)
    console.print_json(json.dumps(result, default=str))


# === Phase B5: `plan add/list` — thin wrappers for the Marco demo ===
#
# These wrap the existing `do_task_add` and `show_mesh` so the user can drive
# the create + cross-fork-read cycle from a single command pair.
#
# No new business logic; pure delegation.
# Zero policy engine / QHE / scoring imports (per user 2026-08-29 constraint).

@app.command(name="plan-add")
def plan_add(
    title: str = typer.Argument(..., help="Task title"),
    due: str = typer.Argument(None, help="Due date YYYY-MM-DD"),
    priority: str = typer.Option("medium", "--priority", "-p", help="high/medium/low"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Add a new task via the mesh create cycle (positional args).

    Writes to interfaces/cli slice + emits TaskChange to review_queue/.
    The worker drains the queue and propagates to other forks.
    """
    result = do_task_add(title=title, due=due, priority=priority)
    if json_out:
        console.print_json(json.dumps(result, default=str))
    else:
        console.print(f"[green]ueid:[/green] {result['ueid']}")
        console.print(f"[green]event_id:[/green] {result['event_id']}")
        console.print(f"[green]status:[/green] {result['status']}")
        console.print(f"[dim]{result['message']}[/dim]")


@app.command(name="plan-list")
def plan_list(
    all_forks: bool = typer.Option(
        False,
        "--all-forks",
        "-a",
        help="Join each row with mesh_show for cross-fork view",
    ),
    json_out: bool = typer.Option(False, "--json"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max tasks to show"),
) -> None:
    """List tasks from data/tasks.jsonl (CLI fork).

    With `--all-forks`, joins each row with show_mesh so you can see what
    the other adapters (taskdog, solverforge_calendar) actually received.
    """
    path = _tasks_path()
    if not path.exists():
        if json_out:
            console.print_json(json.dumps({"tasks": []}))
        else:
            console.print("[dim]No tasks found.[/dim]")
        return

    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if all_forks:
        # Mesh join — proves the sync cycle read path
        joined: list[dict] = []
        for row in rows[:limit]:
            ueid = row.get("ueid")
            if not ueid:
                continue
            mesh = show_mesh(ueid)
            row_out = dict(row)
            row_out["_mesh"] = mesh
            joined.append(row_out)
        if json_out:
            console.print_json(json.dumps(joined, default=str))
        else:
            table = Table(title=f"Plan (all-forks) — {len(joined)} tasks")
            table.add_column("UEID", style="cyan")
            table.add_column("Title", style="white")
            table.add_column("CLI", style="green", width=5)
            table.add_column("Taskdog", style="green", width=8)
            table.add_column("Solverforge", style="green", width=12)
            for r in joined:
                mesh_view = r.get("_mesh", {}).get("view", {})
                cli_ok = "OK" if mesh_view.get("cli") else "-"
                td_ok = "OK" if mesh_view.get("taskdog") else "-"
                sf_ok = "OK" if mesh_view.get("solverforge_calendar") else "-"
                table.add_row(
                    str(r.get("ueid", "?"))[:36],
                    (r.get("title", "?") or "?")[:40],
                    cli_ok,
                    td_ok,
                    sf_ok,
                )
            console.print(table)
            mismatches_flat = [
                m
                for j in joined
                for m in j.get("_mesh", {}).get("mismatches", [])
            ]
            if mismatches_flat:
                console.print("\n[yellow]Mismatches detected:[/yellow]")
                for m in mismatches_flat:
                    console.print(f"  - {m}")
        return

    # Default view: CLI fork only
    if json_out:
        console.print_json(json.dumps(rows[:limit], default=str))
        return

    table = Table(title=f"Plan — {len(rows)} tasks")
    table.add_column("UEID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Due", style="yellow", width=12)
    table.add_column("Priority", style="magenta", width=8)
    for r in rows[:limit]:
        table.add_row(
            str(r.get("ueid", "?"))[:36],
            (r.get("title", "?") or "?")[:50],
            str(r.get("due", "-") or "-"),
            str(r.get("priority", "medium") or "medium"),
        )
    console.print(table)


if __name__ == "__main__":
    app()
