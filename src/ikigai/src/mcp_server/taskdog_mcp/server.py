"""Path 3 — taskdog MCP server (4 tools).

Exposes the 4 Path 1 taskdog @tool functions as MCP server tools via
FastMCP. Reuses Path 1 logic verbatim — no business logic duplication.

Tools:
- taskdog_list_tasks    : List taskdog tasks (filter by status, all flag)
- taskdog_create_task   : Create a new task in taskdog
- taskdog_complete_task : Mark a task as done in taskdog
- taskdog_get_task      : Get full task details from taskdog

Each tool delegates to the corresponding Path 1 @tool function from
`src/agents/tools.py`. This is the canonical Path 3 entry point per
`docs/design-system/24-taskdog-paths-architecture.md`.

Run with::

    python -m mcp_server.taskdog_mcp.server
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
MCP = FastMCP("ikigai-taskdog-gateway")


# ---------------------------------------------------------------------------
# Path 3 handlers — delegate to Path 1 @tool functions
# ---------------------------------------------------------------------------


def _handle_list_tasks(arguments: dict[str, Any]) -> str:
    """Delegate taskdog_list_tasks to Path 1."""
    from agents.tools import taskdog_list_tasks

    status = arguments.get("status")
    include_archived = arguments.get("include_archived", False)
    return taskdog_list_tasks(status=status, include_archived=include_archived)


def _handle_create_task(arguments: dict[str, Any]) -> str:
    """Delegate taskdog_create_task to Path 1."""
    from agents.tools import taskdog_create_task

    name = arguments.get("name", "")
    if not name:
        return "⚠️ taskdog_create_task: 'name' argument is required"
    return taskdog_create_task(name=name)


def _handle_complete_task(arguments: dict[str, Any]) -> str:
    """Delegate taskdog_complete_task to Path 1."""
    from agents.tools import taskdog_complete_task

    task_id = arguments.get("task_id")
    if task_id is None:
        return "⚠️ taskdog_complete_task: 'task_id' argument is required"
    return taskdog_complete_task(task_id=int(task_id))


def _handle_get_task(arguments: dict[str, Any]) -> str:
    """Delegate taskdog_get_task to Path 1."""
    from agents.tools import taskdog_get_task

    task_id = arguments.get("task_id")
    if task_id is None:
        return "⚠️ taskdog_get_task: 'task_id' argument is required"
    return taskdog_get_task(task_id=int(task_id))


# ---------------------------------------------------------------------------
# MCP tool registrations
# ---------------------------------------------------------------------------


@MCP.tool(
    name="taskdog_list_tasks",
    description="List taskdog tasks (filter by status, include archived). Path 3 MCP tool.",
)
def taskdog_list_tasks_mcp(
    status: str | None = None,
    include_archived: bool = False,
) -> str:
    """List taskdog tasks with optional filters."""
    return _handle_list_tasks({"status": status, "include_archived": include_archived})


@MCP.tool(
    name="taskdog_create_task",
    description="Create a new task in taskdog. Path 3 MCP tool.",
)
def taskdog_create_task_mcp(name: str) -> str:
    """Create a new task in taskdog."""
    return _handle_create_task({"name": name})


@MCP.tool(
    name="taskdog_complete_task",
    description="Mark a task as completed in taskdog. Path 3 MCP tool.",
)
def taskdog_complete_task_mcp(task_id: int) -> str:
    """Mark a task as completed in taskdog."""
    return _handle_complete_task({"task_id": task_id})


@MCP.tool(
    name="taskdog_get_task",
    description="Get full task details from taskdog by ID. Path 3 MCP tool.",
)
def taskdog_get_task_mcp(task_id: int) -> str:
    """Get full task details from taskdog."""
    return _handle_get_task({"task_id": task_id})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the taskdog MCP server on stdio."""
    logger.info("Starting ikigai-taskdog-gateway MCP server (Path 3, 4 tools)")
    MCP.run()


if __name__ == "__main__":
    main()
