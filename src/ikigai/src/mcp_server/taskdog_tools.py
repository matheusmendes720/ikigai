"""Taskdog MCP Path 3 — read-only MCP surface for taskdog adapter.

Path 3 per docs/design-system/24-taskdog-paths-architecture.md. Path 1
(harness subprocess → taskdog_cli.py) remains canonical. Path 3 is for
MCP-tool consumers (Claude agents, external MCP clients) that prefer
typed tool calls over subprocess execution.

This module exposes ONLY the read-only surface:
- taskdog_read — get slice by ueid
- taskdog_list — list slices (with optional status filter + limit)
- taskdog_supports_field — capability check

Write path (apply_change) stays out of Path 3 MCP — it routes through the
review queue per Phase 3 v1 ADR-014. Operator CLI / harness subprocess
remains the only write surface until v1.2 (gated on 5+ SONHO logs).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contracts.common import UEID
from mcp.server.fastmcp import FastMCP
from src.mesh.adapters import taskdog as taskdog_mod
from src.mesh.adapters.taskdog import TaskdogAdapter

# Path 3 FastMCP instance — separate from the global ikigai-gateway MCP so
# this module can be wired or registered independently (no cross-talk with
# ADR-013 canonical scope enforcement).
mcp = FastMCP(name="taskdog")


def _apply_db_override(db_path_str: str | None) -> None:
    """Mutate module-level TASKDOG_DB to honor the override (test + ops)."""
    if db_path_str is None:
        return
    target = Path(db_path_str)
    if str(taskdog_mod.TASKDOG_DB) != str(target):
        taskdog_mod.TASKDOG_DB = target


@mcp.tool(
    name="taskdog_read",
    description="Get a taskdog task slice by UEID (read-only). Returns null slice if not found.",
)
def taskdog_read(ueid: str, db_path: str | None = None) -> str:
    """Get the taskdog slice for one UEID. Read-only."""
    _apply_db_override(db_path)
    try:
        parsed = UEID(ueid)
    except ValueError as exc:
        return json.dumps({"error": f"Invalid UEID: {exc}"})
    slice_ = TaskdogAdapter().read(parsed)
    return json.dumps(
        {"ueid": str(parsed), "found": slice_ is not None, "slice": slice_},
        default=str,
    )


@mcp.tool(
    name="taskdog_list",
    description="List taskdog slices (optional status filter, optional limit). Newest first.",
)
def taskdog_list(
    status: str | None = None,
    limit: int | None = None,
    db_path: str | None = None,
) -> str:
    """List taskdog slices, newest first. Read-only."""
    _apply_db_override(db_path)
    tasks: list[dict[str, Any]] = TaskdogAdapter().list_all()
    if status is not None:
        tasks = [t for t in tasks if t.get("status") == status]
    tasks.sort(key=lambda t: t.get("created_at") or "", reverse=True)
    if limit is not None and limit > 0:
        tasks = tasks[:limit]
    return json.dumps(
        {"count": len(tasks), "status_filter": status, "tasks": tasks},
        default=str,
    )


@mcp.tool(
    name="taskdog_supports_field",
    description="Check whether a field name is supported by the taskdog adapter.",
)
def taskdog_supports_field(field_name: str) -> str:
    """Capability check for a taskdog field. Read-only."""
    supported = TaskdogAdapter().supports_field(field_name)
    return json.dumps({"field": field_name, "supported": supported})


# ---------------------------------------------------------------------------
# M148: write tools. Each one enqueues a TaskChange to the mesh review queue
# (data/review_queue/<event_id>.json). Validation happens in agent_consumer;
# propagation fans out to the 3 forks (CLI + taskdog + calendar).
# ---------------------------------------------------------------------------
import uuid as _uuid
from datetime import datetime as _datetime
from typing import Any as _Any

from contracts.task_change import TaskAction, TaskChange
from src.mesh.queue import enqueue as _enqueue_task_change


def _build_task_change(action: TaskAction, ueid: str, fields: dict, *, source: str = "deep_agent") -> str:
    """Build a TaskChange and enqueue it. Returns the event_id."""
    event = TaskChange(
        event_id=str(_uuid.uuid4()),
        ueid=ueid,  # type: ignore[arg-type] — UEID validated by Pydantic at construction
        action=action,
        fields=fields,
        source_fork=source,
        timestamp=_datetime.now(),
    )
    return _enqueue_task_change(event)


@mcp.tool(
    name="taskdog_create",
    description="Create a task in taskdog. Goes through review queue (ADR-014).",
)
def taskdog_create(
    ueid: str,
    title: str,
    due: str | None = None,
    priority: str | int | None = None,
    planned_start: str | None = None,
    planned_end: str | None = None,
) -> str:
    """CREATE: enqueue a new task. Returns event_id."""
    fields: dict[str, _Any] = {"title": title}
    if due is not None:
        fields["due"] = due
    if priority is not None:
        fields["priority"] = priority
    if planned_start is not None:
        fields["planned_start"] = planned_start
    if planned_end is not None:
        fields["planned_end"] = planned_end
    event_id = _build_task_change(TaskAction.CREATE, ueid, fields)
    return json.dumps({"event_id": event_id, "action": "create", "ueid": ueid})


@mcp.tool(
    name="taskdog_done",
    description="Mark a task as done. Goes through review queue.",
)
def taskdog_done(ueid: str) -> str:
    """DONE: enqueue a status='done' mutation."""
    event_id = _build_task_change(TaskAction.DONE, ueid, {})
    return json.dumps({"event_id": event_id, "action": "done", "ueid": ueid})


@mcp.tool(
    name="taskdog_set_status",
    description="Update task status (planned/in_progress/done/cancelled). Goes through review queue.",
)
def taskdog_set_status(ueid: str, status: str) -> str:
    """UPDATE: set status field."""
    if status not in ("planned", "in_progress", "done", "cancelled"):
        return json.dumps({"error": f"invalid status {status!r}; allowed: planned, in_progress, done, cancelled"})
    event_id = _build_task_change(TaskAction.UPDATE, ueid, {"status": status})
    return json.dumps({"event_id": event_id, "action": "update", "field": "status", "value": status, "ueid": ueid})


@mcp.tool(
    name="taskdog_set_priority",
    description="Update task priority (high=1, medium=2, low=3). Goes through review queue.",
)
def taskdog_set_priority(ueid: str, priority: str | int) -> str:
    """UPDATE: set priority field."""
    event_id = _build_task_change(TaskAction.UPDATE, ueid, {"priority": priority})
    return json.dumps({"event_id": event_id, "action": "update", "field": "priority", "value": priority, "ueid": ueid})


@mcp.tool(
    name="taskdog_set_due",
    description="Update task due date (YYYY-MM-DD). Goes through review queue.",
)
def taskdog_set_due(ueid: str, due: str) -> str:
    """UPDATE: set due/deadline field."""
    event_id = _build_task_change(TaskAction.UPDATE, ueid, {"due": due})
    return json.dumps({"event_id": event_id, "action": "update", "field": "due", "value": due, "ueid": ueid})


@mcp.tool(
    name="taskdog_set_planned_dates",
    description="Update task planned start/end dates. Goes through review queue.",
)
def taskdog_set_planned_dates(ueid: str, planned_start: str, planned_end: str) -> str:
    """UPDATE: set planned_start + planned_end fields."""
    fields = {"planned_start": planned_start, "planned_end": planned_end}
    event_id = _build_task_change(TaskAction.UPDATE, ueid, fields)
    return json.dumps({"event_id": event_id, "action": "update", "fields": fields, "ueid": ueid})


@mcp.tool(
    name="taskdog_cancel",
    description="Cancel a task (soft removal: status='cancelled'). Goes through review queue.",
)
def taskdog_cancel(ueid: str) -> str:
    """UPDATE: set status='cancelled' (soft removal). For hard delete, use taskdog_delete."""
    event_id = _build_task_change(TaskAction.UPDATE, ueid, {"status": "cancelled"})
    return json.dumps({"event_id": event_id, "action": "update", "field": "status", "value": "cancelled", "ueid": ueid})


@mcp.tool(
    name="taskdog_delete",
    description="Hard-delete a task from taskdog. Goes through review queue. Irreversible.",
)
def taskdog_delete(ueid: str) -> str:
    """DELETE: remove the row entirely. Use taskdog_cancel for soft removal."""
    event_id = _build_task_change(TaskAction.DELETE, ueid, {})
    return json.dumps({"event_id": event_id, "action": "delete", "ueid": ueid})


@mcp.tool(
    name="taskdog_search",
    description="Search tasks by substring match on name + optional status/priority filters.",
)
def taskdog_search(
    query: str,
    status: str | None = None,
    priority: str | int | None = None,
    limit: int = 10,
) -> str:
    """Search: substring match on task name (case-insensitive) + filters.

    Read-only — does not enqueue anything, hits the adapter directly.
    """
    all_tasks = TaskdogAdapter().list_all()
    q = query.lower().strip()

    def _matches(t: dict) -> bool:
        name = (t.get("name") or "").lower()
        if q and q not in name:
            return False
        if status is not None and t.get("status") != status:
            return False
        if priority is not None:
            # Accept both int and string
            t_pri = t.get("priority")
            if isinstance(priority, str):
                m = {"high": 1, "medium": 2, "low": 3}
                p_int = m.get(priority.lower())
            else:
                p_int = priority
            if t_pri != p_int:
                return False
        return True

    matched = [t for t in all_tasks if _matches(t)]
    matched.sort(key=lambda t: t.get("created_at") or "", reverse=True)
    if limit > 0:
        matched = matched[:limit]
    return json.dumps(
        {"count": len(matched), "query": query, "tasks": matched},
        default=str,
    )


__all__ = [
    "mcp",
    "taskdog_list",
    "taskdog_read",
    "taskdog_supports_field",
    "taskdog_create",
    "taskdog_done",
    "taskdog_set_status",
    "taskdog_set_priority",
    "taskdog_set_due",
    "taskdog_set_planned_dates",
    "taskdog_cancel",
    "taskdog_delete",
    "taskdog_search",
]
