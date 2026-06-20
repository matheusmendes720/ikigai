# `operational` SPEC

## Purpose

The **operational** package (`life-ops/operational/`) provides standalone CLI tooling and domain logic for personal productivity orchestration. It implements the PAV (Produtividade Algorítmica Visual) spec with pure arithmetic algorithms — no LLM, no NLP.

Crucially, **operational** is completely decoupled from the overarching Algorithmic Life OS orchestrator (`life/`) and the `vibe-ops` cybernetic pipeline. It serves as an independent, modular productivity kernel.

## CLI Surface

The main entry point is the Typer CLI `operational`:

```
operational --help
operational routine create "Morning run" MANHA CORE
operational block create TARDE --label "Deep work"
operational journal create --date 2026-06-07
operational habit create "Drink water" physiological
operational metric sleep --quality 9
operational policy setpoints
operational report daily --date 2026-06-07
```

All commands support `--json` for machine-readable output.

## Architecture

### Module Hierarchy

```
operational/
├── constants.py         # PAVConstants (22 fields, frozen)
├── exceptions.py        # 10 PAV error codes, 7 exception classes
├── enums.py             # 10 StrEnum types
├── types.py             # NewType, Protocol, TypeAlias
├── entities/            # 11 Pydantic v2 models
├── core/                # Pure business logic (no I/O)
├── persistence/         # Repository Protocol + InMemory + SQLite
├── parsers/             # YAML frontmatter, CSV → Pydantic
├── reports/             # Markdown daily/weekly generators
├── meta/                # Entity registry, validators, factories
└── cli/                 # Typer CLI (7 command groups)
```

### Key Technologies

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| CLI | Typer |
| Validation | Pydantic v2 (frozen, extra=forbid) |
| Persistence | SQLite (JSON blob, WAL mode) + InMemory |
| Testing | pytest 9.x, hypothesis, 2518 tests |
| Linting | ruff (ALL rules) |
| Typing | mypy --strict |

## Data Model

All entities are Pydantic v2 models with `frozen=True`, `extra="forbid"`. The SQLite backend stores entities in a single `entities` table with a JSON `data` column, keyed by `(entity_type, id)`.

11 entity types are registered in the `EntityRegistry`:

- `rou` → Routine
- `rlog` → RoutineLog
- `blk` → TimeBlock
- `hab` → Habit (incl. HabitState, QHEMetrics)
- `pmo` → PomodoroSession
- `day` → JournalEntry
- `sle` → SleepRecord
- `log` → DailyLog
- `pol` → PolicySetpoints
- `dec` → DecisionRecord
- `aju` → AjusteFino

## Agent Contract

- AI agents must treat this submodule as an isolated project
- Use strict formatting (ruff ALL, mypy --strict)
- Outputs must support `--json` flags
- Do not import from `life/` or `vibe-ops/`
- Update this SPEC.md when changing domain logic or CLI surface
