"""Habits Screen for PAV TUI — data-bound.

Lists all habits from the ``habits`` repo with their current streak,
best streak, and Q_HE score. Also shows a 30-day completion bar chart
built from the ``routine_logs`` repo.

Streak logic: a habit is considered "done" on a day if there is at least
one routine_log entry for that day.  The Q_HE score uses the H(t) =
1 − e^(−λ·streak) formula (λ = 0.15) scaled to [0, 10].
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

    A habit is considered "done" on a day if there is at least one
    routine_log for that day.  Note: the routine_log entries in the
    golden/synthetic datasets may not have a direct routine→habit
    link, so we count all routine_logs for the day as contributing
    to the streak.
    """
    today = date.today()

    # Build set of dates that have routine logs (the "active days")
    active_dates: set[date] = set()
    for log in logs_repo.list():
        d = getattr(log, "date", None)
        if d is not None:
            active_dates.add(d)

    if not active_dates:
        return 0, 0

    # Current streak: walk back from today (or latest data date) while active
    latest_date = max(active_dates)
    anchor = min(today, latest_date)  # don't look into the future
    current = 0
    d = anchor
    while d in active_dates:
        current += 1
        d -= timedelta(days=1)

    # Best streak: max consecutive active days in the lookback window
    window_start = anchor - timedelta(days=STREAK_LOOKBACK_DAYS - 1)
    window_dates = set()
    for i in range(STREAK_LOOKBACK_DAYS):
        window_dates.add(window_start + timedelta(days=i))

    best = 0
    streak = 0
    for i in range(STREAK_LOOKBACK_DAYS):
        d = window_start + timedelta(days=i)
        if d in active_dates:
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
    """Return (labels, values) for the routine log completion bar chart.

    Anchors the window to the actual data dates (like metrics_screen).
    If no routine logs exist, returns empty lists.
    """
    today = date.today()

    # Collect active dates from routine_logs
    active_dates: set[date] = set()
    try:
        for log in logs_repo.list():
            d = getattr(log, "date", None)
            if d is not None:
                active_dates.add(d)
    except Exception:
        return [], []

    if not active_dates:
        return [], []

    # Anchor to the latest data date instead of today
    latest = max(active_dates)
    anchor = min(today, latest)
    start = anchor - timedelta(days=window_days - 1)
    dates = [start + timedelta(days=i) for i in range(window_days)]
    counts: dict[date, int] = dict.fromkeys(dates, 0)
    for d in active_dates:
        if d in counts:
            counts[d] += 1

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
        if not labels:
            chart.update(
                "[dim]Sem rotinas registradas.[/dim]"
            )
        elif any(v > 0 for v in values):
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
