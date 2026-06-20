# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Algorithmic Life OS** — A personal productivity orchestration system written in Python. It is a CLI hub (`life`) that integrates domain "centrals" (task, finance, knowledge, research) with daily/weekly handlers and a plugin system. The repo also contains two major submodules and an active R&D workspace:

- `life-ops/operational/`: **Standalone PAV productivity kernel** — a Poetry project with a Textual TUI (7 screens), pure arithmetic algorithms, 2518 tests, and strict quality gates (ruff ALL, mypy --strict). **Must remain decoupled** from `life/`.
- `vibe-ops/`: **Cybernetic control center** — a Target-Sensor-Adjuster loop that orchestrates Obsidian ↔ SQLite ↔ Taskwarrior, with hybrid RAG indexing and a Rust TUI dashboard.
- `time-tasker/`: **Deployment snapshot** — a duplicate copy of `life/`, `strategics/`, and `taskwarrior/`. **Treat the root as canonical.** Do not edit files inside it unless explicitly asked to update that snapshot.
- `taskwarrior/`: Portable Taskwarrior stack (config, scripts, docs, hooks) consumed by the `task` central.

## Technology Stack

| Layer | Technology |
|-------|------------|
| CLI framework | Typer (root `life/`), Textual (operational/), argparse (vibe-ops), Rust ratatui (TUI) |
| Packaging | Poetry (`life-ops/`), uv (`vibe-ops/` — `uv.lock` present) |
| ORM / Data | SQLAlchemy 2.0, SQLite, ChromaDB, `sqlite-vec` (NumPy fallback) |
| Validation | Pydantic v2 |
| Task management | Taskwarrior binary + `tasklib` (Python) |
| Markdown parsing | `python-frontmatter` |
| Embeddings | Local / OpenAI provider abstraction |
| TUI | Rust + `ratatui` + `crossterm` + `rusqlite` (vibe-ops); Textual (operational/) |
| Shell automation | PowerShell (`.ps1`) scripts |

No `requirements.txt` or `setup.py` exists at the repository root. The root package is run via `python -m life.cli`.

## Running the Code

### Main CLI — `life/`

From repo root (requires parent dir on `PYTHONPATH`, or an editable install):

```bash
python -m life.cli --help

# Core commands
python -m life.cli daily run [--skip-task] [--skip-finance]
python -m life.cli weekly run [--skip-review] [--skip-finance] [--skip-metrics]
python -m life.cli task today
python -m life.cli task daily-review
python -m life.cli task weekly-review
python -m life.cli task metrics
python -m life.cli finance track
python -m life.cli finance report --period day|week
python -m life.cli finance simulate --scenario
python -m life.cli finance derivatives
python -m life.cli knowledge read
python -m life.cli knowledge mindmap-phase0
python -m life.cli research map --depth 2
python -m life.cli research search --backend vector
python -m life.cli submodules
python -m life.cli health           # builtin plugin — checks submodule/task_scripts existence
python -m life.cli config-show [--path] [--json]
```

**On imports:** The codebase is in a transitional state. Some files import from `life.cli.config` / `life.cli.log`, while others still import from `life.config` / `life.log`. The root `__init__.py` was deleted from git; restoring it may be needed for `python -m life.cli` to work depending on `PYTHONPATH` setup. Do not arbitrarily unify these imports unless you are explicitly refactoring the import graph.

### Tests

There is **no Makefile, `pytest.ini`, or `tox`**. Tests are discovered and run through the CLI itself:

```bash
python -m life.cli test           # Run pytest across all submodules with tests/
python -m life.cli test --list    # List discovered test directories
python -m life.cli test -s <name> # Run only one submodule
```

`cli/test_runner.py` discovers submodules containing `tests/` or `test_*.py` and runs `pytest` in each. Official tests live in submodules (e.g., `vibe-ops/tests/`). **`vibe-ops/scratch/`** contains informal `test_*.py` scripts for exploration — these are **not** part of the official test suite.

### `life-ops/operational/` — Standalone PAV Productivity Kernel

A Poetry project at `life-ops/operational/` implementing the PAV (Produtividade Algorítmica Visual) spec. Fully standalone — no imports from root `life/` or `vibe-ops/`. Contains a **Textual TUI** with 7 screens (Dashboard, Daily Flow, Habits, Journal, Metrics, Pomodoro Timer, Policy).

```bash
cd life-ops/operational

poetry install
poetry run pav --help          # Main TUI launcher (pav, pav-os, operational all point to the same app)
poetry run pav screen <name>   # Jump to a specific screen (dashboard|daily|habits|journal|metrics|pomodoro|policy)
poetry run pav log             # Structured JSON log viewer

# Quality gates
poetry run pytest
poetry run ruff check src/
poetry run ruff format --check src/
poetry run mypy src/
poetry run verify_sprint       # Custom sprint-verification script

# Run a single test file
poetry run pytest src/operational/cli/tests/test_app.py -v
poetry run pytest src/operational/core/tests/test_habit_engine.py -v -k "test_qhe"
```

**Quality gates:** ruff ALL rules, mypy --strict, 2518 tests across unit/integration/property/e2e markers.

### `vibe-ops/` — Cybernetic CLI

Uses uv (lockfile present). Run the cybernetic loop or TUI:

```bash
cd vibe-ops

# Python CLI (argparse main.py)
python src/main.py run-daily [--date YYYY-MM-DD]
python src/main.py status
python src/main.py gaps
python src/main.py sync --vault-path <path>

# Typer+Rich CLI (high-performance surface)
python src/vibe_cli.py sync_file [--vault-path]
python src/vibe_cli.py hybrid_search "query"
python src/vibe_cli.py gaps
python src/vibe_cli.py debt_dashboard

# Rust TUI (live dashboard)
cd vibeops-tui && cargo run
```

`run_loop.ps1` is the Windows launcher for the daily loop.

---

## Architecture

### Root CLI — Central-Handler Pattern

```
centrals/    ← domain hubs: task, finance, knowledge, research
handlers/    ← daily.py, weekly.py — orchestrate centrals as subproceses
plugins/     ← plugin system (protocol, loader, builtin health_check)
cli/         ← main Typer app, config, logging, test runner
```

**`centrals/`** are domain hubs. Each exposes a `typer.Typer` sub-app mounted by `cli/cli.py`. They delegate to standalone submodules:
- `task` → Taskwarrior binary (`task`) + Bash/Python scripts in `taskwarrior/scripts/`
- `finance` → `fin_ops` CLI (run via `BaseCentral.run_cli`)
- `knowledge` → `leitura`, `mindmaps`, `notes` CLIs (each standalone Python)
- `research` → `research` CLI (standalone Python)

**`handlers/`** (`daily.py`, `weekly.py`) are the "do my day/week" orchestration commands. They run centrals via `python -m life.cli <central> <cmd> --json` — recursively invoking the CLI. This makes handlers double as integration tests for the entire surface.

**`BaseCentral`** (`centrals/base.py`) — the ABC that all centrals (except `task`) inherit or use via `run_cli()`:

```python
run_cli(cwd: Path, module: str_cli, args: list[str], json_out: bool = True) -> dict[str, Any]
# Returns {ok, stdout, stderr, data, error?}
```

### Plugin System

Plugins implement `PluginProtocol` (`plugins/protocol.py`):

```python
def register(self, app: typer.Typer) -> None: ...   # required
def before_daily(self, context) -> Optional[dict]: ... # lifecycle hooks
def after_daily(self, context) -> None: ...
def before_weekly(self, context) -> Optional[dict]: ...
def after_weekly(self, context) -> None: ...
```

`plugins/loader.py` discovers plugins from `cfg.plugin_dirs` by file convention (`*.py` or `__init__.py` packages). The entry point is a module-level attribute named `PLUGIN`, `plugin`, or `Plugin` — either a `PluginProtocol` instance or a zero-arg callable returning one. `register_plugins(app)` is called at the bottom of `cli/cli.py` at import time.

**The lifecycle hooks (`before_daily`, `after_daily`, etc.) are declared but not yet called by `handlers/daily.py` / `handlers/weekly.py`.** This is the planned extension point when someone wants plugins to react to flow execution.

**`plugins/builtin/health_check.py`** is the only built-in. Registers the `health` command that checks whether all `cfg.submodules` and `cfg.task_scripts` paths exist.

### Config — `cli/config.py`

`LifeConfig` / `load_config()` is the single source of truth. Loads `config/life.yaml` if present, otherwise hardcoded defaults.

Key fields: `root`, `log_dir`, `log_level`, `log_json`, `plugin_dirs`, `submodules` (dict of name → path), `task_scripts`, `finance_store`, `notes_store`, `extra` (catch-all for unknown YAML keys).

`get_submodule_path(name)` resolves a submodule path relative to `root`. Unknown submodules return `{"ok": False, "error": "... not found"}` instead of raising.

### `life-ops/operational/` — PAV Productivity Kernel

Located at `life-ops/operational/src/operational/`, this is the standalone PAV implementation. Key directories:

| Subdir | Purpose |
|--------|---------|
| `constants.py` | PAVConstants (22 frozen fields) |
| `enums.py` | Period, RoutineType, HabitCategory, PolicyState … |
| `types.py` | NewType, Protocol, TypeAlias, UEID_PATTERN |
| `entities/` | 11 Pydantic v2 models (frozen, extra=forbid) |
| `core/` | Pure business logic: sleep_calculator, habit_engine, policy_engine, pomodoro_machine, scenario_classifier, consolidator |
| `persistence/` | Repository Protocol + InMemory + SQLite (JSON blob, WAL) + MigrationRunner |
| `parsers/` | YAML frontmatter → Pydantic; CSV/dict → TimeBlock |
| `reports/` | Markdown daily/weekly narrative generators |
| `meta/` | EntityRegistry (11 prefixes), validators, factories |
| `cli/` | Textual TUI (7 screens: dashboard, daily_flow, habits, journal, metrics, pomodoro_timer, policy) + Typer commands |

**Core algorithms (pure arithmetic, no LLM):**
- `H(t) = 1 − e^(−λ·streak)` — habit consistency model
- `E = R·(1 − H(t))` — energy required
- Q_HE composite score (habit engine)
- 4-state PolicyEngine FSM: PUSH → MAINTAIN → REDUCE → RECOVER

### Vibe-Ops — Cybernetic Architecture

`vibe-ops/` implements a **Target-Sensor-Adjuster** cybernetic loop formalizing the study+dev clusters over a hybrid RAG stack.

**The loop** (`src/cybernetics/daily_loop.py` → `CyberneticDailyLoop.execute_daily_cycle()`):

```
TARGET  →  SENSOR  →  ADJUSTER  →  PERSIST  →  SYNC  →  INDEX
```

1. **TARGET** (`IkigaiScorer`) — reads IKIGAi profile, emits `qhe_target`, `c_comp_target`
2. **SENSOR** — aggregates last 24 h: `study_sessions.hours`, `habit_states` (consistency, infractions), compares against baseline
3. **ADJUSTER** (`PolicyEngine`) — four-state state machine → `PolicyDecision`
4. **PERSIST** — writes `PolicyDecision` row to `policy_decisions` table
5. **SYNC** (`SyncEngine`) — Obsidian ↔ SQLite ↔ Taskwarrior bidirectional
6. **INDEX** (`HybridRAGIndexer`) — re-vectors Obsidian vault into SQLite-vec/ChromaDB

**`PolicyEngine` state machine** (`src/pipeline/policy_engine.py`):

| State | hardwork_budget | pause_min | sleep_target | QHE target | C_comp target |
|-------|-----------------|-----------|--------------|------------|---------------|
| PUSH | 4.0 h | 10 min | 7.5 h | 0.85 | 0.90 |
| MAINTAIN | 2.5 h | 15 min | 8.0 h | 0.65 | 0.85 |
| REDUCE | 1.5 h | 20 min | 8.5 h | 0.45 | 0.75 |
| RECOVER | 0.5 h | 30 min | 9.0 h | 0.25 | 0.65 |

Severity (CRITICAL/HIGH/MEDIUM/LOW) is computed from infractions + hours_deviation + consistency. Transitions have hysteresis — no upward promotion without sustained performance.

**`SyncEngine`** (`src/middleware/sync_engine.py`) — the only module that touches all three systems. Idempotency via a 12-char `upstream_id` (SHA-256 prefix). Three sync pathways:
- `sync_obsidian_to_sqlite()` — parses Markdown frontmatter under vault, upserts into `planning_entities`
- `sync_sqlite_to_taskwarrior(policy_state)` — injects compliant tasks into TW with UDA `upstream_id` and policy tags
- `sync_taskwarrior_to_sqlite()` — reads TW task completion, marks `roadmap_sync` rows completed (closed-loop signal)

**`HybridRAGIndexer`** (`src/pipeline/rag_indexer.py`) — three-index strategy:
1. SQLite (relational SoT for status/storypoints)
2. ChromaDB/SQLite-vec (semantic over study notes, commits, journals)
3. Obsidian links + optional Neo4j (graph for Topic→Prerequisite, Task↔Task, StudyNote→Project)

**UEID format:** `<CLUSTER>:<ENTITY>:<ID>` e.g. `study:topic:st_python_01`, `dev:proj:proj_vibe_01`, `task:tw:81d33ec8`

**Vibe-ops src/ package map:**

| Subdir | Purpose |
|--------|---------|
| `main.py` | argparser CLI: `run-daily`, `status`, `gaps`, `sync` |
| `vibe_cli.py` | Typer+Rich CLI: `sync_file`, `hybrid_search`, `gaps`, `debt_dashboard` |
| `cybernetics/` | `CyberneticDailyLoop`, `BinaryKnowledgeTree`, `GapSearchEngine` |
| `pipeline/` | MVL orchestrators: `policy_engine`, `rag_indexer`, `mvl_orchestrator`, `enrichment_engine`, `cognitive_debt_tracker`, `sync_orchestrator`, `reverse_sync`, `ikigai_scorer` |
| `models/` | Pydantic v2 entities by cluster: temporal, habit, study, project, metric, policy, rag, ikigai, knowledge, feedback, contracts |
| `storage/` | SQLite/SQLAlchemy ORM, `sqlite-vec`, ChromaDB adapter, UEID manager |
| `middleware/` | `SyncEngine` (Obsidian ↔ SQLite ↔ Taskwarrior bridge) |
| `embeddings/` | Pluggable provider: OpenAI / local sentence-transformers / hash-moq fallbacks |
| `schemas/` | `pydantic_v2.py` (PolicyState, PolicyDecision, IkigaiScorer) |
| `contracts/` | YAML/JSON schemas (`planning.v1.yaml`, `registry.yaml`) + Pydantic sync payloads |
| `parsers/` | Markdown/frontmatter utilities |

**Rust TUI** (`vibeops-tui/`): 1-second polling dashboard showing current `PolicyDecision` state + Ikigai score. Read-only, reads from `../vibe_ops.db`.

---

## Key Specification Documents (ADRs, PRDs, BRDs)

The `vibe-ops/` and `life-ops/operational/docs/` directories contain structured engineering documents:

### ADRs (Architecture Decision Records) — `vibe-ops/architecture/`
| File | Content |
|------|---------|
| `ADR-001-data-flow-topology.md` | Multi-cluster data flow topology v1.1 |
| `ADR-002-mesh-contracts-state-machines.md` | Contracts and state machine specs |
| `ADR-003-ikigai-as-meta-brain.md` | IKIGAi as meta-brain architecture |
| `ADR-004-hybrid-rag-strategy.md` | Hybrid RAG indexing strategy |
| `ADR-005-data-mesh-topology.md` | Data mesh topology |

### PRDs (Product Requirements Documents) — `vibe-ops/planning/`
| File | Content |
|------|---------|
| `PRD-01-temporal-engine.md` | Wave/Cycle/Phase temporal engine |
| `PRD-02-habit-tracker.md` | Habit tracker with H(t), E(t), Q_HE |
| `PRD-03-study-backlog.md` | Skill/Topic/Material/Session backlog |
| `PRD-04-project-execution.md` | Project/Epic/Sprint/Task execution |
| `PRD-05-metrics-health.md` | SleepRecord/EnergyReading metrics |
| `PRD-06-policy-governance.md` | PolicyEngine 4-state governance |
| `PRD-07-ikigai-vectors.md` | IKIGAi vector entities |

### BRDs (Business Requirements Documents) — `vibe-ops/planning/`
- `CLUSTER_PLAN_BRD.md` — Business requirements for Cluster 1 (Plan)
- `CLUSTER_PLAN_USER_STORIES.md` — 10 user stories
- `CLUSTER_PLAN_CLI_SPEC.md` — 13 CLI commands spec
- `CLUSTER_PLAN_ROADMAP.md` — 12 sprints Q3 roadmap

### operational/ ADRs — `life-ops/operational/docs/adr/`
| File | Content |
|------|---------|
| `PRD-CONSTANTS-EXCEPTIONS.md` | PAVConstants + 10 error codes |
| `PRD-CORE-HABIT-ENGINE.md` | Habit engine core logic |
| `PRD-CORE-POLICY-CONSOLIDATOR.md` | Policy FSM + consolidator |
| `PRD-CORE-POMODORO-SCENARIO.md` | 8-state pomodoro SM + scenarios |
| `PRD-CORE-SLEEP-VALIDATION.md` | Sleep calculator + validation |
| `PRD-CORE-TIME-BLOCKS-AND-REFLECTION.md` | Time blocks + journal reflection |
| `PRD-ENTITIES-JOURNAL-HABIT.md` | JournalEntry, Habit entities |
| `PRD-ENTITIES-METRIC-CONSOLIDATION.md` | Metric entities + rollup |
| `PRD-ENTITIES-POLICY.md` | PolicySetpoints, PolicyDecision |
| `PRD-ENTITIES-ROUTINE-TIMEBLOCK-POMODORO.md` | Routine, TimeBlock, Pomodoro entities |
| `PRD-ENUMS-TYPES.md` | Enums and type definitions |
| `ARCHITECTURAL_REFRAMING_2026-06-07.md` | Architectural reframe after Sprint 10 |
| `SPRINT-1/2/3-REPORT.md` | Sprint verification reports |

---

## Submodule Dispatch Reference

Every central maps to a standalone CLI subprocess — not a Python import:

| Central | Submodule | CLI invocation |
|---------|-----------|----------------|
| `task` | Taskwarrior binary + `taskwarrior/scripts/` | `subprocess.run(["task", ...])` for `today`; `bash script.sh` for `daily/weekly-review`; `python calculate-metrics.py` for `metrics` |
| `finance` | `fin_ops` | `BaseCentral.run_cli` → `python -m fin_ops.cli ...` |
| `knowledge read` | `leitura` | `BaseCentral.run_cli` → `python -m leitura.cli ...` |
| `knowledge mindmap-phase0/1` | `mindmaps` | `BaseCentral.run_cli` → `python -m mindmaps.cli ...` |
| `knowledge note-add/note-list` | `notes` | `BaseCentral.run_cli` → `python -m notes.cli ...` |
| `research map/crawl/search` | `research` | `BaseCentral.run_cli` → `python -m research.cli ...` |
| (handler) | `life/` itself | `python -m life.cli <central> <cmd> --json` |

---

## Important Rules

### `life-ops/operational/` — Standalone Rule
- **Must remain decoupled.** No imports from root `life/` or `vibe-ops/`.
- Any new CLI command must support `--json` flag for machine-readable output.
- When modifying domain logic or CLI features, update `life-ops/operational/SPEC.md`.
- **Quality gates:** 2518 tests, ruff ALL rules, mypy --strict, pre-commit hooks.

### `vibe-ops/` — Append-Only Rule
- **Never delete, prune, or rewrite** existing sessions, topics, sub-topics, or paragraphs.
- Re-organization is allowed only if every pre-existing string survives intact.
- **Refactor Protocol:** If asked to refactor, stop immediately → propose Action Plan → wait for Approval Gate → only then mutate.

### General
- Prefer **Typer** for new CLI surfaces in `life/`.
- Support `--json` on all new commands wherever feasible.
- Centrals should stay thin — delegate to submodules or scripts.
- Use `from __future__ import annotations` at top of Python files.
- Error collection (not abort) — handlers collect all errors and report at end rather than short-circuiting.

---

## Database Schema Overview

`vibe-ops/src/storage/schema.sql` is the **live** schema; migration files describe planned evolution:

**Temporal cluster:** `temporal_waves` (15-day, regex `^W\d+_[A-Za-z]{3}_\d{4}$`), `temporal_cycles` (45-day), `temporal_phases` (180-day)

**Study cluster:** `study_plans`, `study_topics` (cognitive_debt + depth_level), `study_notes`

**Dev cluster:** `dev_projects`, `dev_roadmaps`, `dev_backlogs`, `dev_changelogs`

**Habit cluster:** `habits`, `habit_states` (FK → habits.id), streak tracking with cybernetic model: `H(t) = 1 − e^(−λ·streak)`, `E = R·(1 − H(t))`

**MVL (Minimum Viable Loop):** `policy_decisions` (output of the loop), `study_sessions`, `planning_entities` (idempotent frontmatter mirror), `roadmap_sync` (TW bridge with `upstream_id` UDA)

**Views:** `v_epistemic_priority` ranks study_topics by `cognitive_debt + depth_level`; `v_dashboard_study_dev` cross-joins roadmaps, study projects, features, backlog tasks, and changelogs.

---

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **life** (12741 symbols, 18843 relationships, 173 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/life/context` | Codebase overview, check index freshness |
| `gitnexus://repo/life/clusters` | All functional areas |
| `gitnexus://repo/life/processes` | All execution flows |
| `gitnexus://repo/life/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
