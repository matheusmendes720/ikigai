"""Standalone launcher for the taskdog MCP server (Path 3, read-only).

Run: python -m mcp_server.__main__taskdog

Per docs/design-system/24-taskdog-paths-architecture.md §Path 3:
- Subprocess-bound FastMCP instance from mcp_server.taskdog_tools
- Stdio JSON-RPC transport
- Read-only surface (taskdog_read, taskdog_list, taskdog_supports_field)
- Wired independently from the ikigai-gateway (no cross-talk)

Usage (after `uv pip install -e .`):
    ikigai-taskdog-mcp   # via [tool.poetry.scripts] entry point
or:
    python -m mcp_server.__main__taskdog
"""

from __future__ import annotations

from mcp_server.taskdog_tools import mcp


def main() -> None:
    """Run taskdog MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
