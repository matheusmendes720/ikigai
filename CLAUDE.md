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
│   ├── contracts/              ← CANONICAL Pydantic contracts (NEW)
│   │   ├── common.py           UEID, Period, Priority, EntityType, RegimeState
│   │   ├── task.py            Task, Subtask, ChecklistItem, Project, Milestone, Deliverable
│   │   ├── planning.py        PlanningCycle, Wave, Sprint, VaultEvent
│   │   └── metrics.py         Burndown, ExecutionRate, QHEScore
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
├── interfaces/                  INTERFACE LAYER (consumers — to be built)
│   ├── cli/                   daily-view, kanban, gantt, calendar
│   └── tui/                   TUI apps
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
poetry install
ikigai.bat mcp          # start MCP server (8 tools)
ikigai.bat agent <thread>
ikigai.bat chat <thread>
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

### MCP Gateway (life-ops/ikigai/MCP_GATEWAY.md)

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
| `planning.py` | `PlanningCycle`, `Wave`, `Sprint`, `VaultEvent` |
| `metrics.py` | `Burndown`, `ExecutionRate`, `QHEScore` |

### Vibe-ops: Target-Sensor-Adjuster Loop

`src/cybernetics/daily_loop.py`: TARGET → SENSOR → ADJUSTER → PERSIST → SYNC → INDEX
`SyncEngine` (src/middleware/sync_engine.py): Obsidian ↔ SQLite ↔ Taskwarrior.
UEID format: `<CLUSTER>:<ENTITY>:<ID>`.

PolicyEngine states (PUSH / MAINTAIN / REDUCE / RECOVER) with hysteresis.

---

## What Is Broken / TODO

- **interfaces/ is empty** — needs building (Phase 4-6 of reorg)
- **MCP Gateway described in docs but not wired as code**
- **Deep Agent harness exists but doesn't fill interfaces yet**
- **vibe_ops.db moved to data/** — some code paths may still reference old locations

---

## Where to Start

| Task | Start here |
|------|-----------|
| Building interfaces | interfaces/cli/ or interfaces/tui/ |
| Deep Agent development | src/ikigai/src/agents/ + vault/ |
| Unifying contracts | src/contracts/ (Phase 3 DONE — verify imports) |
| MCP Gateway integration | life-ops/ikigai/MCP_GATEWAY.md |
| Understanding the system | docs/ARCHITECTURE_INDEX.md |

---

## Refactor Protocol

If touching vault/, vibe-ops/, or strategics/: stop → propose Action Plan → wait for explicit "go" → verify every pre-existing string survives.

---

## Pitfalls

- **Don't restore old PAV TUI/CLI** — apps/cli and apps/tui were deleted intentionally; build new interfaces under interfaces/
- **Deep Agent writes vault; interfaces don't** — interfaces only read from data/
- **Append-only rule** enforced on vault/, vibe-ops/, strategics/
- **vibe_ops.db lives in data/** — update any code paths that reference it at the old root location

---

*Algorithmic Life OS — CLAUDE.md — 2026-08-27*
