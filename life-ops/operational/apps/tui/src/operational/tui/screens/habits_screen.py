"""Habits Screen for PAV TUI."""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from operational.tui.widgets.habit_streak import HabitStreakDisplay

if TYPE_CHECKING:
    from textual.app import ComposeResult


class HabitsScreen(Screen):
    """List of all habits with streak, Q_HE score, and filter/sort."""

    BINDINGS: ClassVar = [
        Binding("a", "add_habit", "Add", show=False),
        Binding("e", "edit_habit", "Edit", show=False),
        Binding("d", "delete_habit", "Delete", show=False),
        Binding("f", "filter_habits", "Filter", show=False),
    ]

    CSS = """
HabitsScreen {
    background: $panel;
    layout: vertical;
}
#filters {
    height: 3;
    width: 100%;
    padding: 1 2;
    background: $surface;
    color: $text-muted;
}
HabitStreakDisplay {
    width: 100%;
    height: 3;
    margin: 0 1;
    border-bottom: solid $border;
    background: $surface;
}
"""

    def compose(self) -> ComposeResult:
        """Compose the habits screen widgets."""
        yield Header()
        yield Static(
            "Filtros: [physiological] [cognitive] [creative] [social]  Sort: [Q_HE▼]",
            id="filters",
        )
        yield HabitStreakDisplay(name="Meditar", current_streak=7, best_streak=14, q_he=8.5)
        yield HabitStreakDisplay(name="Exercitar", current_streak=3, best_streak=10, q_he=7.2)
        yield HabitStreakDisplay(name="Leitura", current_streak=5, best_streak=21, q_he=9.0)
        yield HabitStreakDisplay(name="Journal", current_streak=4, best_streak=7, q_he=6.8)
        yield Footer()

    def on_mount(self) -> None:
        """Initialize habit data on mount."""
        habits = [
            ("Meditar",    7,  14, 8.5),
            ("Exercitar",  3,  10, 7.2),
            ("Leitura",    5,  21, 9.0),
            ("Journal",    4,   7, 6.8),
        ]
        widgets = self.query(HabitStreakDisplay)
        for widget, (name, streak, best, qhe) in zip(widgets, habits, strict=False):
            widget.habit_name = name
            widget.current_streak = streak
            widget.best_streak = best
            widget.q_he = qhe
            widget.refresh()
