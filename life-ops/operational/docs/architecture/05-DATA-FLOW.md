# 05 — Data Flow

> End-to-end trace of a single command: `operational report daily
> --date 2026-06-08`. The user types a string; Rich renders a
> dashboard. Every step, every file, every line number.

The point of this document is to show a new contributor **what
actually happens** when a command runs. The MVC layers are abstract
until you trace one path through them.

---

## 1. The user input

```
$ operational report daily --date 2026-06-08
```

Typer parses this against the sub-typer at
`cli/app.py:46` (`app.add_typer(report_app, name="report", ...)`)
and the command at `cli/commands/report_cmd.py:45-49`.

---

## 2. Sequence diagram

```
┌──────┐         ┌─────────┐         ┌──────────────┐         ┌──────────────┐         ┌──────────┐
│ USER │         │  Typer  │         │  Controller  │         │  core.       │         │  ui.     │
│      │         │  app    │         │  report_cmd  │         │  services    │         │  daily_  │
│      │         │         │         │              │         │              │         │  report  │
└──┬───┘         └────┬────┘         └──────┬───────┘         └──────┬───────┘         └────┬─────┘
   │                  │                     │                        │                      │
   │  "operational    │                     │                        │                      │
   │   report daily   │                     │                        │                      │
   │   --date ...   " │                     │                        │                      │
   │─────────────────>│                     │                        │                      │
   │                  │                     │                        │                      │
   │                  │  parse --date arg,  │                        │                      │
   │                  │  invoke daily()     │                        │                      │
   │                  │────────────────────>│                        │                      │
   │                  │                     │                        │                      │
   │                  │                     │  date.fromisoformat(   │                      │
   │                  │                     │    "2026-06-08")       │                      │
   │                  │                     │  → d = date(2026,6,8)  │                      │
   │                  │                     │                        │                      │
   │                  │                     │  get_day_snapshot(d)   │                      │
   │                  │                     │──────────────────────> │                      │
   │                  │                     │                        │                      │
   │                  │                     │                        │  reads 14 repos:     │
   │                  │                     │                        │  - sleep_records     │
   │                  │                     │                        │  - day_contexts      │
   │                  │                     │                        │  - time_blocks       │
   │                  │                     │                        │  - pomodoros         │
   │                  │                     │                        │  - transicoes        │
   │                  │                     │                        │  - routine_logs      │
   │                  │                     │                        │  - routines          │
   │                  │                     │                        │  - lunch_records     │
   │                  │                     │                        │  - journals          │
   │                  │                     │                        │  - ajustes_finos     │
   │                  │                     │                        │  - daily_reflections │
   │                  │                     │                        │                      │
   │                  │                     │                        │  joins them into     │
   │                  │                     │                        │  DaySnapshot         │
   │                  │                     │                        │  (frozen dataclass)  │
   │                  │                     │                        │                      │
   │                  │                     │       snap             │                      │
   │                  │                     │<────────────────────── │                      │
   │                  │                     │                        │                      │
   │                  │                     │  render_daily_report(snap)                    │
   │                  │                     │───────────────────────────────────────────────>│
   │                  │                     │                        │                      │
   │                  │                     │                        │  compute_day_quadrant│
   │                  │                     │                        │  (snap)              │
   │                  │                     │                        │<─────────────────────│
   │                  │                     │                        │  q_code, x, y        │
   │                  │                     │                        │                      │
   │                  │                     │                        │  build rich.Group:   │
   │                  │                     │                        │   - header Table     │
   │                  │                     │                        │   - kpi cards        │
   │                  │                     │                        │   - pomodoros grid   │
   │                  │                     │                        │   - cartesian plane  │
   │                  │                     │                        │   - next-step panel  │
   │                  │                     │                        │                      │
   │                  │                     │       group            │                      │
   │                  │                     │<───────────────────────────────────────────────│
   │                  │                     │                        │                      │
   │                  │                     │  console.print(group)  │                      │
   │                  │                     │─────────┐              │                      │
   │                  │                     │         │              │                      │
   │                  │                     │<────────┘              │                      │
   │                  │                     │                        │                      │
   │   <ANSI-coded rich dashboard>          │                        │                      │
   │<────────────────────────────────────────────────────────────────────────────────────│
   │                  │                     │                        │                      │
```

The flow has 6 distinct steps. Each is detailed below.

---

## 3. Step 1 — Typer dispatch

`cli/app.py:32-49` builds the root Typer app and registers the
`report` sub-typer:

```python
app = typer.Typer(
    name="time-tasker",
    help="⚡ TIME-TASKER — Algorítmica Visual: rotinas, blocos, ...",
    no_args_is_help=True,
)
app.add_typer(report_app, name="report", help="Gerar relatórios diário/semanal.")
```

Typer parses `operational report daily --date 2026-06-08` and
discovers that the `report` group has a `daily` command. It then
calls:

```python
# cli/commands/report_cmd.py:46
@app.command()
def daily(
    report_date: str | None = typer.Option(None, "--date", "-d", help="Data (YYYY-MM-DD)"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    ...
```

with `report_date="2026-06-08"`, `json=False`.

---

## 4. Step 2 — Validate date

`cli/commands/report_cmd.py:51`:

```python
d = date.fromisoformat(report_date) if report_date else date.today()
```

`date.fromisoformat("2026-06-08")` returns `date(2026, 6, 8)`. A
malformed date would raise `ValueError`, which Typer converts to a
user-facing error. (For a more domain-aware error message, the
project provides `core.services.parse_iso_date` at
`core/services.py:315-327`, which raises `DataInvalidaError` instead.
`report_cmd.daily` uses the stdlib version for now.)

---

## 5. Step 3 — `core.services.get_day_snapshot(d)`

`cli/commands/report_cmd.py:54`:

```python
snap: DaySnapshot = get_day_snapshot(d)
```

`get_day_snapshot` is defined at `core/services.py:133-277`. It
reads the 14 repos via the imports at `core/services.py:27-39`:

```python
from operational.cli.state import (
    ajustes_finos, daily_reflections, day_contexts, journals,
    lunch_records, pomodoros, routine_logs, routines,
    sleep_records, time_blocks, transicoes,
)
```

(That's the documented `core → cli.state` compromise — see
[01-MVC-LAYERS.md §2.2](01-MVC-LAYERS.md#22-the-single-hard-compromise).)

The function:

1. **Sleep** (`core/services.py:139-146`): finds the `SleepRecord`
   for `d`. Builds a `SleepSnapshot` with bedtime, wake, duration,
   quality, notes.
2. **DayContext** (`core/services.py:149-157`): finds a
   `DayContext` for `d`; if absent, infers `TipoDia` from weekday
   (`_infer_tipo_dia` at `core/services.py:280-284`) and pulls
   `hardwork_orcado_min` from `core.budget.budget_for_date(d,
   tipo_dia)`.
3. **Blocks / pomodoros** (`core/services.py:160-168`): filters
   `time_blocks` and `pomodoros` to those starting on `d`. Counts
   pomodoros with `"COMPLETE"` in their state string. Counts
   completed `transicoes`.
4. **Routine logs** (`core/services.py:171-198`): filters
   `routine_logs` to those on `d`. For each log, looks up the
   parent `Routine` and detects workout / meditation by name
   substring (`"workout"`, `"academia"`, `"medita"`, ...).
5. **Lunch** (`core/services.py:200-204`): finds the `LunchRecord`
   for `d`; defaults to `eat=5, rest=30, pesado=False`.
6. **Journal** (`core/services.py:207-218`): finds the
   `JournalEntry` for `d`; pulls `energia_nivel`, `foco_nivel`,
   `humor_morning`, `humor_evening`, `desvios`, `licoes_aprendidas`.
7. **Adjustments** (`core/services.py:221`): collects
   `AjusteFino.reason` for `d`.
8. **Reflection** (`core/services.py:224-238`): finds the
   `DailyReflection` for `d`; pulls `big_win`, `parar_de_fazer`,
   `repetir`, `deu_certo`, `deu_errado`, `maior_aprendizado`.

The function returns a **frozen dataclass** (`core/services.py:55-103`).
This is the contract between `core.services` and `ui.daily_report`:
**Pydantic entities do not leak to the UI**; only the
frozen `DaySnapshot` does.

---

## 6. Step 4 — Branch on `--json`

`cli/commands/report_cmd.py:56-93`:

```python
if json:
    # Plain dict for machine consumption
    q_code, x, y = compute_day_quadrant(snap)
    payload = { "date": d.isoformat(), "tipo_dia": snap.tipo_dia.value, ... }
    typer.echo(format_as_json(payload))
    return
```

For `--json` mode, the controller builds a flat dict, calls
`core.services.compute_day_quadrant` (which uses
`core.budget.productivity_pct` and `efficiency_pct` to derive the
Cartesian position), and emits via
`cli/formatters/base.py:format_as_json` (which uses
`json.dumps` with a fallback for `BaseModel` and `datetime`).

For the **non-JSON** path (which is the focus of the rest of this
document), execution continues to step 5.

---

## 7. Step 5 — `ui.daily_report.render_daily_report(snap)`

`cli/commands/report_cmd.py:96`:

```python
report = render_daily_report(snap)
```

`render_daily_report` is defined at
`ui/daily_report.py:50-340`. It is a **factory** — it takes a
frozen `DaySnapshot` and returns a `rich.console.Group` containing
all the panels and tables of the daily dashboard.

Internally (`ui/daily_report.py:50-80`):

1. `compute_day_quadrant(snap)` → `(q_code, x, y)` — the Cartesian
   position.
2. Build the **header table** (`build_header_table`, line 50)
   showing date · tipo_dia · quadrant emoji · pomodoros.
3. Build a **sleep row** showing bedtime, wake, duration, quality.
4. Build **KPI cards** for hardwork (orçado/realizado), pomodoros,
   sleep, energy/focus.
5. Build a **pomodoros grid** — one cell per round, colour-coded by
   state.
6. Build a **cartesian plane** — the X (produtividade) × Y
   (eficiência) plot with the day's position marked.
7. Build **section panels** for the OKRs (deu_certo, deu_errado,
   maior_aprendizado, big_win, ajustes).
8. Build a **next-step recommendation** panel based on the quadrant.
9. Wrap everything in a `rich.console.Group` and return it.

The function makes heavy use of `ui/components.py` factories:
`kpi_card`, `pomodoros_grid`, `cartesian_plane`, `section_panel`,
`next_step_panel`, `severity_text`. None of these call
`console.print` — they return renderables that the caller composes.

---

## 8. Step 6 — `console.print(group)`

`cli/commands/report_cmd.py:97`:

```python
console.print(report)
```

`console` is imported from `operational.cli.console` at
`cli/commands/report_cmd.py:16`. The shim at
`cli/console.py:10` re-exports the singleton from
`operational.ui`:

```python
# cli/console.py
from operational.ui import CONSOLE_WIDTH, console  # noqa: F401
```

`console.print(group)` walks the Group recursively, calling each
renderable's `__rich_console__` method. The output is emitted to
stdout as ANSI-coded text (or as plain text if `is_captured()` is
True — see `ui/__init__.py:35-37`).

The captured-vs-TTY distinction matters: when the home menu calls a
command in-process via `_run_cmd` (`cli/home.py:49-75`), stdout is
not a TTY. Rich auto-detects this via `force_terminal=False` and
disables colors (`no_color=is_captured()`,
`ui/__init__.py:48`). The home menu then strips any remaining ANSI
codes with `strip_ansi` (`ui/__init__.py:67-73`) before re-printing
on its own central console.

---

## 9. The full call chain (one-liner per layer)

| Layer | File:line | Call |
|---|---|---|
| Typer | `cli/app.py:32` | `app = typer.Typer(...)` |
| Typer | `cli/app.py:46` | `app.add_typer(report_app, name="report", ...)` |
| Controller | `cli/commands/report_cmd.py:46` | `def daily(report_date, json) -> None:` |
| Controller | `cli/commands/report_cmd.py:51` | `d = date.fromisoformat(report_date)` |
| Controller | `cli/commands/report_cmd.py:54` | `snap = get_day_snapshot(d)` |
| Core | `core/services.py:133` | `def get_day_snapshot(d) -> DaySnapshot:` |
| Core | `core/services.py:139-238` | reads 14 repos, joins, returns frozen `DaySnapshot` |
| Controller | `cli/commands/report_cmd.py:96` | `report = render_daily_report(snap)` |
| UI | `ui/daily_report.py:50` | `def render_daily_report(snap) -> Group:` |
| UI | `ui/daily_report.py:50-340` | builds header, KPIs, grid, plane, panels |
| Controller | `cli/commands/report_cmd.py:97` | `console.print(report)` |
| UI | `ui/__init__.py:43` | `console: Console = Console(width=120, ...)` |
| Output | stdout | ANSI-coded rich renderable (or plain if captured) |

Total elapsed: typically **20-80 ms** for a 30-day dataset. The
bottleneck is the 14 `repo.list()` calls in
`core/services.py:139-238` — each one is a full
`_load_all()` of the in-memory dict, which is O(n) for `n` entities.

---

## 10. Variants and side branches

The `report` group has two commands:

- **`daily`** — the path traced above.
- **`weekly`** — `cli/commands/report_cmd.py:106-315`. Walks 7
  days (`ws` to `we`), calls `get_day_snapshot(d)` for each,
  aggregates the KPIs, sparklines, TipoDia / Quadrant
  distributions, daily positions, sleep breakdown, and a
  next-step panel. The weekly command does **more** UI construction
  inline (sparklines, distribution tables at
  `cli/commands/report_cmd.py:196-274`) than the daily command. This is
  the one place in `commands/` where a `Table(...)` and a `Group(...)`
  are built directly. The weekly command is documented as "kept
  lighter — delegate to daily report for now"
  (`cli/commands/report_cmd.py:101`),
  and the inline Table construction is an acknowledged
  compromise until the weekly report is refactored into
  `ui/weekly_report.py` with the same factory discipline as
  `ui/daily_report.py`.

The home menu variant: when invoked from
`operational home` → `Menu item 6` (`cli/home.py:323-330`) →
`report daily` → `_run_cmd(["report", "daily"])` →
`cli/home.py:60` `typer_app(args=["report", "daily"],
standalone_mode=False)`, the same call chain runs **in-process**
and the output is captured via `contextlib.redirect_stdout` and
re-printed on the home menu's central console.

---

## 11. Where to read next

- [01-MVC-LAYERS.md](01-MVC-LAYERS.md) — the layer rules this trace
  obeys
- [02-PERSISTENCE-LAYER.md](02-PERSISTENCE-LAYER.md) — the storage
  layer the trace reads from
- [04-IMPORT-GRAPH.md](04-IMPORT-GRAPH.md) — the static graph
  underlying the dynamic call chain
