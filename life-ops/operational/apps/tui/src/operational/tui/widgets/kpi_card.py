"""KPI Card widget for PAV TUI dashboard."""
from __future__ import annotations

from textual.widgets import Static

# PAV color palette for Rich markup
_CORAL = "#ff6b6b"
_TEAL = "#4ecdc4"
_TEXT = "#E0E0E0"
_TEXT_MUTED = "#A9A9A9"


class KPICard(Static):
    """Display a KPI metric card: icon + label + value + delta."""

    DEFAULT_CSS = """
    KPICard {
        border: solid $border;
        background: $surface;
        padding: 1 2;
        width: 100%;
        height: 3;
    }
    """

    def __init__(
        self,
        label: str,
        value: str,
        delta: str = "",
        icon: str = "",
        severity: str = "primary",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.label = label
        self.value = value
        self.delta = delta
        self.icon = icon
        self.severity = severity

    def render(self) -> str:
        icon_markup = f"[{_TEAL}]{self.icon}[/{_TEAL}] " if self.icon else ""
        label_markup = f"[{_TEXT}]{self.label:<12}[/{_TEXT}]"
        value_markup = f"[bold #fff]{self.value}[/bold #fff]"
        delta_markup = f"[{_TEXT_MUTED}]{self.delta}[/{_TEXT_MUTED}]" if self.delta else ""
        return f"{icon_markup}{label_markup} {value_markup} {delta_markup}"
