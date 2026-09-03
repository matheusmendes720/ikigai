"""Taskdog MCP server — Path 3 of the 3-paths taskdog architecture.

Exposes the 4 taskdog @tools as a standalone MCP server, so external
MCP clients (not the IKIGAI agent) can drive taskdog directly over
the MCP protocol. Per `docs/design-system/24-taskdog-paths-architecture.md`:

  Path 1 (CANONICAL) — IKIGAI agent @tool → subprocess → taskdog.exe
  Path 2 (alternative) — mesh SQLite direct read/write
  Path 3 (this)       — standalone MCP server over stdio

Path 1 remains canonical. Path 3 exists for external MCP clients
that don't go through the agent harness.

Run with:
    python -m src.taskdog_mcp

Architecture:
- Re-uses the same subprocess + reliability patterns as Path 1
  (CircuitBreaker + retry_with_backoff). See src/ikigai/src/agents/tools.py.
- Does NOT import IKIGAI agent code — standalone server.
- vault_write invariant preserved (taskdog doesn't touch vault/).
"""

from __future__ import annotations

from src.taskdog_mcp.server import MCP, main

__all__ = ["MCP", "main"]
