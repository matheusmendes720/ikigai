"""Taskdog CLI fork tools (Python subprocess wrapper).

Per ADR-013: 4 fork tools that wrap `taskdog.exe` (Rust binary). These are
the canonical Path-1 tools for taskdog MCP — the canonical path per
taskdog-3-paths-architecture-canonical-2026-08-31.

Path 3 (taskdog MCP gateway) was DEFERRED until taskdog-mcp 0.23.0 venv
bug is fixed (MissingModuleError: taskdog_client — pipx-injection bug,
NOT in scope for this repo). The Path 1 subprocess tools in this module
are the canonical interface.

M67 (2026-09-18) — STRUCTURED-DATA REWRITE:
- All four tools now invoke `taskdog export --format json` (single
  JSON-encoded array of task dicts), parse with `json.loads`, and
  return `json.dumps(...)` — never raw stdout. LangChain deep-agents
  require structured data per the JSON tool-call contract.
- `taskdog_get_task(id)` filters the export list in-process (taskdog
  0.23.0 CLI has a known `show` bug — `'TaskdogApiClient' object has no
  attribute 'get_task_detail'`. We work around it via export+filter).
- `taskdog_create_task(name)` still uses `add` (only available verb).
- All four keep the retry + circuit-breaker on ConnectionError /
  Timeout / FileNotFoundError / OSError (drop on taskdog not installed).

Exposes (re-exported by tools.py):
- taskdog_list_tasks — list tasks (optionally filtered by status)
- taskdog_create_task — create new task (W3.6 side-effect — gated by
  invoke_skill outputs check)
- taskdog_complete_task — mark task done
- taskdog_get_task — fetch full task details (filter-from-export)

Companion modules:
- tools_sf — Solverforge Calendar fork (2 tools)
- tools_tuiboard — tuiboard Kanban fork (4 tools)
- tools — IKIGAI_TOOLS list (12 entries) + re-exports

Drift invariants enforced:
- test_canonical_scope :: test_ikigai_tools_count_is_12
- test_canonical_scope :: test_invoke_skill_guards_taskdog_call_with_outputs_check
  (taskdog_create_task gated by invoke_skill outputs check)
"""

from __future__ import annotations

import json
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


def _run_export(status_filter: str | None = None, include_archived: bool = False) -> list[dict]:
    """Run `taskdog export --format json` and parse to list[dict].

    Returns [] when taskdog is unavailable (binary not installed / server
    not reachable). Caller is responsible for translating to a tool result.
    """
    args = [_TASKDOG_CLI, "export", "--format", "json"]
    if status_filter:
        args.extend(["--status", status_filter])
    if include_archived:
        args.append("--all")
    proc = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise ConnectionError(f"taskdog error: {(proc.stderr or proc.stdout).strip()}")
    if not proc.stdout.strip():
        return []
    return json.loads(proc.stdout)


def _missing_taskdog_msg(err: Exception) -> str:
    """Stable error envelope when taskdog binary / server unreachable."""
    return json.dumps({"ok": False, "error": f"taskdog unavailable: {err!s}"})


@tool
@circuit_breaker("taskdog", _taskdog_cb_config)
@retry_with_backoff(
    name="taskdog_list_tasks",
    retryable_exceptions=(subprocess.TimeoutExpired, ConnectionError, OSError),
    config=_taskdog_retry_config,
)
def taskdog_list_tasks(
    status: str | None = None, include_archived: bool = False
) -> str:
    """List tasks from taskdog. Returns a JSON envelope with `tasks` array.

    Args:
        status: Filter by status (pending, in_progress, completed, canceled). Optional.
        include_archived: Include archived tasks. Defaults to False.

    Returns:
        JSON string: {"ok": true, "count": N, "tasks": [{...}, ...]}
        or        {"ok": false, "error": "..."} on infrastructure failure.
    """
    try:
        tasks = _run_export(status_filter=status, include_archived=include_archived)
        return json.dumps({"ok": True, "count": len(tasks), "tasks": tasks})
    except FileNotFoundError as e:
        return _missing_taskdog_msg(e)
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("taskdog")
        raise
    except Exception as e:
        return _missing_taskdog_msg(e)


@tool
@circuit_breaker("taskdog", _taskdog_cb_config)
@retry_with_backoff(
    name="taskdog_create_task",
    retryable_exceptions=(subprocess.TimeoutExpired, ConnectionError, OSError),
    config=_taskdog_retry_config,
)
def taskdog_create_task(name: str) -> str:
    """Create a new task in taskdog.

    Args:
        name: Task name.

    Returns:
        JSON string: {"ok": true, "id": <int>, "name": "...", "raw": "stdout"} on success;
        or          {"ok": false, "error": "..."} on failure.

    Side-effect note: gated by invoke_skill outputs check (W3.6). The
    deepagents_harness / proposal_executor.py lazy-proxy this tool.
    """
    try:
        proc = subprocess.run(
            [_TASKDOG_CLI, "add", name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            raise ConnectionError(f"taskdog error: {(proc.stderr or proc.stdout).strip()}")
        # Extract ID from the success line — taskdog prints "(ID: <int>)".
        task_id = None
        import re as _re
        m = _re.search(r"\(\s*ID\s*:\s*(\d+)\s*\)", proc.stdout)
        if m:
            task_id = int(m.group(1))
        return json.dumps({
            "ok": True,
            "id": task_id,
            "name": name,
            "raw": proc.stdout.strip(),
        })
    except FileNotFoundError as e:
        return _missing_taskdog_msg(e)
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("taskdog")
        raise
    except Exception as e:
        return _missing_taskdog_msg(e)


@tool
@circuit_breaker("taskdog", _taskdog_cb_config)
@retry_with_backoff(
    name="taskdog_complete_task",
    retryable_exceptions=(subprocess.TimeoutExpired, ConnectionError, OSError),
    config=_taskdog_retry_config,
)
def taskdog_complete_task(task_id: int) -> str:
    """Mark a task as completed in taskdog.

    Args:
        task_id: Task ID to complete.

    Returns:
        JSON string: {"ok": true, "task_id": <int>, "started": <bool>, "raw": "stdout"} on success;
        or          {"ok": false, "error": "..."} on failure.

    M69 (2026-09-18): AUTO-START WORKAROUND
        taskdog 0.23.0 enforces a PENDING -> IN_PROGRESS -> COMPLETED state
        machine. Calling `done` on a PENDING task returns "task is PENDING.
        Start the task first with 'taskdog start <id>'". To make the deep-agent
        workflow ergonomic, we detect the PENDING error and transparently
        call `start` first, then retry `done`. Idempotent — if the task is
        already IN_PROGRESS, the start call is a no-op (or surfaces "task is
        IN_PROGRESS" which we ignore on the second attempt).
    """
    # Helper: 1-shot run for the `done` or `start` subcommand
    def _run(subcmd: str) -> tuple[int, str, str]:
        proc = subprocess.run(
            [_TASKDOG_CLI, subcmd, str(task_id)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.returncode, proc.stdout, proc.stderr

    try:
        # First attempt: `done`
        rc, out, err = _run("done")
        if rc == 0:
            return json.dumps({"ok": True, "task_id": task_id, "started": False, "raw": out.strip()})

        # Detect the PENDING guard
        err_msg = (err or out or "").strip()
        if "PENDING" in err_msg and "Start" in err_msg:
            # Auto-start: PENDING -> IN_PROGRESS
            start_rc, start_out, start_err = _run("start")
            if start_rc != 0:
                raise ConnectionError(
                    f"taskdog auto-start failed for task {task_id}: "
                    f"{(start_err or start_out).strip()}"
                )
            # Retry the done
            rc, out, err = _run("done")
            if rc == 0:
                return json.dumps({
                    "ok": True, "task_id": task_id,
                    "started": True, "raw": out.strip(),
                    "auto_started": True,
                })
            # Still failed — surface the new error
            err_msg = (err or out or "").strip()
            raise ConnectionError(f"taskdog error after auto-start: {err_msg}")

        # Other terminal error (already-done, archived, etc.)
        raise ConnectionError(f"taskdog error: {err_msg}")
    except FileNotFoundError as e:
        return _missing_taskdog_msg(e)
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("taskdog")
        raise
    except Exception as e:
        return _missing_taskdog_msg(e)


@tool
@circuit_breaker("taskdog", _taskdog_cb_config)
@retry_with_backoff(
    name="taskdog_get_task",
    retryable_exceptions=(subprocess.TimeoutExpired, ConnectionError, OSError),
    config=_taskdog_retry_config,
)
def taskdog_get_task(task_id: int) -> str:
    """Get full task details from taskdog (via export + in-process filter).

    Args:
        task_id: Task ID to retrieve.

    Returns:
        JSON string: {"ok": true, "task": {...}} if found;
        or          {"ok": false, "error": "not found"} if not.
        or          {"ok": false, "error": "..."} on infrastructure failure.

    Note: taskdog 0.23.0 `show` command has a bug ('TaskdogApiClient has
    no attribute get_task_detail'); we filter the export list instead.
    """
    try:
        tasks = _run_export()
        match = next((t for t in tasks if t.get("id") == task_id), None)
        if match is None:
            return json.dumps({"ok": False, "error": f"task {task_id} not found"})
        return json.dumps({"ok": True, "task": match})
    except FileNotFoundError as e:
        return _missing_taskdog_msg(e)
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("taskdog")
        raise
    except Exception as e:
        return _missing_taskdog_msg(e)


__all__ = [
    "taskdog_complete_task",
    "taskdog_create_task",
    "taskdog_get_task",
    "taskdog_list_tasks",
]
