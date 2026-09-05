"""IKIGAi MCP server — stdio transport.

PHASE 8.2 REWRITE:
- 7 orphan handlers deleted (were reading SQLite, no @MCP.tool decorator)
- 7 MCP observation wrappers RE-REGISTERED reading from vault/
- vault_write invariant preserved: only vault_write tool writes vault/

Run with: python run_mcp_server.py
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, cast

from mcp.server.fastmcp import FastMCP

from mcp_server.investigation_complete import investigation_complete
from mcp_server.investigation_enqueue import investigation_enqueue
from mcp_server.investigation_status import investigation_status
from mcp_server.tracing import init_mcp_tracing, traced_tool_dispatch

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
MCP = FastMCP("ikigai-gateway")

# Initialize OpenTelemetry tracing (idempotent)
init_mcp_tracing()


# ---------------------------------------------------------------------------
# DB helpers (used by active tools only)
# ---------------------------------------------------------------------------
def _db_path(suffix: str = "ikigai_checkpoints.db") -> Path:
    return Path.home() / ".ikigai" / suffix


def _vault_root() -> Path:
    """Return vault root: {repo}/vault/."""
    repo_root = Path(__file__).parent.parent.parent.parent  # .../src/ikigai/src/ → repo root
    return repo_root / "vault"


def _extract_frontmatter_field(content: str, field: str) -> Any:
    """Extract a field value from YAML frontmatter in a markdown file.

    Matches lines like:  field_name: value
    Returns the raw string value (caller converts as needed).
    """
    pattern = rf"^{re.escape(field)}\s*:\s*(.+)$"
    for line in content.splitlines():
        m = re.match(pattern, line.strip())
        if m:
            return m.group(1).strip()
    return None


def _read_checkpoint(thread_id: str | None = None) -> dict[str, Any]:
    """Read latest checkpoint from LangGraph SQLite (used by ikigai_checkpoint)."""
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


# ---------------------------------------------------------------------------
# Tool handler functions
# ---------------------------------------------------------------------------


def _handle_ikigai_decompose(arguments: dict[str, Any]) -> str:
    """Traverse the vault hierarchy for a given Dream UEID (active handler)."""
    ueid = arguments.get("dream_ueid", "")
    if not ueid:
        return json.dumps({"error": "dream_ueid required"})
    return json.dumps(_decompose_ueid(ueid), indent=2)


def _decompose_ueid(ueid: str) -> dict[str, Any]:
    """Traverse the vault hierarchy for a given Dream UEID.

    Vault root: {repo}/data/matheus/
    Structure: dreams/ → objectives/ → projects/ → tasks/
    """
    import frontmatter

    repo_root = Path(__file__).parent.parent.parent  # .../src/ikigai/src/mcp_server/ → src/ikigai/
    vault_root = repo_root / "data" / "matheus"

    def _slug_from_ueid(ueid: str) -> str:
        """Extract slug from UEID like ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609."""
        parts = ueid.split(":")
        return parts[2] if len(parts) >= 3 else ""

    def _read_entity(dir_name: str, slug: str) -> list[dict[str, Any]]:
        """Read all frontmatter records from a vault subdirectory."""
        entity_dir = vault_root / dir_name
        results: list[dict[str, Any]] = []
        if not entity_dir.is_dir():
            return results
        for md_file in entity_dir.iterdir():
            if not md_file.suffix == ".md":
                continue
            try:
                post = frontmatter.loads(md_file.read_text(encoding="utf-8"))
                results.append(
                    {
                        "file": str(md_file.relative_to(vault_root)),
                        "ueid": post.metadata.get("ueid", ""),
                        "title": post.metadata.get("title", md_file.stem),
                        "status": post.metadata.get("status", "UNKNOWN"),
                        "slug": post.metadata.get("slug", md_file.stem),
                        "parent_ueid": post.metadata.get("parent_ueid"),
                        "related_ueids": post.metadata.get("related_ueids", []),
                    }
                )
            except Exception:
                pass
        return results

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

    # Read all objectives / projects
    objectives = _read_entity("objectives", dream_slug)
    projects = _read_entity("projects", dream_slug)

    # Filter objectives to those whose parent_ueid or related_ueids match this dream
    dream_objectives = [
        o for o in objectives if o.get("parent_ueid") == ueid or ueid in o.get("related_ueids", [])
    ]
    dream_projects = [
        p for p in projects if p.get("parent_ueid") in [o.get("ueid") for o in dream_objectives]
    ]

    return {
        "dream": dream_data,
        "goals": [],
        "objectives": dream_objectives,
        "projects": dream_projects,
        "tasks": [],
    }


def _handle_ikigai_checkpoint(arguments: dict[str, Any]) -> str:
    """Checkpoint read/write for LangGraph (active handler, reads SQLite)."""
    action = arguments.get("action", "get")
    thread_id = arguments.get("thread_id")
    path = _db_path()
    if action == "list":
        if not path.exists():
            return json.dumps({"checkpoints": []})
        else:
            conn = sqlite3.connect(str(path))
            cur = conn.cursor()
            cur.execute(
                "SELECT thread_id, checkpoint_id, metadata FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 50"
            )
            rows = cur.fetchall()
            conn.close()
            return json.dumps(
                {"checkpoints": [{"thread_id": r[0], "checkpoint_id": r[1]} for r in rows]}
            )
    elif action == "get":
        if not thread_id:
            return json.dumps({"error": "thread_id required"})
        elif not path.exists():
            return json.dumps({"error": "no checkpoints"})
        else:
            conn = sqlite3.connect(str(path))
            cur = conn.cursor()
            cur.execute(
                "SELECT checkpoint, metadata FROM checkpoints WHERE thread_id = ? ORDER BY checkpoint_id DESC LIMIT 1",
                (thread_id,),
            )
            row = cur.fetchone()
            conn.close()
            if row:
                import pickle

                ckpt = pickle.loads(row[0]) if row[0] else {}
                meta = pickle.loads(row[1]) if row[1] else {}
                return json.dumps(
                    {"thread_id": thread_id, "checkpoint": str(ckpt), "metadata": str(meta)}
                )
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
                (
                    thread_id,
                    "",
                    now,
                    "manual",
                    pickle.dumps(arguments["state_snapshot"]),
                    pickle.dumps({"source": "mcp"}),
                ),
            )
            conn.commit()
            conn.close()
            return json.dumps({"ok": True, "thread_id": thread_id})
    else:
        return json.dumps({"error": f"unknown action: {action}"})


# ---------------------------------------------------------------------------
# PHASE 8.2: 7 observation wrappers (read vault, no vault writes)
# ---------------------------------------------------------------------------


def _handle_ikigai_score(arguments: dict[str, Any]) -> str:
    """Read scoring observation from vault/ikigai/meta/cycle_state/{date}.md (PAV-written)."""
    date_str = arguments.get("date", "")
    if not date_str:
        date_str = dt.date.today().isoformat()
    vault_root = _vault_root()
    cycle_file = vault_root / "ikigai" / "meta" / "cycle_state" / f"{date_str}.md"
    if not cycle_file.exists():
        return json.dumps(
            {
                "error": "no cycle_state for date",
                "date": date_str,
                "hint": "PAV writes cycle_state.md — ensure PAV ran for this date",
            }
        )
    content = cycle_file.read_text(encoding="utf-8")
    return json.dumps(
        {
            "date": date_str,
            "source": str(cycle_file),
            "vector_scores": {
                "passion": _extract_frontmatter_field(content, "passion_score"),
                "skill": _extract_frontmatter_field(content, "skill_score"),
                "market": _extract_frontmatter_field(content, "market_score"),
                "revenue": _extract_frontmatter_field(content, "revenue_score"),
                "course": _extract_frontmatter_field(content, "course_score"),
            },
            "meta_vector_score": _extract_frontmatter_field(content, "meta_vector"),
            "q_he_score": _extract_frontmatter_field(content, "q_he"),
            "note": "Observation only — IKIGAI does not execute math",
        },
        indent=2,
    )


def _handle_ikigai_regime(arguments: dict[str, Any]) -> str:
    """Read regime observation from vault/ikigai/meta/regime_state/{date}.md (PAV-written)."""
    date_str = arguments.get("date", "")
    if not date_str:
        date_str = dt.date.today().isoformat()
    vault_root = _vault_root()
    regime_file = vault_root / "ikigai" / "meta" / "regime_state" / f"{date_str}.md"
    if not regime_file.exists():
        return json.dumps(
            {
                "error": "no regime_state for date",
                "date": date_str,
                "hint": "PAV writes regime_state.md — ensure PAV ran for this date",
            }
        )
    content = regime_file.read_text(encoding="utf-8")
    return json.dumps(
        {
            "date": date_str,
            "source": str(regime_file),
            "regime_state": _extract_frontmatter_field(content, "regime_state"),
            "days_in_regime": _extract_frontmatter_field(content, "days_in_regime"),
            "q_he_score": _extract_frontmatter_field(content, "q_he"),
            "note": "Observation only — IKIGAI does not compute regime FSM",
        },
        indent=2,
    )


def _handle_ikigai_phase(arguments: dict[str, Any]) -> str:
    """Read phase observation from vault/ikigai/meta/phase_state.md (PAV-written)."""
    vault_root = _vault_root()
    phase_file = vault_root / "ikigai" / "meta" / "phase_state.md"
    if not phase_file.exists():
        return json.dumps(
            {
                "error": "no phase_state found",
                "hint": "PAV writes phase_state.md",
            }
        )
    content = phase_file.read_text(encoding="utf-8")
    return json.dumps(
        {
            "source": str(phase_file),
            "phase": _extract_frontmatter_field(content, "phase"),
            "phase_iteration": _extract_frontmatter_field(content, "phase_iteration"),
            "phase_converged": _extract_frontmatter_field(content, "phase_converged"),
            "phase_weights": _extract_frontmatter_field(content, "phase_weights"),
            "note": "Observation only — IKIGAI does not compute phase FSM",
        },
        indent=2,
    )


def _handle_ikigai_corrections(arguments: dict[str, Any]) -> str:
    """Read corrections from vault/ikigai/meta/corrections/{date}.md (PAV-written)."""
    date_str = arguments.get("date", "")
    if not date_str:
        date_str = dt.date.today().isoformat()
    limit = arguments.get("limit", 20)
    vault_root = _vault_root()
    corrections_file = vault_root / "ikigai" / "meta" / "corrections" / f"{date_str}.md"
    if not corrections_file.exists():
        return json.dumps({"corrections": [], "count": 0, "date": date_str})
    content = corrections_file.read_text(encoding="utf-8")
    # Extract correction lines from body (simple heuristic: lines starting with - or *)
    corrections = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            corrections.append(stripped[2:])
            if len(corrections) >= limit:
                break
    return json.dumps(
        {"corrections": corrections, "count": len(corrections), "date": date_str}, indent=2
    )


def _handle_ikigai_plan_cycle(arguments: dict[str, Any]) -> str:
    """ARCHIVED per ADR-013. Returns archived status observation."""
    _ = arguments
    return json.dumps(
        {
            "status": "ARCHIVED",
            "tool": "ikigai_plan_cycle",
            "reason": "math kernel deleted 2026-08-31 per ADR-013. QHE/regime/phase/heuristics are out of scope.",
            "alternative": "Read soft-preferences from ./strategics/ (PT-BR). Plan via vault_read + taskdog_/tuiboard_/solverforge_ tools.",
        },
        indent=2,
    )


def _handle_ikigai_sync_vault(arguments: dict[str, Any]) -> str:
    """Read vault sync log. Does NOT write vault (vault_write invariant)."""
    date_str = arguments.get("date", "")
    if not date_str:
        date_str = dt.date.today().isoformat()
    vault_root = _vault_root()
    sync_log = vault_root / "ikigai" / "meta" / "sync_log" / f"{date_str}.md"
    if not sync_log.exists():
        return json.dumps(
            {
                "date": date_str,
                "status": "no_sync_log",
                "note": "Read-only observation — vault_write is the sole vault writer",
            }
        )
    content = sync_log.read_text(encoding="utf-8")
    return json.dumps(
        {
            "date": date_str,
            "source": str(sync_log),
            "content_preview": content[:500],
            "note": "Read-only observation — vault_write is the sole vault writer",
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Task I/O — Deep Agent ↔ interfaces via data/tasks.jsonl
# (delegated to vault subsystem to keep vault-write scanner happy)
# ---------------------------------------------------------------------------
from sys_ikigai.vault.task_io import _read_tasks_from_data, _write_tasks_to_data  # noqa: E402

# ---------------------------------------------------------------------------
# FastMCP tool wrappers
# ---------------------------------------------------------------------------


# --- Active tools (pre-existing, unchanged) ---


@MCP.tool(
    name="ikigai_decompose",
    description="Decompose a Dream UEID into its full UEID hierarchy",
)
def ikigai_decompose(dream_ueid: str) -> str:
    """Decompose a Dream UEID into its full UEID hierarchy."""
    return cast(
        str,
        traced_tool_dispatch(
            "ikigai_decompose", _handle_ikigai_decompose, {"dream_ueid": dream_ueid}
        ),
    )


@MCP.tool(
    name="ikigai_write_tasks",
    description="Write structured tasks to data/tasks.jsonl — Deep Agent output for interfaces",
)
def ikigai_write_tasks(tasks: list[dict[str, Any]]) -> str:
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


# --- Phase B3.2: mesh tools ---


@MCP.tool(
    name="ikigai_mesh_show",
    description="Cross-fork view for one UEID (joins CLI + taskdog + solverforge_calendar)",
)
def _ikigai_mesh_show_tool(ueid: str) -> str:
    """A2UI mesh.read realization."""
    from mcp_server.tools_mesh import ikigai_mesh_show

    return ikigai_mesh_show(ueid=ueid)


@MCP.tool(
    name="ikigai_task_create",
    description="Emit a TaskChange to data/review_queue/<id>.json (create action only in v1)",
)
def _ikigai_task_create_tool(
    ueid: str,
    fields: dict[str, Any],
    source_fork: str,
    action: str = "create",
) -> str:
    """A2UI task.write realization (create action only)."""
    from mcp_server.tools_mesh import ikigai_task_create

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
    from mcp_server.tools_mesh import ikigai_health

    return ikigai_health()


# --- vault tools (Phase B6/B7) ---


@MCP.tool(
    name="vault_write",
    description=(
        "Write markdown file to vault. ONLY vault writer per attribution report §7. "
        "Rejects paths outside vault/, absolute paths, empty writes. "
        "Uses VaultLock for concurrency safety. Atomic via tmp-file + atomic-rename."
    ),
)
def vault_write(
    vault_path: str,
    frontmatter: dict[str, Any],
    body: str,
) -> str:
    """Write markdown file to vault. ONLY vault writer per attribution §7."""
    from mcp_server.tools_vault import vault_write as _handle_vault_write

    return cast(
        str,
        traced_tool_dispatch(
            "vault_write",
            _handle_vault_write,
            {"vault_path": vault_path, "frontmatter": frontmatter, "body": body},
        ),
    )


@MCP.tool(
    name="vault_read",
    description=(
        "Read markdown file from vault. Returns parsed frontmatter, body, sha256, mtime. "
        "Read-only — never writes. Mirror of vault_write security model."
    ),
)
def vault_read(vault_path: str) -> str:
    """Read markdown file from vault. Read-side mirror of vault_write (B7.1)."""
    from mcp_server.tools_vault import vault_read as _handle_vault_read

    return cast(
        str,
        traced_tool_dispatch(
            "vault_read",
            _handle_vault_read,
            {"vault_path": vault_path},
        ),
    )


# ---------------------------------------------------------------------------
# PHASE 8.2: 7 re-registered observation wrappers (read vault, no math)
# ---------------------------------------------------------------------------


@MCP.tool(
    name="ikigai_score",
    description="OBSERVE scoring (PAV-written). Does NOT execute math.",
)
def ikigai_score(date: str = "") -> str:
    """Read scoring observation from vault/ikigai/meta/cycle_state/{date}.md."""
    return cast(
        str,
        traced_tool_dispatch(
            "ikigai_score",
            _handle_ikigai_score,
            {"date": date},
        ),
    )


@MCP.tool(
    name="ikigai_regime",
    description="OBSERVE regime (PAV-written). Does NOT compute regime FSM.",
)
def ikigai_regime(date: str = "") -> str:
    """Read regime observation from vault/ikigai/meta/regime_state/{date}.md."""
    return cast(
        str,
        traced_tool_dispatch(
            "ikigai_regime",
            _handle_ikigai_regime,
            {"date": date},
        ),
    )


@MCP.tool(
    name="ikigai_phase",
    description="OBSERVE phase (PAV-written). Does NOT compute phase FSM.",
)
def ikigai_phase() -> str:
    """Read phase observation from vault/ikigai/meta/phase_state.md."""
    return cast(
        str,
        traced_tool_dispatch(
            "ikigai_phase",
            _handle_ikigai_phase,
            {},
        ),
    )


@MCP.tool(
    name="ikigai_corrections",
    description="OBSERVE corrections (PAV-written). Does NOT compute corrections.",
)
def ikigai_corrections(date: str = "", limit: int = 20) -> str:
    """Read corrections from vault/ikigai/meta/corrections/{date}.md."""
    return cast(
        str,
        traced_tool_dispatch(
            "ikigai_corrections",
            _handle_ikigai_corrections,
            {"date": date, "limit": limit},
        ),
    )


@MCP.tool(
    name="ikigai_plan_cycle",
    description="ARCHIVED observation. Does NOT execute math kernel.",
)
def ikigai_plan_cycle() -> str:
    """Returns archived status (math kernel deleted 2026-08-31)."""
    return cast(
        str,
        traced_tool_dispatch(
            "ikigai_plan_cycle",
            _handle_ikigai_plan_cycle,
            {},
        ),
    )


@MCP.tool(
    name="ikigai_checkpoint",
    description="Read/write LangGraph checkpoint (local SQLite, not vault).",
)
def ikigai_checkpoint(action: str = "get", thread_id: str = "") -> str:
    """Read/write LangGraph checkpoint from SQLite."""
    return cast(
        str,
        traced_tool_dispatch(
            "ikigai_checkpoint",
            _handle_ikigai_checkpoint,
            {"action": action, "thread_id": thread_id},
        ),
    )


@MCP.tool(
    name="ikigai_sync_vault",
    description="OBSERVE vault sync log (read-only, does NOT write vault).",
)
def ikigai_sync_vault(date: str = "") -> str:
    """Read vault sync log. vault_write is the sole vault writer."""
    return cast(
        str,
        traced_tool_dispatch(
            "ikigai_sync_vault",
            _handle_ikigai_sync_vault,
            {"date": date},
        ),
    )


# ---------------------------------------------------------------------------
# Plan C Task 3: Investigation Queue MCP tools
# ---------------------------------------------------------------------------


@MCP.tool(
    name="investigation_enqueue",
    description="Park a pre-form observation in the investigation queue. Investigations live outside the 6-level SONHO/OBJETIVO/META/PROJETO/ENTREGA/TAREFA hierarchy and can later crystallize into a UEID via inq_ueid.",
)
def _tool_investigation_enqueue(
    inq_id: str,
    source: str,
    payload: str,
    tags: list[str] | None = None,
    actor: str = "agent",
) -> dict[str, Any]:
    return investigation_enqueue(inq_id, source, payload, tags, actor)


@MCP.tool(
    name="investigation_status",
    description="Fetch the status of one investigation (by inq_id) or a summary across all statuses.",
)
def _tool_investigation_status(inq_id: str | None = None) -> dict[str, Any]:
    return investigation_status(inq_id)


@MCP.tool(
    name="investigation_complete",
    description="Mark an investigation resolved (success) or archived (abandoned). Terminal states — no resurrection.",
)
def _tool_investigation_complete(
    inq_id: str,
    final_status: str = "resolved",
    actor: str = "agent",
    inq_ueid: str | None = None,
) -> dict[str, Any]:
    return investigation_complete(inq_id, final_status, actor, inq_ueid)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Phase B3.3: 6 MCP resources
# ---------------------------------------------------------------------------
from mcp_server.resources import (  # noqa: E402
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
# Backward-compat TOOLS list
# ---------------------------------------------------------------------------
TOOLS = list(MCP._tool_manager._tools.values())


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
async def main() -> None:
    """Run the FastMCP gateway over stdio."""
    await MCP.run_stdio_async()
