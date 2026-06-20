"""Habit Streak Display widget for PAV TUI."""
from __future__ import annotations

from textual.widgets import Static

# PAV colors for Rich markup
_CORAL = "#ff6b6b"
_TEAL = "#4ecdc4"
_TEXT = "#E0E0E0"
_TEXT_MUTED = "#A9A9A9"
_YELLOW = "#FFD700"


class HabitStreakDisplay(Static):
    """Display habit name, streak, best streak, Q_HE score, and streak bar."""

    DEFAULT_CSS = """
    HabitStreakDisplay {
        height: 3;
        padding: 1 2;
        background: $surface;
        border: solid $border;
    }
    """

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

    def _streak_bar(self) -> str:
        bar_full = "█"
        bar_empty = "░"
        max_len = 10
        filled = min(self.current_streak, max_len)
        return bar_full * filled + bar_empty * (max_len - filled)

    def _qhe_color(self) -> str:
        """Color gradient for Q_HE score: green >8, yellow 6-8, red <6."""
        if self.q_he >= 8.0:
            return "#00FF00"  # green
        elif self.q_he >= 6.0:
            return _YELLOW  # yellow
        elif self.q_he > 0:
            return _CORAL  # coral/red
        return _TEXT_MUTED

    def render(self) -> str:
        bar = self._streak_bar()
        bar_colored = f"[{_TEAL}]{bar}[/{_TEAL}]"
        q_color = self._qhe_color()
        q_label = f"[{q_color}]Q_HE: {self.q_he:.1f}[/{q_color}]" if self.q_he > 0 else f"[{_TEXT_MUTED}]Q_HE: -[/{_TEXT_MUTED}]"
        return (
            f"[bold {_TEXT}]{self.habit_name:<20}[/bold {_TEXT}]"
            f" {bar_colored}  "
            f"[{_TEXT_MUTED}]streak:{self.current_streak}[/{_TEXT_MUTED}]  "
            f"[{_TEXT_MUTED}]best:{self.best_streak}[/{_TEXT_MUTED}]  "
            f"{q_label}"
        )
