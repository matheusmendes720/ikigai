# `operational` — Architecture Master Index

> **Project**: `life-ops/operational` — a standalone Typer CLI that
> implements the PAV (Produtividade Algorítmica Visual) operational
> system. Pure arithmetic, 100% local, no LLM, no cloud.

This is the entry point for the architecture documentation. It maps
the whole project in one page; each section links to a deeper doc.

---

## 1. What is this?

`operational` is a 100% local, single-user CLI for tracking **routines,
time blocks, habits, journal entries, sleep and policy decisions**
according to the PAV (Produtividade Algorítmica Visual) spec. It runs
as a Typer command (`operational <subcommand>`) with an interactive
home menu, exposes **14 Pydantic v2 entity types** persisted in JSON
files under `~/.time-tasker/`, and ships with **2 built-in CSV
datasets** (`golden`, `synthetic`) for regression tests and demos.
The codebase is **2755 tests passing**, zero mypy errors, and follows a
strict three-layer MVC architecture (Core / UI / Controllers) with
zero business logic in controllers.

---

## 2. Architecture layers

```
src/operational/
├── __init__.py            # public API re-exports
├── __main__.py            # python -m operational entry point
├── constants.py           # PAVConstants (24 frozen fields) + DEFAULT
├── enums.py               # 15 StrEnums (Period, PolicyState, ...)
├── types.py               # UEID alias, Repository/Clock/Logger protocols
├── exceptions.py          # ProductivitySystemError + 11 PAV error codes
│
├── core/                  # Layer 1: pure business logic (no Rich/Typer)
│   ├── budget.py            # budget_for_date, classify_quadrant, ...
│   ├── sleep_calculator.py  # calcular_horas_sono, validar_sono_ideal
│   ├── time_validator.py    # validar_horario_acordar
│   ├── break_calculator.py  # compute_breaks, BreakInfo
│   ├── context_switch.py    # net_rest_minutes
│   ├── pomodoro_machine.py  # PomodoroTracker, transition table
│   ├── routine_logger.py    # build_routine_log, RoutineLogger
│   ├── journal_segmenter.py # segment_journal_by_period
│   ├── habit_engine.py      # habit aggregation
│   ├── policy_engine.py     # PolicyEngine FSM (PUSH/MAINTAIN/...)
│   ├── scenario_classifier.py  # classificar_dia
│   ├── consolidator.py      # consolidate_daily
│   ├── weekly_aggregator.py # weekly rollups
│   ├── services.py          # get_day_snapshot, validate_*
│   └── exceptions.py        # core-layer domain errors
│
├── entities/              # 14 Pydantic v2 leaves (no cross-entity imports)
│   ├── routine.py           # Routine, Ritual, Transition, RoutineLog
│   ├── time_block.py        # TimeBlock
│   ├── journal.py           # JournalEntry, AutoIndagacao
│   ├── habit.py             # Habit, HabitState, QHEMetrics
│   ├── metric.py            # SleepRecord, EnergyReading, DailyLog
│   ├── pomodoro.py          # PomodoroConfig, PomodoroRound, PomodoroSession
│   ├── policy.py            # PolicySetpoints, PolicyDecision, DecisionRecord
│   ├── ajuste_fino.py       # AjusteFino
│   ├── consolidation.py     # DailyConsolidation, MetricAlert, WeeklyAggregate
│   └── v3.py                # DayContext, DailyReflection, LunchRecord, TransicaoRegistrada
│
├── ui/                    # Layer 2: Rich factories (no Typer, no logic)
│   ├── __init__.py          # canonical Console singleton
│   ├── components.py        # COLORS, severity helpers, kpi_card, ...
│   ├── daily_report.py      # render_daily_report(snap) -> Group
│   └── logging_setup.py     # log file/JSON config
│
├── cli/                   # Layer 3: thin Typer controllers
│   ├── app.py               # typer.Typer root + 12 sub-typers
│   ├── home.py              # interactive 10-item menu
│   ├── state.py             # 14 _PersistentRepo instances + auto-load
│   ├── console.py           # backward-compat shim -> ui.console
│   ├── dataset_selector.py  # resolve TIME_TASKER_DATASET -> CSV path
│   ├── csv_loader.py        # 14-entity CSV I/O (utf-8-sig, CRLF)
│   ├── seed.py              # demo seed builder (7 PAV scenarios)
│   ├── renderers.py         # make_console, kpi_card, ...
│   ├── input_summary.py     # "você digitou" table
│   ├── formatters/          # format_as_json, format_as_table, ...
│   └── commands/            # 12 subcommand files
│       ├── routine_cmd.py
│       ├── block_cmd.py
│       ├── journal_cmd.py
│       ├── habit_cmd.py
│       ├── metric_cmd.py
│       ├── policy_cmd.py
│       ├── report_cmd.py
│       ├── state_cmd.py
│       ├── reflect_cmd.py
│       ├── lunch_cmd.py
│       ├── demo_cmd.py
│       └── doctor_cmd.py
│
├── persistence/           # Repository Protocol + 3 backends
│   ├── base.py              # RepositoryBase[T_Entity] (ABC)
│   ├── memory.py            # InMemoryRepository (dict-backed)
│   ├── sqlite.py            # SqliteRepository (entities + data JSON)
│   ├── runner.py            # MigrationRunner (SQL files)
│   ├── migrations/          # 001_initial.sql
│   └── exceptions.py        # DuplicateEntityError, MigrationError, ...
│
├── meta/                  # Registry, factories, validators
│   ├── registry.py          # entity_registry
│   ├── factories.py         # make_routine, make_habit, ...
│   └── validators.py        # validate_ueid_format, ...
│
├── parsers/               # YAML/frontmatter parsers
└── reports/               # generate_daily_summary, generate_weekly_report
```

Layered reading order: read **[01-MVC-LAYERS.md](01-MVC-LAYERS.md)**
for the rules, **[02-PERSISTENCE-LAYER.md](02-PERSISTENCE-LAYER.md)**
for the data plumbing, then drill into **[03-ENTITY-LIFECYCLE.md](03-ENTITY-LIFECYCLE.md)**
for the 14 entities.

---

## 3. 14 entities at a glance

| Entity | File | Purpose |
|---|---|---|
| `Routine` | `entities/routine.py:80` | A time-bounded daily task within a `Period` |
| `RoutineLog` | `entities/routine.py:347` | Natural-language log of a single routine execution |
| `Ritual` | `entities/routine.py:215` | Short transitional action (1-60 min) |
| `Transition` | `entities/routine.py:275` | Boundary marker between two `Period` values |
| `TimeBlock` | `entities/time_block.py:41` | Calendar-aware ad-hoc time interval |
| `JournalEntry` | `entities/journal.py:90` | Daily narrative + energy/focus/mood |
| `AutoIndagacao` | `entities/journal.py:248` | Socratic self-inquiry ritual (11 questions) |
| `Habit` | `entities/habit.py:88` | Static habit definition (R, λ, w, frequency) |
| `HabitState` | `entities/habit.py:234` | Daily state of a habit (streak, effort) |
| `QHEMetrics` | `entities/habit.py:407` | Quality-Habit-Effectiveness daily snapshot |
| `SleepRecord` | `entities/metric.py:101` | One night's sleep (bedtime, wake, quality) |
| `EnergyReading` | `entities/metric.py:182` | One self-reported energy sample |
| `DailyLog` | `entities/metric.py:231` | Consolidated daily log (sleep + energy + tasks) |
| `PomodoroConfig` | `entities/pomodoro.py:48` | Pomodoro recipe (work/break/long-break minutes) |
| `PomodoroRound` | `entities/pomodoro.py:184` | A single round of the state machine |
| `PomodoroSession` | `entities/pomodoro.py:290` | A full session (sequence of rounds) |
| `PolicySetpoints` | `entities/policy.py:95` | Operational regime parameters (PUSH/MAINTAIN/...) |
| `PolicyDecision` | `entities/policy.py:271` | Decision record for a specific date |
| `DecisionRecord` | `entities/policy.py:451` | Append-only audit log of state transitions |
| `AjusteFino` | `entities/ajuste_fino.py:36` | Signed minute adjustment between blocks |
| `DayContext` | `entities/v3.py:45` | Daily context (tipo_dia, orçamento, realizado) |
| `DailyReflection` | `entities/v3.py:104` | OKRs V3 (parar/repetir/big_win/...) |
| `LunchRecord` | `entities/v3.py:164` | Lunch eat+rest+pesado record |
| `TransicaoRegistrada` | `entities/v3.py:220` | T1-T9 transition records with completion flag |

That's **24 entity classes** across **10 files**, but only **14 of them
are wired into the persistent state** (see `cli/state.py:91-106`):
Routine, RoutineLog, TimeBlock, JournalEntry, Habit, SleepRecord,
PomodoroRound, PolicyDecision, PolicySetpoints, AjusteFino, DayContext,
DailyReflection, LunchRecord, TransicaoRegistrada.

---

## 4. 11 commands at a glance

The Typer root lives in `cli/app.py:32`. Each sub-typer is registered
at `cli/app.py:38-49`. The home menu dispatcher is `cli/app.py:52-56`.

| Command group | Subcommands | File | Output |
|---|---|---|---|
| `routine` | `create`, `list`, `update`, `archive` | `cli/commands/routine_cmd.py` | Rich table / `--json` |
| `block` | `create`, `list`, `update`, `delete` | `cli/commands/block_cmd.py` | Rich table / `--json` |
| `journal` | `create`, `list`, `delete` | `cli/commands/journal_cmd.py` | Rich table / `--json` |
| `habit` | `create`, `list`, `log`, `state` | `cli/commands/habit_cmd.py` | Rich table / `--json` |
| `metric` | `sleep`, `energy`, `list` | `cli/commands/metric_cmd.py` | Rich table / `--json` |
| `policy` | `setpoints`, `decisions`, `apply` | `cli/commands/policy_cmd.py` | Rich table / `--json` |
| `report` | `daily`, `weekly` | `cli/commands/report_cmd.py` | Rich Group / `--json` |
| `state` | `show`, `show --json` | `cli/commands/state_cmd.py` | 2x2 KPI grid + activity |
| `reflect` | `morning`, `evening` | `cli/commands/reflect_cmd.py` | OKRs panel |
| `lunch` | `record`, `history` | `cli/commands/lunch_cmd.py` | Rich table |
| `demo` | `seed`, `clear`, `show`, `week`, `dataset` | `cli/commands/demo_cmd.py` | Rich table / stat panel |
| `doctor` | (single command) | `cli/commands/doctor_cmd.py` | Environment diagnostic |
| (root) `home` | (single command) | `cli/app.py:52` | Interactive menu |

That's **12 sub-typers** in total (the brief says 11; the 12th is
`doctor` which is a single-command diagnostic). All commands support
`--json` for machine-readable output. The `home` command launches the
interactive menu (`cli/home.py`).

---

## 5. 10 home menu options

The interactive menu is defined in `cli/home.py:33-46`. Each option
corresponds to a **moment in the day**, not a CRUD operation.

1. **🌅 Iniciar Manhã** — wake up → sleep retroativo → ENTRY routine → workout
2. **💻 Iniciar Tarde** — lunch → pomodoros → foco principal
3. **🌙 Encerrar Dia** — jantar → shutdown → reflexão (OKRs)
4. **⚡ Check-in Rápido** — 30s: registrar energia/foco do momento
5. **📊 Dashboard do Dia** — onde estou · o que está logado · estou no plano?
6. **📈 Relatórios** — Diário · Semanal · Estado consolidado
7. **📚 Dados & Histórico** — Rotinas · Blocos · Journal · Habits · Métricas
8. **⚙️ Política & Ajuste** — Setpoints PUSH/MAINTAIN/REDUCE/RECOVER · Decisões
9. **🎬 Demo & Testes** — Seed 7 dias PAV · Limpar · Show · Run tests
10. **ℹ️ Sistema** — Versão · Constantes · Tipos · Categorias
11. (separator)
12. **🚪 Sair** (`q`)

The menu loop is at `cli/home.py:100-115`. Routing is at
`cli/home.py:134-150`. Each menu choice is implemented as a small
orchestrator function (`_flow_morning`, `_flow_afternoon`, ...,
`_system_info`).

---

## 6. State machine

`operational` has three logical runtime states, governed by the
presence of state files in `~/.time-tasker/`:

```
                ┌────────────────────────────┐
                │  IDLE (production default) │
                │  no JSON files present     │
                └─────────────┬──────────────┘
                              │ TIME_TASKER_DATASET=synthetic
                              │   (env var) OR
                              │   operational demo seed
                              ▼
                ┌────────────────────────────┐
                │  DATASET-LOADED            │
                │  state dir populated       │
                │  by csv_loader / seed      │
                └─────────────┬──────────────┘
                              │ any subcommand that
                              │  upserts a repo
                              ▼
                ┌────────────────────────────┐
                │  USER-LOGGING              │
                │  all writes go to          │
                │  _PersistentRepo.upsert()  │
                │  which calls _dump()       │
                └────────────────────────────┘
```

- **IDLE** — Default. State dir is empty (or doesn't exist). Auto-load
  on import is a no-op unless `TIME_TASKER_DATASET` is set
  (`cli/state.py:112-153`).
- **DATASET-LOADED** — One of the two auto-loaders has run:
  `operational demo seed` (writes via `cli/seed.py`) or
  `TIME_TASKER_DATASET=synthetic` (CSV → repos at
  `cli/state.py:131-152`).
- **USER-LOGGING** — Any subcommand that calls `repo.upsert(...)` or
  `repo.delete(...)` triggers `_dump()` (`cli/state.py:74-80`) and
  persists to the JSON file.

The state file format is the entity model dumped via
`model_dump(mode="json")` (ISO 8601 datetimes, enums as values, sets
as sorted lists). Loading tolerates corruption (`cli/state.py:59-60`).

---

## 7. External integrations

| Integration | Status | Where referenced | Notes |
|---|---|---|---|
| **Taskwarrior** | Interface defined | `core/pomodoro_machine.py` (`PomodoroPlugin` protocol) | No live integration; the Timewarrior/Pomodoro sync point is a `Protocol` and an `InMemoryPomodoroPlugin` for tests |
| **ChromaDB / vector store** | Not present | — | The brief mentions ChromaDB but the codebase does not import it; the RAG indexer is not wired |
| **SQLite** | Built, not wired | `persistence/sqlite.py`, `persistence/migrations/001_initial.sql` | `SqliteRepository` is fully implemented; the live system uses `_PersistentRepo` (JSON) in `cli/state.py:39-86` instead. The migration runner is functional but never called by the boot path. |
| **Obsidian vault** | Not present | — | No vault path resolution; no markdown sync |
| **python-frontmatter** | Dependency | `pyproject.toml:32` | Used by `parsers/` (journal frontmatter, time-block lines) but the frontmatter importers are not called by any of the 11 commands |
| **Rich** | Active | `ui/`, `cli/`, all `commands/` | Sole TUI framework. Console singleton at `ui/__init__.py:43-54`. |
| **Typer** | Active | `cli/app.py:32`, all `commands/` | Sole CLI framework. Root command declared at `pyproject.toml:49` (`operational = "operational.cli.app:app"`). |
| **Pydantic v2** | Active | every `entities/*.py` | All 14 wired entities are frozen `BaseModel` subclasses with `extra="forbid"`. |
| **pytest** | Active | `tests/`, 2755 tests passing | Discovered via `pytest.ini`. No `python -m life.cli test`-style wrapper here; tests run with `pytest` from the project root. |

The only "active" integrations at runtime are Rich, Typer, and
Pydantic. Everything else is either a dependency-of-a-dependency
(`python-frontmatter`, `pyyaml`) or a built-but-unwired module
(`SqliteRepository`, `MigrationRunner`, `PomodoroPlugin`).

---

## 8. Where to go next

- **New contributor** → read [01-MVC-LAYERS.md](01-MVC-LAYERS.md) first.
- **Adding an entity** → read [03-ENTITY-LIFECYCLE.md](03-ENTITY-LIFECYCLE.md).
- **Wiring a new persistence backend** → read [02-PERSISTENCE-LAYER.md](02-PERSISTENCE-LAYER.md).
- **Tracing a single command end-to-end** → read [05-DATA-FLOW.md](05-DATA-FLOW.md).
- **CSV format details** → see [../data/01-CSV-SCHEMA.md](../data/01-CSV-SCHEMA.md).
- **Built-in datasets** → see [../data/02-DATASETS.md](../data/02-DATASETS.md).
- **Full component inventory** (file-by-file) → [06-COMPONENT-DECOMPOSITION.md](06-COMPONENT-DECOMPOSITION.md).
- **Data architecture** (entity graph, JSON contracts, 3 backends, CSV/datasets) → [07-DATA-ARCHITECTURE.md](07-DATA-ARCHITECTURE.md).
- **CLI interface** (Typer + Rich, 12 subcommands, output formatters) → [08-INTERFACE-CLI.md](08-INTERFACE-CLI.md).
- **TUI interface** (Textual + plotext, 7 screens, 5 widgets) → [09-INTERFACE-TUI.md](09-INTERFACE-TUI.md).
- **Rust integration** (Cap'n Proto RPC, ratatui TUI, FFI hot path, shared ring buffer) → [10-RUST-INTEGRATION.md](10-RUST-INTEGRATION.md).
- **Visual debug pipeline** (medic capture → ANSI parse → SVG → diff → MiniMax critic) → [11-VISUAL-DEBUG-PIPELINE.md](11-VISUAL-DEBUG-PIPELINE.md).
- **Architecture narrative** (the big picture, RPC evolution, why this shape) → [12-ARCHITECTURE-NARRATIVE.md](12-ARCHITECTURE-NARRATIVE.md).
- **Evolution timeline** (sprint 0 → sprint 10 → medic Go toolkit) → [13-EVOLUTION-TIMELINE.md](13-EVOLUTION-TIMELINE.md).

---

## 9. medic — the Go devops toolkit

`life-ops/operational/medic/` is a **Go binary** that wraps the Python kernel and provides health gates, code review, visual debugging, and agentic workflow execution for the `operational` project. It is written in a different language **by design** — it cannot import the Python kernel; it interacts with it the way any external tool would: running commands, reading output, asserting exit codes.

```
medic/                          Go binary, 9.7 MB stripped
├── cmd/medic/                  root + 13 subcommands
│   ├── main.go                 14 subcommands registered
│   ├── cmd_review/             medic review — test + lint + complexity gate
│   ├── cmd_issue/              medic issue — GitHub issue triage
│   ├── cmd_pr/                 medic pr — PR review workflow
│   ├── cmd_health/             medic health — coverage/complexity/health gates
│   ├── cmd_visualize/          medic visualize — TTY frame capture
│   ├── cmd_vision/             medic vision — MiniMax VL-01 critic on SVG frames
│   └── cmd_workflow/           medic workflow — YAML workflow engine
├── internal/
│   ├── visual/                 ANSI frame parser + SVG/PNG renderer
│   │   ├── frame.go            Frame, Cell, Cursor, ParseANSIText, pendingWrap
│   │   ├── render.go           RenderSVG, RenderTSV, RenderPNG, attrsString
│   │   ├── diff.go             Diff, Hash (fowler-noll-vo)
│   │   └── *_test.go           22 tests, all passing
│   ├── visioncritic/           MiniMax MMX-CLI wrapper
│   │   ├── critic.go           Critique, Finding, Verdict, ParseCritique
│   │   └── *_test.go           13 tests, all passing
│   ├── agentic/                workflow engine + 13 registered actions
│   │   ├── actions.go          StandardRegistry + vision.critique action
│   │   └── engine.go           Execute, When guards, RetryPolicy
│   ├── store/                  JSON-line event store
│   └── config/                 config file loading
└── examples/
    ├── visual_smoketest/        11 sub-test smoke test (golden frame library)
    └── workflow/
        ├── pr-review.yaml       PR review pipeline (6 steps)
        └── visual-critic.yaml  visual debug pipeline (7 steps, guarded)
```

### medic subcommand tree

```
medic
├── review       run test + mypy + ruff + complexity gate
├── issue        GitHub issue triage (label, milestone, assign)
├── pr           PR review workflow
├── health       coverage / complexity / test-count gates
├── visualize    capture TTY frame → SVG/PNG diff
├── vision       MiniMax VL-01 critic on SVG frame
│   ├── capture  run a binary, snapshot one frame, critique it
│   ├── critique critique a saved frame.svg
│   └── doctor  check mmx + MINIMAX_API_KEY availability
├── workflow     YAML workflow runner
│   ├── list    show registered actions
│   ├── validate validate a workflow YAML
│   └── run     execute a workflow
├── dashboard    ASCII dashboard
├── doctor       environment + deps check
├── debug        low-level diagnostic
└── pat          personal access token manager
```

### medic + operational — the full stack

```
                                    medic (Go)
    ┌─────────────────────────────────────────────────────────────┐
    │                                                             │
    │  medic review          medic health         medic visualize │
    │  ├─ pytest ──────────→ packages/core/      ├─ capture TTY  │
    │  ├─ mypy ───────────→ packages/core/       ├─ ANSI parse  │
    │  ├─ ruff ───────────→ packages/core/       ├─ SVG render  │
    │  └─ complexity gate   19 modules           └─ diff golden  │
    │                                                             │
    │  medic vision critique                                      │
    │  ├─ mmx describe frame.svg "UX critic prompt"              │
    │  ├─ ParseCritique(raw) → Critique{Score, Verdict, []Fdg}  │
    │  └─ findings → markdown / JSON                             │
    │                                                             │
    │  medic workflow run visual-critic.yaml                     │
    │  ├─ health (gate)                                          │
    │  ├─ vision_doctor (gate)                                   │
    │  ├─ capture (medic visualize)                              │
    │  ├─ critique (medic vision critique)  ← guarded           │
    │  ├─ patterns (pattern.scan)                                │
    │  └─ report (synthesise findings)                          │
    └─────────────────────────────────────────────────────────────┘
                           ▲
                           │ subprocess / env var / exit code
                           │
              ┌────────────────────────────────────────────────┐
              │ operational (Python kernel)                    │
              │ packages/core/  entities/  persistence/  meta/│
              │ apps/cli/ (Typer+Rich)  apps/tui/ (Textual)   │
              └────────────────────────────────────────────────┘
```

---

## 10. RPC evolution — from TTY to async RPC

The system has progressed through four architectural phases. See [13-EVOLUTION-TIMELINE.md](13-EVOLUTION-TIMELINE.md) for the full sprint-by-sprint narrative, and [10-RUST-INTEGRATION.md](10-RUST-INTEGRATION.md) for the Cap'n Proto RPC design.

| Phase | What it looks like | Analogy |
|---|---|---|
| **TTY** (sprints 0-1) | Sequential, single-threaded; one command at a time | `vi` + pipe |
| **ANSI stream** (sprints 2-4) | In-band metadata; entities carry their own structure | `tmux` panes |
| **Job/channel** (sprints 5-7) | Background workers; Repository Protocol; CLI/TUI as siblings | `vim 8 jobs` |
| **RPC-decoupled** (sprint 8+, medic) | Go binary wraps Python kernel; separate process boundary | **Neovim Msgpack-RPC** |
| **Future: Cap'n Proto** (planned) | Go headless core + Rust ratatui TUI over Unix socket | Neovim + GUI clients |

