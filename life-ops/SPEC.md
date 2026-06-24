# `operational` SPEC

## Purpose

The **operational** package (`life-ops/operational/`) provides standalone CLI tooling and domain logic for personal productivity orchestration. It implements the PAV (Produtividade Algorítmica Visual) spec with pure arithmetic algorithms — no LLM, no NLP.

Crucially, **operational** is completely decoupled from the overarching Algorithmic Life OS orchestrator (`life/`) and the `vibe-ops` cybernetic pipeline. It serves as an independent, modular productivity kernel.

## CLI Surface

Three entry points point to the same CLI:

```
pav --help
pav-os --help
operational --help
pav routine create "Morning run" MANHA CORE
pav block create TARDE --label "Deep work"
pav journal create --date 2026-06-07
pav habit create "Drink water" physiological
pav metric sleep --quality 9
pav policy setpoints
pav report daily --date 2026-06-07
```

Textual TUI (7 screens):

```
pav screen dashboard
pav screen daily_flow
pav screen habits
pav screen journal
pav screen metrics
pav screen pomodoro
pav screen policy
```

All commands support `--json` for machine-readable output.

## Architecture — uv Workspace

Three independently versioned packages under a shared uv workspace:

```
operational/                      # uv workspace root (tool config only)
├── packages/
│   └── core/
│       └── src/operational/   # operational-core: pure domain, no I/O
│           ├── constants.py       PAVConstants (22 fields, frozen)
│           ├── exceptions.py      10 PAV error codes, 7 exception classes
│           ├── enums.py           10 StrEnum types
│           ├── types.py           NewType, Protocol, TypeAlias
│           ├── entities/          11 Pydantic v2 models (frozen, extra=forbid)
│           ├── core/              Pure business logic (sleep, habit, policy, pomodoro…)
│           ├── persistence/       Repository Protocol + InMemory + SQLite
│           ├── parsers/          YAML frontmatter, CSV → Pydantic
│           ├── reports/            Markdown daily/weekly generators
│           └── meta/              Entity registry, validators, factories
│
├── apps/
│   ├── cli/
│   │   └── src/operational/   # operational-cli: Typer/Rich CLI
│   │       ├── cli/          Typer commands (routine, block, journal, habit, metric, policy, report, state, reflect, lunch, block, doctor, demo)
│   │       ├── ui/            Rich component factories
│   │       └── __init__.py    namespace bridge (pkgutil.extend_path)
│   └── tui/
│       └── src/operational/   # operational-tui: Textual TUI
│           └── tui/            7 screens, widgets, theme, charts
│
└── pyproject.toml            # workspace root (no [project] — tool config only)
```

Dependency chain: `tui → cli → core`

### Key Technologies

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| Build | hatchling + uv workspace |
| CLI | Typer 0.12+ / Rich 13.7+ |
| TUI | Textual 0.8+ / plotext 4.2+ |
| Validation | Pydantic v2 (frozen, extra=forbid) |
| Persistence | SQLite (JSON blob, WAL mode) + InMemory |
| Testing | pytest 9.x, hypothesis, 2812 tests |
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
