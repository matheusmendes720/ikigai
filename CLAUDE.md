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
│   ├── ikigai/                ← was life-ops/ikigai/ (Deep Agent + MCP)
│   ├── life_tatics/            ← was life-ops/life_tatics/
│   └── planner/                ← was life-ops/planner/
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
│   ├── cli/                   Typer CLI — `life mesh show`, `life task add` (Phase 3 v1)
│   └── tui/                   TUI apps (planned)
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

## Current Mode (2026-09-04)

**Data-first methodology** — IKIGAi está pausado para *novas decisões de
algoritmo* (M01/N01/A02/A06, IKIGAI vector weights). Não escrever código de
algoritmo novo até 5+ SONHO logs manuais
(`vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/`). Decisões de
algoritmo deferidas até evidência empírica.

> **Phase 8 SHIPPED (2026-09-03, commits `fb41578` → `3b7b8f6`)** actively
> restored agent code (`src/ikigai/src/agents/v2/`) + MCP wrappers + gateway
> E2E + v2 interfaces + 9th v2 node surfacing PAV intentions. The "pausado /
> não escrever novo código" directive is applicable to **algorithm decisions
> only**, not to agent/harness plumbing. Estado vivo em
> `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/MEMORY.md`.

> **Wave 3 SHIPPED (2026-09-04, dcode-harness roadmap)** — **8/8 Wave 3 tasks
> shipped**:
>
> | Task | Commit | Status |
> |------|--------|--------|
> | W3.1 — multi-tree pytest collection | `688b316` | ✅ shipped |
> | W3.2 — QHE constants → prompt-template | `1ef638c` | ✅ shipped (49/49 PASS, ruff clean, ADR-019 forthcoming W5.2) |
> | W3.3 — v2 graph smoke test | `0f3feb1` | ✅ shipped (17/17 PASS, API 529 retry helper per Diag 03) |
> | W3.4 — ADR-025 skill binding mechanism | `9604443` + `82de324` | ✅ shipped **Accepted 2026-09-04** |
> | W3.5 — wire daily entry point | `c3f9251` + `01d4005` + `27e7a4b` + `3c086a1` | ✅ shipped (37 PASS / 9 skipped) |
> | W3.6 — CLI wrapper triggers graph → taskdog Path 1 | `059cffb` | ✅ shipped (75/75 v2 combo PASS, drift invariant l) |
> | W3.7 — stale NODES count assertion | `fbe083c` | ✅ shipped (drift fix discovered during Wave 3 regression sweep) |
> | W3.8 — E2E smoke chat → vault + taskdog → fork | `b77e0f1` | ✅ shipped (78/78 PASS, drift 24/24) |
>
> Wave 3 cumulative regression: **78/78 PASS** in v2 combo (canonical_scope 24
> + invoke_skill_taskdog 12 + daily 17 + graph_smoke 17 + e2e_smoke 3 +
> imports_safely 8 + entry_point 5). ruff clean across all modified files.
> Zero Wave 3 regressions.
>
> **Wave 3 final acceptance gated on user review (#11) of 4 masters + PLAN +
> TASKS.** Two open follow-ups surfaced from Wave 3 review (both non-blocking,
> tracked in `~/.git/sdd/progress.md`):
> 1. CLI wrapper gap — `interfaces/cli/v2.py:_run_weekly/_run_monthly/_run_quarterly`
>    still use the W2.3 cycle+score+regime path and don't route through
>    `invoke_skill()`. Only `_run_daily` was wired in W3.5. Separate scope.
> 2. `interfaces/cli/v2.py` 747 lines (CLAUDE.md 500-line guideline; pre-existing,
>    exacerbated by W3.6 post-processor extraction to `_skill_outputs.py`).
>
> **Wave 4 kickoff (Scenario B: Sub-agents + stateful subgraphs, 32-44h)** is
> pending the user's #11 4-master review acceptance. Wave 3 zero
> regressions; one pre-existing stale-assertion drift fixed (W3.7).
>
> **Wave 3 SHIP-COMPLETE — awaiting #11 4-master review for Wave 4 kickoff.**
> All Wave 3 blockers (ADR-025 acceptance, W3.5/3.6/3.7/3.8 ships) cleared.
> Wave 4 Scenario B (Sub-agents + stateful subgraphs, 32-44h) requires user
> acceptance of the 4 masters before kickoff.

> **Plan D SHIPPED (2026-09-04, commits `2b43502`..`cf353ad`, 14 commits)** — meta-planner integration. Spec at `docs/superpowers/specs/2026-09-04-meta-planner-design.md` + plan at `docs/superpowers/plans/2026-09-04-meta-planner-plan-d.md`. 6 tracks (A contracts / B subgraph nodes / C state wiring / D observe hint / E CLI / F ADR-031). 11 Pydantic v2 strict contracts + 3 nodes + 3-node subgraph factory + `life v2 plan` CLI command + 3 E2E tests. Final reviewer verdict: APPROVED_FOR_USER_ACCEPTANCE. Drift 41/41 PASS, E.2 tests 3/3 PASS. ADR-031 status: DRAFT (pending #11 acceptance).

> **Plan C SHIPPED (2026-09-05, commits `52e0e9e`..`30e0fd1`, 6 commits)** — Investigation Queue. Pre-form observation queue for raw data / shadow loops / ambiguous leads that don't fit the 6-level SONHO/OBJETIVO/META/PROJETO/ENTREGA/TAREFA hierarchy. Plan at `docs/superpowers/plans/2026-09-03-investigation-queue-plan-c.md`. 6 tracks (T1 schema / T2 queue helpers / T3 MCP tools / T4 drift invariant h / T5 dispatcher / T6 integration smoke). 1 Pydantic v2 strict contract (`Investigation` + `InvestigationStatus` Literal) + filesystem append-only queue at `data/investigation_queue/` with audit log + 3 MCP tools (`investigation_enqueue` / `investigation_status` / `investigation_complete`) + cron-invoked dispatcher worker (pure dispatch, NO LLM, 3 rules: stale→archive, crystallized→resolve, ready-tag→hint) + drift invariant (h) `test_investigation_queue_invariants` + 7-test E2E smoke. Final reviewer verdict: APPROVED_FOR_USER_ACCEPTANCE. Drift 41/41 → 42/42 PASS, runnable 95/95 PASS post-W6.X (commit `ff3037f` unblocked 13 tests/mesh/ PermissionErrors; combined sweep 42 drift + 8 contracts + 10 lifecycle + 15 dispatcher + 7 integration + 13 queue). 4 minor non-blocking findings (M-1 docstring vs assertion mismatch, M-2 test count +1 superset, M-3 MCP count 19 not 15 incl Plan B forks, M-4 already-fixed-via-this-update) deferred to Wave 6 hygiene. SONHO tree now persistable from all 3 input streams: Plan A (native), Plan B (external research), Plan C (pre-form observations).

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

## What Is Broken / TODO

- **interfaces/tui/ is empty** — Phase 4-6 of reorg (CLI shipped in Phase 3 v1)
- **MCP Gateway ✅ wired as code** — 19 tools advertised (12 IKIGAI_TOOLS + 7 fork tools: `sf_*` + `tuiboard_*` per Phase A); `vault_write` sole vault writer (ADR-012)
- **Deep Agent harness exists but doesn't fill interfaces yet**
- **`vibe_ops.db` moved to `data/`**; `vibe_ops_test.db` moved to `data/test-fixtures/` (Phase 0 audit-closure 2026-08-31) — some code paths may still reference old locations
- **Phase 3 v1 ships `create` only** for the data mesh; `update`/`delete`/`done` deferred to v1.2-v1.4 (gated on data-first methodology: 5+ SONHO logs). Phase A SHIPPED extended fork side via MCP tools; Phase 8 SHIPPED restored agent v2 plumbing.
- **Phase 3 minor findings (logged, non-blocking)**: UPI `id` churn on UPSERT conflict; `propagate()` doesn't auto-ack `partial_propagation` status
- **Path 3 taskdog MCP gateway DEFERRED** — `taskdog_mcp.server` module not built; canonical path is Path 1 (harness @tool → subprocess → taskdog.exe). See `docs/design-system/24-taskdog-paths-architecture.md`.

---

## Where to Start

| Task | Start here |
|------|-----------|
| Using mesh | `life mesh show <ueid>` (after `life task add ...`) |
| Building interfaces | interfaces/cli/ or interfaces/tui/ |
| Deep Agent development | src/ikigai/src/agents/ + vault/ |
| Unifying contracts | src/contracts/ + src/mesh/ (Phase 3 DONE) |
| MCP Gateway integration | src/ikigai/MCP_GATEWAY.md |
| Understanding the system | docs/ARCHITECTURE_INDEX.md |
| Phase 3 spec/plan | docs/superpowers/specs/ + docs/superpowers/plans/ (2026-08-28) |

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
