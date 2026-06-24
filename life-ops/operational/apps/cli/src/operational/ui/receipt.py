"""Transaction receipt — small helper for the four CRUD commands
(routine, reflect, metric, lunch) to show a beautiful success panel
after recording a Pydantic entity.

The v2 production-grade "Recibo de Transação" looks like:

╭─ ⚙️ Processando Parâmetros ────────╮
│  Propriedade     Valor  Inserido     Status                              │
│ ─────────────────────────────────────────────────────────────────────────│
│  Nome (name)    : Wake Up            [✓] Ok                              │
│  Turno (period) : MANHA              [✓] Ok                              │
╰─────────────────────────────────────────────────────────────────────────╯

✅ SUCESSO: <summary>
Detalhes: ID <ueid> | Range: <range>
"""
from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from operational.ui.tokens import SEVERITY, STYLES


def receipt_panel(
    title: str,
    icon: str,
    success_message: str,
    detail_pairs: list[tuple[str, str]],
    severity: str = "success",
    footer: str = "",
) -> object:
    """Build a transaction-receipt Group: parameters table + success line.

    Args:
        title: Top-of-panel section title (e.g. "NOVA ROTINA").
        icon: Icon prefix (e.g. "📝", "✅", "😴").
        success_message: Single-line success message in bold.
        detail_pairs: List of ``(key, value)`` tuples to render as a 2-col table.
        severity: "success" (green) | "warning" (yellow) | "danger" (red).
        footer: Optional secondary line below the success message.
    """
    clr = SEVERITY.get(severity, SEVERITY["success"])
    param_grid = Table.grid(expand=False, padding=(0, 2))
    param_grid.add_column(min_width=22, justify="left")
    param_grid.add_column(min_width=2, justify="left")
    param_grid.add_column(min_width=42, justify="left")
    for key, value in detail_pairs:
        param_grid.add_row(
            Text(f"  {key}", style=STYLES["body_muted"]),
            Text(":", style=STYLES["body_muted"]),
            Text(str(value), style="bold white"),
        )

    params_panel = Panel(
        param_grid,
        title=f"[{SEVERITY['info']}] {icon} {title} [/]",
        border_style=SEVERITY["info"],
        padding=(0, 1),
    )

    success_line = Text()
    success_line.append(f"  {icon} ", style=clr)
    success_line.append("SUCESSO: ", style=f"bold {clr}")
    success_line.append(success_message, style="bold white")
    if footer:
        success_line.append("\n  ", style="default")
        success_line.append(footer, style=STYLES["body_muted"])

    return Group(params_panel, "", success_line)


__all__ = ["receipt_panel"]
