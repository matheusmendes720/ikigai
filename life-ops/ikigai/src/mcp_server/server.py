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

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

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


def _read_checkpoint() -> dict[str, Any]:
    path = _db_path()
    if not path.exists():
        return {}
    try:
        conn = sqlite3.connect(str(path))
        cur = conn.cursor()
        cur.execute("SELECT state FROM checkpoints ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        return json.loads(row[0]) if row else {}
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
async def _list_tools() -> list[Tool]:
    return TOOLS


async def _call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
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
        return [TextContent(type="text", text=json.dumps({"vector_scores": vs, "meta_vector_score": round(mv, 4), "q_he_score": qhe}, indent=2))]

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
        return [TextContent(type="text", text=json.dumps({"regime_state": regime, "days_in_regime": days, "q_he_score": qhe}, indent=2))]

    elif name == "ikigai_phase":
        d = _read_checkpoint()
        return [TextContent(type="text", text=json.dumps({
            "phase": d.get("phase", "BUSCA"),
            "phase_iteration": d.get("phase_iteration", 0),
            "phase_converged": d.get("phase_converged", False),
            "phase_weights": d.get("phase_weights", {}),
        }, indent=2))]

    elif name == "ikigai_decompose":
        ueid = arguments.get("dream_ueid", "")
        if not ueid:
            return [TextContent(type="text", text=json.dumps({"error": "dream_ueid required"}))]
        result = {"dream_ueid": ueid, "goals": [], "objectives": [], "projects": [], "tasks": []}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

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
        return [TextContent(type="text", text=json.dumps({"corrections": corrs, "count": len(corrs)}, indent=2))]

    elif name == "ikigai_plan_cycle":
        try:
            import sys
            from pathlib import Path as P
            _src = P(__file__).parent.parent / "ikigai" / "src"
            if str(_src) not in sys.path:
                sys.path.insert(0, str(_src))
            from ikigai_maintainer import make_ikigai_graph
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
            return [TextContent(type="text", text=json.dumps({
                "cycle_id": final.get("cycle_id"),
                "regime": final.get("regime_state"),
                "q_he": final.get("q_he_score"),
                "meta_vector": final.get("meta_vector_score"),
                "corrections_count": len(final.get("corrections", [])),
                "prospective_buffer_size": len(final.get("prospective_buffer", [])),
                "retrospective_log_size": len(final.get("retrospective_log", [])),
            }, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    elif name == "ikigai_checkpoint":
        action = arguments.get("action", "get")
        thread_id = arguments.get("thread_id")
        path = _db_path()
        if action == "list":
            if not path.exists():
                return [TextContent(type="text", text=json.dumps({"checkpoints": []}))]
            conn = sqlite3.connect(str(path))
            cur = conn.cursor()
            cur.execute("SELECT thread_id, created_at FROM checkpoints ORDER BY created_at DESC LIMIT 50")
            rows = cur.fetchall()
            conn.close()
            return [TextContent(type="text", text=json.dumps({"checkpoints": [{"thread_id": r[0], "created_at": r[1]} for r in rows]}))]
        if action == "get":
            if not thread_id:
                return [TextContent(type="text", text=json.dumps({"error": "thread_id required"}))]
            if not path.exists():
                return [TextContent(type="text", text=json.dumps({"error": "no checkpoints"}))]
            conn = sqlite3.connect(str(path))
            cur = conn.cursor()
            cur.execute("SELECT state FROM checkpoints WHERE thread_id = ? ORDER BY created_at DESC LIMIT 1", (thread_id,))
            row = cur.fetchone()
            conn.close()
            if row:
                return [TextContent(type="text", text=json.dumps({"thread_id": thread_id, "state": json.loads(row[0])}))]
            return [TextContent(type="text", text=json.dumps({"error": "checkpoint not found"}))]
        if action == "set":
            if not thread_id or arguments.get("state_snapshot") is None:
                return [TextContent(type="text", text=json.dumps({"error": "thread_id and state_snapshot required"}))]
            path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(path))
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS checkpoints (thread_id TEXT, state TEXT, created_at TEXT)")
            cur.execute("INSERT INTO checkpoints (thread_id, state, created_at) VALUES (?, ?, ?)",
                        (thread_id, json.dumps(arguments["state_snapshot"]), dt.datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return [TextContent(type="text", text=json.dumps({"ok": True, "thread_id": thread_id}))]
        return [TextContent(type="text", text=json.dumps({"error": f"unknown action: {action}"}))]

    elif name == "ikigai_sync_vault":
        cycle_id = arguments.get("cycle_id", "")
        if not cycle_id:
            return [TextContent(type="text", text=json.dumps({"error": "cycle_id required"}))]
        vault = Path.home() / ".ikigai" / "vault"
        if not vault.exists():
            return [TextContent(type="text", text=json.dumps({"error": "vault not configured"}))]
        row = _read_entity("plan_entities")
        if not row:
            return [TextContent(type="text", text=json.dumps({"error": f"no cycle {cycle_id}"}))]
        try:
            log_file = vault / "ikigai_cycle_log.md"
            entry = f"\n## Cycle {cycle_id}\n- Date: {dt.date.today().isoformat()}\n- Regime: {row.get('regime')}\n- Q_HE: {row.get('q_he')}"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(entry + "\n")
            return [TextContent(type="text", text=json.dumps({"ok": True, "vault_path": str(log_file)}))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


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
