# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What This Repo Is

**Algorithmic Life OS** — a personal productivity orchestration system, 100% local, single-user, append-only.

**Three architectural layers:**

```
┌─────────────────────────────────────────────────────────────┐
│  INTERFACE LAYER  —  CLI/TUI consumers (Gantt, Kanban,   │
│  Calendar, Daily View) — read from data/, write feedback   │
└──────────────────────────────┬──────────────────────────────┘
                               │ MCP / stdio
┌──────────────────────────────▼──────────────────────────────┐
│  AGENT LAYER  —  Deep Agent (carro-chefe)                 │
│  Reads vault/ → applies strategics + planning → writes     │
│  tasks to data/ → observes planned vs actual → updates    │
│  vault (PAE math stripped per ADR-013 — planner-only)     │
└──────────────────────────────┬──────────────────────────────┘
                               │ contracts (Pydantic)
┌──────────────────────────────▼──────────────────────────────┐
│  DATA LAYER  —  vault/ + data/ + vibe-ops/               │
│  vault/: markdown source of truth (Obsidian-style)         │
│  data/: runtime state (SQLite, chroma, boulder.json)       │
│  vibe-ops/: cybernetic engine (vector store + evidence)    │
└──────────────────────────────────────────────────────────────┘
```

**Canonical flow:**
```
vault (NL planning)
  → Deep Agent (interpreta, aplica strategics + planning, gera tasks)
    → MCP Gateway (sincroniza vault ↔ interfaces)
      → Interfaces preenchem com tasks ricas pro usuário marcar
        → Input manual (burndown, execution rate)
          → Deep Agent observa gap
            → Atualiza planejamento
              → ciclo contínuo
```

**Repo:** github.com/matheusmendes720/ikigai
**Project Board:** github.com/users/matheusmendes720/projects/5

---

## Repository Structure

```
life/
├── src/
│   ├── contracts/              ← CANONICAL Pydantic contracts
│   │   ├── common.py           UEID, Period, Priority, EntityType, RegimeState
│   │   ├── task.py            Task, Subtask, ChecklistItem, Project, Milestone, Deliverable
│   │   ├── task_change.py     TaskChange, PropagationEvent, TaskAction (Phase 3 v1)
│   │   ├── planning.py        PlanningCycle, Wave, Sprint, VaultEvent
│   │   └── metrics.py         Burndown, ExecutionRate, QHEScore
│   ├── mesh/                   ← DATA MESH (Phase 3 v1 — create action)
│   │   ├── queue.py           Filesystem append-only review queue (atomic writes)
│   │   ├── agent_consumer.py  Deep Agent validation (PAE rules: APPROVE/REJECT/CLARIFY)
│   │   ├── agent_propagator.py Deep Agent propagation (per-adapter failure isolation)
│   │   └── adapters/
│   │       ├── base.py        ForkAdapter Protocol (@runtime_checkable)
│   │       ├── cli.py         CliAdapter (data/tasks.jsonl)
│   │       ├── taskdog.py     TaskdogAdapter (SQLite UPSERT on ueid)
│   │       └── solverforge_calendar.py SolverforgeCalendarAdapter (UPI ueid column)
│   ├── ikigai/                ← Deep Agent + MCP gateway (FastMCP server)
│   │   └── src/
│   │       ├── agents/         v2 LangGraph graph (9 nodes + subgraphs)
│   │       └── mcp_server/     15 @MCP.tool + 6 @MCP.resource
│   ├── life_tatics/            ← was life-ops/life_tatics/
│   └── planner/                ← was life-ops/planner/
│
├── sys_ikigai/                 ← was src/ikigai/src/ikigai/ (renamed 2026-09-05, commit 685dec5)
│   ├── entities/              Pydantic v2 strict: UEID, Task, Project, Regime, Score…
│   ├── gateway/               Fork clients (CLI / taskdog / solverforge_calendar / tuiboard)
│   ├── state_machines/        Dream / Goal / Objective / Project / Task / Habit / Routine / Deliverable FSMs
│   ├── propagation/           MarkdownDB + frontmatter + sqlite_adapter + triagem
│   ├── vault/                 VaultLock + vault_write (sole vault writer per ADR-012)
│   ├── security/              kill_switch + transition_validator
│   └── adapters/              drift_detector + checkpoint + sqlite_bridge + state_reducer
│
├── vibe-ops/                   cybernetic engine (Target→Sensor→Adjuster)
│   ├── src/
│   └── vibeops-tui/           Rust TUI (ratatui)
│
├── vault/                      ← PRIMARY NOTES LAYER (was .omo/)
│   ├── ikigai/closing-2026/   planning cycles (Q3, Q4, archive)
│   ├── ikigai/meta/           MOCs, indexes, dashboards
│   ├── ikigai/mock-datasets/
│   ├── drafts/evidence/       PAE coverage, evidence trail
│   ├── plans/                  plan specs
│   └── run-continuation/       session resumption JSON
│
├── data/                       ← RUNTIME DATA (was at repo root)
│   ├── vibe_ops.db
│   ├── vibe_mesh.db
│   ├── boulder.json
│   ├── chroma_db/
│   ├── test-fixtures/          test databases
│   └── session-*.md            session transcripts
│
├── interfaces/                  INTERFACE LAYER (consumers)
│   ├── cli/                   Typer CLI — `life v2 daily/weekly/...`, `life mesh show`, kill_switch
│   │                           v2.py split into 6 modules (commit 11f463b, max 267L)
│   └── tui/
│       └── operator/          Textual 4-tab TUI (Chat / Tasks / State / KillSwitch) — `life tui`
│
├── strategics/                  STRATEGIC KNOWLEDGE (PT-BR, read-only)
│   ├── Hierarquia de Objetivos.md
│   ├── Planejamento (Estratégico e Tático).md
│   ├── Modelagem Operacional.md
│   └── planning-with-files/    vendored skill plugin
│
├── docs/                       ARCHITECTURE DOCS
│   ├── ARCHITECTURE_INDEX.md
│   ├── SYSTEMS_TOPOLOGY.md
│   ├── CONCEPTUAL_MODEL.md
│   ├── CLUSTER_PLAN.md
│   ├── CLUSTER_PROJ.md
│   ├── CLUSTER_STUDY.md
│   ├── PAV_INVENTORY.md
│   └── LANGRAPH_DEV.md
│
├── code-docs/                  ADRs, BRDs, PRDs, RDs
├── specs/                      formal specifications
├── diagrams/                   Mermaid + drawio source
├── taskwarrior/                TW binary + scripts + config
├── logs/
│
├── .claude/                    Claude Code config
├── .github/                    CI workflows
├── Makefile                    LangGraph dev server
├── langgraph.json              5 registered LangGraph graphs (see "LangGraph Graphs" section below)
└── CLAUDE.md
```

---

## Global Conventions

| Rule | What it forbids |
|------|----------------|
| **Deep Agent is the only writer to vault/** | Interfaces only read vault; write goes to data/feedback |
| **Append-only** | Never delete/prune in vault/, vibe-ops/, strategics/ |
| **Contracts in src/contracts/** | Pydantic models imported from src/contracts/ everywhere |
| **Zero LLM in pipeline** | Daily/weekly pipelines are pure arithmetic |
| **`--json` everywhere** | Every CLI command supports --json |
| **Pydantic v2 strict** | frozen=True, extra="forbid" |
| **Fully local** | SQLite + filesystem only, zero cloud deps |

---

## Build / Run / Test

### Test discovery & sys.path

`tests/conftest.py` (repo root) is the single source of truth for test
imports. It:

- Adds `<repo>/` to `sys.path` (resolves BOTH `from src.contracts.X` via `<repo>/src/` AND `from sys_ikigai.X` via `<repo>/sys_ikigai/`).
- Redirects `tempfile.tempdir` + `TMPDIR`/`TEMP`/`TMP` to `data/pytest-tmp/` (gitignored) to dodge Windows `PermissionError [WinError 5]` on stale `AppData\Local\Temp\pytest-of-<user>\` dirs.

`mypy.ini` lives at repo root with `mypy_path = src .. ../..` and
`explicit_package_bases = True` (closes W6.X item 5 dup-source error).

### PAV kernel — ARCHIVED 2026-08-31

The Produtividade Algorítmica Visual (PAV) kernel — pure-arithmetic business
logic (Q_HE, regime FSM, habit engine) — has been archived to
`archive/legacy-pav/src-operational/`. See
[`archive/legacy-pav/SUPERSEDED.md`](archive/legacy-pav/SUPERSEDED.md) for the
canonical reasoning and [ADR-013](../code-docs/adr/ADR-013-canonical-scope-discipline.md)
for scope discipline.

To revive (re-attach math/policy execution if needed):
```bash
cd archive/legacy-pav/src-operational/
uv sync && uv run pytest
```

The IKIGAI agent layer (`src/ikigai/`) is **planner-only** —
math/policy/scoring tools are not in `IKIGAI_TOOLS` (12 tools, see
`src/ikigai/tests/test_canonical_scope.py` for the drift detector).

### IKIGAi Deep Agent (src/ikigai/)

```bash
cd src/ikigai
uv sync                 # uv-managed (NOT poetry — see q3-q4-resolved memory)
# IKIGAI_TOOLS = 12 planning tools (see src/ikigai/tests/test_canonical_scope.py)
# Phase A SHIPPED 7 fork MCP tools (sf_* + tuiboard_*) in SEPARATE UnifiedMCPGateway
# Total gateway surface = 22 tools (12 IKIGAI FastMCP + 7 fork HTTP+SSE) + 6 resources
# (corrected 2026-09-04 per Diag 02 — NOT 19 tools as previously claimed)
ikigai.bat mcp          # start MCP server (15 @MCP.tool + 6 @MCP.resource on FastMCP)
ikigai.bat agent <thread>
ikigai.bat chat <thread>
```

### Interfaces (interfaces/cli/ + interfaces/tui/)

```bash
# CLI — v2 split into 6 modules (commit 11f463b, max 267L in _v2_primitives.py)
python -m interfaces.cli.main v2 daily       # daily run → invoke_skill path
python -m interfaces.cli.main v2 weekly      # weekly run → invoke_skill path
python -m interfaces.cli.main v2 plan        # meta-planner (Plan D SHIPPED 2026-09-04)
python -m interfaces.cli.main mesh show <ueid>
python -m interfaces.cli.main task add ...
python -m interfaces.cli.main kill_switch status|pause|resume  # W5.3 SHIPPED 2026-09-05

# TUI — Textual 4-tab operator (Chat / Tasks / State / KillSwitch)
python -m interfaces.tui.operator.main
# or: life tui
```

The `kill_switch` lives at `sys_ikigai/security/kill_switch.py` and is
the canonical way to pause/resume the cybernetic engine without killing
the daemon process. Both CLI subcommand and 5th TUI tab were added in
W5.3 (commit batch, 7 new files + 2 edits, 13/13 PASS).

### Phase B3 — MCP Gateway

```bash
# Contract test — enumerates tools + resources via stdio handshake
# (corrected 2026-09-04: 15 tools + 6 resources on FastMCP gateway; 7 more fork tools in UnifiedMCPGateway)
make mcp-inspect              # POSIX (uses system python)
scripts/mcp-inspect.bat       # Windows cmd/PowerShell wrapper
python scripts/mcp_inspect.py # Direct invocation (any platform)

# Optional flags
python scripts/mcp_inspect.py --tool-count 15 --resource-count 6
```

### Vibe-ops

```bash
cd vibe-ops
python src/main.py run-daily [--date YYYY-MM-DD]
python src/vibe_cli.py hybrid_search "query"
cd vibeops-tui && cargo run
```

### LangGraph dev

```bash
make dev          # langgraph dev server on :2024
make test
```

---

## Architecture — Key Pieces

### Deep Agent Harness (src/ikigai/src/agents/)

The **carro-chefe**. Reads vault markdown → applies strategics + planning
(planner-only per ADR-013; PAE math stripped from agent layer) → writes
structured tasks to data/ → interfaces consume from data/ → observes planned
vs actual → updates vault.

### MCP Gateway (src/ikigai/MCP_GATEWAY.md)

Exposes tools:
- `read_vault(path)` → NL content
- `write_planning(cycle_id, tasks)` → updates vault
- `sync_interfaces()` → propagates to data/
- `get_metrics()` → reads feedback

### Canonical Contracts (src/contracts/)

Shared Pydantic v2 models. All layers import from here.

| Module | Models |
|--------|--------|
| `common.py` | `UEID`, `Period`, `Priority`, `EntityType`, `RegimeState` |
| `task.py` | `Task`, `Subtask`, `ChecklistItem`, `Project`, `Milestone`, `Deliverable` |
| `task_change.py` | `TaskChange`, `PropagationEvent`, `TaskAction` (Phase 3 v1) |
| `planning.py` | `PlanningCycle`, `Wave`, `Sprint`, `VaultEvent` |
| `metrics.py` | `Burndown`, `ExecutionRate`, `QHEScore` |

### Data Mesh (src/mesh/) — Phase 3 v1

Cross-fork task view + bidirectional sync via Deep Agent gateway. **v1 scope = `create` action only.**

- **UEID** is the canonical join key across all forks (**4-part** regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` per `code-docs/adr/ADR-014-ueid-canonical-format.md`; supersedes the 2026-08-31 5-part claim)
- **Write path**: fork → CLI enqueues `TaskChange` to `data/review_queue/` → Agent validates → propagates `PropagationEvent` to all forks
- **Read path**: `life mesh show <ueid>` joins slices from all 3 adapters (CLI / taskdog / UPI)
- **3 adapters** (all implement `ForkAdapter` Protocol): `CliAdapter`, `TaskdogAdapter`, `SolverforgeCalendarAdapter`
- **Phase A SHIPPED (2026-08-30)**: 4 tuiboard fork MCP tools (`tuiboard_create_task` etc.) — tuiboard adapter is live as MCP fork, no longer "out of scope"
- **v1.2+ (still out of scope)**: `update`, `delete`, `done` actions; LLM-driven validation

### Vibe-ops: Target-Sensor-Adjuster Loop

`vibe-ops/src/cybernetics/daily_loop.py`: TARGET → SENSOR → ADJUSTER → PERSIST → SYNC → INDEX
(composition paths raise `NotImplementedError` per attribution §3; IKIGAI agent does NOT execute this loop — it observes feedback only)
`SyncEngine` (`vibe-ops/src/middleware/sync_engine.py`): Obsidian ↔ SQLite ↔ Taskwarrior.
UEID format: `<CLUSTER>:<ENTITY>:<HASH>:<SEQ>` (**4-part canonical per ADR-014**; the 2026-08-31 5-part claim is superseded).

PolicyEngine states (PUSH / MAINTAIN / REDUCE / RECOVER) with hysteresis.

---

## Current Mode

**Data-first methodology** — IKIGAi está pausado para *novas decisões de
algoritmo* (M01/N01/A02/A06, IKIGAI vector weights). Não escrever código de
algoritmo novo até 5+ SONHO logs manuais
(`vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/`). Decisões de
algoritmo deferidas até evidência empírica. The "pausado" directive applies
to **algorithm decisions only** — agent/harness plumbing and Drift net work
are not paused.

### Planning Note channel (human → agent)

Lightweight canal for planning changes. **Not** a ritual, **not** a gate —
the original "5+ SONHO logs" framing gated Wave 5 Scenario C, which was
dropped 2026-09-03 per
`~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-dropped-2026-09-03.md`;
the template was repurposed for the human→agent channel that the agent
layer will consume when it goes operational.

- **Template:** `vault/ikigai/templates/sonho-log.md` (filename retained for path stability — only CONTENT was repurposed; 1 section: `## Mudança`)
- **Trigger:** manual only — after any planning delta (sprint boundary, goal change, project pivot, scope refinement)
- **Cadence:** event-driven (NOT daily). 1–3 bullets per note, <2 min.
- **Where:** `vault/ikigai/closing-2026/<quarter>/04-relatórios-diários/YYYY-MM-DD.md`
- **Atrito-alvo:** zero — só registra o delta, sem análise ou refinamento

### Where shipped-wave history lives

Wave 3 / Wave 4 / Wave 5 / Plan C / Plan D / W6.X hygiene milestones,
commit hashes, PASS counts, and ADR-acceptance states all live in
`~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/` —
not here. CLAUDE.md is the durable-contract file; memory holds the
audit trail. Add a one-line memory entry per shipped wave and link it
from `MEMORY.md`.

## Root Layout (não-`src/`)

O Typer CLI raiz (`python -m life.cli …`) vive em diretórios paralelos a `src/`:

- `centrals/` — registradores (top-level handlers)
- `cli/` — entrypoints do CLI raiz
- `handlers/` — consumidores de plugins
- `plugins/` — extensões carregadas pelo CLI hub
- `tests/` — testes de integração top-level
- `openwiki/` — workspace parasita (≠ `.openwiki/` que é cache/config)

Pastas `.` de tooling também no root (não interferem no runtime, ignore):
`.agents`, `.atl`, `.claude-flow`, `.codex`, `.gitnexus`, `.hermes`,
`.hypothesis`, `.life`, `.openwiki`, `.pi`.

**Zero-byte artifacts untracked** (5): `0`, `14`, `agent('Execute`, `int`,
`None`. Causa provável: redirecionamento bash malformado
(`> agent('Execute')` virou arquivo em vez de string). Recomenda-se adicionar
ao `.gitignore` antes do próximo commit.

## LangGraph Graphs (vibe-ops, não src/)

Os 5 graphs registrados em `langgraph.json` montam em
`./vibe-ops/src/langgraph_entry.py` (`ikigai_maintainer` foi removido no
attribution §3 — `make_ikigai_graph` factory no longer exists):

| Graph | Entry factory |
|-------|---------------|
| `pae_maintainer` | `make_pae_graph` |
| `quarterly_replan` | `make_replan_graph` |
| `correction_protocol` | `make_correction_graph` |
| `dream_falsification` | `make_falsification_graph` |
| `test_de_fogo_rollup` | `make_rollup_graph` |

Para subir um graph específico: `make dev-graph NAME=pae_maintainer`.

> **Phase 8.1 (commit `fb41578`)** restaurou recovered IKIGAI architecture as
> `src/ikigai/src/agents/v2/` (parallel branch — `graph.py` + 9 nodes) but did
> **not** add a new graph entry to `langgraph.json`. The v2 graph code exists
> but is not registered as a LangGraph runtime graph.

---

---

## Drift Invariants & Tests

The Drift net is the regression guard for canonical contracts. If a
contributor changes a load-bearing invariant without explicitly bumping
the contract version, CI fails.

| File | Purpose | Approx lines |
|------|---------|--------------|
| `src/ikigai/tests/test_canonical_scope.py` | IKIGAI_TOOLS count, planner-only scope (no PAE math), fork MCP surface | 1586 |
| `src/ikigai/tests/test_drift_invariants.py` | UEID 4-part regex, append-only invariants, dual-tree identity | 297 |
| `src/ikigai/tests/test_drift_extended_invariants.py` | Wave 3+ invariants (a-h): canonical_scope, investigation_queue, dual-module identity, cross-pollution | growing |

**Invariant categories:**

1. **canonical_scope** — IKIGAI agent must remain planner-only (no PAE math execution; math/policy/scoring tools are explicitly forbidden per ADR-013).
2. **drift_invariants** — UEID 4-part canonical format (ADR-014); vault/strategics/vibe-ops append-only; vault_write is sole vault writer (ADR-012).
3. **dual_module_identity** — guards the `src.X` vs `X` import split that surfaced via taskdog CLI test failures (W6.X item 3). Tests must patch BOTH identities or `monkeypatch.setattr` silently no-ops.
4. **cross_pollution** — flags state pollution between test modules (e.g. shared filesystem fixtures leaking across boundaries). Same root cause as W6.X deferred finding.

**When you add a feature that crosses an invariant boundary**, the right
move is to add a new test in `test_drift_extended_invariants.py` rather
than weakening an existing one. Drift tests are append-only — they grow
with the system but never get deleted.

---

## Import-Path Rules

Two import styles coexist, and mixing them silently breaks tests:

| Layer | Style | Example | Resolves via |
|-------|-------|---------|--------------|
| `src/contracts/`, `src/mesh/`, `src/ikigai/` (agents/MCP) | dotted-prefix | `from src.contracts.sonho import ...` | `<repo>/src/` |
| `sys_ikigai/` (entities, gateway, state_machines, vault, security) | bare namespace | `from sys_ikigai.entities.task import Task` | `<repo>/sys_ikigai/` |

Both resolve from `<repo>/` after the 2026-09-05 namespace rename
(`src/ikigai/src/ikigai/` → `sys_ikigai/`, commit `685dec5`). The
`tests/conftest.py` setup adds `<repo>/` to `sys.path` once, and both
styles work.

**Why this matters — dual-module identity bug class:**

If production code uses dotted-prefix (`from src.contracts.X`) but a test
monkeypatches the bare module (`monkeypatch.setattr(sys.modules["contracts.X"], ...)`),
the patch silently no-ops because `sys.modules["src.contracts.X"]` is
the *actual* module instance the production code holds. The test
passes its assertion against an unpatched object. The first hit was
`test_taskdog_cli.py` (W6.X item 3, commit `3a4ed8c`); the structural
fix was the sys_ikigai rename which made the dotted-prefix pattern
explicit. **Rule: when monkeypatching, patch BOTH identities.**

---

## Windows Quirks

A handful of Windows-only bugs have shipped and stayed fixed. If you
hit them again, the fix is already known:

| Bug | Fix | Commit |
|-----|-----|--------|
| `sys.stdin.readline()` HANGS on Windows pipes (MCP stdio handshake) | Use `sys.stdin.buffer.readline()` | `b93a1f3` |
| pytest-asyncio raises `PermissionError [WinError 5]` on stale `AppData\Local\Temp\pytest-of-<user>\` dirs | `tests/conftest.py` redirects `tempfile.tempdir` + `TMPDIR`/`TEMP`/`TMP` to `data/pytest-tmp/` | `ff3037f` |
| Empty directory locked by another process (e.g. `__pycache__` mid-collect) | Mark for deletion via `PendingFileRenameOperations` registry, finishes on next reboot | per Windows orphan-dir memory |

**`mypy.ini`** lives at repo root (`mypy_path = src .. ../..` + `explicit_package_bases = True`, commit `39fd55a`) — the dup-source resolution closes the W6.X item 5 finding. The 542 remaining `[import-not-found]` errors are pre-existing stub-resolution issues, separate scope.

---

## What Is Broken / TODO

- **Deep Agent harness exists but doesn't fill interfaces yet — current state, NOT implicit roadmap.** v2 graph code lives at `src/ikigai/src/agents/v2/` but is not registered as a LangGraph runtime graph (Phase 8.1, commit `fb41578`). User scope (2026-09-06 pivot): agent **operates the interface** and **reasons about planning context** (SONHOS / metas / objetivos across projects/tasks). Filling interface fields automatically from agent output is **NOT the priority** and should not be re-introduced as a roadmap item without explicit user demand.
- **`vibe_ops.db` lives in `data/`** (Phase 0 audit-closure 2026-08-31) — some code paths may still reference old root location
- **Phase 3 v1 ships `create` only** for the data mesh; `update`/`delete`/`done` deferred. v1.2-v1.4 is **NOT a roadmap item** — only proceeds if user adjudicates (data-first SONHO-log gate was DROPPED 2026-09-03 per [[algorithm-gate-dropped-2026-09-03]]). Phase A extended fork side via MCP tools; Phase 8 restored agent v2 plumbing.
- **Phase 3 minor findings (logged, non-blocking)**: UPI `id` churn on UPSERT conflict; `propagate()` doesn't auto-ack `partial_propagation` status
- **MCP Gateway ✅ wired as code** — 15 IKIGAI_TOOLS + 7 fork tools (`sf_*` + `tuiboard_*`) in UnifiedMCPGateway + 6 resources (corrected 2026-09-04 per Diag 02); `vault_write` is the sole vault writer (ADR-012)
- **Path 3 taskdog MCP shipped (read-only)** — commit `6b9c9d1`. Canonical write path is still Path 1 (harness @tool → subprocess → taskdog.exe). See `docs/design-system/24-taskdog-paths-architecture.md`.

---

## Where to Start

| Task | Start here |
|------|-----------|
| Using mesh | `python -m interfaces.cli.main mesh show <ueid>` (after `task add ...`) |
| Building interfaces | `interfaces/cli/` (split 6 modules) or `interfaces/tui/operator/` (Textual 4-tab) |
| Deep Agent development | `src/ikigai/src/agents/` (v2 graph + 9 nodes) + `vault/` |
| Unifying contracts | `src/contracts/` + `src/mesh/` (Phase 3 DONE) |
| MCP Gateway integration | `src/ikigai/MCP_GATEWAY.md` |
| Understanding the system | `docs/ARCHITECTURE_INDEX.md` |
| Kill switch (pause/resume engine) | `sys_ikigai/security/kill_switch.py` + CLI `kill_switch status\|pause\|resume` + 5th TUI tab |
| Drift net / invariant work | `src/ikigai/tests/test_canonical_scope.py` + `test_drift_invariants.py` + `test_drift_extended_invariants.py` |
| Phase 3 spec/plan | `docs/superpowers/specs/` + `docs/superpowers/plans/` (2026-08-28) |

---

## Refactor Protocol

If touching vault/, vibe-ops/, or strategics/: stop → propose Action Plan → wait for explicit "go" → verify every pre-existing string survives.

---

## Pitfalls

- **Don't restore old PAV TUI/CLI** — apps/cli and apps/tui were deleted intentionally; build new interfaces under interfaces/
- **Deep Agent writes vault; interfaces don't** — interfaces only read from data/
- **Append-only rule** enforced on vault/, vibe-ops/, strategics/, AND `data/review_queue/`
- **vibe_ops.db lives in data/** — update any code paths that reference it at the old root location
- **v1 mesh scope = create only** — adapters early-return on non-create actions; do not add update/delete/done logic until v1.2

---

*Algorithmic Life OS — CLAUDE.md — 2026-09-03 (audit cleanup)*

<!-- OPENWIKI:START -->

## OpenWiki

See [AGENTS.md](AGENTS.md) for OpenWiki agent instructions.

<!-- OPENWIKI:END -->
