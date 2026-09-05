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

from mcp.server.fastmcp import FastMCP
from src.contracts.common import UEID
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


__all__ = [
    "mcp",
    "taskdog_read",
    "taskdog_list",
    "taskdog_supports_field",
]
