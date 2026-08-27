"""Downstream MCP server adapters — backward-compat re-export shim.

The three factory functions live in gateway/clients/ subpackage.
This module re-exports them so existing imports from ikigai.gateway.downstream
continue to work without modification.
"""

from __future__ import annotations

from pathlib import Path

from ikigai.gateway.clients.solverforge_calendar import SolverforgeCalendarAdapter
from ikigai.gateway.clients.taskdog import TaskdogAdapter
from ikigai.gateway.clients.tuiboard import TuiboardAdapter


def register_default_adapters(gateway, *, data_dir: Path | None = None) -> None:
    """Register all 3 downstream adapters on a gateway.

    No-op if a server binary is missing — adapters register only what
    we can actually spawn. Caller decides whether to fail loudly.
    """
    for factory in (
        TuiboardAdapter(data_dir=str(data_dir) if data_dir else None),
        TaskdogAdapter(),
        SolverforgeCalendarAdapter(),
    ):
        gateway.register(factory)


__all__ = [
    "SolverforgeCalendarAdapter",
    "TaskdogAdapter",
    "TuiboardAdapter",
    "register_default_adapters",
]
