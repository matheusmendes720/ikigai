"""CLI — Typer application for the operational system.

The ``app`` Typer instance is **lazily** loaded via PEP 562
(``__getattr__`` at module level). This breaks the historical circular
dependency:

    cli.app  →  tui.app  →  screens.*  →  cli.state  →  cli.app  (cycle)

By deferring the import of ``operational.cli.app`` until ``app`` is
actually accessed, we let the TUI screens finish loading before the CLI
app module is initialized.

Entry points in ``pyproject.toml`` use the absolute path
``operational.cli.app:app`` — they don't go through this module.
Tests using ``from operational.cli import app`` still work.
"""
from __future__ import annotations

from typing import Any

__all__ = ["app"]


def __getattr__(name: str) -> Any:
    """PEP 562 lazy attribute — only import the heavy Typer app on demand."""
    if name == "app":
        from operational.cli.app import app as _typer_app

        # Cache so subsequent lookups don't re-import
        globals()["app"] = _typer_app
        return _typer_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")