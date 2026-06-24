"""KPI Card widget for PAV TUI dashboard.

Reactive: ``label``, ``value``, ``delta``, ``icon`` are Textual reactive
attributes — assigning to them auto-refreshes the widget.
"""
from __future__ import annotations

from operational.tui.theme import TUI_COLORS
from textual.reactive import reactive
from textual.widgets import Static


class KPICard(Static):
    """Display a KPI metric card: icon + label + value + delta."""

    DEFAULT_CSS = """
    KPICard {
        border: solid $border;
        background: $surface;
        padding: 1 2;
        width: 100%;
        height: 3;
        color: $text;
    }
    """

    label = reactive("")
    value = reactive("")
    delta = reactive("")
    icon = reactive("")
    severity = reactive("primary")

    def __init__(
        self,
        label: str = "",
        value: str = "",
        delta: str = "",
        icon: str = "",
        severity: str = "primary",
        *,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        # Seed reactive defaults (set before mount to avoid spurious refreshes)
        self.label = label
        self.value = value
        self.delta = delta
        self.icon = icon
        self.severity = severity

    def update(  # type: ignore[override]
        self,
        *,
        value: str | None = None,
        delta: str | None = None,
        icon: str | None = None,
        severity: str | None = None,
        label: str | None = None,
    ) -> None:
        """Atomically update one or more reactive fields and refresh once."""
        if value is not None:
            self.value = value
        if delta is not None:
            self.delta = delta
        if icon is not None:
            self.icon = icon
        if severity is not None:
            self.severity = severity
        if label is not None:
            self.label = label

    def render(self) -> str:
        icon_markup = (
            f"[{TUI_COLORS['info']}]{self.icon}[/{TUI_COLORS['info']}] "
            if self.icon else ""
        )
        label_markup = f"[bold]{self.label:<12}[/bold]"
        sev_color = TUI_COLORS.get(self.severity, TUI_COLORS["primary"])
        value_markup = f"[bold {sev_color}]{self.value}[/bold {sev_color}]"
        delta_markup = (
            f"[{TUI_COLORS['muted']}]{self.delta}[/{TUI_COLORS['muted']}]"
            if self.delta else ""
        )
        return f"{icon_markup}{label_markup} {value_markup} {delta_markup}"
