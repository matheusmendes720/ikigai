# operational

> **Standalone operational/cybernetic program** — PAV routines, habit engine, Q_HE, policy FSM, journal log, time blocks, metrics & health.
> 100% local · 100% standalone · 0 LLM · 0 NLP · pure arithmetic.

## Quick Start

```bash
poetry install
poetry run operational --help
poetry run pytest
poetry run verify_sprint
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
src/operational/
├── constants.py         # PAVConstants (frozen, 22 fields)
├── exceptions.py        # 10 PAV error codes + hierarchy
├── enums.py             # Period, RoutineType, HabitCategory, ...
├── types.py             # NewType, Protocol, TypeAlias
├── entities/            # Pydantic v2 models
├── core/                # Pure business logic (no I/O)
├── persistence/         # Repository Protocol, InMemory, SQLite
├── parsers/             # Frontmatter YAML → Pydantic
├── reports/             # Daily/weekly/narrative generators
├── meta/                # Registry, validators, factories
└── cli/                 # Typer commands
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
| **Total tests** | **2518** |

---

*operational v0.1.0 — 2026-06-07 — Standalone Memory Machine*
