"""Taskdog CLI fork tools (Python subprocess wrapper).

Per user scope (ADR-013): 4 fork tools that wrap taskdog.exe (Rust
binary). These are the canonical Path-1 tools for taskdog MCP — the
canonical path per taskdog-3-paths-architecture-canonical-2026-08-31.

Path 3 (taskdog MCP gateway) was DEFERRED until taskdog_mcp.server
module exists. The Path 1 subprocess tools in this module are the
canonical interface.

Exposes (re-exported by tools.py):
- ``taskdog_list_tasks`` — list tasks (optionally filtered by status)
- ``taskdog_create_task`` — create new task (W3.6 side-effect — gated
  by invoke_skill() outputs check)
- ``taskdog_complete_task`` — mark task done
- ``taskdog_get_task`` — fetch full task details

Companion modules:
- ``tools_sf`` — Solverforge Calendar fork (2 tools)
- ``tools_tuiboard`` — tuiboard Kanban fork (4 tools)
- ``tools`` — IKIGAI_TOOLS list (12 entries) + re-exports

Architectural reference:
- ADR-013 — planner-only; 4 of 10 external data tools
- taskdog-3-paths-architecture-canonical-2026-08-31 — Path 1 is CANONICAL

Drift invariants enforced:
- test_canonical_scope :: test_ikigai_tools_count_is_12
- test_canonical_scope :: test_invoke_skill_guards_taskdog_call_with_outputs_check
  (taskdog_create_task gated by invoke_skill outputs check)
"""

from __future__ import annotations

import os
import subprocess

from langchain_core.tools import tool

from .reliability import (
    CircuitBreakerConfig,
    RetryConfig,
    circuit_breaker,
    invalidate_session_cache,
    retry_with_backoff,
)

# Taskdog CLI path (configurable via env var)
_TASKDOG_CLI = os.environ.get("TASKDOG_CLI", "taskdog.exe")

# Retry + circuit breaker for taskdog
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

    Side-effect note: gated by invoke_skill() outputs check (W3.6) —
    deepagents_harness / proposal_executor.py lazy-proxy this tool
    and consults the skill manifest's outputs list before invoking it.
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
            return (
                f"⚠️ taskdog show {task_id} unavailable: {(result.stderr or result.stdout).strip()}"
            )
        return result.stdout
    except FileNotFoundError as e:
        return f"⚠️ taskdog unavailable (binary not found): {e}"
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("taskdog")
        raise
    except Exception as e:
        return f"⚠️ taskdog unavailable: {e}"


__all__ = [
    "taskdog_complete_task",
    "taskdog_create_task",
    "taskdog_get_task",
    "taskdog_list_tasks",
]
