"""MCP client wrapper for IKIGAI agent — async-loadable taskdog tools.

Per M97b Option A: wire taskdog-mcp (26 tools) into the deep-agent via
langchain-mcp-adapters. This module exposes a SYNC facade over the async
``MultiServerMCPClient`` so it can be called from the synchronous
``_make_agent`` factory.

The MCP client is short-lived (one-shot per agent init): we don't need a
persistent connection because the agent invokes tools through the loaded
``StructuredTool`` objects after ``get_tools()`` returns.

Usage:
    from .mcp_taskdog_client import get_taskdog_tools
    extra = get_taskdog_tools()  # list[StructuredTool], 26 entries
    all_tools = IKIGAI_TOOLS + extra
    agent = create_deep_agent(tools=all_tools, ...)

Failures fall back to IKIGAI_TOOLS only (4 taskdog @tool wrappers), so
the harness always boots even if MCP is unavailable (e.g. CI without
taskdog-mcp on PATH).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _is_mcp_enabled() -> bool:
    """Return True unless IKIGAI_DISABLE_MCP_TASKDOG=1 (escape hatch for CI)."""
    return os.environ.get("IKIGAI_DISABLE_MCP_TASKDOG", "0") != "1"


def _taskdog_mcp_on_path() -> bool:
    """Return True if `taskdog-mcp` binary is callable on PATH."""
    import shutil

    return shutil.which("taskdog-mcp") is not None


async def _async_get_taskdog_tools() -> list[Any]:
    """Async loader — fetch 26 taskdog tools from taskdog-mcp over stdio."""
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
    return list(tools)


def get_taskdog_tools() -> list[Any]:
    """Sync facade over async loader — safe to call from non-async code.

    Returns the 26 taskdog tools from taskdog-mcp, or [] on any failure
    (with a logged warning). Never raises — the agent must boot even
    without MCP available.
    """
    if not _is_mcp_enabled():
        logger.info("IKIGAI_DISABLE_MCP_TASKDOG=1, skipping MCP taskdog tools")
        return []
    if not _taskdog_mcp_on_path():
        logger.warning("taskdog-mcp binary not on PATH; skipping MCP tools")
        return []
    try:
        tools = asyncio.run(_async_get_taskdog_tools())
        logger.info("loaded %d tools from taskdog-mcp", len(tools))
        return tools
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to load taskdog-mcp tools: %s", exc)
        return []


def build_agent_tools() -> list[Any]:
    """Build the full tool list for the deep-agent: IKIGAI_TOOLS + MCP tools.

    IKIGAI_TOOLS stays at exactly 12 (drift-detector-pinned). MCP tools
    are appended at runtime — they do NOT count against the 12-tool
    invariant because they live outside tools.py.
    """
    # Imported lazily to avoid circular imports at module load time.
    from .tools import IKIGAI_TOOLS

    mcp_tools = get_taskdog_tools()
    return list(IKIGAI_TOOLS) + mcp_tools
