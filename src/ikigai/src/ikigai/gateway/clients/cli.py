"""cli_adapter factory — native IKIGAI CLI fork.

Expected tools: cli_* (ikigai chat, agent, mcp subcommands).
"""

from __future__ import annotations

import os
import sys

from ikigai.gateway.stdio_adapter import StdioAdapter, StdioAdapterConfig


def cli_adapter(
    *,
    python: str | None = None,
    module: str = "ikigai.cli",
) -> StdioAdapter:
    """Adapter for the native IKIGAI CLI (ikigai.chat, ikigai.agent, ikigai.mcp).

    This is a read-only / planning-oriented fork; it does not write vault/.
    Writes go through the vault_write MCP tool exclusively.

    Expected namespace: ``cli_*``
    """
    py = python or os.environ.get("PYTHON", sys.executable)
    cmd = [py, "-m", module]
    return StdioAdapter(
        name="cli",
        config=StdioAdapterConfig(command=cmd, env={}, call_timeout_s=15.0),
    )
