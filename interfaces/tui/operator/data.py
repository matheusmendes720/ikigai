"""Data loaders for the operator TUI.

Mirrors the canonical adapter registry from `interfaces.cli.server`
so the TUI stays in sync with `life server ls/inspect/status`.

We deliberately import adapter classes directly from `src.mesh.adapters`
rather than going through `interfaces.cli.server` to keep the import
chain shallow (avoids test-fixture shadowing of `contracts`/`mesh`
packages by pytest's `tests/*` __init__.py convention).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Direct imports — avoids chain through interfaces.cli → read_tasks → contracts
from src.mesh.adapters.cli import TASKS_JSONL
from src.mesh.adapters.solverforge_calendar import UPI_DB
from src.mesh.adapters.taskdog import TASKDOG_DB

REPO_ROOT = Path(__file__).parent.parent.parent.parent
REVIEW_QUEUE_DIR = REPO_ROOT / "data" / "review_queue"


# === Adapter registry (mirror of interfaces.cli.server.ADAPTER_REGISTRY) ===
#
# If the registry in interfaces/cli/server.py changes, mirror the change here.
# Single source of truth: interfaces/cli/server.py — this is a structural copy
# to keep the TUI import chain shallow.

@dataclass(frozen=True)
class AdapterInfo:
    """Metadata for one fork adapter in the IKIGAI mesh topology."""

    name: str
    slice_type: str  # "jsonl" | "sqlite" | "spec-only"
    storage_path: Path | None  # None when slice_type is "spec-only"
    spec_ref: str | None = None

    def exists(self) -> bool:
        if self.storage_path is None:
            return True
        return self.storage_path.exists()


ADAPTER_REGISTRY: dict[str, AdapterInfo] = {
    "cli": AdapterInfo(name="cli", slice_type="jsonl", storage_path=TASKS_JSONL),
    "taskdog": AdapterInfo(name="taskdog", slice_type="sqlite", storage_path=TASKDOG_DB),
    "solverforge_calendar": AdapterInfo(
        name="solverforge_calendar", slice_type="sqlite", storage_path=UPI_DB
    ),
    "a2ui": AdapterInfo(
        name="a2ui",
        slice_type="spec-only",
        storage_path=None,
        spec_ref="docs/superpowers/specs/2026-08-28-a2ui-protocol-design.md",
    ),
}


# === Backend process registry (mirror of interfaces.cli.server.BACKEND_PROCESSES) ===

MCP_GATEWAY_PIDFILE = REPO_ROOT / "data" / "run" / "mcp_gateway.pid"
REVIEW_QUEUE_WORKER_PIDFILE = REPO_ROOT / "data" / "run" / "review_queue_worker.pid"

BACKEND_PROCESSES: dict[str, dict[str, Any]] = {
    "review_queue_worker": {
        "phase": "B4",
        "description": "Consumes data/review_queue/<id>.json events",
        "pidfile_path": REVIEW_QUEUE_WORKER_PIDFILE,
    },
    "agent_consumer": {
        "phase": "B5",
        "description": "Validates TaskChange (PAE: APPROVE/REJECT/CLARIFY) — runs inside review_queue_worker",
    },
    "agent_propagator": {
        "phase": "B5",
        "description": "Emits PropagationEvents to all fork adapters — runs inside review_queue_worker",
    },
    "mcp_gateway": {
        "phase": "B3",
        "description": "13 tools + 6 resources MCP gateway (B3.1-B3.3)",
        "pidfile_path": MCP_GATEWAY_PIDFILE,
    },
}


# === Render-ready row types ===

@dataclass(frozen=True)
class AdapterRow:
    """Render-ready row for the adapters table."""

    name: str
    slice_type: str
    exists: bool
    storage_path: str
    spec_ref: str | None

    @classmethod
    def from_info(cls, info: AdapterInfo) -> "AdapterRow":
        return cls(
            name=info.name,
            slice_type=info.slice_type,
            exists=info.exists(),
            storage_path=str(info.storage_path) if info.storage_path else "—",
            spec_ref=info.spec_ref,
        )


@dataclass(frozen=True)
class BackendRow:
    """Render-ready row for the backend processes table."""

    name: str
    phase: str
    running: bool
    pid: int | None
    description: str


@dataclass(frozen=True)
class QueueRow:
    """Render-ready row for the review queue table."""

    event_id: str
    ueid: str
    action: str
    source_fork: str
    timestamp: str
    status: str


# === Load helpers ===

def list_adapters() -> list[AdapterInfo]:
    """Return all registered adapters in stable order."""
    return [ADAPTER_REGISTRY[name] for name in sorted(ADAPTER_REGISTRY)]


def get_adapter(name: str) -> AdapterInfo:
    """Return adapter by name. Raises KeyError if not registered."""
    if name not in ADAPTER_REGISTRY:
        available = ", ".join(sorted(ADAPTER_REGISTRY))
        raise KeyError(f"Unknown adapter {name!r}. Available: {available}")
    return ADAPTER_REGISTRY[name]


def _pid_alive(pid: int) -> bool:
    """Cross-platform liveness check."""
    if pid <= 0:
        return False
    try:
        import os

        if os.name == "nt":
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle == 0:
                return False
            try:
                exit_code = ctypes.c_ulong()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return False
                return exit_code.value == STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        else:
            os.kill(pid, 0)
            return True
    except (OSError, AttributeError):
        return False


def _read_pidfile(pidfile_path: Path) -> int | None:
    """Read PID from pidfile. Returns None if missing or invalid."""
    if not pidfile_path.exists():
        return None
    try:
        return int(pidfile_path.read_text().strip())
    except (ValueError, OSError):
        return None


def backend_status() -> list[dict[str, Any]]:
    """Return status snapshot for all backend processes."""
    rows: list[dict[str, Any]] = []
    for name, meta in BACKEND_PROCESSES.items():
        row: dict[str, Any] = {
            "name": name,
            "phase": meta["phase"],
            "description": meta["description"],
            "running": False,
            "pid": None,
            "started_at": None,
        }
        pidfile = meta.get("pidfile_path")
        if pidfile is not None:
            pid = _read_pidfile(pidfile)
            if pid is not None and _pid_alive(pid):
                row["running"] = True
                row["pid"] = pid
                try:
                    row["started_at"] = pidfile.stat().st_mtime
                except OSError:
                    pass
        rows.append(row)
    return rows


def load_adapter_rows() -> list[AdapterRow]:
    """Return all adapters as render-ready rows."""
    return [AdapterRow.from_info(info) for info in list_adapters()]


def load_backend_rows() -> list[BackendRow]:
    """Return all backend processes as render-ready rows."""
    snapshot = backend_status()
    return [
        BackendRow(
            name=row["name"],
            phase=row["phase"],
            running=row["running"],
            pid=row.get("pid"),
            description=row["description"],
        )
        for row in snapshot
    ]


def load_queue_rows(limit: int = 100) -> list[QueueRow]:
    """Read pending TaskChange events from data/review_queue/."""
    if not REVIEW_QUEUE_DIR.is_dir():
        return []

    rows: list[QueueRow] = []
    for f in sorted(REVIEW_QUEUE_DIR.glob("*.json"))[:limit]:
        try:
            payload: dict[str, Any] = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rows.append(
            QueueRow(
                event_id=str(payload.get("event_id", f.stem)),
                ueid=str(payload.get("ueid", "—")),
                action=str(payload.get("action", "—")),
                source_fork=str(payload.get("source_fork", "—")),
                timestamp=str(payload.get("timestamp", "—")),
                status=str(payload.get("status", "pending")),
            )
        )
    return rows


def adapter_summary() -> dict[str, Any]:
    """Single-adapter deep-dive payload."""
    rows = load_adapter_rows()
    return {
        "total": len(rows),
        "ok": sum(1 for r in rows if r.exists),
        "missing": sum(1 for r in rows if not r.exists),
    }


__all__ = [
    "AdapterInfo",
    "AdapterRow",
    "BackendRow",
    "QueueRow",
    "load_adapter_rows",
    "load_backend_rows",
    "load_queue_rows",
    "adapter_summary",
    "ADAPTER_REGISTRY",
    "BACKEND_PROCESSES",
    "get_adapter",
    "list_adapters",
    "backend_status",
]
