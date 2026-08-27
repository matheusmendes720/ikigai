# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What This Repo Is

**Algorithmic Life OS** — a personal productivity orchestration system, 100% local, single-user, append-only.

Three subsystems, one kernel:

```
life/ (root) ── Typer CLI hub: centrals + handlers + plugins
   │
   ├── subprocess ──→ vibe-ops/   Cybernetic engine: Target→Sensor→Adjuster→Persist→Sync→Index
   │
   └── (no link)    life-ops/operational/  PAV productivity kernel (uv workspace — decoupled)
```

**One app is under active development:** `life-ops/operational/` (the PAV productivity kernel).
Everything else is either a stable integration (`vibe-ops/`, `taskwarrior/`, `life_tatics/`) or
documentation (`strategics/`, `docs/`, `cluster docs`, `code-docs/`).

**Repo:** github.com/matheusmendes720/ikigai
**Project Board:** github.com/users/matheusmendes720/projects/5
**CI:** `.github/workflows/ci.yml` — runs `ruff check`, `ruff format --check`, `mypy src/`, and `pytest -m "not e2e"` per package in a matrix.

---

## Recent Major Changes

Rolling highlights from the last few commits on the active branch (`gitbutler/workspace`):

- **`1d9479a`** — docs(observability): add 4 specs for next steps (server-side reliability, smoke test, merge plan, worktree dissolve). Specs live at `life-ops/ikigai/docs/observability/0{1..4}-*.md`.
- **`0e528d0`** — feat(observability): IKIGAI server-side stack tracing via `init_tracing()` + `@observed_tool` decorator. Spans flow to LangSmith + Langfuse when `OTEL_ENABLED=true`.
- **`87f6ef9`** — feat(reliability): client-side retry + circuit-breaker + scoped cache invalidation in `src/agents/tools.py`. CB-outer / retry-inner so CB counts logical calls (not attempts).
- **`ca4e65c`** — feat(propagation): `SQLiteAdapter.upsert()` with append-only history.
- **`0ff111d`** — refactor(commit, mcp-server): route plan entity writes through `SQLiteAdapter` (resolves the canonical-24 vs runtime-11 schema split-brain).
- **`eeac3aa`** — chore(scripts): `migrate_plan_entities.py` for legacy 11-col DBs.
- **`fd4b8dd`** — feat(entities): add UEID primitive type with 5-part format validator (`<CLUSTER>:<ENTITY>:<ID>`).
- **`20f1e72`** — chore(observability): wire OpenTelemetry SDK to LangSmith + Langfuse via OTLP/HTTP (single SDK, two exporters).
- **`604d6af`** — **chore: delete PAV UI** — `apps/cli`, `apps/tui`, `home_v2`, `dataset_selector`, TUI widgets, theme tokens removed. `packages/core` is now the sole workspace member. The `operational` / `pav` / `pav-os` console scripts are **broken** (their editable-install `.pth` still points at the deleted `apps/cli/src`). Tests under `tests/unit/cli/` fail until the CLI is restored.

**Observability sprint status (4 repos):** IKIGAI (`gitbutler/workspace` ← `life-mcp-observability-worktree`, 8 commits) ✅ dual export + reliability + stack tracing. `apps/kanban/tuiboard` `feat/otel-tracing` ✅ dual export wired (`2c39867` fix). `apps/dev-tools/taskdog` `feat/otel-tracing` ✅ dual export wired. `apps/calendar/solverforge-calendar` `feat/otel-tracing` ✅ dual export wired (built on top of `feat/rust-build-fix`). Merges gated by Spec 03 + Spec 02.

---

## Global Conventions (load-bearing invariants)

Violations break the system. Re-read before any non-trivial edit.

| Rule | Where it applies | What it forbids |
|------|------------------|-----------------|
| **Standalone** | `life-ops/operational/` | Imports from root `life/` or `vibe-ops/` — must remain decoupled |
| **Append-only** | `vibe-ops/`, `strategics/`, all cluster docs | Deleting, pruning, or rewriting existing content; reorg only if every string survives intact |
| **Zero LLM** | Daily/weekly pipelines | NLP / LLM calls in the hot path — pure arithmetic only |
| **`--json` everywhere** | All new CLI commands | A new subcommand without machine-readable output |
| **Pydantic v2 strict** | All data schemas | `frozen=True`, `extra="forbid"`, strict mode — non-negotiable |
| **Idempotent pipelines** | Sync, indexing, persist stages | Non-deterministic writes — keys must be `upstream_id` / `ueid` |
| **Fully local** | The whole repo | Cloud deps, API keys, OAuth — SQLite + filesystem only |
| **PT-BR ↔ EN split** | Prose vs code | Strategic prose in Portuguese; code, file names, AI specs in English |

---

## Build / Run / Test

### Root CLI hub (`life/`)

From repo root:

```bash
# Test discovery across submodules
python -m life.cli test                 # discover + run pytest across submodules
python -m life.cli test -s <name>       # one submodule
python -m life.cli test --list          # list discovered test dirs

# Handlers / centrals (run from repo root; root __init__.py enables `python -m life.cli`)
python -m life.cli daily run [--skip-task]
python -m life.cli weekly run [--skip-review] [--skip-metrics]
python -m life.cli task today --json
python -m life.cli health
```

### PAV kernel (`life-ops/operational/`) — primary dev target

This is a **uv workspace** (single root `pyproject.toml`; per-package `pyproject.toml`s). Poetry is not used here.

```bash
cd life-ops/operational
uv sync                                                      # install whole workspace

# CLI entry points — all three are equivalent (NOTE: currently broken — see PAV CLI note below)
pav --help
pav-os --help
operational --help

pav home                                                     # interactive 10-item menu (broken)
pav tui                                                      # launch TUI (broken)
pav tui --screen daily_flow --debug --golden                 # screen/dataset/debug flags (broken)
pav doctor                                                   # health check (broken)
pav demo seed                                                # populate 7 days of mock data (broken)

# Quality gates (CI runs these per package — never commit red)
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
uv run pytest                          # full suite — markers: unit / integration / property / e2e / tui
uv run pytest tests/unit/cli -v        # narrow by directory
uv run pytest -k "test_qhe" -v        # narrow by test name
uv run pytest --collect-only -q | tail -1   # exact test count
uv run pre-commit run --all-files      # gating hooks (ruff + mypy + whitespace)
# `uv run verify_sprint` is .sh-only — use `bash scripts/verify_sprint.sh`
```

**Test suite:** 74 pytest test files across `tests/` (unit/integration/property/e2e/tui) — markers in `pytest.ini`: `unit`, `integration`, `property`, `e2e`, `slow`. CI runs `pytest -m "not e2e"` per package.

### Vibe-ops cybernetic engine (`vibe-ops/`)

```bash
cd vibe-ops
python src/main.py run-daily [--date YYYY-MM-DD]              # argparse CLI
python src/main.py status
python src/vibe_cli.py hybrid_search "query"                  # Typer+Rich surface
cd vibeops-tui && cargo run                                   # Rust TUI polling ../vibe_ops.db
```

`run_loop.ps1` is the Windows launcher for the daily loop.

### Life-tatics (`life-ops/life_tatics/`)

```bash
cd life-ops && poetry install && poetry run life-tatics --help
```

### LangGraph dev workflow (Makefile)

```bash
make help                                                    # show targets
make dev                                                     # langgraph dev server on :2024
make dev-graph NAME=planner                                  # run one graph
make test                                                    # full cross-workspace pytest
make logs / make status / make clean
```

---

## Architecture — Big Picture

### Root CLI: central-handler pattern

```
life/
├── cli/cli.py          — Typer app root; mounts centrals, handlers, plugins
├── cli/config.py       — LifeConfig dataclass; YAML + env loading
├── cli/log.py          — Structured logger
├── handlers/           — daily.py, weekly.py (call centrals via subprocess)
├── centrals/           — Thin domain wrappers (delegate to external submodules)
│   └── base.py         BaseCentral.run_cli(cwd, module, args, json_out) returns {ok, stdout, stderr, data, error?}
└── plugins/            — Plugin discovery + lifecycle hooks; PluginProtocol in plugins/protocol.py
```

`BaseCentral.run_cli` (in `centrals/base.py`) is the integration glue — it shells out, parses JSON, and returns a dict. Handlers calling centrals via `python -m life.cli <central> <cmd> --json` is recursive by design: **handlers double as integration tests**.

### PAV kernel: packages/core only (apps/cli and apps/tui deleted)

```
life-ops/operational/
├── packages/core/src/operational/        Pure logic, zero I/O, no Rich/Typer/Textual
│   ├── entities/                         15 Pydantic v2 models (frozen, extra=forbid, isolated — no cross-entity imports)
│   ├── core/                             habit_engine · policy_engine · pomodoro_machine · sleep_calculator · consolidator
│   ├── persistence/                      Repository Protocol + InMemory + SQLite + migrations
│   ├── parsers/                          YAML/frontmatter → Pydantic
│   ├── reports/                          Markdown daily/weekly narrative generators
│   └── agents/                           harness · orchestrator · workflows (owns reload_stale_repos())
│
├── apps/cli/src/operational/cli/         DELETED in 604d6af — CLI broken
├── apps/tui/src/operational/tui/          DELETED in 604d6af — TUI broken
└── tests/                                74 pytest files (unit/integration/property/e2e/tui)
```

**PAV CLI is currently broken.** `uv run pav`, `uv run operational`, `python -m operational` all fail because the editable-install `.pth` files point to the deleted `apps/cli/src`. Tests in `tests/unit/cli/` fail. Restoration is needed before the PAV CLI works again.

**Core algorithms are pure arithmetic** — the load-bearing formulas:

| Algorithm | Formula | Module |
|-----------|---------|--------|
| Habit consistency | `H(t) = 1 − e^(−λ·streak)` | `core/habit_engine.py` |
| Energy required | `E = R·(1 − H(t))` | `core/habit_engine.py` |
| Q_HE composite | weighted composite of H, E, streak | `core/habit_engine.py` |
| PolicyEngine FSM | 4 states + hysteresis: PUSH→MAINTAIN→REDUCE→RECOVER | `core/policy_engine.py` |
| Pomodoro SM | 8 states + scenario classifier | `core/pomodoro_machine.py` |

### Vibe-ops: Target-Sensor-Adjuster loop

```
src/
├── main.py              argparse CLI: run-daily, status, gaps, sync
├── vibe_cli.py          Typer+Rich CLI: sync_file, hybrid_search, gaps
├── cybernetics/         CyberneticDailyLoop (the cybernetic engine itself)
├── middleware/          SyncEngine — the ONLY module touching all three systems
├── pipeline/            ~30 modules: policy_engine, ikigai_scorer, rag_indexer, …
├── models/              17 Pydantic entity modules
├── storage/             SQLite + ChromaDB + sqlite-vec + UEID manager
├── contracts/           YAML + Pydantic sync payloads
├── embeddings/          OpenAI / local / hash-moq provider abstraction
└── vibeops-tui/         Rust TUI (ratatui) — polls vibe_ops.db
```

**`SyncEngine`** (`src/middleware/sync_engine.py`) — the chokepoint bridging Obsidian ↔ SQLite ↔ Taskwarrior. UEID format: `<CLUSTER>:<ENTITY>:<ID>` (e.g. `study:topic:st_python_01`). All keys are content-addressed (`upstream_id` SHA-256) so re-runs are idempotent.

**PolicyEngine states (vibe-ops):**

| State | hardwork_budget | pause_min | sleep_target | Q_HE target |
|-------|-----------------|-----------|--------------|-------------|
| PUSH | 4.0 h | 10 min | 7.5 h | 0.85 |
| MAINTAIN | 2.5 h | 15 min | 8.0 h | 0.65 |
| REDUCE | 1.5 h | 20 min | 8.5 h | 0.45 |
| RECOVER | 0.5 h | 30 min | 9.0 h | 0.25 |

Severity (CRITICAL/HIGH/MEDIUM/LOW) = function of infractions + hours_deviation + consistency. **Transitions have hysteresis** — no upward promotion without sustained performance.

### 3 Operational Clusters (cross-cutting)

Each cluster is a Standalone Memory Machine (self-contained, cross-referenced):

| Cluster | Canonical Doc | Focus |
|---------|---------------|-------|
| **PLAN** | `CLUSTER_PLAN.md` | Routines, habits, Q_HE, daily/weekly rhythm |
| **PROJECT** | `CLUSTER_PROJ.md` | PMO ↔ Taskwarrior, roadmap, changelog |
| **STUDIES** | `CLUSTER_STUDY.md` | PKM, prerequisites graph, cognitive debt |

Meta-brain: IKIGAi (5 vectors: Passion, Skill, Market, Revenue, Course) — implemented across `vibe-ops/base/IKIGAi.md` (conceptual) and `life-ops/planner/ikigai_planning/` (mathematical specs).

### LangGraph Integration

`langgraph.json` at root registers 6 graphs via `vibe-ops/src/langgraph_entry.py`:
`pae_maintainer`, `quarterly_replan`, `test_de_fogo_rollup`, `correction_protocol`, `dream_falsification`, `ikigai_maintainer`.

---

## Subsystem Map

| Subdir | Role | Status | Package manager |
|--------|------|--------|-----------------|
| `life-ops/operational/` | **PAV productivity kernel** (packages/core only) | 🟡 Restoring CLI | uv workspace |
| `life-ops/life_tatics/` | Standalone time-block planner | 🟡 Stable | Poetry |
| `life-ops/planner/`, `life-ops/ikigai/` | IKIGAi drilldown + math specs | 🟡 Stable | — |
| `vibe-ops/` | Cybernetic engine (Target-Sensor-Adjuster) | 🟡 Stable | uv |
| `taskwarrior/` | TW binary + scripts + config consumed by `life/` centrals | 🟢 Stable | — |
| `code-docs/{prd,brd,ard}/` | Product / business / arch requirements | 🟡 Stable | — |
| `strategics/` | PT-BR strategy docs (frameworks, models) | 🟢 Read-only | — |
| `docs/`, `diagrams/` | Master reading index + Mermaid source | 🟢 Read-only | — |
| `logs/` | Runtime stdout/stderr | — | — |

---

## Where to Start (by task)

| Task | Start here |
|------|-----------|
| New to the codebase | `ARCHITECTURE_INDEX.md` → relevant cluster doc |
| Implementing in PAV | `life-ops/operational/SPEC.md` → `packages/core/src/operational/` |
| Restoring PAV CLI | `life-ops/operational/` — `apps/cli/src` was deleted in `604d6af` |
| Running the daily/weekly loop | `life-ops/operational/` — CLI currently broken (see note above) |
| Touching `vibe-ops/` | Read the **Append-Only Rule** (§Global Conventions) before writing anything |
| Tracing a bug through 3 systems | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Renaming / extracting a symbol | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` (never grep+replace) |
| Auditing blast radius before edit | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |

---

## Pitfalls (from AGENTS.md — read before acting)

- **PAV CLI is broken.** `uv run pav`, `uv run operational`, `python -m operational` all fail post-`604d6af`. Editable-install `.pth` files under `.venv/Lib/site-packages/` still point at the deleted `apps/cli/src`. Tests in `tests/unit/cli/` fail. Verify restoration scope before recommending changes.
- **Orphaned test dirs.** `tests/tui/` and `tests/ui/` survive but their source was deleted in `604d6af` — expect collection errors or skips.
- **Stray 0-byte files at repo root.** Names like `2`, `0`, `4}`, `dict[str`, `ISO`, `None`, `String`, `bool`, `new` are untracked crash/typo artifacts. Don't read them.
- **Throwaway files at `life-ops/operational/` root** (`output.txt`, `CheckResult`, `not`, etc.) are not source — don't open or add new ones.
- **Two CLAUDE.md files** (`CLAUDE.md` root + `life-ops/operational/CLAUDE.md`) describe overlapping scopes; verify against `git log` + filesystem.
- **`ikigai.bat` venv path.** The launcher hard-codes `.venv\Scripts\python.exe`; if you recreate the venv with `poetry env remove` + `poetry install`, the .bat still finds it — but renaming `.venv/` breaks it silently.
- **`scripts/verify_sprint.sh` vs `uv run verify_sprint`.** Only `.sh` exists; `uv run verify_sprint` fails. Use `bash scripts/verify_sprint.sh`.
- **`life-ops/operational/` is a uv workspace, not Poetry.** The Makefile `test` target uses `poetry run pytest` for this workspace — that only works by accident. Use `cd life-ops/operational && uv run pytest` instead.

---

## Claude Code–Specific Operations

### Hook Pipeline (`.claude/hooks/`)

Project-level hooks live in `.claude/hooks/` with fallback to `%USERPROFILE%\.claude\helpers\`. See `.claude/hooks/README.md` for the full hook chain.

### Skills (`.claude/skills/`)

Loaded via the `Skill` tool — **never read them with file tools** (the harness loads them with full activation context). Load `superpowers:using-superpowers` before any non-trivial task.

Key skills for this repo:

| Task | Skill |
|------|-------|
| Tracing bugs | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Blast radius before edit | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Renaming / extracting symbols | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tool reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |

### Refactor Protocol (vibe-ops / append-only surfaces)

If asked to refactor anything in `vibe-ops/`, `strategics/`, or a cluster doc: **stop** → propose Action Plan (every file to touch, every string to preserve, migration path) → wait for explicit user "go" → only then mutate, and verify every pre-existing string survives byte-for-byte.

### GitNexus

The repo is indexed by GitNexus as project `life` (symbols, relationships, execution flows). Before editing any symbol: run blast-radius analysis. If HIGH or CRITICAL, do not proceed without user approval. Never use find-and-replace for renames — use the GitNexus `rename` tool. If the index is stale: `node .gitnexus/run.cjs analyze` from project root.

---

*Algorithmic Life OS — CLAUDE.md — 2026-08-27*
