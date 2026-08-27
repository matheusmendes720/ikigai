# operational — Roadmap

## Overview

10-sprint build for the standalone `operational` package (PAV-based productivity kernel).
100% local, 0 LLM, 0 NLP, pure arithmetic.

## Sprint Summary

| Sprint | Focus | Tests | Status |
|:-------|:------|------:|:------:|
| 0 | Scaffolding + tooling | — | 🟢 |
| 1 | Foundation (constants, exceptions, enums, types) | 551 | 🟢 |
| 2 | Entities (8 Pydantic modules) | 820 | 🟢 |
| 3 | Core P1 (sleep, validation, pomodoro, scenario) | 444 | 🟢 |
| 4 | Core P2 (habit engine, policy engine, consolidator) | 432 | 🟢 |
| 5 | Persistence (Repository, InMemory, SQLite, migrations) | 77 | 🟢 |
| 6 | Parsers (frontmatter, time_block) + Reports (daily, weekly) | 40 | 🟢 |
| 7 | Meta (registry, validators, factories) + CLI (Typer) | 64 | 🟢 |
| 8 | Integration (factory↔persistence) + E2E (PAV §8 scenarios) | 31 | 🟢 |
| 9 | Documentation + ADRs | — | 🟢 |
| 10 | Verification (mypy, ruff) + sign-off | — | 🟢 |
| **Total** | | **2518** | 🟢 |

## Module Map — uv Workspace

```
operational/                  # uv workspace root
├── packages/
│   └── core/
│       └── src/operational/ # Core domain (no I/O, no CLI)
│           ├── constants.py
│           ├── exceptions.py
│           ├── enums.py
│           ├── types.py
│           ├── entities/         # 11 Pydantic v2 models (frozen, extra=forbid)
│           ├── core/           # Pure business logic (no I/O)
│           │   ├── sleep_calculator.py
│           │   ├── time_validator.py
│           │   ├── pomodoro_machine.py
│           │   ├── scenario_classifier.py
│           │   ├── habit_engine.py    # H(t), E_req, Q_HE
│           │   ├── policy_engine.py    # 4-state cybernetic FSM
│           │   ├── weekly_aggregator.py
│           │   ├── consolidator.py
│           │   ├── break_calculator.py
│           │   ├── context_switch.py
│           │   ├── journal_segmenter.py
│           │   └── routine_logger.py
│           ├── persistence/    # Repository Protocol + backends
│           ├── parsers/        # YAML/frontmatter → Pydantic
│           ├── reports/        # Markdown generators
│           └── meta/           # EntityRegistry, validators, factories
│
├── apps/
│   ├── cli/
│   │   └── src/operational/ # CLI layer (Typer/Rich)
│   │       ├── cli/         # Typer commands + state repos
│   │       ├── ui/          # Rich component factories
│   │       └── __init__.py  # namespace bridge for operational.*
│   └── tui/
│       └── src/operational/ # Textual TUI (7 screens)
│           └── tui/         # app, screens, widgets, theme, charts
│
└── pyproject.toml        # workspace root (tool config only)
```

## Key Design Decisions

- **Single `entities` table** in SQLite with JSON `data` column — optimal for single-user local use
- **Computed fields excluded** from serialization (`model_dump(exclude=model_computed_fields)`)
- **PAV error codes** — 10 registered codes (ERR_TIME_001–003, ERR_SLEEP_001–002, ERR_MEAL_001, ERR_LIGHT_001, ERR_POMO_001–002, ERR_ROUTINE_001)
- **UEID pattern** `^[a-z]{3,5}_[a-z0-9_]+$` — enforced at type level via `Annotated[str, Field(pattern=...)]`
- **Typer CLI** with `--json` flag on every command
- **No LLM, no NLP, no cloud** — pure deterministic arithmetic (PAV §6 formulas verbatim)
