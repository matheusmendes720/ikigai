"""V2 Home Menu — uses rich.layout.Layout for a structured dashboard.

The PAV-OS v2 home menu (definitive edition). 3-zone Layout (header /
menu / footer) with explicit size, 5 themed sections
(FLUXO, DASHBOARD, RELATORIOS, DADOS, SISTEMA), today's snapshot
visible at the top, regime context shown in header.
"""
from __future__ import annotations

import io
from contextlib import redirect_stdout
from datetime import date

from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from operational import __version__
from operational.cli.app import app as typer_app
from operational.cli.console import console
from operational.ui import strip_ansi
from operational.ui.tokens import SEVERITY


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


def _make_today_snapshot_renderable():
    """Today's snapshot as a renderable. Avoids circular import.

    If no data for today, finds the most recent day with data and
    shows that (e.g. when running on synthetic/golden dataset which
    contains historical days).
    """
    from operational.core.services import get_day_snapshot
    from operational.cli.state import day_contexts

    target_date = date.today()
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
    if choice != "q":
        Prompt.ask("[dim]Press Enter to continue[/dim]", default="")
    run()


__all__ = ["run", "MENU_GROUPS"]
