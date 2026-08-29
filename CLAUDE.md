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
│  Reads vault/ → applies strategics + PAE → writes tasks   │
│  to data/ → observes planned vs actual → updates vault    │
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
  → Deep Agent (interpreta, aplica PAE, gera tasks)
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
│   ├── operational/            ← was life-ops/operational/ (PAV kernel)
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
├── langgraph.json              6 registered LangGraph graphs
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

### PAV kernel (src/operational/)

```bash
cd src/operational
uv sync
uv run pytest
uv run ruff check src/
uv run mypy src/
```

### IKIGAi Deep Agent (src/ikigai/)

```bash
cd src/ikigai
uv sync                 # uv-managed (NOT poetry — see q3-q4-resolved memory)
ikigai.bat mcp          # start MCP server (8 tools)
ikigai.bat agent <thread>
ikigai.bat chat <thread>
```

### Phase B3 — MCP Gateway

```bash
# Contract test — enumerates tools + resources via stdio handshake
make mcp-inspect              # POSIX (uses system python)
scripts/mcp-inspect.bat       # Windows cmd/PowerShell wrapper
python scripts/mcp_inspect.py # Direct invocation (any platform)

# Optional flags
python scripts/mcp_inspect.py --tool-count 13 --resource-count 3
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

The **carro-chefe**. Reads vault markdown → applies strategics + PAE → writes structured tasks to data/ → interfaces consume from data/ → observes planned vs actual → updates vault.

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

- **UEID** is the canonical join key across all forks (5-part regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`)
- **Write path**: fork → CLI enqueues `TaskChange` to `data/review_queue/` → Agent validates → propagates `PropagationEvent` to all forks
- **Read path**: `life mesh show <ueid>` joins slices from all 3 adapters (CLI / taskdog / UPI)
- **3 adapters** (all implement `ForkAdapter` Protocol): `CliAdapter`, `TaskdogAdapter`, `SolverforgeCalendarAdapter`
- **v1.2+ (out of scope)**: `update`, `delete`, `done` actions; tuiboard adapter; LLM-driven validation

### Vibe-ops: Target-Sensor-Adjuster Loop

`src/cybernetics/daily_loop.py`: TARGET → SENSOR → ADJUSTER → PERSIST → SYNC → INDEX
`SyncEngine` (src/middleware/sync_engine.py): Obsidian ↔ SQLite ↔ Taskwarrior.
UEID format: `<CLUSTER>:<ENTITY>:<ID>`.

PolicyEngine states (PUSH / MAINTAIN / REDUCE / RECOVER) with hysteresis.

---

## Current Mode (2026-08-28)

**Data-first methodology** — IKIGAi está pausado. Não escrever novo código
até 5+ SONHO logs manuais
(`vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/`). Decisões de
algoritmo (M01/N01/A02/A06, IKIGAI vector weights) deferidas até evidência
empírica. Estado vivo em
`~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/MEMORY.md`.

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

Todos os 6 graphs registrados em `langgraph.json` montam em
`./vibe-ops/src/langgraph_entry.py`:

| Graph | Entry factory |
|-------|---------------|
| `pae_maintainer` | `make_pae_graph` |
| `ikigai_maintainer` | `make_ikigai_graph` |
| `quarterly_replan` | `make_replan_graph` |
| `correction_protocol` | `make_correction_graph` |
| `dream_falsification` | `make_falsification_graph` |
| `test_de_fogo_rollup` | `make_rollup_graph` |

Para subir um graph específico: `make dev-graph NAME=ikigai_maintainer`.

---

## What Is Broken / TODO

- **interfaces/tui/ is empty** — Phase 4-6 of reorg (CLI shipped in Phase 3 v1)
- **MCP Gateway described in docs but not wired as code**
- **Deep Agent harness exists but doesn't fill interfaces yet**
- **vibe_ops.db moved to data/** — some code paths may still reference old locations
- **Phase 3 v1 ships `create` only** — `update`/`delete`/`done` deferred to v1.2-v1.4 (gated on data-first methodology: 5+ SONHO logs)
- **Phase 3 minor findings (logged, non-blocking)**: UPI `id` churn on UPSERT conflict; `propagate()` doesn't auto-ack `partial_propagation` status

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

*Algorithmic Life OS — CLAUDE.md — 2026-08-28*
