"""B3.2 mesh tools: ikigai_mesh_show, ikigai_task_create, ikigai_health.

These are the three MCP tools that map directly to A2UI's three methods
(see docs/superpowers/specs/2026-08-28-a2ui-protocol-design.md §11 R1):

  ikigai_mesh_show(ueid)        <->  A2UI mesh.read
  ikigai_task_create(...)       <->  A2UI task.write (action=create only in v1)
  ikigai_health()               <->  gateway heartbeat

v1 scope: create action only. Other actions return -32601 (deferred to v1.2+).
"""
from __future__ import annotations

import json
import time as _time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from pydantic import ValidationError

from src.contracts.common import UEID
from src.contracts.task_change import TaskAction, TaskChange
from src.mesh import queue as _queue
from src.mesh.adapters import CliAdapter, SolverforgeCalendarAdapter, TaskdogAdapter


_GATEWAY_STARTED_AT: float = _time.time()
_GATEWAY_VERSION = "1.0.0"


def _load_adapters() -> list:
    """Load the 3 fork adapters."""
    return [CliAdapter(), TaskdogAdapter(), SolverforgeCalendarAdapter()]


def _adapter_status(adapter) -> dict[str, Any]:
    """Probe one adapter."""
    info: dict[str, Any] = {
        "name": adapter.name,
        "slice_type": getattr(adapter, "slice_type", "unknown"),
        "exists": True,
    }
    try:
        if hasattr(adapter, "storage_path") and adapter.storage_path is not None:
            info["storage_path"] = str(adapter.storage_path)
            info["exists"] = adapter.storage_path.exists()
    except Exception as e:
        info["exists"] = False
        info["error"] = str(e)
    return info


# ---------------------------------------------------------------------------
# ikigai_mesh_show — A2UI mesh.read
# ---------------------------------------------------------------------------
def ikigai_mesh_show(ueid: Annotated[str, "UEID to look up across forks"]) -> str:
    """Cross-fork view for one UEID."""
    try:
        parsed = UEID(ueid)
    except ValueError as e:
        return json.dumps({"error": f"Invalid UEID: {e}"})

    adapters = _load_adapters()
    view: dict[str, Any] = {}
    mismatches: list[str] = []

    for adapter in adapters:
        try:
            record = adapter.read(parsed)
            view[adapter.name] = record
        except Exception as e:
            view[adapter.name] = None
            mismatches.append(f"{adapter.name}: {type(e).__name__}: {e}")

    # A2uiAdapter is deferred per spec §1 — include a null entry to preserve the contract
    view["a2ui"] = None

    statuses = {
        name: rec.get("status")
        for name, rec in view.items()
        if isinstance(rec, dict) and "status" in rec
    }
    if len(set(statuses.values())) > 1:
        mismatches.append(f"status mismatch across adapters: {statuses}")

    return json.dumps({
        "ueid": str(parsed),
        "view": view,
        "mismatches": mismatches,
    }, indent=2, default=str)


# ---------------------------------------------------------------------------
# ikigai_task_create — A2UI task.write (create only in v1)
# ---------------------------------------------------------------------------
def ikigai_task_create(
    ueid: Annotated[str, "UEID for the new task"],
    fields: Annotated[dict, "Task fields (title required, priority/due/etc. optional)"],
    source_fork: Annotated[str, "Originating fork name (e.g. 'interfaces/cli')"],
    action: Annotated[str, "Task action: create only in v1"] = "create",
) -> str:
    """Emit a TaskChange to data/review_queue/<id>.json (atomic append-only)."""
    if action != "create":
        return json.dumps({
            "error": f"action={action!r} not supported in v1 (create only)",
            "code": -32601,
        })

    try:
        parsed_ueid = UEID(ueid)
    except ValueError as e:
        return json.dumps({"error": f"Invalid UEID: {e}"})

    if not fields.get("title"):
        return json.dumps({"error": "fields.title is required"})

    if not source_fork or len(source_fork) < 2:
        return json.dumps({"error": "source_fork must be >= 2 chars"})

    try:
        event = TaskChange(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            ueid=parsed_ueid,
            action=TaskAction.CREATE,
            fields=fields,
            source_fork=source_fork,
            timestamp=datetime.now(UTC).replace(tzinfo=None),
        )
    except ValidationError as e:
        return json.dumps({"error": f"TaskChange validation failed: {e}"})

    try:
        _queue.enqueue(event)
    except Exception as e:
        return json.dumps({"error": f"queue enqueue failed: {e}"})

    return json.dumps({
        "event_id": event.event_id,
        "status": "pending",
        "ueid": str(parsed_ueid),
    }, indent=2)


# ---------------------------------------------------------------------------
# ikigai_health — gateway heartbeat
# ---------------------------------------------------------------------------
def ikigai_health() -> str:
    """Gateway heartbeat: version, uptime, adapter statuses."""
    adapters = _load_adapters()
    return json.dumps({
        "name": "ikigai-gateway",
        "version": _GATEWAY_VERSION,
        "started_at": _GATEWAY_STARTED_AT,
        "uptime_s": round(_time.time() - _GATEWAY_STARTED_AT, 3),
        "adapters": [_adapter_status(a) for a in adapters],
    }, indent=2)


__all__ = [
    "ikigai_mesh_show",
    "ikigai_task_create",
    "ikigai_health",
]
