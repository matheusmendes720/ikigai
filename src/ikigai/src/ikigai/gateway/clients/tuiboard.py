"""TuiboardAdapter factory — Task 14."""

from __future__ import annotations

import os

from ikigai.gateway.stdio_adapter import StdioAdapter, StdioAdapterConfig


def TuiboardAdapter(
    *,
    binary: str | None = None,
    data_dir: str | None = None,
) -> StdioAdapter:
    """Adapter for the tuiboard Rust MCP server (dashboard rendering).

    Expected tools: tuiboard_render, tuiboard_snapshot, tuiboard_diff.
    """
    cmd = [binary or os.environ.get("TUIBOARD_BIN", "tuiboard-mcp")]
    env: dict[str, str] = {}
    if data_dir:
        env["TUIBOARD_DATA_DIR"] = data_dir
    return StdioAdapter(
        name="tuiboard",
        config=StdioAdapterConfig(command=cmd, env=env, call_timeout_s=15.0),
    )
