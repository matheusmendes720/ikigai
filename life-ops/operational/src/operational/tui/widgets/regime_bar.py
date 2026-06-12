"""Regime Bar widget for PAV TUI dashboard."""
from __future__ import annotations

from textual.widgets import Static

REGIME_GLYPHS = {"PUSH": "▲", "MAINTAIN": "◆", "REDUCE": "▼", "RECOVER": "✗"}


class RegimeBar(Static):
    """Display PUSH / MAINTAIN / REDUCE / RECOVER states with current highlighted."""

    def __init__(self, current: str = "MAINTAIN", history: dict[str, int] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.current = current
        self.history = history or {}

    def render(self) -> str:
        parts = []
        for regime in ("PUSH", "MAINTAIN", "REDUCE", "RECOVER"):
            REGIME_GLYPHS[regime]
            if regime == self.current:
                parts.append(f"[{regime}]")
            else:
                self.history.get(regime, 0)
                parts.append(f"{regime}")
        return "  ".join(parts)
