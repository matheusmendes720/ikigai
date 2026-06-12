"""Time Block Display widget for PAV TUI."""
from __future__ import annotations

from textual.widgets import Static

STATUS_INDICATORS = {"OK": "✓", "WARN": "⚠", "CRIT": "✗", "PEND": "◌", "ACTIVE": "●"}


class TimeBlockDisplay(Static):
    """Display a single time block row: status + period + label + time range."""

    def __init__(
        self,
        label: str = "",
        start: str = "",
        end: str = "",
        status: str = "PEND",
        period: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.label = label
        self.start = start
        self.end = end
        self.status = status
        self.period = period

    def render(self) -> str:
        indicator = STATUS_INDICATORS.get(self.status, "○")
        time_range = f"{self.start}→{self.end}" if self.start and self.end else ""
        period_str = f"[{self.period}]" if self.period else ""
        return f"{indicator}  {period_str:<8} {self.label}  {time_range}"
