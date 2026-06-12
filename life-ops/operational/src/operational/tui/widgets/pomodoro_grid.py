"""Pomodoro Grid widget for PAV TUI dashboard."""
from __future__ import annotations

from textual.widgets import Static


class PomodoroGrid(Static):
    """Display 3 sessions (S1/S2/S3) × 4 rounds with done/skip/partial glyphs."""

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
        return {"done": "▣", "skip": "▢", "partial": "▤"}.get(state, "○")

    def render(self) -> str:
        lines = []
        labels = ["S1 manha", "S2 tarde", "S3 noite"]
        for i, (label, rounds) in enumerate(zip(labels, self.sessions, strict=False)):
            cells = " ".join(self._glyph(s) for s in rounds)
            score = self.focus_scores[i] if i < len(self.focus_scores) else 0
            stars = f"⭐ {score}/10" if score > 0 else "⭐ -"
            pct = round(sum(1 for s in rounds if s == "done") / len(rounds) * 100)
            lines.append(f"{label}  {cells}  {pct}%   {stars}")
        return "\n".join(lines)
