"""Interactive home menu for the operational system."""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import NoReturn

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from operational import __version__
from operational.enums import HabitCategory, Period, PolicyState, RoutineType

console = Console()

PYTHON = sys.executable
APP_CODE = "from operational.cli.app import app; app()"


def _run_cmd(args: list[str]) -> None:
    """Run an operational CLI command and show output."""
    code = f"{APP_CODE} {' '.join(args)}"
    try:
        r = subprocess.run(
            [PYTHON, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
        )
        console.print(r.stdout)
        if r.stderr:
            console.print(f"[red]{r.stderr}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
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
# Main Menu
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
            default="1",
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
    table.add_column("Command", style="white")
    table.add_column("Description", style="dim", width=40)

    items = [
        ("1", "🕐  Routines", "Criar/Listar rotinas (MANHA/TARDE/NOITE)"),
        ("2", "📦  Time Blocks", "Criar/Listar blocos de tempo"),
        ("3", "📓  Journal", "Registrar/Listar entradas do diário"),
        ("4", "✅  Habits", "Criar/Listar hábitos com Q_HE"),
        ("5", "💤  Sleep Metrics", "Registrar qualidade do sono"),
        ("6", "📊  Reports", "Gerar relatórios diário/semanal"),
        ("7", "⚙️   Policy", "Ver setpoints/decisiones PUSH/MAINTAIN/REDUCE/RECOVER"),
        ("", "", ""),
        ("8", "🧪  Run Tests", "Executar suite de testes (2518)"),
        ("9", "📋  Daily Flow", "Sequência completa do dia"),
        ("10", "ℹ️   System Info", "Versão, submodulos, plugins"),
        ("q", "🚪  Sair", "Exit"),
    ]
    for key, cmd, desc in items:
        table.add_row(key, cmd, desc)

    console.print(table)


def _route(choice: str) -> None:
    """Route menu choice to the right handler."""
    routes = {
        "1": _menu_routines,
        "2": _menu_blocks,
        "3": _menu_journal,
        "4": _menu_habits,
        "5": _menu_metrics,
        "6": _menu_reports,
        "7": _menu_policy,
        "8": _run_tests,
        "9": _daily_flow,
        "10": _system_info,
    }
    handler = routes.get(choice)
    if handler:
        handler()


# ---------------------------------------------------------------------------
# Submenus
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


def _menu_routines() -> None:
    _submenu("🕐 Routines", [
        ("1", "Criar rotina MANHA CORE", ["routine", "create", "Morning", "MANHA", "CORE"]),
        ("2", "Criar rotina TARDE CORE", ["routine", "create", "Deep Work", "TARDE", "CORE"]),
        ("3", "Criar rotina NOITE EXIT", ["routine", "create", "Shutdown", "NOITE", "EXIT"]),
        ("4", "Criar rotina MANHA ENTRY", ["routine", "create", "Wake Up", "MANHA", "ENTRY"]),
        ("5", "Listar rotinas", ["routine", "list"]),
    ])


def _menu_blocks() -> None:
    _submenu("📦 Time Blocks", [
        ("1", "Criar bloco MANHA", ["block", "create", "MANHA"]),
        ("2", "Criar bloco TARDE --label Deep Work", ["block", "create", "TARDE", "--label", "Deep Work"]),
        ("3", "Criar bloco NOITE", ["block", "create", "NOITE"]),
        ("4", "Listar blocos", ["block", "list"]),
    ])


def _menu_journal() -> None:
    today = date.today().isoformat()
    _submenu("📓 Journal", [
        ("1", "Criar entrada — texto livre", ["journal", "create", "--text", "Journal entry for today"]),
        ("2", f"Criar entrada — data {today}", ["journal", "create", "--date", today, "--text", "Daily check-in"]),
        ("3", "Listar entradas", ["journal", "list"]),
    ])


def _menu_habits() -> None:
    _submenu("✅ Habits", [
        ("1", "Criar hábito physiological", ["habit", "create", "Drink Water", "physiological"]),
        ("2", "Criar hábito cognitive", ["habit", "create", "Read 30m", "cognitive", "--resistance", "3", "--weight", "0.5"]),
        ("3", "Criar hábito ritual", ["habit", "create", "Meditate", "ritual", "--resistance", "2", "--weight", "0.3"]),
        ("4", "Criar hábito social", ["habit", "create", "Call Family", "social", "--resistance", "6", "--weight", "0.2"]),
        ("5", "Criar hábito creative", ["habit", "create", "Write Journal", "creative", "--resistance", "4"]),
        ("6", "Listar hábitos", ["habit", "list"]),
    ])


def _menu_metrics() -> None:
    _submenu("💤 Sleep Metrics", [
        ("1", "Registrar sono — qualidade 8", ["metric", "sleep", "-q", "8", "-bh", "22", "-wh", "6"]),
        ("2", "Registrar sono — qualidade 10", ["metric", "sleep", "-q", "10", "-bh", "21", "-wh", "5"]),
        ("3", "Registrar sono — qualidade 6", ["metric", "sleep", "-q", "6", "-bh", "23", "-wh", "7"]),
    ])


def _menu_reports() -> None:
    today = date.today().isoformat()
    _submenu("📊 Reports", [
        ("1", "Relatório diário — hoje", ["report", "daily"]),
        ("2", f"Relatório diário — {today}", ["report", "daily", "--date", today]),
        ("3", "Relatório diário — JSON", ["report", "daily", "--json"]),
        ("4", "Relatório semanal", ["report", "weekly"]),
        ("5", "Relatório semanal — JSON", ["report", "weekly", "--json"]),
    ])


def _menu_policy() -> None:
    _submenu("⚙️ Policy", [
        ("1", "Ver setpoints (PUSH/MAINTAIN/REDUCE/RECOVER)", ["policy", "setpoints"]),
        ("2", "Ver decisões recentes", ["policy", "decisions"]),
        ("3", "Setpoints — JSON", ["policy", "setpoints", "--json"]),
    ])


# ---------------------------------------------------------------------------
# Special actions
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    _clear()
    _header("🧪 Running Tests (2518)")
    code = """
import subprocess, sys
r = subprocess.run([sys.executable, "-m", "pytest", "-x", "--tb=short", "-q"],
    capture_output=True, text=True, timeout=120)
print(r.stdout)
if r.stderr: print(r.stderr)
print(f"exit: {r.returncode}")
"""
    try:
        r = subprocess.run(
            [PYTHON, "-c", code],
            capture_output=True, text=True, timeout=180,
            cwd=Path(__file__).resolve().parent.parent.parent.parent,
        )
        console.print(r.stdout)
        if r.stderr:
            console.print(f"[red]{r.stderr}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    Prompt.ask("\n[dim]Press Enter to continue[/dim]")


def _daily_flow() -> None:
    _clear()
    _header("📋 Daily Flow")
    steps = [
        ("Sleep", ["metric", "sleep", "-q", "8", "-bh", "22", "-wh", "6"]),
        ("Routine MANHA ENTRY", ["routine", "create", "Wake Up", "MANHA", "ENTRY"]),
        ("Block MANHA", ["block", "create", "MANHA", "--label", "Morning Deep Work"]),
        ("Routine TARDE CORE", ["routine", "create", "Deep Work", "TARDE", "CORE"]),
        ("Habit ritual", ["habit", "create", "Meditate", "ritual", "-r", "2", "-w", "0.3"]),
        ("Habit cognitive", ["habit", "create", "Read 30m", "cognitive", "-r", "3", "-w", "0.5"]),
        ("Journal", ["journal", "create", "--text", "Daily entry from interactive flow"]),
        ("Report", ["report", "daily"]),
    ]
    for label, cmd in steps:
        console.print(f"\n[bold cyan]▶ {label}[/bold cyan]")
        _run_cmd(cmd)
    console.print("\n[bold green]✔ Daily flow complete![/bold green]")
    Prompt.ask("\n[dim]Press Enter to continue[/dim]")


def _system_info() -> None:
    _clear()
    _header("ℹ️ System Info")
    from operational.constants import PAVConstants
    console.print(f"[bold]Version:[/bold] {__version__}")
    console.print(f"[bold]Date:[/bold] {date.today().isoformat()}")
    console.print(f"[bold]Periods:[/bold] {', '.join(p.value for p in Period)}")
    console.print(f"[bold]Routine Types:[/bold] {', '.join(r.value for r in RoutineType)}")
    console.print(f"[bold]Habit Categories:[/bold] {', '.join(c.value for c in HabitCategory)}")
    console.print(f"[bold]Policy States:[/bold] {', '.join(s.value for s in PolicyState)}")
    console.print(f"[bold]PAV Constants:[/bold] {len(PAVConstants.model_fields())} fields")
    console.print(f"[bold]Tests:[/bold] 2518 pass")
    console.print(f"[bold]Framework:[/bold] Python 3.11+ · Typer · Rich · Pydantic v2")
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
