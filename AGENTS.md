# AGENTS.md

Algorithmic Life OS — a personal productivity orchestration system, 100% local, single-user, append-only at the vault layer.

## What This Repo Is

**Algorithmic Life OS** — a personal productivity orchestration system, 100% local, single-user, append-only.

**Three layers:**

```
┌─────────────────────────────────────────────────────────────┐
│  INTERFACE LAYER  —  CLI/TUI consumers (CLI v2, Textual   │
│  5-tab TUI) — read from data/, write feedback              │
└──────────────────────────────┬──────────────────────────────┘
                               │ MCP / stdio
┌──────────────────────────────▼──────────────────────────────┐
│  AGENT LAYER  —  Deep Agent (carro-chefe)                 │
│  Reads vault/ → applies strategics + planning → writes     │
│  tasks to data/ → observes planned vs actual → updates     │
│  vault (PAE math stripped per ADR-013 — planner-only)       │
└──────────────────────────────┬──────────────────────────────┘
                               │ contracts (Pydantic)
┌──────────────────────────────▼──────────────────────────────┐
│  DATA LAYER  —  vault/ + data/ + vibe-ops/               │
│  vault/: markdown source of truth (Obsidian-style)         │
│  data/: runtime state (SQLite, chroma, boulder.json)       │
│  vibe-ops/: cybernetic engine (vector store + evidence)    │
└─────────────────────────────────────────────────────────────┘
```

**Canonical flow:** `vault` (NL planning) → Deep Agent → MCP Gateway → interfaces → manual feedback → Deep Agent observes gap → updates `vault`.

**Repo:** github.com/matheusmendes720/ikigai
**Project Board:** github.com/users/matheusmendes720/projects/5

## Global Conventions

| Rule | What it forbids |
|------|----------------|
| **Deep Agent is the only writer to `vault/`** | Interfaces only read vault; user feedback goes to `data/feedback.jsonl`, fork writes go to `data/review_queue/` |
| **Append-only** | Never delete/prune in `vault/`, `vibe-ops/`, `strategics/` |
| **Contracts in `src/contracts/`** | Pydantic v2 strict (`frozen=True`, `extra="forbid"`) imported from one place |
| **Zero LLM in pipeline** | Daily/weekly pipelines are pure arithmetic |
| **`--json` everywhere** | Every CLI command supports `--json` |
| **Fully local** | SQLite + filesystem only, zero cloud deps |

## Current Mode

**Data-first methodology** — IKIGAI is paused for *new algorithm decisions* (M01/N01/A02/A06, IKIGAI vector weights). Do not write new algorithm code until 5+ SONHO logs land in `vault/ikigai/closing-2026/<quarter>/04-relatórios-diários/`. The "pausado" directive applies to **algorithm decisions only** — agent/harness plumbing and Drift net work are NOT paused.

### Planning Note channel (human → agent)

- **Template:** `vault/ikigai/templates/sonho-log.md` (1 section: `## Mudança`)
- **Trigger:** manual only, after any planning delta
- **Cadence:** event-driven (NOT daily). 1–3 bullets per note, <2 min
- **Where:** `vault/ikigai/closing-2026/<quarter>/04-relatórios-diários/YYYY-MM-DD.md`

## Setup commands

- Python: 3.11+ (see `.python-version`)
- Editable install: `pip install -e ".[dev,mesh]"` (root)
- `src/ikigai/` (Poetry): `cd src/ikigai && poetry install`
- `vibe-ops/` (uv): `cd vibe-ops && uv sync`
- Run the CLI: `python -m life.cli --help` (or `life` after editable install)
- LangGraph dev: `make install && make dev` (port 2024)

## Build / Test / Lint

- Build: setuptools auto-discovery via `pyproject.toml` (`packages = ["life", ...]`)
- Test: `pytest tests/ -v` (root; Phase 3 mesh + contracts + integration). Submodule suites: `cd src/ikigai && poetry run pytest`, `cd vibe-ops && uv run pytest`
- Phase 3 v1 e2e driver: `bash scripts/smoke/phase3_v1.sh` (or `scripts\smoke\phase3_v1.bat` on Windows)
- Lint: `ruff check .` (`[tool.ruff]` in `pyproject.toml`)
- Typecheck: `mypy .` (`mypy.ini` at root, `mypy_path = src .. ../..`)
- Pre-commit: `pre-commit run --all-files` (`.pre-commit-config.yaml` at root)
- Console scripts declared in root `pyproject.toml`: `life` → `life.cli:_main_console`, `td` → `src.mesh.taskdog_cli:main`

## Project layout

- `life/` — meta-package (`cli/`, `centrals/`, `handlers/`, `plugins/`, `plugins/builtin/`)
- `src/` — three independent Python subpackages: `ikigai/` (Poetry, MCP/deep-agent), `mesh/` (uv, Phase 3 data mesh), `contracts/` (canonical Pydantic v2), `life_tatics/`, `planner/`
- `sys_ikigai/` — bare-namespace entities, gateway, state machines, vault, security, adapters
- `vibe-ops/` — cybernetic engine (Target→Sensor→Adjuster loop, SQLite, ChromaDB)
- `interfaces/{cli,tui}/` — consumer surfaces
- `vault/` — primary notes layer (Obsidian-style markdown, append-only)
- `data/` — runtime state (`vibe_ops.db`, `vibe_mesh.db`, `boulder.json`, `chroma_db/`, `review_queue/`)
- `scripts/smoke/` — Phase 3 v1 driver + other smoke tests
- `code-docs/{prd,brd,adr,ard}/`, `docs/`, `diagrams/`, `specs/` — requirements + architecture
- `archive/legacy-pav/` — superseded PAV kernel (do not edit)
- `strategics/`, `taskwarrior/`, `tools/`, `examples/`, `reports/`, `notes/`, `openwiki/`, `logs/` — supporting

## Tooling split (do not mix)

| Subpath | Build system | Notes |
|---|---|---|
| root + `src/contracts/`, `src/mesh/`, `src/life_tatics/` | setuptools / plain Python | `src/` on `PYTHONPATH` (set by `pytest.ini`) |
| `src/ikigai/` | Poetry | has its own venv; launcher `ikigai.bat` |
| `vibe-ops/` | uv | owns its own lockfile |
| `archive/legacy-pav/src-operational/` | archived | do not revive |

## Code style

- Python 3.11+, `from __future__ import annotations` at top of every module
- Pydantic v2 strict: `frozen=True`, `extra="forbid"` for all shared contracts in `src/contracts/`
- Single source of truth for shared models: `src/contracts/{common,task,task_change,planning,metrics}.py` — never re-define `UEID`, `Task`, `TaskChange`, etc.
- CLI: Typer sub-apps, `--json` everywhere feasible
- UEID format: 4-part `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` per `code-docs/adr/ADR-014-ueid-canonical-format.md`

## Testing instructions

- Unit + integration: `pytest tests/ -v` from repo root (120 root tests, Phase 3 scope)
- Submodule suites: `cd src/ikigai && poetry run pytest`, `cd vibe-ops && uv run pytest`
- Drift net: `src/ikigai/tests/test_canonical_scope.py` + `test_drift_invariants.py` + `test_drift_extended_invariants.py` — invariant tests are append-only, never delete
- E2E: `bash scripts/smoke/phase3_v1.sh` (isolated temp dir, does not touch real `data/`)
- Add a test for every new behavior in the same package as the code

## Architectural rules (load-bearing)

- **Append-only:** `vault/`, `vibe-ops/`, `strategics/` — never delete or prune. Refactor protocol: stop → propose Action Plan → wait for "go" → only then mutate
- **IKIGAI is planner-only** per ADR-013 — no PAV math/policy/scoring tools in agent layer (`IKIGAI_TOOLS` count guarded by drift test)
- **Deep Agent is the sole writer to `vault/`** (per ADR-012) — interfaces read only
- **Phase 3 mesh v1** ships `create` action only; `update`/`delete`/`done` are out of scope
- **Vault dual-tree identity:** `from src.contracts.X` vs `from sys_ikigai.X` resolve through `<repo>/src` and `<repo>/sys_ikigai` respectively; both work via `tests/conftest.py`. When monkeypatching in tests, patch BOTH
- **No secrets in repo** — `.env` is gitignored; `.env.example` is the template

## PR & commit conventions

- Branch from `main`; never push to it directly
- Conventional commits: `feat:` / `fix:` / `docs:` / `refactor:` / `chore:` / `test:`
- Drift tests are append-only — when crossing an invariant boundary, add a test in `test_drift_extended_invariants.py` instead of weakening an existing one

## Pitfalls

- `make test` is partially broken — it references removed `langgraph_tests/` and `src/operational/`. Use `pytest tests/ -v` directly
- Zero-byte root artifacts (`0`, `14`, `agent('Execute`, etc.) are stray bash-redirect typos — do not edit, leave gitignored
- `strategics/planning-with-files` submodule is intentionally dirty (vendored third-party); do not commit its contents
- Root `CLAUDE.md` and archived `archive/legacy-pav/src-operational/CLAUDE.md` describe overlapping scopes; verify against `git log -- <path>` for ground truth

## Architecture — Key Pieces

### Canonical Contracts (`src/contracts/`)

Shared Pydantic v2 models. All layers import from here.

| Module | Models |
|--------|--------|
| `common.py` | `UEID`, `Period`, `Priority`, `EntityType`, `RegimeState` |
| `task.py` | `Task`, `Subtask`, `ChecklistItem`, `Project`, `Milestone`, `Deliverable` |
| `task_change.py` | `TaskChange`, `PropagationEvent`, `TaskAction` (Phase 3 v1) |
| `planning.py` | `PlanningCycle`, `Wave`, `Sprint`, `VaultEvent` |
| `metrics.py` | `Burndown`, `ExecutionRate`, `QHEScore` |

### Data Mesh (`src/mesh/`) — Phase 3 v1

Cross-fork task view + bidirectional sync via Deep Agent gateway. **v1 scope = `create` action only.**

- **UEID** is the canonical join key: 4-part regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` per ADR-014
- **Write path:** fork → CLI enqueues `TaskChange` to `data/review_queue/` → Agent validates → propagates `PropagationEvent` to all forks
- **Read path:** `life mesh show <ueid>` joins slices from all 3 adapters
- **3 adapters** (all implement `ForkAdapter` Protocol): `CliAdapter` (`data/tasks.jsonl`), `TaskdogAdapter` (SQLite UPSERT on ueid), `SolverforgeCalendarAdapter` (UPI ueid column)
- **v1.2+ still out of scope:** `update`, `delete`, `done` actions

### Vibe-ops: Target-Sensor-Adjuster Loop

`vibe-ops/src/cybernetics/engine.py` is the current cybernetic kernel (TARGET → SENSOR → ADJUSTER → PERSIST → SYNC → INDEX).
PolicyEngine states: PUSH / MAINTAIN / REDUCE / RECOVER with hysteresis.
IKIGAI agent does **not** execute this loop — it observes feedback only.

### MCP Gateway

`src/ikigai/MCP_GATEWAY.md` documents the surface. Key tools: `read_vault(path)`, `write_planning(cycle_id, tasks)`, `sync_interfaces()`, `get_metrics()`. The agent is the **sole** vault writer (ADR-012).

## Drift Invariants & Tests

The Drift net is the regression guard for canonical contracts. **If a contributor changes a load-bearing invariant without explicitly bumping the contract version, CI fails.**

| File | Purpose |
|------|---------|
| `src/ikigai/tests/test_canonical_scope.py` | IKIGAI_TOOLS count, planner-only scope (no PAE math), fork MCP surface |
| `src/ikigai/tests/test_drift_invariants.py` | UEID 4-part regex, append-only invariants, dual-tree identity |
| `src/ikigai/tests/test_drift_extended_invariants.py` | Wave 3+ invariants (a-h): canonical_scope, investigation_queue, dual-module identity, cross-pollution |

**Invariant categories:**

1. **canonical_scope** — IKIGAI agent must remain planner-only per ADR-013 (math/policy/scoring tools explicitly forbidden)
2. **drift_invariants** — UEID 4-part format (ADR-014); vault/strategics/vibe-ops append-only; `vault_write` is sole vault writer (ADR-012)
3. **dual_module_identity** — guards the `src.X` vs `X` import split
4. **cross_pollution** — flags state pollution between test modules

**Drift tests are append-only — they grow with the system but never get deleted.** When you add a feature that crosses an invariant boundary, add a new test in `test_drift_extended_invariants.py` rather than weakening an existing one.

## Import-Path Rules

Two import styles coexist, and mixing them silently breaks tests:

| Layer | Style | Example | Resolves via |
|-------|-------|---------|--------------|
| `src/contracts/`, `src/mesh/`, `src/ikigai/` (agents/MCP) | dotted-prefix | `from src.contracts.sonho import ...` | `<repo>/src/` |
| `sys_ikigai/` (entities, gateway, state_machines, vault, security) | bare namespace | `from sys_ikigai.entities.task import Task` | `<repo>/sys_ikigai/` |

**Rule: when monkeypatching, patch BOTH identities.** If production code uses dotted-prefix (`from src.contracts.X`) but a test monkeypatches the bare module (`monkeypatch.setattr(sys.modules["contracts.X"], ...)`), the patch silently no-ops.

## Windows Quirks

| Bug | Fix | Commit |
|-----|-----|--------|
| `sys.stdin.readline()` HANGS on Windows pipes (MCP stdio handshake) | Use `sys.stdin.buffer.readline()` | `b93a1f3` |
| pytest-asyncio `PermissionError [WinError 5]` on stale temp dirs | `tests/conftest.py` redirects `tempfile.tempdir` to `data/pytest-tmp/` | `ff3037f` |
| Empty directory locked by another process | Mark for deletion via `PendingFileRenameOperations` registry | — |

## Refactor Protocol

If touching `vault/`, `vibe-ops/`, or `strategics/`: **stop** → propose Action Plan → wait for explicit "go" → verify every pre-existing string survives.

## Where to Start

| Task | Start here |
|------|-----------|
| Using mesh | `python -m interfaces.cli mesh-show <ueid>` (after `task-add ...`) |
| Building interfaces | `interfaces/cli/v2.py` (1042 lines) or `interfaces/tui/operator/` (Textual 5-tab) |
| Deep Agent development | `src/ikigai/src/agents/v2/` (registered as `ikigai_maintainer_v2` in `langgraph.json`) + `vault/` |
| Unifying contracts | `src/contracts/` + `src/mesh/` (Phase 3 DONE) |
| MCP Gateway integration | `src/ikigai/MCP_GATEWAY.md` |
| Understanding the system | `docs/ARCHITECTURE_INDEX.md` |
| Kill switch | `sys_ikigai/security/kill_switch.py` + CLI `kill-switch status\|pause\|resume` + TUI tab |
| Drift net / invariant work | `src/ikigai/tests/test_canonical_scope.py` + `test_drift_invariants.py` + `test_drift_extended_invariants.py` |
| Phase 3 spec/plan | `docs/superpowers/specs/` + `docs/superpowers/plans/` |
| Paperclip work | `src/ikigai/src/agents/paperclip/` (graph + policy/router) + `specs/M169-paperclip/...M193` + ADR-036 |