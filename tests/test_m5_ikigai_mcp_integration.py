"""M5 IKIGAI MCP integration tests.

Exercises the IKIGAI MCP server (src/ikigai/src/mcp_server/server.py) via
the official MCP Python SDK stdio client. Performs the canonical
`initialize` -> `tools/call` handshake and asserts the `ikigai_health`
response shape matches what `tools_mesh.ikigai_health()` produces.

Acceptance: SPEC.md criterion #5 (M5 IKIGAI MCP Integration).

Cost: $0 (no LLM). Subprocess spawn via stdio_client + JSON-RPC only.

Uses the proven stdio handshake path from `scripts/mcp_inspect.py` (which
has shipped as the B3.5 contract test). Earlier raw-bytes draft hung on
FastMCP framing — switched to SDK client (same approach as the inspector).

NOTE: This test file lives at <repo>/tests/ (per CLAUDE.md `## Where the rest lives`).
The conftest at <repo>/tests/conftest.py handles sys.path and tempdir redirect.
"""

from __future__ import annotations

import asyncio
import json
import os
import platform
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO_ROOT = Path(__file__).resolve().parent.parent
IKIGAI_DIR = REPO_ROOT / "src" / "ikigai"
IKIGAI_SRC = IKIGAI_DIR / "src"
LIFE_SRC = REPO_ROOT / "src"


def _build_pythonpath() -> str:
    """Build PYTHONPATH for the gateway subprocess.

    Three entries are required to satisfy every import style in the codebase
    (per CLAUDE.md `## Import-Path Rules`):
      1. REPO_ROOT  -- for dotted-prefix `from src.contracts.common import ...`
                       (src/contracts/base.py:11 uses this style)
      2. LIFE_SRC   -- for bare-namespace `from contracts.investigation import ...`
                       (src/ikigai/src/mcp_server/investigation_complete.py:7)
      3. IKIGAI_SRC -- so `python -m mcp_server` resolves the package
                       (src/ikigai/src/mcp_server/__init__.py)

    Puts REPO_ROOT first so dotted-prefix imports get priority; mirrors
    scripts/mcp_inspect.py:build_pythonpath (which uses src_dir + mcp_src).
    """
    sep = ";" if platform.system() == "Windows" else ":"
    return f"{REPO_ROOT}{sep}{LIFE_SRC}{sep}{IKIGAI_SRC}"


def _server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-u", "-m", "mcp_server"],
        # CRITICAL: cwd must be src/ikigai/src (the INNER src), NOT src/ikigai.
        # When cwd=src/ikigai, Python prepends '' to sys.path -> resolves
        # `import contracts.X` to <repo>/src/ikigai/contracts/ (an old,
        # shadowed editable-install layout) instead of <repo>/src/contracts/.
        # The inner-src layout sidesteps the shadow. Same as scripts/mcp_inspect.py.
        cwd=str(IKIGAI_SRC),
        env={**os.environ, "PYTHONPATH": _build_pythonpath()},
    )


async def _do_health_handshake() -> dict:
    """Spawn the gateway, perform initialize + tools/call ikigai_health.

    Returns the parsed JSON payload from ikigai_health (the JSON-decoded
    text block, not the MCP envelope). Raises on any handshake failure.
    """
    params = _server_params()
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            # Touch serverInfo so the assert below has something to read
            assert init.serverInfo.name, "serverInfo.name empty"

            result = await session.call_tool("ikigai_health", {})
            # FastMCP wraps string tool outputs in a TextContent block.
            assert result.content, f"ikigai_health returned no content: {result!r}"
            first = result.content[0]
            assert getattr(first, "type", None) == "text", (
                f"expected text content block, got: {first!r}"
            )
            return json.loads(first.text)


async def _do_tools_list() -> list[str]:
    """Spawn the gateway, list tools, return tool names."""
    params = _server_params()
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            return [t.name for t in tools.tools]


# ---------- tests ----------


def test_ikigai_mcp_health_via_stdio_jsonrpc() -> None:
    """Full stdio JSON-RPC handshake + `ikigai_health` roundtrip.

    Validates the canonical FastMCP server accepts the MCP protocol
    (initialize -> tools/call) and returns the health payload produced
    by tools_mesh.ikigai_health():
        {
            "name": "ikigai-gateway",
            "version": <str>,
            "started_at": <float>,   # _time.time() at gateway startup
            "uptime_s":   <float>,
            "adapters":   <list>,
        }

    Recorded shape per the actual server response (NOT a hypothetical
    string/iso timestamp — see tools_mesh.py:163 where started_at is set
    from _time.time()). This is the canonical M5 acceptance criterion #5
    from SPEC.md.
    """
    health_data = asyncio.run(_do_health_handshake())

    assert health_data.get("name") == "ikigai-gateway", (
        f"unexpected gateway name: {health_data!r}"
    )
    assert isinstance(health_data.get("version"), str), (
        f"version missing or not str: {health_data!r}"
    )
    started_at = health_data.get("started_at")
    assert isinstance(started_at, (int, float)) and started_at > 0, (
        f"started_at missing or non-numeric: {health_data!r}"
    )
    uptime = health_data.get("uptime_s")
    assert isinstance(uptime, (int, float)) and uptime >= 0, (
        f"uptime_s missing or non-numeric: {health_data!r}"
    )
    adapters = health_data.get("adapters")
    assert isinstance(adapters, list), (
        f"adapters missing or not a list: {health_data!r}"
    )


def test_ikigai_mcp_tools_list_includes_health() -> None:
    """`tools/list` confirms `ikigai_health` is registered on the server.

    Defensive companion to the health-call test: ensures the registered
    tool surface actually contains the tool we just invoked. Catches
    regressions where the @MCP.tool decorator is removed without updating
    tests/SPEC.
    """
    names = asyncio.run(_do_tools_list())
    assert "ikigai_health" in names, (
        f"ikigai_health not in registered tools. got: {sorted(names)}"
    )
