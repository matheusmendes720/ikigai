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
import re
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
    name="taskdog_cancel",
    description="Cancel a task (soft removal: status='cancelled'). Goes through review queue.",
)
def taskdog_cancel(ueid: str) -> str:
    """UPDATE: set status='cancelled' (soft removal). For hard delete, use taskdog_delete."""
    event_id = _build_task_change(TaskAction.UPDATE, ueid, {"status": "cancelled"})
    return json.dumps({"event_id": event_id, "action": "update", "field": "status", "value": "cancelled", "ueid": ueid})


# ---------------------------------------------------------------------------
# M163/M164 — full MCP surface for the v2 schema (tags, deps, notes, audit).
# Each write tool enqueues a TaskChange to the mesh review queue per ADR-014;
# read-only tools query the TaskdogAdapter directly. The drift-net guard
# test_taskdog_tools_read_only_contract allows write tools here IF they
# route through _enqueue_task_change (no direct SQLite writes from MCP).
# ---------------------------------------------------------------------------

# Tag validation — same regex the td CLI uses (alphanumeric+hyphen+underscore,
# 1-32 chars). Kept inline so the MCP tool returns a clear error before the
# review queue worker sees it.
_TAG_REGEX = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
_MAX_TAG_LEN = 32
_MAX_NOTE_LEN = 4000


def _validate_ueid(ueid: str) -> tuple[bool, str]:
    """Return (ok, parsed_or_error_msg). parsed is UEID instance on success."""
    try:
        return True, UEID(ueid)
    except (ValueError, TypeError) as exc:
        return False, f"Invalid UEID: {exc}"


def _validate_tags(tags: Any) -> tuple[bool, str | None]:
    """Validate tag list. Returns (ok, error_msg)."""
    if not isinstance(tags, list):
        return False, f"tags must be list[str], got {type(tags).__name__}"
    if not tags:
        return False, "tags must not be empty"
    for t in tags:
        if not isinstance(t, str):
            return False, f"each tag must be a string, got {type(t).__name__}"
        if not _TAG_REGEX.match(t):
            return False, (
                f"invalid tag {t!r} (max {_MAX_TAG_LEN} chars, "
                "alphanumeric+hyphen+underscore)"
            )
    return True, None


# ---------------------------------------------------------------------------
# Tag tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="taskdog_tag_add",
    description="Append tags to a task's tag set. Idempotent. Goes through review queue (ADR-014).",
)
def taskdog_tag_add(ueid: str, tags: list[str]) -> str:
    """TAG_ADD: append tags list. Returns event_id."""
    ok, err = _validate_ueid(ueid)
    if not ok:
        return json.dumps({"error": err})
    ok_t, err_t = _validate_tags(tags)
    if not ok_t:
        return json.dumps({"error": err_t})
    event_id = _build_task_change(TaskAction.TAG_ADD, ueid, {"tags": list(tags)})
    return json.dumps(
        {"event_id": event_id, "action": "tag_add", "ueid": ueid, "tags": list(tags)}
    )


@mcp.tool(
    name="taskdog_tag_remove",
    description="Remove tags from a task. Missing tags are no-ops. Goes through review queue (ADR-014).",
)
def taskdog_tag_remove(ueid: str, tags: list[str]) -> str:
    """TAG_REMOVE: drop tags list. Returns event_id."""
    ok, err = _validate_ueid(ueid)
    if not ok:
        return json.dumps({"error": err})
    ok_t, err_t = _validate_tags(tags)
    if not ok_t:
        return json.dumps({"error": err_t})
    event_id = _build_task_change(TaskAction.TAG_REMOVE, ueid, {"tags": list(tags)})
    return json.dumps(
        {"event_id": event_id, "action": "tag_remove", "ueid": ueid, "tags": list(tags)}
    )


@mcp.tool(
    name="taskdog_tag_list",
    description="Return the canonical tag list for a task (read-only). Empty list if no tags.",
)
def taskdog_tag_list(ueid: str, db_path: str | None = None) -> str:
    """Read the tags array for a task directly from the adapter slice."""
    _apply_db_override(db_path)
    ok, parsed_or_err = _validate_ueid(ueid)
    if not ok:
        return json.dumps({"error": parsed_or_err})
    slice_ = TaskdogAdapter().read(parsed_or_err)
    if slice_ is None:
        return json.dumps({"error": "ueid not found", "ueid": str(parsed_or_err)})
    tags = slice_.get("tags") or []
    return json.dumps(
        {"ueid": str(parsed_or_err), "count": len(tags), "tags": tags}, default=str
    )


@mcp.tool(
    name="taskdog_tag_clear",
    description="Remove all tags from a task. Idempotent. Goes through review queue (ADR-014).",
)
def taskdog_tag_clear(ueid: str) -> str:
    """TAG_CLEAR: wipe all tags. Returns event_id."""
    ok, err = _validate_ueid(ueid)
    if not ok:
        return json.dumps({"error": err})
    event_id = _build_task_change(TaskAction.TAG_CLEAR, ueid, {})
    return json.dumps({"event_id": event_id, "action": "tag_clear", "ueid": ueid})


# ---------------------------------------------------------------------------
# Dep tools
# ---------------------------------------------------------------------------


def _parsed_safe(ueid: str) -> UEID | None:
    """Best-effort UEID parse — returns None on bad input. Used for the
    self-dep comparison without double-counting validation errors."""
    try:
        return UEID(ueid)
    except (ValueError, TypeError):
        return None


def _validate_two_ueids(ueid: str, other_ueid: str) -> tuple[bool, str]:
    """Validate both ueids. Returns (ok, error_msg)."""
    ok1, err1 = _validate_ueid(ueid)
    if not ok1:
        return False, err1
    ok2, err2 = _validate_ueid(other_ueid)
    if not ok2:
        return False, f"invalid other_ueid: {err2}"
    return True, ""


@mcp.tool(
    name="taskdog_dep_add",
    description="Add a dependency: this task depends on `other_ueid` being done. Goes through review queue (ADR-014).",
)
def taskdog_dep_add(ueid: str, other_ueid: str) -> str:
    """UPDATE: append other_ueid to deps list. Returns event_id."""
    ok, err = _validate_two_ueids(ueid, other_ueid)
    if not ok:
        return json.dumps({"error": err})
    p1 = _parsed_safe(ueid)
    p2 = _parsed_safe(other_ueid)
    if p1 is not None and p2 is not None and str(p1) == str(p2):
        return json.dumps({"error": "ueid and other_ueid must differ (no self-deps)"})
    event_id = _build_task_change(
        TaskAction.UPDATE, ueid, {"deps_add": [other_ueid]}
    )
    return json.dumps(
        {"event_id": event_id, "action": "update", "field": "deps_add", "ueid": ueid, "other_ueid": other_ueid}
    )


@mcp.tool(
    name="taskdog_dep_remove",
    description="Remove a dependency on `other_ueid`. Goes through review queue (ADR-014).",
)
def taskdog_dep_remove(ueid: str, other_ueid: str) -> str:
    """UPDATE: drop other_ueid from deps list. Returns event_id."""
    ok, err = _validate_two_ueids(ueid, other_ueid)
    if not ok:
        return json.dumps({"error": err})
    event_id = _build_task_change(
        TaskAction.UPDATE, ueid, {"deps_remove": [other_ueid]}
    )
    return json.dumps(
        {"event_id": event_id, "action": "update", "field": "deps_remove", "ueid": ueid, "other_ueid": other_ueid}
    )


@mcp.tool(
    name="taskdog_dep_list",
    description="Return the dependency list for a task (read-only). Empty list if no deps.",
)
def taskdog_dep_list(ueid: str, db_path: str | None = None) -> str:
    """Read the deps array for a task directly from the adapter slice."""
    _apply_db_override(db_path)
    ok, parsed_or_err = _validate_ueid(ueid)
    if not ok:
        return json.dumps({"error": parsed_or_err})
    slice_ = TaskdogAdapter().read(parsed_or_err)
    if slice_ is None:
        return json.dumps({"error": "ueid not found", "ueid": str(parsed_or_err)})
    deps = slice_.get("deps") or []
    return json.dumps(
        {"ueid": str(parsed_or_err), "count": len(deps), "deps": deps}, default=str
    )


@mcp.tool(
    name="taskdog_dep_blocked",
    description="Return tasks with at least one unmet dependency (read-only). Scans all tasks.",
)
def taskdog_dep_blocked(db_path: str | None = None) -> str:
    """Find tasks whose deps include at least one UEID whose status != 'done'."""
    _apply_db_override(db_path)
    tasks = TaskdogAdapter().list_all()
    by_ueid: dict[str, dict[str, Any]] = {
        str(t.get("ueid")): t for t in tasks if t.get("ueid")
    }
    blocked: list[dict[str, Any]] = []
    for t in tasks:
        ueid_str = str(t.get("ueid") or "")
        deps = t.get("deps") or []
        if not deps:
            continue
        unmet = [
            d for d in deps
            if d not in by_ueid or by_ueid[d].get("status") != "done"
        ]
        if unmet:
            blocked.append({
                "ueid": ueid_str,
                "name": t.get("name"),
                "status": t.get("status"),
                "deps": list(deps),
                "unmet_deps": unmet,
            })
    return json.dumps(
        {"count": len(blocked), "blocked": blocked}, default=str
    )


# ---------------------------------------------------------------------------
# Note tools (notes are stored in the audit_log with action='note_add')
# ---------------------------------------------------------------------------


@mcp.tool(
    name="taskdog_note_add",
    description="Append a free-text note to a task. Goes through review queue (ADR-014).",
)
def taskdog_note_add(ueid: str, text: str) -> str:
    """UPDATE: append note entry to audit_log. Returns event_id."""
    ok, err = _validate_ueid(ueid)
    if not ok:
        return json.dumps({"error": err})
    if not isinstance(text, str):
        return json.dumps({"error": f"text must be str, got {type(text).__name__}"})
    if not text:
        return json.dumps({"error": "text must not be empty"})
    if len(text) > _MAX_NOTE_LEN:
        return json.dumps({"error": f"text exceeds {_MAX_NOTE_LEN} chars"})
    event_id = _build_task_change(
        TaskAction.UPDATE, ueid, {"note": text}
    )
    return json.dumps(
        {"event_id": event_id, "action": "update", "field": "note", "ueid": ueid, "length": len(text)}
    )


@mcp.tool(
    name="taskdog_note_show",
    description="Return the notes (audit_log entries with action='note_add') for a task (read-only).",
)
def taskdog_note_show(ueid: str, db_path: str | None = None) -> str:
    """Read the audit_log filtered to note_add entries."""
    _apply_db_override(db_path)
    ok, parsed_or_err = _validate_ueid(ueid)
    if not ok:
        return json.dumps({"error": parsed_or_err})
    slice_ = TaskdogAdapter().read(parsed_or_err)
    if slice_ is None:
        return json.dumps({"error": "ueid not found", "ueid": str(parsed_or_err)})
    audit = slice_.get("audit_log") or []
    notes = [
        e for e in audit
        if isinstance(e, dict) and e.get("action") == "note_add"
    ]
    return json.dumps(
        {"ueid": str(parsed_or_err), "count": len(notes), "notes": notes},
        default=str,
    )


# ---------------------------------------------------------------------------
# Status wrappers (pause / reopen) — cancel already exists above.
# ---------------------------------------------------------------------------


# Allowed statuses for pause/reopen. cancel reuses taskdog_cancel.
# 'paused' is a logical state the agent layer uses; the SQLite adapter
# may or may not accept it depending on the v2 schema version. We
# enqueue the event either way (the consumer validates per-schema).
_PAUSE_STATUS = "paused"
_REOPEN_STATUS = "planned"


@mcp.tool(
    name="taskdog_pause",
    description="Pause a task (status='paused'). Goes through review queue (ADR-014).",
)
def taskdog_pause(ueid: str) -> str:
    """UPDATE: set status='paused'."""
    ok, err = _validate_ueid(ueid)
    if not ok:
        return json.dumps({"error": err})
    event_id = _build_task_change(TaskAction.UPDATE, ueid, {"status": _PAUSE_STATUS})
    return json.dumps(
        {"event_id": event_id, "action": "update", "field": "status", "value": _PAUSE_STATUS, "ueid": ueid}
    )


@mcp.tool(
    name="taskdog_reopen",
    description="Reopen a task (status='planned'). Goes through review queue (ADR-014).",
)
def taskdog_reopen(ueid: str) -> str:
    """UPDATE: set status='planned'."""
    ok, err = _validate_ueid(ueid)
    if not ok:
        return json.dumps({"error": err})
    event_id = _build_task_change(TaskAction.UPDATE, ueid, {"status": _REOPEN_STATUS})
    return json.dumps(
        {"event_id": event_id, "action": "update", "field": "status", "value": _REOPEN_STATUS, "ueid": ueid}
    )


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


@mcp.tool(
    name="taskdog_audit",
    description="Return the full audit_log array for a task (read-only).",
)
def taskdog_audit(ueid: str, db_path: str | None = None) -> str:
    """Read the full audit_log for one task."""
    _apply_db_override(db_path)
    ok, parsed_or_err = _validate_ueid(ueid)
    if not ok:
        return json.dumps({"error": parsed_or_err})
    slice_ = TaskdogAdapter().read(parsed_or_err)
    if slice_ is None:
        return json.dumps({"error": "ueid not found", "ueid": str(parsed_or_err)})
    audit = slice_.get("audit_log") or []
    return json.dumps(
        {"ueid": str(parsed_or_err), "count": len(audit), "audit_log": audit},
        default=str,
    )


__all__ = [
    "mcp",
    "taskdog_list",
    "taskdog_read",
    "taskdog_supports_field",
    "taskdog_create",
    "taskdog_set_status",
    "taskdog_set_priority",
    "taskdog_set_due",
    "taskdog_cancel",
    # M163/M164 surface
    "taskdog_tag_add",
    "taskdog_tag_remove",
    "taskdog_tag_list",
    "taskdog_tag_clear",
    "taskdog_dep_add",
    "taskdog_dep_remove",
    "taskdog_dep_list",
    "taskdog_dep_blocked",
    "taskdog_note_add",
    "taskdog_note_show",
    "taskdog_pause",
    "taskdog_reopen",
    "taskdog_audit",
]
