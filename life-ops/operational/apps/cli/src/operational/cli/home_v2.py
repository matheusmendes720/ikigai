"""V2 Home Menu — categorized, production-grade.

The PAV-OS v2 home menu (definitive edition). Uses ``big_panel`` and
``two_column_grid`` to render the 5 themed sections (FLUXO,
DASHBOARD, DADOS, SISTEMA) in the canonical wireframe from
``docs/design-system/DESIGN_SYSTEM.md``.

Visual layout:
- Header (PAV-OS logo + version + regime)
- 3 category boxes (2 columns): FLUXO + DASHBOARD
- 1 wide category box: DADOS & SISTEMA
- Action footer with prompt
"""

from __future__ import annotations

import io
import subprocess
import sys
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path

from rich.box import DOUBLE
from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from operational import __version__
from operational.cli.app import app as typer_app
from operational.cli.console import CONSOLE_WIDTH, console
from operational.cli.services import get_day_snapshot
from operational.cli.state import day_contexts
from operational.ui import strip_ansi
from operational.ui.tokens import SEVERITY, STYLES

__all__ = ["MENU_GROUPS", "run"]

# Resolve the package root so subprocesses can be invoked with the correct
# --directory argument. This file lives at:
#   <root>/apps/cli/src/operational/cli/home_v2.py
# so the project root (where pyproject.toml lives) is 4 parents up from
# __file__, but we walk upwards to be robust to install layouts.
_THIS_FILE = Path(__file__).resolve()
ROOT = next(
    (p for p in [_THIS_FILE.parent, *_THIS_FILE.parents] if (p / "pyproject.toml").is_file()),
    _THIS_FILE.parents[3],
)


# Menu groups: each entry is (group_key, panel_title, panel_icon, severity, items)
# items = list of (key, label_with_icon, subtitle, command)
MENU_GROUPS: list[dict] = [
    {
        "key": "FLUXO",
        "title": "EXECUÇÃO DIÁRIA (Flow)",
        "icon": "🚀",
        "severity": "primary",
        "items": [
            ("1", "🌅 Iniciar Manhã", "Sleep → ENTRY → workout", ["routine", "list"]),
            ("2", "💻 Iniciar Tarde", "Almoço → pomodoros → foco", ["block", "list"]),
            ("3", "🌙 Encerrar Dia", "Shutdown → reflexão (OKRs)", ["reflect", "saida"]),
            ("4", "⚡ Check-in Rápido", "30s · energia/foco", ["state", "show"]),
        ],
    },
    {
        "key": "DASHBOARD",
        "title": "INSIGHTS & DADOS",
        "icon": "🧠",
        "severity": "info",
        "items": [
            ("5", "📊 Dashboard do Dia", "Onde estou · o que está logado", ["state", "show"]),
            ("6", "📈 Relatórios", "Diário · Semanal · Estado", None),
            ("7", "📚 Dados & Histórico", "Rotinas · Blocos · Journal", ["routine", "list"]),
        ],
    },
    {
        "key": "DADOS",
        "title": "SISTEMA & CONFIGURAÇÕES",
        "icon": "⚙️",
        "severity": "accent",
        "items": [
            ("8", "⚙️ Política & Ajuste", "PUSH/MAINTAIN/REDUCE/RECOVER", ["policy", "decisions"]),
            ("9", "🎬 Demo & Testes", "Seed 7 dias · Limpar · Show", ["demo", "show"]),
            ("10", "🔍 Sistema", "Versão · Constantes · Tipos", ["doctor"]),
        ],
    },
]


def _make_today_snapshot_renderable() -> Text | Table:
    """Today's snapshot as a renderable.

    If no data for today, finds the most recent day with data.
    """
    target_date = datetime.now(UTC).date()
    ctx_list = day_contexts.list()
    if ctx_list and not any(c.date == target_date for c in ctx_list):
        target_date = max(c.date for c in ctx_list)

    try:
        snap = get_day_snapshot(target_date)
    except Exception:  # noqa: BLE001
        return Text("  (snapshot indisponivel — rode 'demo seed')", style=SEVERITY["muted"])

    sleep_dur = snap.sleep.duration_hours
    sleep_str = f"{sleep_dur:.1f}h" if sleep_dur is not None else "—"
    pomo_str = f"{snap.n_pomodoros}/{snap.pomodoros_meta}" if snap.pomodoros_meta else "—"

    today = datetime.now(UTC).date()
    date_label = "Hoje:" if target_date == today else f"Último ({target_date.isoformat()}):"
    t = Table.grid(expand=False, padding=(0, 3))
    t.add_column(justify="left", style="bold cyan")
    t.add_column(justify="left")
    t.add_column(justify="left", style="bold cyan")
    t.add_column(justify="left")
    t.add_column(justify="left", style="bold cyan")
    t.add_column(justify="left")
    t.add_row(
        date_label,
        target_date.isoformat(),
        "Sono:",
        sleep_str,
        "Pomodoros:",
        pomo_str,
    )
    return t


def _make_category_panel(group: dict, width: int = 58) -> Panel:
    """Render a single category as a panel with menu items inside."""
    sev = SEVERITY.get(group["severity"], SEVERITY["primary"])
    lines: list = []
    for key, label, sub, _cmd in group["items"]:
        line = Text()
        line.append(f"  [{key}] ", style=f"bold {sev}")
        line.append(label, style="white")
        line.append("  ·  ", style=SEVERITY["muted"])
        line.append(sub, style=SEVERITY["muted"])
        lines.append(line)
    body = Group(*lines)
    return Panel(
        body,
        title=f"[{sev}] {group['icon']} {group['title']} [/]",
        border_style=sev,
        padding=(0, 1),
        width=width,
    )


def _make_dispatch_table() -> dict[str, list[str]]:
    """Map menu keys to typer command invocations."""
    return {key: cmd for g in MENU_GROUPS for key, _l, _s, cmd in g["items"]}


# Subcommands that write/prompt and need direct TTY access.
# Running these in-process with redirect_stdout suppresses Rich's Prompt.ask.
_INTERACTIVE_COMMANDS = frozenset(
    [
        ("reflect", "entrada"),
        ("reflect", "saida"),
        ("journal", "create"),
        ("routine", "create"),
        ("block", "create"),
        ("metric", "energy"),
        ("metric", "sleep"),
    ]
)


def _is_interactive(args: list[str]) -> bool:
    """Return True if the command chain involves interactive write/prompt subcommands."""
    it = iter(args)
    prev = next(it, None)
    for curr in it:
        if (prev, curr) in _INTERACTIVE_COMMANDS:
            return True
        prev = curr
    return False


def _run_cmd(args: list[str]) -> None:
    """Run a CLI command — interactive commands get a real TTY via subprocess."""
    # Deduplicate consecutive repeated command names (e.g. ["doctor", "doctor"]).
    # Typer would otherwise try to pass the duplicate as a named argument.
    deduped: list[str] = []
    for a in args:
        if not (deduped and deduped[-1] == a):
            deduped.append(a)
    args = deduped

    if _is_interactive(args):
        # Interactive command: delegate to subprocess so Prompt.ask works normally.
        # Two strategies — try uv first (matches dev workflow), fall back to
        # the current interpreter if uv is not installed (e.g. production user).
        strategies: list[list[str]] = [
            ["uv", "run", "--directory", str(ROOT), "pav", *args],
            [sys.executable, "-m", "operational.cli", *args],
        ]
        last_err: Exception | None = None
        for cmd in strategies:
            try:
                result = subprocess.run(cmd, check=False)  # noqa: S603
                if result.returncode == 0:
                    return
                last_err = RuntimeError(f"exit code {result.returncode}")
            except FileNotFoundError as e:
                last_err = e
                continue
            except Exception as e:  # noqa: BLE001
                last_err = e
                break
        console.print(
            f"[red]Error running {args[0]} {args[1] if len(args) > 1 else ''}: {last_err}[/red]"
        )
        return

    # Read-only/list command: capture and render output in-process.
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            typer_app(args=args, standalone_mode=False)
    except SystemExit:
        pass
    except Exception as e:  # noqa: BLE001
        out.write(f"Error: {e}\n")
    text = out.getvalue()
    text = strip_ansi(text)
    if text.strip():
        console.print(text, end="")


def _prompt() -> str:
    """Prompt the user for a menu choice."""
    return Prompt.ask(
        "[bold cyan]>[/] [bold white]Escolha uma opção[/] [grey58][1-10, q][/]",
        choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "q"],
        default="5",
        show_default=False,
    )


def _make_header() -> Panel:
    """Render the production-grade header bar."""
    line = Text()
    line.append("  ⚡ ", style="bold cyan")
    line.append("PAV-OS", style="bold white on dodger_blue1")
    line.append(" · Cybernetic Life OS", style="white")
    line.append("    ", style="default")
    line.append(f"v{__version__}", style=SEVERITY["muted"])
    line.append("    ", style="default")
    line.append("|", style=SEVERITY["muted"])
    line.append(f"  {datetime.now(UTC).date().isoformat()}", style=STYLES["mono"])
    line.append("    ", style="default")
    line.append("|", style=SEVERITY["muted"])
    line.append("  🏠 MAIN MENU", style="bold white")
    return Panel(
        line,
        border_style=SEVERITY["primary"],
        box=DOUBLE,
        padding=(0, 1),
    )


def _make_footer_prompt() -> Panel:
    """Render the bottom action footer with the menu prompt."""
    return Panel(
        Text("  [q] 🚪 Sair do Terminal", style=STYLES["body_muted"]),
        border_style=SEVERITY["muted"],
        box=DOUBLE,
        padding=(0, 1),
    )


def _reports_submenu() -> None:
    """Show reports submenu and dispatch to the chosen report type."""
    console.print()
    header = Text()
    header.append("  📈 ", style="bold cyan")
    header.append("RELATÓRIOS", style="bold white")
    header.append("  ·  ", style="muted")
    header.append("Diário · Semanal · Estado", style="muted")
    header_panel = Panel(
        header,
        border_style=SEVERITY["info"],
        box=DOUBLE,
        padding=(0, 1),
        width=CONSOLE_WIDTH - 2,
    )
    console.print(header_panel)
    console.print()

    options = Text()
    options.append("  [D]  📅  Relatório Diário", style="bold white")
    options.append("   —   Resumo do dia com métricas e insights\n", style="muted")
    options.append("  [S]  📊  Relatório Semanal", style="bold white")
    options.append("   —   Vista dos últimos 7 dias\n", style="muted")
    options.append("  [E]  📌  Estado do Sistema", style="bold white")
    options.append("   —   Q_HE, regime, política atual\n", style="muted")
    options.append("  [V]  🔙  Voltar ao Menu", style=SEVERITY["muted"])
    options.append("   —   Menu principal", style="muted")

    panel = Panel(
        options,
        border_style=SEVERITY["info"],
        box=DOUBLE,
        padding=(1, 2),
        width=CONSOLE_WIDTH - 2,
    )
    console.print(panel)
    console.print()

    choice = Prompt.ask(
        "[bold cyan]>[/] [bold white]Escolha[/] [grey58][D/S/E/V][/]",
        choices=["d", "s", "e", "v"],
        default="v",
        show_default=False,
    )

    if choice == "d":
        _run_cmd(["report", "daily"])
    elif choice == "s":
        _run_cmd(["report", "weekly"])
    elif choice == "e":
        _run_cmd(["state", "show"])
    console.print()


def run() -> None:
    """Run the v2 home menu — production-grade categorized boxes."""
    while True:
        console.print(_make_header())
        console.print()

        console.print(_make_today_snapshot_renderable())
        console.print()

        fluxo_panel = _make_category_panel(MENU_GROUPS[0])
        dash_panel = _make_category_panel(MENU_GROUPS[1])
        console.print(Columns([fluxo_panel, dash_panel], equal=True, expand=True))
        console.print()

        dados_panel = _make_category_panel(MENU_GROUPS[2], width=CONSOLE_WIDTH - 2)
        console.print(dados_panel)
        console.print()

        console.print(_make_footer_prompt())
        console.print()

        choice = _prompt()
        should_quit = _dispatch(choice)
        if should_quit:
            return
        console.print()
        Prompt.ask("[dim]Pressione [Enter] para voltar[/dim]", default="")


def _dispatch(choice: str) -> bool:
    """Dispatch a menu choice to the appropriate command.

    Returns True if the menu should exit (user chose 'q'),
    False otherwise so the loop continues.
    """
    if choice == "q":
        console.print("[bold cyan]Até![/]")
        return True

    if choice == "6":
        _reports_submenu()
        return False

    dispatch_map = _make_dispatch_table()
    args = dispatch_map.get(choice, ["--help"])
    _run_cmd(args)
    return False
