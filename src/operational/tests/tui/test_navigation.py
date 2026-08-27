"""Tests for operational.tui.navigation."""
from __future__ import annotations

from operational.tui.navigation import (
    ScreenKind,
    TUIState,
    screen_registry,
    get_state,
    set_state,
    navigate_to,
)


def test_screen_kind_has_7_variants() -> None:
    assert len(ScreenKind) == 7
    assert ScreenKind.DASHBOARD in ScreenKind
    assert ScreenKind.JOURNAL in ScreenKind


def test_tui_state_defaults() -> None:
    state = TUIState()
    assert state.current_screen == ScreenKind.DASHBOARD
    assert state.regime == "MAINTAIN"


def test_screen_registry_has_7_entries() -> None:
    assert len(screen_registry) == 7


def test_navigate_to_updates_state() -> None:
    state = get_state()
    original = state.current_screen
    navigate_to(ScreenKind.HABITS)
    assert get_state().current_screen == ScreenKind.HABITS
    navigate_to(original)