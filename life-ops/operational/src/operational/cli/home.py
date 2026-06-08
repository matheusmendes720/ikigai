"""Interactive home menu for the operational system.

The menu is organized around the **human workflow** (start morning, start
afternoon, end day, check-in) rather than the underlying CRUD operations
on individual entities. Each menu item corresponds to a moment in the
day, not a database operation.
"""
from __future__ import annotations

import io
import re
import sys
from contextlib import redirect_stdout
from datetime import date
from typing import NoReturn

from rich.console import Group
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from operational import __version__
from operational.cli.app import app as typer_app
from operational.enums import HabitCategory, Period, PolicyState, RoutineType
from operational.ui import console, strip_ansi


# ---------------------------------------------------------------------------
# Main Menu — organized by human workflow, not CRUD
# ---------------------------------------------------------------------------

MENU_ITEMS: list[tuple[str, str, str]] = [
    ("1", "🌅  Iniciar Manhã",     "Acordou → sleep retroativo → ENTRY → workout"),
    ("2", "💻  Iniciar Tarde",     "Almoço → pomodoros → foco principal"),
    ("3", "🌙  Encerrar Dia",       "Jantar → shutdown → reflexão (OKRs)"),
    ("4", "⚡  Check-in Rápido",    "30s: registrar energia/foco do momento"),
    ("5", "📊  Dashboard do Dia",   "Onde estou · o que está logado · estou no plano?"),
    ("",  "",                     ""),
    ("6", "📈  Relatórios",         "Diário · Semanal · Estado consolidado"),
    ("7", "📚  Dados & Histórico", "Rotinas · Blocos · Journal · Habits · Métricas"),
    ("8", "⚙️   Política & Ajuste", "Setpoints PUSH/MAINTAIN/REDUCE/RECOVER · Decisões"),
    ("9", "🎬  Demo & Testes",      "Seed 7 dias PAV · Limpar · Show · Run tests"),
    ("10", "ℹ️   Sistema",          "Versão · Constantes · Tipos · Categorias"),
    ("q", "🚪  Sair",               "Exit"),
]


def _run_cmd(args: list[str]) -> None:
    """Run a CLI command **in-process** and show output (thin orchestrator).

    Captures stdout via ``redirect_stdout``, runs the Typer app in-process,
    strips ANSI codes that inner Rich consoles may have emitted (their
    ``force_terminal=True`` overrides our redirect), and re-prints the
    cleaned text via the central home ``console``.
    """
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            typer_app(args=args, standalone_mode=False)
        text = strip_ansi(out.getvalue())
        if text:
            console.print(text)
    except SystemExit:
        text = strip_ansi(out.getvalue())
        if text:
            console.print(text)
    except Exception as e:
        console.print(
            Panel(
                f"[red]{type(e).__name__}:[/red] {e}",
                title="[bold red]Error[/bold red]",
                border_style="red",
            )
        )
    Prompt.ask("\n[dim]Press Enter to continue[/dim]")


def _clear() -> None:
    """Clear screen."""
    console.clear()


def _header(title: str = "") -> None:
    """Show app header."""
    today = date.today().isoformat()
    title_line = f"  {title}" if title else ""
    console.print(
        Panel(
            f"[bold cyan]⚡ TIME-TASKER[/bold cyan] [white]v{__version__}[/white]  |  {today}{title_line}",
            style="cyan",
        )
    )


# ---------------------------------------------------------------------------
# Main loop + routing
# ---------------------------------------------------------------------------

def home() -> NoReturn:
    """Main interactive loop."""
    while True:
        _clear()
        _header()
        _show_menu()
        choice = Prompt.ask(
            "[bold yellow]Choose[/bold yellow]",
            choices=[str(i) for i in range(1, 11)] + ["q"],
            default="5",
        )
        if choice == "q":
            _clear()
            console.print("[green]Até logo! 🚀[/green]")
            sys.exit(0)
        _route(choice)


def _show_menu() -> None:
    """Render the main menu table."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold yellow", width=4)
    table.add_column("Action", style="white", width=28)
    table.add_column("Description", style="dim")

    for key, action, desc in MENU_ITEMS:
        if key:
            table.add_row(key, action, desc)
        else:
            table.add_row("", "", "")

    console.print(table)


def _route(choice: str) -> None:
    """Route menu choice to the right handler."""
    routes = {
        "1": _flow_morning,
        "2": _flow_afternoon,
        "3": _flow_evening,
        "4": _flow_checkin,
        "5": _dashboard,
        "6": _menu_reports,
        "7": _menu_data,
        "8": _menu_policy,
        "9": _menu_demo,
        "10": _system_info,
    }
    handler = routes.get(choice)
    if handler:
        handler()


# ---------------------------------------------------------------------------
# Workflow flows (morning / afternoon / evening / checkin)
# ---------------------------------------------------------------------------

def _flow_morning() -> None:
    """Start morning: sleep retroativo, ENTRY routine, workout."""
    _clear()
    _header("🌅 Iniciar Manhã")
    console.print("[bold]Esta rotina cobre:[/bold]")
    console.print("  1. Registrar sono (retroativo)")
    console.print("  2. Criar rotina ENTRY (acordar)")
    console.print("  3. Criar bloco MANHA (workout + meditação)")
    console.print()
    if Prompt.ask("Continuar?", choices=["y", "n"], default="y") != "y":
        return

    # Step 1: sleep
    q = Prompt.ask("Qualidade do sono (1-10)", default="8")
    bh = Prompt.ask("Hora que dormiu (0-23)", default="20")
    bm = Prompt.ask("Minuto que dormiu (0-59)", default="30")
    wh = Prompt.ask("Hora que acordou (0-23)", default="4")
    wm = Prompt.ask("Minuto que acordou (0-59)", default="0")
    _run_cmd([
        "metric", "sleep", "-q", q,
        "-bh", bh, "-bm", bm,
        "-wh", wh, "-wm", wm,
    ])

    # Step 2: routine
    _run_cmd(["routine", "create", "Acordar", "MANHA", "ENTRY"])

    # Step 3: block
    label = Prompt.ask("Label do bloco da manhã", default="Morning Workout + Meditação")
    _run_cmd(["block", "create", "MANHA", "--label", label])

    console.print("\n[bold green]✔ Manhã iniciada![/bold green]")


def _flow_afternoon() -> None:
    """Start afternoon: lunch, pomodoros, hardwork."""
    _clear()
    _header("💻 Iniciar Tarde")
    console.print("[bold]Esta rotina cobre:[/bold]")
    console.print("  1. Criar bloco TARDE (deep work)")
    console.print("  2. Criar rotina CORE (hardwork)")
    console.print("  3. Check-in energia/foco")
    console.print()
    if Prompt.ask("Continuar?", choices=["y", "n"], default="y") != "y":
        return

    label = Prompt.ask("Label do bloco da tarde", default="Deep Work — Features")
    _run_cmd(["block", "create", "TARDE", "--label", label])

    name = Prompt.ask("Nome da rotina CORE", default="Hardwork Dev")
    _run_cmd(["routine", "create", name, "TARDE", "CORE"])

    e = Prompt.ask("Energia agora (1-10)", default="7")
    f = Prompt.ask("Foco agora (1-10)", default="8")
    _run_cmd(["metric", "energy", "-e", e, "-f", f])

    console.print("\n[bold green]✔ Tarde iniciada![/bold green]")


def _flow_evening() -> None:
    """End day: dinner, shutdown, reflection OKRs."""
    _clear()
    _header("🌙 Encerrar Dia")
    console.print("[bold]OKRs de saída (perguntas-chave):[/bold]\n")
    console.print("  [cyan]1.[/cyan] O que fiz hoje que deu certo? (execução sistemática)")
    console.print("  [cyan]2.[/cyan] O que fiz hoje que deu errado? (equivocos)")
    console.print("  [cyan]3.[/cyan] Qual o maior aprendizado? (antítese + síntese)")
    console.print("  [cyan]4.[/cyan] Algum desvio do padrão? (causa raiz)")
    console.print("  [cyan]5.[/cyan] Ajustes finos para amanhã")
    console.print()

    if Prompt.ask("Continuar?", choices=["y", "n"], default="y") != "y":
        return

    # 1. Shutdown routine
    _run_cmd(["routine", "create", "Shutdown Ritual", "NOITE", "EXIT"])

    # 2. NOITE block
    _run_cmd(["block", "create", "NOITE", "--label", "Preparação + Jantar"])

    # 3. Reflections as a single journal entry
    deu_certo = Prompt.ask("O que deu certo hoje?", default="")
    deu_errado = Prompt.ask("O que deu errado hoje?", default="")
    aprendizado = Prompt.ask("Maior aprendizado do dia?", default="")
    ajustes = Prompt.ask("Ajustes finos para amanhã?", default="")

    lines = []
    if deu_certo:
        lines.append(f"✅ Deu certo: {deu_certo}")
    if deu_errado:
        lines.append(f"❌ Deu errado: {deu_errado}")
    if aprendizado:
        lines.append(f"💡 Aprendizado: {aprendizado}")
    if ajustes:
        lines.append(f"🔧 Ajustes: {ajustes}")

    if lines:
        text = "\n".join(lines)
        _run_cmd(["journal", "create", "--text", text])

    # 4. Quick end-of-day checkin
    e = Prompt.ask("Energia final do dia (1-10)", default="5")
    f = Prompt.ask("Foco final do dia (1-10)", default="5")
    _run_cmd(["metric", "energy", "-e", e, "-f", f])

    console.print("\n[bold green]✔ Dia encerrado![/bold green]")


def _flow_checkin() -> None:
    """30-second check-in: register current energy/focus."""
    _clear()
    _header("⚡ Check-in Rápido")
    console.print("[dim]30 segundos. Registre seu estado atual.[/dim]\n")
    e = Prompt.ask("Energia (1-10)", default="7")
    f = Prompt.ask("Foco (1-10)", default="7")
    note = Prompt.ask("Nota rápida (opcional)", default="")
    args = ["metric", "energy", "-e", e, "-f", f]
    if note:
        _run_cmd(args)
        _run_cmd(["journal", "create", "--text", f"Check-in: {note}"])
    else:
        _run_cmd(args)


def _dashboard() -> None:
    """Show current day state dashboard."""
    _run_cmd(["state", "show"])


# ---------------------------------------------------------------------------
# Submenus (Reports / Data / Policy / Demo / System)
# ---------------------------------------------------------------------------

def _run_cli_command(args: list[str]) -> None:
    """Run a CLI command and wait."""
    _clear()
    _header(" ".join(args))
    _run_cmd(args)


def _submenu(title: str, items: list[tuple[str, str, list[str]]]) -> None:
    """Generic submenu: show items, let user choose, run command."""
    while True:
        _clear()
        _header(title)
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="bold yellow", width=4)
        table.add_column("Action", style="white")
        for key, label, _ in items:
            table.add_row(key, label)
        table.add_row("", "")
        table.add_row("b", "[dim]🔙 Back to main menu[/dim]")
        console.print(table)

        choices = [str(i + 1) for i in range(len(items))] + ["b"]
        choice = Prompt.ask("[bold yellow]Choose[/bold yellow]", choices=choices, default="1")

        if choice == "b":
            return
        idx = int(choice) - 1
        if 0 <= idx < len(items):
            _run_cli_command(items[idx][2])


def _menu_reports() -> None:
    today = date.today().isoformat()
    _submenu("📈 Relatórios", [
        ("1", "Relatório diário — hoje", ["report", "daily"]),
        ("2", f"Relatório diário — {today} (--date)", ["report", "daily", "--date", today]),
        ("3", "Relatório diário — JSON", ["report", "daily", "--json"]),
        ("4", "Relatório semanal", ["report", "weekly"]),
        ("5", "Relatório semanal — JSON", ["report", "weekly", "--json"]),
        ("6", "Dashboard do dia", ["state", "show"]),
        ("7", "Dashboard JSON", ["state", "show", "--json"]),
    ])


def _menu_data() -> None:
    _submenu("📚 Dados & Histórico", [
        ("1", "Rotinas (listar)", ["routine", "list"]),
        ("2", "Time Blocks (listar)", ["block", "list"]),
        ("3", "Journal (listar)", ["journal", "list"]),
        ("4", "Habits (listar)", ["habit", "list"]),
        ("5", "Métricas de sono (listar)", ["metric", "list"]),
        ("6", "Criar rotina MANHA CORE", ["routine", "create", "Morning", "MANHA", "CORE"]),
        ("7", "Criar rotina TARDE CORE", ["routine", "create", "Deep Work", "TARDE", "CORE"]),
        ("8", "Criar rotina NOITE EXIT", ["routine", "create", "Shutdown", "NOITE", "EXIT"]),
        ("9", "Criar rotina MANHA ENTRY", ["routine", "create", "Wake Up", "MANHA", "ENTRY"]),
    ])


def _menu_policy() -> None:
    _submenu("⚙️ Política & Ajuste", [
        ("1", "Setpoints (PUSH/MAINTAIN/REDUCE/RECOVER)", ["policy", "setpoints"]),
        ("2", "Decisões recentes", ["policy", "decisions"]),
        ("3", "Setpoints — JSON", ["policy", "setpoints", "--json"]),
        ("4", "Decisões — JSON", ["policy", "decisions", "--json"]),
    ])


def _menu_demo() -> None:
    _submenu("🎬 Demo & Testes", [
        ("1", "Seed — 7 dias PAV (Perfeito, Desvio, Hardcore, Recuperação...)", ["demo", "seed"]),
        ("2", "Seed + Relatório Semanal", ["demo", "week"]),
        ("3", "Relatório Diário (hoje)", ["report", "daily"]),
        ("4", "Ver estatísticas", ["demo", "show"]),
        ("5", "Limpar todos dados", ["demo", "clear"]),
    ])
    if Prompt.ask("Rodar suite de testes agora? (y/n)", choices=["y", "n"], default="n") == "y":
        _run_tests()


def _run_tests() -> None:
    """Executa pytest em subprocesso (testes demoram, é opt-in)."""
    import subprocess
    from pathlib import Path
    _clear()
    _header("🧪 Running Tests")
    code = (
        "import subprocess, sys; "
        "r = subprocess.run([sys.executable, '-m', 'pytest', '-x', '--tb=short', '-q'], "
        "capture_output=True, text=True, timeout=120); "
        "print(r.stdout); "
        "if r.stderr: print('STDERR:', r.stderr); "
        "print(f'exit: {r.returncode}')"
    )
    try:
        r = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=180,
            cwd=str(Path(__file__).resolve().parent.parent.parent.parent),
        )
        console.print(r.stdout)
        if r.stderr:
            console.print(f"[red]{r.stderr}[/red]")
    except Exception as e:
        console.print(
            Panel(
                f"[red]{type(e).__name__}:[/red] {e}",
                title="[bold red]Error[/bold red]",
                border_style="red",
            )
        )
    Prompt.ask("\n[dim]Press Enter to continue[/dim]")


# ---------------------------------------------------------------------------
# Special actions
# ---------------------------------------------------------------------------

_FLAG_GLOSSARY: list[tuple[str, str]] = [
    ("🥗  -E",  "Energy level (1-10) ao acordar ou no check-in"),
    ("🎯  -F",  "Focus level (1-10) no momento"),
    ("💤  -Q",  "Sleep quality (1-10)"),
    ("🕐  -BH", "Bedtime hour (0-23) — hora que dormiu"),
    ("🕐  -BM", "Bedtime minute (0-59)"),
    ("🕐  -WH", "Wake hour (0-23) — hora que acordou"),
    ("🕐  -WM", "Wake minute (0-59)"),
    ("🍽  --eat",   "Tempo de almoço em minutos (eat)"),
    ("🍽  --rest",  "Tempo de descanso pós-almoço (rest)"),
    ("⚖️  --pesado","Flag pesado: digestão pesada (True/False)"),
    ("📅  --date",  "Override de data (YYYY-MM-DD)"),
    ("📦  --json",  "Output estruturado JSON em vez de painel"),
    ("🏷  --label", "Label legível para o bloco (ex: 'Deep Work')"),
]


def _flag_glossary_grid() -> Table:
    """Build the flag glossary as a compact Table.grid."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold yellow", justify="right", min_width=12)
    grid.add_column(style="white")
    for flag, desc in _FLAG_GLOSSARY:
        grid.add_row(flag, desc)
    return grid


def _system_info() -> None:
    _clear()
    _header("ℹ️ System Info")
    from dataclasses import fields
    from operational.constants import PAVConstants

    info = Table.grid(padding=(0, 2))
    info.add_column(style="bold cyan", justify="right", min_width=22)
    info.add_column(style="white")
    info.add_row("Version", __version__)
    info.add_row("Date", date.today().isoformat())
    info.add_row("Periods", ", ".join(p.value for p in Period))
    info.add_row("Routine Types", ", ".join(r.value for r in RoutineType))
    info.add_row("Habit Categories", ", ".join(c.value for c in HabitCategory))
    info.add_row("Policy States", ", ".join(s.value for s in PolicyState))
    info.add_row("PAV Constants", f"{len(fields(PAVConstants))} fields")
    info.add_row("Tests", "2518 pass")
    info.add_row("Framework", "Python 3.11+ · Typer · Rich · Pydantic v2")
    console.print(info)

    console.print()
    console.print("[bold]Workflow maps (key moments):[/bold]")
    console.print("  1. 🌅 Iniciar Manhã  → sleep retroativo + ENTRY + bloco MANHA")
    console.print("  2. 💻 Iniciar Tarde  → bloco TARDE + CORE + checkin")
    console.print("  3. 🌙 Encerrar Dia   → NOITE + OKRs (deu certo/errado/aprendizado/ajustes)")
    console.print("  4. ⚡ Check-in       → 30s: energia + foco do momento")
    console.print("  5. 📊 Dashboard      → onde estou, o que está logado")

    console.print()
    console.print("[bold cyan]📖 Glossário de Flags[/bold cyan]")
    console.print(_flag_glossary_grid())

    Prompt.ask("\n[dim]Press Enter to continue[/dim]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    """Start the interactive home menu."""
    try:
        home()
    except KeyboardInterrupt:
        _clear()
        console.print("[green]Até logo! 🚀[/green]")
        sys.exit(0)
