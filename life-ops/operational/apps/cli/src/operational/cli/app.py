"""Main Typer application for the operational CLI.

Usage:
    operational --help           # See all commands
    operational home             # Interactive menu (PAV-OS v2)
    operational routine create "Morning run" MANHA CORE
    operational block create TARDE --label "Deep work"
    operational journal create --date 2026-06-07 --text "Good day"
    operational habit create "Drink water" physiological
    operational metric sleep --quality 9
    operational report daily --date 2026-06-07

Logging / Telemetry:
    --verbose       Enable TRACE-level logging on stderr
    --json-log      Output all logs as structured JSON on stderr
    --log-file <p>  Append all logs to <p> (rotating text file)
"""

from __future__ import annotations

import asyncio

import typer

from operational.cli.commands.block_cmd import app as block_app
from operational.cli.commands.demo_cmd import app as demo_app
from operational.cli.commands.doctor_cmd import run_health_check
from operational.cli.commands.habit_cmd import app as habit_app
from operational.cli.commands.journal_cmd import app as journal_app
from operational.cli.commands.lunch_cmd import app as lunch_app
from operational.cli.commands.analytics_cmd import analytics_app as analytics_app
from operational.cli.commands.metric_cmd import app as metric_app
from operational.cli.commands.plan_cmd import app as plan_app
from operational.cli.commands.policy_cmd import app as policy_app
from operational.cli.commands.reflect_cmd import app as reflect_app
from operational.cli.commands.report_cmd import app as report_app
from operational.cli.commands.routine_cmd import app as routine_app
from operational.cli.commands.state_cmd import app as state_app
from operational.cli.commands.sync_cmd import app as sync_app
from operational.cli.telemetry import Level, configure
from operational.tui.app import PAVApp

__all__ = ["app"]

app = typer.Typer(
    name="pav-os",
    help="◆ PAV-OS v2 — production-grade visual. Cybernetic Life OS — Target. Sense. Adjust.",
    no_args_is_help=True,
)

# Global telemetry / debug flags — applied before any command runs.
# These are registered on a CallbackDefinition so Typer processes them
# before dispatching to sub-commands.
@app.callback()
def global_options(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable TRACE-level structured logging on stderr.",
    ),
    json_log: bool = typer.Option(
        False,
        "--json-log",
        help="Output all telemetry as structured JSON on stderr (machine-readable).",
    ),
    log_file: str | None = typer.Option(
        None,
        "--log-file",
        help="Append all telemetry logs to this file (path is created if needed).",
    ),
) -> None:
    """Global options for all PAV commands — telemetry, debugging."""
    if ctx.resilient_parsing:
        return
    level = Level.TRACE if verbose else Level.INFO
    configure(
        level=level,
        json_log=json_log,
        log_file=log_file,
        quiet=False,
    )

app.add_typer(routine_app, name="routine", help="Gerenciar rotinas (MANHA/TARDE/NOITE).")
app.add_typer(block_app, name="block", help="Gerenciar blocos de tempo.")
app.add_typer(journal_app, name="journal", help="Gerenciar entradas do diário.")
app.add_typer(habit_app, name="habit", help="Gerenciar hábitos com Q_HE.")
app.add_typer(metric_app, name="metric", help="Registrar métricas (sono, energia).")
app.add_typer(
    policy_app,
    name="policy",
    help="Gerenciar setpoints e decisões PUSH/MAINTAIN/REDUCE/RECOVER.",
)
app.add_typer(demo_app, name="demo", help="Gerenciar dados de demonstração (seed/clear/show).")
app.add_typer(
    report_app,
    name="report",
    help="Gerar relatórios diário/semanal (PAV-OS v2 design system).",
)
app.add_typer(state_app, name="state", help="Dashboard do dia corrente (PAV-OS v2 design system).")
app.add_typer(reflect_app, name="reflect", help="OKRs — reflexão de entrada/saída.")
app.add_typer(lunch_app, name="lunch", help="Registrar almoço (eat + rest + flag pesado).")
app.add_typer(
    analytics_app,
    name="analytics",
    help="Analytics e data storytelling — 180 dias de dados.",
)
app.add_typer(
    sync_app,
    name="sync",
    help="Sync vault period reports with vibe_ops.db.",
)
app.add_typer(
    plan_app,
    name="plan",
    help="Strategic planning via PAE-Maintainer agent (NEW subcommand for T11).",
)


@app.command(name="doctor")
def doctor_root(
    json_out: bool = typer.Option(False, "--json", help="Output as JSON"),  # noqa: FBT001, FBT003
) -> None:
    """Run a comprehensive health check on the operational CLI."""
    run_health_check(json_out=json_out)


@app.command()
def home() -> None:
    """Menu interativo — PAV-OS v2 menu (definitive edition)."""
    from operational.cli.home_v2 import run as run_home_v2  # noqa: PLC0415

    run_home_v2()


@app.command()
def tui(
    screen: str | None = typer.Option(
        None,
        "--screen",
        "-s",
        help=(
            "Jump directly to screen: "
            "dashboard | daily_flow | pomodoro_timer | "
            "habits | metrics | policy | journal | analytics"
        ),
    ),
    data_file: str | None = typer.Option(
        None,
        "--data-file",
        help="Path to CSV data file for metrics (default: built-in sample data)",
    ),
    golden: bool = typer.Option(  # noqa: FBT001
        False,  # noqa: FBT003
        "--golden",
        help="Load golden dataset for visual debugging (7 canonical PAV days)",
    ),
    synthetic: bool = typer.Option(  # noqa: FBT001
        False,  # noqa: FBT003
        "--synthetic",
        help="Load synthetic dataset (30+ days with edge cases)",
    ),
    debug: bool = typer.Option(  # noqa: FBT001
        False,  # noqa: FBT003
        "--debug",
        help="Enable Textual dev mode with live reload and exception traceback",
    ),
) -> None:
    """Launch the PAV TUI (Textual-based 8-screen terminal UI).

    Screens: dashboard | daily_flow | pomodoro_timer | habits | metrics | policy | journal | analytics
    Keys: 1-8 switch screens | q quit | Ctrl+C interrupt

    Data: by default the TUI reads from ~/.time-tasker/*.json (empty on first run).
    Use --golden or --synthetic to populate it with mock data so screens render.
    Use ``operational demo seed`` to load the rich 7-scenario mock dataset from Python.
    Use ``operational demo dataset golden`` to see the CSV-based golden dataset.
    """
    tui_app = PAVApp(
        initial_screen=screen,
        data_file=data_file,
        golden=golden,
        synthetic=synthetic,
    )

    if debug:
        tui_app._devtools = True  # noqa: SLF001

    asyncio.run(tui_app.run_async())


if __name__ == "__main__":
    app()
