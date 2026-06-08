# 05 — Home Menu

> The home menu is the **primary interface** of the `operational` CLI. It is a numbered text menu — not a TUI library, not `textual`, not a full-screen app. It is a `while True:` loop that prints a Rich `Table` and uses `rich.prompt.Prompt.ask()` to dispatch. The menu is organized around the **human workflow** (start morning, start afternoon, end day, check-in) rather than the underlying CRUD operations on entities. This makes it the right place to land when the user opens the CLI, not the wrong place to escape from.

## `MENU_ITEMS` — the 10 options + `q`

**Defined in:** `cli/home.py:33-46`.

```python
# cli/home.py:33-46
MENU_ITEMS: list[tuple[str, str, str]] = [
    ("1",  "🌅  Iniciar Manhã",     "Acordou → sleep retroativo → ENTRY → workout"),
    ("2",  "💻  Iniciar Tarde",     "Almoço → pomodoros → foco principal"),
    ("3",  "🌙  Encerrar Dia",       "Jantar → shutdown → reflexão (OKRs)"),
    ("4",  "⚡  Check-in Rápido",    "30s: registrar energia/foco do momento"),
    ("5",  "📊  Dashboard do Dia",   "Onde estou · o que está logado · estou no plano?"),
    ("",   "",                      ""),
    ("6",  "📈  Relatórios",         "Diário · Semanal · Estado consolidado"),
    ("7",  "📚  Dados & Histórico", "Rotinas · Blocos · Journal · Habits · Métricas"),
    ("8",  "⚙️   Política & Ajuste", "Setpoints PUSH/MAINTAIN/REDUCE/RECOVER · Decisões"),
    ("9",  "🎬  Demo & Testes",      "Seed 7 dias PAV · Limpar · Show · Run tests"),
    ("10", "ℹ️   Sistema",          "Versão · Constantes · Tipos · Categorias"),
    ("q",  "🚪  Sair",               "Exit"),
]
```

The list is a 3-tuple of `(key, action, description)`. The empty row at index 5 is a visual separator that the renderer preserves (`_show_menu` at `home.py:118-131` adds a blank row when the key is empty).

## The menu UI

The menu is rendered by `_show_menu` (`home.py:118-131`) as a Rich `Table` with three columns:

```python
table = Table(show_header=False, box=None, padding=(0, 2))
table.add_column("Key", style="bold yellow", width=4)
table.add_column("Action", style="white", width=28)
table.add_column("Description", style="dim")
```

**Visual mockup:**

```text
╭─────────────────────────────────────────────────────────────────────╮
│  ⚡ TIME-TASKER  v0.1.0  |  2026-06-08                              │
╰─────────────────────────────────────────────────────────────────────╯
Key  Action                       Description
─────────────────────────────────────────────────────────────────────
1    🌅  Iniciar Manhã             Acordou → sleep retroativo → ENTRY → workout
2    💻  Iniciar Tarde             Almoço → pomodoros → foco principal
3    🌙  Encerrar Dia              Jantar → shutdown → reflexão (OKRs)
4    ⚡  Check-in Rápido           30s: registrar energia/foco do momento
5    📊  Dashboard do Dia          Onde estou · o que está logado · estou no plano?

6    📈  Relatórios                Diário · Semanal · Estado consolidado
7    📚  Dados & Histórico         Rotinas · Blocos · Journal · Habits · Métricas
8    ⚙️   Política & Ajuste        Setpoints PUSH/MAINTAIN/REDUCE/RECOVER · Decisões
9    🎬  Demo & Testes             Seed 7 dias PAV · Limpar · Show · Run tests
10   ℹ️   Sistema                  Versão · Constantes · Tipos · Categorias
q    🚪  Sair                      Exit
```

## Workflow grouping

Options are grouped by **moment in the day**, not by entity:

| Range | Group | Purpose |
|-------|-------|---------|
| 1-4 | Workflow flows | The four "key moments" — start morning, start afternoon, end day, check-in. Multi-step flows that compose several commands. |
| 5 | Dashboard | Quick read of current state — "where am I, what is logged, am I on plan?" |
| 6-9 | Submenus | Drill into reports, data, policy, demo data |
| 10 | System | Static reference info — version, constants, types, categories |
| `q` | Quit | Exit the CLI |

Each option dispatches via the `_route` dict (`home.py:136-147`):

```python
routes = {
    "1":  _flow_morning,
    "2":  _flow_afternoon,
    "3":  _flow_evening,
    "4":  _flow_checkin,
    "5":  _dashboard,
    "6":  _menu_reports,
    "7":  _menu_data,
    "8":  _menu_policy,
    "9":  _menu_demo,
    "10": _system_info,
}
```

The handler functions for 1-5 are *workflow flows* — they run a sequence of prompts and Typer commands. The handlers for 6-9 are *submenus* (implemented by the generic `_submenu` function at `home.py:297-318`). Option 10 is a static info dump. `q` triggers `sys.exit(0)`.

## Selection mechanism

`home()` at `home.py:100-115` is the main loop:

```python
choice = Prompt.ask(
    "[bold yellow]Choose[/bold yellow]",
    choices=[str(i) for i in range(1, 11)] + ["q"],
    default="5",
)
```

`Prompt.ask` with `choices=...` re-prompts on invalid input (Rich handles the loop). The `default="5"` means pressing Enter opens the dashboard. This is the deliberate "press Enter to see where you are" UX.

`Prompt.ask` reads a single line and trims whitespace. It is **synchronous** — there are no async prompts in this CLI (see `06-INTERACTIVITY.md`).

## How dispatch works — `_run_cmd(args)`

`_run_cmd` at `home.py:49-67` is the orchestrator. It runs a Typer command **in-process** and re-prints its output through the home console:

```python
def _run_cmd(args: list[str]) -> None:
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
```

Key points:

- **`typer_app(args=args, standalone_mode=False)`** — runs the Typer app with the given argv, in the **same Python process**. `standalone_mode=False` prevents Typer from calling `sys.exit()` on completion (which would kill the menu loop).
- **`contextlib.redirect_stdout(out)`** — captures everything written to `sys.stdout` during the command. This is the *only* reason ANSI codes can leak (some renderers use `force_terminal=True`); see the next section.
- **`strip_ansi`** — defensive cleanup of any escape codes that leaked.
- **`console.print(text)`** — re-emits the cleaned output through the singleton console (which honors `is_captured()` *correctly* because the home loop is itself running under a real TTY).
- **`Prompt.ask("\n[dim]Press Enter to continue[/dim]")`** — pauses before returning to the menu. This is the "Voltar" mechanism.

## The `redirect_stdout` trick

Why capture-and-reprint instead of just letting the command print directly?

When the home menu's `console` has `is_captured() = False` (real TTY) but an inner command's renderer builds a **new** `Console(force_terminal=True)` (as `cli/renderers.py:make_console` does), the inner console emits ANSI escape codes that the *outer* console's `print()` would render as literal text. The captured buffer holds the raw bytes; the outer console is the one trusted to render them.

The trick is:

1. Capture everything written to `sys.stdout` during the inner command into a `StringIO`.
2. Strip ANSI codes with `strip_ansi`.
3. Re-print the cleaned text via the singleton `console.print(text)`.

This is robust even if every inner command uses a different `Console` constructor — the home loop normalizes the output before showing it.

## Adding a new menu item

1. **Add to `MENU_ITEMS`** (`home.py:33-46`). Pick a key that does not collide (1-9, 10 for 2-digit, then add 11, 12 if you really need to; the `default="5"` UX assumes 1-9 + `q`).
2. **Add a handler function** above `_route` (or for a submenu, add the items to the relevant `_menu_*` function).
3. **Register in `_route`** (`home.py:136-147`).
4. **Update `choices` in `home()`** (`home.py:108`) — if you add `11`, add `"11"` to the list.
5. **If it is a multi-step flow**, follow the `_flow_morning` pattern (`home.py:157-188`): clear screen, show header, show preview, ask "Continuar?", then run a sequence of `_run_cmd` calls.
6. **If it is a single command**, just `_run_cmd(["your", "args"])`.

Keep the handler functions **short** — 30-50 lines each. If a handler is getting long, extract a `_flow_*` helper.

## The "Voltar" mechanism

After every `_run_cmd`, the function calls `Prompt.ask("\n[dim]Press Enter to continue[/dim]")` (line 76). This blocks until the user presses Enter, then the outer `while True:` loop in `home()` iterates, calls `_clear()` and `_header()`, and shows the menu again.

For submenus, the "Voltar" mechanism is different. Each `_menu_*` function calls the generic `_submenu` helper (`home.py:297-318`), which appends a `b 🔙 Back to main menu` row and uses `choices=[..., "b"]`. If the user picks `b`, `_submenu` returns; the outer `_menu_*` function returns; the main `home()` loop iterates.

There is no way to "go back" mid-flow. The four workflow flows (1-4) are atomic — once you start, you either complete or `KeyboardInterrupt` out. This is deliberate: a half-finished morning flow leaves the state in an inconsistent place.
