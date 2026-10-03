"""mcp_bridge — loop-side MCP bridge for orchestrator/worker/verifier agents.

Mirrors the architecture of `src/ikigai/src/agents/v2/mcp_bridge.py` (M5 +
Phase 8.2) but lives at the LOOP layer (`.claude/loop/`). It exposes a thin,
callable Python surface for the **14 IKIGAI MCP tools** + **6 MCP resource
accessors** so loop sub-agents can do `ikigai_mesh_show(ueid=...)` without
hand-rolling the stdio JSON-RPC handshake from inside a worker worktree.

**M142 slice (6 read-only):** `ikigai_decompose`, `ikigai_read_tasks`,
`ikigai_mesh_show`, `ikigai_health`, `ikigai_task_create` (with
`dry_run=True` default), `taskdog_list`.

**M144 slice (6 write-side):** `vault_read`, `ikigai_write_tasks`,
`vault_write`, `investigation_enqueue`, `investigation_status`,
`investigation_complete`. Write tools inherit the server-side security
model (VaultLock for vault_write, path validation, audit logging).

**M145 slice (2 read-side taskdog + 6 resource accessors):** `taskdog_read`,
`taskdog_supports_field`, plus `read_ueid_resource`, `read_queue_pending_resource`,
`read_queue_event_resource`, `read_health_resource`,
`read_plans_cycles_resource`, `read_plans_cycle_resource`.

Architecture:
    Worker / Verifier / Orchestrator
        → `.claude/loop/mcp_bridge.ikigai_mesh_show(ueid=...)`
        → `_call(tool_name, args)` (wrapped in OTel span — M143)
        → module-level `_server.call(tool_name, args)`

`_server` is `None` by default — production must bind it to a FastMCP client
at loop startup (M146). Tests monkeypatch `_server` to a `MagicMock`
(FakeMcpServer pattern, same as v2 mcp_bridge).

Error policy: errors propagate. Caller catches and routes to its own
error_channel. Matches v2 mcp_bridge.py contract.

**OTel spans (M143).** Every `_call(...)` opens a span named
`{SPAN_PREFIX}{tool_name}` (e.g. `loop.mcp.ikigai_mesh_show`). Tracer name
prefix `loop.mcp` is deliberately distinct from v2's `ikigai.bridge` and
server-side `ikigai.mcp` so the 3 layers don't double-count in trace
exporters. Same 5-attribute schema as v2 mcp_bridge.py:_call (T-8.3.1,
2026-09-08): `tool.name`, `tool.arguments_hash`, `tool.duration_ms`, plus
`tool.error.class` / `tool.error.message` / `tool.error.traceback` on error.

Adding a new tool here requires:
  1. Append a sync wrapper to this module (e.g. `def ikigai_X(*, ...): ...`)
  2. The drift tests `test_drift_count_of_read_only_wrappers_is_6` (M142)
     and `test_drift_count_of_write_wrappers_is_6` (M144) auto-detect
     that count is now N+1 — update them explicitly. No silent growth.

Do NOT add PAV-math tools (`ikigai_observe_pav_state`, `ikigai_score_vectors`,
etc. — see `src/ikigai/src/mcp_server/server.py:218+`) here — they are
FORBIDDEN per ADR-013 (planner-only boundary).
"""

from __future__ import annotations

import hashlib
import json
import time
import traceback
from typing import Any

from opentelemetry.trace import Status, StatusCode

from src.ikigai.src.observability.otel_init import get_tracer

# Span-name prefix constant — pinned by drift test
# `test_m143_span_prefix_constant_matches_actual_span_name`. Changing this
# requires an explicit spec bump (no silent prefix rotation).
SPAN_PREFIX = "loop.mcp."

# Module-level server handle. Production binds this to the FastMCP gateway
# client (deferred to M146). Tests monkeypatch to a MagicMock. Same pattern
# as `src/ikigai/src/agents/v2/mcp_bridge.py:_server`.
_server: Any = None

# Module-level tracer — span prefix `loop.mcp.{tool_name}` is deliberately
# distinct from server-side `ikigai.mcp.{tool_name}` (see
# mcp_server/tracing.py:23) and v2-bridge-side `ikigai.bridge.{tool_name}`
# so the three layers don't double-count in trace exporters.
_tracer = get_tracer("loop.mcp")


# ---------------------------------------------------------------------------
# Core dispatcher
# ---------------------------------------------------------------------------


def _call(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Dispatch an MCP tool call inside an OTel span (M143).

    Span name: `{SPAN_PREFIX}{tool_name}` (e.g. `loop.mcp.ikigai_mesh_show`).
    Attributes mirror v2 `mcp_bridge.py:_call` (T-8.3.1, 2026-09-08):
      - tool.name (string)
      - tool.arguments_hash (SHA-256 of canonical JSON, first 16 hex)
      - tool.duration_ms (number)
      - tool.error.class (only on error)
      - tool.error.message (only on error, truncated to 500 chars)
      - tool.error.traceback (only on error, truncated to 3000 chars)

    Raises:
        RuntimeError: when `_server` is unbound (production must initialize
            the MCP Gateway client before invoking any ikigai_X wrapper).
        Exception: anything raised by `_server.call(...)` propagates after
            being recorded on the span. Caller (worker / verifier /
            orchestrator) catches and routes to its own error_channel.
    """
    if _server is None:
        raise RuntimeError(
            "mcp_bridge._server is not bound. "
            "Production code must initialize the MCP Gateway client "
            "before calling any ikigai_X function. "
            "See M142 SPEC §Honest scope — production binding is M146."
        )
    args_hash = hashlib.sha256(
        json.dumps(args, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    with _tracer.start_as_current_span(f"{SPAN_PREFIX}{tool_name}") as span:
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("tool.arguments_hash", args_hash)
        start = time.perf_counter()
        try:
            result = _server.call(tool_name, args)
            span.set_attribute("tool.duration_ms", (time.perf_counter() - start) * 1000)
            span.set_status(Status(StatusCode.OK))
            return result
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.set_attribute("tool.error.class", type(exc).__name__)
            span.set_attribute("tool.error.message", str(exc)[:500])
            tb_str = traceback.format_exc(limit=15)
            span.set_attribute("tool.error.traceback", tb_str[:3000])
            span.set_attribute("tool.duration_ms", (time.perf_counter() - start) * 1000)
            raise


# ---------------------------------------------------------------------------
# Read-only IKIGAI tools (M142 scope = 6)
# ---------------------------------------------------------------------------
#
# These are pure read-side or safe-default wrappers. NO `vault_write`, NO
# `ikigai_write_tasks`, NO `investigation_*` — see M144 for those.


def ikigai_decompose(*, task_id: str) -> dict[str, Any]:
    """Decompose a task into subtasks (read-shape; planner-side helper).

    Mirrors `src/ikigai/src/mcp_server/server.py` @MCP.tool registration.
    """
    return _call("ikigai_decompose", {"task_id": task_id})


def ikigai_read_tasks(*, horizon: str | None = None, limit: int = 50) -> dict[str, Any]:
    """Read IKIGAI planning-cycle tasks (horizon: 'week' | 'month' | None).

    Read-only. Default `limit=50` matches server-side default.
    """
    args: dict[str, Any] = {"limit": limit}
    if horizon is not None:
        args["horizon"] = horizon
    return _call("ikigai_read_tasks", args)


def ikigai_mesh_show(*, ueid: str) -> dict[str, Any]:
    """Join CLI / taskdog / solverforge_calendar slices for one UEID.

    Read-only — the canonical mesh read for orchestrator state inspection.
    """
    return _call("ikigai_mesh_show", {"ueid": ueid})


def ikigai_health() -> dict[str, Any]:
    """Health check for the MCP gateway. Returns {status, ...} dict.

    Read-only. Workers call this at tick start to verify gateway reachability.
    """
    return _call("ikigai_health", {})


def ikigai_task_create(*, ueid: str, fields: dict[str, Any] | None = None, dry_run: bool = True) -> dict[str, Any]:
    """Create a task under a UEID. Read-shape via `dry_run=True` default.

    NOTE: this wrapper defaults to `dry_run=True` to preserve the read-only
    invariant of M142. A worker that actually wants to create a task should
    use `python -m life.cli task add ...` (canonical write path) or escalate
    to v2 graph (which has its own audit log). The dry_run=True default
    means production callers must explicitly opt-in to a write, which the
    drift test pins (see `test_m142_task_create_default_is_dry_run`).
    """
    args: dict[str, Any] = {"ueid": ueid, "dry_run": dry_run}
    if fields is not None:
        args["fields"] = fields
    return _call("ikigai_task_create", args)


def taskdog_list(*, status: str | None = None, limit: int | None = None) -> dict[str, Any]:
    """List taskdog tasks (read-only fork tool).

    Status filter: 'pending' | 'completed' | None (all).
    """
    args: dict[str, Any] = {}
    if status is not None:
        args["status"] = status
    if limit is not None:
        args["limit"] = limit
    return _call("taskdog_list", args)


# ---------------------------------------------------------------------------
# M144 slice (6 write-side). NO PAV-math tools (FORBIDDEN per ADR-013).
# ---------------------------------------------------------------------------


def vault_read(vault_path: str) -> dict[str, Any]:
    """Read a markdown file from the vault (read-side write-tool companion).

    Returns parsed frontmatter, body, sha256, mtime. Read-only — never
    writes. Mirror of `vault_write` security model (path validation,
    vault-rooted paths only). Server signature mirrors
    `src/ikigai/src/mcp_server/server.py:148-159`.
    """
    return _call("vault_read", {"vault_path": vault_path})


def ikigai_write_tasks(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Write structured tasks to `data/tasks.jsonl` — Deep Agent output.

    Server signature: `src/ikigai/src/mcp_server/server.py:67-71`.
    Returns a JSON string describing the write outcome.
    """
    return _call("ikigai_write_tasks", {"tasks": tasks})


def vault_write(
    *,
    vault_path: str,
    frontmatter: dict[str, Any],
    body: str,
) -> dict[str, Any]:
    """Write a markdown file to the vault — canonical writer per ADR-012.

    Rejects paths outside `vault/`, absolute paths, empty writes.
    Uses VaultLock for concurrency safety; atomic via tmp-file + rename.

    All three kwargs are REQUIRED — no defaults. A typo or missing field
    should fail loud, not silently write a half-baked note.
    """
    return _call(
        "vault_write",
        {
            "vault_path": vault_path,
            "frontmatter": frontmatter,
            "body": body,
        },
    )


def investigation_enqueue(
    *,
    inq_id: str,
    source: str,
    payload: str,
    tags: list[str] | None = None,
    actor: str = "loop-agent",
) -> dict[str, Any]:
    """Park a pre-form observation in the investigation queue.

    Investigations live outside the 6-level SONHO/OBJETIVO/META/PROJETO/
    ENTREGA/TAREFA hierarchy and can later crystallize into a UEID via
    `inq_ueid` on `investigation_complete`.

    `actor` defaults to `"loop-agent"` — distinguishable from v2 graph's
    default `"agent"` and operator-TUI's typed actor. Trivial to grep
    by source.
    """
    args: dict[str, Any] = {
        "inq_id": inq_id,
        "source": source,
        "payload": payload,
        "actor": actor,
    }
    if tags is not None:
        args["tags"] = tags
    return _call("investigation_enqueue", args)


def investigation_status(inq_id: str | None = None) -> dict[str, Any]:
    """Fetch the status of one investigation (by inq_id) or a summary.

    Read-side. Pass `inq_id=None` to get a summary across all statuses.
    """
    return _call("investigation_status", {"inq_id": inq_id})


def investigation_complete(
    *,
    inq_id: str,
    final_status: str = "resolved",
    actor: str = "loop-agent",
    inq_ueid: str | None = None,
) -> dict[str, Any]:
    """Mark an investigation resolved (success) or archived (abandoned).

    Terminal state — no resurrection. Pass `inq_ueid` when the
    investigation crystallizes into a UEID.

    `final_status` defaults to `"resolved"`. Use `"archived"` for
    abandoned investigations.
    """
    args: dict[str, Any] = {
        "inq_id": inq_id,
        "final_status": final_status,
        "actor": actor,
    }
    if inq_ueid is not None:
        args["inq_ueid"] = inq_ueid
    return _call("investigation_complete", args)


# ---------------------------------------------------------------------------
# M145 slice (2 read-side taskdog forks). NO PAV-math tools (ADR-013).
# ---------------------------------------------------------------------------


def taskdog_read(ueid: str, db_path: str | None = None) -> dict[str, Any]:
    """Get a taskdog task slice by UEID (read-only fork tool).

    Returns `null` slice if not found. `db_path` is an optional override
    for tests; omit in production (the canonical path is auto-discovered).
    """
    args: dict[str, Any] = {"ueid": ueid}
    if db_path is not None:
        args["db_path"] = db_path
    return _call("taskdog_read", args)


def taskdog_supports_field(field_name: str) -> dict[str, Any]:
    """Capability check: is `field_name` a supported taskdog field?

    Returns `{"field": field_name, "supported": bool}`.
    Read-only; useful before writing to avoid rejection.
    """
    return _call("taskdog_supports_field", {"field_name": field_name})


# ---------------------------------------------------------------------------
# M148 slice — taskdog write tools + search. All writes go through the
# mesh review queue (ADR-014). Validation happens in agent_consumer; the
# adapter then mutates the SQLite store on APPROVE.
# ---------------------------------------------------------------------------
def taskdog_create(
    ueid: str,
    title: str,
    due: str | None = None,
    priority: str | int | None = None,
    planned_start: str | None = None,
    planned_end: str | None = None,
) -> dict[str, Any]:
    """Create a task. Enqueues a CREATE TaskChange to the review queue.

    Args:
        ueid: Canonical join key (validated by MCP server).
        title: Task title (>=5 chars, not 'todo'/'tbd', per agent_consumer).
        due: Optional YYYY-MM-DD due date.
        priority: Optional priority as int (1=high, 2=medium, 3=low) or
            string ("high", "medium", "low").
        planned_start, planned_end: Optional planned dates (YYYY-MM-DD).
    """
    args: dict[str, Any] = {"ueid": ueid, "title": title}
    if due is not None:
        args["due"] = due
    if priority is not None:
        args["priority"] = priority
    if planned_start is not None:
        args["planned_start"] = planned_start
    if planned_end is not None:
        args["planned_end"] = planned_end
    return _call("taskdog_create", args)


def taskdog_done(ueid: str) -> dict[str, Any]:
    """Mark a task as done. Enqueues a DONE TaskChange (no fields).

    Idempotent at the adapter layer — marking an already-done task is a
    no-op (not an error).
    """
    return _call("taskdog_done", {"ueid": ueid})


def taskdog_set_status(ueid: str, status: str) -> dict[str, Any]:
    """Update task status. Enqueues an UPDATE with status=field.

    Allowed: planned, in_progress, done, cancelled. For marking done
    semantically, prefer `taskdog_done` (takes no fields).
    """
    if status not in ("planned", "in_progress", "done", "cancelled"):
        raise ValueError(
            f"invalid status {status!r}; "
            "allowed: planned, in_progress, done, cancelled"
        )
    return _call("taskdog_set_status", {"ueid": ueid, "status": status})


def taskdog_set_priority(ueid: str, priority: str | int) -> dict[str, Any]:
    """Update task priority. Enqueues an UPDATE with priority=field.

    Accepts int (1=high, 2=medium, 3=low) or string ("high", "medium",
    "low"). Adapter normalizes both forms.
    """
    return _call("taskdog_set_priority", {"ueid": ueid, "priority": priority})


def taskdog_set_due(ueid: str, due: str) -> dict[str, Any]:
    """Update task due date (YYYY-MM-DD). Enqueues an UPDATE."""
    return _call("taskdog_set_due", {"ueid": ueid, "due": due})


def taskdog_set_planned_dates(
    ueid: str,
    planned_start: str,
    planned_end: str,
) -> dict[str, Any]:
    """Update both planned_start and planned_end dates. Enqueues an UPDATE."""
    return _call(
        "taskdog_set_planned_dates",
        {"ueid": ueid, "planned_start": planned_start, "planned_end": planned_end},
    )


def taskdog_cancel(ueid: str) -> dict[str, Any]:
    """Soft-cancel a task (status='cancelled'). Enqueues an UPDATE.

    For hard removal, use `taskdog_delete` instead.
    """
    return _call("taskdog_cancel", {"ueid": ueid})


def taskdog_delete(ueid: str) -> dict[str, Any]:
    """Hard-delete a task from taskdog. Enqueues a DELETE TaskChange.

    Irreversible. Prefer `taskdog_cancel` if you might want to restore.
    """
    return _call("taskdog_delete", {"ueid": ueid})


def taskdog_search(
    query: str,
    status: str | None = None,
    priority: str | int | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search tasks by substring match on name + filters.

    Read-only — does NOT enqueue anything, hits the adapter directly.
    Useful for finding tasks before applying mutations.
    """
    args: dict[str, Any] = {"query": query, "limit": limit}
    if status is not None:
        args["status"] = status
    if priority is not None:
        args["priority"] = priority
    return _call("taskdog_search", args)


# ---------------------------------------------------------------------------
# M163/M164 slice — full MCP surface for v2 schema (tags, deps, notes,
# pause/reopen, audit). Mirrors the 13 @mcp.tool functions in
# `src/ikigai/src/mcp_server/taskdog_tools.py` so `_build_lc_tools()` in
# `src/ikigai/src/agents/taskdog_mcp_graph.py` exposes them to the
# ReAct agent.
#
# All write tools enqueue a TaskChange to the mesh review queue per
# ADR-014. Validation happens in agent_consumer; the adapter then
# mutates the SQLite store on APPROVE.
#
# Read-only tools (suffix `_list`, `_show`, `_blocked`, `_audit`) hit
# the adapter directly and do NOT enqueue anything.
# ---------------------------------------------------------------------------


def taskdog_tag_add(ueid: str, tags: list[str]) -> dict[str, Any]:
    """Append tags to a task's tag set. Idempotent. Routes through review queue."""
    return _call("taskdog_tag_add", {"ueid": ueid, "tags": list(tags)})


def taskdog_tag_remove(ueid: str, tags: list[str]) -> dict[str, Any]:
    """Remove tags from a task. Missing tags are no-ops. Routes through review queue."""
    return _call("taskdog_tag_remove", {"ueid": ueid, "tags": list(tags)})


def taskdog_tag_list(ueid: str, db_path: str | None = None) -> dict[str, Any]:
    """Return the canonical tag list for a task (read-only). Empty list if no tags."""
    args: dict[str, Any] = {"ueid": ueid}
    if db_path is not None:
        args["db_path"] = db_path
    return _call("taskdog_tag_list", args)


def taskdog_tag_clear(ueid: str) -> dict[str, Any]:
    """Remove all tags from a task. Idempotent. Routes through review queue."""
    return _call("taskdog_tag_clear", {"ueid": ueid})


def taskdog_dep_add(ueid: str, other_ueid: str) -> dict[str, Any]:
    """Add a dependency: this task depends on `other_ueid` being done.

    Routes through review queue.
    """
    return _call("taskdog_dep_add", {"ueid": ueid, "other_ueid": other_ueid})


def taskdog_dep_remove(ueid: str, other_ueid: str) -> dict[str, Any]:
    """Remove a dependency on `other_ueid`. Routes through review queue."""
    return _call("taskdog_dep_remove", {"ueid": ueid, "other_ueid": other_ueid})


def taskdog_dep_list(ueid: str, db_path: str | None = None) -> dict[str, Any]:
    """Return the dependency list for a task (read-only). Empty list if no deps."""
    args: dict[str, Any] = {"ueid": ueid}
    if db_path is not None:
        args["db_path"] = db_path
    return _call("taskdog_dep_list", args)


def taskdog_dep_blocked(db_path: str | None = None) -> dict[str, Any]:
    """Return tasks with at least one unmet dependency (read-only).

    Scans all tasks.
    """
    args: dict[str, Any] = {}
    if db_path is not None:
        args["db_path"] = db_path
    return _call("taskdog_dep_blocked", args)


def taskdog_note_add(ueid: str, text: str) -> dict[str, Any]:
    """Append a free-text note to a task. Routes through review queue.

    Notes are stored in the audit_log with action='note_add'.
    """
    return _call("taskdog_note_add", {"ueid": ueid, "text": text})


def taskdog_note_show(ueid: str, db_path: str | None = None) -> dict[str, Any]:
    """Return the notes (audit_log entries with action='note_add') for a task (read-only)."""
    args: dict[str, Any] = {"ueid": ueid}
    if db_path is not None:
        args["db_path"] = db_path
    return _call("taskdog_note_show", args)


def taskdog_pause(ueid: str) -> dict[str, Any]:
    """Pause a task (status='paused'). Routes through review queue."""
    return _call("taskdog_pause", {"ueid": ueid})


def taskdog_reopen(ueid: str) -> dict[str, Any]:
    """Reopen a task (status='planned'). Routes through review queue."""
    return _call("taskdog_reopen", {"ueid": ueid})


def taskdog_audit(ueid: str, db_path: str | None = None) -> dict[str, Any]:
    """Return the full audit_log array for a task (read-only)."""
    args: dict[str, Any] = {"ueid": ueid}
    if db_path is not None:
        args["db_path"] = db_path
    return _call("taskdog_audit", args)


# ---------------------------------------------------------------------------
# M145 slice — MCP resource accessors
# ---------------------------------------------------------------------------
#
# FastMCP resources use `read_resource(uri)`, NOT `call(tool_name, args)`.
# So resource accessors are separate helper functions that delegate to
# `_server.read_resource(uri)` — they do NOT go through `_call(...)` and
# therefore do NOT emit OTel spans (lesson from M143 deferral: OTel for
# resources lands in M146 if it lands at all).
#
# The URI map (`RESOURCE_URIS`) is pinned by drift test
# `test_m145_resource_uri_dict_length_is_6` so URI drift between server
# (`@MCP.resource` decorators) and bridge is caught immediately.

RESOURCE_URIS: dict[str, str] = {
    "ueid": "ueid://{ueid}",
    "queue_pending": "queue://pending",
    "queue_event": "queue://events/{event_id}",
    "health": "health://gateway",
    "plans_cycles": "plans://cycles",
    "plans_cycle": "plans://cycles/{cycle_id}",
}


def read_ueid_resource(ueid: str) -> Any:
    """Read the `ueid://{ueid}` resource — task slice by UEID across forks.

    Returns the parsed FastMCP resource envelope (a `dict[str, Any]`),
    not the raw envelope shape. Parsing happens in `_parse_resource_envelope`
    (M146). Falls back to raw payload if envelope shape unrecognized.
    """
    return _parse_resource_envelope(
        _server.read_resource(RESOURCE_URIS["ueid"].format(ueid=ueid))
    )


def read_queue_pending_resource() -> Any:
    """Read the `queue://pending` resource — pending TaskChange events.

    Returns parsed envelope.
    """
    return _parse_resource_envelope(
        _server.read_resource(RESOURCE_URIS["queue_pending"])
    )


def read_queue_event_resource(event_id: str) -> Any:
    """Read the `queue://events/{event_id}` resource — one resolved event."""
    return _parse_resource_envelope(
        _server.read_resource(RESOURCE_URIS["queue_event"].format(event_id=event_id))
    )


def read_health_resource() -> Any:
    """Read the `health://gateway` resource — MCP gateway heartbeat."""
    return _parse_resource_envelope(
        _server.read_resource(RESOURCE_URIS["health"])
    )


def read_plans_cycles_resource() -> Any:
    """Read the `plans://cycles` resource — all planning cycles summary."""
    return _parse_resource_envelope(
        _server.read_resource(RESOURCE_URIS["plans_cycles"])
    )


def read_plans_cycle_resource(cycle_id: str) -> Any:
    """Read the `plans://cycles/{cycle_id}` resource — one cycle detail."""
    return _parse_resource_envelope(
        _server.read_resource(
            RESOURCE_URIS["plans_cycle"].format(cycle_id=cycle_id)
        )
    )


# ---------------------------------------------------------------------------
# M146 — resource envelope parsing
# ---------------------------------------------------------------------------
#
# FastMCP `read_resource(uri)` returns a `ReadResourceResult` whose shape
# varies by SDK version:
#   - v1.x: list of `(uri, mime_type, text|blob)` tuples (`ReadResourceContents`)
#   - v0.x: list of dicts `{uri, mimeType, text}` or single dict
#   - raw payload: bytes or str (some legacy servers)
#
# `_parse_resource_envelope` normalizes all 3 shapes into a single
# `dict[str, Any]` that workers can consume uniformly. Falls back to
# `{"raw": payload}` when shape is unrecognized so callers always get
# something predictable.


def _parse_resource_envelope(payload: Any) -> dict[str, Any]:
    """Normalize FastMCP `read_resource(uri)` response into a dict.

    Handles:
      1. Single dict: `{"uri": ..., "mimeType": ..., "text": ...}` → as-is
      2. List of dicts / ReadResourceContents: concat `.text` or `.blob`
      3. Raw str/bytes: wrap in `{"raw": payload}`
      4. Anything else: `{"raw": payload}` (fallback)
    """
    # Shape 3: raw str or bytes
    if isinstance(payload, (str, bytes)):
        return {"raw": payload}

    # Shape 1: single dict (v0.x or simple server)
    if isinstance(payload, dict):
        # Already a dict — pass through, but normalize keys
        if "uri" in payload or "text" in payload or "mimeType" in payload:
            return payload
        return {"raw": payload}

    # Shape 2: list of ReadResourceContents / dicts
    if isinstance(payload, list):
        if not payload:
            return {"contents": []}
        items: list[dict[str, Any]] = []
        text_parts: list[str] = []
        for item in payload:
            # ReadResourceContents has .uri, .mimeType, .text or .blob attrs
            if hasattr(item, "text"):
                text_parts.append(str(item.text))
                items.append(
                    {
                        "uri": getattr(item, "uri", None),
                        "mimeType": getattr(item, "mimeType", None),
                        "text": str(item.text),
                    }
                )
            elif hasattr(item, "blob"):
                items.append(
                    {
                        "uri": getattr(item, "uri", None),
                        "mimeType": getattr(item, "mimeType", None),
                        "blob": str(item.blob),
                    }
                )
            elif isinstance(item, dict):
                items.append(item)
                if "text" in item:
                    text_parts.append(str(item["text"]))
            else:
                items.append({"raw": str(item)})
        if text_parts and all(
            i.get("mimeType") is None or i.get("mimeType", "").startswith(("text/", "application/json"))
            for i in items
        ):
            # Concatenated text — return as single text + items list
            joined = "\n".join(text_parts)
            try:
                import json as _json
                return _json.loads(joined)
            except (ValueError, TypeError):
                return {"text": joined, "items": items}
        return {"contents": items}

    # Shape 4: fallback
    return {"raw": payload}
