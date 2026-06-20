"""Backward-compat shim — re-exports the legacy CLI rendering utilities
that the non-report commands depend on.

This module exists only to satisfy the remaining imports of v1
rendering helpers (``make_console``, ``COLORS``, ``progress_bar``,
``maybe_print_input_summary``) by the CRUD command modules
(``routine_cmd``, ``block_cmd``, ``metric_cmd``, ``journal_cmd``,
``lunch_cmd``, ``habit_cmd``, ``reflect_cmd``).

The report/state commands have been fully migrated to the v2 design
system in ``ui/components_v2.py`` + ``ui/v2_renderers.py`` and no
longer depend on this shim.
"""
from __future__ import annotations

import os
import shutil
import sys
from typing import Any

from rich.box import SIMPLE_HEAD
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# ---------------------------------------------------------------------------
# make_console — TTY-aware Console factory (kept for command-level CLIs)
# ---------------------------------------------------------------------------


def make_console(*, width: int | None = None) -> Console:
    """Build a Console with auto-detected TTY width and color policy.

    - Real TTY: enable colors and detect width.
    - Non-TTY: disable colors but keep Unicode, default to 120.
    """
    is_tty = sys.stdout.isatty() if sys.stdout is not None else False
    if width is None:
        if is_tty:
            try:
                width = shutil.get_terminal_size().columns
            except Exception:
                width = 120
        else:
            width = 120
    width = max(60, min(140, width))

    return Console(
        force_terminal=True,
        color_system="truecolor" if is_tty else None,
        no_color=not is_tty,
        width=width,
        highlight=True,
        markup=True,
        emoji=True,
        soft_wrap=False,
        legacy_windows=False,
        safe_box=False,
    )


# ---------------------------------------------------------------------------
# Color palette (compatible with the v1 import name)
# ---------------------------------------------------------------------------


COLORS: dict[str, str] = {
    "primary": "cyan",
    "secondary": "white",
    "muted": "bright_black",
    "ok": "bright_green",
    "warn": "yellow",
    "crit": "bold red",
    "info": "blue",
    "accent": "magenta",
    "highlight": "bold cyan",
    "energy": "yellow1",
    "focus": "deep_sky_blue1",
    "sleep": "dodger_blue2",
    "hardwork": "green3",
    "ease": "magenta",
    "transition": "deep_pink1",
}


# ---------------------------------------------------------------------------
# progress_bar — used by metric_cmd and habit_cmd listings
# ---------------------------------------------------------------------------


def progress_bar(
    value: float,
    total: float,
    *,
    width: int = 18,
    color: str = "primary",
    label: str = "",
) -> Text:
    """Render a simple bar + percent + label as a Rich Text."""
    clr = COLORS.get(color, color)
    pct = 0.0 if total <= 0 else max(0.0, min(1.0, value / total))
    filled = int(round(pct * width))
    empty = width - filled
    t = Text()
    t.append("█" * filled, style=clr)
    t.append("░" * empty, style="grey50")
    t.append(f"  {int(pct * 100):3d}%", style=f"bold {clr}")
    if label:
        t.append(f"  ({label})", style="grey58")
    return t


# ---------------------------------------------------------------------------
# maybe_print_input_summary — echo user-typed parameters
# ---------------------------------------------------------------------------


_ANSI_ESCAPE_RE = __import__("re").compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def maybe_print_input_summary(
    *,
    title: str,
    params: dict[str, Any],
    flag_legend: dict[str, str] | None = None,
    show_legend_footer: bool = True,
) -> None:
    """Print a "você digitou" panel unless disabled."""
    if os.environ.get("TIME_TASKER_NO_INPUT_SUMMARY") == "1":
        return

    console = make_console()
    t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    t.add_column("Parâmetro", style="bold cyan", min_width=14)
    t.add_column("Valor", style="white", min_width=20)
    t.add_column("Flag", style="dim", min_width=18)

    for k, v in params.items():
        flag_hint = ""
        if flag_legend:
            for short, long in flag_legend.items():
                if long.endswith(k) or long.replace("--", "") == k:
                    flag_hint = f"{short} / {long}"
                    break
        t.add_row(k, str(v), flag_hint)

    panel = Panel(
        t,
        title=f"[bold cyan]{title}[/bold cyan]",
        border_style="cyan",
        box=SIMPLE_HEAD,
        padding=(0, 1),
    )
    console.print(panel)


__all__ = ["make_console", "COLORS", "progress_bar", "maybe_print_input_summary"]
