# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## Project Overview

**Algorithmic Life OS** — A personal productivity orchestration system written in Python. It acts as a CLI hub (`life`) that integrates domain "centrals" (task, knowledge, research) with daily/weekly handlers and a plugin system.

**Active development has one app:** `life-ops/operational/` (the PAV productivity kernel). Everything else is either a supported integration (`vibe-ops/`, `taskwarrior/`) or documentation (`strategics/`, `docs/`, `vibe-ops/planning/`, `vibe-ops/architecture/`).

| Subdir | Role |
|--------|------|
| `life-ops/operational/` | **Active development** — PAV productivity kernel (uv workspace: `packages/core`, `apps/cli`, `apps/tui`) |
| `vibe-ops/` | R&D cybernetic engine — Target-Sensor-Adjuster loop, Obsidian ↔ SQLite ↔ Taskwarrior |
| `taskwarrior/` | Taskwarrior binary + scripts + config consumed by the `task` central |
| `strategics/` | PT-BR strategy documents (frameworks, models, operational analysis) |
| `docs/` | Master reading index (`ÍNDICE PROGRESSIVO.md`) |
| `diagrams/` | Mermaid source + rendered PNGs |
| `logs/` | Runtime logs |

## Running the Code

### `life/` — Root CLI hub

From repo root (requires parent dir on `PYTHONPATH`, or an editable install):

```bash
python -m life.cli --help

# Handlers
python -m life.cli daily run [--skip-task]
python -m life.cli weekly run [--skip-review] [--skip-metrics]

# Centrals
python -m life.cli task today
python -m life.cli task daily-review
python -m life.cli task weekly-review
python -m life.cli task metrics
python -m life.cli knowledge read
python -m life.cli knowledge mindmap-phase0
python -m life.cli research map --depth 2
python -m life.cli research search --backend vector

# Plugins & config
python -m life.cli submodules
python -m life.cli health
python -m life.cli config-show [--path] [--json]

# Tests
python -m life.cli test           # discover + run pytest across submodules
python -m life.cli test --list    # list discovered test dirs
python -m life.cli test -s <name> # run one submodule's tests
```

All canonical source files use `life.cli.config` / `life.cli.log`. The root `__init__.py` enables `python -m life.cli`.

### `life-ops/operational/` — PAV Productivity Kernel

A **uv workspace** with three packages: `packages/core` (pure logic), `apps/cli` (Typer CLI), `apps/tui` (Textual TUI).

```bash
cd life-ops/operational

# Install (uv or poetry)
uv sync          # or: poetry install

# CLI entry points (all equivalent)
pav --help
pav-os --help
operational --help

# Interactive menu
pav home

# TUI screens
pav screen dashboard    # jump to specific screen
pav screen daily_flow
pav screen habits
pav screen journal
pav screen metrics
pav screen pomodoro
pav screen policy

# Quality gates
uv run pytest
uv run ruff check packages/core/src/
uv run ruff format --check packages/core/src/
uv run mypy packages/core/src/
uv run verify_sprint

# Single test
uv run pytest packages/core/src/operational/core/tests/test_habit_engine.py -v -k "test_qhe"
```

**Quality gates:** ruff ALL rules, mypy --strict, 2518 tests (unit/integration/property/e2e markers).

### `vibe-ops/` — Cybernetic Engine

```bash
cd vibe-ops

# argparse CLI
python src/main.py run-daily [--date YYYY-MM-DD]
python src/main.py status
python src/main.py gaps
python src/main.py sync --vault-path <path>

# Typer+Rich CLI
python src/vibe_cli.py sync_file [--vault-path]
python src/vibe_cli.py hybrid_search "query"
python src/vibe_cli.py gaps
python src/vibe_cli.py debt_dashboard

# Rust TUI
cd vibeops-tui && cargo run
```

`run_loop.ps1` is the Windows launcher for the daily loop.

---

## Architecture

### Root CLI — Central-Handler Pattern

```
life/
├── centrals/    domain hubs: task, knowledge, research
├── handlers/    daily.py, weekly.py — orchestrate centrals as subprocesses
├── plugins/     plugin protocol, loader, builtin health_check
└── cli/         Typer app, config, logging, test runner
```

**`centrals/`** expose `typer.Typer` sub-apps mounted by `cli/cli.py`. They delegate to standalone submodules:

| Central | Delegate |
|---------|----------|
| `task` | Taskwarrior binary + `taskwarrior/scripts/` |
| `knowledge` | `leitura`, `mindmaps`, `notes` (standalone Python CLIs) |
| `research` | `research` (standalone Python CLI) |

**`handlers/`** (`daily.py`, `weekly.py`) run centrals via `python -m life.cli <central> <cmd> --json` — recursively invoking the CLI. This makes handlers double as integration tests.

**`BaseCentral`** (`centrals/base.py`):
```python
run_cli(cwd: Path, module: str, args: list[str], json_out: bool = True) -> dict[str, Any]
# Returns {ok, stdout, stderr, data, error?}
```

### Plugin System

Plugins implement `PluginProtocol` (`plugins/protocol.py`):
```python
def register(self, app: typer.Typer) -> None: ...
def before_daily(self, context) -> Optional[dict]: ...  # planned but not yet called
def after_daily(self, context) -> None: ...
def before_weekly(self, context) -> Optional[dict]: ...
def after_weekly(self, context) -> None: ...
```

`plugins/loader.py` discovers plugins from `cfg.plugin_dirs`. Entry point is a module-level `PLUGIN`, `plugin`, or `Plugin` attribute. `register_plugins(app)` is called at import time in `cli/cli.py`.

`plugins/builtin/health_check.py` is the only built-in — registers the `health` command.

### Config — `cli/config.py`

`LifeConfig` / `load_config()` loads `config/life.yaml` if present, else hardcoded defaults.

Key fields: `root`, `log_dir`, `plugin_dirs`, `submodules` (name → path dict), `task_scripts`, `notes_store`.

`get_submodule_path(name)` returns `{"ok": False, "error": "... not found"}` for unknown submodules instead of raising.

### `life-ops/operational/` — uv Workspace Structure

```
life-ops/operational/
├── pyproject.toml              # uv workspace root
├── packages/
│   └── core/
│       ├── pyproject.toml
│       └── src/operational/
│           ├── constants.py    PAVConstants (22 frozen fields)
│           ├── enums.py       Period, RoutineType, HabitCategory, PolicyState …
│           ├── types.py       NewType, Protocol, TypeAlias
│           ├── exceptions.py  10 PAV error codes
│           ├── entities/      10 Pydantic v2 models (frozen, extra=forbid)
│           ├── core/          Pure logic: habit_engine, policy_engine,
│           │                  pomodoro_machine, sleep_calculator,
│           │                  scenario_classifier, consolidator …
│           ├── persistence/   Repository Protocol + InMemory + SQLite + migrations
│           ├── parsers/      YAML/frontmatter → Pydantic
│           ├── reports/      Markdown daily/weekly generators
│           └── meta/         EntityRegistry, validators, factories
├── apps/
│   ├── cli/
│   │   ├── pyproject.toml   # pav, pav-os, operational entry points
│   │   └── src/operational/cli/
│   │       ├── app.py        12 sub-typers
│   │       ├── home_v2.py    interactive 10-item menu
│   │       ├── state.py      14 _PersistentRepo (JSON flat files)
│   │       ├── csv_loader.py
│   │       └── commands/     one file per subcommand group
│   └── tui/
│       ├── pyproject.toml
│       └── src/operational/tui/
│           ├── app.py        PAVApp — SCREENS dict + BINDINGS
│           ├── theme.py      get_tui_theme()
│           ├── charts.py     plotext chart renderers
│           ├── screens/      7 screens
│           └── widgets/      kpi_card, regime_bar, sparkline …
├── tests/                     2518 pytest tests (unit/integration/property/e2e)
├── docs/                     ADR + sprint reports
└── scripts/                  verify_sprint, manual_test.py
```

**Core algorithms (pure arithmetic, no LLM):**
- `H(t) = 1 − e^(−λ·streak)` — habit consistency model
- `E = R·(1 − H(t))` — energy required
- Q_HE composite score
- 4-state PolicyEngine FSM: PUSH → MAINTAIN → REDUCE → RECOVER
- 8-state Pomodoro state machine + scenario classifier

### `vibe-ops/` — Cybernetic Architecture

Target-Sensor-Adjuster loop (`src/cybernetics/daily_loop.py`):

```
TARGET → SENSOR → ADJUSTER → PERSIST → SYNC → INDEX
```

| Stage | Module | Responsibility |
|-------|--------|----------------|
| TARGET | `IkigaiScorer` | Reads IKIGAi profile, emits `qhe_target`, `c_comp_target` |
| SENSOR | aggregates | `study_sessions.hours`, `habit_states` (24h window) |
| ADJUSTER | `PolicyEngine` | 4-state FSM → `PolicyDecision` |
| PERSIST | writes | `PolicyDecision` row to `policy_decisions` table |
| SYNC | `SyncEngine` | Obsidian ↔ SQLite ↔ Taskwarrior (idempotent, `upstream_id` SHA-256) |
| INDEX | `HybridRAGIndexer` | Re-vectors vault into SQLite-vec / ChromaDB |

**PolicyEngine states:**

| State | hardwork_budget | pause_min | sleep_target | QHE target |
|-------|----------------|-----------|--------------|------------|
| PUSH | 4.0 h | 10 min | 7.5 h | 0.85 |
| MAINTAIN | 2.5 h | 15 min | 8.0 h | 0.65 |
| REDUCE | 1.5 h | 20 min | 8.5 h | 0.45 |
| RECOVER | 0.5 h | 30 min | 9.0 h | 0.25 |

Severity (CRITICAL/HIGH/MEDIUM/LOW) computed from infractions + hours_deviation + consistency. Transitions have hysteresis — no upward promotion without sustained performance.

**SyncEngine** (`src/middleware/sync_engine.py`) — only module touching all three systems:
- `sync_obsidian_to_sqlite()` — parses Markdown frontmatter → `planning_entities`
- `sync_sqlite_to_taskwarrior()` — injects TW tasks with `upstream_id` UDA + policy tags
- `sync_taskwarrior_to_sqlite()` — marks `roadmap_sync` rows completed on TW task close

**UEID format:** `<CLUSTER>:<ENTITY>:<ID>` e.g. `study:topic:st_python_01`

**Vibe-ops src/ layout:**

| Subdir | Purpose |
|--------|---------|
| `main.py` | argparse CLI: `run-daily`, `status`, `gaps`, `sync` |
| `vibe_cli.py` | Typer+Rich CLI: `sync_file`, `hybrid_search`, `gaps`, `debt_dashboard` |
| `cybernetics/` | `CyberneticDailyLoop`, `BinaryKnowledgeTree`, `GapSearchEngine` |
| `pipeline/` | `policy_engine`, `rag_indexer`, `mvl_orchestrator`, `enrichment_engine`, `cognitive_debt_tracker`, `sync_orchestrator`, `reverse_sync`, `ikigai_scorer` |
| `models/` | Pydantic entities: temporal, habit, study, project, metric, policy, rag, ikigai, knowledge, feedback, contracts |
| `storage/` | SQLite/SQLAlchemy ORM, `sqlite-vec`, ChromaDB adapter, UEID manager |
| `middleware/` | `SyncEngine` |
| `embeddings/` | OpenAI / local / hash-moq provider abstraction |
| `contracts/` | YAML/JSON schemas + Pydantic sync payloads |
| `migrations/` | SQL schema + Alembic-style Python migrations |

**Rust TUI** (`vibeops-tui/`): ratatui dashboard polling `../vibe_ops.db` every second.

---

## Testing Strategy

**Root package:** No test directory at root. Test coverage lives in submodules. Use `python -m life.cli test` to discover and run tests across all submodule paths.

**`life-ops/operational/tests/`:** 2518 pytest tests with markers: `unit`, `integration`, `property`, `e2e`.

**`vibe-ops/tests/`:** pytest suite with in-memory SQLite fixtures and mocked ChromaDB. **`vibe-ops/scratch/`** has informal `test_*.py` exploration scripts — **not** part of the official test suite.

**Adding tests:** Place them in the appropriate `tests/` directory and use pytest fixtures. Mock external services (ChromaDB, Taskwarrior, etc.).

---

## Security & Deployment

- **Fully local / air-gapped by design.** No API keys, OAuth, or network services required for core operation.
- SQLite databases (`vibe_ops.db`, `test_vibe.db`) and ChromaDB (`chroma_db/`) reside inside the working directory.
- No secrets management infrastructure present.
- Deployment is manual: run PowerShell scripts or Python modules directly on the host machine.
- The Rust TUI reads from `../vibe_ops.db` relative to its executable location.

---

## Important Rules

### `life-ops/operational/` — Standalone Rule
- **Must remain decoupled.** No imports from root `life/` or `vibe-ops/`.
- Any new CLI command must support `--json` for machine-readable output.
- When modifying domain logic or CLI features, update `life-ops/operational/SPEC.md`.
- **Quality gates:** 2518 tests, ruff ALL rules, mypy --strict, pre-commit hooks.

### `vibe-ops/` — Append-Only Rule
- **Never delete, prune, or rewrite** existing sessions, topics, sub-topics, or paragraphs.
- Re-organization is allowed only if every pre-existing string survives intact.
- **Refactor Protocol:** If asked to refactor, stop → propose Action Plan → wait for Approval Gate → only then mutate.

### General
- Prefer **Typer** for new CLI surfaces in `life/`.
- Support `--json` on all new commands wherever feasible.
- Centrals should stay thin — delegate to submodules or scripts.
- Use `from __future__ import annotations` at top of Python files.
- Error collection (not abort) — handlers collect all errors and report at end rather than short-circuiting.

---

## File Roles Quick Reference

| File / Dir | Purpose |
|------------|---------|
| `cli/cli.py` | Main Typer app; registers centrals, handlers, plugins |
| `cli/config.py` | `LifeConfig` dataclass; YAML + env loading |
| `cli/log.py` | Structured logging (plain or JSON) to file + stderr |
| `cli/test_runner.py` | Pytest discovery & runner across submodules |
| `centrals/base.py` | `BaseCentral` with `run_cli()` subprocess helper |
| `centrals/task.py` | Task central → Taskwarrior binary |
| `centrals/knowledge.py` | Knowledge central → `leitura`, `mindmaps`, `notes` |
| `centrals/research.py` | Research central → `research` CLI |
| `plugins/protocol.py` | `PluginProtocol` (register + lifecycle hooks) |
| `plugins/loader.py` | File-system plugin discovery |
| `plugins/builtin/health_check.py` | Built-in: registers `health` command |
| `handlers/daily.py` | Orchestrates centrals for daily run |
| `handlers/weekly.py` | Orchestrates centrals for weekly run |
| `vibe-ops/src/main.py` | Cybernetic CLI entry (argparse) |
| `vibe-ops/src/vibe_cli.py` | High-level Typer+Rich surface |
| `vibe-ops/src/cybernetics/daily_loop.py` | Target-Sensor-Adjuster loop |
| `vibe-ops/src/pipeline/policy_engine.py` | 4-state policy FSM |
| `vibe-ops/src/middleware/sync_engine.py` | Obsidian ↔ SQLite ↔ Taskwarrior |
| `vibe-ops/src/storage/schema.sql` | Live database schema |
| `vibe-ops/migrations/` | SQL + Alembic-style schema migrations |
| `life-ops/operational/packages/core/src/operational/core/` | Pure arithmetic business logic |
| `life-ops/operational/apps/cli/src/operational/cli/` | Typer CLI controllers |
| `life-ops/operational/apps/tui/src/operational/tui/` | Textual TUI (7 screens) |

---

## Cluster Doc Quick Index

| File | Domain | Language |
|------|--------|----------|
| `CONCEPTUAL_MODEL.md` | Tensão → Comportamento → Solução (5 tensões, 4 regimes) | PT-BR |
| `SYSTEMS_TOPOLOGY.md` | Middleware map + data flow | PT-BR |
| `CLUSTER_PLAN.md` | Plan + Personal Productivity (rotinas, blocos, pomodoro) | PT-BR |
| `CLUSTER_PROJ.md` | Project Execution (PMO ↔ Taskwarrior) | PT-BR |
| `CLUSTER_STUDY.md` | Studies & Lifelong Learning (PKM + cognitive prerequisites) | PT-BR |
| `ARCHITECTURE_INDEX.md` | Master index — all layers, 50+ cross-refs | PT-BR/EN |

For ADRs, PRDs, specs see `ARCHITECTURE_INDEX.md §3–§5`.

---

<!-- gitnexus:start -->
## Code Intelligence — GitNexus

This project is indexed by GitNexus as **life** (12741 symbols, 18843 relationships, 173 execution flows).

### When to Use GitNexus vs. Standard Tools

| Situation | Tool |
|-----------|------|
| "Where is X used?" / "What calls this function?" | `impact()` — blast radius analysis |
| "What execution flows involve X?" | `query({query: "concept"})` — ranked process groups |
| "Walk me through how X works, start to finish" | `context({name: "symbolName"})` — full call graph |
| "Find a file by name" | Glob / Grep |
| "Find text inside files" | Grep |
| Before **any** edit | Run `impact()` first |

**Before editing any symbol:** `impact({target: "symbolName", direction: "upstream"})` and report blast radius. If it returns HIGH or CRITICAL risk, do not proceed without user approval.

**Before committing:** `detect_changes()` to verify only expected symbols and execution flows are affected. For regression review: `detect_changes({scope: "compare", base_ref: "main"})`.

Never rename symbols with find-and-replace — use `rename` which understands the call graph.

### GitNexus Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/life/context` | Codebase overview, check index freshness |
| `gitnexus://repo/life/clusters` | All functional areas |
| `gitnexus://repo/life/processes` | All execution flows |
| `gitnexus://repo/life/process/{name}` | Step-by-step execution trace |

| Task | Skill |
|------|-------|
| Architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root. No `.gitnexus/run.cjs`? Try `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

<!-- gitnexus:end -->
