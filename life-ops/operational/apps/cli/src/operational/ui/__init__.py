"""Centralized Console configuration (Singleton).

This is the ONE place that owns the Rich Console for the entire
operational CLI. All commands and UI components import from here.

The console:
- Uses a fixed width of 120 columns (dashboard-style layout)
- Has soft_wrap=True to prevent text from breaking in middle of words
- Auto-detects color system (truecolor → 16 → 8 → none)
- Auto-detects Unicode support
- Strips ANSI codes when output is captured (for in-process calls from
  the home menu or any redirect_stdout context)

Also installs the Rich traceback handler globally so that any uncaught
exception prints a beautiful, colorized traceback instead of the
default Python one.
"""
from __future__ import annotations

import re
import sys
from typing import Any

from rich.console import Console
from rich.traceback import install as install_rich_traceback

# ---------------------------------------------------------------------------
# Single canonical Console instance
# ---------------------------------------------------------------------------

CONSOLE_WIDTH: int = 120
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def is_captured() -> bool:
    """True if stdout is not a TTY (piped, captured, opencode tool, etc)."""
    return not (sys.stdout is not None and sys.stdout.isatty())


# Build a single Console. The `soft_wrap=True` + explicit width=120
# gives us predictable layout regardless of the actual terminal width.
# When captured, no_color=True so we never leak raw ANSI codes.
console: Console = Console(
    width=CONSOLE_WIDTH,
    soft_wrap=True,
    force_terminal=False,  # let Rich auto-detect; we only force width
    color_system="auto",
    no_color=is_captured(),
    highlight=True,
    markup=True,
    emoji=True,
    legacy_windows=False,
    safe_box=False,  # Use full Unicode box characters (╭─╮ etc)
)


# Install Rich's traceback handler globally. This makes any uncaught
# exception print a beautiful, colorized traceback with show_locals
# (essential for debugging data pipeline issues).
install_rich_traceback(
    show_locals=True,
    width=CONSOLE_WIDTH,
    max_frames=5,
)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from a string.

    Used by the home menu to clean output that was captured from inner
    commands that ran in a different TTY context.
    """
    return _ANSI_ESCAPE_RE.sub("", text)


__all__ = ["CONSOLE_WIDTH", "console", "is_captured", "strip_ansi"]

