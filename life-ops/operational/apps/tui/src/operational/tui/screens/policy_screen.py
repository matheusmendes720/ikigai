"""Policy Screen for PAV TUI — data-bound.

Shows the current policy regime, last N decisions, and hysteresis
thresholds. Reads from the ``policy_decisions`` and
``policy_setpoints`` repos.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from operational.cli.state import policy_decisions as decisions_repo
from operational.core.next_step import get_current_regime
from operational.tui.widgets.regime_bar import RegimeBar
from rich.text import Text
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

MAX_HISTORY = 8  # how many decisions to show


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
    height: auto;
    width: 100%;
    padding: 1 2;
    color: $text-muted;
}
#decisions-list {
    height: auto;
    width: 100%;
    padding: 0 2;
    margin: 1 1;
    background: $surface;
    border: solid $border;
}
#hysteresis {
    height: auto;
    width: 100%;
    padding: 1 2;
    color: $accent;
    background: $surface;
}
"""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("🕹️ SETPOINT ATUAL", id="setpoint-title")
        yield RegimeBar(id="current-regime")
        yield Static(id="setpoint-detail")
        yield Static("📝 ÚLTIMAS DECISÕES DE POLÍTICA", id="history-title")
        yield Static(id="decisions-list")
        yield Static(id="hysteresis")
        yield Footer()

    def on_mount(self) -> None:
        # Defer the initial refresh until the widget tree is fully attached.
        self.call_after_refresh(self._refresh)

    def _refresh(self) -> None:
        regime = get_current_regime()
        self.query_one("#current-regime", RegimeBar).current = regime
        self.query_one("#setpoint-detail", Static).update(
            f"[bold]Modo atual: {regime}[/bold]   ·   "
            f"Decisões baseadas em sono, energia e foco dos últimos 7 dias."
        )

        # Decisions history
        try:
            decisions = sorted(
                decisions_repo.list(),
                key=lambda d: getattr(d, "date", None) or "",
                reverse=True,
            )[:MAX_HISTORY]
        except Exception:
            decisions = []

        if not decisions:
            self.query_one("#decisions-list", Static).update(
                "[dim]Nenhuma decisão registrada ainda.[/dim]\n"
                "[dim]A primeira aparece após `pav demo seed` ou `pav policy setpoints`.[/dim]"
            )
        else:
            lines: list[str] = []
            for d in decisions:
                date_str = str(getattr(d, "date", "—"))
                prev_state = getattr(d, "previous_state", None)
                from_state = str(prev_state.value) if prev_state else "?"
                curr_state = getattr(d, "state", "?")
                to_state = str(curr_state.value) if hasattr(curr_state, "value") else str(curr_state)
                reason = getattr(d, "rationale", "")
                severity = getattr(d, "severity", "INFO")
                sev_color = {
                    "CRITICAL": "red",
                    "WARNING": "yellow",
                    "INFO": "cyan",
                }.get(str(severity).upper(), "white")
                arrow = "→" if from_state != to_state else "="
                lines.append(
                    f"  [dim]{date_str}[/dim]  [{sev_color}]{from_state} {arrow} {to_state}[/{sev_color}]  "
                    f"[dim]({severity})[/dim]  {reason}"
                )
            self.query_one("#decisions-list", Static).update(Text.from_markup("\n".join(lines)))

        # Hysteresis thresholds (from PAV V3 §6 — see docs/algorithms/06-POLICY-ENGINE.md)
        self.query_one("#hysteresis", Static).update(Text.from_markup(
            "[bold]Histerese:[/bold]\n"
            "  PUSH  → MAINTAIN  @  Q_HE ≥ 7.5  por ≥ 2 dias\n"
            "  MAINTAIN → REDUCE   @  Q_HE ≤ 5.0  ou sono < 6.5h\n"
            "  REDUCE  → RECOVER  @  energia ≤ 3  por 2 dias\n"
            "  RECOVER → REDUCE    @  energia ≥ 6  + sono ≥ 7.5h"
        ))

    def action_show_history(self) -> None:
        self.app.notify(
            f"Mostrando últimas {MAX_HISTORY} decisões.",
            title="Histórico",
        )

    def action_show_setpoints(self) -> None:
        self.app.notify(
            "Setpoints: `pav policy setpoints` no CLI.",
            title="Setpoints",
        )
