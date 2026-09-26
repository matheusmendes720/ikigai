"""mcp_bridge — loop-side MCP bridge for orchestrator/worker/verifier agents.

Mirrors the architecture of `src/ikigai/src/agents/v2/mcp_bridge.py` (M5 +
Phase 8.2) but lives at the LOOP layer (`.claude/loop/`). It exposes a thin,
callable Python surface for the **6 read-only IKIGAI MCP tools** so loop
sub-agents can do `ikigai_mesh_show(ueid=...)` without hand-rolling the
stdio JSON-RPC handshake from inside a worker worktree.

**READ-ONLY slice (M142).** Write-side tools (`vault_write`,
`ikigai_write_tasks`, `investigation_*`) are deliberately NOT exposed here —
they live in v2 graph / operator-TUI per ADR-012/013 and arrive as M144.

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
  2. The drift test `tests/test_m142_mcp_bridge.py::test_drift_count_of_wrapped_tools_is_6`
     auto-detects that count is now N+1 — update it explicitly. No silent growth.

Do NOT add `vault_write` / `ikigai_write_tasks` / `investigation_*` here
without an M144 spec — see `.claude/agents/loop/orchestrator.md` for the
planner-only boundary (ADR-013).
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
