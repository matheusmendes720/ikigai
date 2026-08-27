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
# Tool handlers
# ---------------------------------------------------------------------------


async def _list_tools(ctx, params) -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)


async def _call_tool(ctx, params) -> CallToolResult:
    name = params.name
    arguments = params.arguments or {}
    text = ""

    if name == "ikigai_score":
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
        text = json.dumps({"vector_scores": vs, "meta_vector_score": round(mv, 4), "q_he_score": qhe}, indent=2)

    elif name == "ikigai_regime":
        d = _read_checkpoint()
        regime = d.get("regime_state", "MAINTAIN")
        days = d.get("days_in_regime", 0)
        qhe = d.get("q_he_score")
        if not d:
            row = _read_entity("plan_entities")
            if row:
                regime = row.get("regime", regime)
                qhe = row.get("q_he", qhe)
        text = json.dumps({"regime_state": regime, "days_in_regime": days, "q_he_score": qhe}, indent=2)

    elif name == "ikigai_phase":
        d = _read_checkpoint()
        text = json.dumps({
            "phase": d.get("phase", "BUSCA"),
            "phase_iteration": d.get("phase_iteration", 0),
            "phase_converged": d.get("phase_converged", False),
            "phase_weights": d.get("phase_weights", {}),
        }, indent=2)

    elif name == "ikigai_decompose":
        ueid = arguments.get("dream_ueid", "")
        if not ueid:
            text = json.dumps({"error": "dream_ueid required"})
        else:
            text = json.dumps(_decompose_ueid(ueid), indent=2)

    elif name == "ikigai_corrections":
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
        text = json.dumps({"corrections": corrs, "count": len(corrs)}, indent=2)

    elif name == "ikigai_plan_cycle":
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
                from ikigai.propagation.sqlite_adapter import SQLiteAdapter

                plan_db = Path.home() / ".ikigai" / "plan_entities.db"
                adapter = SQLiteAdapter(db_path=plan_db)

                cycle_id = final.get("cycle_id")
                created_at = dt.datetime.now().isoformat()
                ueid = f"cycle:{cycle_id}"
                vs = final.get("vector_scores", {})

                adapter.upsert(
                    ueid=ueid,
                    entity_type="cycle",
                    slug=cycle_id,
                    title=f"Cycle {cycle_id}",
                    description=f"Regime: {final.get('regime_state')}, Q_HE: {final.get('q_he_score')}",
                    status="ACTIVE",
                    created_at=created_at,
                    updated_at=created_at,
                    ikigai_vectors=vs,
                    primary_score=final.get("q_he_score"),
                    regime_at_creation=final.get("regime_state"),
                    custom={"corrections": final.get("corrections", []), "meta_vector": final.get("meta_vector_score")},
                )
            except Exception:
                pass  # non-fatal

            text = json.dumps({
                "cycle_id": final.get("cycle_id"),
                "regime": final.get("regime_state"),
                "q_he": final.get("q_he_score"),
                "meta_vector": final.get("meta_vector_score"),
                "corrections_count": len(final.get("corrections", [])),
                "prospective_buffer_size": len(final.get("prospective_buffer", [])),
                "retrospective_log_size": len(final.get("retrospective_log", [])),
            }, indent=2)
        except Exception as e:
            text = json.dumps({"error": str(e)})

    elif name == "ikigai_checkpoint":
        action = arguments.get("action", "get")
        thread_id = arguments.get("thread_id")
        path = _db_path()
        if action == "list":
            if not path.exists():
                text = json.dumps({"checkpoints": []})
            else:
                conn = sqlite3.connect(str(path))
                cur = conn.cursor()
                cur.execute("SELECT thread_id, checkpoint_id, metadata FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 50")
                rows = cur.fetchall()
                conn.close()
                text = json.dumps({"checkpoints": [{"thread_id": r[0], "checkpoint_id": r[1]} for r in rows]})
        elif action == "get":
            if not thread_id:
                text = json.dumps({"error": "thread_id required"})
            elif not path.exists():
                text = json.dumps({"error": "no checkpoints"})
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
                    text = json.dumps({"thread_id": thread_id, "checkpoint": str(ckpt), "metadata": str(meta)})
                else:
                    text = json.dumps({"error": "checkpoint not found"})
        elif action == "set":
            if not thread_id or arguments.get("state_snapshot") is None:
                text = json.dumps({"error": "thread_id and state_snapshot required"})
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
                text = json.dumps({"ok": True, "thread_id": thread_id})
        else:
            text = json.dumps({"error": f"unknown action: {action}"})

    elif name == "ikigai_sync_vault":
        cycle_id = arguments.get("cycle_id", "")
        if not cycle_id:
            text = json.dumps({"error": "cycle_id required"})
        else:
            # Vault root: {repo}/data/matheus/ikigai_state/
            repo_root = Path(__file__).parent.parent.parent  # .../life-ops/ikigai/
            vault_dir = repo_root / "data" / "matheus" / "ikigai_state"
            vault_dir.mkdir(parents=True, exist_ok=True)

            # Read from plan_entities.db (written by ikigai_plan_cycle)
            row = _read_plan_entity(cycle_id)
            if not row:
                text = json.dumps({"error": f"no cycle {cycle_id} in plan_entities.db — run ikigai_plan_cycle first"})
            else:
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
                    text = json.dumps({"ok": True, "vault_path": str(log_file)})
                except Exception as e:
                    text = json.dumps({"error": str(e)})

    else:
        text = f"Unknown tool: {name}"

    is_error = text.startswith('{"error"')
    return CallToolResult(content=[TextContent(type="text", text=text)], is_error=is_error)


# ---------------------------------------------------------------------------
# Server instance with constructor callbacks
# ---------------------------------------------------------------------------
SERVER = Server(
    "ikigai-maintainer",
    on_list_tools=_list_tools,
    on_call_tool=_call_tool,
)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await SERVER.run(read_stream, write_stream, SERVER.create_initialization_options())
