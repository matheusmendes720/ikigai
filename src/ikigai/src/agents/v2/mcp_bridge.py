"""mcp_bridge — sync wrappers around async MCP Gateway calls.

Architecture:
    v2 Node → mcp_bridge.ikigai_X(**kwargs) → async mcp_client.call()
        → MCP Gateway stdio (production)
        → FakeMcpServer (tests via monkeypatch on _server)

9 graph-facing wrappers (the 12 IKIGAI_TOOLS total includes 3
infrastructure-level tools not invoked from v2 nodes). Adding a new tool
requires editing this file AND the drift detector in
src/ikigai/tests/test_canonical_scope.py — do NOT add silently.

Error policy: errors propagate. Caller catches and routes to
error_type for graceful degradation per Phase 8.2 SPEC §3.

Observability (T-8.3.1): every _call() invocation opens an OTel
span `ikigai.bridge.{tool_name}` so bridge dispatch latency and
errors are visible alongside the server-side `ikigai.mcp.{tool_name}`
spans emitted by mcp_server/tracing.py.
"""

from __future__ import annotations

import hashlib
import json
import time
import traceback
from typing import Any

from opentelemetry.trace import Status, StatusCode

from src.ikigai.src.observability.otel_init import get_tracer

# Production binding — spawn the FastMCP gateway subprocess and return a
# sync-call client (FastMcpClient.call() mirrors FakeMcpServer.call()).
from src.ikigai.src.agents.v2 import mcp_client as mcp_client_mod  # noqa: E402

bind_prod_server = mcp_client_mod.bind_server_to_gateway

# Module-level server handle — production binds the FastMCP client; tests monkeypatch to FakeMcpServer.
_server: Any = None

# Module-level tracer — span prefix `ikigai.bridge.{tool_name}` is
# deliberately distinct from server-side `ikigai.mcp.{tool_name}`
# (see mcp_server/tracing.py:23) so the two layers don't double-count
# in trace exporters.
_tracer = get_tracer("ikigai.bridge")


def _call(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Run an async MCP call synchronously inside an OTel span.

    Span name: ikigai.bridge.{tool_name}
    Attributes mirror mcp_server/tracing.py:traced_tool_dispatch:
      - tool.name (string)
      - tool.arguments_hash (SHA-256 of canonical JSON, first 16 hex)
      - tool.duration_ms (number)
      - tool.error.class (only on error)
      - tool.error.message (only on error, truncated to 500 chars)
      - tool.error.traceback (only on error, truncated to 3000 chars)
    """
    if _server is None:
        raise RuntimeError(
            "mcp_bridge._server is not bound. "
            "Production code must initialize the MCP Gateway client "
            "before calling any ikigai_X function."
        )
    args_hash = hashlib.sha256(
        json.dumps(args, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    with _tracer.start_as_current_span(f"ikigai.bridge.{tool_name}") as span:
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


# --- 9 graph-facing IKIGAI_TOOL wrappers ---


def ikigai_observe_pav_state(*, date: str) -> dict[str, Any]:
    """Read Q_HE observation for a given date."""
    return _call("ikigai_observe_pav_state", {"date": date})


def ikigai_score_vectors(*, vectors: list[float]) -> dict[str, Any]:
    """Score a list of priority vectors."""
    return _call("ikigai_score_vectors", {"vectors": vectors})


def ikigai_heuristics(*, context: dict[str, Any]) -> dict[str, Any]:
    """Apply heuristics to a planning context."""
    return _call("ikigai_heuristics", {"context": context})


def ikigai_balance(*, load: float) -> dict[str, Any]:
    """Compute load balance adjustment."""
    return _call("ikigai_balance", {"load": load})


def ikigai_decompose(*, task_id: str) -> dict[str, Any]:
    """Decompose a task into subtasks."""
    return _call("ikigai_decompose", {"task_id": task_id})


def ikigai_plan(*, cycle_id: str) -> dict[str, Any]:
    """Build a plan for a planning cycle."""
    return _call("ikigai_plan", {"cycle_id": cycle_id})


def ikigai_reflect(*, cycle_id: str) -> dict[str, Any]:
    """Reflect on a completed cycle."""
    return _call("ikigai_reflect", {"cycle_id": cycle_id})


def ikigai_tag_and_persist(*, ueid: str) -> dict[str, Any]:
    """Read tags for a UEID (read-only — vault_write is separate work)."""
    return _call("ikigai_tag_and_persist", {"ueid": ueid})


def ikigai_commit_summary(*, cycle_id: str) -> dict[str, Any]:
    """Build a commit summary for a cycle."""
    return _call("ikigai_commit_summary", {"cycle_id": cycle_id})


# The remaining 3 IKIGAI_TOOLS are infrastructure-level (vault_write,
# investigation_enqueue, sync_vault) — not used by v2 graph nodes.
# Phase 8.3 wires production binding; see SPEC §2 for the 9 wrappers.
