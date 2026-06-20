"""Policy Screen for PAV TUI."""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from operational.tui.widgets.regime_bar import RegimeBar

if TYPE_CHECKING:
    from textual.app import ComposeResult


class PolicyScreen(Screen):
    """Current regime + FSM transition history + hysteresis markers."""

    BINDINGS: ClassVar = [
        Binding("h", "show_history", "History", show=False),
        Binding("s", "show_setpoints", "Setpoints", show=False),
    ]

    CSS = """
PolicyScreen {
    background: $panel;
    layout: vertical;
}
#setpoint-title, #history-title {
    height: 3;
    width: 100%;
    padding: 1 2;
    background: $surface;
    color: $text;
    text-style: bold;
}
#current-regime {
    width: 100%;
    height: 3;
    margin: 1 1;
    border: solid $border;
    background: $surface;
}
#setpoint-detail {
    height: 3;
    width: 100%;
    padding: 0 2;
    color: $text-muted;
}
#hysteresis {
    height: 3;
    width: 100%;
    padding: 1 2;
    color: $teal;
    background: $surface;
}
"""

    def compose(self) -> ComposeResult:
        """Compose the policy screen widgets."""
        yield Header()
        yield Static("🕹️ SETPOINT ATUAL", id="setpoint-title")
        yield RegimeBar(current="MAINTAIN", id="current-regime")
        yield Static("Atualizado: 2026-06-10  |  MAINTAIN ◆", id="setpoint-detail")
        yield Static("📝 ÚLTIMAS DECISÕES DE POLÍTICA", id="history-title")
        yield Static("2026-06-09 | PUSH → MAINTAIN | Fim de sprint")
        yield Static("2026-06-07 | MAINTAIN → REDUCE | Excesso de work")
        yield Static("2026-06-05 | REDUCE → MAINTAIN | Recuperação ok")
        yield Static(
            "Histerese: PUSH→MAINTAIN @ Q_HE≥7.5 | MAINTAIN→REDUCE @ Q_HE≤5.0",
            id="hysteresis",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize policy state on mount."""
        self.query_one("#current-regime", RegimeBar).current = "MAINTAIN"
        self.query_one("#setpoint-detail", Static).update(
            "Atualizado: 2026-06-12  |  MAINTAIN ◆"
        )
