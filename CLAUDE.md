# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in code in this repository.

> **Tooling split:** This file is Claude-Code-specific. The near-identical `AGENTS.md` is for
> Codex (Codex.ai/code). Both files MUST agree on the load-bearing invariants in
> §"Global Conventions" below. When they drift, this file wins for Claude Code.

---

## What This Repo Is

**Algorithmic Life OS** — a personal productivity orchestration system, 100% local, single-user, append-only.

Three subsystems, one kernel:

```
life/ (root) ── Typer CLI hub: centrals (task, knowledge, research) + handlers (daily, weekly) + plugins
   │
   ├── subprocess ──→ vibe-ops/   Cybernetic engine: Target→Sensor→Adjuster→Persist→Sync→Index
   │
   └── (no link)    life-ops/operational/  PAV productivity kernel (uv workspace — must stay decoupled)
```

**One app is under active development:** `life-ops/operational/` (the PAV productivity kernel).
Everything else is either a stable integration (`vibe-ops/`, `taskwarrior/`, `life_tatics/`) or
documentation (`strategics/`, `docs/`, `cluster docs`, `code-docs/`).

**Repo:** github.com/matheusmendes720/ikigai
**Project Board:** github.com/users/matheusmendes720/projects/5
**CI:** `.github/workflows/ci.yml` — runs `ruff check`, `ruff format --check`, `mypy src/`,
and `pytest -m "not e2e"` per package in a matrix.

---

## Recent Major Changes

Rolling highlights from the last few commits on the active branch (`gitbutler/workspace`):

- **`7bbb28f`** — chore: update `CLAUDE.md`, `README.md`, pre-commit config with TUI + v2_renderers. Docs aligned with the new 8-screen Textual TUI and the v2 design system widgets.
- **`8077bda`** — test(unit+tui): commit core, cli integration, e2e, home pause, report v2 flags, tui launch coverage. Suite now spans 72 pytest files (unit / integration / property / e2e / tui / ui).
- **`0908b5b`** — feat(tui): Textual screens and charts for analytics, dashboard, daily flow, habits, journal, metrics, policy, plus Help modal. BINDINGS `1`–`8` switch screens, `q` quits, `Ctrl+H` opens help.
- **`95f0d47`** — chore(cli): commit `seed`, `csv_loader`, `dataset_selector`, and the v2 formatters — the `pav demo seed` flow + `TIME_TASKER_DATASET=<name>` boot loader are now first-class.
- **`11397bf`** — chore(cli): commit `state`, `services`, `console`, `telemetry`, `home_v2`. The 15 `_PersistentRepo` singletons in `state.py` ship with cross-process mtime reload (`reload_stale_repos()`) so the TUI reflects CLI writes from other terminals within one refresh tick.

When picking up a refactor or adding a new screen/command, run `git log --oneline -20` first to spot the most recent contracts you must respect.

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
| **Error collection** | All handlers | Short-circuiting on partial failure — collect and report at end |
| **Typer over argparse** | New CLI surfaces in `life/` | argparse in root CLI; vibe-ops `main.py` is the only legacy argparse surface |

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

# CLI entry points — all three are equivalent
pav --help
pav-os --help
operational --help

pav home                                                     # interactive 10-item menu
pav tui                                                      # launch TUI (defaults to dashboard)
pav tui --screen daily_flow --debug --golden                 # screen/dataset/debug flags
pav doctor                                                   # health check
pav demo seed                                                # populate 7 days of mock data

# Quality gates (CI runs these per package — never commit red)
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
uv run pytest                          # full suite — markers: unit / integration / property / e2e / tui
uv run pytest tests/unit/cli -v        # narrow by directory
uv run pytest -k "test_qhe" -v         # narrow by test name
uv run pytest packages/core/tests/test_habit_engine.py::TestHabitEngine::test_qhe_composite -v   # fully qualified
uv run verify_sprint                   # the sprint verifier (scripts/verify_sprint.sh)
uv run pre-commit run --all-files      # gating hooks (ruff + mypy + whitespace)
```

**Test suite:** 72 pytest test files across `tests/` (unit/integration/property/e2e/tui/ui) — markers: `unit`, `integration`, `property`, `e2e`, `tui`. CI runs `pytest -m "not e2e"` per package. To get an exact test count after a refactor: `uv run pytest --collect-only -q | tail -1`.

### Vibe-ops cybernetic engine (`vibe-ops/`)

```bash
cd vibe-ops
python src/main.py run-daily [--date YYYY-MM-DD]              # argparse CLI
python src/main.py status
python src/vibe_cli.py hybrid_search "query"                  # Typer+Rich surface
python src/vibe_cli.py debt_dashboard
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
│   └── base.py         — BaseCentral.run_cli(cwd, module, args, json_out) returns {ok, stdout, stderr, data, error?}
└── plugins/            — Plugin discovery + lifecycle hooks; PluginProtocol in plugins/protocol.py
```

`BaseCentral.run_cli` (in `centrals/base.py`) is the integration glue — it shells out, parses
JSON, and returns a dict. Handlers calling centrals via `python -m life.cli <central> <cmd> --json`
is recursive by design: **handlers double as integration tests**.

### PAV kernel: 3-layer MVC inside a uv workspace

```
life-ops/operational/
├── packages/core/src/operational/        Layer 1 — pure logic, zero I/O, no Rich/Typer/Textual
│   ├── entities/                         15 Pydantic v2 models (frozen, extra=forbid, isolated — no cross-entity imports)
│   ├── core/                             habit_engine · policy_engine · pomodoro_machine · sleep_calculator · scenario_classifier · consolidator
│   ├── persistence/                      Repository Protocol + InMemory + SQLite + migrations
│   ├── parsers/                          YAML/frontmatter → Pydantic
│   └── reports/                          Markdown daily/weekly narrative generators
│
├── apps/cli/src/operational/cli/         Layer 3 — thin Typer controllers (15 sub-typers). All logic in core/.
│
├── apps/tui/src/operational/tui/         Textual TUI (8 screens + Help modal). PAVApp.SCREENS dict + BINDINGS in app.py.
│
└── tests/                                pytest (markers: unit / integration / property / e2e / tui)
```

**PAV persistence** lives in `apps/cli/src/operational/cli/state.py` — 15 `_PersistentRepo`
instances backed by JSON flat files in `~/.time-tasker/`. Each repo tracks the on-disk mtime
so the TUI's refresh loop can detect cross-process writes (e.g. a CLI mutation committed
from another terminal) via `_PersistentRepo.needs_reload()` / `reload_stale_repos()`.
TUI uses `switch_screen()` (pop+push) for top-level navigation, `push_screen()` only for
modal overlays (help). This prevents screen-stack leaks.

**Core algorithms are pure arithmetic** — the load-bearing formulas:

| Algorithm | Formula | Module |
|-----------|---------|--------|
| Habit consistency | `H(t) = 1 − e^(−λ·streak)` | `core/habit_engine.py` |
| Energy required | `E = R·(1 − H(t))` | `core/habit_engine.py` |
| Q_HE composite | weighted composite of H, E, streak | `core/habit_engine.py` |
| PolicyEngine FSM | 4 states + hysteresis: PUSH→MAINTAIN→REDUCE→RECOVER | `core/policy_engine.py` |
| Pomodoro SM | 8 states + scenario classifier | `core/pomodoro_machine.py` |

**Design tokens** (colors, glyphs, severity styles) live exclusively in
`apps/cli/src/operational/ui/tokens.py`. Never hardcode colors in components. The v2 widget
library is in `ui/components_v2.py` (~30 production widgets).

**CSV datasets** for visual/CLI regression are selected with `TIME_TASKER_DATASET=synthetic`
or `pav demo seed`. Datasets are defined in `apps/cli/src/operational/cli/dataset_selector.py`
(`golden` + `synthetic`).

### Vibe-ops: Target-Sensor-Adjuster loop

```
src/
├── main.py              argparse CLI: run-daily, status, gaps, sync
├── vibe_cli.py         Typer+Rich CLI: sync_file, hybrid_search, gaps, debt_dashboard
├── cybernetics/         CyberneticDailyLoop (the cybernetic engine itself)
├── middleware/          SyncEngine — the ONLY module touching all three systems
├── pipeline/            ~30 modules: policy_engine, ikigai_scorer, rag_indexer, …
├── models/              17 Pydantic entity modules
├── storage/             SQLite + ChromaDB + sqlite-vec + UEID manager
├── contracts/           YAML + Pydantic sync payloads
├── embeddings/          OpenAI / local / hash-moq provider abstraction
└── vibeops-tui/         Rust TUI (ratatui) — polls vibe_ops.db
```

**`SyncEngine`** (`src/middleware/sync_engine.py`) — the chokepoint that bridges
Obsidian ↔ SQLite ↔ Taskwarrior. UEID format is `<CLUSTER>:<ENTITY>:<ID>`
(e.g. `study:topic:st_python_01`). All keys are content-addressed (`upstream_id` SHA-256) so
re-runs are idempotent.

**PolicyEngine states (vibe-ops):**

| State | hardwork_budget | pause_min | sleep_target | Q_HE target |
|-------|-----------------|-----------|--------------|-------------|
| PUSH | 4.0 h | 10 min | 7.5 h | 0.85 |
| MAINTAIN | 2.5 h | 15 min | 8.0 h | 0.65 |
| REDUCE | 1.5 h | 20 min | 8.5 h | 0.45 |
| RECOVER | 0.5 h | 30 min | 9.0 h | 0.25 |

Severity (CRITICAL/HIGH/MEDIUM/LOW) = function of infractions + hours_deviation + consistency.
**Transitions have hysteresis** — no upward promotion without sustained performance.

### 3 Operational Clusters (cross-cutting)

Each cluster is a Standalone Memory Machine (self-contained, cross-referenced):

| Cluster | Canonical Doc | Focus |
|---------|---------------|-------|
| **PLAN** | `CLUSTER_PLAN.md` | Routines, habits, Q_HE, daily/weekly rhythm |
| **PROJECT** | `CLUSTER_PROJ.md` | PMO ↔ Taskwarrior, roadmap, changelog |
| **STUDIES** | `CLUSTER_STUDY.md` | PKM, prerequisites graph, cognitive debt |

Meta-brain: IKIGAi (5 vectors: Passion, Skill, Market, Revenue, Course) — implemented across
`vibe-ops/base/IKIGAi.md` (conceptual) and `life-ops/planner/ikigai_planning/` (mathematical specs).

**Other cross-cutting prose:** `CONCEPTUAL_MODEL.md` (Tensão→Comportamento→Solução,
5 tensões, 4 regimes), `SYSTEMS_TOPOLOGY.md` (middleware M1–M8, cybernetic loop),
`ARCHITECTURE_INDEX.md` (master index, 50+ cross-refs).

---

## Subsystem map (one-line per dir)

| Subdir | Role | Status | Package manager |
|--------|------|--------|-----------------|
| `life-ops/operational/` | **PAV productivity kernel** | 🟢 Active | uv workspace |
| `life-ops/life_tatics/` | Standalone time-block planner | 🟡 Stable | Poetry |
| `life-ops/planner/`, `life-ops/ikigai/` | IKIGAi drilldown + math specs | 🟡 Stable | — |
| `vibe-ops/` | Cybernetic engine (Target-Sensor-Adjuster) | 🟡 Stable | uv |
| `taskwarrior/` | TW binary + scripts + config consumed by `life/` centrals | 🟢 Stable | — |
| `code-docs/{prd,brd,ard,adr}/` | Product / business / arch requirements | 🟡 Stable | — |
| `strategics/` | PT-BR strategy docs (frameworks, models) | 🟢 Read-only | — |
| `docs/`, `diagrams/` | Master reading index + Mermaid source | 🟢 Read-only | — |
| `logs/` | Runtime stdout/stderr | — | — |

---

## Testing Strategy

| Subtree | Test location | Runner | Notes |
|---------|---------------|--------|-------|
| Root `life/` | No test dir at root; tests live in submodules | `python -m life.cli test` | Discovers across all `cfg.submodules` |
| `life-ops/operational/` | `tests/` (also per-package `tests/`) | `uv run pytest` | Markers: `unit` / `integration` / `property` / `e2e` / `tui`. CI runs `pytest -m "not e2e"`. |
| `vibe-ops/` | `tests/` | `pytest` | In-memory SQLite + mocked ChromaDB |

**`vibe-ops/scratch/`** has informal `test_*.py` exploration scripts — **NOT** part of the
official suite. Do not run them as tests. The spec is at `vibe-ops/SPEC.md`.

**Adding tests:** place in the right `tests/` directory; use pytest fixtures; mock
external services (ChromaDB, Taskwarrior, network).

---

## Where to Start (by task)

| Task | Start here |
|------|-----------|
| New to the codebase | `README.md` → `ARCHITECTURE_INDEX.md` → relevant cluster doc |
| Implementing in PAV | `life-ops/operational/SPEC.md` → `packages/core/src/operational/` |
| Running the daily/weekly loop | `life-ops/operational/` → `pav home` (interactive) or `pav tui --screen <name>` |
| Touching `vibe-ops/` | Read the **Append-Only Rule** (§Global Conventions) before writing anything |
| Tracing a bug through 3 systems | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Renaming / extracting a symbol | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` (never grep+replace) |
| Auditing blast radius before edit | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Designing a feature | `superpowers:brainstorming` before `EnterPlanMode` |
| PR review | `python .github/scripts/code_review.py --base <branch> --review-format` (invoked by CI) |

---

## Claude-Code-Specific Operations

### Claude Flow v3 Hook Pipeline (`.codex/`)

This project wires the Claude Flow v3 hook chain through `.codex/hooks.json` (139 lines, 8 hook
types) and `.codex/config.toml`. When `CLAUDE_FLOW_V3_ENABLED=true` and `CLAUDE_FLOW_HOOKS_ENABLED=true`
are set (see `[shell_environment_policy.set]` in `.codex/config.toml`), every Claude Code session in
this repo runs through the chain:

| Hook event | Fires on | Handler |
|------------|----------|---------|
| `PreToolUse` (Bash) | every Bash invocation | `hook-handler.cjs pre-bash` — pre-flight risk check |
| `PreToolUse` (Write/Edit/MultiEdit) | every edit | `hook-handler.cjs pre-edit` — blast-radius probe |
| `PostToolUse` (Write/Edit/MultiEdit) | every edit | `hook-handler.cjs post-edit` — auto-memory persist |
| `PostToolUse` (Bash) | every Bash invocation | `hook-handler.cjs post-bash` — outcome capture |
| `PreCompact` (manual / auto) | context compaction | `hook-handler.cjs compact-*` + `session-end` |
| `SessionStart` | new session | `hook-handler.cjs session-restore` + `auto-memory-hook.mjs import` |
| `UserPromptSubmit` | every user turn | `hook-handler.cjs route` — task → optimal model/tier |
| `SubagentStart` / `SubagentStop` | subagent lifecycle | `hook-handler.cjs status` / `post-task` |
| `Stop` | session end | `auto-memory-hook.mjs sync` — flush to `.swarm/memory.db` |

The handler chain lives in `.claude/helpers/hook-handler.cjs` (project-local) with a fallback to
`%USERPROFILE%\.claude\helpers\hook-handler.cjs` (user-global). If a hook blocks, it surfaces in the
transcript with the failing command — investigate that line before retrying. The
`hook-handler.cjs pre-bash` step is the one most likely to refuse commands it classifies as
risky (e.g. bulk `rm`, force-push, secret exfiltration patterns).

### Skills (`.claude/skills/`)

Loaded via the `Skill` tool — **never read them with file tools** (the harness loads them with
full activation context). Load `superpowers:using-superpowers` before any non-trivial task.

### SessionStart hook (auto-runs)

A `SessionStart:startup` hook instructs Claude Code to always use `codebase-memory-mcp` tools
**first** for code exploration: `search_graph`, `trace_path`, `get_code_snippet`, `query_graph`,
`get_architecture`, `search_code`. Fall back to `Grep`/`Glob`/`Read` only for text, configs,
and non-code files.

The repo is indexed by **GitNexus** as project `life` (symbols, relationships, execution flows).
Skill paths are at `.claude/skills/gitnexus/` (NOT `.Codex/` — that path in older docs is
Codex-only):

| Task | Skill |
|------|-------|
| Architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tool reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |

**Before editing any symbol:** run blast-radius analysis. If HIGH or CRITICAL, do not proceed
without user approval. **Before committing:** verify with `detect_changes()` that only expected
symbols / flows are affected. Never use find-and-replace for renames — use the GitNexus
`rename` tool.

If the GitNexus index is stale, run `node .gitnexus/run.cjs analyze` from project root. No
`.gitnexus/run.cjs`? Try `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`).

---

## Refactor Protocol (for `vibe-ops/` and append-only surfaces)

If asked to refactor anything in `vibe-ops/`, `strategics/`, or a cluster doc:

1. **Stop** — do not start editing.
2. **Propose an Action Plan** — list every file to touch, every string to preserve, the migration path.
3. **Wait for the Approval Gate** — explicit user "go".
4. **Only then mutate** — and verify every pre-existing string survives byte-for-byte.

This applies to renames, splits, extractions, and re-organizations. The append-only rule
(§Global Conventions) is enforced by this protocol.

---

## Security & Deployment

- **Fully local / air-gapped by design.** No API keys, OAuth, or network services required for
  core operation.
- SQLite databases (`vibe_ops.db`, `test_vibe.db`) and ChromaDB (`chroma_db/`) reside inside
  the working directory.
- No secrets-management infrastructure present.
- Deployment is manual: run PowerShell scripts or Python modules directly on the host machine.
- The Rust TUI reads from `../vibe_ops.db` relative to its executable location.

---

*When in doubt: the README has the full subsystem map; AGENTS.md has the parallel Codex
view; this file governs Claude-Code-specific ops + the load-bearing invariants.*
