"""mcp_bridge — sync wrappers around async MCP Gateway calls.

Architecture:
    v2 Node → mcp_bridge.ikigai_X(**kwargs) → async mcp_client.call()
        → MCP Gateway stdio (production)
        → FakeMcpServer (tests via monkeypatch on _server)

12 wrappers, one per canonical IKIGAI_TOOL. Adding a new tool
requires editing this file AND the drift detector in
src/ikigai/tests/test_canonical_scope.py — do NOT add silently.

Error policy: errors propagate. Caller catches and routes to
error_channel for graceful degradation per Phase 8.2 SPEC §3.
"""

from __future__ import annotations

import asyncio
from typing import Any

# Module-level server handle. Production binds this to the
# FastMCP gateway client. Tests monkeypatch it to FakeMcpServer.
_server: Any = None


def _call(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Run an async MCP call synchronously."""
    if _server is None:
        raise RuntimeError(
            "mcp_bridge._server is not bound. "
            "Production code must initialize the MCP Gateway client "
            "before calling any ikigai_X function."
        )
    return _server.call(tool_name, args)


# --- 12 IKIGAI_TOOLS wrappers (canonical list) ---


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
# Phase 8.2 wires only the 9 graph-facing tools above. See SPEC §2.
