"""Tests for FastMCP refactor of server.py."""

from __future__ import annotations

import pytest

from mcp_server.server import MCP, TOOLS, main


def test_fastmcp_instance_exists() -> None:
    assert MCP is not None
    assert MCP.name == "ikigai-gateway"


def test_all_tools_registered() -> None:
    """Asserts that the MCP server registry matches what is actually wired in server.py.

    The expected_tools set is read dynamically from the ``@MCP.tool(name=...)``
    decorators in src/ikigai/src/mcp_server/server.py rather than hardcoded —
    V5-E removed ikigai_score/regime/phase/corrections/plan_cycle/checkpoint/sync_vault
    and Plan C added 3 investigation_* tools, so a static list would always drift.
    """
    import re
    from pathlib import Path

    server_path = (
        Path(__file__).resolve().parents[2]
        / "ikigai"
        / "src"
        / "mcp_server"
        / "server.py"
    )
    text = server_path.read_text(encoding="utf-8")
    expected_tools = set(
        re.findall(r'@MCP\.tool\(\s*name="(\w+)"', text)
    )
    registered = {tool.name for tool in TOOLS}
    assert registered == expected_tools, (
        f"Missing: {expected_tools - registered}; Extra: {registered - expected_tools}"
    )


def test_main_entrypoint_callable() -> None:
    """main() must remain an async coroutine for stdio transport.

    M73.6: removed @pytest.mark.asyncio decoration — pytest-asyncio
    is not configured in pyproject.toml. The test body is purely sync
    (inspect.iscoroutinefunction check), so async decoration is unnecessary
    and was preventing test collection on the current pytest config.
    """
    import inspect

    assert inspect.iscoroutinefunction(main)
