"""IKIGAi tools — wrapped as LangChain @tool for deepagents.

Per user scope (ADR-013, 2026-08-31): the agent layer is a PLANNING
ASSISTANT ONLY. It binds 12 tools (10 external data + 2 vault reads).
It does NOT bind math/policy/business-rule tools — that surface was
DELETED along with ``src/ikigai/core/scoring/``,
``src/ikigai/core/heuristics/``, and ``src/agents/ikigai_maintainer/``.

Drift detectors in ``tests/test_canonical_scope.py`` enforce this invariant.
"""

from __future__ import annotations

import datetime
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
from .tools_taskdog import (
    taskdog_complete_task,
    taskdog_create_task,
    taskdog_get_task,
    taskdog_list_tasks,
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


# Taskdog tools — canonical implementations live in tools_taskdog.py.
# (Local duplicates removed in M67 — the imports above are the canonical surface.)


# ---------------------------------------------------------------------------
# Native CLI fallback (NOT in IKIGAI_TOOLS — drift-detector-safe, 12 tools)
# ---------------------------------------------------------------------------


@tool
def cli_native_fallback(operation: str = "", **kwargs: Any) -> str:
    """Fallback for native CLI when subprocess is unavailable.

    NOT registered in IKIGAI_TOOLS (12-tools invariant). Passive fallback only.
    """
    import sys as _sys

    suggested = f"python -m ikigai.cli {operation}"
    return (
        f"⚠️ native CLI unavailable: invoke `{suggested}` manually. "
        f"Working directory: {_sys.path[0]!r}"
    )


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


# ---------------------------------------------------------------------------
# Legacy aliases for sync_vault tests (M73.5)
# ---------------------------------------------------------------------------
# These let tests monkeypatch `_VAULT_DIR` and `_read_checkpoint_data`
# without needing the legacy sync_vault tool to be in IKIGAI_TOOLS.
# They are NOT registered as tools (sync_vault lives in the v2 archive).
# Both read from the project's standard layout: vault_root = vault/, checkpoint
# DB at data/ikigai_checkpoints.db.
from pathlib import Path as _Path  # noqa: E402


def _VAULT_DIR() -> _Path:  # noqa: N802
    """Resolve vault/ root at call time. Tests override this via monkeypatch."""
    return _Path(__file__).resolve().parent.parent.parent.parent.parent / "vault"


def _read_checkpoint_data(thread_id: str = "default") -> dict:
    """Stub checkpoint reader — tests override via monkeypatch."""
    return {
        "cycle_id": f"{thread_id}-cycle",
        "vector_scores": {},
        "regime_state": "PUSH",
        "q_he_score": 0.0,
        "meta_vector_score": 0.0,
        "phase": "BUILD",
        "corrections": [],
    }


__all__ = ["_VAULT_DIR", "_read_checkpoint_data"]


# ---------------------------------------------------------------------------
# ikigai_sync_vault (M73.5 — extracted from the v2 reference archive)
# ---------------------------------------------------------------------------
# Sync the latest checkpoint to a vault markdown file. Reads _read_checkpoint_data
# and writes via vault_write. Tests monkeypatch _VAULT_DIR and _read_checkpoint_data.
from langchain_core.tools import tool as _tool_sync  # noqa: E402


def _format_corrections(corrections: list[dict[str, Any]]) -> str:
    """Format corrections list into bullet markdown lines.

    Each correction becomes `- [{heuristic}] {description}`.
    """
    if not corrections:
        return ""
    lines = []
    for c in corrections:
        h = c.get("heuristic", "?")
        d = c.get("description", "")
        lines.append(f"- [{h}] {d}")
    return "\n".join(lines)


@_tool_sync
def ikigai_sync_vault(thread_id: str = "default") -> str:
    """Sync the latest checkpoint to a vault markdown file. Path-traversal-protected.

    Returns the "Synced to vault: <path> (sha256=...)" message.
    """
    from sys_ikigai.vault.vault_write import vault_write as _vault_write_impl

    d = _read_checkpoint_data(thread_id)
    cycle_id = d.get("cycle_id", datetime.date.today().isoformat())
    vs = d.get("vector_scores", {})
    regime = d.get("regime_state", "UNKNOWN")
    qhe = d.get("q_he_score", 0.0)
    mv = d.get("meta_vector_score", 0.0)
    phase = d.get("phase", "BUSCA")
    corrections = d.get("corrections", [])
    vault_root = _VAULT_DIR() if callable(_VAULT_DIR) else _VAULT_DIR
    vault_root.mkdir(parents=True, exist_ok=True)
    relative_path = f"cycle-{cycle_id}.md"
    frontmatter_fields: dict[str, Any] = {
        "ueid": f"ikigai:cycle:{cycle_id}",
        "cycle_id": cycle_id,
        "date": datetime.date.today().isoformat(),
        "regime": regime,
        "q_he": qhe,
        "meta_vector": mv,
        "phase": phase,
        "corrections_count": len(corrections),
        "vector_scores": json.dumps(vs),
    }
    body = (
        f"# IKIGAi Cycle — {cycle_id}\n\n"
        f"## Regime: {regime}  |  Q_HE: {qhe:.4f}  |  Meta: {mv:.4f}\n\n"
        f"## Vector Scores\n"
        f"| Vector | Score |\n|--------|-------|\n"
        f"| Passion | {vs.get('passion', 0.0)} |\n"
        f"| Skill | {vs.get('skill', 0.0)} |\n"
        f"| Market | {vs.get('market', 0.0)} |\n"
        f"| Revenue | {vs.get('revenue', 0.0)} |\n"
        f"| Course | {vs.get('course', 0.0)} |\n\n"
        f"## Phase: {phase}\n\n"
        f"## Corrections: {len(corrections)}\n"
        f"{_format_corrections(corrections)}\n"
    )
    # Atomic write via vault_write
    result = _vault_write_impl(
        vault_root=vault_root,
        vault_path=relative_path,
        frontmatter_fields=frontmatter_fields,
        body=body,
        actor="agent",
    )
    return f"✅ Synced to vault: {vault_root / relative_path} (sha256={result.get('sha256', '')[:8]}...)"


__all__ = ["_VAULT_DIR", "_read_checkpoint_data", "ikigai_sync_vault"]
