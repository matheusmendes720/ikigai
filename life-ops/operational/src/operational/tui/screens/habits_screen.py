"""Habits Screen for PAV TUI."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from operational.tui.widgets.habit_streak import HabitStreakDisplay

if TYPE_CHECKING:
    from textual.app import ComposeResult


class HabitsScreen(Screen):
    """List of all habits with streak, Q_HE score, and filter/sort."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Filtros: [physiological] [cognitive] [creative] [social]  Sort: [Q_HE▼]", id="filters")
        yield HabitStreakDisplay(name="Meditar", current_streak=7, best_streak=14, q_he=8.5)
        yield HabitStreakDisplay(name="Exercitar", current_streak=3, best_streak=10, q_he=7.2)
        yield HabitStreakDisplay(name="Leitura", current_streak=5, best_streak=21, q_he=9.0)
        yield HabitStreakDisplay(name="Journal", current_streak=4, best_streak=7, q_he=6.8)
        yield Footer()

    def on_mount(self) -> None:
        pass
