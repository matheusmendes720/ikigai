"""Habits Screen for PAV TUI — data-bound.

Lists all habits from the ``habits`` repo with their current streak,
best streak, and Q_HE score. Computes Q_HE inline from a simple
consistency heuristic (more advanced computation lives in
``operational.core.habit_engine``).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, ClassVar

from operational.cli.state import habits as habits_repo
from operational.cli.state import routine_logs as logs_repo
from operational.tui.widgets.habit_streak import HabitStreakDisplay
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

STREAK_LOOKBACK_DAYS = 30  # how many days back to count streak


def _compute_streak(habit_id: str) -> tuple[int, int]:
    """Return ``(current_streak, best_streak)`` for a habit.

    Counts consecutive days (ending today) where a routine_log mentions
    this habit's routine. Falls back to ``(0, 0)`` if no logs exist.
    """
    today = date.today()
    logs_by_date: dict[date, int] = {}
    for log in logs_repo.list():
        if str(getattr(log, "routine_id", "")) == habit_id:
            d = getattr(log, "date", None)
            if d is None:
                continue
            logs_by_date[d] = logs_by_date.get(d, 0) + 1

    # current streak: walk back from today while we have logs
    current = 0
    d = today
    while d in logs_by_date:
        current += 1
        d -= timedelta(days=1)

    # best streak: max consecutive days in the lookback window
    best = 0
    streak = 0
    for i in range(STREAK_LOOKBACK_DAYS):
        d = today - timedelta(days=i)
        if d in logs_by_date:
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    return current, best


def _compute_q_he(current_streak: int, best_streak: int) -> float:
    """Return a 0-10 Q_HE score based on streak.

    Uses H(t) = 1 − e^(−λ·streak), scaled to [0, 10]. λ = 0.15.
    """
    import math
    lam = 0.15
    h = 1.0 - math.exp(-lam * current_streak)
    return round(h * 10, 1)


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
#empty-msg {
    padding: 2 4;
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
        yield Header()
        yield Static(
            "[F]iltros: [physiological] [cognitive] [creative] [social]   "
            "[O]rdenar: [Q_HE▼] [streak▼] [name▲]",
            id="filters",
        )
        yield Static(id="empty-msg")
        yield Footer()

    def on_mount(self) -> None:
        self.call_after_refresh(self._refresh)

    def _refresh(self) -> None:
        for w in self.query(HabitStreakDisplay):
            w.remove()

        empty = self.query_one("#empty-msg", Static)
        try:
            all_habits = list(habits_repo.list())
        except Exception:
            all_habits = []
        if not all_habits:
            empty.update(
                "[dim]Nenhum hábito cadastrado.[/dim]\n"
                "[dim]Adicione com: `pav habit create \"Nome\" physiological`[/dim]"
            )
            return
        empty.update("")

        for h in all_habits:
            hid = str(getattr(h, "id", ""))
            try:
                cur, best = _compute_streak(hid)
                qhe = _compute_q_he(cur, best)
            except Exception:
                cur, best, qhe = 0, 0, 0.0
            self.mount(HabitStreakDisplay(
                name=getattr(h, "name", "(sem nome)"),
                current_streak=cur,
                best_streak=best,
                q_he=qhe,
            ))

    def action_add_habit(self) -> None:
        self.app.notify(
            "Use `pav habit create \"Nome\" physiological` para adicionar.",
            title="Novo hábito",
        )

    def action_edit_habit(self) -> None:
        self.app.notify("Edição em breve — use `pav habit list` no CLI.", title="Editar")

    def action_delete_habit(self) -> None:
        self.app.notify("Remoção em breve — use `pav habit delete <id>`.", title="Remover")

    def action_filter_habits(self) -> None:
        self.app.notify("Filtro em breve.", title="Filtrar")
