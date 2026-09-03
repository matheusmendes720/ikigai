"""Taskdog MCP server (Path 3) — FastMCP wrapper around taskdog.exe subprocess.

Exposes 4 tools over MCP (stdio transport):
  - taskdog_list_tasks
  - taskdog_create_task
  - taskdog_complete_task
  - taskdog_get_task

Mirrors the 4 taskdog @tools in src/ikigai/src/agents/tools.py (Path 1)
but as a standalone MCP server so external clients can drive taskdog
without going through the IKIGAI agent.

Per docs/design-system/24-taskdog-paths-architecture.md §Path-3:
  "External MCP clients connect to this server via stdio. The server
  spawns taskdog.exe subprocesses per request, applies CircuitBreaker +
  retry patterns, and returns JSON-formatted responses."
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_TASKDOG_CLI = os.environ.get("TASKDOG_CLI", "taskdog.exe")
_SERVER_VERSION = "1.0.0"
_STARTED_AT = asyncio.get_event_loop().time() if asyncio._get_running_loop() else 0.0

# Lazy-initialized on first MCP run call
MCP = FastMCP("taskdog-mcp-gateway")


# ---------------------------------------------------------------------------
# Subprocess helpers — mirrors Path 1 in src/ikigai/src/agents/tools.py
# ---------------------------------------------------------------------------

def _run_taskdog(args: list[str], timeout: float = 30.0) -> dict[str, Any]:
    """Run taskdog CLI as subprocess; return structured result.

    Returns:
        dict with keys: ok (bool), stdout (str), stderr (str), returncode (int)
    """
    try:
        result = subprocess.run(  # noqa: S603 — controlled argv list
            [_TASKDOG_CLI, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except FileNotFoundError as e:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"taskdog binary not found: {e}",
            "returncode": -1,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"taskdog timeout after {timeout}s",
            "returncode": -2,
        }
    except Exception as e:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"taskdog subprocess error: {type(e).__name__}: {e}",
            "returncode": -3,
        }


def _format_response(result: dict[str, Any], operation: str) -> str:
    """Format subprocess result as MCP response string."""
    import json

    if result["ok"]:
        return json.dumps(
            {
                "status": "ok",
                "operation": operation,
                "output": result["stdout"],
            },
            indent=2,
        )
    return json.dumps(
        {
            "status": "error",
            "operation": operation,
            "error": result["stderr"] or "unknown error",
            "returncode": result["returncode"],
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@MCP.tool(
    name="taskdog_list_tasks",
    description="List tasks from taskdog. Optional status filter (pending/done) and --all for archived.",
)
def taskdog_list_tasks(status: str | None = None, include_archived: bool = False) -> str:
    """List tasks from taskdog CLI."""
    args = ["list"]
    if status:
        args.extend(["--status", status])
    if include_archived:
        args.append("--all")
    result = _run_taskdog(args)
    return _format_response(result, "list")


@MCP.tool(
    name="taskdog_create_task",
    description="Create a new task in taskdog. Returns the created task ID.",
)
def taskdog_create_task(name: str) -> str:
    """Create a task in taskdog."""
    result = _run_taskdog(["add", name])
    return _format_response(result, "create")


@MCP.tool(
    name="taskdog_complete_task",
    description="Mark a task as completed in taskdog by task ID.",
)
def taskdog_complete_task(task_id: int) -> str:
    """Complete a task in taskdog."""
    result = _run_taskdog(["done", str(task_id)])
    return _format_response(result, "complete")


@MCP.tool(
    name="taskdog_get_task",
    description="Get full task details from taskdog by task ID. Note: taskdog 0.23.0 'show' has a known bug — surfaces error gracefully.",
)
def taskdog_get_task(task_id: int) -> str:
    """Get task details from taskdog."""
    result = _run_taskdog(["show", str(task_id)])
    # taskdog 0.23.0 'show' has a known bug; surface as warning, not error.
    import json

    if not result["ok"]:
        return json.dumps(
            {
                "status": "warning",
                "operation": "get",
                "task_id": task_id,
                "error": result["stderr"] or result["stdout"],
                "note": "taskdog show may not be fully supported in 0.23.0 — see taskdog issue tracker",
            },
            indent=2,
        )
    return _format_response(result, "get")


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@MCP.resource("taskdog://health")
def taskdog_health_resource() -> str:
    """Taskdog MCP gateway health snapshot."""
    import json
    import time

    return json.dumps(
        {
            "name": "taskdog-mcp-gateway",
            "version": _SERVER_VERSION,
            "started_at": _STARTED_AT,
            "uptime_s": round(time.time() - _STARTED_AT, 3) if _STARTED_AT else 0,
            "binary": _TASKDOG_CLI,
            "tools": [
                "taskdog_list_tasks",
                "taskdog_create_task",
                "taskdog_complete_task",
                "taskdog_get_task",
            ],
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def main() -> None:
    """Run the FastMCP gateway over stdio."""
    await MCP.run_stdio_async()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
