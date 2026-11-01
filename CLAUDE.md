# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What This Repo Is

**Algorithmic Life OS** — a personal productivity orchestration system, 100% local, single-user, append-only.

**Three layers:**

```
┌─────────────────────────────────────────────────────────────┐
│  INTERFACE LAYER  —  CLI/TUI consumers (CLI v2, Textual   │
│  5-tab TUI) — read from data/, write feedback               │
└──────────────────────────────┬──────────────────────────────┘
                               │ MCP / stdio
┌──────────────────────────────▼──────────────────────────────┐
│  AGENT LAYER  —  Deep Agent (carro-chefe)                 │
│  Reads vault/ → applies strategics + planning → writes     │
│  tasks to data/ → observes planned vs actual → updates     │
│  vault (PAE math stripped per ADR-013 — planner-only)      │
└──────────────────────────────┬──────────────────────────────┘
                               │ contracts (Pydantic)
┌──────────────────────────────▼──────────────────────────────┐
│  DATA LAYER  —  vault/ + data/ + vibe-ops/                │
│  vault/: markdown source of truth (Obsidian-style)         │
│  data/: runtime state (SQLite, chroma, boulder.json)       │
│  vibe-ops/: cybernetic engine (vector store + evidence)    │
└─────────────────────────────────────────────────────────────┘
```

**Canonical flow:** `vault` (NL planning) → Deep Agent → MCP Gateway → interfaces → manual feedback → Deep Agent observes gap → updates `vault`.

**Repo:** github.com/matheusmendes720/ikigai
**Project Board:** github.com/users/matheusmendes720/projects/5

---

## Global Conventions

| Rule | What it forbids |
|------|----------------|
| **Deep Agent is the only writer to `vault/`** | Interfaces only read vault; user feedback goes to `data/feedback.jsonl`, fork writes go to `data/review_queue/` (TaskChange events awaiting Agent validation) |
| **Append-only** | Never delete/prune in `vault/`, `vibe-ops/`, `strategics/` |
| **Contracts in `src/contracts/`** | Pydantic v2 strict (`frozen=True`, `extra="forbid"`) imported from one place |
| **Zero LLM in pipeline** | Daily/weekly pipelines are pure arithmetic |
| **`--json` everywhere** | Every CLI command supports `--json` |
| ~~**Fully local**~~ | SQLite + filesystem only, zero cloud deps — **substituída 2026-11-01** por *single cloud store + local cache* (ADR-037 D1/D3) |
| **Single cloud store** | Postgres serverless (candidata Supabase) — vector, graph e busca estruturada no mesmo banco. Prose continua em markdown `vault/`; estruturado vive no store, e o store vence |
| **Um writer por store** | `vault_write` no markdown · `src/services/` no Postgres — `revision` otimista + `idempotency_key`; conflito = **409**, nunca last-write-wins |
| **Um DOM, N projeções** | Contrato único em `src/contracts/`; **cada app decide a view**. Nenhum campo de interface no contrato |

---

## Current Mode

**Virada canônica — camada de dados primeiro (2026-11-01, ADR-037).**

Toda a força vai para a **camada de dados**, nesta ordem:

1. **DOM unificado** (schema + tipagem forte + UID) · 2. **Store cloud** (Postgres serverless: versionamento, índices, vector, graph) · 3. **Services + transporte MCP** · 4. **Backend** (harness **pi**, já pronto — a repo **não** constrói harness) · 5. **Clientes** (Telegram é o foco; TUI em standby)

- **Não** iniciar produto novo (Telegram, timeline, TUI) antes da fase 3 verde.
- **Não** propor harness, grafo custom, orquestrador de agentes, gateway MCP de tools, ou banco de embeddings separado — cada um já foi diagnosticado como custo sem retorno.
- **Foco aceito agora:** schema, índice, consulta, sync, vector, grafo, versionamento, conflito de escrita.
- Documentos: [ADR-037](code-docs/adr/ADR-037-data-layer-canonical-turn.md) · [série de specs](docs/superpowers/specs/2026-11-01-00-data-layer-series.md) · [TECH.md](specs/data-layer/TECH.md) · [README](docs/README.md)

**Gate anterior ("5+ SONHO logs") substituído** pela métrica de 14 dias do ADR-037 §8: nota escrita sem editar arquivo à mão, de cliente não-desktop (≥5) · zero lost update com 2 clientes · p95 de busca estruturada < 100ms.

### Planning Note channel (human → agent)

- **Template:** `vault/ikigai/templates/sonho-log.md` (1 section: `## Mudança`)
- **Trigger:** manual only, after any planning delta
- **Cadence:** event-driven (NOT daily). 1–3 bullets per note, <2 min
- **Where:** `vault/ikigai/closing-2026/<quarter>/04-relatórios-diários/YYYY-MM-DD.md`

### Where shipped-wave history lives

Wave 3/4/5, Plan C/D, W6.X, drift ship dates, commit hashes, PASS counts → `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/`. **CLAUDE.md is the durable contract; memory holds the audit trail.** Add a one-line memory entry per shipped wave and link from `MEMORY.md`.

---

## Build / Run / Test

### Tests

`tests/conftest.py` (repo root) is the single source of truth for test imports. It:

- Adds `<repo>/` to `sys.path` (resolves BOTH `from src.contracts.X` via `<repo>/src/` AND `from sys_ikigai.X` via `<repo>/sys_ikigai/`)
- Redirects `tempfile.tempdir` + `TMPDIR`/`TEMP`/`TMP` to `data/pytest-tmp/` to dodge Windows `PermissionError [WinError 5]`

**Root-level pytest** (interactive only) needs system Python with `pip install -c constraints.txt` (installs `mcp<2`). CI uses submodule `uv sync` with its own pin (`mcp = "^1.1"` in `src/ikigai/pyproject.toml`). Canonical test entry per CI quality-gates (`.github/workflows/ci.yml`): `uv run pytest -m "not e2e"` from inside each matrix package. Single-test example: `pytest src/ikigai/tests/test_drift_invariants.py::test_ueid_regex`.

**`pytest.ini`** at repo root: `pythonpath = src src/ikigai/src` + `testpaths = tests` — this is what makes root-level `from src.contracts.X` and `from src.ikigai.X` resolve. `make test` runs only `vibe-ops/tests/`, `archive/legacy-pav/src-operational/tests/`, and `langgraph_tests/` (NOT the full CI matrix).

**`mypy.ini`** at repo root has `mypy_path = src .. ../..` + `explicit_package_bases = True` (closes W6.X item 5 dup-source error). The ~542 remaining `[import-not-found]` errors are pre-existing stub-resolution issues, separate scope.

### Lint / format / typecheck (CI quality-gates)

```bash
uv run ruff check                        # lint (5 matrix packages in CI)
uv run ruff format --check               # format check
uv run mypy                              # typecheck
pre-commit run --all-files               # .pre-commit-config.yaml hooks
```

These run across all 5 CI matrix packages (`ikigai`, `vibe-ops`, `interfaces-cli`, `src-contracts`, `src-mesh`) per `.github/workflows/ci.yml` quality-gates job. Python version: `.python-version` pins 3.11 (matches `langgraph.json` `python_version`).

### Cross-platform loop tick

- **Bash** (Linux/macOS native, canonical): `bash .claude/loop/loop-tick.sh`
- **TypeScript** (cross-platform, requires Deno 1.40+): `deno run --allow-all .claude/loop/loop-tick.ts`
- **Windows .bat** (legacy, Git Bash required): `.claude/loop/loop-tick.bat`

The TS entry is a thin wrapper that parses flags then delegates to `loop-tick.sh` for the orchestrator/worker/verifier logic. Same flags: `--dry-run`, `--cost-cap`, `--max-runtime`, `--graph <name>`, `--auto-cleanup`. On Windows the TS entry falls back to `C:\Program Files\Git\bin\bash.exe` when no `bash` is on `PATH`. Deno install:

- Windows (PowerShell): `irm https://deno.land/install.ps1 | iex`
- macOS / Linux: `curl -fsSL https://deno.land/install.sh | sh`

### PAV kernel — ARCHIVED 2026-08-31

The Produtividade Algorítmica Visual (PAV) kernel — pure-arithmetic business logic (Q_HE, regime FSM, habit engine) — is archived to `archive/legacy-pav/src-operational/`. See `archive/legacy-pav/SUPERSEDED.md` and [ADR-013](code-docs/adr/ADR-013-canonical-scope-discipline.md). The IKIGAI agent layer is **planner-only** — math/policy/scoring tools are NOT in `IKIGAI_TOOLS` (12 tools, drift-enforced in `src/ikigai/tests/test_canonical_scope.py`). To revive: `cd archive/legacy-pav/src-operational/ && uv sync && uv run pytest`.

### IKIGAI Deep Agent (`src/ikigai/`)

```bash
cd src/ikigai && uv sync                 # uv-managed (NOT poetry)
ikigai.bat mcp                            # Windows: start FastMCP gateway
src/ikigai/start_mcp_gateway.sh          # POSIX equivalent
ikigai.bat agent <thread>                 # run agent on a thread
ikigai.bat chat <thread>                  # chat with a thread

# REPL — soul-aware agent shell (M16)
python scripts/chat_repl.py              # /profile switching + chat persistence + SSE events
```

### Interfaces (CLI + TUI)

```bash
# CLI — V5: single v2.py (1042 lines); only `v2 plan` retained
# Module is `interfaces.cli` (via `__main__.py` shim), not `interfaces.cli.main`
python -m interfaces.cli v2 plan
python -m interfaces.cli mesh-show <ueid>
python -m interfaces.cli task-add ...
python -m interfaces.cli kill-switch status|pause|resume

# TUI — Textual 5-tab operator (Tasks / Adapters / Backend / Queue / KillSwitch)
python -m interfaces.tui.operator
# or: life tui
```

The `kill_switch` at `sys_ikigai/security/kill_switch.py` pauses/resumes the cybernetic engine without killing the daemon.

### MCP Gateway contract test

```bash
make mcp-inspect              # POSIX (uses system python)
scripts/mcp-inspect.bat       # Windows cmd/PowerShell wrapper
python scripts/mcp_inspect.py # Direct invocation (any platform)
```

Enumerates tools + resources via stdio handshake. Use `--tool-count N --resource-count M` to assert the contract.

### Vibe-ops

```bash
# Run from inside life/ — vibe-ops/ is a child of life/, not a peer
cd vibe-ops
python src/vibe_cli.py hybrid_search "query"   # only extant script (main.py was retired)
cd vibeops-tui && cargo run       # Rust TUI (ratatui) — polls ../data/vibe_ops.db
```

### LangGraph dev

```bash
# First-time setup (requires Python 3.13):
py -3.13 -m pip install langgraph-cli

# Start the dev server:
scripts\langgraph-dev.bat           # langgraph dev server on :2024 (Python 3.13)
# Or with make (if make is on PATH):
make dev
make dev-graph NAME=ikigai_maintainer_v2   # one graph
make test
```

`langgraph.json` registers **5 graphs** (all in `src/ikigai/src/agents/`):

| Graph | Entry |
|-------|-------|
| `ikigai_maintainer_v2` | `src/ikigai/src/agents/v2/graph.py:make_v2_graph` |
| `ikigai_fork_smoke` | `src/ikigai/src/agents/v2/fork_smoke_graph.py:make_fork_smoke_graph` |
| `ikigai_taskdog_mcp` | `src/ikigai/src/agents/taskdog_mcp_graph.py:make_taskdog_mcp_graph_sync` |
| `ikigai_paperclip` | `src/ikigai/src/agents/paperclip/graph.py:make_paperclip_graph` |
| `ikigai_dynamic` | `src/ikigai/src/agents/paperclip_dynamic/graph.py:make_dynamic_graph` |

The v2 graph wires 8/16 NODES to real MCP calls via `mcp_bridge.py` (PAV-flavored wrappers removed in M12; only `ikigai_decompose` survives). The remaining 8 NODES are either prompt-chain stubs (`surface_intentions`), read-only (`tag_and_persist` — vault_write is separate work), or not yet wired (`tag_propagation`, `dep_graph`, `gantt_suggest`, `score_vectors`, `balance`, `dispatch_sub_agents`). NODES tuple is in `src/ikigai/src/agents/v2/graph.py`.

### Paperclip Meta-Orchestrator (`src/ikigai/src/agents/paperclip/`)

Meta-orchestrator layer that lets the IKIGAI agent *delegate* work to other LLM agents (Claude / Pi / omo / OpenClaw / mmx-cli / hermes — last two remain stubs). **6th daemon in the loop fleet** (auto-spawner polls `.claude/loop/inbox/` every 5m).

**The 4-nested-loops framework** ([ADR-036](code-docs/adr/ADR-036-paperclip-four-nested-loops.md)):
1. LLM decides **what** to do (intent extraction)
2. Paperclip decides **who** does it (adapter router, priority pi>omo>openclaw>claude)
3. Three auto-throttles gate **how much**: `CostGate` (M173, fail-open, $5/day) → `WallClockGate` (M175, fail-open, 3600s) → `RiskGate` (M176, fail-CLOSED, 18 keywords)
4. Worktree-isolated execute → HIL pause (`interrupt()`) → merge → cleanup

**Key entry points:**
- `paperclip` Typer CLI (M177): `paperclip status|run|spec|validate`
- `scripts/paperclip-spawner.sh` — bash auto-prompt loop (206L, polls inbox, `which <adapter>` health probe)
- `scripts/paperclip-dashboard.py` + `scripts/paperclip_heartbeat_http.py` — observability
- `policy.py` — `CostGate` / `WallClockGate` / `RiskGate` classes
- `router.py` — Pydantic v2 adapter router, fail-CLOSED on cost, fail-OPEN on missing health

**5th graph `ikigai_dynamic`** (M191): 4 nested loops framework skeleton with fan-out to N parallel subagents per spec.

**Drift net touches:** 72 → 79 (canonical HTTP adapter per M190, workspace template per M180, paperclip-cli + 6th daemon inv per M177).

---

## Architecture — Key Pieces

---

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

- **UEID** is the canonical join key: 4-part regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` per [ADR-014](code-docs/adr/ADR-014-ueid-canonical-format.md) (supersedes 5-part claim)
- **Write path:** fork → CLI enqueues `TaskChange` to `data/review_queue/` → Agent validates → propagates `PropagationEvent` to all forks
- **Read path:** `life mesh show <ueid>` joins slices from all 3 adapters
- **3 adapters** (all implement `ForkAdapter` Protocol): `CliAdapter` (`data/tasks.jsonl`), `TaskdogAdapter` (SQLite UPSERT on ueid), `SolverforgeCalendarAdapter` (UPI ueid column)
- **Phase A fork MCP tools** (live, in separate `UnifiedMCPGateway`): 2 `sf_*` + 4 `tuiboard_*` + 4 `taskdog_*` (taskdog wrappers are read-only — Path 3; canonical write is Path 1: harness `@tool` → subprocess → `taskdog.exe`)
- **v1.2+ still out of scope:** `update`, `delete`, `done` actions; LLM-driven validation
- **Minor known issues (non-blocking):** UPI `id` churn on UPSERT conflict; `propagate()` doesn't auto-ack `partial_propagation` status
- **Investigation queue** (`data/investigation_queue/`): `enqueue`/`status`/`complete` MCP tools + TUI read-only browse. Drift-enforced via `test_drift_extended_invariants.py`

### Vibe-ops: Target-Sensor-Adjuster Loop

`vibe-ops/src/cybernetics/engine.py` is the current cybernetic kernel (TARGET → SENSOR → ADJUSTER → PERSIST → SYNC → INDEX; composition paths raise `NotImplementedError` per attribution §3).
`SyncEngine` (`vibe-ops/src/middleware/sync_engine.py`): Obsidian ↔ SQLite ↔ Taskwarrior. UEID format `<CLUSTER>:<ENTITY>:<HASH>:<SEQ>` (4-part canonical per ADR-014).
PolicyEngine states: PUSH / MAINTAIN / REDUCE / RECOVER with hysteresis.
IKIGAI agent does **not** execute this loop — it observes feedback only.

### MCP Gateway

`src/ikigai/MCP_GATEWAY.md` documents the surface. Key tools: `read_vault(path)`, `write_planning(cycle_id, tasks)`, `sync_interfaces()`, `get_metrics()`. The agent is the **sole** vault writer (ADR-012). The `vault_write` function in `sys_ikigai/vault/` is the canonical entry point.

---

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
3. **dual_module_identity** — guards the `src.X` vs `X` import split (see "Import-Path Rules" below)
4. **cross_pollution** — flags state pollution between test modules (shared filesystem fixtures leaking across boundaries)

**Drift tests are append-only — they grow with the system but never get deleted.** When you add a feature that crosses an invariant boundary, add a new test in `test_drift_extended_invariants.py` rather than weakening an existing one.

---

## Import-Path Rules

Two import styles coexist, and mixing them silently breaks tests:

| Layer | Style | Example | Resolves via |
|-------|-------|---------|--------------|
| `src/contracts/`, `src/mesh/`, `src/ikigai/` (agents/MCP) | dotted-prefix | `from src.contracts.sonho import ...` | `<repo>/src/` |
| `sys_ikigai/` (entities, gateway, state_machines, vault, security) | bare namespace | `from sys_ikigai.entities.task import Task` | `<repo>/sys_ikigai/` |

Both resolve from `<repo>/` after the 2026-09-05 namespace rename (`src/ikigai/src/ikigai/` → `sys_ikigai/`, commit `685dec5`). The `tests/conftest.py` setup adds `<repo>/` to `sys.path` once, and both styles work.

**Why this matters — dual-module identity bug class:**

If production code uses dotted-prefix (`from src.contracts.X`) but a test monkeypatches the bare module (`monkeypatch.setattr(sys.modules["contracts.X"], ...)`), the patch silently no-ops because `sys.modules["src.contracts.X"]` is the *actual* module instance the production code holds. The test passes its assertion against an unpatched object. The first hit was `test_taskdog_cli.py` (W6.X item 3, commit `3a4ed8c`); the structural fix was the `sys_ikigai` rename which made the dotted-prefix pattern explicit. **Rule: when monkeypatching, patch BOTH identities.**

---

## Windows Quirks

A handful of Windows-only bugs have shipped and stayed fixed. If you hit them again, the fix is already known:

| Bug | Fix | Commit |
|-----|-----|--------|
| `sys.stdin.readline()` HANGS on Windows pipes (MCP stdio handshake) | Use `sys.stdin.buffer.readline()` | `b93a1f3` |
| pytest-asyncio `PermissionError [WinError 5]` on stale `AppData\Local\Temp\pytest-of-<user>\` dirs | `tests/conftest.py` redirects `tempfile.tempdir` + `TMPDIR`/`TEMP`/`TMP` to `data/pytest-tmp/` | `ff3037f` |
| Empty directory locked by another process (e.g. `__pycache__` mid-collect) | Mark for deletion via `PendingFileRenameOperations` registry, finishes on next reboot | — |

---

## Where to Start

| Task | Start here |
|------|-----------|
| Using mesh | `python -m interfaces.cli mesh-show <ueid>` (after `task-add ...`) |
| Building interfaces | `interfaces/cli/v2.py` (1042 lines) or `interfaces/tui/operator/` (Textual 5-tab) |
| Deep Agent development | `src/ikigai/src/agents/v2/` (registered in `langgraph.json` as `ikigai_maintainer_v2`) + `vault/` |
| Unifying contracts | `src/contracts/` + `src/mesh/` (Phase 3 DONE) |
| MCP Gateway integration | `src/ikigai/MCP_GATEWAY.md` |
| Understanding the system | `docs/ARCHITECTURE_INDEX.md` |
| Kill switch | `sys_ikigai/security/kill_switch.py` + CLI `kill-switch status\|pause\|resume` + TUI tab |
| Drift net / invariant work | `src/ikigai/tests/test_canonical_scope.py` + `test_drift_invariants.py` + `test_drift_extended_invariants.py` |
| Phase 3 spec/plan | `docs/superpowers/specs/` + `docs/superpowers/plans/` |
| Paperclip work | `src/ikigai/src/agents/paperclip/` (graph + policy/router) + `specs/M169-paperclip/...M193` + [ADR-036](code-docs/adr/ADR-036-paperclip-four-nested-loops.md) |

---

## Refactor Protocol

If touching `vault/`, `vibe-ops/`, or `strategics/`: **stop** → propose Action Plan → wait for explicit "go" → verify every pre-existing string survives.

---

## Pitfalls

- **Don't restore old PAV TUI/CLI** — `apps/cli` and `apps/tui` were deleted intentionally; build new interfaces under `interfaces/`
- **Deep Agent writes vault; interfaces don't** — interfaces only read from `data/`
- **Append-only** enforced on `vault/`, `vibe-ops/`, `strategics/`, AND `data/review_queue/`
- **`vibe_ops.db` lives in `data/`** — not at the old root location
- **v1 mesh scope = `create` only** — adapters early-return on non-create actions; don't add update/delete/done logic until v1.2
- **IKIGAI agent is planner-only** — don't re-introduce PAV math into `src/ikigai/` (drift net enforces)
- **Deep Agent harness does NOT fill interface fields automatically** — explicit 2026-09-06 user pivot. Agent reasons about planning context (SONHOS / metas / objetivos), not interface rendering
- **Submodule `strategics/planning-with-files` is intentionally dirty** — vendored third-party (user's own fork), do not commit. Treated as immutable

---

<!-- OPENWIKI:START -->

## OpenWiki

See [AGENTS.md](AGENTS.md) for OpenWiki agent instructions.

<!-- OPENWIKI:END -->

*Algorithmic Life OS — CLAUDE.md — 2026-10-12 (paperclip + dynamic-workflows graphs documented)*
