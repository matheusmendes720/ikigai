"""IKIGAi tools — wrapped as LangChain @tool for deepagents.

Each tool is a clean function with docstring + TypedDict return type.
These are the 8 operations the conversational agent can call.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Literal

from langchain_core.tools import tool

from .reliability import (
    RetryConfig,
    CircuitBreakerConfig,
    retry_with_backoff,
    circuit_breaker,
    invalidate_session_cache,
    CircuitOpenError,
    _set_cache_ref,
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

# Project-local defaults (avoid ~/.ikigai/ — Windows-lock risk per audit B5.0-F10).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_CHECKPOINT_DB = str(_PROJECT_ROOT / "data" / "ikigai_checkpoints.db")
_VAULT_DIR = _PROJECT_ROOT / "vault"


def _get_checkpoint_path() -> Path:
    p = Path(_CHECKPOINT_DB)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _read_checkpoint_data(thread_id: str = "default") -> dict[str, Any]:
    """Read latest checkpoint for a thread.

    langgraph stores state in checkpoint['channel_values'].
    """
    p = _get_checkpoint_path()
    if not p.exists():
        return {}
    import msgpack

    conn = sqlite3.connect(str(p))
    cur = conn.cursor()
    cur.execute(
        """
        SELECT checkpoint FROM checkpoints
        WHERE thread_id = ?
        ORDER BY checkpoint_id DESC LIMIT 1
        """,
        (thread_id,),
    )
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        try:
            data = msgpack.unpackb(row[0])
            # langgraph wraps state in channel_values
            return data.get("channel_values", data)
        except Exception:
            return {}
    return {}


# ---------------------------------------------------------------------------
# Tool 1: score — 5-vector scores + meta-vector
# ---------------------------------------------------------------------------


@tool
def ikigai_score(thread_id: str = "default") -> str:
    """Get current IKIGAi 5-vector scores (passion, skill, market, revenue, course)
    and the meta-vector composite score.

    Args:
        thread_id: Checkpoint thread to read from. Defaults to "default".

    Returns:
        Formatted table of vector scores with ASCII bar charts.
    """
    d = _read_checkpoint_data(thread_id)
    vs = d.get("vector_scores", {})
    mv = d.get("meta_vector_score", 0.0)
    qhe = d.get("q_he_score", 0.0)

    if not vs:
        return "⚠️ No vector scores found in checkpoint. Run `plan` first."

    lines = [f"**IKIGAi Scores**  (meta: {mv:.4f}  Q_HE: {qhe:.4f})", ""]
    for vec in ("passion", "skill", "market", "revenue", "course"):
        v = vs.get(vec, 0.0)
        bar = "█" * int(v / 10) + "░" * (10 - int(v / 10))
        lines.append(f"  {vec.capitalize():12s} [{bar}] {v:.1f}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 2: regime — regime state, Q_HE, days in regime
# ---------------------------------------------------------------------------


@tool
def ikigai_regime(thread_id: str = "default") -> str:
    """Get current IKIGAi regime state (PUSH / MAINTAIN / REDUCE / RECOVER),
    Q_HE score, and days-in-regime counter.

    Args:
        thread_id: Checkpoint thread to read from. Defaults to "default".

    Returns:
        One-line regime status with emoji indicator.
    """
    d = _read_checkpoint_data(thread_id)
    regime = d.get("regime_state", "MAINTAIN")
    days = d.get("days_in_regime", 0)
    qhe = d.get("q_he_score", 0.65)

    emoji = {
        "PUSH": "🔴",
        "MAINTAIN": "🟡",
        "REDUCE": "🟠",
        "RECOVER": "🟢",
    }.get(regime, "⚪")

    return f"{emoji} **Regime: {regime}**  |  Q_HE: {qhe:.4f}  |  Days: {days}"


# ---------------------------------------------------------------------------
# Tool 3: phase — current phase and weight distribution
# ---------------------------------------------------------------------------


@tool
def ikigai_phase(thread_id: str = "default") -> str:
    """Get current IKIGAi phase (FUNDAÇÃO / BUSCA / HACKATHON / RECUPERACAO / OVERCLOCK)
    and the 5-vector weight distribution.

    Args:
        thread_id: Checkpoint thread to read from. Defaults to "default".

    Returns:
        Phase name with iteration count and weight table.
    """
    d = _read_checkpoint_data(thread_id)
    phase = d.get("phase", "BUSCA")
    pi = d.get("phase_iteration", 0)
    converged = d.get("phase_converged", False)
    pw = d.get("phase_weights", {})

    emoji = {
        "FUNDAÇÃO": "🏗️",
        "BUSCA": "🔍",
        "HACKATHON": "⚡",
        "RECUPERACAO": "🔧",
        "OVERCLOCK": "🔥",
    }.get(phase, "❓")

    lines = [
        f"{emoji} **Phase: {phase}**  iter={pi}  converged={converged}",
        "",
        "Weights:",
    ]
    for k, v in pw.items():
        lines.append(f"  {k.capitalize():12s}: {v:.2f}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 4: corrections — H1-H6 heuristic signals
# ---------------------------------------------------------------------------


@tool
def ikigai_corrections(thread_id: str = "default") -> str:
    """Get active IKIGAi correction signals from H1-H6 heuristics.

    Returns the most recent correction signals emitted by the regime FSM,
    phase FSM, and balance heuristics.

    Args:
        thread_id: Checkpoint thread to read from. Defaults to "default".

    Returns:
        List of correction signals with heuristic tags and descriptions.
    """
    d = _read_checkpoint_data(thread_id)
    corrs = d.get("corrections", [])

    if not corrs:
        return "✅ No corrections — system is balanced."

    lines = [f"**Corrections ({len(corrs)})**", ""]
    for c in corrs[-5:]:
        lines.append(f"  [{c.get('heuristic', '?')}] {c.get('description', '')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 5: decompose — UEID hierarchy (dream → goal → objective → project)
# ---------------------------------------------------------------------------


@tool
def ikigai_decompose(ueid: str, thread_id: str = "default") -> str:
    """Decompose a UEID into its full hierarchy:
    Dream → Objectives → Projects → Tasks.

    Args:
        ueid: Full UEID to decompose (e.g. "ikigai:dream:vaga-remota-2026").
        thread_id: Checkpoint thread to read from. Defaults to "default".

    Returns:
        Formatted hierarchy tree with status for each level.
    """
    if not ueid:
        return "⚠️ Provide a UEID, e.g. `ikigai_decompose(ueid='ikigai:dream:vaga-remota-2026')`"

    # Try to decompose via the existing mcp_server helper
    try:
        from mcp_server.server import _decompose_ueid

        result = _decompose_ueid(ueid)
        dream = result.get("dream", {})
        objectives = result.get("objectives", [])
        projects = result.get("projects", [])

        lines = [
            f"**Dream:** {dream.get('title', dream.get('slug', ueid))}  [{dream.get('status', '?')}]",
            "",
        ]
        if objectives:
            lines.append(f"  Objectives ({len(objectives)}):")
            for o in objectives:
                lines.append(f"    • {o.get('title', '?')}  [{o.get('status', '?')}]")
        if projects:
            lines.append(f"  Projects ({len(projects)}):")
            for p in projects:
                lines.append(f"    • {p.get('title', '?')}  [{p.get('status', '?')}]")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Could not decompose UEID: {e}"


# ---------------------------------------------------------------------------
# Tool 6: plan_cycle — run full IKIGAi agent cycle
# ---------------------------------------------------------------------------


@tool
def ikigai_plan_cycle(thread_id: str = "default") -> str:
    """Run one full IKIGAi strategic planning cycle.

    Executes the 8-node LangGraph: observe → score_vectors → heuristics
    → balance → decompose → plan → reflect → commit.

    Uses SqliteSaver checkpointing. Results are persisted and resumable.

    Args:
        thread_id: Thread ID for checkpointing. Defaults to "default".

    Returns:
        Summary of the completed cycle: regime, Q_HE, corrections, buffers.
    """
    import datetime as _dt
    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P(__file__).parent.parent.parent / "src"))
    from agents.ikigai_maintainer import make_ikigai_graph

    today = _dt.date.today()
    graph = make_ikigai_graph(checkpoint_db=_CHECKPOINT_DB)
    config = {"configurable": {"thread_id": thread_id}}

    initial = {
        "cycle_id": today.isoformat(),
        "cycle_start": today.isoformat(),
        "cycle_end": (today + _dt.timedelta(days=45)).isoformat(),
        "iteration": 0,
        "last_step": "",
        "regime_state": "MAINTAIN",
        "q_he_score": 0.65,
        "days_in_regime": 1,
        "is_hysteresis_active": False,
        "phase": "BUSCA",
        "phase_iteration": 0,
        "phase_converged": False,
        "phase_weights": {
            "passion": 0.15,
            "skill": 0.25,
            "market": 0.25,
            "revenue": 0.20,
            "course": 0.15,
        },
        "vector_scores": {},
        "meta_vector_score": 0.0,
        "active_dream_ueid": None,
        "active_goal_ueids": [],
        "active_objective_ueids": [],
        "active_project_ueids": [],
        "active_task_ueids": [],
        "workload_estimate": 2.0,
        "capacity_estimate": 8.0,
        "balancer_verdict": "OK",
        "prospective_buffer": [],
        "retrospective_log": [],
        "corrections": [],
        "kill_switch_triggered": False,
        "terminated": False,
    }

    final = graph.invoke(initial, config)
    vs = final.get("vector_scores", {})
    mv = final.get("meta_vector_score", 0.0)
    regime = final.get("regime_state", "?")
    qhe = final.get("q_he_score", 0.0)
    corrections = final.get("corrections", [])
    prospective = final.get("prospective_buffer", [])
    retrospective = final.get("retrospective_log", [])

    return (
        f"✅ Plan cycle complete\n"
        f"   Regime: {regime}  |  Q_HE: {qhe:.4f}  |  Meta: {mv:.4f}\n"
        f"   Vectors: {len(vs)} scored\n"
        f"   Corrections: {len(corrections)}  |  Prospective: {len(prospective)}  |  Retrospective: {len(retrospective)}"
    )


# ---------------------------------------------------------------------------
# Tool 7: sync_vault — write cycle checkpoint to vault markdown
# ---------------------------------------------------------------------------


@tool
def ikigai_sync_vault(thread_id: str = "default") -> str:
    """Sync the latest checkpoint to a vault markdown file.

    Writes a cycle log to ~/.ikigai/vault/cycle-YYYY-MM-DD.md
    with current vector scores, regime, phase, and corrections.

    Args:
        thread_id: Checkpoint thread to read from. Defaults to "default".

    Returns:
        Path to the written vault file.
    """
    import datetime as _dt

    d = _read_checkpoint_data(thread_id)
    cycle_id = d.get("cycle_id", _dt.date.today().isoformat())
    vs = d.get("vector_scores", {})
    regime = d.get("regime_state", "UNKNOWN")
    qhe = d.get("q_he_score", 0.0)
    mv = d.get("meta_vector_score", 0.0)
    phase = d.get("phase", "BUSCA")
    corrections = d.get("corrections", [])

    vault_dir = _VAULT_DIR
    vault_dir.mkdir(parents=True, exist_ok=True)
    log_file = vault_dir / f"cycle-{cycle_id}.md"

    content = f"""---
ueid: ikigai:cycle:{cycle_id}
cycle_id: {cycle_id}
date: {_dt.date.today().isoformat()}
regime: {regime}
q_he: {qhe}
meta_vector: {mv}
phase: {phase}
corrections_count: {len(corrections)}
vector_scores: {json.dumps(vs)}
---

# IKIGAi Cycle — {cycle_id}

## Regime: {regime}  |  Q_HE: {qhe:.4f}  |  Meta: {mv:.4f}

## Vector Scores
| Vector | Score |
|--------|-------|
| Passion | {vs.get('passion', 0.0)} |
| Skill | {vs.get('skill', 0.0)} |
| Market | {vs.get('market', 0.0)} |
| Revenue | {vs.get('revenue', 0.0)} |
| Course | {vs.get('course', 0.0)} |

## Phase: {phase}

## Corrections: {len(corrections)}
{''.join(f"- [{c.get('heuristic','?')}] {c.get('description','')}\n" for c in corrections[-5:]) if corrections else '_None_'}
"""
    log_file.write_text(content, encoding="utf-8")
    return f"✅ Synced to vault: {log_file}"


# ---------------------------------------------------------------------------
# Tool 8: checkpoint — list / get / set checkpoint state
# ---------------------------------------------------------------------------


@tool
def ikigai_checkpoint(
    action: Literal["list", "get", "state"] = "list",
    thread_id: str = "default",
) -> str:
    """Manage IKIGAi checkpoint state.

    - list: Show all recent checkpoint threads
    - get: Show current state for a thread
    - state: Return full state dict as JSON string

    Args:
        action: One of "list", "get", or "state". Defaults to "list".
        thread_id: Thread to operate on. Defaults to "default".

    Returns:
        Checkpoint info in requested format.
    """
    p = _get_checkpoint_path()
    if not p.exists():
        return "⚠️ No checkpoint DB found. Run `plan_cycle` first."

    conn = sqlite3.connect(str(p))
    cur = conn.cursor()

    if action == "list":
        cur.execute(
            "SELECT thread_id, checkpoint_ns, checkpoint_id FROM checkpoints "
            "ORDER BY checkpoint_id DESC LIMIT 20"
        )
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return "No checkpoints found."
        lines = [f"**Checkpoints ({len(rows)}):**", ""]
        for r in rows:
            lines.append(f"  • {r[0]}  [{r[1]}]  {r[2]}")
        return "\n".join(lines)

    if action in ("get", "state"):
        cur.execute(
            "SELECT checkpoint FROM checkpoints "
            "WHERE thread_id = ? ORDER BY checkpoint_id DESC LIMIT 1",
            (thread_id,),
        )
        row = cur.fetchone()
        conn.close()
        if not row or not row[0]:
            return f"No checkpoint found for thread '{thread_id}'."
        try:
            import msgpack

            data = msgpack.unpackb(row[0])
            data = data.get("channel_values", data)
        except Exception:
            data = {}
        if action == "get":
            summary = [
                f"cycle_id:    {data.get('cycle_id', '?')}",
                f"regime:      {data.get('regime_state', '?')}  Q_HE={data.get('q_he_score', 0):.4f}",
                f"phase:       {data.get('phase', '?')}  iter={data.get('phase_iteration', 0)}",
                f"verdict:     {data.get('balancer_verdict', '?')}",
                f"meta-vector: {data.get('meta_vector_score', 0):.4f}",
                f"corrections: {len(data.get('corrections', []))}",
            ]
            return "\n".join(summary)
        # state — return JSON
        import copy

        serializable = {}
        for k, v in data.items():
            try:
                json.dumps(v)
                serializable[k] = v
            except (TypeError, ValueError):
                serializable[k] = str(v)
        return json.dumps(serializable, indent=2)

    conn.close()
    return f"Unknown action: {action}"


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
    except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
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
            [_SOLVERFORGE_CLI, "events", "create", "--title", title, "--date", date, "--time", time],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ConnectionError(f"solverforge error: {result.stderr}")
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
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


def _tuiboard_rpc(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a JSON-RPC call to tuiboard MCP over stdio."""
    import json

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
    except json.JSONDecodeError:
        raise ConnectionError(f"tuiboard invalid response: {result.stdout}")

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
    except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
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
def tuiboard_get_tasks(board_path: str, column: int | None = None, filter: str = "all") -> str:
    """Get tasks from a tuiboard kanban board.

    Args:
        board_path: Path to the markdown board file.
        column: Optional column index to filter by.
        filter: Filter type (all, pending, done). Defaults to "all".

    Returns:
        Formatted task list or error message.
    """
    try:
        result = _tuiboard_rpc("get_tasks", {"board_path": board_path, "column": column, "filter": filter})
        if not result:
            return "⚠️ No tasks found"
        lines = [f"**Tasks from {board_path}:**", ""]
        for task in result:
            status = "✅" if task.get("done") else "⬜"
            lines.append(f"  {status} {task.get('title', 'untitled')} [{task.get('priority', '?')}]")
        return "\n".join(lines)
    except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
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
        result = _tuiboard_rpc("create_task", {"board_path": board_path, "title": title, "column": column})
        return f"✅ Task created: {result.get('id', 'unknown')}"
    except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
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
        params = {"board_path": board_path, "task_id": task_id}
        if done is not None:
            params["done"] = done
        if priority is not None:
            params["priority"] = priority
        if tags is not None:
            params["tags"] = tags
        result = _tuiboard_rpc("update_task", params)
        return f"✅ Task updated: {task_id}"
    except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
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
            args.append("--include-archived")
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise ConnectionError(f"taskdog error: {result.stderr}")
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
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
            [_TASKDOG_CLI, "create", "--name", name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ConnectionError(f"taskdog error: {result.stderr}")
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
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
            [_TASKDOG_CLI, "complete", str(task_id)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ConnectionError(f"taskdog error: {result.stderr}")
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
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
            [_TASKDOG_CLI, "get", str(task_id)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ConnectionError(f"taskdog error: {result.stderr}")
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError):
        invalidate_session_cache("taskdog")
        raise
    except Exception as e:
        return f"⚠️ taskdog unavailable: {e}"


# ---------------------------------------------------------------------------
# All tools as list (for create_deep_agent)
# ---------------------------------------------------------------------------
IKIGAI_TOOLS = [
    # IKIGAi internal tools
    ikigai_score,
    ikigai_regime,
    ikigai_phase,
    ikigai_corrections,
    ikigai_decompose,
    ikigai_plan_cycle,
    ikigai_sync_vault,
    ikigai_checkpoint,
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
