"""Server management sub-app — `life server {ls,inspect,status,start,stop}`.

This is the operator-facing CLI for inspecting and managing the IKIGAI backend
topology. It exposes:
  - `ls`: list all fork adapters (cli, taskdog, solverforge_calendar, a2ui)
  - `inspect <name>`: detailed view of one adapter
  - `status`: backend process status (queue worker, agent consumer, MCP gateway)
  - `start/stop <name>`: placeholder for B4-B5 wiring

Registered as a Typer sub-app of the main `app` in `interfaces.cli.read_tasks`.

Design notes:
  - All adapter storage paths are sourced from the adapter modules themselves
    (TASKS_JSONL, TASKDOG_DB, UPI_DB) so the registry stays in sync if those
    constants change.
  - a2ui has no storage path (spec-only per user decision 2026-08-28); its
    metadata points to the spec doc.
  - start/stop are stubs that print a clear "not yet implemented" message
    so users can probe the surface today. Real wiring lands in B4 (queue
    worker) and B5 (agent consumer/propagator).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from src.mesh.adapters import CliAdapter, TaskdogAdapter
from src.mesh.adapters.cli import TASKS_JSONL
from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter, UPI_DB
from src.mesh.adapters.taskdog import TASKDOG_DB

# === Registry ===

@dataclass(frozen=True)
class AdapterInfo:
    """Metadata for one fork adapter in the IKIGAI mesh topology."""
    name: str
    slice_type: str  # "jsonl" | "sqlite" | "spec-only"
    storage_path: Path | None  # None when slice_type is "spec-only"
    spec_ref: str | None = None  # Path to design spec (for spec-only slices)

    def exists(self) -> bool:
        """Whether the storage backing this adapter is reachable on disk."""
        if self.storage_path is None:
            return True  # spec-only is always "available"
        return self.storage_path.exists()


ADAPTER_REGISTRY: dict[str, AdapterInfo] = {
    "cli": AdapterInfo(
        name="cli",
        slice_type="jsonl",
        storage_path=TASKS_JSONL,
    ),
    "taskdog": AdapterInfo(
        name="taskdog",
        slice_type="sqlite",
        storage_path=TASKDOG_DB,
    ),
    "solverforge_calendar": AdapterInfo(
        name="solverforge_calendar",
        slice_type="sqlite",
        storage_path=UPI_DB,
    ),
    "a2ui": AdapterInfo(
        name="a2ui",
        slice_type="spec-only",
        storage_path=None,
        spec_ref="docs/superpowers/specs/2026-08-28-a2ui-protocol-design.md",
    ),
}


def list_adapters() -> list[AdapterInfo]:
    """Return all registered adapters in stable order."""
    return [ADAPTER_REGISTRY[name] for name in sorted(ADAPTER_REGISTRY)]


def get_adapter(name: str) -> AdapterInfo:
    """Return adapter by name. Raises KeyError if not registered."""
    if name not in ADAPTER_REGISTRY:
        available = ", ".join(sorted(ADAPTER_REGISTRY))
        raise KeyError(f"Unknown adapter {name!r}. Available: {available}")
    return ADAPTER_REGISTRY[name]


# === Backend process registry ===

# Backend processes that B4-B5 will populate with real status. Each entry
# is a dict the future status-checker fills in (pid, started_at, etc.).
BACKEND_PROCESSES: dict[str, dict[str, Any]] = {
    "review_queue_worker": {
        "phase": "B4",
        "description": "Consumes data/review_queue/<id>.json events",
    },
    "agent_consumer": {
        "phase": "B5",
        "description": "Validates TaskChange (PAE: APPROVE/REJECT/CLARIFY)",
    },
    "agent_propagator": {
        "phase": "B5",
        "description": "Emits PropagationEvents to all fork adapters",
    },
    "mcp_gateway": {
        "phase": "B3",
        "description": "8+2 tools IPC server (src/ikigai/src/mcp_server/server.py)",
    },
}


def backend_status() -> list[dict[str, Any]]:
    """Return status snapshot for all backend processes.

    v1 shape (B2): every process reports `running=false` because the actual
    supervisor lands in B4-B5. Fields are stable so future code can populate
    `pid`, `started_at`, `last_heartbeat` without changing consumers.
    """
    return [
        {
            "name": name,
            "phase": meta["phase"],
            "description": meta["description"],
            "running": False,
            "pid": None,
            "started_at": None,
        }
        for name, meta in BACKEND_PROCESSES.items()
    ]


# === Typer sub-app ===

server_app = typer.Typer(help="Server management: ls, inspect, status, start, stop")
console = Console()


@server_app.command("ls")
def ls(
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """List all registered fork adapters."""
    adapters = list_adapters()

    if json_output:
        rows = [
            {
                "name": a.name,
                "slice_type": a.slice_type,
                "storage_path": str(a.storage_path) if a.storage_path else None,
                "exists": a.exists(),
                "spec_ref": a.spec_ref,
            }
            for a in adapters
        ]
        console.print_json(__import__("json").dumps(rows))
        return

    table = Table(title="Fork Adapters")
    table.add_column("Name", style="cyan", width=22)
    table.add_column("Slice Type", style="magenta", width=10)
    table.add_column("Exists", style="green", width=7)
    table.add_column("Storage Path", style="dim")

    for a in adapters:
        exists_mark = "✅" if a.exists() else "❌"
        path_str = str(a.storage_path) if a.storage_path else f"[dim]{a.spec_ref}[/dim]"
        table.add_row(a.name, a.slice_type, exists_mark, path_str)

    console.print(table)


@server_app.command("inspect")
def inspect(
    name: str = typer.Argument(..., help="Adapter name (cli, taskdog, solverforge_calendar, a2ui)"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Show detailed view of one adapter."""
    try:
        info = get_adapter(name)
    except KeyError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    payload = asdict(info)
    payload["exists"] = info.exists()
    payload["storage_path"] = str(info.storage_path) if info.storage_path else None

    if json_output:
        console.print_json(__import__("json").dumps(payload))
        return

    # Pretty render
    console.print(f"[bold cyan]Adapter:[/bold cyan] {info.name}")
    console.print(f"[bold]Slice type:[/bold] {info.slice_type}")
    if info.storage_path:
        console.print(f"[bold]Storage path:[/bold] {info.storage_path}")
        console.print(f"[bold]Exists:[/bold] {'✅ yes' if info.exists() else '❌ no'}")
    else:
        console.print(f"[bold]Spec ref:[/bold] {info.spec_ref}")
    console.print(f"[dim]Available fields: see {info.name} adapter's SUPPORTED_FIELDS[/dim]")


@server_app.command("status")
def status(
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Show backend process status (B4-B5 deliverable; v1 reports all stopped)."""
    snapshot = backend_status()

    if json_output:
        console.print_json(__import__("json").dumps(snapshot))
        return

    table = Table(title="Backend Processes")
    table.add_column("Name", style="cyan", width=24)
    table.add_column("Phase", style="magenta", width=5)
    table.add_column("Running", style="green", width=9)
    table.add_column("Description", style="dim")

    for row in snapshot:
        running_mark = "✅" if row["running"] else "⏸"
        table.add_row(row["name"], row["phase"], running_mark, row["description"])

    console.print(table)
    console.print("\n[dim]All processes report running=false (B2 stub). Real wiring in B4-B5.[/dim]")


@server_app.command("start")
def start(
    name: str = typer.Argument(..., help="Backend process name (review_queue_worker, agent_consumer, agent_propagator, mcp_gateway)"),
) -> None:
    """Start a backend process. STUB — wires up in B4 (queue worker) and B5 (agent)."""
    if name not in BACKEND_PROCESSES:
        available = ", ".join(sorted(BACKEND_PROCESSES))
        console.print(f"[red]Unknown process {name!r}. Available: {available}[/red]")
        raise typer.Exit(1)

    phase = BACKEND_PROCESSES[name]["phase"]
    console.print(
        f"[yellow]STUB:[/yellow] start {name} not implemented yet. "
        f"Delivers in phase {phase} per docs/superpowers/plans/2026-08-28-backend-phase-reordering.md."
    )


@server_app.command("stop")
def stop(
    name: str = typer.Argument(..., help="Backend process name"),
) -> None:
    """Stop a backend process. STUB — wires up in B4 (queue worker) and B5 (agent)."""
    if name not in BACKEND_PROCESSES:
        available = ", ".join(sorted(BACKEND_PROCESSES))
        console.print(f"[red]Unknown process {name!r}. Available: {available}[/red]")
        raise typer.Exit(1)

    phase = BACKEND_PROCESSES[name]["phase"]
    console.print(
        f"[yellow]STUB:[/yellow] stop {name} not implemented yet. "
        f"Delivers in phase {phase}."
    )


__all__ = [
    "AdapterInfo",
    "ADAPTER_REGISTRY",
    "BACKEND_PROCESSES",
    "list_adapters",
    "get_adapter",
    "backend_status",
    "server_app",
]