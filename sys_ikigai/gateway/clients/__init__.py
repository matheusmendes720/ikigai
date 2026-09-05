"""Downstream MCP client factories — one module per client."""

from __future__ import annotations

from sys_ikigai.gateway.clients.solverforge_calendar import solverforge_calendar_adapter
from sys_ikigai.gateway.clients.taskdog import taskdog_adapter
from sys_ikigai.gateway.clients.tuiboard import tuiboard_adapter

try:
    from sys_ikigai.gateway.clients.cli import cli_adapter
except ImportError:
    # cli.py may not exist on all builds
    cli_adapter = None  # type: ignore[assignment]

__all__ = [
    "cli_adapter",
    "solverforge_calendar_adapter",
    "taskdog_adapter",
    "tuiboard_adapter",
]
