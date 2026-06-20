"""Pomodoro Grid widget for PAV TUI dashboard."""
from __future__ import annotations

from textual.widgets import Static

# PAV colors for Rich markup
_CORAL = "#ff6b6b"
_TEAL = "#4ecdc4"
_TEXT = "#E0E0E0"
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
    }
    """

    def __init__(
        self,
        sessions: list[list[str]] | None = None,
        focus_scores: list[int] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.sessions = sessions or [
            ["done", "done", "done", "skip"],
            ["done", "done", "skip", "skip"],
            ["skip", "skip", "skip", "skip"],
        ]
        self.focus_scores = focus_scores or [8, 6, 0]

    def _glyph(self, state: str) -> str:
        """Return colored glyph for round state."""
        glyph_map = {"done": "▣", "skip": "▢", "partial": "▤"}
        color_map = {"done": _GREEN, "skip": _TEXT_MUTED, "partial": _YELLOW}
        glyph = glyph_map.get(state, "○")
        color = color_map.get(state, _TEXT_MUTED)
        return f"[{color}]{glyph}[/{color}]"

    def render(self) -> str:
        lines = []
        labels = [
            (f"[bold {_TEXT}]S1[/bold {_TEXT}]", "[#16213e]MANHÃ[/#16213e]"),
            (f"[bold {_TEXT}]S2[/bold {_TEXT}]", "[#0f3460]TARDE[/#0f3460]"),
            (f"[bold {_TEXT}]S3[/bold {_TEXT}]", "[#1a1a2e]NOITE[/#1a1a2e]"),
        ]
        for i, (label, period_tag) in enumerate(labels):
            rounds = self.sessions[i] if i < len(self.sessions) else ["skip"] * 4
            cells = " ".join(self._glyph(s) for s in rounds)
            score = self.focus_scores[i] if i < len(self.focus_scores) else 0
            if score > 0:
                stars = f"[{_TEAL}]⭐ {score}[/{_TEAL}]"
            else:
                stars = f"[{_TEXT_MUTED}]⭐ -[/{_TEXT_MUTED}]"
            pct = round(sum(1 for s in rounds if s == "done") / len(rounds) * 100)
            pct_color = _GREEN if pct >= 75 else _YELLOW if pct >= 50 else _CORAL
            pct_markup = f"[{pct_color}]{pct}%[/{pct_color}]"
            lines.append(f"{label} {period_tag}  {cells}  {pct_markup}   {stars}")
        return "\n".join(lines)
