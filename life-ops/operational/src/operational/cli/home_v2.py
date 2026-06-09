"""V2 Home Menu — uses rich.layout.Layout for a structured dashboard.

Differences from v1 home:
- 3-zone Layout (header / menu / footer) with explicit size
- Menu grouped in 5 themed sections (FLUXO, DASHBOARD, RELATORIOS, DADOS, SISTEMA)
- Today's snapshot visible at the top (no need to run state show)
- Regime context (PUSH/MAINTAIN/REDUCE/RECOVER) shown in header
- Console.rule dividers between sections
- Backward compat: v1 home is still the default; opt-in via --v2 flag
"""
from __future__ import annotations

import io
import re
from contextlib import redirect_stdout
from datetime import date
from typing import NoReturn

from rich.console import Group
from rich.layout import Layout
from rich.padding import Padding
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from operational import __version__
from operational.cli.app import app as typer_app
from operational.cli.console import console
from operational.ui import strip_ansi
from operational.ui.components_v2 import header_v2, kpi_v2
from operational.ui.tokens import CONSOLE_WIDTH_V2, Glyph, SEVERITY


# Menu groups (key, label, subtitle) - organized by human workflow, not CRUD
MENU_GROUPS: list[tuple[str, str, list[tuple[str, str, str]]]] = [
    ("FLUXO", "FLUXO DO DIA", [
        ("1", "🌅  Iniciar Manhã",     "Acordou → sleep → ENTRY → workout"),
        ("2", "💻  Iniciar Tarde",     "Almoço → pomodoros → foco principal"),
        ("3", "🌙  Encerrar Dia",       "Jantar → shutdown → reflexão (OKRs)"),
        ("4", "⚡  Check-in Rápido",    "30s: registrar energia/foco do momento"),
    ]),
    ("DASHBOARD", "DASHBOARD", [
        ("5", "📊  Dashboard do Dia",   "Onde estou · o que está logado"),
    ]),
    ("RELATORIOS", "RELATÓRIOS", [
        ("6", "📈  Relatórios",         "Diário · Semanal · Estado consolidado"),
    ]),
    ("DADOS", "DADOS & HISTÓRICO", [
        ("7", "📚  Dados & Histórico",  "Rotinas · Blocos · Journal · Habits · Métricas"),
        ("8", "⚙️   Política & Ajuste",  "Setpoints PUSH/MAINTAIN/REDUCE/RECOVER"),
        ("9", "🎬  Demo & Testes",       "Seed 7 dias PAV · Limpar · Show · Run tests"),
    ]),
    ("SISTEMA", "SISTEMA", [
        ("10", "ℹ️   Sistema",          "Versão · Constantes · Tipos · Categorias"),
        ("q", "🚪  Sair",                "Exit"),
    ]),
]


def _make_header_bar() -> Text:
    """Top bar: PAV-OS name + regime context + date."""
    return Text()


def _render_group_table(group_key: str, group_label: str, items: list) -> Table:
    """Render one menu group as a Table."""
    t = Table.grid(expand=False, padding=(0, 1))
    t.add_column(min_width=4, justify="left", style="bold cyan")
    t.add_column(min_width=40, justify="left")
    t.add_column(justify="left", style="grey58")
    for key, label, sub in items:
        t.add_row(f"  {key} ", label, sub)
    return t


def _today_snapshot() -> RenderableType:
    """Build the today's-snapshot row at the top of the home menu."""
    from operational.core.services import get_day_snapshot
    try:
        snap = get_day_snapshot(date.today())
    except Exception:
        return Text("  (snapshot unavailable — run 'demo seed' to populate)", style="grey58")

    sleep_dur = snap.sleep.duration_hours
    sleep_str = f"{sleep_dur:.1f}h" if sleep_dur is not None else "—"
    pomo_str = f"{snap.n_pomodoros}/{snap.pomodoros_meta}" if snap.pomodoros_meta else "—/—"

    t = Table.grid(expand=False, padding=(0, 3))
    t.add_column(justify="left", style="bold cyan")
    t.add_column(justify="left")
    t.add_column(justify="left", style="bold cyan")
    t.add_column(justify="left")
    t.add_column(justify="left", style="bold cyan")
    t.add_column(justify="left")
    t.add_row(
        "Hoje:", date.today().isoformat(),
        "Sono:", sleep_str,
        "Pomodoros:", pomo_str,
    )
    return t


def _make_today_snapshot_renderable():
    """Today's snapshot as a renderable. Avoids circular import.

    If no data for today, finds the most recent day with data and
    shows that (e.g. when running on synthetic/golden dataset which
    contains historical days).
    """
    from rich.console import Group
    from operational.core.services import get_day_snapshot
    from operational.cli.state import day_contexts, sleep_records

    target_date = date.today()
    # If no data for today, use the most recent day with data
    ctx_list = day_contexts.list()
    if ctx_list and not any(c.date == target_date for c in ctx_list):
        target_date = max(c.date for c in ctx_list)

    try:
        snap = get_day_snapshot(target_date)
    except Exception:
        return Text("  (snapshot indisponivel — rode 'demo seed')", style="grey58")

    sleep_dur = snap.sleep.duration_hours
    sleep_str = f"{sleep_dur:.1f}h" if sleep_dur is not None else "—"
    pomo_str = f"{snap.n_pomodoros}/{snap.pomodoros_meta}" if snap.pomodoros_meta else "—"

    date_label = "Hoje:" if target_date == date.today() else f"Ultimo ({target_date.isoformat()}):"
    t = Table.grid(expand=False, padding=(0, 3))
    t.add_column(justify="left", style="bold cyan")
    t.add_column(justify="left")
    t.add_column(justify="left", style="bold cyan")
    t.add_column(justify="left")
    t.add_column(justify="left", style="bold cyan")
    t.add_column(justify="left")
    t.add_row(
        date_label, target_date.isoformat(),
        "Sono:", sleep_str,
        "Pomodoros:", pomo_str,
    )
    return t


def _make_menu_layout() -> Layout:
    """Build the v2 home menu layout (3 zones: header / menu / footer)."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="snapshot", size=2),
        Layout(name="menu"),
        Layout(name="footer", size=1),
    )
    return layout


def _run_cmd(args: list[str]) -> None:
    """Run a CLI command **in-process** and show output (thin orchestrator)."""
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            typer_app(args=args, standalone_mode=False)
    except SystemExit:
        pass
    except Exception as e:
        out.write(f"Error: {e}\n")
    text = out.getvalue()
    text = strip_ansi(text)
    if text.strip():
        console.print(text, end="")


def _prompt() -> str:
    """Prompt the user for a menu choice."""
    return Prompt.ask(
        "[bold cyan]Escolha[/] [grey58][1-10, q][/]",
        choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "q"],
        default="5",
        show_default=False,
    )


def run() -> None:
    """Run the v2 home menu — Layout-based dashboard."""
    # --- HEADER ---
    header_text = Text()
    header_text.append("  ◆ ", style="bold cyan")
    header_text.append("PAV-OS", style="bold white on dodger_blue1")
    header_text.append(" · Cybernetic Life OS", style="white")
    header_text.append("    ", style="default")
    header_text.append(f"v{__version__}", style="grey58")
    header_text.append("    ", style="default")
    header_text.append("regime: ", style="grey58")
    header_text.append("MAINTAIN", style=SEVERITY["primary"])
    console.print(header_text)
    console.print(Rule(style="grey30"))

    # --- SNAPSHOT (today at a glance) ---
    console.print(_make_today_snapshot_renderable())
    console.print()

    # --- MENU (grouped in 5 sections) ---
    for key, label, items in MENU_GROUPS:
        console.print(f"  [bold cyan]{label}[/]")
        for k, lbl, sub in items:
            console.print(f"    [bold cyan]{k}[/]  {lbl}  [grey58]{sub}[/]")
        console.print()

    # --- FOOTER (rule + prompt) ---
    console.print(Rule(style="grey30"))
    choice = _prompt()
    _dispatch(choice)


def _dispatch(choice: str) -> None:
    """Dispatch a menu choice to the appropriate command."""
    if choice == "q":
        console.print("[bold cyan]Até![/]")
        return

    # Map choice -> typer args
    dispatch_map = {
        "1": ["routine", "list"],
        "2": ["block", "list"],
        "3": ["reflect"],
        "4": ["state", "show"],
        "5": ["state", "show"],
        "6": ["report", "weekly"],
        "7": ["routine", "list"],
        "8": ["policy", "decisions"],
        "9": ["demo", "show"],
        "10": ["doctor", "doctor"],
    }
    args = dispatch_map.get(choice, ["--help"])
    _run_cmd(args)
    console.print()
    # Recurse for next action
    run()


__all__ = ["run", "MENU_GROUPS"]


# Avoid forward reference issue with RenderableType
from rich.console import RenderableType  # noqa: E402
