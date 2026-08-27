# operational

> **Standalone operational/cybernetic program** — PAV routines, habit engine, Q_HE, policy FSM, journal log, time blocks, metrics & health.
> 100% local · 100% standalone · 0 LLM · 0 NLP · pure arithmetic.

## Quick Start

```bash
uv sync
uv run operational --help
uv run pytest
uv run verify_sprint
```

## Architecture (10 sprints, 30-40 days)

| Sprint | Focus | Duration |
|:-------|:------|:---------|
| 0 | Scaffolding + tooling | 1-2d |
| 1 | Foundation (constants, exceptions, enums, types) | 2-3d |
| 2 | Entities (8 Pydantic modules) | 4-5d |
| 3 | Core Part 1 (sleep, validation, pomodoro, scenarios) | 3-4d |
| 4 | Core Part 2 (habit engine, policy engine) | 4-5d |
| 5 | Persistence (Repository, InMemory, SQLite, migrations) | 3-4d |
| 6 | Parsers + Reports | 2-3d |
| 7 | Meta + CLI | 4-5d |
| 8 | Integration + E2E tests | 3-4d |
| 9 | Documentation + ADRs | 2-3d |
| 10 | Verification + sign-off | 1-2d |

See `docs/ROADMAP.md` for the full sprint-by-sprint breakdown.

## Source of Truth

- `vibe-ops/base/Produtividade Algorítmica Visual.md` (815K) — PAV canonical spec
- `vibe-ops/planning/PRD-02-habit-tracker.md` (10.3K) — habit + Q_HE
- `vibe-ops/planning/PRD-05-metrics-health.md` (7.9K) — metrics & health
- `life-ops/planner/Points_of_premisses-task-habits.md` (11.8K) — math + histerese
- `strategics/Modelagem Operacional.md` (13.2K) — 4 regimes, histerese

## Engineering Conventions

- **Python 3.11+** with `Self`, `Literal`, `match-case`
- **Pydantic v2 strict mode** (sem coerção implícita)
- **mypy --strict** + Protocol + NewType + TypeVar
- **ruff** (lint + format, ALL rules)
- **pre-commit** (gate antes de commit)
- **pytest** com markers (unit, integration, e2e, property)
- **0 except:** genérico (sempre tipos específicos)
- **100% CLI com --json**

## Package Structure

```
packages/core/src/operational/   # Pure logic, zero I/O
├── constants.py         # PAVConstants (frozen, 22 fields)
├── enums.py             # Period, RoutineType, HabitCategory, ...
├── exceptions.py        # 10 PAV error codes + hierarchy
├── types.py             # NewType, Protocol, TypeAlias
├── entities/            # 14 Pydantic v2 models (frozen, extra=forbid)
├── core/                # Pure business logic (no I/O) — habit/policy/sleep/pomodoro
├── persistence/         # Repository Protocol, InMemory, SQLite
├── parsers/             # Frontmatter YAML → Pydantic
├── reports/             # Daily/weekly narrative generators
├── meta/                # Registry, validators, factories
└── analytics/           # Circadian + engine helpers

apps/cli/src/operational/cli/    # Typer CLI
├── app.py               # 12 sub-typers registered here
├── home_v2.py           # Interactive 10-item menu
├── state.py             # 14 _PersistentRepo (JSON flat files)
├── services.py          # Pure data services (get_day_snapshot)
├── seed.py              # Demo dataset seeder
├── dataset_selector.py  # Dataset resolution (golden / synthetic)
├── csv_loader.py        # CSV → entities
├── console.py           # Rich console factory
├── telemetry.py         # Lightweight metric counters
├── commands/            # One file per subcommand group
└── formatters/          # Output adapters (JSON, table, ...)

apps/tui/src/operational/tui/    # Textual TUI (7 screens)
├── app.py               # PAVApp — SCREENS dict + BINDINGS
├── navigation.py        # Screen routing helpers
├── theme.py             # get_tui_theme() — color palette
├── charts.py            # plotext chart renderers
├── screens/             # 7 screens (dashboard, daily_flow, ...)
└── widgets/             # kpi_card, regime_bar, sparkline, ...
```

## Status

| Component | Status |
|:----------|:------:|
| Sprint 0 — Scaffolding | 🟢 |
| Sprint 1 — Foundation | 🟢 |
| Sprint 2 — Entities | 🟢 |
| Sprint 3 — Core Part 1 | 🟢 |
| Sprint 4 — Core Part 2 | 🟢 |
| Sprint 5 — Persistence | 🟢 |
| Sprint 6 — Parsers + Reports | 🟢 |
| Sprint 7 — Meta + CLI | 🟢 |
| Sprint 8 — Integration + E2E | 🟢 |
| Sprint 9 — Documentation + ADRs | 🟢 |
| Sprint 10 — Verification | 🟢 |
| **Total tests** | **2839** |

---

*operational v0.1.0 — 2026-07-01 — Standalone Memory Machine*
