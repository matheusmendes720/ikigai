"""IKIGAi-Maintainer MCP server — 8 tools via stdio transport.

Run with: python run_mcp_server.py
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any, Annotated

from mcp.server.fastmcp import FastMCP

from mcp_server.tracing import init_mcp_tracing, traced_tool_dispatch


# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
MCP = FastMCP("ikigai-gateway")

# Initialize OpenTelemetry tracing (idempotent)
init_mcp_tracing()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def _db_path(suffix: str = "ikigai_checkpoints.db") -> Path:
    return Path.home() / ".ikigai" / suffix


def _decompose_ueid(ueid: str) -> dict[str, Any]:
    """Traverse the vault hierarchy for a given Dream UEID.

    Vault root: {repo}/data/matheus/
    Structure: dreams/ → objectives/ → projects/ → tasks/
    """
    import frontmatter
    import re

    repo_root = Path(__file__).parent.parent.parent  # .../src/ikigai/src/mcp_server/ → src/ikigai/
    vault_root = repo_root / "data" / "matheus"

    def _slug_from_ueid(ueid: str) -> str:
        """Extract slug from UEID like ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609."""
        parts = ueid.split(":")
        return parts[2] if len(parts) >= 3 else ""

    def _read_entity(dir_name: str, slug: str) -> list[dict[str, Any]]:
        """Read all frontmatter records from a vault subdirectory."""
        entity_dir = vault_root / dir_name
        results = []
        if not entity_dir.is_dir():
            return results
        for md_file in entity_dir.iterdir():
            if not md_file.suffix == ".md":
                continue
            try:
                post = frontmatter.loads(md_file.read_text(encoding="utf-8"))
                results.append({
                    "file": str(md_file.relative_to(vault_root)),
                    "ueid": post.metadata.get("ueid", ""),
                    "title": post.metadata.get("title", md_file.stem),
                    "status": post.metadata.get("status", "UNKNOWN"),
                    "slug": post.metadata.get("slug", md_file.stem),
                    "parent_ueid": post.metadata.get("parent_ueid"),
                    "related_ueids": post.metadata.get("related_ueids", []),
                })
            except Exception:
                pass
        return results

    def _children(ueid: str, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [e for e in entities if e.get("parent_ueid") == ueid]

    dream_slug = _slug_from_ueid(ueid)
    dream_file = vault_root / "dreams" / f"{dream_slug}.md"

    # Read dream
    dream_data = {}
    if dream_file.exists():
        try:
            post = frontmatter.loads(dream_file.read_text(encoding="utf-8"))
            dream_data = {
                "file": f"dreams/{dream_slug}.md",
                "ueid": post.metadata.get("ueid", ueid),
                "title": post.metadata.get("title", dream_slug),
                "status": post.metadata.get("status", "UNKNOWN"),
                "slug": post.metadata.get("slug", dream_slug),
            }
        except Exception:
            pass

    # Read all objectives / projects / tasks
    objectives = _read_entity("objectives", dream_slug)
    projects = _read_entity("projects", dream_slug)

    # Filter objectives to those whose parent_ueid or related_ueids match this dream
    dream_objectives = [o for o in objectives if o.get("parent_ueid") == ueid or ueid in o.get("related_ueids", [])]
    dream_projects = [p for p in projects if p.get("parent_ueid") in [o.get("ueid") for o in dream_objectives]]

    return {
        "dream": dream_data,
        "goals": [],  # goals not yet in vault
        "objectives": dream_objectives,
        "projects": dream_projects,
        "tasks": [],  # tasks not yet in vault
    }


def _read_checkpoint(thread_id: str | None = None) -> dict[str, Any]:
    """Read latest checkpoint from LangGraph SQLite.

    LangGraph schema: thread_id, checkpoint_ns, checkpoint_id, checkpoint (BLOB), metadata (BLOB).
    Ordered by checkpoint_id DESC (contains nanosecond timestamp).
    """
    path = _db_path()
    if not path.exists():
        return {}
    try:
        import pickle
        conn = sqlite3.connect(str(path))
        cur = conn.cursor()
        if thread_id:
            cur.execute(
                "SELECT checkpoint FROM checkpoints WHERE thread_id = ? ORDER BY checkpoint_id DESC LIMIT 1",
                (thread_id,),
            )
        else:
            cur.execute("SELECT checkpoint FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            return pickle.loads(row[0]) or {}
        return {}
    except Exception:
        return {}


def _read_plan_entity(cycle_id: str) -> dict[str, Any]:
    """Read cycle state from plan_entities.db (written by ikigai_plan_cycle)."""
    plan_db = Path.home() / ".ikigai" / "plan_entities.db"
    if not plan_db.exists():
        return {}
    try:
        conn = sqlite3.connect(str(plan_db))
        cur = conn.cursor()
        cur.execute("SELECT * FROM plan_entities WHERE cycle_id = ? ORDER BY created_at DESC LIMIT 1", (cycle_id,))
        row = cur.fetchone()
        cols = [d[0] for d in cur.description] if cur.description else []
        conn.close()
        return dict(zip(cols, row)) if row else {}
    except Exception:
        return {}


def _read_entity(table: str) -> dict[str, Any]:
    path = Path.home() / ".ikigai" / "plan_entities.db"
    if not path.exists():
        return {}
    try:
        conn = sqlite3.connect(str(path))
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if not row:
            return {}
        cols = [d[0] for d in cur.description or []]
        return dict(zip(cols, row))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Task I/O — Deep Agent ↔ interfaces via data/tasks.jsonl
# ---------------------------------------------------------------------------

def _tasks_path() -> Path:
    """Path to the shared tasks file. Lives in data/ at repo root."""
    repo_root = Path(__file__).parent.parent.parent.parent  # .../src/ikigai/src/ → repo root
    return repo_root / "data" / "tasks.jsonl"


def _write_tasks_to_data(tasks: list[dict]) -> str:
    """Append structured tasks (from Deep Agent) to data/tasks.jsonl.

    Each line is a JSON object with a uuid, timestamp, and the task fields.
    Returns a summary of what was written.
    """
    import uuid as _uuid

    path = _tasks_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    now = dt.datetime.utcnow().isoformat()
    with path.open("a", encoding="utf-8") as fh:
        for t in tasks:
            record = {
                "id": str(_uuid.uuid4())[:8],
                "written_at": now,
                "source": "deep_agent",
                "title": t.get("title", ""),
                "description": t.get("description", ""),
                "horizon": t.get("horizon", "this_week"),
                "priority": t.get("priority", "medium"),
                "project_id": t.get("project_id"),
                "estimated_minutes": t.get("estimated_minutes"),
                "done": False,
                "done_at": None,
                "ueid": t.get("ueid"),
                "vector": t.get("vector"),
                "due": t.get("due"),
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

    return json.dumps({"ok": True, "written": written, "path": str(path)})


def _read_tasks_from_data(
    horizon: str | None = None,
    done: bool | None = None,
    project_id: str | None = None,
    limit: int = 50,
) -> str:
    """Read tasks from data/tasks.jsonl, optionally filtered.

    Returns a JSON array of task objects.
    """
    path = _tasks_path()
    if not path.exists():
        return json.dumps([])

    results = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    task = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # Apply filters
                if horizon is not None and task.get("horizon") != horizon:
                    continue
                if done is not None and task.get("done") != done:
                    continue
                if project_id is not None and task.get("project_id") != project_id:
                    continue
                results.append(task)
                if len(results) >= limit:
                    break
    except OSError:
        return json.dumps([])

    return json.dumps(results, indent=2)


# ---------------------------------------------------------------------------
# Tool handler functions (for traced dispatch)
# ---------------------------------------------------------------------------

def _handle_ikigai_score(arguments: dict[str, Any]) -> str:
    d = _read_checkpoint()
    vs = d.get("vector_scores", {})
    mv = d.get("meta_vector_score", 0.0)
    qhe = d.get("q_he_score")
    if not vs:
        row = _read_entity("plan_entities")
        if row:
            vs = {k: row.get(k, 0.0) for k in ("passion", "skill", "market", "revenue", "course")}
            mv = row.get("meta_vector", 0.0)
            qhe = row.get("q_he")
    return json.dumps({"vector_scores": vs, "meta_vector_score": round(mv, 4), "q_he_score": qhe}, indent=2)


def _handle_ikigai_regime(arguments: dict[str, Any]) -> str:
    d = _read_checkpoint()
    regime = d.get("regime_state", "MAINTAIN")
    days = d.get("days_in_regime", 0)
    qhe = d.get("q_he_score")
    if not d:
        row = _read_entity("plan_entities")
        if row:
            regime = row.get("regime", regime)
            qhe = row.get("q_he", qhe)
    return json.dumps({"regime_state": regime, "days_in_regime": days, "q_he_score": qhe}, indent=2)


def _handle_ikigai_phase(arguments: dict[str, Any]) -> str:
    d = _read_checkpoint()
    return json.dumps({
        "phase": d.get("phase", "BUSCA"),
        "phase_iteration": d.get("phase_iteration", 0),
        "phase_converged": d.get("phase_converged", False),
        "phase_weights": d.get("phase_weights", {}),
    }, indent=2)


def _handle_ikigai_decompose(arguments: dict[str, Any]) -> str:
    ueid = arguments.get("dream_ueid", "")
    if not ueid:
        return json.dumps({"error": "dream_ueid required"})
    return json.dumps(_decompose_ueid(ueid), indent=2)


def _handle_ikigai_corrections(arguments: dict[str, Any]) -> str:
    d = _read_checkpoint()
    limit = arguments.get("limit", 20)
    corrs = d.get("corrections", [])[-limit:]
    if not corrs:
        row = _read_entity("plan_entities")
        if row:
            try:
                corrs = json.loads(row.get("corrections", "[]"))[-limit:]
            except Exception:
                corrs = []
    return json.dumps({"corrections": corrs, "count": len(corrs)}, indent=2)


def _handle_ikigai_plan_cycle(arguments: dict[str, Any]) -> str:
    try:
        import sys
        from pathlib import Path as P
        _src = P(__file__).parent.parent  # .../ikigai/src/
        if str(_src) not in sys.path:
            sys.path.insert(0, str(_src))
        from agents.ikigai_maintainer import make_ikigai_graph
        today = dt.date.today()
        graph = make_ikigai_graph()
        initial = {
            "cycle_id": today.isoformat(),
            "cycle_start": arguments.get("cycle_start") or today.isoformat(),
            "cycle_end": arguments.get("cycle_end") or (today + dt.timedelta(days=45)).isoformat(),
            "iteration": 0, "last_step": "",
            "regime_state": "MAINTAIN", "q_he_score": 0.65,
            "days_in_regime": 1, "is_hysteresis_active": False,
            "phase": "BUSCA", "phase_iteration": 0, "phase_converged": False,
            "phase_weights": {"passion": 0.15, "skill": 0.25, "market": 0.25, "revenue": 0.20, "course": 0.15},
            "vector_scores": {}, "meta_vector_score": 0.0,
            "active_dream_ueid": arguments.get("active_dream_ueid"),
            "active_goal_ueids": [], "active_objective_ueids": [],
            "active_project_ueids": [], "active_task_ueids": [],
            "workload_estimate": 2.0, "capacity_estimate": 8.0,
            "balancer_verdict": "OK",
            "prospective_buffer": [], "retrospective_log": [],
            "corrections": [], "kill_switch_triggered": False, "terminated": False,
        }
        config = {"configurable": {"thread_id": f"cycle_{today.isoformat()}"}}
        final = graph.invoke(initial, config)

        # Persist final state to plan_entities.db for ikigai_sync_vault
        try:
            plan_db = Path.home() / ".ikigai" / "plan_entities.db"
            plan_db.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(plan_db))
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS plan_entities (
                    cycle_id TEXT PRIMARY KEY,
                    regime TEXT,
                    q_he REAL,
                    passion REAL, skill REAL, market REAL, revenue REAL, course REAL,
                    meta_vector REAL,
                    corrections TEXT,
                    created_at TEXT
                )
            """)
            vs = final.get("vector_scores", {})
            cur.execute("""
                INSERT OR REPLACE INTO plan_entities
                (cycle_id, regime, q_he, passion, skill, market, revenue, course, meta_vector, corrections, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                final.get("cycle_id"),
                final.get("regime_state"),
                final.get("q_he_score"),
                vs.get("passion"),
                vs.get("skill"),
                vs.get("market"),
                vs.get("revenue"),
                vs.get("course"),
                final.get("meta_vector_score"),
                json.dumps(final.get("corrections", [])),
                dt.datetime.now().isoformat(),
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass  # non-fatal

        return json.dumps({
            "cycle_id": final.get("cycle_id"),
            "regime": final.get("regime_state"),
            "q_he": final.get("q_he_score"),
            "meta_vector": final.get("meta_vector_score"),
            "corrections_count": len(final.get("corrections", [])),
            "prospective_buffer_size": len(final.get("prospective_buffer", [])),
            "retrospective_log_size": len(final.get("retrospective_log", [])),
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def _handle_ikigai_checkpoint(arguments: dict[str, Any]) -> str:
    action = arguments.get("action", "get")
    thread_id = arguments.get("thread_id")
    path = _db_path()
    if action == "list":
        if not path.exists():
            return json.dumps({"checkpoints": []})
        else:
            conn = sqlite3.connect(str(path))
            cur = conn.cursor()
            cur.execute("SELECT thread_id, checkpoint_id, metadata FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 50")
            rows = cur.fetchall()
            conn.close()
            return json.dumps({"checkpoints": [{"thread_id": r[0], "checkpoint_id": r[1]} for r in rows]})
    elif action == "get":
        if not thread_id:
            return json.dumps({"error": "thread_id required"})
        elif not path.exists():
            return json.dumps({"error": "no checkpoints"})
        else:
            conn = sqlite3.connect(str(path))
            cur = conn.cursor()
            cur.execute("SELECT checkpoint, metadata FROM checkpoints WHERE thread_id = ? ORDER BY checkpoint_id DESC LIMIT 1", (thread_id,))
            row = cur.fetchone()
            conn.close()
            if row:
                import pickle
                ckpt = pickle.loads(row[0]) if row[0] else {}
                meta = pickle.loads(row[1]) if row[1] else {}
                return json.dumps({"thread_id": thread_id, "checkpoint": str(ckpt), "metadata": str(meta)})
            else:
                return json.dumps({"error": "checkpoint not found"})
    elif action == "set":
        if not thread_id or arguments.get("state_snapshot") is None:
            return json.dumps({"error": "thread_id and state_snapshot required"})
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            import pickle
            conn = sqlite3.connect(str(path))
            cur = conn.cursor()
            now = dt.datetime.now().isoformat()
            cur.execute(
                "INSERT OR REPLACE INTO checkpoints (thread_id, checkpoint_ns, checkpoint_id, type, checkpoint, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (thread_id, "", now, "manual", pickle.dumps(arguments["state_snapshot"]), pickle.dumps({"source": "mcp"}))
            )
            conn.commit()
            conn.close()
            return json.dumps({"ok": True, "thread_id": thread_id})
    else:
        return json.dumps({"error": f"unknown action: {action}"})


def _handle_ikigai_sync_vault(arguments: dict[str, Any]) -> str:
    cycle_id = arguments.get("cycle_id", "")
    if not cycle_id:
        return json.dumps({"error": "cycle_id required"})
    # Vault root: {repo}/data/matheus/ikigai_state/
    repo_root = Path(__file__).parent.parent.parent  # .../src/ikigai/src/mcp_server/ → src/ikigai/
    vault_dir = repo_root / "data" / "matheus" / "ikigai_state"
    vault_dir.mkdir(parents=True, exist_ok=True)

    # Read from plan_entities.db (written by ikigai_plan_cycle)
    row = _read_plan_entity(cycle_id)
    if not row:
        return json.dumps({"error": f"no cycle {cycle_id} in plan_entities.db — run ikigai_plan_cycle first"})
    try:
        log_file = vault_dir / f"cycle-{cycle_id}.md"
        vs = {
            "passion": row.get("passion"),
            "skill": row.get("skill"),
            "market": row.get("market"),
            "revenue": row.get("revenue"),
            "course": row.get("course"),
        }
        content = f"""---
ueid: ikigai:cycle:{cycle_id}
cycle_id: {cycle_id}
date: {dt.date.today().isoformat()}
regime: {row.get('regime', 'UNKNOWN')}
q_he: {row.get('q_he')}
meta_vector: {row.get('meta_vector')}
vector_scores: {json.dumps(vs)}
phase: {row.get('phase', 'BUSCA')}
corrections_count: 0
prospective_buffer_size: 0
retrospective_log_size: 0
---

# IKIGAi Cycle — {cycle_id}

## Vector Scores

| Vector | Score |
|--------|-------|
| Passion | {row.get('passion', 'N/A')} |
| Skill | {row.get('skill', 'N/A')} |
| Market | {row.get('market', 'N/A')} |
| Revenue | {row.get('revenue', 'N/A')} |
| Course | {row.get('course', 'N/A')} |

**Meta-vector:** {row.get('meta_vector', 'N/A')}

## Regime

- **State:** {row.get('regime', 'UNKNOWN')}
- **Q_HE:** {row.get('q_he', 'N/A')}

## Corrections (0)

_No corrections emitted in this cycle._

## Prospective Buffer (0)

"""
        log_file.write_text(content, encoding="utf-8")
        return json.dumps({"ok": True, "vault_path": str(log_file)})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# FastMCP tool wrappers — delegate to existing handlers via traced dispatch
# ---------------------------------------------------------------------------


@MCP.tool(
    name="ikigai_score",
    description="Returns current IKIGAi 5-vector scores and meta-vector score",
)
def ikigai_score() -> str:
    """5-vector IKIGAi scores (passion/skill/market/revenue/course) + meta-vector."""
    return traced_tool_dispatch("ikigai_score", _handle_ikigai_score, {})


@MCP.tool(
    name="ikigai_regime",
    description="Returns current regime (PUSH/MAINTAIN/REDUCE/RECOVER) and days in regime",
)
def ikigai_regime() -> str:
    """Current IKIGAi regime and days-in-regime."""
    return traced_tool_dispatch("ikigai_regime", _handle_ikigai_regime, {})


@MCP.tool(
    name="ikigai_phase",
    description="Returns current phase (FUNDAÇÃO/BUSCA/HACKATHON/RECUPERACAO/OVERCLOCK)",
)
def ikigai_phase() -> str:
    """Current IKIGAi phase and phase iteration."""
    return traced_tool_dispatch("ikigai_phase", _handle_ikigai_phase, {})


@MCP.tool(
    name="ikigai_decompose",
    description="Decompose a Dream UEID into its full UEID hierarchy",
)
def ikigai_decompose(dream_ueid: str) -> str:
    """Decompose a Dream UEID into its full UEID hierarchy."""
    return traced_tool_dispatch("ikigai_decompose", _handle_ikigai_decompose, {"dream_ueid": dream_ueid})


@MCP.tool(
    name="ikigai_corrections",
    description="List recent correction signals from H1-H6 heuristics",
)
def ikigai_corrections(limit: int = 20) -> str:
    """List recent correction signals from H1-H6 heuristics."""
    return traced_tool_dispatch("ikigai_corrections", _handle_ikigai_corrections, {"limit": limit})


@MCP.tool(
    name="ikigai_plan_cycle",
    description="Trigger an IKIGAi plan cycle — runs the full LangGraph agent",
)
def ikigai_plan_cycle(
    active_dream_ueid: str | None = None,
    cycle_start: str | None = None,
    cycle_end: str | None = None,
) -> str:
    """Trigger an IKIGAi plan cycle — runs the full LangGraph agent."""
    return traced_tool_dispatch("ikigai_plan_cycle", _handle_ikigai_plan_cycle, {
        "active_dream_ueid": active_dream_ueid,
        "cycle_start": cycle_start,
        "cycle_end": cycle_end,
    })


@MCP.tool(
    name="ikigai_checkpoint",
    description="Get or set a named checkpoint in the IKIGAi checkpoint DB",
)
def ikigai_checkpoint(
    action: str = "get",
    thread_id: str | None = None,
    state_snapshot: dict | None = None,
) -> str:
    """Get or set a named checkpoint in the IKIGAi checkpoint DB."""
    return traced_tool_dispatch("ikigai_checkpoint", _handle_ikigai_checkpoint, {
        "action": action,
        "thread_id": thread_id,
        "state_snapshot": state_snapshot,
    })


@MCP.tool(
    name="ikigai_sync_vault",
    description="Sync IKIGAi cycle data to the markdown vault",
)
def ikigai_sync_vault(cycle_id: str) -> str:
    """Sync IKIGAi cycle data to the markdown vault."""
    return traced_tool_dispatch("ikigai_sync_vault", _handle_ikigai_sync_vault, {"cycle_id": cycle_id})


@MCP.tool(
    name="ikigai_write_tasks",
    description="Write structured tasks to data/tasks.jsonl — Deep Agent output for interfaces",
)
def ikigai_write_tasks(tasks: list[dict]) -> str:
    """Write structured tasks to data/tasks.jsonl — Deep Agent output for interfaces."""
    return _write_tasks_to_data(tasks)


@MCP.tool(
    name="ikigai_read_tasks",
    description="Read structured tasks from data/tasks.jsonl — interfaces consumer",
)
def ikigai_read_tasks(
    horizon: str | None = None,
    done: bool | None = None,
    project_id: str | None = None,
    limit: int = 50,
) -> str:
    """Read structured tasks from data/tasks.jsonl — interfaces consumer."""
    return _read_tasks_from_data(horizon=horizon, done=done, project_id=project_id, limit=limit)


# ---------------------------------------------------------------------------
# Phase B3.2 — 3 new mesh tools (delegate to tools_mesh.py)
# ---------------------------------------------------------------------------
from mcp_server.tools_mesh import (
    ikigai_health,
    ikigai_mesh_show,
    ikigai_task_create,
)
from mcp_server.tools_vault import vault_write as _handle_vault_write


@MCP.tool(
    name="ikigai_mesh_show",
    description="Cross-fork view for one UEID (joins CLI + taskdog + solverforge_calendar)",
)
def _ikigai_mesh_show_tool(ueid: str) -> str:
    """A2UI mesh.read realization — see docs/.../a2ui-protocol-design.md §11 R1."""
    return ikigai_mesh_show(ueid=ueid)


@MCP.tool(
    name="ikigai_task_create",
    description="Emit a TaskChange to data/review_queue/<id>.json (create action only in v1)",
)
def _ikigai_task_create_tool(
    ueid: str,
    fields: dict,
    source_fork: str,
    action: str = "create",
) -> str:
    """A2UI task.write realization (create action only)."""
    return ikigai_task_create(
        ueid=ueid,
        fields=fields,
        source_fork=source_fork,
        action=action,
    )


@MCP.tool(
    name="ikigai_health",
    description="Gateway heartbeat: version, uptime, adapter statuses",
)
def _ikigai_health_tool() -> str:
    """Returns gateway health snapshot."""
    return ikigai_health()


# ---------------------------------------------------------------------------
# Phase B6.7 — vault_write (only vault writer per attribution §7)
# ---------------------------------------------------------------------------
@MCP.tool(
    name="vault_write",
    description=(
        "Write markdown file to vault. ONLY vault writer per attribution report §7. "
        "Rejects paths outside vault/, absolute paths, empty writes. "
        "Uses VaultLock for concurrency. Atomic via frontmatter.dump()."
    ),
)
def vault_write(
    vault_path: str,
    frontmatter: dict,
    body: str,
) -> str:
    """Write markdown file to vault. ONLY vault writer per attribution §7."""
    return traced_tool_dispatch(
        "vault_write",
        _handle_vault_write,
        {"vault_path": vault_path, "frontmatter": frontmatter, "body": body},
    )


# ---------------------------------------------------------------------------
# Phase B3.3 — 6 MCP resources (delegate to resources.py)
# ---------------------------------------------------------------------------
from mcp_server.resources import (
    health_resource,
    plans_cycle_resource,
    plans_cycles_resource,
    queue_event_resource,
    queue_pending_resource,
    ueid_resource,
)


@MCP.resource("ueid://{ueid}")
def _ueid_resource(ueid: str) -> str:
    """Cross-fork view for one UEID."""
    return ueid_resource(ueid)


@MCP.resource("queue://pending")
def _queue_pending_resource() -> str:
    """List of pending TaskChange events."""
    return queue_pending_resource()


@MCP.resource("queue://events/{event_id}")
def _queue_event_resource(event_id: str) -> str:
    """One TaskChange event by ID."""
    return queue_event_resource(event_id)


@MCP.resource("health://gateway")
def _health_resource() -> str:
    """Gateway heartbeat."""
    return health_resource()


@MCP.resource("plans://cycles")
def _plans_cycles_resource() -> str:
    """List of recent PlanningCycles."""
    return plans_cycles_resource()


@MCP.resource("plans://cycles/{cycle_id}")
def _plans_cycle_resource(cycle_id: str) -> str:
    """One PlanningCycle full record."""
    return plans_cycle_resource(cycle_id)


# ---------------------------------------------------------------------------
# Backward-compat TOOLS list — exposes registered tools for test introspection
# ---------------------------------------------------------------------------
TOOLS = list(MCP._tool_manager._tools.values())


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
async def main() -> None:
    """Run the FastMCP gateway over stdio."""
    await MCP.run_stdio_async()
