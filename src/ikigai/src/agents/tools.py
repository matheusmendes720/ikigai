"""IKIGAi tools — wrapped as LangChain @tool for deepagents.

Per user scope (2026-08-31): the agent layer is a PLANNING ASSISTANT ONLY.
It binds 12 tools (10 external data + 2 vault reads). It does NOT bind
math/policy/business-rule tools (ikigai_score, ikigai_regime, ikigai_phase,
ikigai_corrections, ikigai_decompose, ikigai_plan_cycle, ikigai_sync_vault,
ikigai_checkpoint) — those live behind the MCP interface
(`src/mcp_server/server.py`) per attribution §3.
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
    _set_cache_ref,
    circuit_breaker,
    invalidate_session_cache,
    retry_with_backoff,
)

# ---------------------------------------------------------------------------
# MCP Session Cache (for connection state tracking)
# ---------------------------------------------------------------------------

# Cache for session initialization state — invalidated on connection failures
_MCP_SESSION_CACHE: dict[str, bool] = {}
_set_cache_ref(_MCP_SESSION_CACHE)

# ---------------------------------------------------------------------------
# External tool configurations
# ---------------------------------------------------------------------------

_SOLVERFORGE_CLI = os.environ.get("SOLVERFORGE_CLI", "solverforge-calendar-cli.exe")
_TUIBOARD_CLI = os.environ.get("TUIBOARD_CLI", "bun")
_TUIBOARD_MCP = os.environ.get("TUIBOARD_MCP", "tuiboard-mcp.ts")
_TASKDOG_CLI = os.environ.get("TASKDOG_CLI", "taskdog.exe")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Algorithm helpers — STRIPPED 2026-08-31 (see note below).
# What was removed: _PROJECT_ROOT, _CHECKPOINT_DB, _VAULT_DIR module vars,
# _get_checkpoint_path(), _read_checkpoint_data(). These existed solely to
# serve the 8 algorithm @tool decorators that have been removed from this
# module (the agent layer must NOT bind math/policy/business-rule tools).



# ---------------------------------------------------------------------------
# Algorithm @tool decorators — STRIPPED 2026-08-31 (see note below).
# What was removed: 8 @tool functions that bound IKIGAi math/policy/
# business-rule execution to the conversational agent (ikigai_score,
# ikigai_regime, ikigai_phase, ikigai_corrections, ikigai_decompose,
# ikigai_plan_cycle, ikigai_sync_vault, ikigai_checkpoint). Per user
# scope, the agent is a PLANNING ASSISTANT ONLY — algorithms live behind
# the MCP interface (`src/mcp_server/server.py`).
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Tools 2-5: regime, phase, corrections, decompose — STRIPPED (see note above).
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Tool 6: plan_cycle — STRIPPED (see note above). This tool previously imported
# `make_ikigai_graph` from `agents.ikigai_maintainer` and invoked it with the
# full algo state — the bridge between MCP interface-style calls and the
# LangGraph algorithm execution graph. Algorithm execution does NOT happen
# in the agent layer; the agent only plans via prompt chains.
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Tools 7-8: sync_vault, checkpoint — STRIPPED (see note above).
# The `_format_corrections()` helper and these two @tool decorators both
# assumed the persistence-layer checkpoint DB. The agent layer does not
# own checkpoint state; vault writes go through `vault_write` (B6.4) and
# checkpoint introspection belongs behind the MCP interface.
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# External Tool: Solverforge Calendar (Rust CLI)
# ---------------------------------------------------------------------------

# Retry config for solverforge
_solverforge_retry_config = RetryConfig(
    max_attempts=3,
    initial_backoff_s=0.5,
    max_backoff_s=8.0,
    backoff_multiplier=2.0,
    jitter=True,
)

_solverforge_cb_config = CircuitBreakerConfig(
    failure_threshold=5,
    reset_timeout_s=30.0,
)


@tool
@circuit_breaker("solverforge", _solverforge_cb_config)
@retry_with_backoff(
    name="solverforge_list_events",
    retryable_exceptions=(subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError),
    config=_solverforge_retry_config,
)
def solverforge_list_events(days: int = 7) -> str:
    """List upcoming calendar events from solverforge.

    Args:
        days: Number of days to look ahead. Defaults to 7.

    Returns:
        Formatted list of upcoming events or error message.
    """
    try:
        result = subprocess.run(
            [_SOLVERFORGE_CLI, "events", "list", "--days", str(days)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ConnectionError(f"solverforge error: {result.stderr}")
        return result.stdout
    except FileNotFoundError as e:
        # Binary missing — return friendly message instead of crashing agent.invoke().
        return f"⚠️ solverforge unavailable (binary not found): {e}"
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("solverforge")
        raise
    except Exception as e:
        return f"⚠️ solverforge unavailable: {e}"


@tool
@circuit_breaker("solverforge", _solverforge_cb_config)
@retry_with_backoff(
    name="solverforge_create_event",
    retryable_exceptions=(subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError),
    config=_solverforge_retry_config,
)
def solverforge_create_event(title: str, date: str, time: str = "09:00") -> str:
    """Create a calendar event in solverforge.

    Args:
        title: Event title.
        date: Event date (YYYY-MM-DD).
        time: Event time (HH:MM). Defaults to "09:00".

    Returns:
        Confirmation message or error.
    """
    try:
        result = subprocess.run(
            [
                _SOLVERFORGE_CLI,
                "events",
                "create",
                "--title",
                title,
                "--date",
                date,
                "--time",
                time,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ConnectionError(f"solverforge error: {result.stderr}")
        return result.stdout
    except FileNotFoundError as e:
        # Binary missing — return friendly message instead of crashing agent.invoke().
        return f"⚠️ solverforge unavailable (binary not found): {e}"
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("solverforge")
        raise
    except Exception as e:
        return f"⚠️ solverforge unavailable: {e}"


# ---------------------------------------------------------------------------
# External Tool: Tuiboard Kanban (SolidJS MCP via JSON-RPC)
# ---------------------------------------------------------------------------

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
        # Binary missing — return friendly message instead of crashing agent.invoke().
        # This fork is not wired up (tuiboard requires `bun` runtime which isn't installed).
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
        # Binary missing — return friendly message instead of crashing agent.invoke().
        # This fork is not wired up (tuiboard requires `bun` runtime which isn't installed).
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
        # Binary missing — return friendly message instead of crashing agent.invoke().
        # This fork is not wired up (tuiboard requires `bun` runtime which isn't installed).
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
        # Binary missing — return friendly message instead of crashing agent.invoke().
        # This fork is not wired up (tuiboard requires `bun` runtime which isn't installed).
        return f"⚠️ tuiboard unavailable (binary not found): {e}"
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("tuiboard")
        raise
    except Exception as e:
        return f"⚠️ tuiboard unavailable: {e}"


# ---------------------------------------------------------------------------
# External Tool: Taskdog (Python MCP)
# ---------------------------------------------------------------------------

_taskdog_retry_config = RetryConfig(
    max_attempts=3,
    initial_backoff_s=0.5,
    max_backoff_s=8.0,
    backoff_multiplier=2.0,
    jitter=True,
)

_taskdog_cb_config = CircuitBreakerConfig(
    failure_threshold=5,
    reset_timeout_s=30.0,
)


@tool
@circuit_breaker("taskdog", _taskdog_cb_config)
@retry_with_backoff(
    name="taskdog_list_tasks",
    retryable_exceptions=(subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError),
    config=_taskdog_retry_config,
)
def taskdog_list_tasks(status: str | None = None, include_archived: bool = False) -> str:
    """List tasks from taskdog.

    Args:
        status: Filter by status (pending, done). Optional.
        include_archived: Include archived tasks. Defaults to False.

    Returns:
        Formatted task list or error message.
    """
    try:
        args = [_TASKDOG_CLI, "list"]
        if status:
            args.extend(["--status", status])
        if include_archived:
            args.append("--all")
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise ConnectionError(f"taskdog error: {result.stderr}")
        return result.stdout
    except FileNotFoundError as e:
        # Binary missing — return friendly message instead of crashing agent.invoke().
        return f"⚠️ taskdog unavailable (binary not found): {e}"
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("taskdog")
        raise
    except Exception as e:
        return f"⚠️ taskdog unavailable: {e}"


@tool
@circuit_breaker("taskdog", _taskdog_cb_config)
@retry_with_backoff(
    name="taskdog_create_task",
    retryable_exceptions=(subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError),
    config=_taskdog_retry_config,
)
def taskdog_create_task(name: str) -> str:
    """Create a new task in taskdog.

    Args:
        name: Task name.

    Returns:
        Confirmation message or error.
    """
    try:
        result = subprocess.run(
            [_TASKDOG_CLI, "add", name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ConnectionError(f"taskdog error: {result.stderr}")
        return result.stdout
    except FileNotFoundError as e:
        # Binary missing — return friendly message instead of crashing agent.invoke().
        return f"⚠️ taskdog unavailable (binary not found): {e}"
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("taskdog")
        raise
    except Exception as e:
        return f"⚠️ taskdog unavailable: {e}"


@tool
@circuit_breaker("taskdog", _taskdog_cb_config)
@retry_with_backoff(
    name="taskdog_complete_task",
    retryable_exceptions=(subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError),
    config=_taskdog_retry_config,
)
def taskdog_complete_task(task_id: int) -> str:
    """Mark a task as completed in taskdog.

    Args:
        task_id: Task ID to complete.

    Returns:
        Confirmation message or error.
    """
    try:
        result = subprocess.run(
            [_TASKDOG_CLI, "done", str(task_id)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ConnectionError(f"taskdog error: {result.stderr}")
        return result.stdout
    except FileNotFoundError as e:
        # Binary missing — return friendly message instead of crashing agent.invoke().
        return f"⚠️ taskdog unavailable (binary not found): {e}"
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("taskdog")
        raise
    except Exception as e:
        return f"⚠️ taskdog unavailable: {e}"


@tool
@circuit_breaker("taskdog", _taskdog_cb_config)
@retry_with_backoff(
    name="taskdog_get_task",
    retryable_exceptions=(subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError),
    config=_taskdog_retry_config,
)
def taskdog_get_task(task_id: int) -> str:
    """Get full task details from taskdog.

    Args:
        task_id: Task ID to retrieve.

    Returns:
        Task details or error message.
    """
    try:
        result = subprocess.run(
            [_TASKDOG_CLI, "show", str(task_id)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Note: taskdog 0.23.0 'show' has a known bug ('TaskdogApiClient has no attribute get_task_detail').
        # The error surfaces in stdout with non-zero returncode. Surface it as a string instead of
        # raising ConnectionError, which would trip the retry decorator + invoke-fallback path.
        if result.returncode != 0:
            return f"⚠️ taskdog show {task_id} unavailable: {(result.stderr or result.stdout).strip()}"
        return result.stdout
    except FileNotFoundError as e:
        # Binary missing — return friendly message instead of crashing agent.invoke().
        return f"⚠️ taskdog unavailable (binary not found): {e}"
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("taskdog")
        raise
    except Exception as e:
        return f"⚠️ taskdog unavailable: {e}"


# ---------------------------------------------------------------------------
# All tools as list (for create_deep_agent)
# ---------------------------------------------------------------------------
IKIGAI_TOOLS = [
    # Solverforge Calendar
    solverforge_list_events,
    solverforge_create_event,
    # Tuiboard kanban
    tuiboard_list_boards,
    tuiboard_get_tasks,
    tuiboard_update_task,
    tuiboard_create_task,
    # Taskdog task management
    taskdog_list_tasks,
    taskdog_create_task,
    taskdog_complete_task,
    taskdog_get_task,
]


# ---------------------------------------------------------------------------
# B7.3 — vault-grounded agent tools (appended; vault_write remains ONLY writer)
# ---------------------------------------------------------------------------
from .ikigai_read_strategics import ikigai_read_strategics  # noqa: E402
from .ikigai_read_vault import ikigai_read_vault  # noqa: E402

IKIGAI_TOOLS.extend(
    [
        ikigai_read_strategics,
        ikigai_read_vault,
    ]
)
