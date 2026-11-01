# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What This Repo Is

**Algorithmic Life OS** — a personal productivity orchestration system, 100% local, single-user, append-only.

**Three layers:**

```
┌─────────────────────────────────────────────────────────────┐
│  INTERFACE LAYER  —  CLI consumer (python -m             │
│  interfaces.cli) — read from data/, write feedback           │
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

1. **DOM unificado** (schema + tipagem forte + UID) · 2. **Store cloud** (Postgres serverless: versionamento, índices, vector, graph) · 3. **Services + transporte MCP** · 4. **Backend** (harness **pi**, já pronto — a repo **não** constrói harness) · 5. **Clientes** (Telegram é o foco; a TUI saiu do escopo publicado — ADR-037)

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

**`pytest.ini`** at repo root: `pythonpath = src src/ikigai/src` + `testpaths = tests` — this is what makes root-level `from src.contracts.X` and `from src.ikigai.X` resolve. `make test` is NOT the canonical entry — it still points at retired paths. Use the per-package commands above.

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

The Produtividade Algorítmica Visual (PAV) kernel — pure-arithmetic business logic (Q_HE, regime FSM, habit engine) — was archived on 2026-08-31 to `archive/legacy-pav/src-operational/` and is **not published** (the whole `archive/` tree is outside the remote branch, ADR-037). See [ADR-013](code-docs/adr/ADR-013-canonical-scope-discipline.md). The IKIGAI agent layer is **planner-only** — math/policy/scoring tools are NOT in the canonical tool surface (drift-enforced in `src/ikigai/tests/test_canonical_scope.py`).

### IKIGAI Deep Agent (`src/ikigai/`)

```bash
cd src/ikigai && poetry install           # Poetry-managed (CI matrix entry "ikigai")
poetry run pytest -m "not e2e"            # canonical test entry for this package
poetry run ruff check src/ && poetry run ruff format --check src/
poetry run mypy -p src.ikigai.src        # never invoke mypy with a path

# The published src/ikigai surface is: contracts, data layer (src/data),
# services (src/services), transport (src/transport), souls, docs and tests.
# The PC-only langgraph/langchain harness (src/ikigai/src/agents/, mcp_server/,
# bin/, ikigai.bat) is NOT published (ADR-037).
```

### Interfaces (CLI only — serverless pivot, ADR-037)

```bash
# Module is `interfaces.cli` (via `__main__.py` shim), not `interfaces.cli.main`
python -m interfaces.cli --help
python -m interfaces.cli list
python -m interfaces.cli done <ueid>
python -m interfaces.cli stats
python -m interfaces.cli mesh-show <ueid>
python -m interfaces.cli task-add ...
python -m interfaces.cli plan-add ...
python -m interfaces.cli plan-list
python -m interfaces.cli kill-switch status|pause|resume

# The operator TUI (interfaces/tui, Textual 5-tab) is PC-only and is NOT part
# of the published serverless surface.
```

The `kill_switch` at `sys_ikigai/security/kill_switch.py` pauses/resumes the cybernetic engine without killing the daemon.

### Canonical transport contract

The published transport is `src/transport/mcp_server.py` — FastMCP over HTTP,
serving the services layer. Its contract is gated by the `ikigai` CI matrix
entry (`poetry run pytest -m "not e2e"` over `src/ikigai/tests/transport`).

The former stdio MCP gateway (`src/ikigai/src/mcp_server/`, `ikigai.bat mcp`,
`scripts/mcp_inspect.py`) was retired by the serverless pivot (ADR-037) and is
not part of the published tree.

### Vibe-ops

```bash
# Run from inside life/ — vibe-ops/ is a child of life/, not a peer
cd vibe-ops
python src/vibe_cli.py hybrid_search "query"   # only extant script (main.py was retired)
```

### LangGraph / Paperclip harness — RETIRED (PC-only, ADR-037)

The langgraph dev server, the `langgraph.json` graphs (`ikigai_maintainer_v2`,
`ikigai_fork_smoke`, `ikigai_taskdog_mcp`, `ikigai_paperclip`,
`ikigai_dynamic`) and the Paperclip meta-orchestrator lived under
`src/ikigai/src/agents/` and `src/ikigai/src/chat/`. They are **not published**
— the remote branch carries the canonical data layer, the contracts, the mesh,
the transport and the specs. The specs remain in `specs/M169-paperclip/...M193`
and `code-docs/adr/ADR-036-paperclip-four-nested-loops.md`.

The cloud harness is specified in `specs/harness/` and is built serverless —
the repo does not build a harness.

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
- **Read path:** `life mesh show <ueid>` joins slices from both published adapters
- **2 adapters** (both implement `ForkAdapter` Protocol): `CliAdapter` (`data/tasks.jsonl`), `TaskdogAdapter` (SQLite UPSERT on ueid)
- **Retired forks (ADR-037):** `SolverforgeCalendarAdapter` (UPI ueid column) and the `tuiboard` / `sf_*` fork MCP tools are PC-only and no longer part of the published surface
- **v1.2+ still out of scope:** `update`, `delete`, `done` actions; LLM-driven validation
- **Minor known issues (non-blocking):** `propagate()` doesn't auto-ack `partial_propagation` status
- **Investigation queue** (`data/investigation_queue/`): `enqueue`/`status`/`complete` MCP tools. Drift-enforced via `test_drift_extended_invariants.py`

### Vibe-ops: Target-Sensor-Adjuster Loop

`vibe-ops/src/cybernetics/engine.py` is the current cybernetic kernel (TARGET → SENSOR → ADJUSTER → PERSIST → SYNC → INDEX; composition paths raise `NotImplementedError` per attribution §3).
`SyncEngine` (`vibe-ops/src/middleware/sync_engine.py`): Obsidian ↔ SQLite ↔ Taskwarrior. UEID format `<CLUSTER>:<ENTITY>:<HASH>:<SEQ>` (4-part canonical per ADR-014).
PolicyEngine states: PUSH / MAINTAIN / REDUCE / RECOVER with hysteresis.
IKIGAI agent does **not** execute this loop — it observes feedback only.

### Transport / Gateway

The published transport is `src/transport/mcp_server.py` (FastMCP over HTTP) on top of `src/services/` and `src/data/`. The agent remains the **sole** vault writer (ADR-012): `vault_write` in `sys_ikigai/vault/` is the canonical entry point. The old stdio gateway doc (`src/ikigai/MCP_GATEWAY.md`) is PC-only and unpublished (ADR-037).

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
| Building interfaces | `interfaces/cli/read_tasks.py` (canonical CLI surface) — the operator TUI is unpublished |
| Data layer development | `src/data/` + `src/services/` + `src/transport/` + `src/contracts/` (ADR-037 canonical turn) |
| Unifying contracts | `src/contracts/` + `src/mesh/` (Phase 3 DONE) |
| Transport integration | `src/transport/mcp_server.py` (FastMCP over HTTP) |
| Understanding the system | `docs/ARCHITECTURE_INDEX.md` |
| Kill switch | `sys_ikigai/security/kill_switch.py` + CLI `kill-switch status\|pause\|resume` |
| Drift net / invariant work | `src/ikigai/tests/test_canonical_scope.py` + `test_drift_invariants.py` + `test_drift_extended_invariants.py` |
| Phase 3 spec/plan | `docs/superpowers/specs/` + `docs/superpowers/plans/` |
| Paperclip work | specs live in `specs/M169-paperclip/...M193` + [ADR-036](code-docs/adr/ADR-036-paperclip-four-nested-loops.md); the runtime is PC-only |

---

## Refactor Protocol

If touching `vault/`, `vibe-ops/`, or `strategics/`: **stop** → propose Action Plan → wait for explicit "go" → verify every pre-existing string survives.

---

## Pitfalls

- **Don't restore old PAV TUI/CLI** — `apps/cli` and `apps/tui` were deleted intentionally; build new interfaces under `interfaces/`
- **Don't re-publish the PC-only surfaces** — the operator TUI, the stdio MCP servers and the langgraph/langchain harness stay out of the remote branch (ADR-037); they are gitignored, not deleted
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
