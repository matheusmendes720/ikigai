"""Input summary helper — shows user what they just typed.

Used by every command that accepts flags, so users always know what
parameters were sent without having to read the help docs.

Disable by setting ``TIME_TASKER_NO_INPUT_SUMMARY=1`` in the environment.
"""
from __future__ import annotations

import os
from typing import Any

from rich.console import Console
from rich.box import SIMPLE_HEAD
from rich.panel import Panel
from rich.table import Table

from operational.cli.renderers import make_console

console = make_console()


def maybe_print_input_summary(
    *,
    title: str,
    params: dict[str, Any],
    flag_legend: dict[str, str] | None = None,
    show_legend_footer: bool = True,
) -> None:
    """Print a "você digitou" panel unless disabled.

    Args:
        title: Title for the panel.
        params: Parameter dict.
        flag_legend: Optional mapping of short -> long flag names.
        show_legend_footer: Whether to show the legend footer.
    """
    if os.environ.get("TIME_TASKER_NO_INPUT_SUMMARY") == "1":
        return

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

    panel = Panel(t, title=f"[bold cyan]📝 {title}[/bold cyan]", border_style="cyan", box=SIMPLE_HEAD, padding=(0, 1))
    console.print(panel)


__all__ = ["maybe_print_input_summary"]
