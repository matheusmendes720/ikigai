"""SolverforgeCalendarAdapter factory — Task 14."""

from __future__ import annotations

import os

from ikigai.gateway.stdio_adapter import StdioAdapter, StdioAdapterConfig


def SolverforgeCalendarAdapter(
    *,
    python: str | None = None,
    module: str | None = None,
    solver_binary: str | None = None,
) -> StdioAdapter:
    """Adapter for solverforge-calendar — calendar/optimizer MCP server.

    Expected tools: sf_schedule, sf_replan, sf_availability.
    """
    py = python or os.environ.get("PYTHON", "python")
    mod = module or os.environ.get("SOLVERFORGE_MODULE", "solverforge_calendar.server")
    cmd = [py, "-m", mod]
    env: dict[str, str] = {}
    if solver_binary:
        env["SOLVERFORGE_BIN"] = solver_binary
    return StdioAdapter(
        name="solverforge-calendar",
        config=StdioAdapterConfig(command=cmd, env=env, call_timeout_s=60.0),
    )
