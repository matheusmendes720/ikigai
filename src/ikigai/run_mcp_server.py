#!/usr/bin/env python
"""Run the IKIGAi MCP server.

Usage:
    python run_mcp_server.py

Or from project root with uv:
    cd src/ikigai && uv run python run_mcp_server.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure src/ is on the Python path
_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from mcp_server.server import main

if __name__ == "__main__":
    asyncio.run(main())
