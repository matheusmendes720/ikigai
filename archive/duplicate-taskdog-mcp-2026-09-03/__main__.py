"""Taskdog MCP server entry point — `python -m src.taskdog_mcp`."""

from __future__ import annotations

import asyncio

from src.taskdog_mcp.server import main

if __name__ == "__main__":
    asyncio.run(main())
