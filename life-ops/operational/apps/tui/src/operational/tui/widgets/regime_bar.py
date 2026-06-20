"""Regime Bar widget for PAV TUI dashboard."""
from __future__ import annotations

from textual.widgets import Static

from operational.tui.theme import REGIME_COLORS

REGIME_GLYPHS = {"PUSH": "▲", "MAINTAIN": "◆", "REDUCE": "▼", "RECOVER": "✗"}


class RegimeBar(Static):
    """Display PUSH / MAINTAIN / REDUCE / RECOVER states with current highlighted."""

    DEFAULT_CSS = """
    RegimeBar {
        height: 3;
        padding: 1 2;
        background: $surface;
        border: solid $border;
    }
    """

    def __init__(self, current: str = "MAINTAIN", history: dict[str, int] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.current = current
        self.history = history or {}

    def render(self) -> str:
        parts = []
        for regime in ("PUSH", "MAINTAIN", "REDUCE", "RECOVER"):
            glyph = REGIME_GLYPHS[regime]
            color = REGIME_COLORS[regime]
            if regime == self.current:
                parts.append(f"[bold {color}]{glyph} {regime}[/bold {color}]")
            else:
                parts.append(f"[dim]{glyph} {regime}[/dim]")
        return "  ".join(parts)
