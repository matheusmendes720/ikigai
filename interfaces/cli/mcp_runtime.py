"""Shared MCP runtime for IKIGAI CLI commands.

Provides:
- get_mcp_tools_async() — async loader for the 26 taskdog-mcp tools
- _ensure_ikigai_src_on_path() — idempotent sys.path bootstrap

Used by:
- M98: `life v2 agent` (interfaces/cli/v2.py)
- M99: `life v2 chat`  (interfaces/cli/v2.py)
- M100: `life taskdog *` (interfaces/cli/taskdog_app.py)
"""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

_IKIGAI_SRC_BOOTSTRAPPED: bool = False


def _ensure_ikigai_src_on_path() -> None:
    """Add src/ikigai/src to sys.path so `from strategics.loader import ...`
    resolves when running `life v2 *` from a PYTHONPATH=REPO_ROOT shell.

    Idempotent (module-level guard + list check).
    """
    global _IKIGAI_SRC_BOOTSTRAPPED
    if _IKIGAI_SRC_BOOTSTRAPPED:
        return
    # Caller file: <repo>/interfaces/cli/<file>.py
    # Target:     <repo>/src/ikigai/src
    caller = os.path.abspath(__file__)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(caller), os.pardir, os.pardir))
    ikigai_src = os.path.join(repo_root, "src", "ikigai", "src")
    if os.path.isdir(ikigai_src) and ikigai_src not in sys.path:
        sys.path.insert(0, ikigai_src)
    _IKIGAI_SRC_BOOTSTRAPPED = True


_MCP_TOOLS_CACHE: list[Any] | None = None


async def get_mcp_tools_async() -> list[Any]:
    """Async loader for the 26 taskdog-mcp tools (cached after first call).

    Uses langchain_mcp_adapters.MultiServerMCPClient to spawn taskdog-mcp
    as a stdio subprocess and discover its tools via the MCP protocol.
    """
    global _MCP_TOOLS_CACHE
    if _MCP_TOOLS_CACHE is not None:
        return _MCP_TOOLS_CACHE

    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(
        {
            "taskdog": {
                "command": "taskdog-mcp",
                "args": [],
                "transport": "stdio",
            }
        }
    )
    tools = await client.get_tools()
    _MCP_TOOLS_CACHE = list(tools)
    return _MCP_TOOLS_CACHE


def get_mcp_tools_sync() -> list[Any]:
    """Sync facade — runs the async loader via asyncio.run()."""
    return asyncio.run(get_mcp_tools_async())


__all__ = [
    "_ensure_ikigai_src_on_path",
    "_IKIGAI_SRC_BOOTSTRAPPED",
    "get_mcp_tools_async",
    "get_mcp_tools_sync",
]
