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

import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from src.mesh.adapters.cli import TASKS_JSONL
from src.mesh.adapters.solverforge_calendar import UPI_DB
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

# Path to pidfile that the (future) gateway-start command will write.
# For B3.4 we only READ this; gateway-start lands in a later phase.
MCP_GATEWAY_PIDFILE = (
    Path(__file__).parent.parent.parent / "data" / "run" / "mcp_gateway.pid"
)
REVIEW_QUEUE_WORKER_PIDFILE = (
    Path(__file__).parent.parent.parent / "data" / "run" / "review_queue_worker.pid"
)

# Backend processes that B4-B5 will populate with real status. Each entry
# is a dict the future status-checker fills in (pid, started_at, etc.).
BACKEND_PROCESSES: dict[str, dict[str, Any]] = {
    "review_queue_worker": {
        "phase": "B4",
        "description": "Consumes data/review_queue/<id>.json events",
        "pidfile_path": REVIEW_QUEUE_WORKER_PIDFILE,
    },
    "agent_consumer": {
        "phase": "B5",
        "description": "Validates TaskChange (PAE: APPROVE/REJECT/CLARIFY) — runs inside review_queue_worker, not a separate process",
    },
    "agent_propagator": {
        "phase": "B5",
        "description": "Emits PropagationEvents to all fork adapters — runs inside review_queue_worker, not a separate process",
    },
    "mcp_gateway": {
        "phase": "B3",
        "description": "13 tools + 6 resources MCP gateway (B3.1-B3.3)",
        "pidfile_path": MCP_GATEWAY_PIDFILE,
    },
}

# === B2: subprocess management ===
# Per-process subprocess command (argv list). agent_consumer + agent_propagator
# are intentionally NOT here — they are functions called by review_queue_worker
# and have no standalone entrypoint.
#
# PYTHONPATH=. is set so `python -m src.<...>` resolves from repo root regardless
# of the cwd from which `life server start` was invoked.
START_COMMANDS: dict[str, list[str]] = {
    "mcp_gateway": [sys.executable, "-m", "src.ikigai.src.mcp_server"],
    "review_queue_worker": [
        sys.executable,
        "-m",
        "src.mesh.review_queue_worker",
        "start",
    ],
}

LOG_DIR = Path(__file__).parent.parent.parent / "data" / "run" / "logs"


def _pid_alive(pid: int) -> bool:
    """Cross-platform liveness check. Delegates to gateway_probe to keep one impl."""
    from interfaces.cli.mcp_gateway_probe import _is_pid_alive

    return _is_pid_alive(pid)


def _read_pidfile(pidfile_path: Path) -> int | None:
    """Read PID from pidfile. Returns None if missing or invalid."""
    if not pidfile_path.exists():
        return None
    try:
        return int(pidfile_path.read_text().strip())
    except (ValueError, OSError):
        return None


def _start_process(name: str, cmd: list[str], pidfile_path: Path) -> tuple[bool, str]:
    """Spawn cmd as detached subprocess, write pidfile, return (ok, message).

    Refuses to start if pidfile exists AND PID is alive (already-running).
    Cleans up stale pidfile (PID dead) before spawning.

    Returns (False, "already running with PID=N") when refused.
    Returns (False, "process exited within Ns after spawn") when spawn dies fast.
    Returns (True, "started with PID=N") on success.
    """
    pidfile_path.parent.mkdir(parents=True, exist_ok=True)

    # Check for already-running
    existing = _read_pidfile(pidfile_path)
    if existing is not None and _pid_alive(existing):
        return False, f"already running with PID={existing} (pidfile={pidfile_path})"

    # Stale pidfile from a previous crash: remove before spawning
    if pidfile_path.exists():
        pidfile_path.unlink(missing_ok=True)

    # Log files for stdout/stderr (operator can tail for debugging)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stdout_log = LOG_DIR / f"{name}.stdout.log"
    stderr_log = LOG_DIR / f"{name}.stderr.log"

    env = os.environ.copy()
    # Ensure subprocess can resolve `src.<...>` absolute imports
    env.setdefault("PYTHONPATH", str(Path(__file__).parent.parent.parent))

    proc = subprocess.Popen(  # noqa: S603 — controlled command list
        cmd,
        env=env,
        stdout=stdout_log.open("ab"),
        stderr=stderr_log.open("ab"),
        stdin=subprocess.DEVNULL,
        # New process group on POSIX so we can SIGTERM the whole tree later.
        # On Windows, CREATE_NEW_PROCESS_GROUP = 0x00000200.
        creationflags=0x00000200 if os.name == "nt" else 0,
        start_new_session=os.name != "nt",
    )

    pidfile_path.write_text(str(proc.pid))

    # Brief liveness probe — give the subprocess ~500ms to crash on import errors
    time.sleep(0.5)
    if proc.poll() is not None:
        # Died immediately
        pidfile_path.unlink(missing_ok=True)
        return (
            False,
            f"process exited within 0.5s of spawn (exit={proc.returncode}; see {stderr_log})",
        )

    if not _pid_alive(proc.pid):
        pidfile_path.unlink(missing_ok=True)
        return False, f"process PID={proc.pid} not alive after spawn (see {stderr_log})"

    return True, f"started with PID={proc.pid} (log={stdout_log})"


def _stop_process(name: str, pidfile_path: Path) -> tuple[bool, str]:
    """Read pidfile, kill PID (cross-platform), remove pidfile. Idempotent.

    Returns (killed, message):
      killed=True  → process was alive, we killed it
      killed=False → no-op (pidfile missing OR PID already dead)
    """
    pid = _read_pidfile(pidfile_path)
    if pid is None:
        return False, "no pidfile (nothing to stop)"

    if not _pid_alive(pid):
        # Stale pidfile — clean up and report no-op
        pidfile_path.unlink(missing_ok=True)
        return False, f"pidfile stale (PID={pid} not alive); cleaned up"

    # Cross-platform kill
    try:
        if os.name == "nt":
            # Windows: SIGTERM not always available; use TerminateProcess via taskkill
            # /T = kill process tree, /F = force. Force is the only reliable way
            # when the subprocess uses CREATE_NEW_PROCESS_GROUP.
            subprocess.run(  # noqa: S603 — controlled invocation
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                check=False,
                capture_output=True,
            )
        else:
            import signal

            os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        return False, f"kill failed for PID={pid}: {exc}"

    pidfile_path.unlink(missing_ok=True)
    return True, f"killed PID={pid}"


def backend_status() -> list[dict[str, Any]]:
    """Return status snapshot for all backend processes.

    For mcp_gateway (B3.4) and review_queue_worker (B4.2): reads pidfile +
    checks PID alive. Other 2 processes still report running=False (their
    wiring lands in B5).
    """
    from interfaces.cli.mcp_gateway_probe import probe_mcp_gateway
    from src.mesh.review_queue_worker import worker_status

    rows = []
    for name, meta in BACKEND_PROCESSES.items():
        row = {
            "name": name,
            "phase": meta["phase"],
            "description": meta["description"],
            "running": False,
            "pid": None,
            "started_at": None,
        }
        pidfile = meta.get("pidfile_path")
        if pidfile is not None:
            if name == "mcp_gateway":
                probe = probe_mcp_gateway(pidfile_path=pidfile)
            elif name == "review_queue_worker":
                probe = worker_status(pidfile)
            else:
                probe = None
            if probe is not None:
                row["running"] = probe["running"]
                row["pid"] = probe["pid"]
                row["started_at"] = probe["started_at"]
        rows.append(row)
    return rows


# === Typer sub-app ===

server_app = typer.Typer(help="Server management: ls, inspect, status, start, stop")
console = Console()


@server_app.command("ls")
def ls(
    json_output: bool = typer.Option(
        False, "--json", help="Machine-readable JSON output"
    ),
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
    name: str = typer.Argument(
        ..., help="Adapter name (cli, taskdog, solverforge_calendar, a2ui)"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Machine-readable JSON output"
    ),
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
    console.print(
        f"[dim]Available fields: see {info.name} adapter's SUPPORTED_FIELDS[/dim]"
    )


@server_app.command("status")
def status(
    json_output: bool = typer.Option(
        False, "--json", help="Machine-readable JSON output"
    ),
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
    console.print(
        "\n[dim]All processes report running=false (B2 stub). Real wiring in B4-B5.[/dim]"
    )


@server_app.command("start")
def start(
    name: str = typer.Argument(
        ..., help="Backend process name (review_queue_worker, mcp_gateway)"
    ),
) -> None:
    """Start a backend process as a detached subprocess.

    Real wiring (B2). agent_consumer + agent_propagator are NOT separate
    processes — they run inside review_queue_worker. Use --reason to inspect.
    """
    if name not in BACKEND_PROCESSES:
        available = ", ".join(sorted(BACKEND_PROCESSES))
        console.print(f"[red]Unknown process {name!r}. Available: {available}[/red]")
        raise typer.Exit(1)

    # agent_consumer / agent_propagator are functions inside the worker, not processes
    if name not in START_COMMANDS:
        console.print(
            f"[yellow]Not a standalone process:[/yellow] {name} runs inside review_queue_worker. "
            f"Start that instead with: [cyan]life server start review_queue_worker[/cyan]"
        )
        raise typer.Exit(0)

    pidfile_path = BACKEND_PROCESSES[name]["pidfile_path"]
    cmd = START_COMMANDS[name]

    ok, msg = _start_process(name, cmd, pidfile_path)
    if ok:
        console.print(f"[green]✓[/green] {name}: {msg}")
    else:
        console.print(f"[red]✗[/red] {name}: {msg}")
        raise typer.Exit(1)


@server_app.command("stop")
def stop(
    name: str = typer.Argument(..., help="Backend process name"),
) -> None:
    """Stop a backend process (kill PID from pidfile, remove pidfile). Idempotent."""
    if name not in BACKEND_PROCESSES:
        available = ", ".join(sorted(BACKEND_PROCESSES))
        console.print(f"[red]Unknown process {name!r}. Available: {available}[/red]")
        raise typer.Exit(1)

    # agent_consumer / agent_propagator have no pidfile — they're functions, not processes
    pidfile_path = BACKEND_PROCESSES[name].get("pidfile_path")
    if pidfile_path is None:
        console.print(
            f"[yellow]Not a standalone process:[/yellow] {name} runs inside review_queue_worker. "
            f"Stop that instead with: [cyan]life server stop review_queue_worker[/cyan]"
        )
        raise typer.Exit(0)

    killed, msg = _stop_process(name, pidfile_path)
    if killed:
        console.print(f"[green]✓[/green] {name}: {msg}")
    else:
        console.print(f"[dim]{name}:[/dim] {msg}")


__all__ = [
    "AdapterInfo",
    "ADAPTER_REGISTRY",
    "BACKEND_PROCESSES",
    "MCP_GATEWAY_PIDFILE",
    "list_adapters",
    "get_adapter",
    "backend_status",
    "server_app",
]
