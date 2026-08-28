# AGENTS.md

Guidance for coding agents (Codex, Claude Code, Hermes, GitNexus) working in this repository.

## Project Overview

**Algorithmic Life OS** — Python productivity orchestration. Root `cli/` + `centrals/` + `handlers/` + `plugins/` is the CLI hub that integrates domain "centrals" (task / knowledge / research) with daily / weekly handlers and a plugin system. Three independent Python packages live under `src/`; each is a separate project with its own manifest and lockfile — don't mix their tooling. (Previous `life-ops/*` paths were reorged to `src/*`; old paths are noted where still relevant in `Makefile` / `.pre-commit-config.yaml` / etc. — see Pitfalls.)

| Path | Tooling | Role |
|------|---------|------|
| `cli/`, `centrals/`, `handlers/`, `plugins/`, `__init__.py` (root) | Python | Root `life` CLI hub (Typer). Imports `from life import __version__` — repo root must be on `PYTHONPATH`. |
| `src/operational/` | uv workspace | PAV productivity kernel — `pyproject.toml` declares `members = ["packages/core"]` only; `apps/cli` + `apps/tui` were deleted in `604d6af` (CLI scripts still broken) |
| `src/ikigai/` | Poetry | IKIGAi meta-brain — MCP server, deep-agent harness, LangGraph `ikigai_maintainer` graph, OpenTelemetry wiring |
| `src/life_tatics/` | none (no `pyproject.toml`) | Standalone `life-tatics` time-block planner — runs as a module: `python -m life_tatics.cli` |
| `src/mesh/` | uv (root) | Phase 3 v1 data mesh — `ForkAdapter` Protocol, `CliAdapter` / `TaskdogAdapter` / `SolverforgeCalendarAdapter`, append-only review queue, Deep Agent consumer + propagator. **v1 scope: `create` action only.** |
| `src/contracts/` | uv (root) | Canonical Pydantic v2 contracts shared across layers (`UEID`, `Task`, `TaskChange`, `PlanningCycle`, etc.) — frozen + `extra="forbid"` |
| `src/planner/` | — | Planning notes + scalar-decomposition backlog |
| `vibe-ops/` | uv | Cybernetic engine — Target-Sensor-Adjuster loop, Obsidian ↔ SQLite ↔ Taskwarrior |
| `taskwarrior/` | — | Taskwarrior binary + scripts + config consumed by the `task` central |
| `interfaces/{cli,tui}/` | — | Interface-layer consumers; `cli/` ships Phase 3 v1 `read_tasks.py`, `tui/` is empty |
| `vault/` | — | Primary notes layer (markdown source of truth, Obsidian-style) — **append-only** |
| `data/` | — | Runtime state — `vibe_ops.db`, `vibe_mesh.db`, `boulder.json`, `chroma_db/`, `review_queue/`, `test-fixtures/`, `session-*.md` |
| `code-docs/{prd,brd,adr,ard}/` | — | Requirements docs |
| `strategics/` | — | PT-BR strategy / operational analysis |
| `docs/` | — | Master reading index (`ÍNDICE PROGRESSIVO.md`) |
| `diagrams/` | — | Mermaid source + PNGs |
| `langgraph.json` + root `Makefile` | — | Hosts 6 LangGraph graphs on `langgraph dev` (port 2024) |

## Recent Major Changes

### Phase 3 v1 — Data Mesh (commits `d4d28f5`..`97d84c2`, on master, 8 ahead of origin)

- **`2aa67e9` `feat(contracts)`** — `TaskChange` + `PropagationEvent` Pydantic models (Phase 3 v1 spec).
- **`a5ae67e` `feat(contracts)`** — `UEID` Pydantic type with 5-part regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`.
- **`6df8879` `feat(mesh)`** — Filesystem append-only review queue with atomic writes (`src/mesh/queue.py`).
- **`5c1c283` `feat(mesh)`** — Deep Agent consumer (`agent_consumer.py`) with PAE validation rules → `Decision.APPROVE|REJECT|CLARIFY`.
- **`dfb3668` `feat(mesh)`** — Deep Agent propagator (`agent_propagator.py`) with per-adapter failure isolation.
- **`ddf9ebe` `feat(mesh)`** — `CliAdapter` for `interfaces/cli` `tasks.jsonl`.
- **`abc0f6f` `feat(mesh)`** — `TaskdogAdapter` for taskdog SQLite (simplified schema, native SQLite UPSERT in `c698114`).
- **`e2be826` `feat(mesh)`** — `SolverforgeCalendarAdapter` for UPI `ueid` column; preserves id on UPSERT conflict (`1e7399c`); auto-acks partial_propagation in `propagate()` (`bb0edd5`).
- **`a8ecf80` `feat(cli)`** — `life mesh show` + `life task add` (Phase 3 v1 commands).
- **`118a374` `test(integration)`** — end-to-end create flow across all forks.
- **`8136bd5` `docs`** — Phase 3 audit + spec + plan artifacts.
- **`752922e` `docs(claude)`** — Phase 3 v1 data mesh layer documentation in `CLAUDE.md`.
- **`9461456` `test(smoke)`** — Phase 3 v1 8-step happy path smoke (`scripts/smoke/phase3_v1.{sh,bat}`).
- **`97d84c2` `docs`** — ship registry tier-1 quick wins (D02/D05/P03/A08).
- **`248e359` `chore`** — remove 3 zero-byte root artifacts from reorg.
- **`d4d28f5` `chore(operational)`** — remove orphan `cli/tui/ui` test scaffolding.
- **`fb515f4` `chore(operational)`** — sync `uv.lock` after cli/tui deprecation.

### Earlier observability / IKIGAi work (still relevant)

- **`1d9479a`** — docs(observability): 4 follow-up specs (server-side reliability, smoke test, merge plan, worktree dissolve) at `src/ikigai/docs/observability/0{1..4}-*.md`.
- **`0e528d0`** — feat(observability): IKIGAI server-side stack tracing (`init_tracing()` + `@observed_tool`).
- **`87f6ef9`** — feat(reliability): client-side retry + circuit-breaker + scoped cache invalidation in `src/agents/tools.py`.
- **`fd4b8dd`** — feat(entities): UEID primitive + 5-part format validator (`<CLUSTER>:<ENTITY>:<ID>`).
- **`eeac3aa`** — chore(scripts): `migrate_plan_entities.py` for legacy 11-col DBs.
- **`0ff111d`** — refactor(commit, mcp-server): plan entity writes routed through `SQLiteAdapter`.
- **`ca4e65c`** — feat(propagation): `SQLiteAdapter.upsert()` with append-only history.
- **`20f1e72`** — chore(observability): wire OpenTelemetry to LangSmith + Langfuse (single SDK, two OTLP exporters).
- **`ea97ea9` / `b3f9977`** — docs(ikigai): SPEC.md §14 constitutional references; cycle bootstrap analysis.
- **`604d6af`** — **chore: delete PAV UI** — `apps/cli`, `apps/tui`, `home_v2`, `dataset_selector`, TUI widgets, theme tokens removed. Console scripts `operational` / `pav` / `pav-os` and `python -m operational` are still **broken** (editable-install `.pth` still points at deleted `apps/cli/src`).
- **`8077bda`** — test suite: **49 pytest files** under `src/operational/tests/{core,e2e,integration,unit,property/,tui/,ui/}` (the last three dirs are empty scaffolding post-`d4d28f5`).
- **`b484795` / `ac4177f` / `66aa517`** — IKIGAi deep-agent harness + `ikigai-maintainer-mcp` (8 tools, stdio) + LangGraph `ikigai_maintainer` graph with `SqliteSaver` checkpointing.

**Observability sprint — 4 repos in worktrees (status post-reorg):**
- `src/ikigai` (IKIGAI) — `feat/mcp-observability` branch, 8 commits, awaiting merge to `gitbutler/workspace` (see spec `src/ikigai/docs/observability/03-merge-plan.md`).
- `apps/kanban/tuiboard-otel-worktree` — `feat/otel-tracing`, 2 commits (`590ea60` + `2c39867`), unmerged.
- `apps/dev-tools/taskdog-otel-worktree` — `feat/otel-tracing`, 2 commits (`5a8b1bb2` + `600c92b9` uv.lock), unmerged.
- `apps/calendar/solverforge-calendar` — `feat/otel-tracing` + `feat/rust-build-fix`, 3 commits (`1716b16` build-fix + `cfbf12b` + `064b8c9` OTel fix), unmerged. Build-fix must merge to main BEFORE OTel rebases on it.

## Build & Test

### Root CLI hub (`life` package — `cli/` + `centrals/` + `handlers/` + `plugins/`)

Root `__init__.py` enables `python -m life.cli`; **repo root must be on `PYTHONPATH`** for the `from life import __version__` import in `cli/cli.py`. The Phase 3 v1 commands also import `from src.mesh.adapters import …` (via `PYTHONPATH=$REPO/src`).

```bash
# Daily / weekly from the repo root
python -m life.cli --help
python -m life.cli daily run [--skip-task]
python -m life.cli weekly run [--skip-review] [--skip-metrics]
python -m life.cli task {today,daily-review,weekly-review,metrics}
python -m life.cli knowledge {read,mindmap-phase0}
python -m life.cli research {map --depth 2,search --backend vector}
python -m life.cli submodules
python -m life.cli health
python -m life.cli config-show [--path] [--json]
python -m life.cli test [--list|-s <submodule>]   # discover + run pytest across submodules

# Phase 3 v1 mesh commands (canonical path)
python -m life.cli mesh show <ueid>            # join slices from CLI / taskdog / UPI
python -m life.cli task add <ueid> ...         # enqueues TaskChange to data/review_queue/

# Phase 3 v1 smoke (isolated temp dir — does NOT touch real data/)
bash scripts/smoke/phase3_v1.sh
scripts\smoke\phase3_v1.bat                    # Windows
```

### `src/operational/` — PAV kernel (uv workspace)

`pyproject.toml` declares `members = ["packages/core"]` only. Real source lives at `src/operational/packages/core/src/operational/`.

```bash
cd src/operational
uv sync                                                       # install (uv, not poetry)
uv run pytest                                                 # full suite (49 test files in src/operational/tests)
uv run pytest -m "not e2e"                                    # CI matrix
uv run pytest tests/unit -v                                   # narrow by directory
uv run pytest -k "test_qhe" -v                                # narrow by name
uv run pytest --collect-only -q | tail -1                     # count check after refactor
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
uv run pre-commit run --all-files                             # gating hooks (hooked from root .pre-commit-config.yaml)
# `uv run verify_sprint` is referenced in CI but scripts/verify_sprint.py is .sh-only —
# use scripts/verify_sprint.sh or `bash scripts/verify_sprint.sh` until it's ported.
```

Markers (`pytest.ini`): `unit`, `integration`, `property`, `e2e`, `slow`. CI runs `pytest -m "not e2e"` per package plus a separate `pytest -m e2e` job. (Note: the `property`, `tui`, `ui` markers still appear but the corresponding dirs are empty post-`d4d28f5`.)

### `src/ikigai/` — IKIGAi meta-brain (Poetry)

```bash
cd src/ikigai
poetry install
poetry run pytest                                              # IKIGAi test suite (34 test files in src/ikigai/tests)
# Windows launcher (sets venv python + PYTHONPATH=src automatically):
ikigai.bat mcp                                                 # start MCP server (stdio, 8 tools)
ikigai.bat agent <thread>                                      # run one agent cycle
ikigai.bat chat <thread>                                       # REPL chat mode
ikigai.bat list                                                # list checkpoints
# Cross-cutting MCP gateway (IKIGAi + tuiboard + taskdog + solverforge):
./start_mcp_gateway.sh {status|test}                           # bash; Windows: bash start_mcp_gateway.sh
```

Console scripts (in `pyproject.toml`): `ikigai-maintainer-mcp` → `run_mcp_server:main`, `ikigai-deep-agent` → `agents.deepagents_harness:main`. OpenTelemetry wired to LangSmith + Langfuse via two OTLP exporters from a single SDK.

### `src/life_tatics/` — Time-Tactics Planner (no `pyproject.toml`)

No Poetry/uv here — it's just a Python module on `PYTHONPATH`. Run as `python -m life_tatics.cli`:

```bash
# Run from repo root with src on PYTHONPATH:
PYTHONPATH=$REPO/src python -m life_tatics.cli --help
```

### `src/mesh/` — Phase 3 v1 Data Mesh (uv, uses repo venv)

No `pyproject.toml` — mesh is imported as `from src.mesh import …` after putting repo root on `PYTHONPATH`. The smoke script at `scripts/smoke/phase3_v1.{sh,bat}` is the canonical e2e driver.

```bash
# Run the v1 happy path (isolated temp dir, real data/ untouched)
PYTHONPATH=$REPO/src bash scripts/smoke/phase3_v1.sh
```

Root tests for Phase 3 live at `tests/{contracts,mesh,integration}/` (9 test files total). Run with: `pytest tests/ -v` from repo root with `src/` on `PYTHONPATH`.

### `vibe-ops/` — Cybernetic engine (uv)

```bash
cd vibe-ops
python src/main.py {run-daily [--date YYYY-MM-DD],status,gaps,sync --vault-path <path>}
python src/vibe_cli.py {sync_file,hybrid_search "q",gaps,debt_dashboard}
cd vibeops-tui && cargo run                                    # Rust TUI (polling ../vibe_ops.db)
```

### LangGraph dev workflow (root `Makefile`)

`langgraph.json` registers 6 graphs under `vibe-ops/src/langgraph_entry.py`: `pae_maintainer`, `quarterly_replan`, `test_de_fogo_rollup`, `correction_protocol`, `dream_falsification`, `ikigai_maintainer`. Python 3.11; loads `.env`.

```bash
make help           # list targets
make install        # uv add langgraph + langgraph-checkpoint (+ optional pae-maintainer)
make dev            # langgraph dev (port 2024)
make dev-graph NAME=pae_maintainer
make test           # runs vibe-ops/tests/, src/operational/tests/ (via stale poetry shim — see Pitfalls), and langgraph_tests/
make logs           # tail .langgraph/logs/dev.log
make status         # list registered graphs + last 5 commits
make clean          # rm .langgraph/state.db + .langgraph/checkpoints/ (NOT the running server)
```

## Architecture

### Root CLI — central-handler + plugin

```
cli/  centrals/  handlers/  plugins/   (all at repo root, NOT under life/)
```

- `cli/cli.py` is the Typer entry; imports `from life import __version__` (from repo-root `__init__.py`).
- `centrals/` expose `typer.Typer` sub-apps mounted by `cli/cli.py`. Delegates: `task` → Taskwarrior binary; `knowledge` → `leitura` / `mindmaps` / `notes`; `research` → `research` CLI. `BaseCentral.run_cli()` returns `{ok, stdout, stderr, data, error?}`.
- `handlers/daily.py`, `handlers/weekly.py` re-invoke the CLI via `python -m life.cli <central> <cmd> --json` (handlers double as integration tests).
- `plugins/protocol.py` defines `register()` + `before/after_{daily,weekly}()` lifecycle hooks. `plugins/loader.py` discovers via `cfg.plugin_dirs` looking for a module-level `PLUGIN` / `plugin` / `Plugin` attr. `plugins/builtin/health_check.py` is the only built-in.
- `cli/config.py` — `LifeConfig` / `load_config()` loads `config/life.yaml` if present; key fields: `root`, `log_dir`, `plugin_dirs`, `submodules`, `task_scripts`, `notes_store`. `get_submodule_path(name)` returns `{"ok": False, "error": ...}` for unknown submodules (never raises).
- `cli/test_runner.py` discovers `tests/` dirs from `cfg.submodules` and runs `pytest -v` per submodule.

### `src/operational/` — uv workspace layout

`pyproject.toml` declares `members = ["packages/core"]` only. Real source lives at `src/operational/packages/core/src/operational/` with modules: `constants.py` (PAVConstants, 22 frozen fields), `enums.py`, `types.py`, `exceptions.py` (10 codes), `entities/` (15 Pydantic v2 frozen models, `extra=forbid`, no cross-entity imports), `core/` (habit_engine, policy_engine, pomodoro_machine, sleep_calculator, scenario_classifier, consolidator, budget, routine_logger, weekly_aggregator, insights, break_calculator, context_switch, journal_segmenter, next_step, time_validator, analytics), `persistence/` (Repository Protocol + InMemory + SQLite + migrations), `parsers/` (YAML/frontmatter → Pydantic), `reports/` (Markdown daily/weekly), `analytics/`, `meta/` (EntityRegistry, validators, factories), `input_validation.py`. `agents/` (harness, orchestrator, workflows — incl. `agents/orchestrator/state.py` which owns `reload_stale_repos()`; the old `apps/cli/state.py` path is gone). `medic/` is a Go diagnostic CLI binary (with `medic.exe` already built). `workflows/` holds `daily_pipeline.yaml` + `pav_qa_pipeline.yaml`. `tests/` has 49 test files across `tests/{core,e2e,integration,unit,property/,tui/,ui/}` (the last three dirs are empty scaffolding from before `d4d28f5`).

Core algorithms (pure arithmetic, zero LLM): `H(t) = 1 − e^(−λ·streak)`, `E = R·(1 − H(t))`, Q_HE composite, 4-state PolicyEngine FSM (PUSH → MAINTAIN → REDUCE → RECOVER with hysteresis), 8-state Pomodoro SM + scenario classifier.

### `src/ikigai/` — MCP meta-brain

IKIGAi is consumed by Claude Code / LangChain deep-agents via its MCP server. Architecture: `LangChain Deep Agent ──HTTP+SSE──► Unified MCP Gateway ──stdio──► ikigai-maintainer-mcp (8 tools)`. The 8 tools are: `score`, `regime`, `phase`, `decompose`, `corrections`, `plan_cycle`, `checkpoint`, `sync_vault`. Checkpointing uses `langgraph-checkpoint-sqlite` (`SqliteSaver`). UEID format: `<CLUSTER>:<ENTITY>:<ID>` e.g. `study:topic:st_python_01` (validated as a primitive by the Pydantic `UEID` type).

### `src/contracts/` — Canonical Pydantic v2 contracts

Shared across all layers; **never duplicate contract models elsewhere**. Frozen + `extra="forbid"`. Modules: `common.py` (`UEID`, `Period`, `Priority`, `EntityType`, `RegimeState`), `task.py` (`Task`, `Subtask`, `ChecklistItem`, `Project`, `Milestone`, `Deliverable`), `task_change.py` (`TaskChange`, `PropagationEvent`, `TaskAction` — Phase 3 v1), `planning.py` (`PlanningCycle`, `Wave`, `Sprint`, `VaultEvent`), `metrics.py` (`Burndown`, `ExecutionRate`, `QHEScore`).

### `src/mesh/` — Phase 3 v1 Data Mesh

`ForkAdapter` Protocol (`@runtime_checkable`, `src/mesh/adapters/base.py`) + 3 adapters: `CliAdapter` (`interfaces/cli` `tasks.jsonl`), `TaskdogAdapter` (taskdog SQLite, native UPSERT on `ueid`), `SolverforgeCalendarAdapter` (UPI `ueid` column). Write path: any fork → CLI enqueues `TaskChange` to `data/review_queue/` → `agent_consumer.consume_pending()` validates with PAE rules (`Decision.APPROVE|REJECT|CLARIFY`) → `agent_propagator.propagate()` writes `PropagationEvent` to all forks with per-adapter failure isolation. UEID is the canonical join key. **v1.2+ is out of scope** (`update` / `delete` / `done` gated on data-first methodology: 5+ SONHO logs).

### `vibe-ops/` — cybernetic loop

`src/cybernetics/daily_loop.py` runs TARGET (`IkigaiScorer`) → SENSOR (aggregates) → ADJUSTER (4-state `PolicyEngine`) → PERSIST (`policy_decisions` table) → SYNC (`SyncEngine` — Obsidian ↔ SQLite ↔ Taskwarrior, idempotent `upstream_id` SHA-256) → INDEX (`HybridRAGIndexer` → SQLite-vec / ChromaDB). Severity (CRITICAL/HIGH/MEDIUM/LOW) = f(infractions, hours_deviation, consistency); transitions have hysteresis. `src/` subdirs: `main.py` (argparse), `vibe_cli.py` (Typer+Rich), `langgraph_entry.py`, `cybernetics/`, `pipeline/` (policy_engine, rag_indexer, mvl_orchestrator, enrichment_engine, cognitive_debt_tracker, sync_orchestrator, reverse_sync, ikigai_scorer), `models/`, `storage/` (sqlite-vec, ChromaDB adapter, UEID manager), `middleware/`, `embeddings/`, `contracts/`, `migrations/`, `cli/`, `agents/`, `integration/`, `schemas/`. Rust TUI at `vibeops-tui/` polls `../data/vibe_ops.db` every second.

## Testing

- **Root `tests/`** (9 files) is Phase 3 only: `tests/{contracts,mesh,integration}/`. Run with `pytest tests/ -v` from repo root with `src/` on `PYTHONPATH`. **`langgraph_tests/` no longer exists** — the Makefile still references it and breaks `make test` (see Pitfalls).
- **`src/operational/tests/`** — 49 test files. Markers in `pytest.ini`. CI runs `pytest -m "not e2e"` per package + a dedicated `pytest -m e2e` job. Scaffolding dirs `tests/{property,tui,ui}/` exist but are empty post-`d4d28f5`.
- **`src/ikigai/tests/`** — 34 files. Poetry-managed. The Makefile claims 250+ tests; current count is 34.
- **`vibe-ops/tests/`** — in-memory SQLite fixtures + mocked ChromaDB. `vibe-ops/scratch/` has informal `test_*.py` exploration scripts — **not** part of the official suite.
- **`scripts/smoke/phase3_v1.{sh,bat}`** — Phase 3 v1 8-step happy path; isolated temp dir; the canonical end-to-end driver for the mesh layer.
- Mock external services (ChromaDB, Taskwarrior) in tests. Don't hand-edit `tests/fixtures/`.

## Important Rules

- **`src/operational/` — standalone**: no imports from root `life/` or `vibe-ops/`. New CLI commands must support `--json`. Domain logic / CLI changes → update `src/operational/SPEC.md`. Quality gates: 49 pytest files, ruff ALL rules (extended in `src/operational/ruff.toml`), mypy --strict, pre-commit.
- **`src/ikigai/` — decoupling**: no imports from `src/operational/` (the kernel is consumed via MCP contracts, not Python imports). Contracts come from `src/contracts/` only.
- **`src/contracts/` — single source**: all Pydantic models shared across layers live here; never re-define `UEID`, `Task`, `TaskChange`, etc. elsewhere.
- **`src/mesh/` — Phase 3 v1 scope**: `create` action only. Don't add `update`/`delete`/`done` until Phase 3 v1.2 spec (gated on data-first methodology). PAE validation is the only sanctioned gate before propagation.
- **`vault/`, `vibe-ops/`, `strategics/` — append-only**: never delete / prune / rewrite existing sessions, topics, sub-topics, or paragraphs. Re-organisation is allowed only if every pre-existing string survives byte-for-byte. Refactor protocol: stop → propose Action Plan → wait for explicit "go" → only then mutate.
- **`data/` — runtime only**: never hand-edit `vibe_ops.db`, `vibe_mesh.db`, `boulder.json`, or `review_queue/`. Regenerate via the canonical CLI or smoke script.
- **General**: prefer Typer for new `life/` CLI surfaces. `--json` everywhere feasible. Centrals stay thin — delegate to submodules or scripts. `from __future__ import annotations` at the top of every Python file. Handlers collect errors and report at end (no short-circuit).
- **Two CLAUDE.md files** (`CLAUDE.md` root + `src/operational/CLAUDE.md`) describe overlapping scopes; trust neither blindly, verify against `git log` + filesystem. The root `CLAUDE.md` is more up-to-date on the `src/*` reorg + Phase 3 mesh layer.

## Pitfalls

- **Operational CLI is broken.** `uv run operational`, `uv run pav`, `uv run pav-os`, `python -m operational` all fail post-`604d6af`. Editable-install `.pth` files under `.venv/Lib/site-packages/` still point at the deleted `apps/cli/src` and `apps/tui/src`; don't take absence of an immediate ImportError as proof it works. Verify whether restoration is in scope before recommending.
- **Stale `life-ops/*` paths in tool config.** Both the root `Makefile` (`cd life-ops/operational && poetry run pytest`) and `.pre-commit-config.yaml` header comment still reference `life-ops/operational/`. Real paths are `src/operational/`. The Makefile `test` target works only when a Poetry shim happens to exist; prefer `cd src/operational && uv run pytest`. **The Makefile's third `test` invocation `pytest langgraph_tests/` is broken** — that dir was removed; comment it out or skip the target.
- **`langgraph_tests/` is gone.** Root `tests/` is Phase 3 only (mesh + contracts + integration). The Makefile's `make test` calls into a dead dir.
- **Stray 0-byte files at repo root.** Names like `'`, `0`, `14`, `None`, `int`, `agent('Execute`, ``` ``1`` ```, and (in `src/operational/`) `'`, `1\``, `3`, `4.0\``, `6.0`, `60`, `None`, `Path`, `Severity\`,-`, `TimeSeriesSlice`, `tuple[date`, `tuple[str` are untracked crash/typo artifacts. Don't `read_file` them. Use `search_files pattern` if a real file with that name exists elsewhere.
- **Orphaned test dirs.** `src/operational/tests/{tui,ui,property}/` survive but their source was deleted in `604d6af`/`d4d28f5` — empty dirs, no collection impact, but `pytest --collect-only` may warn.
- **Don't expand the uv workspace casually.** CI matrix is `operational-core` + `ikigai` + `vibe-ops` (paths `src/operational/packages/core`, `src/ikigai`, `vibe-ops`). Adding a new member requires updating `.github/workflows/ci.yml` `matrix.include` and `members = [...]` in `src/operational/pyproject.toml`.
- **Tooling split.** `uv sync` for `src/operational/` and `vibe-ops/`. `poetry install` for `src/ikigai/`. No `pyproject.toml` for `src/life_tatics/` or `src/mesh/` — run as plain Python modules with `PYTHONPATH=$REPO/src`. Never mix.
- **Mtime reload moved.** `apps/cli/state.py` `reload_stale_repos()` now lives at `src/operational/agents/orchestrator/state.py`.
- **LangGraph dev holds port 2024.** `make clean` wipes state + checkpoints only — kill the server before re-running.
- **Throwaway files at `src/operational/` root** (`output.txt`, `CheckResult`, `not`, etc.) are not source — don't open or add new ones there. Same pattern of stray tokens is now leaking into `src/ikigai/` (`$null`, `dict`, `str`, `int`, etc.).
- **`ikigai.bat` venv path.** The launcher hard-codes `.venv\Scripts\python.exe`; if you ever recreate the venv with `poetry env remove` + `poetry install`, the .bat still finds it — but renaming `.venv/` breaks it silently.
- **Observability worktrees pending merge.** 4 OTel branches are sitting on disk (IKIGAI `feat/mcp-observability` worktree + 3 external `feat/otel-tracing` branches in `apps/{kanban,dev-tools,calendar}/`). Merge procedure in `src/ikigai/docs/observability/03-merge-plan.md`. Don't rebase or rewrite their history without reading the merge plan first — order matters (solverforge build-fix first).
- **`scripts/verify_sprint.sh` vs `uv run verify_sprint`.** Only `.sh` exists; `uv run verify_sprint` fails. Use `bash scripts/verify_sprint.sh` until it's ported.
- **PYTHONPATH for root CLI.** `cli/cli.py` does `from life import __version__`. The root `__init__.py` defines it, but only if repo root is on `PYTHONPATH`. Either `cd` to repo root or export `PYTHONPATH=.` before invoking `python -m life.cli`.
- **Phase 3 mesh smoke is the canonical driver.** `scripts/smoke/phase3_v1.{sh,bat}` runs in an isolated temp dir; if you change the mesh layer's public surface, update both the smoke script and the contracts in `src/contracts/task_change.py`. The Python driver inside the smoke script redirects module-level path constants (`cli.TASKS_JSONL`, `taskdog.TASKDOG_DB`, `solverforge_calendar.UPI_DB`, `queue.QUEUE_DIR`) before exercising the flow.

## File Roles Quick Reference

| File / Dir | Purpose |
|---|---|
| `__init__.py` (root) | `__version__ = "0.1.0"`; makes root a `life` package when on PYTHONPATH |
| `cli/cli.py` | Main Typer app; registers centrals, handlers, plugins |
| `cli/config.py` | `LifeConfig` + YAML/env loading |
| `cli/log.py` | Structured logging (plain or JSON) |
| `cli/test_runner.py` | Discovers submodules' `tests/` dirs and runs `pytest -v` per dir |
| `centrals/base.py` | `BaseCentral.run_cli()` subprocess helper |
| `centrals/{task,knowledge,research}.py` | Central sub-apps |
| `handlers/daily.py`, `handlers/weekly.py` | Orchestrate centrals via `python -m life.cli` |
| `plugins/{protocol,loader}.py` + `plugins/builtin/health_check.py` | Plugin discovery + lifecycle |
| `interfaces/cli/read_tasks.py` | Phase 3 v1 reader for `CliAdapter` slice |
| `src/contracts/{common,task,task_change,planning,metrics}.py` | Canonical Pydantic v2 contracts (frozen, `extra="forbid"`) |
| `src/mesh/queue.py` | Filesystem append-only review queue (atomic writes) |
| `src/mesh/agent_consumer.py` | Deep Agent validation (`Decision.APPROVE|REJECT|CLARIFY`) |
| `src/mesh/agent_propagator.py` | Deep Agent propagation (per-adapter failure isolation) |
| `src/mesh/adapters/{base,cli,taskdog,solverforge_calendar}.py` | Phase 3 v1 `ForkAdapter` Protocol + 3 implementations |
| `src/operational/{pyproject.toml,pytest.ini,ruff.toml,SPEC.md}` | uv workspace + gates |
| `src/operational/scripts/{verify_sprint,lint,test,typecheck}.sh` | Local gate scripts |
| `src/operational/packages/core/src/operational/{core,entities,persistence,parsers,reports,analytics,meta}/` | Pure PAV logic |
| `src/operational/agents/{harness,orchestrator,workflows}/` | Agentic systems (engine, scheduler, monitor, state, task_types, qa_swarm.yaml) |
| `src/operational/medic/` | Go diagnostic CLI (has prebuilt `medic.exe`) |
| `src/operational/workflows/{daily_pipeline,pav_qa_pipeline}.yaml` | Workflow specs |
| `src/ikigai/{SPEC.md,MCP_GATEWAY.md,ikigai.bat,run_mcp_server.py,start_mcp_gateway.sh,langgraph.json,pyproject.toml}` | IKIGAi entry + manifest |
| `src/ikigai/src/{agents,mcp_server,ikigai,observability}/` | Deep-agent harness, MCP server, IKIGAi core, OTel init |
| `src/ikigai/data/matheus/{dreams,objectives,projects,deliverables,ikigai_state}/` | BYD case-study vault (PT-BR deliverables) |
| `src/life_tatics/{cli.py,domain/}` | Standalone time-block planner (no `pyproject.toml`) |
| `src/planner/ikigai_planning/` | Planning notes |
| `tests/{contracts,mesh,integration}/` | Phase 3 v1 cross-fork test suite (9 files) |
| `scripts/smoke/phase3_v1.{sh,bat}` | Phase 3 v1 8-step happy path smoke |
| `vibe-ops/src/{main,vibe_cli,langgraph_entry}.py` | argparse / Typer / LangGraph entries |
| `vibe-ops/src/cybernetics/daily_loop.py` | Target-Sensor-Adjuster loop |
| `vibe-ops/src/pipeline/policy_engine.py` | 4-state FSM |
| `vibe-ops/src/middleware/sync_engine.py` | Obsidian ↔ SQLite ↔ Taskwarrior |
| `vibe-ops/migrations/`, `vibe-ops/src/storage/schema.sql` | SQL + Python migrations |
| `langgraph.json` + root `Makefile` + `LANGRAPH_DEV.md` | LangGraph dev server (port 2024) |
| `CONCEPTUAL_MODEL.md`, `SYSTEMS_TOPOLOGY.md`, `CLUSTER_{PLAN,PROJ,STUDY}.md`, `ARCHITECTURE_INDEX.md` | Cluster docs (PT-BR) — `ARCHITECTURE_INDEX.md §3–§5` for ADRs/PRDs/specs |

## Codex-Specific Operations

### Claude Flow v3 Hook Pipeline (`.codex/hooks.json`)

When `CLAUDE_FLOW_V3_ENABLED=true` and `CLAUDE_FLOW_HOOKS_ENABLED=true` (set in `.codex/config.toml`), every Codex session runs through the chain defined in `.codex/hooks.json` (8 hook types): `PreToolUse` (Bash + Write/Edit/MultiEdit), `PostToolUse` (Write/Edit + Bash), `PreCompact`, `SessionStart`, `UserPromptSubmit`, `SubagentStart`/`Stop`, `Stop`. Handlers live at `.claude/helpers/hook-handler.cjs` (project-local) with fallback to `%USERPROFILE%\.claude\helpers\hook-handler.cjs` (user-global). `pre-bash` is the most likely to refuse commands (e.g. bulk `rm`, force-push, secret exfil).

### Skills (`.claude/skills/`)

Loaded by Codex via native skill activation — **never read them with file tools** (the harness loads them with full activation context). Load `superpowers:using-superpowers` before any non-trivial task.

### SessionStart hook (auto-runs)

A `SessionStart:startup` hook instructs Codex to use `codebase-memory-mcp` tools **first** for code exploration: `search_graph`, `trace_path`, `get_code_snippet`, `query_graph`, `get_architecture`, `search_code`. Fall back to `Grep`/`Glob`/`Read` only for text, configs, non-code files.

### GitNexus skill paths (`.Codex/skills/gitnexus/`)

| Task | Skill |
|---|---|
| Architecture / "How does X work?" | `gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `gitnexus-refactoring/SKILL.md` |
| Tools / resources / schema | `gitnexus-guide/SKILL.md` |

**Before editing any symbol:** run blast-radius analysis. If HIGH or CRITICAL, do not proceed without user approval. **Before committing:** `detect_changes()` to verify only expected symbols / flows are affected. Never rename via find-and-replace — use the GitNexus `rename` tool. Index stale? `node .gitnexus/run.cjs analyze` from project root (or `npx gitnexus analyze`; npm 11 may crash → `npm i -g gitnexus`).

### Refactor Protocol (vibe-ops / append-only surfaces)

If asked to refactor anything in `vibe-ops/`, `strategics/`, `vault/`, or a cluster doc: stop → propose Action Plan (every file touched, every string preserved, migration path) → wait for explicit user "go" → only then mutate, and verify every pre-existing string survives byte-for-byte. The append-only rule is enforced by this protocol. **`vault/` is the primary notes layer (post-reorg) and is append-only by rule**, even though it isn't a `vibe-ops/` subtree.

<!-- gitnexus:start -->
## Code Intelligence — GitNexus

This project is indexed by GitNexus as **life**. Use GitNexus tools (`impact`, `query`, `context`) for symbol-level questions and standard Grep/Glob/Read for text and configs. GitNexus resources: `gitnexus://repo/life/{context,clusters,processes,process/<name>}`. Same blast-radius + `detect_changes()` discipline applies — see the GitNexus skills table above for tool/skill routing.

<!-- gitnexus:end -->
