# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`operational` is a **standalone PAV productivity kernel** — a Poetry Python project implementing the Produtividade Algorítmica Visual (PAV) spec. It is 100% local, 100% standalone, and uses zero LLM/NLP — pure arithmetic algorithms only.

**Two interfaces:**
- **Typer CLI** — `pav`, `pav-os`, or `operational` (all equivalent)
- **Textual TUI** — 7 screens (Dashboard, Daily Flow, Habits, Journal, Metrics, Pomodoro Timer, Policy) launched via `pav screen <name>` or `pav` for the home menu

## Build & Run

```bash
cd life-ops/operational

# Install
poetry install

# CLI entry points (all equivalent)
poetry run pav --help
poetry run pav-os --help
poetry run operational --help

# Interactive home menu (v2)
poetry run pav home

# TUI screens
poetry run pav screen dashboard   # jump to specific screen
poetry run pav screen daily_flow
poetry run pav screen habits
poetry run pav screen journal
poetry run pav screen metrics
poetry run pav screen pomodoro
poetry run pav screen policy
poetry run pav screen help

# Run all tests
poetry run pytest

# Single test file
poetry run pytest src/operational/core/tests/test_habit_engine.py -v -k "test_qhe"

# Quality gates
poetry run ruff check src/
poetry run ruff format --check src/
poetry run mypy src/
poetry run verify_sprint
```

## Architecture

### Three-Layer MVC

```
src/operational/
├── core/         # Layer 1: pure business logic — NO Rich, NO Typer, NO I/O
│   ├── habit_engine.py      # H(t) = 1 − e^(−λ·streak), E = R·(1−H(t)), Q_HE
│   ├── policy_engine.py     # 4-state FSM: PUSH → MAINTAIN → REDUCE → RECOVER
│   ├── pomodoro_machine.py  # 8-state pomodoro SM + scenarios
│   ├── sleep_calculator.py  # sleep hours validation
│   ├── budget.py            # time budget classification
│   ├── consolidator.py      # daily/weekly rollups
│   └── services.py          # get_day_snapshot, validate_* helpers
│
├── entities/     # 14 Pydantic v2 frozen models (extra=forbid, no cross-entity imports)
│   ├── routine.py, time_block.py, journal.py, habit.py, metric.py
│   ├── pomodoro.py, policy.py, consolidation.py, ajuste_fino.py, v3.py
│
├── ui/          # Layer 2: Rich component factories — NO Typer, NO business logic
│
├── cli/         # Layer 3: thin Typer controllers — ONLY orchestration, NO logic
│   ├── app.py              # 12 sub-typers registered here
│   ├── home.py / home_v2.py # interactive 10-item menu
│   ├── state.py             # 14 _PersistentRepo instances (JSON flat files)
│   ├── commands/            # one file per subcommand group
│   └── formatters/         # output adapters (JSON, table, etc.)
│
├── persistence/  # Repository Protocol + InMemory + SQLite (JSON is live; SQLite is built-but-unwired)
├── meta/        # entity_registry, factories, validators (UEID format)
├── parsers/     # YAML/frontmatter → Pydantic
└── reports/     # Markdown daily/weekly narrative generators
```

### Core Algorithms (pure arithmetic, no LLM)

- **Habit consistency:** `H(t) = 1 − e^(−λ·streak)`
- **Energy required:** `E = R·(1 − H(t))`
- **Q_HE composite score** (habit engine)
- **PolicyEngine FSM** with 4 states (PUSH/MAINTAIN/REDUCE/RECOVER) and hysteresis
- **8-state Pomodoro state machine** with scenario classifier

### State Machine

`operational` has three logical runtime states based on `~/.time-tasker/` JSON files:

1. **IDLE** — default, no state files
2. **DATASET-LOADED** — `TIME_TASKER_DATASET=synthetic` env var OR `poetry run pav demo seed`
3. **USER-LOGGING** — any write operation triggers `_dump()` to persist

### Key Design Rules

- **No LLM, no NLP** — pure arithmetic algorithms only
- **Entities are isolated** — no cross-entity imports in `entities/`
- **Core has zero I/O** — no Rich, no Typer, no file/network calls
- **CLI is thin** — all logic lives in `core/`, not in `cli/commands/`
- **14 persistent entities** — wired in `cli/state.py:91-106`: Routine, RoutineLog, TimeBlock, JournalEntry, Habit, SleepRecord, PomodoroRound, PolicyDecision, PolicySetpoints, AjusteFino, DayContext, DailyReflection, LunchRecord, TransicaoRegistrada
- **All commands support `--json`** for machine-readable output

### CSV Datasets

Two built-in datasets (`cli/dataset_selector.py`):
- `golden` — curated regression dataset
- `synthetic` — algorithmically generated test data

Load with `TIME_TASKER_DATASET=synthetic poetry run pav state show`.

## TUI Architecture

The Textual TUI (`src/operational/tui/`) has 7 screens and a shared theme:

```
tui/
├── app.py          # PAVApp — top-level App with BINDINGS and SCREENS dict
├── navigation.py   # screen routing helpers
├── theme.py        # get_tui_theme() — color palette
├── charts.py       # plotext-based chart renderers
├── screens/
│   ├── dashboard_screen.py
│   ├── daily_flow_screen.py
│   ├── habits_screen.py
│   ├── journal_screen.py
│   ├── metrics_screen.py
│   ├── pomodoro_timer_screen.py
│   ├── policy_screen.py
│   └── help_screen.py
└── widgets/
    ├── kpi_card.py, regime_bar.py, habit_streak.py
    ├── pomodoro_grid.py, time_block.py, sparkline_chart.py
```

## Source of Truth

Canonical specs live in sibling directories (not in this project):
- `vibe-ops/base/Produtividade Algorítmica Visual.md` — 815K PAV spec
- `vibe-ops/planning/PRD-02-habit-tracker.md` — habit + Q_HE
- `vibe-ops/planning/PRD-05-metrics-health.md` — metrics & health
- `strategics/Modelagem Operacional.md` — 4 regimes + hysteresis

Engineering docs and ADRs are in `docs/` (architecture, algorithms, UX screens, data schemas).

## Common Tasks

```bash
# Add a new entity
# 1. Create entity in src/operational/entities/<name>.py (Pydantic v2, frozen, extra=forbid)
# 2. Register in src/operational/meta/registry.py
# 3. Add _PersistentRepo in src/operational/cli/state.py
# 4. Wire into cli/commands/<name>_cmd.py

# Add a new CLI command
# 1. Create file in src/operational/cli/commands/<name>_cmd.py
# 2. Import and add_typer in src/operational/cli/app.py

# Add a new TUI screen
# 1. Create in src/operational/tui/screens/<name>_screen.py (inherit Screen)
# 2. Register in PAVApp.SCREENS dict in src/operational/tui/app.py
# 3. Add binding in BINDINGS list

# Run specific quality gate
poetry run ruff check src/operational/core/
poetry run mypy src/operational/entities/
```
