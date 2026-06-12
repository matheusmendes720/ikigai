"""Policy Screen for PAV TUI."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from operational.tui.widgets.regime_bar import RegimeBar

if TYPE_CHECKING:
    from textual.app import ComposeResult


class PolicyScreen(Screen):
    """Current regime + FSM transition history + hysteresis markers."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("🕹️ SETPOINT ATUAL", id="setpoint-title")
        yield RegimeBar(current="MAINTAIN", id="current-regime")
        yield Static("Atualizado: 2026-06-10  |  MAINTAIN ◆", id="setpoint-detail")
        yield Static("📝 ÚLTIMAS DECISÕES DE POLÍTICA", id="history-title")
        yield Static("2026-06-09 | PUSH → MAINTAIN | Fim de sprint")
        yield Static("2026-06-07 | MAINTAIN → REDUCE | Excesso de work")
        yield Static("2026-06-05 | REDUCE → MAINTAIN | Recuperação ok")
        yield Static("Histerese: PUSH→MAINTAIN @ Q_HE≥7.5 | MAINTAIN→REDUCE @ Q_HE≤5.0", id="hysteresis")
        yield Footer()

    def on_mount(self) -> None:
        pass
