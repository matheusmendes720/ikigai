"""Design tokens for PAV-OS v2.

Centralized values for colors, glyphs, spacing. NEVER hardcode these
in components. Import from here.

See ``docs/design-system/DESIGN-SYSTEM.md`` for the full spec.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# ---------------------------------------------------------------------------
# Severity palette (the 8 core semantic colors)
# ---------------------------------------------------------------------------

SEVERITY: Final[dict[str, str]] = {
    "primary":   "dodger_blue1",
    "success":   "bright_green",
    "warning":   "yellow",
    "danger":    "bold red",
    "info":      "deep_sky_blue1",
    "muted":     "grey70",
    "accent":    "magenta",
    "inverse":   "white on black",
}


# ---------------------------------------------------------------------------
# Surface (background tints)
# ---------------------------------------------------------------------------

SURFACE: Final[dict[str, str]] = {
    "base":       "default",
    "raised":     "grey11",
    "sunken":     "grey7",
    "highlight":  "grey23",
    "danger":     "dark_red",
    "success":    "dark_green",
}


# ---------------------------------------------------------------------------
# Policy regimes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RegimeSpec:
    color: str
    glyph: str
    label_pt: str
    action_pt: str


REGIME: Final[dict[str, RegimeSpec]] = {
    "PUSH":     RegimeSpec("bright_green", "▲", "PUSH",     "Aumentar carga"),
    "MAINTAIN": RegimeSpec("dodger_blue1", "◆", "MAINTAIN", "Manter ritmo"),
    "REDUCE":   RegimeSpec("yellow",       "▼", "REDUCE",   "Reduzir carga"),
    "RECOVER":  RegimeSpec("bold red",     "✗", "RECOVER",  "Recuperar urgente"),
}


# ---------------------------------------------------------------------------
# Quadrants
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class QuadrantSpec:
    color: str
    glyph: str
    label_pt: str
    action_pt: str


QUADRANT: Final[dict[str, QuadrantSpec]] = {
    "Q1": QuadrantSpec("bright_green", "◆", "Excelente",            "Manter ritmo"),
    "Q2": QuadrantSpec("cyan",         "▲", "Otimizado, pouco output", "Aumentar volume"),
    "Q3": QuadrantSpec("bold red",     "✗", "Critico",               "Revisao urgente"),
    "Q4": QuadrantSpec("yellow",       "?", "Produtivo disperso",  "Reduzir distracao"),
}


# ---------------------------------------------------------------------------
# Typography styles (Rich style strings)
# ---------------------------------------------------------------------------

STYLES: Final[dict[str, str]] = {
    "h1":          "bold white on dodger_blue1",
    "h2":          "bold cyan",
    "h3":          "bold white",
    "body":        "default",
    "body_muted":  "grey70",
    "mono":        "dim cyan",
    "emphasis":    "bold yellow",
    "danger_num":  "bold red",
    "success_num": "bold bright_green",
    "warning_num": "bold yellow",
}


# ---------------------------------------------------------------------------
# Spacing (Rich padding tuples: (vertical, horizontal))
# ---------------------------------------------------------------------------

PADDING: Final[dict[str, tuple[int, int]]] = {
    "xs": (0, 1),
    "sm": (0, 2),
    "md": (1, 2),
    "lg": (2, 4),
    "xl": (3, 6),
}


# ---------------------------------------------------------------------------
# Glyph library (Unicode)
# ---------------------------------------------------------------------------

class Glyph:
    """Centralized Unicode glyphs. NEVER hardcode in components."""

    POMO_DONE    = "▣"
    POMO_SKIP    = "▢"
    POMO_PARTIAL = "▤"

    PT_EXCEL     = "◆"
    PT_OPT       = "▲"
    PT_CRIT      = "✗"
    PT_DISP      = "?"

    LINE_V       = "┊"
    LINE_H       = "┈"
    AXIS_CROSS   = "┼"
    AXIS_X       = "─"
    AXIS_Y       = "│"
    AXIS_LABEL   = "·"

    SPARK_CHARS  = "▁▂▃▄▅▆▇█"

    BAR_FULL     = "█"
    BAR_SEVEN    = "▇"
    BAR_FIVE     = "▅"
    BAR_THREE    = "▃"
    BAR_ONE      = "▁"
    BAR_EMPTY    = "░"

    CHECK        = "✓"
    CROSS        = "✗"
    PENDING      = "◌"
    ACTIVE       = "●"
    MUTED_DOT    = "○"


# ---------------------------------------------------------------------------
# Console width (the v2 standard)
# ---------------------------------------------------------------------------

CONSOLE_WIDTH_V2: Final[int] = 128


__all__ = [
    "CONSOLE_WIDTH_V2",
    "PADDING",
    "QUADRANT",
    "REGIME",
    "SEVERITY",
    "STYLES",
    "SURFACE",
    "Glyph",
    "QuadrantSpec",
    "RegimeSpec",
]
