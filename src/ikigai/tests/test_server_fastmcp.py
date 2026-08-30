"""Tests for FastMCP refactor of server.py."""
from __future__ import annotations

import pytest

from mcp_server.server import MCP, main, TOOLS


def test_fastmcp_instance_exists() -> None:
    assert MCP is not None
    assert MCP.name == "ikigai-gateway"


def test_all_ten_tools_registered() -> None:
    expected_tools = {
        "ikigai_score",
        "ikigai_regime",
        "ikigai_phase",
        "ikigai_decompose",
        "ikigai_corrections",
        "ikigai_plan_cycle",
        "ikigai_checkpoint",
        "ikigai_sync_vault",
        "ikigai_write_tasks",
        "ikigai_read_tasks",
        # Phase B3.2 additions
        "ikigai_mesh_show",
        "ikigai_task_create",
        "ikigai_health",
        # Phase B6.7 additions
        "vault_write",
    }
    registered = {tool.name for tool in TOOLS}
    assert registered == expected_tools, (
        f"Missing: {expected_tools - registered}; "
        f"Extra: {registered - expected_tools}"
    )


@pytest.mark.asyncio
async def test_main_entrypoint_callable() -> None:
    """main() must remain an async coroutine for stdio transport."""
    import inspect
    assert inspect.iscoroutinefunction(main)
