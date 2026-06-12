"""Habit Streak Display widget for PAV TUI."""
from __future__ import annotations

from textual.widgets import Static


class HabitStreakDisplay(Static):
    """Display habit name, streak, best streak, Q_HE score, and streak bar."""

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

    def render(self) -> str:
        bar = self._streak_bar()
        q_label = f"Q_HE: {self.q_he:.1f}" if self.q_he > 0 else "Q_HE: -"
        return f"{self.habit_name:<20} {bar}  streak:{self.current_streak}  best:{self.best_streak}  {q_label}"
