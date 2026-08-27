# AGENTS.md

Guidance for coding agents (Codex, Claude Code, Hermes, GitNexus) working in this repository.

## Project Overview

**Algorithmic Life OS** — Python productivity orchestration. Root `life/` CLI hub integrates domain "centrals" (task / knowledge / research) with daily / weekly handlers and a plugin system. Three independent workspaces live underneath it; each is a separate Python project with its own manifest and lockfile — don't mix their tooling.

| Path | Tooling | Role |
|------|---------|------|
| `life-ops/operational/` | uv workspace | PAV productivity kernel — pure logic, `packages/core` is the sole member (apps/cli + apps/tui were deleted in `604d6af`) |
| `life-ops/ikigai/` | Poetry | IKIGAi meta-brain — MCP server, deep-agent harness, LangGraph `ikigai_maintainer` graph, OpenTelemetry wiring |
| `life-ops/life_tatics/` | Poetry | Standalone `life-tatics` time-block planner |
| `life-ops/life-mcp-observability-worktree/` | — | Observability worktree (LangSmith / Langfuse / OpenTelemetry) |
| `vibe-ops/` | uv | Cybernetic engine — Target-Sensor-Adjuster loop, Obsidian ↔ SQLite ↔ Taskwarrior |
| `taskwarrior/` | — | Taskwarrior binary + scripts + config consumed by the `task` central |
| `code-docs/{prd,brd,adr,ard}/` | — | Requirements docs |
| `strategics/` | — | PT-BR strategy / operational analysis |
| `docs/` | — | Master reading index (`ÍNDICE PROGRESSIVO.md`) |
| `diagrams/` | — | Mermaid source + PNGs |
| `langgraph.json` + root `Makefile` | — | Hosts 6 LangGraph graphs on `langgraph dev` (port 2024) |

## Recent Major Changes

- **`1d9479a`** — docs(observability): 4 follow-up specs (server-side reliability, smoke test, merge plan, worktree dissolve) at `life-ops/ikigai/docs/observability/0{1..4}-*.md`.
- **`0e528d0`** — feat(observability): IKIGAI server-side stack tracing (`init_tracing()` + `@observed_tool`).
- **`87f6ef9`** — feat(reliability): client-side retry + circuit-breaker + scoped cache invalidation in `src/agents/tools.py`.
- **`fd4b8dd`** — feat(entities): UEID primitive + 5-part format validator (`<CLUSTER>:<ENTITY>:<ID>`).
- **`eeac3aa`** — chore(scripts): `migrate_plan_entities.py` for legacy 11-col DBs.
- **`0ff111d`** — refactor(commit, mcp-server): plan entity writes routed through `SQLiteAdapter` (resolves canonical-24 vs runtime-11 schema split-brain).
- **`ca4e65c`** — feat(propagation): `SQLiteAdapter.upsert()` with append-only history.
- **`20f1e72`** — chore(observability): wire OpenTelemetry to LangSmith + Langfuse (single SDK, two OTLP exporters).
- **`ea97ea9`** / **`b3f9977`** — docs(ikigai): SPEC.md §14 constitutional references; cycle bootstrap analysis.
- **`604d6af`** — **chore: delete PAV UI** — `apps/cli`, `apps/tui`, `home_v2`, `dataset_selector`, TUI widgets, theme tokens removed. `packages/core` is now the sole workspace member. The `operational` / `pav` / `pav-os` console scripts and `python -m operational` are **broken** (their editable-install `.pth` still points at the deleted `apps/cli/src`). Tests under `tests/unit/cli/` fail until the CLI is restored.
- **`8077bda`** — test suite: **74 pytest files** under `tests/{core,unit,integration,property,e2e,tui,ui}/`.
- **`b484795`** / **`ac4177f`** / **`66aa517`** — IKIGAi deep-agent harness + `ikigai-maintainer-mcp` (8 tools, stdio) + LangGraph `ikigai_maintainer` graph with `SqliteSaver` checkpointing.

**Observability sprint (4 repos, branched in worktrees):**
- `life-ops/life-mcp-observability-worktree` (IKIGAI) — `feat/mcp-observability` branch, 8 commits, awaiting merge to `gitbutler/workspace` (see spec `03-merge-plan.md`)
- `apps/kanban/tuiboard-otel-worktree` — `feat/otel-tracing` branch, 2 commits (`590ea60` + `2c39867` dual-export fix), unmerged
- `apps/dev-tools/taskdog-otel-worktree` — `feat/otel-tracing` branch, 2 commits (`5a8b1bb2` + `600c92b9` uv.lock), unmerged
- `apps/calendar/solverforge-calendar` — `feat/otel-tracing` + `feat/rust-build-fix` branches, 3 commits (`1716b16` build-fix + `cfbf12b` + `064b8c9` OTel fix), unmerged. Build-fix must merge to main BEFORE OTel rebases on it.

## Build & Test

### `life/` — Root CLI hub

```bash
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
```

All canonical source files use `life.cli.config` / `life.cli.log`. Root `__init__.py` enables `python -m life.cli`.

### `life-ops/operational/` — PAV kernel (uv workspace)

```bash
cd life-ops/operational
uv sync                                                       # install (uv, not poetry)
uv run pytest                                                 # full suite (74 files)
uv run pytest -m "not e2e"                                    # CI matrix
uv run pytest tests/unit/cli -v                               # narrow by directory
uv run pytest -k "test_qhe" -v                                # narrow by name
uv run pytest --collect-only -q | tail -1                     # count check after refactor
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
uv run pre-commit run --all-files                             # gating hooks
# `uv run verify_sprint` is referenced in CI but scripts/verify_sprint.py is .sh-only —
# use scripts/verify_sprint.sh or `bash scripts/verify_sprint.sh` until it's ported.
```

Markers (`pytest.ini`): `unit`, `integration`, `property`, `e2e`, `slow`. CI runs `pytest -m "not e2e"` per package plus a separate `pytest -m e2e` job.

### `life-ops/ikigai/` — IKIGAi meta-brain (Poetry)

```bash
cd life-ops/ikigai
poetry install
poetry run pytest                                              # IKIGAi test suite
# Windows launcher (sets venv python + PYTHONPATH=src automatically):
ikigai.bat mcp                                                 # start MCP server (stdio, 8 tools)
ikigai.bat agent <thread>                                      # run one agent cycle
ikigai.bat chat <thread>                                       # REPL chat mode
ikigai.bat list                                                # list checkpoints
# Cross-cutting MCP gateway (IKIGAi + tuiboard + taskdog + solverforge):
./start_mcp_gateway.sh {status|test}                           # bash; Windows: bash start_mcp_gateway.sh
```

Console scripts (in `pyproject.toml`): `ikigai-maintainer-mcp` → `run_mcp_server:main`, `ikigai-deep-agent` → `agents.deepagents_harness:main`.

### `life-ops/life_tatics/` — Time-Tactics Planner (Poetry)

```bash
cd life-ops && poetry install && poetry run life-tatics --help
```

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
make test           # pytest vibe-ops/tests/ + operational/tests/ + langgraph_tests/
make logs           # tail .langgraph/logs/dev.log
make status         # list registered graphs + last 5 commits
make clean          # rm .langgraph/state.db + .langgraph/checkpoints/ (NOT the running server)
```

## Architecture

### Root CLI — central-handler + plugin

```
life/{centrals,handlers,plugins,cli}/
```

- `centrals/` expose `typer.Typer` sub-apps mounted by `cli/cli.py`. Delegates: `task` → Taskwarrior binary; `knowledge` → `leitura` / `mindmaps` / `notes`; `research` → `research` CLI. `BaseCentral.run_cli()` returns `{ok, stdout, stderr, data, error?}`.
- `handlers/daily.py`, `handlers/weekly.py` re-invoke the CLI via `python -m life.cli <central> <cmd> --json` (handlers double as integration tests).
- `plugins/protocol.py` defines `register()` + `before/after_{daily,weekly}()` lifecycle hooks. `plugins/loader.py` discovers via `cfg.plugin_dirs` looking for a module-level `PLUGIN` / `plugin` / `Plugin` attr. `plugins/builtin/health_check.py` is the only built-in.
- `cli/config.py` — `LifeConfig` / `load_config()` loads `config/life.yaml` if present; key fields: `root`, `log_dir`, `plugin_dirs`, `submodules`, `task_scripts`, `notes_store`. `get_submodule_path(name)` returns `{"ok": False, "error": ...}` for unknown submodules (never raises).

### `life-ops/operational/` — uv workspace layout

`pyproject.toml` declares `members = ["packages/core"]` only. `packages/core/src/operational/` modules: `constants.py` (PAVConstants, 22 frozen fields), `enums.py`, `types.py`, `exceptions.py` (10 codes), `entities/` (15 Pydantic v2 frozen models, `extra=forbid`, no cross-entity imports), `core/` (habit_engine, policy_engine, pomodoro_machine, sleep_calculator, scenario_classifier, consolidator, budget, routine_logger, weekly_aggregator, insights, break_calculator, context_switch, journal_segmenter, next_step, time_validator, analytics), `persistence/` (Repository Protocol + InMemory + SQLite + migrations), `parsers/` (YAML/frontmatter → Pydantic), `reports/` (Markdown daily/weekly), `analytics/`, `meta/` (EntityRegistry, validators, factories), `input_validation.py`. `agents/` (harness, orchestrator, workflows — incl. `agents/orchestrator/state.py` which owns `reload_stale_repos()`; the old `apps/cli/state.py` path is gone). `medic/` is a Go diagnostic CLI binary. `tests/` is 74 files across `tests/{core,unit/{cli,core,entities,meta,parsers,persistence,reports},integration,property,e2e,tui,ui}/`.

Core algorithms (pure arithmetic, zero LLM): `H(t) = 1 − e^(−λ·streak)`, `E = R·(1 − H(t))`, Q_HE composite, 4-state PolicyEngine FSM (PUSH → MAINTAIN → REDUCE → RECOVER with hysteresis), 8-state Pomodoro SM + scenario classifier.

### `life-ops/ikigai/` — MCP meta-brain

IKIGAi is consumed by Claude Code / LangChain deep-agents via its MCP server. Architecture: `LangChain Deep Agent ──HTTP+SSE──► Unified MCP Gateway ──stdio──► ikigai-maintainer-mcp (8 tools)`. The 8 tools are: `score`, `regime`, `phase`, `decompose`, `corrections`, `plan_cycle`, `checkpoint`, `sync_vault`. Checkpointing uses `langgraph-checkpoint-sqlite` (`SqliteSaver`). UEID format: `<CLUSTER>:<ENTITY>:<ID>` e.g. `study:topic:st_python_01` (now validated as a primitive).

### `vibe-ops/` — cybernetic loop

`src/cybernetics/daily_loop.py` runs TARGET (`IkigaiScorer`) → SENSOR (aggregates) → ADJUSTER (4-state `PolicyEngine`) → PERSIST (`policy_decisions` table) → SYNC (`SyncEngine` — Obsidian ↔ SQLite ↔ Taskwarrior, idempotent `upstream_id` SHA-256) → INDEX (`HybridRAGIndexer` → SQLite-vec / ChromaDB). Severity (CRITICAL/HIGH/MEDIUM/LOW) = f(infractions, hours_deviation, consistency); transitions have hysteresis. `src/` subdirs: `main.py` (argparse), `vibe_cli.py` (Typer+Rich), `langgraph_entry.py`, `cybernetics/`, `pipeline/` (policy_engine, rag_indexer, mvl_orchestrator, enrichment_engine, cognitive_debt_tracker, sync_orchestrator, reverse_sync, ikigai_scorer), `models/`, `storage/` (sqlite-vec, ChromaDB adapter, UEID manager), `middleware/`, `embeddings/`, `contracts/`, `migrations/`, `cli/`, `agents/`, `integration/`, `schemas/`. Rust TUI at `vibeops-tui/` polls `../vibe_ops.db` every second.

## Testing

- `life/` root has no test dir — coverage lives in submodules; `python -m life.cli test` discovers and runs.
- `life-ops/operational/tests/` — 74 files. Markers in `pytest.ini`. CI runs `pytest -m "not e2e"` per package + a dedicated `pytest -m e2e` job.
- `vibe-ops/tests/` — in-memory SQLite fixtures + mocked ChromaDB. `vibe-ops/scratch/` has informal `test_*.py` exploration scripts — **not** part of the official suite.
- `langgraph_tests/` (root) — run via `make test` with `--with langgraph --with pydantic`.
- `life-ops/ikigai/tests/` — Poetry-managed; mirror of the 250+ IKIGAi tests noted in the Makefile.
- Mock external services (ChromaDB, Taskwarrior) in tests. Don't hand-edit `tests/fixtures/`.

## Important Rules

- **`life-ops/operational/` — standalone**: no imports from root `life/` or `vibe-ops/`. New CLI commands must support `--json`. Domain logic / CLI changes → update `life-ops/operational/SPEC.md`. Quality gates: 74 pytest files, ruff ALL rules, mypy --strict, pre-commit.
- **`life-ops/ikigai/` — decoupling**: no imports from `life-ops/operational/` (the kernel is consumed via MCP contracts, not Python imports).
- **`vibe-ops/` — append-only**: never delete / prune / rewrite existing sessions, topics, sub-topics, or paragraphs. Re-organisation is allowed only if every pre-existing string survives byte-for-byte. Refactor protocol: stop → propose Action Plan → wait for explicit "go" → only then mutate.
- **General**: prefer Typer for new `life/` CLI surfaces. `--json` everywhere feasible. Centrals stay thin — delegate to submodules or scripts. `from __future__ import annotations` at the top of every Python file. Handlers collect errors and report at end (no short-circuit).

## Pitfalls

- **Operational CLI is broken.** `uv run operational`, `uv run pav`, `uv run pav-os`, `python -m operational` all fail post-`604d6af`. Editable-install `.pth` files under `.venv/Lib/site-packages/` still point at the deleted `apps/cli/src` and `apps/tui/src`; don't take absence of an immediate ImportError as proof it works. Tests under `tests/unit/cli/` fail. Verify whether restoration is in scope before recommending.
- **Stray 0-byte files at repo root.** Names like `2`, `0`, `4}`, `dict[str`, `ISO`, `Existing`, `Path`, `int`, `None`, `String`, `bool`, `new`, `de`, `tem` are untracked crash/typo artifacts. Don't `read_file` them. Use `search_files pattern` if a real file with that name exists elsewhere.
- **Orphaned test dirs.** `tests/tui/` and `tests/ui/` survive but their source was deleted in `604d6af` — expect collection errors or skips.
- **Don't expand the uv workspace casually.** CI matrix is `operational-core` + `vibe-ops`; adding a new member requires updating `.github/workflows/ci.yml` `matrix.include` and `members = [...]` in `life-ops/operational/pyproject.toml`.
- **Tooling split.** `uv sync` for `life-ops/operational/` and `vibe-ops/`. `poetry install` for `life-ops/ikigai/` and `life-ops/life_tatics/`. Never mix.
- **Mtime reload moved.** `apps/cli/state.py` `reload_stale_repos()` now lives at `life-ops/operational/agents/orchestrator/state.py`.
- **LangGraph dev holds port 2024.** `make clean` wipes state + checkpoints only — kill the server before re-running.
- **Two CLAUDE.md files** (`CLAUDE.md` root + `life-ops/operational/CLAUDE.md`) describe overlapping scopes; trust neither blindly, verify against `git log` + filesystem.
- **Throwaway files at `life-ops/operational/` root** (`output.txt`, `CheckResult`, `not`, etc.) are not source — don't open or add new ones there. Same pattern of stray tokens is now leaking into `life-ops/ikigai/` (`$null`, `dict`, `str`, `int`, etc.).
- **`ikigai.bat` venv path.** The launcher hard-codes `.venv\Scripts\python.exe`; if you ever recreate the venv with `poetry env remove` + `poetry install`, the .bat still finds it — but renaming `.venv/` breaks it silently.
- **Observability worktrees pending merge.** 4 OTel branches are sitting on disk (IKIGAI `feat/mcp-observability` worktree + 3 external `feat/otel-tracing` branches in `apps/{kanban,dev-tools,calendar}/`). Merge procedure in `life-ops/ikigai/docs/observability/03-merge-plan.md`. Don't rebase or rewrite their history without reading the merge plan first — order matters (solverforge build-fix first).
- **Makefile `test` target** uses `cd life-ops/operational && poetry run pytest` even though `operational/` is a uv workspace (not Poetry). It works only when `poetry` happens to find a shim; prefer `cd life-ops/operational && uv run pytest` for the operational suite.
- **`scripts/verify_sprint.sh` vs `uv run verify_sprint`.** Only `.sh` exists; `uv run verify_sprint` fails. Use `bash scripts/verify_sprint.sh` until it's ported.

## File Roles Quick Reference

| File / Dir | Purpose |
|---|---|
| `cli/cli.py` | Main Typer app; registers centrals, handlers, plugins |
| `cli/config.py` | `LifeConfig` + YAML/env loading |
| `cli/log.py` | Structured logging (plain or JSON) |
| `centrals/base.py` | `BaseCentral.run_cli()` subprocess helper |
| `handlers/daily.py`, `handlers/weekly.py` | Orchestrate centrals via `python -m life.cli` |
| `plugins/{protocol,loader}.py` + `plugins/builtin/health_check.py` | Plugin discovery + lifecycle |
| `vibe-ops/src/{main,vibe_cli,langgraph_entry}.py` | argparse / Typer / LangGraph entries |
| `vibe-ops/src/cybernetics/daily_loop.py` | Target-Sensor-Adjuster loop |
| `vibe-ops/src/pipeline/policy_engine.py` | 4-state FSM |
| `vibe-ops/src/middleware/sync_engine.py` | Obsidian ↔ SQLite ↔ Taskwarrior |
| `vibe-ops/migrations/`, `vibe-ops/src/storage/schema.sql` | SQL + Python migrations |
| `langgraph.json` + root `Makefile` + `LANGRAPH_DEV.md` | LangGraph dev server (port 2024) |
| `life-ops/operational/{pyproject.toml,pytest.ini,ruff.toml,SPEC.md}` | uv workspace + gates |
| `life-ops/operational/scripts/{verify_sprint,lint,test,typecheck}.sh` | Local gate scripts |
| `life-ops/operational/packages/core/src/operational/{core,entities,persistence,parsers,reports,analytics,meta}/` | Pure PAV logic |
| `life-ops/operational/agents/{harness,orchestrator,workflows}/` | Agentic systems (engine, scheduler, monitor, state, task_types, qa_swarm.yaml) |
| `life-ops/ikigai/{SPEC.md,MCP_GATEWAY.md,ikigai.bat,run_mcp_server.py,start_mcp_gateway.sh,langgraph.json,pyproject.toml}` | IKIGAi entry + manifest |
| `life-ops/ikigai/src/{agents,mcp_server,ikigai}/` | Deep-agent harness, MCP server, IKIGAi core |
| `life-ops/ikigai/data/matheus/{dreams,objectives,projects,deliverables,ikigai_state}/` | BYD case-study vault (PT-BR deliverables) |
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

If asked to refactor anything in `vibe-ops/`, `strategics/`, or a cluster doc: stop → propose Action Plan (every file touched, every string preserved, migration path) → wait for explicit user "go" → only then mutate, and verify every pre-existing string survives byte-for-byte. The append-only rule is enforced by this protocol.

<!-- gitnexus:start -->
## Code Intelligence — GitNexus

This project is indexed by GitNexus as **life**. Use GitNexus tools (`impact`, `query`, `context`) for symbol-level questions and standard Grep/Glob/Read for text and configs. GitNexus resources: `gitnexus://repo/life/{context,clusters,processes,process/<name>}`. Same blast-radius + `detect_changes()` discipline applies — see the GitNexus skills table above for tool/skill routing.

<!-- gitnexus:end -->
