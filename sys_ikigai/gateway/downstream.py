"""Downstream adapter registry — backward-compat re-export shim.

The stdio MCP client factories (taskdog-mcp, tuiboard, solverforge-calendar)
lived here and were retired with the serverless pivot (ADR-037, 2026-11-01).
What remains are the data-mesh adapters: the CLI fork and the taskdog SQLite
fork, both of which speak plain files/SQLite instead of spawning a local MCP
server process.
"""

from __future__ import annotations

from pathlib import Path

from sys_ikigai.gateway.adapters.cli_adapter import CliAdapter
from sys_ikigai.gateway.adapters.taskdog_adapter import TaskdogAdapter


def register_default_adapters(gateway, *, data_dir: Path | None = None) -> None:
    """Register the surviving downstream adapters on a gateway.

    Only adapters that need no local server binary are registered.
    """
    gateway.register(CliAdapter())
    gateway.register(TaskdogAdapter())


__all__ = [
    "CliAdapter",
    "TaskdogAdapter",
    "register_default_adapters",
]
