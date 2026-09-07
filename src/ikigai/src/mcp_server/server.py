"""IKIGAi MCP server — stdio transport (T10.X slimmed orchestrator).

V5-E (2026-09-07 "Opção B-A — radical-máxima") stripped the
observation-only PAV/cycle-state wrappers + checkpoint sync:

  - 7 doomed ``@MCP.tool`` decorators DELETED (ikigai_score / regime /
    phase / corrections / plan_cycle / checkpoint / sync_vault) —
    all read PAV-written vault artifacts and were reclassified as
    anti-patterns per ADR-013 (planner-only). Test coverage that
    pinned their presence (test_v2_mcp_observation_wrappers_registered)
    was retired alongside its source (test_v2_prompt_chains.py).
  - 2 inline drift-pinned handlers DELETED (``_handle_ikigai_score`` +
    ``_handle_ikigai_sync_vault``) — replaced handler bodies read
    vault/ cycle-state / sync-log files; no IKIGAI write path.
  - 4 orphan helpers in handlers.py retired (``_db_path`` /
    ``_vault_root`` / ``_extract_frontmatter_field`` /
    ``_read_checkpoint``).

T10.X SPLIT (2026-09-06):
- ``handlers.py`` — 1 surviving handler body (``_handle_ikigai_decompose``)
- server.py keeps: imports + MCP init + 11 ``@MCP.tool`` decorators +
  6 ``@MCP.resource`` decorators + entrypoint

Run with: python run_mcp_server.py
"""

from __future__ import annotations

import json
from typing import Any, cast

from mcp.server.fastmcp import FastMCP

from mcp_server.handlers import _handle_ikigai_decompose
from mcp_server.investigation_complete import investigation_complete
from mcp_server.investigation_enqueue import investigation_enqueue
from mcp_server.investigation_status import investigation_status
from mcp_server.tracing import init_mcp_tracing, traced_tool_dispatch

MCP = FastMCP("ikigai-gateway")
init_mcp_tracing()  # idempotent


# ---------------------------------------------------------------------------
# Task I/O (Deep Agent ↔ interfaces via data/tasks.jsonl)
# ---------------------------------------------------------------------------
from sys_ikigai.vault.task_io import _read_tasks_from_data, _write_tasks_to_data  # noqa: E402

# ---------------------------------------------------------------------------
# @MCP.tool wrappers — 11 total (8 IKIGAI + 3 Plan C investigation)
# ---------------------------------------------------------------------------


@MCP.tool(
    name="ikigai_decompose",
    description="Decompose a Dream UEID into its full UEID hierarchy",
)
def ikigai_decompose(dream_ueid: str) -> str:
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
    return _read_tasks_from_data(horizon=horizon, done=done, project_id=project_id, limit=limit)


@MCP.tool(
    name="ikigai_mesh_show",
    description="Cross-fork view for one UEID (joins CLI + taskdog + solverforge_calendar)",
)
def _ikigai_mesh_show_tool(ueid: str) -> str:
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
    from mcp_server.tools_mesh import ikigai_health

    return ikigai_health()


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
    from mcp_server.tools_vault import vault_read as _handle_vault_read

    return cast(
        str,
        traced_tool_dispatch(
            "vault_read",
            _handle_vault_read,
            {"vault_path": vault_path},
        ),
    )


# --- Plan C Task 3: Investigation Queue MCP tools (3) ---


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
    return ueid_resource(ueid)


@MCP.resource("queue://pending")
def _queue_pending_resource() -> str:
    return queue_pending_resource()


@MCP.resource("queue://events/{event_id}")
def _queue_event_resource(event_id: str) -> str:
    return queue_event_resource(event_id)


@MCP.resource("health://gateway")
def _health_resource() -> str:
    return health_resource()


@MCP.resource("plans://cycles")
def _plans_cycles_resource() -> str:
    return plans_cycles_resource()


@MCP.resource("plans://cycles/{cycle_id}")
def _plans_cycle_resource(cycle_id: str) -> str:
    return plans_cycle_resource(cycle_id)


# Backward-compat TOOLS list
TOOLS = list(MCP._tool_manager._tools.values())


async def main() -> None:
    """Run the FastMCP gateway over stdio."""
    await MCP.run_stdio_async()
