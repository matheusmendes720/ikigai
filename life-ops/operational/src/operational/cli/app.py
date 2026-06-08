"""Main Typer application for the operational CLI.

Usage:
    operational --help           # See all commands
    operational home             # Interactive menu
    operational routine create "Morning run" MANHA CORE
    operational block create TARDE --label "Deep work"
    operational journal create --date 2026-06-07 --text "Good day"
    operational habit create "Drink water" physiological
    operational metric sleep --quality 9
    operational report daily --date 2026-06-07
"""
from __future__ import annotations

import typer

from operational.cli.commands.block_cmd import app as block_app
from operational.cli.commands.habit_cmd import app as habit_app
from operational.cli.commands.journal_cmd import app as journal_app
from operational.cli.commands.metric_cmd import app as metric_app
from operational.cli.commands.policy_cmd import app as policy_app
from operational.cli.commands.demo_cmd import app as demo_app
from operational.cli.commands.report_cmd import app as report_app
from operational.cli.commands.routine_cmd import app as routine_app
from operational.cli.commands.state_cmd import app as state_app
from operational.cli.commands.reflect_cmd import app as reflect_app
from operational.cli.commands.lunch_cmd import app as lunch_app
from operational.cli.commands.doctor_cmd import app as doctor_app

__all__ = ["app"]

app = typer.Typer(
    name="time-tasker",
    help="⚡ TIME-TASKER — Algorítmica Visual: rotinas, blocos, hábitos, métricas, policy.",
    no_args_is_help=True,
)

app.add_typer(routine_app, name="routine", help="Gerenciar rotinas (MANHA/TARDE/NOITE).")
app.add_typer(block_app, name="block", help="Gerenciar blocos de tempo.")
app.add_typer(journal_app, name="journal", help="Gerenciar entradas do diário.")
app.add_typer(habit_app, name="habit", help="Gerenciar hábitos com Q_HE.")
app.add_typer(metric_app, name="metric", help="Registrar métricas (sono, energia).")
app.add_typer(policy_app, name="policy", help="Gerenciar setpoints e decisões PUSH/MAINTAIN/REDUCE/RECOVER.")
app.add_typer(demo_app, name="demo", help="Gerenciar dados de demonstração (seed/clear/show).")
app.add_typer(report_app, name="report", help="Gerar relatórios diário/semanal.")
app.add_typer(state_app, name="state", help="Dashboard do dia corrente (onde estou, o que está logado).")
app.add_typer(reflect_app, name="reflect", help="OKRs V3 — reflexão de entrada/saída.")
app.add_typer(lunch_app, name="lunch", help="Registrar almoço (eat + rest + flag pesado).")
app.add_typer(doctor_app, name="doctor", help="Diagnóstico completo do ambiente.")


@app.command()
def home() -> None:
    """Menu interativo — interface principal do Time-Tasker."""
    from operational.cli.home import run as run_home
    run_home()
