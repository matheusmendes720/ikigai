"""IKIGAi-Maintainer MCP server — 8 tools via stdio transport.

Run with: python run_mcp_server.py
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any

import frontmatter
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ListToolsResult, CallToolResult

from mcp_server.tracing import init_mcp_tracing, traced_tool_dispatch


# ---------------------------------------------------------------------------
# Tool list
# ---------------------------------------------------------------------------
TOOLS: list[Tool] = [
    Tool(
        name="ikigai_score",
        description="Returns current IKIGAi 5-vector scores and meta-vector score",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="ikigai_regime",
        description="Returns current regime (PUSH/MAINTAIN/REDUCE/RECOVER) and days in regime",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="ikigai_phase",
        description="Returns current phase (FUNDAÇÃO/BUSCA/HACKATHON/RECUPERACAO/OVERCLOCK)",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="ikigai_decompose",
        description="Decompose a Dream UEID into its full UEID hierarchy",
        inputSchema={
            "type": "object",
            "properties": {"dream_ueid": {"type": "string", "description": "Dream UEID"}},
            "required": ["dream_ueid"],
        },
    ),
    Tool(
        name="ikigai_corrections",
        description="List recent correction signals from H1-H6 heuristics",
        inputSchema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 20}},
        },
    ),
    Tool(
        name="ikigai_plan_cycle",
        description="Trigger an IKIGAi plan cycle — runs the full LangGraph agent",
        inputSchema={
            "type": "object",
            "properties": {
                "active_dream_ueid": {"type": "string"},
                "cycle_start": {"type": "string"},
                "cycle_end": {"type": "string"},
            },
        },
    ),
    Tool(
        name="ikigai_checkpoint",
        description="Get or set a named checkpoint in the IKIGAi checkpoint DB",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["get", "set", "list"]},
                "thread_id": {"type": "string"},
                "state_snapshot": {"type": "object"},
            },
        },
    ),
    Tool(
        name="ikigai_sync_vault",
        description="Sync IKIGAi cycle data to the markdown vault",
        inputSchema={
            "type": "object",
            "properties": {"cycle_id": {"type": "string"}},
            "required": ["cycle_id"],
        },
    ),
    Tool(
        name="ikigai_write_tasks",
        description="Write structured tasks to data/tasks.jsonl — Deep Agent output for interfaces",
        inputSchema={
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "description": "List of task objects to write",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "horizon": {"type": "string", "enum": ["today", "tomorrow", "this_week", "next_week", "this_month", "next_month", "this_quarter", "next_quarter", "this_year", "onda", "sprint"]},
                            "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                            "project_id": {"type": "string"},
                            "estimated_minutes": {"type": "integer"},
                        },
                        "required": ["title", "horizon"],
                    },
                },
            },
            "required": ["tasks"],
        },
    ),
    Tool(
        name="ikigai_read_tasks",
        description="Read structured tasks from data/tasks.jsonl — interfaces consumer",
        inputSchema={
            "type": "object",
            "properties": {
                "horizon": {"type": "string"},
                "done": {"type": "boolean"},
                "project_id": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
]


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

    repo_root = Path(__file__).parent.parent.parent  # .../life-ops/ikigai/
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
    repo_root = Path(__file__).parent.parent.parent.parent  # .../life-ops/ikigai/ → repo root
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
# Server instance — mcp>=1.1 decorator-based API
# ---------------------------------------------------------------------------
SERVER = Server("ikigai-maintainer")

# Initialize OpenTelemetry tracing (idempotent)
init_mcp_tracing()


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
    repo_root = Path(__file__).parent.parent.parent  # .../life-ops/ikigai/
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


# Tool dispatch mapping
_TOOL_DISPATCH: dict[str, callable] = {
    "ikigai_score": _handle_ikigai_score,
    "ikigai_regime": _handle_ikigai_regime,
    "ikigai_phase": _handle_ikigai_phase,
    "ikigai_decompose": _handle_ikigai_decompose,
    "ikigai_corrections": _handle_ikigai_corrections,
    "ikigai_plan_cycle": _handle_ikigai_plan_cycle,
    "ikigai_checkpoint": _handle_ikigai_checkpoint,
    "ikigai_sync_vault": _handle_ikigai_sync_vault,
    "ikigai_write_tasks": _write_tasks_to_data,
    "ikigai_read_tasks": _read_tasks_from_data,
}


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


@SERVER.list_tools()
async def _list_tools(request) -> ListToolsResult:
    """Return the list of 8 IKIGAI tools."""
    return ListToolsResult(tools=TOOLS)


@SERVER.call_tool()
async def _call_tool(name: str, arguments: dict[str, Any] | None) -> CallToolResult:
    """Dispatch one tool call by name with OpenTelemetry tracing."""
    arguments = arguments or {}

    handler = _TOOL_DISPATCH.get(name)
    if handler is None:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")],
            is_error=True,
        )

    try:
        text = traced_tool_dispatch(name, handler, arguments)
        is_error = text.startswith('{"error"')
        return CallToolResult(content=[TextContent(type="text", text=text)], is_error=is_error)
    except Exception as exc:
        # traced_tool_dispatch already captured the traceback in the span.
        return CallToolResult(
            content=[TextContent(type="text", text=f"ERROR: {type(exc).__name__}: {exc}")],
            is_error=True,
        )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await SERVER.run(read_stream, write_stream, SERVER.create_initialization_options())
