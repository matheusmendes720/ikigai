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
import shutil
import sys
from typing import Any

_IKIGAI_SRC_BOOTSTRAPPED: bool = False


def _repo_root() -> str:
    """Absolute path of the repository root.

    Caller file: <repo>/interfaces/cli/<file>.py
    """
    caller = os.path.abspath(__file__)
    return os.path.abspath(os.path.join(os.path.dirname(caller), os.pardir, os.pardir))


def _ensure_ikigai_src_on_path() -> None:
    """Add src/ikigai/src to sys.path so `from strategics.loader import ...`
    resolves when running `life v2 *` from a PYTHONPATH=REPO_ROOT shell.

    Idempotent (module-level guard + list check).
    """
    global _IKIGAI_SRC_BOOTSTRAPPED
    if _IKIGAI_SRC_BOOTSTRAPPED:
        return
    repo_root = _repo_root()
    ikigai_src = os.path.join(repo_root, "src", "ikigai", "src")
    if os.path.isdir(ikigai_src) and ikigai_src not in sys.path:
        sys.path.insert(0, ikigai_src)
    _IKIGAI_SRC_BOOTSTRAPPED = True


def _mcp_server_spec() -> dict[str, Any]:
    """Resolve how to spawn the taskdog MCP server.

    Preference order:
    1. `taskdog-mcp` on PATH (standalone launcher package, Path 3).
    2. `python -m mcp_server` from this repo (src/ikigai/src/mcp_server).

    The in-repo fallback exists because the standalone binary is not part of
    this repository's install set: without it every `life v2 *` import would
    die at MCP discovery. The child process needs REPO_ROOT, REPO_ROOT/src
    and src/ikigai/src on PYTHONPATH (mcp_server imports `contracts.*` and
    `src.mesh.*`).
    """
    if shutil.which("taskdog-mcp") is not None:
        return {"command": "taskdog-mcp", "args": [], "transport": "stdio"}

    repo_root = _repo_root()
    ikigai_src = os.path.join(repo_root, "src", "ikigai", "src")
    env = dict(os.environ)
    search_path = [repo_root, os.path.join(repo_root, "src"), ikigai_src]
    existing = env.get("PYTHONPATH")
    if existing:
        search_path.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(p for p in search_path if p)

    return {
        "command": sys.executable,
        "args": ["-m", "mcp_server"],
        "transport": "stdio",
        "env": env,
        "cwd": ikigai_src,
    }


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

    client = MultiServerMCPClient({"taskdog": _mcp_server_spec()})
    tools = await client.get_tools()
    _MCP_TOOLS_CACHE = list(tools)
    return _MCP_TOOLS_CACHE


def get_mcp_tools_sync() -> list[Any]:
    """Sync facade — runs the async loader via asyncio.run()."""
    return asyncio.run(get_mcp_tools_async())


__all__ = [
    "_IKIGAI_SRC_BOOTSTRAPPED",
    "_ensure_ikigai_src_on_path",
    "get_mcp_tools_async",
    "get_mcp_tools_sync",
]
