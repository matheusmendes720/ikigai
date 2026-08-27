# 01 — MVC Layers

> The three-layer architecture that makes `operational` testable, with
> hard rules about who can import whom.

The project follows **strict MVC** with three layers and one
discipline: **controllers are thin, core is pure, ui is factories**.
This doc is the spec; if you want to add a new feature, read this
first and pick the right layer.

---

## 1. The rule

> **Controllers never contain business logic.**
> **Core never imports Rich or Typer.**
> **UI is a set of factory functions that return Rich renderables.**

In one sentence:

```
Typer command  →  calls services  →  returns frozen dataclass
                                       ↓
                                 passed to ui.* renderable factory
                                       ↓
                                 Group / Panel / Table returned
                                       ↓
                                 console.print(group)
```

The discipline is enforced by the import graph: `core/` cannot import
from `ui/` or `cli/`, and `ui/` cannot import from `cli/commands/`.
Tests rely on this — `tests/core/` exercises pure functions in
isolation, and `tests/ui/` exercises factories with pre-built
dataclasses.

---

## 2. Layer 1: Core

**Location:** `src/operational/core/`

Pure business logic. **No Rich, no Typer, no console.print, no I/O**
(except for the two places that touch `cli/state.py`, which is a
known compromise — see below).

| File | What lives here |
|---|---|
| `budget.py` | `budget_for_date`, `classify_quadrant`, `productivity_pct`, `efficiency_pct`, `infer_tipo_dia`, `classify_infracao` |
| `sleep_calculator.py` | `calcular_horas_sono`, `validar_sono_ideal`, `is_within_optimal_window`, `get_sleep_matrix`, `SleepQuality`, `SleepDecision` |
| `time_validator.py` | `validar_horario_acordar`, `is_optimal_wake_hour`, `WakeUpValidation` |
| `break_calculator.py` | `compute_break_minutes`, `compute_breaks`, `compute_break_statistics`, `BreakInfo`, `BreakStatistics`, `adjusted_net_rest_minutes` |
| `context_switch.py` | `context_switch_overhead_minutes`, `estimate_context_switch`, `net_rest_minutes`, `ContextSwitchSeverity` |
| `pomodoro_machine.py` | `PomodoroTracker`, `PomodoroPlugin` (Protocol), `InMemoryPomodoroPlugin`, transition table |
| `routine_logger.py` | `RoutineLogger`, `build_routine_log`, `build_ajuste_fino`, `filter_routine_logs_by_date` |
| `journal_segmenter.py` | `segment_journal_by_period`, `render_natural_language_report`, `render_full_day_report`, `JournalReport` |
| `habit_engine.py` | Habit aggregation, QHE-aware streak math |
| `policy_engine.py` | `PolicyEngine` state machine (PUSH/MAINTAIN/REDUCE/RECOVER) + `DecisionRecord` history |
| `scenario_classifier.py` | `classificar_dia`, `is_hardcore_alert`, `Scenario`, `HARDCORE_MAX_PER_MONTH` |
| `consolidator.py` | `consolidate_daily`, `compute_energy_score`, `compute_productivity_score`, `generate_alerts`, `generate_recommendations` |
| `weekly_aggregator.py` | Weekly rollups over `DailyConsolidation` |
| `services.py` | **`get_day_snapshot(d)`**, `compute_day_quadrant`, `validate_pomodoro_count`, `parse_iso_date`, `require_sleep_record`, `require_day_context`, `validate_required_fields`, `distribute_pomodoros_across_sessions` |
| `exceptions.py` | `FaltaDadosError`, `ValorForaRangeError`, `RepositorioVazioError`, `LimitePomodoroExcedidoError`, `DataInvalidaError` |

### 2.1 What Core imports

- `operational.entities.*` — reads entities from `cli/state` (see 2.2)
- `operational.enums` — period / policy / state enums
- `operational.constants` — `PAVConstants`, `DEFAULT`
- `operational.types` — `UEID`, `Clock`, `Logger`
- `operational.core.exceptions` — domain errors
- **Never** `rich.*`, `typer.*`, or `operational.cli.*` (with one
  exception — see 2.2)

### 2.2 The single hard compromise

`core/services.py:27-39` imports from `operational.cli.state`:

```python
from operational.cli.state import (
    ajustes_finos, daily_reflections, day_contexts, journals,
    lunch_records, pomodoros, routine_logs, routines,
    sleep_records, time_blocks, transicoes,
)
```

This is the **one** place the layering is broken, and it's broken on
purpose: services are *the* place that wants "all entities for a given
date", and the 14 repos live in `cli/state.py` for backwards-compat
with the interactive home menu. The fix would be to move the repos
into a dedicated `operational.persistence.live` module; that work is
not on the current roadmap. Until then, treat `core/services.py` as
the *de facto* cross-cutting data-access layer.

> **Rule of thumb**: if you need to read entities, go through
> `services.get_day_snapshot(d)` rather than importing repos
> directly. Direct repo access in a controller is a smell.

---

## 3. Layer 2: UI

**Location:** `src/operational/ui/`

Rich renderable factories. No Typer, no business logic, no data
fetching.

| File | What lives here |
|---|---|
| `__init__.py` | The canonical `Console` singleton (width=120, soft_wrap), `CONSOLE_WIDTH`, `is_captured()`, `strip_ansi()`, and global Rich traceback install |
| `components.py` | Reusable renderable factories: `kpi_card`, `metric_table`, `progress_bar`, `pomodoros_grid`, `timeline_h`, `cartesian_plane`, `sparkline`, `status_badge`, `input_summary`, `next_step`, `section_header`, `severity_text`, plus the color palettes `COLORS`, `TIPO_DIA_COLOR`, `QUADRANT_COLOR`, `QUADRANT_LABEL`, `QUADRANT_ACTION` |
| `daily_report.py` | `render_daily_report(snap: DaySnapshot) -> Group` — the full daily V3 report |
| `logging_setup.py` | Log file/JSON configuration |

### 3.1 The Console singleton

The single Rich `Console` instance lives at `ui/__init__.py:43-54`:

```python
console: Console = Console(
    width=CONSOLE_WIDTH,           # 120
    soft_wrap=True,
    force_terminal=False,          # let Rich auto-detect
    color_system="auto",
    no_color=is_captured(),        # strip ANSI when captured
    highlight=True,
    markup=True,
    emoji=True,
    legacy_windows=False,
    safe_box=False,                # full Unicode box characters
)
```

It is **imported** by every layer that needs to print, including the
backward-compat shim at `cli/console.py` (which re-exports it for
pre-refactor files that still `from operational.cli.console import
console`).

The Rich traceback handler is installed globally at
`ui/__init__.py:60-64` (5 frames, show_locals). Any uncaught
exception in any layer prints a beautiful colorized traceback.

### 3.2 The factory pattern

Every function in `ui/components.py` and `ui/daily_report.py` has the
same shape:

```python
def kpi_card(title: str, value: str, *, color: str, footer: str,
             icon: str, width: int = 30) -> Panel:
    """Build a single big-number card."""
    # ... build a rich.Panel ...
    return panel
```

Inputs are Python data (str, int, dataclass, list). The output is a
Rich `RenderableType` (Panel, Table, Group, Text). **The function
does not call `console.print()`** — the caller does. This is what
makes the factories composable: a Panel can be wrapped in a Group
can be wrapped in another Panel can be passed to a top-level
`console.print`.

> **Forbidden pattern**: `f"x{' ' * n}y"` for alignment. Use
> `Table.grid(expand=False, padding=(0, 1))` with explicit columns.
> See `ui/components.py:10` for the rationale.

---

## 4. Layer 3: Controllers

**Location:** `src/operational/cli/commands/`

Thin Typer dispatchers. The module docstrings literally say so:

```python
"""Report generation CLI commands — thin orchestrators (MVC controller layer).

Per architecture rules:
- This file ONLY captures CLI args, calls core.services for data,
  and feeds the data into ui.* factories for rendering.
- NO business logic here.
- NO Rich construction here (no Table, Panel, Text building).
- NO string concatenation for visual layout.
"""
# (cli/commands/report_cmd.py:1-9)
```

There are 12 sub-typer files. Each is shaped the same way:

```python
# cli/commands/routine_cmd.py:17
app = typer.Typer(help="Manage routines.")

@app.command()
def create(name: str, period: Period, ...) -> None:
    # 1. Capture CLI args (Typer does this for us)
    # 2. Build entity (or call core.services)
    # 3. repo.upsert(entity)
    # 4. Either console.print(...) or typer.echo(format_as_json(...))
```

### 4.1 The `_run_cmd` pattern (home menu)

The interactive home menu in `cli/home.py` does not invoke Typer as a
subprocess; it **invokes the app in-process** with
`typer_app(args=args, standalone_mode=False)` and captures stdout via
`contextlib.redirect_stdout` (`cli/home.py:49-75`). ANSI codes are
stripped (`strip_ansi`) because inner Rich consoles may force TTY mode.

```python
# cli/home.py:49-75
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
        console.print(Panel(f"[red]{type(e).__name__}:[/red] {e}",
                            title="[bold red]Error[/bold red]",
                            border_style="red"))
    Prompt.ask("\n[dim]Press Enter to continue[/dim]")
```

This is the only place where the layering is bent: the home menu
imports `operational.cli.app` *and* re-runs it in-process. The
recursive import works because the `home` command at `cli/app.py:52-56`
is defined as a thin function that defers the heavy import.

### 4.2 The Typer app structure

The root Typer app lives at `cli/app.py:32-36`. Sub-typers are
registered at `cli/app.py:38-49`:

```python
app = typer.Typer(
    name="time-tasker",
    help="⚡ TIME-TASKER — Algorítmica Visual: rotinas, blocos, ...",
    no_args_is_help=True,
)
app.add_typer(routine_app, name="routine", help="Gerenciar rotinas (MANHA/TARDE/NOITE).")
app.add_typer(block_app,   name="block",   help="Gerenciar blocos de tempo.")
# ... 10 more add_typer() calls ...
```

The `home` command is special: it's a plain `@app.command()` at
`cli/app.py:52-56` that defers to `cli/home.run_home()` (which lives
in a different module to avoid the recursive import).

---

## 5. Import graph

```
                         ┌──────────────────────────┐
                         │   operational.cli.app    │
                         │   (Typer root, controllers│
                         │    register themselves)  │
                         └────────────┬─────────────┘
                                      │ imports 12 sub-typers
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
   operational.cli.commands.   operational.cli.home      operational.cli.dataset_selector
       {routine,block,...}_cmd       │                  operational.cli.csv_loader
            │                         │                         │
            ├───── imports ───────────┼─────────────────────────┤
            │                         │                         │
            ▼                         ▼                         ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  operational.cli.state  ─→  operational.persistence.memory  │
   │  (14 _PersistentRepo     ─→  operational.entities.<X>      │
   │   instances, auto-load)   ─→  operational.enums            │
   │                            ─→  operational.types            │
   │                            ─→  operational.constants        │
   └─────────────────────────────────────────────────────────────┘
                                      ▲
                                      │  imported by
                                      │
   ┌──────────────────────────────────┴──────────────────────────┐
   │   operational.core.services                                   │
   │   (get_day_snapshot, validate_*, compute_day_quadrant)       │
   │   ─→  operational.enums                                       │
   │   ─→  operational.constants                                   │
   │   ─→  operational.core.exceptions                             │
   │   ─→  operational.entities.<X>   (via cli.state import)       │
   │   ─→  operational.core.budget                                  │
   └─────────────────────────────────────────────────────────────────┘
                                      ▲
                                      │  imported by controllers
                                      │  AND by ui/
                                      │
   ┌────────────────────────────────────────────────────────────────┐
   │   operational.ui.*                                              │
   │   ─→  operational.cli.console  (backward-compat shim →          │
   │                                  operational.ui.console)       │
   │   ─→  operational.core.services  (for DaySnapshot + quadrant)   │
   │   ─→  operational.enums                                       │
   │   ─→  operational.constants                                   │
   │   ─→  NO operational.cli.* (except the console shim)            │
   │   ─→  NO operational.persistence.* (UI never touches storage)  │
   │   ─→  NO typer                                                │
   └────────────────────────────────────────────────────────────────┘

   ┌────────────────────────────────────────────────────────────────┐
   │  Leaves (no operational imports):                              │
   │  • operational.enums          • operational.types              │
   │  • operational.constants       • operational.exceptions        │
   │  • operational.entities.*     (Pydantic models are leaves)     │
   └────────────────────────────────────────────────────────────────┘
```

**Critical rules visible in this graph:**

1. **`ui/` never imports `typer`**. The only Typer import in any UI
   file would be a layering bug.
2. **`ui/` never imports `persistence`**. The UI consumes frozen
   dataclasses from `core.services`; it does not know there is a repo
   underneath.
3. **`core/` never imports `rich`**. The grep is enforceable.
4. **`core/services.py` is the only core file that imports
   `operational.cli.state`** (the hard compromise documented in
   2.2). Every other core module imports only from `enums`,
   `constants`, `types`, and other `core/*` modules.

---

## 6. The "no business logic in controllers" rule

A controller should look like this — **good**:

```python
# cli/commands/journal_cmd.py  (abbreviated)
@app.command()
def create(text: str, date: str | None = None) -> None:
    d = date.fromisoformat(date) if date else date.today()
    j = JournalEntry(id=f"day_{d.isoformat()}", date=d, entry_text=text,
                     created_at=datetime.now())
    journals.upsert(j)              # repo write
    typer.echo(format_as_json({     # output
        "id": j.id, "date": j.date.isoformat(), "text": j.entry_text,
    }))
```

It should **not** look like this — **bad**:

```python
# DO NOT DO THIS
@app.command()
def create(text: str) -> None:
    # 1. Validation in the controller — wrong layer
    if not text or not text.strip():
        typer.echo("❌ Text cannot be empty")
        raise typer.Exit(1)
    if len(text) > 5000:
        typer.echo("❌ Text too long")
        raise typer.Exit(1)

    # 2. Domain logic in the controller — wrong layer
    today = date.today()
    weekday = today.weekday()
    if weekday < 5 and not text.startswith("[TRABALHO]"):
        # business rule: weekdays need a tag
        text = f"[TRABALHO] {text}"

    # 3. ID generation in the controller — wrong layer
    jid = f"day_{today.isoformat()}_{uuid4().hex[:8]}"

    # 4. Entity construction in the controller — debatable
    j = JournalEntry(id=jid, date=today, entry_text=text, created_at=datetime.now())

    # 5. Persistence + rendering both in the controller
    journals.upsert(j)
    panel = Panel(Text(text, style="bold green"),
                  title=f"Journal {today}")
    console.print(panel)
```

What's wrong with the bad example:

- **Validation belongs in the Pydantic entity** (it already enforces
  `max_length=5000` and `min_length=1` on `JournalEntry.entry_text`).
  The duplicate check is dead code.
- **The "weekday needs a tag" rule is a domain rule.** It belongs in
  `core/journal_segmenter.py` or a dedicated validator.
- **The ID convention belongs in `meta/factories.py`** as
  `make_journal_entry(date)`.
- **Building a Panel in the controller** is forbidden by
  `ui/components.py:1-11`. Use `ui.components.section_panel(...)` or
  similar factory.

The bad example is a strawman, but the *kinds* of mistakes it makes
are real and recur in PRs that skip this layer check. When in doubt,
grep for `Panel(`, `Table(`, `Text(`, `f"x{' '*n}y"` in
`cli/commands/*.py` — the only acceptable matches are local helpers
named `_kpi` / `_panel` that delegate to `ui.components.*`.

---

## 7. Data flow

End-to-end: user types a command → output is rendered.

```
┌─────────────────────────────────────────────────────────────────┐
│  USER                                                            │
│   $ operational report daily --date 2026-06-08                   │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Typer dispatch (cli/app.py:32)                                  │
│   parses "report daily --date 2026-06-08"                       │
│   → cli/commands/report_cmd.py:46  def daily(...)                │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Controller (MVC layer 3)                                        │
│   • Validate date with date.fromisoformat()                      │
│   • Call core.services.get_day_snapshot(d)                       │
│   • Decide: --json?  Yes → typer.echo(format_as_json(...))       │
│             No  → render_daily_report(snap) → console.print(r)  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                          ▼
┌──────────────────────────┐  ┌──────────────────────────────────┐
│  core.services           │  │  ui.daily_report                 │
│  get_day_snapshot(d)     │  │  render_daily_report(snap)       │
│   • reads 14 repos       │  │   • builds header Table          │
│   • joins sleep +        │  │   • builds pomodoros grid        │
│     blocks + pomodoros +  │  │   • builds kpi cards             │
│     journals + ...       │  │   • builds cartesian plane       │
│   • returns DaySnapshot   │  │   • wraps in Group               │
│     (frozen dataclass)   │  │   → returns rich.Group           │
└──────────────────────────┘  └──────────────────────────────────┘
              │                          │
              └────────────┬─────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Console (ui/__init__.py:43)                                      │
│   console.print(group_or_panel)                                   │
│   → ANSI codes (or none, if is_captured())                        │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
                     STDOUT (TTY or pipe)
```

For the full `operational report daily` walkthrough with line numbers,
see [05-DATA-FLOW.md](05-DATA-FLOW.md).
