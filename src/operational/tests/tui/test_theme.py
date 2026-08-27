"""Tests for operational.tui.theme."""
from __future__ import annotations

from operational.tui.theme import TUI_COLORS, REGIME_COLORS, QUADRANT_COLORS, get_tui_theme


def test_tui_colors_has_8_keys() -> None:
    assert len(TUI_COLORS) == 8
    assert "primary" in TUI_COLORS
    assert "success" in TUI_COLORS
    assert "danger" in TUI_COLORS


def test_regime_colors_has_4_regimes() -> None:
    assert len(REGIME_COLORS) == 4
    assert "PUSH" in REGIME_COLORS
    assert "MAINTAIN" in REGIME_COLORS
    assert "REDUCE" in REGIME_COLORS
    assert "RECOVER" in REGIME_COLORS


def test_quadrant_colors_has_4_quadrants() -> None:
    assert len(QUADRANT_COLORS) == 4
    assert "Q1" in QUADRANT_COLORS
    assert "Q2" in QUADRANT_COLORS
    assert "Q3" in QUADRANT_COLORS
    assert "Q4" in QUADRANT_COLORS


def test_get_tui_theme_returns_theme() -> None:
    theme = get_tui_theme()
    assert theme.name == "pav-dark"
    assert theme.primary == "#1E90FF"
    assert theme.background == "#0d0d1a"
    assert theme.dark is True
