"""Pomodoro Grid widget for PAV TUI dashboard.

3 sessions (S1/S2/S3) x 4 rounds with done/skip/partial glyphs. All
attributes are reactive — assigning to them auto-refreshes the widget.
"""
from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static

# PAV period color tints (period-aware background swatches)
PERIOD_TAG = {
    "S1": "MANHÃ",
    "S2": "TARDE",
    "S3": "NOITE",
}

# PAV color tokens
_CORAL = "#ff6b6b"
_TEAL = "#4ecdc4"
_TEXT_MUTED = "#A9A9A9"
_GREEN = "#00FF00"
_YELLOW = "#FFD700"


class PomodoroGrid(Static):
    """Display 3 sessions (S1/S2/S3) × 4 rounds with done/skip/partial glyphs."""

    DEFAULT_CSS = """
    PomodoroGrid {
        height: auto;
        padding: 1 2;
        background: $surface;
        border: solid $border;
        color: $text;
    }
    """

    sessions: reactive[list[list[str]]] = reactive(
        list,
        init=False,
    )
    focus_scores: reactive[list[int]] = reactive(
        list,
        init=False,
    )

    def __init__(
        self,
        sessions: list[list[str]] | None = None,
        focus_scores: list[int] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        # _init sets reactive defaults before the watch fires
        self.set_reactive(
            PomodoroGrid.sessions,
            sessions or [
                ["skip"] * 4,
                ["skip"] * 4,
                ["skip"] * 4,
            ],
        )
        self.set_reactive(
            PomodoroGrid.focus_scores,
            focus_scores or [0, 0, 0],
        )

    def update(  # type: ignore[override]
        self,
        sessions: list[list[str]] | None = None,
        focus_scores: list[int] | None = None,
    ) -> None:
        if sessions is not None:
            self.sessions = sessions
        if focus_scores is not None:
            self.focus_scores = focus_scores

    def _glyph(self, state: str) -> str:
        glyph_map = {"done": "▣", "skip": "▢", "partial": "▤"}
        color_map = {"done": _GREEN, "skip": _TEXT_MUTED, "partial": _YELLOW}
        glyph = glyph_map.get(state, "○")
        color = color_map.get(state, _TEXT_MUTED)
        return f"[{color}]{glyph}[/{color}]"

    def watch_sessions(self, old: list[list[str]], new: list[list[str]]) -> None:
        self.refresh()

    def watch_focus_scores(self, old: list[int], new: list[int]) -> None:
        self.refresh()

    def render(self) -> str:
        lines: list[str] = []
        labels = [
            ("[bold]S1[/bold]", f"[{TUI_COLORS_DIM}]MANHÃ[/{TUI_COLORS_DIM}]"),
            ("[bold]S2[/bold]", f"[{TUI_COLORS_DIM}]TARDE[/{TUI_COLORS_DIM}]"),
            ("[bold]S3[/bold]", f"[{TUI_COLORS_DIM}]NOITE[/{TUI_COLORS_DIM}]"),
        ]
        for i, (label, period_tag) in enumerate(labels):
            rounds = self.sessions[i] if i < len(self.sessions) else ["skip"] * 4
            cells = " ".join(self._glyph(s) for s in rounds)
            score = self.focus_scores[i] if i < len(self.focus_scores) else 0
            if score > 0:
                stars = f"[{_TEAL}]⭐ {score}[/{_TEAL}]"
            else:
                stars = f"[{_TEXT_MUTED}]⭐ -[/{_TEXT_MUTED}]"
            pct = (
                round(sum(1 for s in rounds if s == "done") / len(rounds) * 100)
                if rounds else 0
            )
            pct_color = _GREEN if pct >= 75 else _YELLOW if pct >= 50 else _CORAL
            pct_markup = f"[{pct_color}]{pct}%[/{pct_color}]"
            lines.append(f"{label} {period_tag}  {cells}  {pct_markup}   {stars}")
        return "\n".join(lines)


# Period dim color (dark navy tints — pulled from theme)
TUI_COLORS_DIM = "#16213e"
