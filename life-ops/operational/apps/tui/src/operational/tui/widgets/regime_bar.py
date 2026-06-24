"""Regime Bar widget for PAV TUI.

Shows the 4 policy regimes (PUSH / MAINTAIN / REDUCE / RECOVER) with the
current regime highlighted. ``current`` is reactive — assigning to it
auto-refreshes the widget.
"""
from __future__ import annotations

from operational.tui.theme import REGIME_COLORS, TUI_COLORS
from textual.reactive import reactive
from textual.widgets import Static

REGIME_GLYPHS = {"PUSH": "▲", "MAINTAIN": "◆", "REDUCE": "▼", "RECOVER": "✗"}
REGIME_ORDER = ("PUSH", "MAINTAIN", "REDUCE", "RECOVER")


class RegimeBar(Static):
    """Display PUSH / MAINTAIN / REDUCE / RECOVER states with current highlighted."""

    DEFAULT_CSS = """
    RegimeBar {
        height: 3;
        padding: 1 2;
        background: $surface;
        border: solid $border;
        color: $text;
    }
    """

    current = reactive("MAINTAIN")

    def __init__(
        self,
        current: str = "MAINTAIN",
        history: dict[str, int] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.current = current
        self.history = history or {}

    def watch_current(self, old: str, new: str) -> None:
        self.refresh()

    def render(self) -> str:
        parts: list[str] = []
        for regime in REGIME_ORDER:
            glyph = REGIME_GLYPHS.get(regime, "·")
            color = REGIME_COLORS.get(regime, TUI_COLORS["primary"])
            if regime == self.current:
                parts.append(f"[bold {color}]{glyph} {regime}[/bold {color}]")
            else:
                parts.append(f"[dim]{glyph} {regime}[/dim]")
        return "  ".join(parts)
