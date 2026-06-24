# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## Project Overview

`operational` is a **standalone PAV productivity kernel** — a uv workspace Python project implementing the Produtividade Algorítmica Visual (PAV) spec. It is 100% local, 100% standalone, and uses zero LLM/NLP — pure arithmetic algorithms only.

**Two interfaces:**
- **Typer CLI** — entry points `pav`, `pav-os`, or `operational` (all equivalent). 12 sub-typers under `pav <subcommand>` plus `pav home` (interactive menu) and `pav tui` (Textual launch).
- **Textual TUI** — 7 screens (Dashboard, Daily Flow, Habits, Journal, Metrics, Pomodoro Timer, Policy) + Help modal. Launched via `pav tui` (defaults to dashboard) or `pav tui --screen <name>` to jump to a specific screen.

## Workspace Layout

This is a **uv workspace** (single `pyproject.toml` at the root defines the workspace, individual packages have their own `pyproject.toml`):

```
life-ops/operational/
├── pyproject.toml              # uv workspace root
├── uv.lock                      # resolved deps
├── ruff.toml
├── packages/
│   └── core/                    # pure logic, no Rich, no Typer, no Textual
│       ├── pyproject.toml
│       └── src/operational/
│           ├── constants.py    # PAVConstants (22 frozen fields)
│           ├── enums.py        # Period, RoutineType, HabitCategory, PolicyState…
│           ├── entities/       # 10 Pydantic v2 frozen models
│           ├── core/           # habit_engine, policy_engine, pomodoro_machine, …
│           ├── persistence/    # Repository Protocol + InMemory + SQLite
│           ├── parsers/        # YAML/frontmatter → Pydantic
│           └── reports/        # Markdown daily/weekly generators
├── apps/
│   ├── cli/                    # Typer CLI
│   │   ├── pyproject.toml
│   │   └── src/operational/cli/
│   │       ├── app.py          # 12 sub-typers registered here
│   │       ├── home_v2.py      # interactive 10-item menu
│   │       ├── state.py        # 14 _PersistentRepo (JSON flat files)
│   │       ├── commands/       # one file per subcommand group
│   │       ├── formatters/     # output adapters (JSON, table, etc.)
│   │       └── services.py     # pure data services (get_day_snapshot)
│   └── tui/                    # Textual TUI
│       ├── pyproject.toml
│       └── src/operational/tui/
│           ├── app.py          # PAVApp — top-level App with BINDINGS and SCREENS
│           ├── navigation.py
│           ├── theme.py        # get_tui_theme() — color palette
│           ├── charts.py       # plotext chart builders
│           ├── screens/        # 7 screens + help
│           └── widgets/        # kpi_card, regime_bar, habit_streak, …
├── tests/                      # pytest tests across unit/integration/property/e2e/tui
├── docs/                       # architecture, algorithms, UX screens, design system
└── scripts/
```

## Build & Run

```bash
cd life-ops/operational

# Install (uv or poetry)
uv sync                          # or: poetry install

# CLI entry points (all equivalent)
pav --help
pav-os --help
operational --help

# Interactive home menu (v2)
pav home

# Top-level commands
pav tui                                  # launch TUI on dashboard
pav tui --screen daily_flow             # jump straight to a screen
pav tui --golden                        # load golden dataset for visual debug
pav tui --debug                         # enable Textual dev mode
pav doctor                              # health check

# Subcommand examples
pav routine create "Morning run" MANHA CORE
pav block create TARDE --label "Deep work"
pav journal create --date 2026-06-07 --text "Good day"
pav habit create "Drink water" physiological
pav metric sleep --quality 9
pav report daily --date 2026-06-07
pav demo seed                           # populate 7 days of mock data
pav demo dataset                        # list available datasets

# Run tests
uv run pytest
uv run pytest tests/unit/cli -v
uv run pytest tests/tui -v

# Quality gates
uv run ruff check packages/core/src/
uv run ruff format --check packages/core/src/
uv run mypy packages/core/src/
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
│   ├── tokens.py             # design tokens (SEVERITY, STYLES, REGIME, QUADRANT, Glyph)
│   ├── components_v2.py      # 30+ production-grade v2 widgets
│   ├── mock_profiles.py      # mock data for visual regression testing
│   └── receipt.py            # success/error receipt panel
│
├── cli/         # Layer 3: thin Typer controllers — ONLY orchestration, NO logic
│   ├── app.py                # 12 sub-typers registered here
│   ├── home_v2.py            # interactive 10-item menu (FLUXO/DASHBOARD/DADOS)
│   ├── state.py              # 14 _PersistentRepo instances (JSON flat files)
│   ├── services.py           # pure data services
│   ├── commands/             # one file per subcommand group
│   └── formatters/           # output adapters
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
2. **DATASET-LOADED** — `TIME_TASKER_DATASET=synthetic` env var OR `pav demo seed`
3. **USER-LOGGING** — any write operation triggers `_dump()` to persist

### Key Design Rules

- **No LLM, no NLP** — pure arithmetic algorithms only
- **Entities are isolated** — no cross-entity imports in `entities/`
- **Core has zero I/O** — no Rich, no Typer, no file/network calls
- **CLI is thin** — all logic lives in `core/`, not in `cli/commands/`
- **14 persistent entities** — wired in `apps/cli/src/operational/cli/state.py`:
  Routine, RoutineLog, TimeBlock, JournalEntry, Habit, SleepRecord,
  PomodoroRound, PolicyDecision, PolicySetpoints, AjusteFino,
  DayContext, DailyReflection, LunchRecord, TransicaoRegistrada
- **All commands support `--json`** for machine-readable output

### Design System

The full spec lives in `docs/design-system/DESIGN-SYSTEM.md` (676 lines). All colors,
glyphs, and styles come from `apps/cli/src/operational/ui/tokens.py` — never
hardcode these in components. The v2 component library lives in
`apps/cli/src/operational/ui/components_v2.py` (30+ widgets: `kpi_v2`,
`big_panel`, `regime_bar`, `cartesian_v2`, `pomodoros_v2`, `next_step_v2`,
`error_panel_v2`, `timeline_log`, `kronograma_table`, `policy_actions_table`, etc.).

### CSV Datasets

Two built-in datasets (`apps/cli/src/operational/cli/dataset_selector.py`):
- `golden` — curated regression dataset
- `synthetic` — algorithmically generated test data

Load with `TIME_TASKER_DATASET=synthetic pav state show`.

## TUI Architecture

The Textual TUI has 7 screens and a shared theme:

```
apps/tui/src/operational/tui/
├── app.py          # PAVApp — top-level App with BINDINGS and SCREENS dict
├── navigation.py   # screen routing helpers (TUIState global)
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
│   └── help_screen.py     # ModalScreen — Ctrl+H
└── widgets/
    ├── kpi_card.py        # single-line KPI (icon + label + value + delta)
    ├── regime_bar.py      # PUSH/MAINTAIN/REDUCE/RECOVER bar
    ├── habit_streak.py    # habit name + streak + Q_HE
    ├── pomodoro_grid.py   # 3 sessions × 4 rounds
    ├── time_block.py      # single time block row
    └── sparkline_chart.py # PlotextChart wrapper (sparkline/bar/dual_axis/subplot)
```

**Key bindings (L0):** `q` quit, `Ctrl+H` help (modal), `Esc` back
**Screen switcher (L1):** `1` Dashboard · `2` Daily Flow · `3` Pomodoro · `4` Habits · `5` Metrics · `6` Policy · `7` Journal

The TUI uses `switch_screen()` (pop + push) for top-level navigation and
`push_screen()` only for modal overlays (help). This prevents screen-stack
leaks.

## Source of Truth

Canonical specs live in sibling directories (not in this project):
- `vibe-ops/base/Produtividade Algorítmica Visual.md` — 815K PAV spec
- `vibe-ops/planning/PRD-02-habit-tracker.md` — habit + Q_HE
- `vibe-ops/planning/PRD-05-metrics-health.md` — metrics & health
- `strategics/Modelagem Operacional.md` — 4 regimes + hysteresis

Engineering docs and ADRs are in `docs/` (architecture, algorithms, UX screens, data schemas, design system).

## Common Tasks

```bash
# Add a new entity
# 1. Create entity in packages/core/src/operational/entities/<name>.py (Pydantic v2, frozen, extra=forbid)
# 2. Register in packages/core/src/operational/meta/registry.py
# 3. Add _PersistentRepo in apps/cli/src/operational/cli/state.py
# 4. Wire into apps/cli/src/operational/cli/commands/<name>_cmd.py

# Add a new CLI command
# 1. Create file in apps/cli/src/operational/cli/commands/<name>_cmd.py
# 2. Import and add_typer in apps/cli/src/operational/cli/app.py

# Add a new TUI screen
# 1. Create in apps/tui/src/operational/tui/screens/<name>_screen.py (inherit Screen)
# 2. Register in PAVApp.SCREENS dict in apps/tui/src/operational/tui/app.py
# 3. Add binding in BINDINGS list

# Add a new v2 component
# 1. Add factory function in apps/cli/src/operational/ui/components_v2.py
# 2. Use tokens from apps/cli/src/operational/ui/tokens.py — NEVER hardcode colors
# 3. Add a snapshot test in tests/ui/test_components_v2.py

# Run specific quality gate
uv run ruff check packages/core/src/
uv run mypy packages/core/src/
uv run pytest tests/tui -v
```