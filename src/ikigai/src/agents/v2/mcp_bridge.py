"""mcp_bridge — sync wrappers around async MCP Gateway calls.

Architecture:
    v2 Node → mcp_bridge.ikigai_decompose(**kwargs) → async mcp_client.call()
        → MCP Gateway stdio (production)
        → FakeMcpServer (tests via monkeypatch on _server)

1 graph-facing wrapper (``ikigai_decompose``). The 8 PAV-flavored
wrappers that existed in earlier versions (``ikigai_observe_pav_state``,
``ikigai_score_vectors``, ``ikigai_heuristics``, ``ikigai_balance``,
``ikigai_plan``, ``ikigai_reflect``, ``ikigai_tag_and_persist``,
``ikigai_commit_summary``) were REMOVED in M12 (T-12.1) per the M11
diagnosis Priority 1, item 1 (L4 G-1): those names were registered in
this bridge but absent from ``server.py``'s ``@MCP.tool`` registry after
V5-E (``b960e852``) deleted the 7 PAV-math tools. Wrapping a
non-existent server tool silently failed at runtime via dict-protocol
detector — the bridge and server drifted apart silently.

8 v2 nodes that previously called the deleted wrappers
(observe/balance/heuristics/commit/plan/reflect/score_vectors/
tag_and_persist) all guard their call with ``try/except`` per Phase 8.2
SPEC §3 — they now route to ``error_channel`` and continue. The drift
test ``test_mcp_bridge_wrapped_tool_count_matches_canonical`` (T-12.1)
pins bridge/server alignment so future drift trips the detector instead
of silently growing agent surface (T-11.5 G-2).

Adding a new tool requires editing this file AND the drift detector in
src/ikigai/tests/test_canonical_scope.py — do NOT add silently.

Error policy: errors propagate. Caller catches and routes to
error_channel for graceful degradation per Phase 8.2 SPEC §3.

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

# Module-level server handle. Production binds this to the
# FastMCP gateway client. Tests monkeypatch it to FakeMcpServer.
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
    args_hash = hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()[
        :16
    ]
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


# ---------------------------------------------------------------------------
# Graph-facing wrappers — MUST be a subset of server.py's @MCP.tool registry.
# Drift-detected by test_mcp_bridge_wrapped_tool_count_matches_canonical.
# ---------------------------------------------------------------------------


def ikigai_decompose(*, task_id: str) -> dict[str, Any]:
    """Decompose a task into subtasks."""
    return _call("ikigai_decompose", {"task_id": task_id})
