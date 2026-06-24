"""Habit Streak Display widget for PAV TUI.

All attributes are reactive — assigning to them auto-refreshes the widget.
"""
from __future__ import annotations

# PAV color tokens (single source of truth: operational.tui.theme)
from operational.tui.theme import TUI_COLORS
from textual.reactive import reactive
from textual.widgets import Static

_TEAL = TUI_COLORS["info"]
_TEXT = "#E0E0E0"
_TEXT_MUTED = TUI_COLORS["muted"]
_YELLOW = TUI_COLORS["warning"]
_CORAL = TUI_COLORS["danger"]


class HabitStreakDisplay(Static):
    """Display habit name, streak, best streak, Q_HE score, and streak bar."""

    DEFAULT_CSS = """
    HabitStreakDisplay {
        height: 3;
        padding: 1 2;
        background: $surface;
        border: solid $border;
        color: $text;
    }
    """

    habit_name = reactive("")
    current_streak = reactive(0)
    best_streak = reactive(0)
    q_he = reactive(0.0)

    def __init__(
        self,
        name: str = "",
        current_streak: int = 0,
        best_streak: int = 0,
        q_he: float = 0.0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.habit_name = name
        self.current_streak = current_streak
        self.best_streak = best_streak
        self.q_he = q_he

    def update(  # type: ignore[override]
        self,
        *,
        habit_name: str | None = None,
        current_streak: int | None = None,
        best_streak: int | None = None,
        q_he: float | None = None,
    ) -> None:
        if habit_name is not None:
            self.habit_name = habit_name
        if current_streak is not None:
            self.current_streak = current_streak
        if best_streak is not None:
            self.best_streak = best_streak
        if q_he is not None:
            self.q_he = q_he

    def _streak_bar(self) -> str:
        bar_full = "█"
        bar_empty = "░"
        max_len = 10
        filled = min(self.current_streak, max_len)
        return bar_full * filled + bar_empty * (max_len - filled)

    def _qhe_color(self) -> str:
        if self.q_he >= 8.0:
            return TUI_COLORS["success"]
        if self.q_he >= 6.0:
            return _YELLOW
        if self.q_he > 0:
            return _CORAL
        return _TEXT_MUTED

    def watch_habit_name(self, old: str, new: str) -> None:
        self.refresh()

    def watch_current_streak(self, old: int, new: int) -> None:
        self.refresh()

    def watch_best_streak(self, old: int, new: int) -> None:
        self.refresh()

    def watch_q_he(self, old: float, new: float) -> None:
        self.refresh()

    def render(self) -> str:
        bar = self._streak_bar()
        bar_colored = f"[{_TEAL}]{bar}[/{_TEAL}]"
        q_color = self._qhe_color()
        if self.q_he > 0:
            q_label = f"[{q_color}]Q_HE: {self.q_he:.1f}[/{q_color}]"
        else:
            q_label = f"[{_TEXT_MUTED}]Q_HE: -[/{_TEXT_MUTED}]"
        return (
            f"[bold {_TEXT}]{self.habit_name:<20}[/bold {_TEXT}]"
            f" {bar_colored}  "
            f"[{_TEXT_MUTED}]streak:{self.current_streak}[/{_TEXT_MUTED}]  "
            f"[{_TEXT_MUTED}]best:{self.best_streak}[/{_TEXT_MUTED}]  "
            f"{q_label}"
        )
