# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this Repository.

## Project Overview

`operational` is the **pure-logic kernel** of the Algorithmic Life OS — a uv workspace Python project implementing the Produtividade Algorítmica Visual (PAV) spec. It is 100% local, 100% standalone, and uses zero LLM/NLP — pure arithmetic algorithms only.

**No UI lives here.** This package contains only business logic. It is consumed by AI agents via MCP tool contracts defined in the parent `life-ops/ikigai/` workspace.

## Workspace Layout

This is a **uv workspace** (single `pyproject.toml` at the root defines the workspace):

```
life-ops/operational/
├── pyproject.toml              # uv workspace root
├── uv.lock
├── ruff.toml
├── packages/
│   └── core/                  # pure logic — NO Rich, NO Typer, NO Textual, NO I/O
│       ├── pyproject.toml
│       └── src/operational/
│           ├── constants.py    # PAVConstants (22 frozen fields)
│           ├── enums.py       # Period, RoutineType, HabitCategory, PolicyState…
│           ├── entities/       # 15 Pydantic v2 frozen models
│           ├── core/          # habit_engine, policy_engine, pomodoro_machine, …
│           ├── persistence/    # Repository Protocol + InMemory + SQLite
│           ├── parsers/        # YAML/frontmatter → Pydantic
│           └── reports/        # Markdown daily/weekly generators
├── tests/                     # pytest tests (unit / integration / property / e2e)
└── docs/                     # architecture, algorithms, design system
```

## Build & Run

```bash
cd life-ops/operational

# Install (uv workspace)
uv sync

# Run tests
uv run pytest

# Single test
uv run pytest packages/core/tests/test_habit_engine.py -v -k "test_qhe"

# Quality gates
uv run ruff check packages/core/src/
uv run ruff format --check packages/core/src/
uv run mypy packages/core/src/
```

## Architecture

### Core Layer (pure logic, zero I/O)

```
src/operational/
├── core/         # Pure business logic — NO Rich, NO Typer, NO Textual, NO I/O
│   ├── habit_engine.py      # H(t) = 1 − e^(−λ·streak), E = R·(1−H(t)), Q_HE
│   ├── policy_engine.py     # 4-state FSM: PUSH → MAINTAIN → REDUCE → RECOVER
│   ├── pomodoro_machine.py  # 8-state pomodoro SM + scenarios
│   ├── sleep_calculator.py  # sleep hours validation
│   ├── budget.py            # time budget classification
│   ├── consolidator.py      # daily/weekly rollups
│   └── services.py          # get_day_snapshot, validate_* helpers
│
├── entities/     # 15 Pydantic v2 frozen models (extra=forbid, no cross-entity imports)
│   ├── routine.py, time_block.py, journal.py, habit.py, metric.py
│   ├── pomodoro.py, policy.py, consolidation.py, ajuste_fino.py, v3.py
│
├── persistence/  # Repository Protocol + InMemory + SQLite + migrations
│
├── parsers/      # YAML/frontmatter → Pydantic
│
└── reports/      # Markdown daily/weekly narrative generators
```

### Core Algorithms (pure arithmetic, no LLM)

- **Habit consistency:** `H(t) = 1 − e^(−λ·streak)`
- **Energy required:** `E = R·(1 − H(t))`
- **Q_HE composite score** (habit engine)
- **PolicyEngine FSM** with 4 states (PUSH/MAINTAIN/REDUCE/RECOVER) and hysteresis
- **8-state Pomodoro state machine** with scenario classifier

### Key Design Rules

- **No LLM, no NLP** — pure arithmetic algorithms only
- **Entities are isolated** — no cross-entity imports in `entities/`
- **Core has zero I/O** — no Rich, no Typer, no file/network calls
- **15 persistent entities** (in-memory repository + SQLite persistence):
  Routine, RoutineLog, TimeBlock, JournalEntry, Habit, SleepRecord,
  PomodoroRound, PolicyDecision, PolicySetpoints, AjusteFino, PortfolioArtifact,
  DayContext, DailyReflection, LunchRecord, TransicaoRegistrada

## Source of Truth

Canonical specs live in sibling directories:
- `life-ops/ikigai/SPEC.md` — IKIGAi meta-brain (5 vectors, 6 heuristics, UEID hierarchy)
- `vibe-ops/base/Produtividade Algorítmica Visual.md` — 815K PAV spec
- `vibe-ops/planning/PRD-02-habit-tracker.md` — habit + Q_HE
- `vibe-ops/planning/PRD-05-metrics-health.md` — metrics & health
- `strategics/Modelagem Operacional.md` — 4 regimes + hysteresis

Engineering docs and ADRs are in `docs/` (architecture, algorithms, data schemas, design system).

## Claude Flow v3 Hook Pipeline

This project participates in the parent `life/` repo's Claude Flow v3 hook chain via `../../.codex/hooks.json`. When hooks are enabled, every Claude Code session in this repo runs through PreToolUse, PostToolUse, PreCompact, SessionStart, and Subagent hooks.

## Common Tasks

```bash
# Add a new entity
# 1. Create entity in packages/core/src/operational/entities/<name>.py (Pydantic v2, frozen, extra=forbid)
# 2. Register in packages/core/src/operational/meta/registry.py

# Run specific quality gate
uv run ruff check packages/core/src/
uv run mypy packages/core/src/
uv run pytest packages/core/tests/ -v
```
