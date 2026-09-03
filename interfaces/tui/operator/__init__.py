"""Operator TUI — backend control plane.

A Textual-based dashboard for inspecting the IKIGAI backend topology:
  - fork adapters (cli, taskdog, solverforge_calendar, a2ui)
  - backend processes (mcp_gateway, review_queue_worker)
  - data/ review queue (pending TaskChange events)

Per dual-layer architecture (memory: interfaces-architecture-2026-08-27):
this is the operator control plane ONLY. User-facing views live in forks
(tuiboard, taskdog, solverforge-calendar) — NOT here.

Launch:
    python -m interfaces.tui.operator
    # or
    life tui operator
"""

from __future__ import annotations

from interfaces.tui.operator.app import OperatorApp

__all__ = ["OperatorApp"]
