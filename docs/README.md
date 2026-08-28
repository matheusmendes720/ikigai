# Algorithmic Life OS

> **Personal productivity orchestration** — a deep-agent (AI-native) harness
> that bidirectionally syncs forks-prontas widgets (tuiboard, taskdog,
> solverforge-calendar) with a vault of local markdown. 100% local,
> single-user, append-only. Post-pivot (2026-08-26): PAV desativado,
> IKIGAi in design.

---

## GitHub Infrastructure

| Resource | URL |
|----------|-----|
| **Repository** | https://github.com/matheusmendes720/ikigai |
| **Project Board** | https://github.com/users/matheusmendes720/projects/5 |
| **Issues** | https://github.com/matheusmendes720/ikigai/issues |
| **Wiki** | https://github.com/matheusmendes720/ikigai/wiki |
| **CI/CD** | `.github/workflows/ci.yml` — ruff, mypy, pytest, pre-commit |

---

## TL;DR — Canonical Architecture (post 2026-08-26)

```
┌────────────────────────────────────────────────────────────────┐
│  Deep Agent (AI-native harness)                                │
│  Reads vault/ → applies strategics + PAE → writes tasks to    │
│  data/ → observes planned vs actual → updates vault            │
└────────────────────────────┬───────────────────────────────────┘
                             │ MCP contracts (Pydantic v2 strict)
        ┌────────────────────┼─────────────────────┐
        ▼                    ▼                     ▼
   ┌─────────┐          ┌─────────┐          ┌──────────────────┐
   │tuiboard │          │ taskdog │          │solverforge-      │
   │(TS/Bun) │          │ (Py)    │          │calendar (Rust)   │
   │ Kanban  │          │ Tasks   │          │ Calendar         │
   └─────────┘          └─────────┘          └──────────────────┘
   forks-prontas widgets — bidirectional sync ↔ vault/ local `.db.markdown`
```

**Canonical flow:**
```
vault (NL planning)
  → Deep Agent (interprets, applies PAE, generates tasks)
    → MCP Gateway (syncs vault ↔ forks)
      → Forks render tasks for the user to mark
        → Manual input (burndown, execution rate)
          → Deep Agent observes gap
            → Updates planning (vault)
              → continuous cycle
```

For the full canonical contract, see
[master-branch-carro-chefe-2026-08-28](https://github.com/matheusmendes720/ikigai)
(reference doc in memory `master-branch-carro-chefe-2026-08-28.md`).

---

## Subsystem Components

| Path | Type | Role | Status |
|------|------|------|--------|
| `src/operational/` | Python (uv) | PAV productivity kernel — reference implementation, desativado | 🟡 Reference |
| `src/ikigai/` | Python (uv) | Deep Agent + MCP server — design in progress | 🟢 Design |
| `src/contracts/` | Pydantic v2 | Canonical contracts (`UEID`, `Task`, `PlanningCycle`, `TaskChange`) | 🟢 Canonical |
| `src/mesh/` | Python (uv) | Data mesh (Phase 3 v1) — `create` action across 3 adapters | 🟢 Active |
| `vault/` | Markdown | NL planning source of truth (append-only) | 🟢 Active |
| `data/` | SQLite + JSON | Runtime state (append-only) | 🟢 Active |
| `vibe-ops/` | Python + Rust | Cybernetic engine — preserved per append-only invariant | 🟡 Reference |
| `strategics/` | Markdown (PT-BR) | Strategic prose — read-only | 🟢 Read-only |
| `interfaces/` | Typer CLI + Rust TUI | User-facing consumers — read from `data/`, write feedback | 🟢 Phase 4-6 |
| `langgraph.json` | Spec | 2 active graphs (ikigai_maintainer, pae_maintainer) | 🟢 Active |

For full subsystem topology, see [docs/SYSTEMS_TOPOLOGY.md](SYSTEMS_TOPOLOGY.md)
(retained, SUPERSEDED trailer noting pre-pivot framing — see new canonical
section in `docs/diagnostics/2026-08-28-structure-audit/`).

---

## Current Mode (2026-08-28)

**Data-first methodology (ADR-007):** IKIGAi is paused. No new code
until **5+ manual SONHO logs** exist in
`vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/`.
Algorithm/template/registry polish deferred per
`algorithm-decisions-defer-2026-08-28`.

The deep-agent harness above is the **design target** — implemented
incrementally as logs prove the workflow.

---

## Quick Start

### Phase 3 v1 mesh (active)

```bash
# Add a task (CLI adapter)
life task add "Write architecture ADR" --priority HIGH --json

# Show cross-fork state for a task
life mesh show <ueid>
```

### PAV reference (read-only — desativado)

```bash
cd src/operational
uv sync
uv run pytest             # reference implementation, kept for audit
```

### IKIGAi (design — pending 5+ SONHO logs)

```bash
cd src/ikigai
uv sync
ikigai.bat mcp            # MCP server (8 tools)
```

---

## Directory Tree (post 2026-08-28 audit)

```
life/
├── CLAUDE.md                      Claude Code guidance (canonical)
├── AGENTS.md                      AI agent rules
├── docs/                          Architecture docs + diagnostics
│   ├── ARCHITECTURE_INDEX.md       [SUPERSEDED] pre-pivot index
│   ├── SYSTEMS_TOPOLOGY.md         [SUPERSEDED] pre-pivot topology
│   ├── CONCEPTUAL_MODEL.md         [SUPERSEDED] pre-pivot model
│   ├── PAV_INVENTORY.md            [SUPERSEDED] PAV kernel inventory (1976L)
│   ├── DEPLOY.md                   [SUPERSEDED] WSL2 / VPS bootstrap
│   ├── diagnostics/                Audit + migration plans
│   │   ├── 2026-08-28-structure-audit/
│   │   └── 2026-08-28-doc-migration/
│   └── superpowers/                Specs, plans, glossaries (mostly trailers)
│
├── src/                           Canonical code (per CLAUDE.md §Root Layout)
│   ├── operational/               PAV kernel — desativado, reference only
│   ├── ikigai/                    Deep Agent + MCP — design in progress
│   ├── contracts/                 Pydantic v2 canonical models
│   └── mesh/                      Phase 3 v1 data mesh
│
├── vault/                         Append-only markdown source of truth
│   ├── ikigai/closing-2026/       Planning cycles
│   ├── ikigai/meta/               MOCs, indexes, dashboards
│   └── drafts/evidence/           PAE coverage, evidence trail
│
├── data/                          Runtime state (SQLite + chroma + JSON)
│   ├── vibe_ops.db
│   ├── vibe_mesh.db
│   └── boulder.json
│
├── vibe-ops/                      Cybernetic engine — append-only
├── strategics/                    PT-BR strategic prose — read-only
├── interfaces/                    CLI + TUI consumers (Phase 4-6)
├── code-docs/                     ADRs, BRDs, PRDs, RDs (33 SUPERSEDED trailers)
├── diagrams/                      Mermaid source files
├── taskwarrior/                   TW binary + scripts (reference)
└── langgraph.json                 2 active LangGraph graphs
```

---

## Global Conventions

| Rule | Description |
|------|-------------|
| **Deep Agent is the only writer to `vault/`** | Interfaces only read vault; write goes to `data/feedback/` |
| **Append-only invariant** | Never delete in `vault/`, `vibe-ops/`, `strategics/`, `data/review_queue/` |
| **Pydantic v2 strict** | All schemas: `frozen=True`, `extra="forbid"` |
| **Contracts in `src/contracts/`** | Imported by all layers — single source of truth |
| **`--json` everywhere** | Every CLI command supports `--json` |
| **Fully local** | SQLite + filesystem only, zero cloud deps |
| **uv, not poetry** | Both PAV and IKIGAi managed with uv (per Q3 resolved 2026-08-27) |

---

## Canonical References (post 2026-08-26)

- **Architecture (canonical):** `~/.claude/projects/.../memory/master-branch-carro-chefe-2026-08-28.md`
- **Era context:** `~/.claude/projects/.../memory/legacy-pav-ui-era-2026-08-28.md`
- **Data-first mode:** `~/.claude/projects/.../memory/data-first-methodology.md`
- **Trailer pattern:** `~/.claude/projects/.../memory/docs-superseded-trailer-2026-08-28.md`
- **Structure audit:** `docs/diagnostics/2026-08-28-structure-audit/00-INDEX.md`
- **Doc migration:** `docs/diagnostics/2026-08-28-doc-migration/00-INDEX.md`

---

## Entry Points by Persona

| Persona | Start Here |
|---------|-----------|
| Human wanting to use the system | `interfaces/cli/` (Phase 3 v1 mesh CLI) |
| Human wanting to understand the system | `docs/diagnostics/2026-08-28-structure-audit/00-INDEX.md` |
| AI agent implementing a feature | `src/contracts/` + relevant `code-docs/adr/` (read trailers first) |
| AI agent auditing gaps | `docs/diagnostics/2026-08-28-structure-audit/` |

---

*Algorithmic Life OS — Root README — rewritten 2026-08-28 under canonical architecture*
