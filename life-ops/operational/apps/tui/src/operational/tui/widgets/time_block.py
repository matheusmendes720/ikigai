"""Time Block Display widget for PAV TUI.

All attributes are reactive — assigning to them auto-refreshes the widget.
"""
from __future__ import annotations

from operational.tui.theme import TUI_COLORS
from textual.reactive import reactive
from textual.widgets import Static

STATUS_INDICATORS = {
    "OK": "✓",
    "WARN": "⚠",
    "CRIT": "✗",
    "PEND": "◌",
    "ACTIVE": "●",
}
STATUS_COLORS = {
    "OK": TUI_COLORS["success"],
    "WARN": TUI_COLORS["warning"],
    "CRIT": TUI_COLORS["danger"],
    "PEND": TUI_COLORS["muted"],
    "ACTIVE": TUI_COLORS["info"],
}
PERIOD_COLORS = {"MANHA": "#16213e", "TARDE": "#0f3460", "NOITE": "#1a1a2e"}
_TEXT = "#E0E0E0"
_MUTED = TUI_COLORS["muted"]


class TimeBlockDisplay(Static):
    """Display a single time block row: status + period + label + time range."""

    DEFAULT_CSS = """
    TimeBlockDisplay {
        height: 3;
        padding: 1 2;
        background: $surface;
        border: solid $border;
        color: $text;
    }
    """

    label = reactive("")
    start = reactive("")
    end = reactive("")
    status = reactive("PEND")
    period = reactive("")

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

    def update(  # type: ignore[override]
        self,
        *,
        label: str | None = None,
        start: str | None = None,
        end: str | None = None,
        status: str | None = None,
        period: str | None = None,
    ) -> None:
        if label is not None:
            self.label = label
        if start is not None:
            self.start = start
        if end is not None:
            self.end = end
        if status is not None:
            self.status = status
        if period is not None:
            self.period = period

    def watch_label(self, old: str, new: str) -> None:
        self.refresh()

    def watch_start(self, old: str, new: str) -> None:
        self.refresh()

    def watch_end(self, old: str, new: str) -> None:
        self.refresh()

    def watch_status(self, old: str, new: str) -> None:
        self.refresh()

    def watch_period(self, old: str, new: str) -> None:
        self.refresh()

    def render(self) -> str:
        indicator = STATUS_INDICATORS.get(self.status, "○")
        color = STATUS_COLORS.get(self.status, _MUTED)
        time_range = f"{self.start}→{self.end}" if self.start and self.end else ""
        period_str = f"[{self.period}]" if self.period else ""

        ind_markup = f"[{color}]{indicator}[/{color}]"

        if self.period in PERIOD_COLORS:
            pcolor = PERIOD_COLORS[self.period]
            period_markup = f"[{pcolor}]{period_str}[/{pcolor}]"
        else:
            period_markup = f"[{_MUTED}]{period_str}[/{_MUTED}]"

        return (
            f"{ind_markup}  {period_markup:<8} "
            f"[{_TEXT}]{self.label}[/{_TEXT}]  "
            f"[{_MUTED}]{time_range}[/{_MUTED}]"
        )
