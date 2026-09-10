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
    ikigai-tui
"""

from __future__ import annotations

from interfaces.tui.operator.app import OperatorApp
from interfaces.tui.operator._tui_chat_tab import TuiChatTab


def main() -> int:
    """Entry point for the `ikigai-tui` console script.

    Same logic as interfaces/tui/operator/__main__.py: build an
    OperatorApp and run it. Duplicated here so the entry point
    `ikigai-tui = "interfaces.tui.operator:main"` resolves the symbol
    without importing the package's __main__ (which doesn't auto-expose
    its main()).
    """
    app = OperatorApp()
    app.run()
    return 0


__all__ = ["OperatorApp", "TuiChatTab", "main"]
