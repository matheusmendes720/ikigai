# CLI Interface — Typer + Rich

> **Status:** 🟢 Authoritative. Synced with `apps/cli/src/operational/cli/` at time of writing.
> **Related:** `02-COMPONENT-CATALOG.md` (TUI sibling), `tui/03-LAYOUT-GRID-SYSTEM.md`, `DESIGN-SYSTEM.md`.

This document describes the **terminal-CLI** interface of `operational`. It is one of two interfaces — the other is the TUI (see `09-INTERFACE-TUI.md`). Both interfaces share the same underlying `core/` algorithms and `entities/` data model; only the presentation layer differs.

---

## 1. Stack

| Layer | Library | Version | Role |
|---|---|---|---|
| Entry-points | `typer` | ≥ 0.12 | CLI framework, three aliases (`pav`, `pav-os`, `operational`) |
| Layout | `rich` | ≥ 13 | Console, panels, tables, trees, progress |
| Layout | `rich.live` | (Rich built-in) | Spinners + live status |
| Markup | `rich.markup` | (Rich built-in) | `[bold red]…[/]` inline markup |
| Markdown | `rich.markdown` | (Rich built-in) | Report rendering |
| Inputs | `rich.prompt` | (Rich built-in) | `IntPrompt`, `Confirm`, `Prompt` |
| Tables | `rich.table` | (Rich built-in) | Tabular data |
| Trees | `rich.tree` | (Rich built-in) | Indented trees |
| Tracing | `rich.traceback` | (Rich built-in) | Pretty tracebacks |

**No curses, no prompt_toolkit, no click.** Rich alone covers everything — the CLI is a single dependency layer.

## 2. Three entry points, one app

```python
# pyproject.toml [project.scripts]
pav        = "operational.cli.app:app"
pav-os     = "operational.cli.app:app"
operational = "operational.cli.app:app"
```

All three are the same Typer `app`. This means:

- `pav --help` ≡ `pav-os --help` ≡ `operational --help`
- shell completion scripts work for all three
- users pick the one they like

## 3. Subcommand tree

```
pav
├── routine         create | list | show | log
├── block           create | list | show | gap
├── journal         create | list | show | segment
├── habit           create | list | show | streak
├── metric          create | list | show | sleep
├── pomodoro        create | list | show | scenario
├── policy          create | list | show | adjust
├── report          daily | weekly
├── demo            seed | dataset
└── tui             (launches apps/tui via subprocess)

pav home             interactive 10-item menu
pav doctor           environment check + version
pav screen <name>    jump straight to a TUI screen (subprocess)
pav state show       dump all 14 _PersistentRepo as JSON
pav config-show      show resolved config
pav test             pytest entry point (delegates to pytest)
```

12 Typer subcommands, each with 2-4 verbs.

## 4. Command shape

Every command follows the same skeleton (`apps/cli/src/operational/cli/commands/routine.py`):

```python
@app.command()
def create(
    name: str = typer.Argument(..., help="Routine name"),
    period: Period = typer.Option(Period.MANHA, "--period", "-p"),
    type: RoutineType = typer.Option(RoutineType.CORE, "--type", "-t"),
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
) -> None:
    """Create a routine. Wraps the factory; never touches the repo directly."""
    spec = {"name": name, "period": period, "type": type, "created_at": now()}
    routine = factories.make_routine(spec)            # 1. validate
    repo.routines.add(routine)                        # 2. persist
    if json_out:
        print_json(routine)                          # 3. emit
    else:
        receipt_panel(routine)                       # 4. receipt
```

**Three rules every command obeys:**

1. **Never call the repository with raw dicts** — go through `factories.make_*()`.
2. **Always support `--json`** — the same data shape, regardless of formatting.
3. **Always render a receipt** — the user knows success/failure instantly without scrolling.

## 5. The interactive `pav home` menu

`apps/cli/home_v2.py` is a Typer callback that renders a numbered menu and dispatches to subcommands. It exists so non-technical users can drive the CLI without remembering verbs.

```
┌─ operational home ────────────────────────────────────────┐
│ 1  Fluxo    — start/finish a routine / block / lunch      │
│ 2  Dash     — see today's KPIs                             │
│ 3  Dados    — load golden or synthetic                     │
│ 4  Habits   — list + create + streak                       │
│ 5  Journal  — write + segment                              │
│ 6  Metrics  — sleep + others                               │
│ 7  Policy   — see regime + adjust                         │
│ 8  Relatorio — daily / weekly                              │
│ 9  TUI      — launch full screen mode                      │
│ 0  Sair     — exit                                          │
└────────────────────────────────────────────────────────────┘
pick> 1
```

## 6. Rich component library (Layer 2)

`apps/cli/ui/components_v2.py` contains **30+ production-grade widgets**. They are organised by purpose:

| Family | Examples | Doc |
|---|---|---|
| KPI / panel | `kpi_v2`, `big_panel`, `next_step_v2` | `docs/ux/02-componentes/01-kpi-card.md` |
| Layout | `section_panel`, `cartesian_v2`, `regime_bar` | `docs/ux/02-componentes/02-section-panel.md` |
| Progress | `progress_bar`, `pomodoros_v2`, `sparkline` | `docs/ux/02-componentes/07-progress-bar.md` |
| Tables | `kronograma_table`, `metric_table`, `policy_actions_table` | `docs/ux/02-componentes/09-metric-table.md` |
| Feedback | `error_panel_v2`, `success_panel`, `receipt.py` | `docs/ux/02-componentes/04-error-panel.md` |
| Logs | `timeline_log` | `docs/ux/02-componentes/11-timeline-h.md` |

Every widget reads design tokens from `apps/cli/ui/tokens.py` — **never hardcode colours or glyphs** in a widget.

## 7. Output formatters (`apps/cli/formatters/`)

Three output formats, all consuming the same entity:

| Format | Used for | Function |
|---|---|---|
| `json` | `--json` flag, machine consumers | `format_json(entity)` |
| `table` | default for list commands | `format_table(rows, columns)` |
| `panel` | default for show commands | `format_panel(entity)` |
| `receipt` | default for create/update | `receipt.success(entity)` / `failure(err)` |

All four use the same Rich `Console` instance from `console.py` to ensure consistent theming and width.

## 8. State (the JSON-flat path)

`apps/cli/state.py` declares 14 `_PersistentRepo[T]` instances — one per entity — backed by JSON files at `~/.time-tasker/<entity>.json`. These are the "view" of the CLI when you run `pav state show`; the source of truth is SQLite, but the JSON view is human-readable and Git-friendly.

```python
routines     = _PersistentRepo[Routine]   ("~/.time-tasker/routines.json")
blocks       = _PersistentRepo[TimeBlock]  ("~/.time-tasker/blocks.json")
journals     = _PersistentRepo[JournalEntry]("~/.time-tasker/journals.json")
# … 11 more
```

## 9. Cross-cutting

- **`_compat.py`** — version shims for Typer/Rich/Pydantic combo compatibility. The CLI tests against a pinned trio.
- **`console.py`** — one Rich `Console` singleton, width=120, theme-aware.
- **`services.py`** — pure data services (`get_day_snapshot`, `validate_*`); the CLI can call these without going through `core/` if the work is already trivial.

## 10. Anti-patterns explicitly avoided

| Don't | Why | Instead |
|---|---|---|
| Print directly with `print()` | Bypasses Rich, no colour, no wrap | Use `console.print()` |
| Hardcode a colour in a widget | Breaks theming | Use `tokens.SEVERITY_*` |
| Construct an entity from `BaseModel(**dict)` | Skips factory validation | Always go through `factories.make_*` |
| Read JSON without `model_validate_json` | Silent schema drift | `Entity.model_validate_json(text)` |
| Capture output in a string for `--json` | Branchy code, easy to desync | Render the same entity both ways from one source |
