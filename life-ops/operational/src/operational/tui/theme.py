"""Textual theme mapping from ui/tokens.py design tokens."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual.theme import Theme

TUI_COLORS: dict[str, str] = {
    "primary":   "#1E90FF",
    "success":   "#00FF00",
    "warning":   "#FFD700",
    "danger":    "#FF4444",
    "info":      "#00BFFF",
    "muted":     "#A9A9A9",
    "accent":    "#FF00FF",
    "inverse":   "#FFFFFF on #000000",
}

REGIME_COLORS: dict[str, str] = {
    "PUSH":     "#00FF00",
    "MAINTAIN": "#1E90FF",
    "REDUCE":   "#FFD700",
    "RECOVER":  "#FF4444",
}

QUADRANT_COLORS: dict[str, str] = {
    "Q1": "#00FF00",
    "Q2": "#00CED1",
    "Q3": "#FF4444",
    "Q4": "#FFD700",
}

def get_tui_theme() -> Theme:
    from textual.theme import Theme
    return Theme(
        name="pav-dark",
        dark=True,
        primary=TUI_COLORS["primary"],
        secondary=TUI_COLORS["info"],
        accent=TUI_COLORS["accent"],
        background="#000000",
        surface="#111111",
        panel="#1a1a1a",
        warning=TUI_COLORS["warning"],
        error=TUI_COLORS["danger"],
        success=TUI_COLORS["success"],
    )
