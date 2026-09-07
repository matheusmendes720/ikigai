"""Tuiboard Kanban fork tools (SolidJS MCP via JSON-RPC stdio).

Per user scope (ADR-013): 4 fork tools that wrap tuiboard-mcp.ts (Bun
runtime). All calls route through the private ``_tuiboard_rpc`` helper
which performs a JSON-RPC request/response cycle over subprocess stdio.

The fork is OPTIONAL: if the ``bun`` runtime isn't installed locally,
``_tuiboard_rpc`` raises FileNotFoundError and each tool returns a
friendly "binary not found" message instead of crashing agent.invoke().

Exposes (re-exported by tools.py):
- ``tuiboard_list_boards`` — list markdown kanban boards
- ``tuiboard_get_tasks`` — read tasks from a board (optionally filtered)
- ``tuiboard_create_task`` — create a new task
- ``tuiboard_update_task`` — patch task (done / priority / tags)

Companion modules:
- ``tools_sf`` — Solverforge Calendar fork (2 tools)
- ``tools_taskdog`` — taskdog CLI fork (4 tools)
- ``tools`` — IKIGAI_TOOLS list (12 entries) + re-exports

Architectural reference:
- ADR-013 — planner-only; 4 of 10 external data tools
- W3.6 — side-effect tools (create_task, update_task) gated by
  invoke_skill() outputs check

Drift invariants enforced:
- test_canonical_scope :: test_ikigai_tools_count_is_12
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from langchain_core.tools import tool

from .reliability import (
    CircuitBreakerConfig,
    RetryConfig,
    circuit_breaker,
    invalidate_session_cache,
    retry_with_backoff,
)

# Tuiboard CLI/MCP module paths (configurable via env vars)
_TUIBOARD_CLI = os.environ.get("TUIBOARD_CLI", "bun")
_TUIBOARD_MCP = os.environ.get("TUIBOARD_MCP", "tuiboard-mcp.ts")

# Retry + circuit breaker for tuiboard
_tuiboard_retry_config = RetryConfig(
    max_attempts=3,
    initial_backoff_s=0.5,
    max_backoff_s=8.0,
    backoff_multiplier=2.0,
    jitter=True,
)

_tuiboard_cb_config = CircuitBreakerConfig(
    failure_threshold=5,
    reset_timeout_s=30.0,
)


def _tuiboard_rpc(method: str, params: dict[str, Any] | None = None) -> Any:
    """Execute a JSON-RPC call to tuiboard MCP over stdio."""
    import shutil

    # Short-circuit if tuiboard binary is not installed (e.g. `bun` missing on PATH).
    # Without this guard, subprocess.run raises FileNotFoundError which trips the
    # reliability retry decorator and the tool_node, crashing the agent.invoke().
    if not shutil.which(_TUIBOARD_CLI):
        raise FileNotFoundError(
            f"tuiboard CLI '{_TUIBOARD_CLI}' not found on PATH — tuiboard fork is not wired up; use taskdog_* tools instead."
        )

    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    request_str = json.dumps(request)

    result = subprocess.run(
        [_TUIBOARD_CLI, "run", _TUIBOARD_MCP],
        input=request_str,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise ConnectionError(f"tuiboard error: {result.stderr}")

    # Parse JSON-RPC response
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ConnectionError(f"tuiboard invalid response: {result.stdout}") from exc

    if "error" in response:
        raise ConnectionError(f"tuiboard RPC error: {response['error']}")

    return response.get("result", {})


@tool
@circuit_breaker("tuiboard", _tuiboard_cb_config)
@retry_with_backoff(
    name="tuiboard_list_boards",
    retryable_exceptions=(subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError),
    config=_tuiboard_retry_config,
)
def tuiboard_list_boards() -> str:
    """List all markdown kanban boards from tuiboard.

    Returns:
        Formatted list of available boards or error message.
    """
    try:
        result = _tuiboard_rpc("list_boards", {})
        if not result:
            return "⚠️ No boards found"
        lines = ["**Tuiboard Boards:**", ""]
        for board in result:
            lines.append(f"  • {board.get('name', 'unnamed')} ({board.get('path', '')})")
        return "\n".join(lines)
    except FileNotFoundError as e:
        return f"⚠️ tuiboard unavailable (binary not found): {e}"
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("tuiboard")
        raise
    except Exception as e:
        return f"⚠️ tuiboard unavailable: {e}"


@tool
@circuit_breaker("tuiboard", _tuiboard_cb_config)
@retry_with_backoff(
    name="tuiboard_get_tasks",
    retryable_exceptions=(subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError),
    config=_tuiboard_retry_config,
)
def tuiboard_get_tasks(board_path: str, column: int | None = None, filter_: str = "all") -> str:
    """Get tasks from a tuiboard kanban board.

    Args:
        board_path: Path to the markdown board file.
        column: Optional column index to filter by.
        filter: Filter type (all, pending, done). Defaults to "all".

    Returns:
        Formatted task list or error message.
    """
    try:
        result = _tuiboard_rpc(
            "get_tasks", {"board_path": board_path, "column": column, "filter": filter}
        )
        if not result:
            return "⚠️ No tasks found"
        lines = [f"**Tasks from {board_path}:**", ""]
        for task in result:
            status = "✅" if task.get("done") else "⬜"
            lines.append(
                f"  {status} {task.get('title', 'untitled')} [{task.get('priority', '?')}]"
            )
        return "\n".join(lines)
    except FileNotFoundError as e:
        return f"⚠️ tuiboard unavailable (binary not found): {e}"
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("tuiboard")
        raise
    except Exception as e:
        return f"⚠️ tuiboard unavailable: {e}"


@tool
@circuit_breaker("tuiboard", _tuiboard_cb_config)
@retry_with_backoff(
    name="tuiboard_create_task",
    retryable_exceptions=(subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError),
    config=_tuiboard_retry_config,
)
def tuiboard_create_task(board_path: str, title: str, column: int = 0) -> str:
    """Create a new task in a tuiboard kanban board.

    Args:
        board_path: Path to the markdown board file.
        title: Task title.
        column: Column index to add task to. Defaults to 0.

    Returns:
        Confirmation message or error.
    """
    try:
        result = _tuiboard_rpc(
            "create_task", {"board_path": board_path, "title": title, "column": column}
        )
        return f"✅ Task created: {result.get('id', 'unknown')}"
    except FileNotFoundError as e:
        return f"⚠️ tuiboard unavailable (binary not found): {e}"
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("tuiboard")
        raise
    except Exception as e:
        return f"⚠️ tuiboard unavailable: {e}"


@tool
@circuit_breaker("tuiboard", _tuiboard_cb_config)
@retry_with_backoff(
    name="tuiboard_update_task",
    retryable_exceptions=(subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError),
    config=_tuiboard_retry_config,
)
def tuiboard_update_task(
    board_path: str,
    task_id: str,
    done: bool | None = None,
    priority: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Update a task in a tuiboard kanban board.

    Args:
        board_path: Path to the markdown board file.
        task_id: Task ID to update.
        done: Mark task as done/pending.
        priority: Set priority (low, medium, high).
        tags: Set tags list.

    Returns:
        Confirmation message or error.
    """
    try:
        params: dict[str, Any] = {"board_path": board_path, "task_id": task_id}
        if done is not None:
            params["done"] = done
        if priority is not None:
            params["priority"] = priority
        if tags is not None:
            params["tags"] = tags
        result = _tuiboard_rpc("update_task", params)
        _ = result  # result discarded; status surfaces via RPC error handling
        return f"✅ Task updated: {task_id}"
    except FileNotFoundError as e:
        return f"⚠️ tuiboard unavailable (binary not found): {e}"
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("tuiboard")
        raise
    except Exception as e:
        return f"⚠️ tuiboard unavailable: {e}"


__all__ = [
    "tuiboard_create_task",
    "tuiboard_get_tasks",
    "tuiboard_list_boards",
    "tuiboard_update_task",
]
