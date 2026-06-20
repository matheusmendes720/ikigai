"""Backward-compat shim — re-exports the central console from ``operational.ui``.

Some files in transitional state still ``from operational.cli.console import
console`` (pre-refactor pattern). The canonical home is now
``operational.ui.console``. This shim keeps those imports working until
they are migrated to ``from operational.ui import console``.
"""
from __future__ import annotations

from operational.ui import CONSOLE_WIDTH, console  # noqa: F401

__all__ = ["console", "CONSOLE_WIDTH"]
