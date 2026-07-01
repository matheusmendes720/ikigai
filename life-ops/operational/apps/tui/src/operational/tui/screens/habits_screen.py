"""Habits Screen for PAV TUI — data-bound.

Lists all habits from the ``habits`` repo with their current streak,
best streak, and Q_HE score. Computes Q_HE inline from a simple
consistency heuristic (more advanced computation lives in
``operational.core.habit_engine``).

Also shows a 30-day habit completion bar chart built from the
``routine_logs`` repo so users can see their daily compliance at a
glance.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, ClassVar

from operational.cli.state import habits as habits_repo
from operational.cli.state import routine_logs as logs_repo
from operational.tui.widgets.habit_streak import HabitStreakDisplay
from operational.tui.widgets.sparkline_chart import ChartColors, PlotextChart
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

STREAK_LOOKBACK_DAYS = 30  # how many days back to count streak
COMPLETION_WINDOW_DAYS = 30


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


def _completion_per_day(window_days: int) -> tuple[list[str], list[int]]:
    today = date.today()
    dates = [today - timedelta(days=i) for i in range(window_days - 1, -1, -1)]
    counts: dict[date, int] = dict.fromkeys(dates, 0)
    try:
        for log in logs_repo.list():
            d = getattr(log, "date", None)
            if d in counts:
                counts[d] += 1
    except Exception:
        pass
    labels = [d.strftime("%d/%m") for d in dates]
    values = [counts[d] for d in dates]
    return labels, values


class HabitsScreen(Screen):  # type: ignore[type-arg]
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
#chart-label {
    height: 3;
    width: 100%;
    padding: 1 2;
    color: $text;
    text-style: bold;
}
#habits-chart {
    height: 10;
    width: 100%;
    padding: 0 2;
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
        yield Static(
            f"Conclusão de hábitos — últimos {COMPLETION_WINDOW_DAYS} dias",
            id="chart-label",
        )
        yield PlotextChart(id="habits-chart")
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
                '[dim]Adicione com: `pav habit create "Nome" physiological`[/dim]'
            )
        else:
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

        self._render_completion_chart()

    def _render_completion_chart(self) -> None:
        labels, values = _completion_per_day(COMPLETION_WINDOW_DAYS)
        chart = self.query_one("#habits-chart", PlotextChart)
        if any(v > 0 for v in values):
            chart.bar_chart(
                labels,
                [float(v) for v in values],
                color=ChartColors.ENERGY["primary"],
                orientation="v",
                bar_width=0.7,
                y_label="rotinas",
                title=f"Rotinas/dia — últimos {COMPLETION_WINDOW_DAYS}d",
                hide_grid=True,
            )
        else:
            chart.update(
                "[dim]Sem rotinas registradas nesta janela — "
                f"últimos {COMPLETION_WINDOW_DAYS} dias.[/dim]"
            )

    def action_add_habit(self) -> None:
        self.app.notify(
            'Use `pav habit create "Nome" physiological` para adicionar.',
            title="Novo hábito",
        )

    def action_edit_habit(self) -> None:
        self.app.notify("Edição em breve — use `pav habit list` no CLI.", title="Editar")

    def action_delete_habit(self) -> None:
        self.app.notify("Remoção em breve — use `pav habit delete <id>`.", title="Remover")

    def action_filter_habits(self) -> None:
        self.app.notify("Filtro em breve.", title="Filtrar")
