# Algorithmic Life OS

> **Camada de dados primeiro.** A virada canônica de 2026-11-01 (ADR-037)
> substituiu o foco em interfaces por um foco na **engenharia de dados**:
> um único Postgres serverless que hospeda o vault versionado e indexado,
> servindo **vector + graph + embeddings**, exposto por camadas de serviço
> e transporte (MCP) a múltiplos clientes e dispositivos — sobre um harness
> **já pronto** (pi), não um novo.
>
> Anterior (2026-08-28): deep-agent bidirecional ↔ forks-prontas widgets com
> vault markdown local. PAV desativado (2026-08-26).

---

## ⭐ Virada Canônica — 2026-11-01 (ADR-037)

**A ordem de esforço é esta, e ela *é* a decisão:**

```
1. CAMADA DE DADOS          ← toda a força vai aqui agora
   ├─ DOM unificado (schema + tipagem forte + UID)
   ├─ Store cloud (Postgres serverless) — versionamento, índices, vector, graph
   └─ Sync vault markdown ↔ store
2. CAMADAS DE SERVIÇO + TRANSPORTE   (services/ → MCP over HTTP)
3. BACKEND                   (harness pi; a repo NÃO constrói harness)
4. CLIENTES                  (Telegram ← foco atual · TUI/PC ← standby)
```

| Decisão | O que significa |
|---|---|
| **Um DOM, N projeções** | Um modelo de dados único em `src/contracts/`. Cada app decide como usá-lo. KPI/DESC/OKR → **UID** → a mesma view em N clientes, zero duplicação |
| **Um único store cloud** | Postgres serverless (candidata: Supabase). Serve vector (pgvector), graph (arestas + FK) e busca estruturada — um só banco, uma transação, um backup |
| **Um writer por store** | `vault_write` no markdown; a service layer no Postgres. `revision` otimista + `idempotency_key` → conflito explícito (409), nunca last-write-wins |
| **Versionamento multi-cliente** | Updates do vault versionados entre dispositivos, com histórico append-only (`artifact_revisions`, soft delete) |
| **Reusar harness** | O pi é o runtime. A repo **não** constrói agent framework, grafo custom, checkpoint ou memory layer |
| **TUI em standby** | Uma das superfícies previstas (PC). Telegram é o cliente em foco — mas **só depois** de infra |
| **Invariante substituída** | "Fully local — zero cloud deps" → **single cloud store + local cache** |

**Documentos canônicos:**
- Decisão: [`code-docs/adr/ADR-037-data-layer-canonical-turn.md`](../code-docs/adr/ADR-037-data-layer-canonical-turn.md)
- Série de specs: [`docs/superpowers/specs/2026-11-01-00-data-layer-series.md`](superpowers/specs/2026-11-01-00-data-layer-series.md) · [01 DOM](superpowers/specs/2026-11-01-01-unified-dom.md) · [02 Store](superpowers/specs/2026-11-01-02-cloud-store.md) · [03 Service+Transporte](superpowers/specs/2026-11-01-03-service-transport-pi.md)
- Plano de implementação: [`specs/data-layer/TECH.md`](../specs/data-layer/TECH.md)
- Relatório que precede a virada: [`docs/vanilla-pivot.html`](vanilla-pivot.html) (2026-10-30)

**A série anterior (Vanilla Pivot, 2026-10-30) e como foi re-alvo:** ver [ADR-037 §7](../code-docs/adr/ADR-037-data-layer-canonical-turn.md) — as specs 01 e 03 foram superadas, a 02 virou o primeiro cliente, a 04 foi adiada, e a 05 (corte ~15k LOC) foi antecipada e segue *gated*.

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
| `src/contracts/` | Pydantic v2 | Canonical contracts (`UEID`, `Task`, `PlanningCycle`, `TaskChange`) + **DOM unificado** (SPEC-01) | 🟢 Canonical |
| `src/data/` + `src/services/` + `src/transport/` | Python | **Camada de dados**: client Postgres · domínio puro · MCP over HTTP | 🆕 SPEC-01–03 — a construir |
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

## Current Mode (2026-11-01 — camada de dados)

**A força vai para a camada de dados.** Nada de produto novo antes de a base existir.

| Fase | Spec | Entrega | Condição de passagem |
|---|---|---|---|
| 1 | [SPEC-01](superpowers/specs/2026-11-01-01-unified-dom.md) | DOM unificado — schema, tipagem forte, UID | Contrato Pydantic + drift test contra o SQL |
| 2 | [SPEC-02](superpowers/specs/2026-11-01-02-cloud-store.md) | Store cloud — versionamento, índices, vector, graph, RLS | Busca < 50ms p95 em 10k; escrita concorrente sem lost update |
| 3 | [SPEC-03](superpowers/specs/2026-11-01-03-service-transport-pi.md) | Services + MCP + integração pi | `search`/`upsert` respondem **no fluxo normal do pi** |
| 4 | — | Cliente Telegram (primeiro cliente real) | KPI/DESC/OKR do vault aparecem no bot |
| 5 | — | Corte do harness (~15k LOC, SPEC-05) | *gated* — go explícito do owner |

**O gate anterior ("5+ SONHO logs") foi substituído** pela métrica de 14 dias do
ADR-037 §8: uma nota escrita **sem editar arquivo à mão**, de um cliente que não
é o desktop; **zero lost update** com 2 clientes ativos; `p95` de busca
estruturada < 100ms.

**O que está explicitamente em standby:** TUI (uma das superfícies PC), o
`fin_ops` (read-only, intocado), o timeline como artefato-alvo (vira uma *view*
sobre o DOM), e qualquer harness novo.

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
| **Fully local** | ~~SQLite + filesystem only, zero cloud deps~~ → **substituída** por *single cloud store + local cache* (ADR-037 D1/D3) |
| **Single cloud store** | Postgres serverless (candidata Supabase) — vector, graph e busca estruturada no mesmo banco, uma transação |
| **Um writer por store** | `vault_write` no markdown · service layer no Postgres — `revision` otimista + `idempotency_key`; conflito = **409**, nunca last-write-wins |
| **Um DOM, N projeções** | Contrato único em `src/contracts/`; **cada app decide a view**. Nenhum campo de interface no contrato |
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
| **AI agent implementing the data layer** (a prioridade agora) | [ADR-037](../code-docs/adr/ADR-037-data-layer-canonical-turn.md) → [série 2026-11-01](superpowers/specs/2026-11-01-00-data-layer-series.md) → [TECH.md](../specs/data-layer/TECH.md) |
| **AI agent implementing a feature** (fora da camada de dados) | `src/contracts/` + relevant `code-docs/adr/` — **e confira a fase em ADR-037 §3 D1 antes de aceitar** |
| AI agent auditing gaps | `docs/diagnostics/2026-08-28-structure-audit/` |
| Human wanting to understand the system | `docs/README.md` §"⭐ Virada Canônica" → ADR-037 |
| Human wanting to use the system | `interfaces/cli/` — mas a TUI está **standby**; o cliente em foco depois da infra é o Telegram |

---

*Algorithmic Life OS — Root README — virada canônica 2026-11-01: camada de dados primeiro (ADR-037)*

---

## Documentation index (2026-08-28 refactor)

Este README cobre apenas a camada raiz. A canonical reference completa
vive em [`docs/design-system/`](design-system/00-INDEX.md) (40 docs em 9 camadas).
Abaixo, índice de todas as sub-árvores de documentação sob `docs/` para
navegação rápida:

**Camada canônica (referência pós-pivot 2026-08-26):**
- [`docs/design-system/`](design-system/00-INDEX.md) — **canônico**. 40 docs, 9 camadas: topology, architecture canvases, patterns, forks, tokens, journeys, validation, critical analysis. **Comece aqui.**
- [`docs/auto-performance-os/`](auto-performance-os/) — matemática deep-agent (derivação dos auto-performace algorithms que substituem o PAV)

**Auditorias & migrações (diagnósticos 2026-08-28):**
- [`docs/diagnostics/2026-08-28-structure-audit/`](diagnostics/2026-08-28-structure-audit/) — varredura estrutural pós-pivot (40 findings, 13 refuted)
- [`docs/diagnostics/2026-08-28-doc-migration/`](diagnostics/2026-08-28-doc-migration/) — migração de docs legacy (95 docs classificados, 33 trailers aplicados)

**Plano & specs (superpowers, com trailers aplicados):**
- [`docs/superpowers/`](superpowers/) — specs formais, planos de implementação, glossários (maioria já trailer SUPERSEDED 2026-08-28)

**Integrações & visualizadores (escopo preservado):**
- [`docs/integrations/`](integrations/) — integrações externas (job-hunter, fin_ops, etc.)
- [`docs/openwiki-visualizer/`](openwiki-visualizer/) — workspace parasita OpenWiki (visualização)
- [`docs/research/`](research/) — research notes, papers, references

**Root docs preservados (escopo legacy PAV-era, com trailers):**
- [`docs/SPEC.md`](SPEC.md) — índice de ADRs/PRDs/BRDs (escopo preservado)
- [`docs/ARCHITECTURE_INDEX.md`](ARCHITECTURE_INDEX.md) — [SUPERSEDED] índice pré-pivot
- [`docs/CONCEPTUAL_MODEL.md`](CONCEPTUAL_MODEL.md) — [SUPERSEDED] modelo conceitual T→B→S pré-pivot
- [`docs/SYSTEMS_TOPOLOGY.md`](SYSTEMS_TOPOLOGY.md) — [SUPERSEDED] mapa de middlewares pré-pivot
- [`docs/PAV_INVENTORY.md`](PAV_INVENTORY.md) — [SUPERSEDED] inventário PAV kernel (1982L)
- [`docs/DEPLOY.md`](DEPLOY.md) — [SUPERSEDED] WSL2 / VPS bootstrap

**Regra de navegação:** comece pelo [`docs/design-system/00-INDEX.md`](design-system/00-INDEX.md)
e só desça para `auto-performance-os/` ou `superpowers/` quando o deep-agent
pedir matemática derivada ou specs formais específicas.

*Para a entry-point por persona (humano vs AI agent), ver a tabela
"Entry Points by Persona" acima neste README; o equivalente atualizado vive
no design-system/00-INDEX.md.*
