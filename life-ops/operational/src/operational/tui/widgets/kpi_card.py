"""KPI Card widget for PAV TUI dashboard."""
from __future__ import annotations

from textual.widgets import Static


class KPICard(Static):
    """Display a KPI metric card: icon + label + value + delta."""

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
        icon = f"{self.icon} " if self.icon else ""
        delta = f"  {self.delta}" if self.delta else ""
        return f"{icon}{self.label:<12} {self.value}{delta}"
