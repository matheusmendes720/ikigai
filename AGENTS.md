# AGENTS.md

> Agent-facing guide for the **Algorithmic Life OS** monorepo.  
> Read this first before editing any file.  
> For human contributors, see `CLAUDE.md` (overlap is intentional).

---

## 1. Project Overview

**Algorithmic Life OS** (`life/`) is a personal productivity orchestration system written in Python. It acts as a CLI hub (`life`) that integrates domain "centrals" (task, finance, knowledge, research) with daily/weekly handlers and a plugin system. The repository also contains architectural specs, data-mesh pipelines, and a cybernetic decision engine under `vibe-ops/`.

Key characteristics:
- **Fully local** — zero cloud dependencies; all data lives on the filesystem (SQLite, Markdown vaults, Taskwarrior).
- **Portuguese-language documentation** — strategy docs, ADRs, PRDs, and specs are written in Portuguese. Source-code comments are mostly in English.
- **Monorepo with sub-projects** — root `life/` package, standalone Poetry project in `life-ops/`, and a Python+Rust sub-project in `vibe-ops/`.

---

## 2. Repository Layout

```
life/
├── centrals/              # Domain hubs: task, knowledge, research (finance removed in 4dc18c1)
├── cli/                   # Main Typer CLI, config, logging, test runner
├── handlers/              # daily.py, weekly.py — orchestrate centrals
├── plugins/               # Plugin protocol, loader, builtin health_check
├── life-ops/              # Standalone Poetry projects
│   ├── life-tatics CLI   # Time-tracking CLI (Poetry, must remain decoupled)
│   └── operational/       # Standalone PAV cybernetic engine (habits, routines, policy FSM)
├── vibe-ops/              # Cybernetic orchestrator, data mesh, ADRs, specs
├── vibe-ops/              # Cybernetic orchestrator, data mesh, ADRs, specs
│   ├── src/               # Pipeline, models, storage, middleware, CLI
│   ├── vibeops-tui/       # Rust ratatui TUI (Cargo project)
│   ├── migrations/        # SQL schema + Alembic-style Python migrations
│   ├── tests/             # pytest suite
│   └── doc/               # Architecture & data-mesh documentation
├── time-tasker/           # DUPLICATE snapshot of root files + taskwarrior docs
├── strategics/            # Markdown strategy documents (Portuguese)
├── logs/                  # Runtime logs
└── verify_mesh.py         # Quick import sanity check for vibe-ops models
```

### Important note on `time-tasker/`
This directory contains copies of the root Python source tree (`life/`, `strategics/`, `taskwarrior/`) and appears to be a deployment snapshot or alternate workspace. **Treat the root directory as the canonical source of truth.** Do not edit files inside `time-tasker/` unless you are explicitly asked to update that snapshot.

### Important note on `finance` central
The finance central (`centrals/finance.py`) and its `fin_ops` submodule dependency have been **removed permanently** (commit `4dc18c1`). The `cli/config.py` no longer references `fin_ops` in `DEFAULT_SUBMODULES`, and `FinanceConfig.finance_store` has been stripped. The root `__init__.py` was also restored (deleted in the checkpoint commit) and old-style imports (`life.config`, `life.log`, `life.test_runner`) have been migrated to `life.cli.*` across all canonical source files.

---

## 3. Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.10+ |
| CLI framework | Typer |
| Config / packaging | Poetry (`life-ops/`), uv (`vibe-ops/` — `uv.lock` present) |
| Data & ORM | SQLAlchemy 2.0, SQLite, ChromaDB, `sqlite-vec` (fallback to NumPy) |
| Validation | Pydantic v2 |
| Task management | Taskwarrior binary + `tasklib` (Python) |
| Markdown parsing | `python-frontmatter` |
| Embeddings | Local / OpenAI provider abstraction |
| TUI | Rust + `ratatui` + `crossterm` + `rusqlite` |
| Shell automation | PowerShell (`.ps1`) scripts |

No `requirements.txt` or `setup.py` exists at the repository root. The root package is intended to be run via `python -m life.cli` (requires the parent directory on `PYTHONPATH`, or an editable install).

---

## 4. Build and Run Commands

### Root CLI (`life`)
```bash
# From repo root (requires parent dir on PYTHONPATH)
python -m life.cli --help
python -m life.cli daily run
python -m life.cli weekly run
python -m life.cli task today
python -m life.cli finance report --period week
python -m life.cli submodules
python -m life.cli health
```

### Tests (root)
There is **no Makefile, `pytest.ini`, or `tox`**. Tests are discovered and executed through the CLI itself:
```bash
python -m life.cli test           # Run pytest across all submodules with tests/
python -m life.cli test --list    # List discovered test directories
python -m life.cli test -s <name> # Run only one submodule
```
`cli/test_runner.py` discovers submodules containing `tests/` or `test_*.py` and runs `pytest` in each.

### `life-ops/` (`life-tatics`)
Must remain completely decoupled from the root `life/` package.
```bash
cd life-ops
poetry install
poetry run life-tatics --help
```

### `vibe-ops/`
Uses uv (lockfile present). Two Python CLIs and a Rust TUI:
```bash
cd vibe-ops

# argparse CLI (main.py)
python src/main.py run-daily [--date YYYY-MM-DD]
python src/main.py status
python src/main.py gaps
python src/main.py sync --vault-path <path>

# Typer+Rich CLI (higher-level surface)
python src/vibe_cli.py sync_file [--vault-path]
python src/vibe_cli.py hybrid_search "query"
python src/vibe_cli.py gaps
python src/vibe_cli.py debt_dashboard

# PowerShell launcher (Windows)
.\run_loop.ps1
```

#### Rust TUI
```bash
cd vibe-ops/vibeops-tui
cargo run
```

---

## 5. Code Organization & Architecture

### 5.1 Central–Handler Pattern
- **`centrals/`** are domain hubs (`task`, `knowledge`, `research` — **finance was removed**). Each central exposes Typer subcommands that dispatch to submodules or external scripts.
- **`handlers/`** (`daily.py`, `weekly.py`) orchestrate centrals by running the main CLI as a subprocess (`python -m life.cli <central> <cmd> --json`) and aggregating results.

### 5.2 Removed: Finance Central
The `finance` central and its `fin_ops` submodule dependency were **decoupled and removed** in commit `4dc18c1`. The `fin_ops` directory no longer exists at the repo root. `cli/config.py` no longer references it, `handlers/daily.py`/`handlers/weekly.py` no longer call `--skip-finance` or `--finance-period`. This was a clean decoupling: the finance domain may be resurrected as its own standalone project under `life-ops/` in the future.

### 5.3 Root `__init__.py` Restored
The root `__init__.py` (defining `__version__ = "0.1.0"`) was deleted in the checkpoint commit. It has been restored to enable `python -m life.cli` imports. Old-style imports across the codebase (`life.config` → `life.cli.config`, `life.log` → `life.cli.log`, `life.test_runner` → `life.cli.test_runner`) have been updated in all canonical source files.

### 5.4 BaseCentral
All centrals inherit from `BaseCentral` (`centrals/base.py`). It provides:
```python
run_cli(cwd: Path, module: str, args: list[str], json_out: bool = True) -> dict[str, Any]
```
This runs `python -m <module> <args> [--json]` in a subprocess and returns `{ok, stdout, stderr, data}`.

### 5.3 Submodule Dispatch
Most centrals do not contain heavy logic directly. They delegate to standalone submodules configured in `LifeConfig.submodules` (`cli/config.py`):

| Central | Submodule(s) |
|---------|-------------|
| `task` | Taskwarrior binary (`task`), bash scripts in `taskwarrior/scripts/` |
| `knowledge` | `leitura`, `mindmaps`, `notes` (each standalone Python CLIs) |
| `research` | `research` (standalone Python CLI) |

### 5.4 Plugin System
Plugins implement `PluginProtocol` (`plugins/protocol.py`) with `register(app)` and optional lifecycle hooks (`before_daily`, `after_daily`, etc.).
- `plugins/loader.py` discovers plugins from `plugin_dirs` (configurable in `config/life.yaml`).
- `plugins/builtin/health_check.py` is the built-in plugin; it registers the `health` command.
- Plugins are auto-registered at startup in `cli/cli.py` via `register_plugins(app)`.
- **Plugin lifecycle hooks (`before_daily`, `after_daily`, etc.) are declared but not yet called by `handlers/daily.py` / `handlers/weekly.py`.**

### 5.5 Config (`cli/config.py`)
`LifeConfig` / `load_config` is the single source of truth. It loads `config/life.yaml` if present, otherwise falls back to hardcoded defaults. Key paths: `submodules`, `task_scripts`, `log_dir`, `plugin_dirs`.

**Note:** The default `submodules` dict in `cli/config.py` points to paths that may not exist on this system (`fin_ops/`, `system/raise_data/`, etc.). `get_submodule_path()` returns `{"ok": False, "error": "... not found"}` for unknown submodules rather than raising.

### 5.6 Vibe-Ops Cybernetic Architecture
`vibe-ops/` implements a **Target-Sensor-Adjuster** cybernetic loop:
1. **Target** — Ikigai-based setpoints (`IkigaiScorer`).
2. **Sensor** — SQLite metrics (study hours, habit consistency, infractions).
3. **Adjuster** — `PolicyEngine` state machine (`PUSH → MAINTAIN → REDUCE → RECOVER`).
4. **Persist & Sync** — `SyncEngine` bidirectionally syncs Obsidian ↔ SQLite ↔ Taskwarrior.
5. **Semantic Indexing** — `HybridRAGIndexer` indexes the Obsidian vault into SQLite-vec/ChromaDB.

Key modules:
- `src/pipeline/` — ingestion, enrichment, policy, sync, RAG, orchestrators.
- `src/models/` — Pydantic entities (study, habit, project, policy, RAG, etc.).
- `src/storage/` — SQLite/SQLAlchemy adapters, vector store, UEID manager.
- `src/middleware/` — `SyncEngine` (Obsidian ↔ SQLite ↔ Taskwarrior).
- `src/cybernetics/` — `CyberneticDailyLoop`, `BinaryKnowledgeTree`, `GapSearchEngine`.
- `src/contracts/` — data contracts and sync schemas.

### 5.7 `life-ops/operational/` — Standalone PAV Cybernetic Engine

A Poetry project at `life-ops/operational/` implementing the operational/cybernetic domain from the PAV (Produtividade Algorítmica Visual) spec. Fully standalone — no imports from root `life/` or `vibe-ops/`.

**Architecture:**
```
src/operational/
├── constants.py         # PAVConstants (22 frozen fields)
├── exceptions.py        # 10 PAV error codes
├── enums.py             # Period, RoutineType, PolicyState, ...
├── types.py             # NewTypes, Protocols, TypeVars
├── entities/            # 8 Pydantic v2 modules (routine, time_block, habit, policy, ...)
├── core/                # Pure business logic (sleep, pomodoro, habit, policy engine, ...)
├── persistence/         # Repository Protocol + InMemory + SQLite + migrations
├── parsers/             # Frontmatter YAML → Pydantic
├── reports/             # Daily/weekly narrative generators
├── meta/                # Registry, validators, factories
└── cli/                 # Typer commands (routine, block, journal, habit, metric, policy, report)
```

**Quality gates:** 2518 tests ✅, 0 mypy errors ✅, CLI with `--json` support.

---

### 6.1 `vibe-ops/` — Append-Only Rule
Due to the high density of architectural context, this directory follows a strict **Append-Only & Enrichment** policy:
1. **Never delete** existing sessions, topics, sub-topics, or paragraphs.
2. **Never rewrite** existing content in a way that reduces information quantity.
3. You may **re-organize** (sub-headings, lists), but the original text must survive intact.

**Refactor Protocol:** If the user asks for structural refactoring:
1. Stop editing immediately.
2. Propose a **Plan of Action** describing blocks and vectors to be moved.
3. Request explicit user approval ("Approval Gate").
4. Only mutate destructively after approval.

### 6.2 `life-ops/` (`life-tatics`) — Standalone Rule
- **Must remain decoupled.** Do not import or depend on modules from the root `life/` package or `taskwarrior/` scripts.
- Any new CLI command must support a `--json` flag for machine-readable output.
- When modifying domain logic or CLI features, update `life-ops/SPEC.md`.

### 6.3 General CLI Conventions
- Prefer **Typer** for new CLI surfaces.
- Support `--json` on all new commands wherever feasible.
- Use `from __future__ import annotations` at the top of Python files.
- Keep centrals thin; delegate to submodules or scripts.

### 6.4 Imports — Transitional State (Mostly Resolved)

All canonical source files in the root `life/` package have been migrated to `life.cli.*` imports (commit `4dc18c1`). The `time-tasker/` snapshot still has the old-style imports, but it is not canonical. New files should use `life.cli.config` / `life.cli.log` / `life.cli.test_runner`.

---

## 7. Testing Strategy

- **Root package:** No dedicated test directory at root. Test coverage lives in submodules. Use the built-in `python -m life.cli test` command to discover and run tests across submodule paths.
- **`vibe-ops/tests/`:** Contains `pytest` tests (e.g., `test_mvl_orchestrator.py`). Uses in-memory SQLite fixtures and mocks ChromaDB.
- **`vibe-ops/scratch/`:** Contains informal `test_*.py` scripts used for iterative exploration. These are **not** part of the official test suite.
- **No CI configuration** (GitHub Actions, etc.) is present. Testing is local-only.

When adding features to `vibe-ops/`, add corresponding tests under `vibe-ops/tests/` using pytest fixtures and mock external services (ChromaDB, Taskwarrior, etc.).

---

## 8. Security & Deployment Considerations

- **Fully local / air-gapped by design.** No API keys, OAuth, or network services are required for core operation.
- SQLite databases (`vibe_ops.db`, `test_vibe.db`, `vibe_mesh.db`) and ChromaDB (`chroma_db/`) reside inside the working directory.
- No secrets management infrastructure is present.
- Deployment is manual: run PowerShell scripts or Python modules directly on the host machine.
- The Rust TUI reads from `../vibe_ops.db` relative to its executable location.

---

## 9. Quick Reference: File Roles

| File / Dir | Purpose |
|------------|---------|
| `cli/cli.py` | Main Typer app; registers centrals, handlers, plugins |
| `cli/config.py` | `LifeConfig` dataclass; YAML + env loading |
| `cli/log.py` | Structured logging (plain or JSON) to file + stderr |
| `cli/test_runner.py` | Pytest discovery & runner across submodules |
| `centrals/base.py` | `BaseCentral` with `run_cli()` subprocess helper |
| `plugins/protocol.py` | `PluginProtocol` (register + lifecycle hooks) |
| `plugins/loader.py` | File-system plugin discovery |
| `vibe-ops/src/main.py` | Cybernetic CLI entry point (`argparse`) |
| `vibe-ops/src/cybernetics/daily_loop.py` | Target-Sensor-Adjuster loop |
| `vibe-ops/src/pipeline/policy_engine.py` | State-machine policy decisions |
| `vibe-ops/src/middleware/sync_engine.py` | Obsidian ↔ SQLite ↔ Taskwarrior sync |
| `vibe-ops/migrations/` | SQL schema definitions |
| `verify_mesh.py` | Quick import sanity check for ORM models |
| `CONCEPTUAL_MODEL.md` | Tensão → Comportamento → Solução (5 tensões, 4 regimes, 3 frequências) — o "porquê" do sistema |
| `SYSTEMS_TOPOLOGY.md` | Índice-of-índices + mapa de middlewares — o "como" do sistema |
| `CLUSTER_PLAN.md` | Plan + Personal Productivity (rotinas, blocos, rituais, pomodoro) — Cluster 1 standalone |
| `CLUSTER_PROJ.md` | Project Execution (PMO ↔ Taskwarrior) — Cluster 2 standalone |
| `CLUSTER_STUDY.md` | Studies & Lifelong Learning (PKM + pré-req cognitivo + intersecção roadmap) — Cluster 3 standalone |
| `diagrams/` | Diagramas Mermaid renderizados (topologia, conceitual, clusters) + instruções mmdc |

---

## 10. Known Issues & Transitional State

1. **Missing root `__init__.py`** — may prevent `python -m life.cli` from working depending on how `PYTHONPATH` is set. (🟢 **Fixed** in `4dc18c1`)
2. **Mixed import paths** — `life.cli.config` vs `life.config`; `life.cli.log` vs `life.log`. (🟢 **Fixed** in `4dc18c1` for all canonical source files)
3. **`time-tasker/` duplication** — appears to be a snapshot; edits should target root files.
4. **`vibe-ops/` is active R&D** — many pipeline modules have placeholder or partially implemented logic. Check `IMPLEMENTATION_LOG.md` for current batch status before assuming a feature is complete.

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
