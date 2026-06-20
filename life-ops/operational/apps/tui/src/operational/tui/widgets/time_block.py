"""Time Block Display widget for PAV TUI."""
from __future__ import annotations

from textual.widgets import Static

STATUS_INDICATORS = {"OK": "✓", "WARN": "⚠", "CRIT": "✗", "PEND": "◌", "ACTIVE": "●"}
STATUS_COLORS = {"OK": "#00FF00", "WARN": "#FFD700", "CRIT": "#FF4444", "PEND": "#A9A9A9", "ACTIVE": "#4ecdc4"}

# PAV period colors
PERIOD_COLORS = {"MANHA": "#16213e", "TARDE": "#0f3460", "NOITE": "#1a1a2e"}
_TEXT = "#E0E0E0"


class TimeBlockDisplay(Static):
    """Display a single time block row: status + period + label + time range."""

    DEFAULT_CSS = """
    TimeBlockDisplay {
        height: 3;
        padding: 1 2;
        background: $surface;
        border: solid $border;
    }
    """

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
        color = STATUS_COLORS.get(self.status, "#A9A9A9")
        time_range = f"{self.start}→{self.end}" if self.start and self.end else ""
        period_str = f"[{self.period}]" if self.period else ""

        # Build colored indicator
        ind_markup = f"[{color}]{indicator}[/{color}]"

        # Build period tag with period color
        if self.period in PERIOD_COLORS:
            pcolor = PERIOD_COLORS[self.period]
            period_markup = f"[{pcolor}]{period_str}[/{pcolor}]"
        else:
            period_markup = f"[#A9A9A9]{period_str}[/#A9A9A9]"

        return f"{ind_markup}  {period_markup:<8} [{_TEXT}]{self.label}[/{_TEXT}]  [#A9A9A9]{time_range}[/#A9A9A9]"
