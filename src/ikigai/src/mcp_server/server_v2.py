"""Server v2 — zero-cost re-export of FastMCP-refactored server.

Lets downstream imports like `from mcp_server.server_v2 import main` work
without forcing renames in run_mcp_server.py or tests.

Created in Phase B3 (2026-08-28).
"""

from mcp_server.server import (
    MCP,
    TOOLS,
    ikigai_checkpoint,
    ikigai_corrections,
    ikigai_decompose,
    ikigai_phase,
    ikigai_plan_cycle,
    ikigai_read_tasks,
    ikigai_regime,
    ikigai_score,
    ikigai_sync_vault,
    ikigai_write_tasks,
    main,
)

__all__ = [
    "MCP",
    "TOOLS",
    "ikigai_checkpoint",
    "ikigai_corrections",
    "ikigai_decompose",
    "ikigai_phase",
    "ikigai_plan_cycle",
    "ikigai_read_tasks",
    "ikigai_regime",
    "ikigai_score",
    "ikigai_sync_vault",
    "ikigai_write_tasks",
    "main",
]
