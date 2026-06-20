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
        primary=TUI_COLORS["primary"],     # #1E90FF
        secondary=TUI_COLORS["info"],      # #00BFFF
        accent=TUI_COLORS["accent"],        # #FF00FF
        background="#0d0d1a",               # near-black navy
        surface="#141428",                 # slightly lighter navy
        panel="#1a1a2e",                  # PAV NOITE (darkest)
        warning=TUI_COLORS["warning"],      # #FFD700
        error=TUI_COLORS["danger"],         # #FF4444
        success=TUI_COLORS["success"],      # #00FF00
        variables={
            # Map PAV period names to standard Theme attributes
            "noite":  "#1a1a2e",   # same as panel
            "manha":  "#16213e",   # same as surface
            "tarde":  "#0f3460",   # same as surface
            # Map PAV semantic names to standard colors
            "coral":  "#ff6b6b",   # same as error/danger
            "teal":   "#4ecdc4",   # same as success
            # Standard semantic slots
            "text":         "#E0E0E0",
            "text-muted":   "#A9A9A9",
            "text-dim":     "#6B6B8B",
            "border":       "#2a2a4a",
            "border-focus": "#1E90FF",
            "overlay":      "#1e1e3a",
            "selection":    "#2a2a5a",
            # Regime colors
            "regime-push":     "#00FF00",
            "regime-maintain": "#1E90FF",
            "regime-reduce":   "#FFD700",
            "regime-recover":  "#FF4444",
            # Quadrants
            "q1": "#00FF00", "q2": "#00CED1", "q3": "#FF4444", "q4": "#FFD700",
            # Compatibility aliases
            "muted":   TUI_COLORS["muted"],
            "success": TUI_COLORS["success"],
            "warning": TUI_COLORS["warning"],
            "danger":  TUI_COLORS["danger"],
            "info":    TUI_COLORS["info"],
        },
    )
