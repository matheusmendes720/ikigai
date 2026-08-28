# 00 — Índice: Design System (Híbrido — UI Tokens + Arquitetura)

> **Categoria:** INDEX navegável (stub — atualização completa no Batch 8)
> **Público:** Eu mesmo + agentes futuros
> **Localização:** `docs/design-system/`
> **Total planejado:** 38 documentos em 8 camadas

---

## §0 — Visão panorâmica (post-pivot 2026-08-26)

Este docset é o **índice navegável** do design system híbrido do IKIGAi na era **deep-agent canonical** (PAV desativado). Cobre duas dimensões complementares:

1. **UI Tokens** — paleta semântica, tipografia, espaçamento, glifos, componentes visuais (cross-link para `src/operational/docs/ux/` e estende para era deep-agent)
2. **Padrões arquiteturais** — UEID tri-key, hysteresis FSM, ForkAdapter protocol, hybrid meta-vector, etc.

**Modo:** INDEX + cross-link. Não duplica conteúdo existente; preserva single-source-of-truth.

**Stack conceitual (8 camadas):**

```
Layer 0 — Index (este doc)
   ↓
Layer 1 — Topology & canonical narrative (master-branch carro-chefe)
   ↓
Layer 2 — Architecture canvases (mesh, contracts, agents, sync, cybernetic loop)
   ↓
Layer 3 — Patterns catalog (10 padrões load-bearing)
   ↓
Layer 4 — Forks catalog (3 forks-prontas + status-enum mapping)
   ↓
Layer 5 — Tokens & components (canônico deep-agent + SUPERSEDED PAV-era)
   ↓
Layer 6 — User journeys & screens (cross-link para ux/vault)
   ↓
Layer 7 — Validation & heuristics (Nielsen + ADR-007 data-first)
```

## §1 — Convenções

- **Idioma:** PT-BR prose + EN technical terms (UEID, FSM, IKIGAi, PAV, deep-agent, fork, regime, MCP, KPI, SCR, FLOW)
- **Naming:** `NN-categoria-nome-kebab.md` (zero-padded 2-digit para ≤99)
- **Template:** 5 seções numeradas (§1-§5) — intuição / enunciado / justificativa / refs cruzadas / fontes
- **Math notation:** H(t), Q_HE, UEID preservados verbatim
- **Code references:** paths absolutos preservados sem tradução
- **Padrão de fonte:** paths absolutos do repo (`src/...`, `vault/...`, `vibe-ops/...`)
- **SUPERSEDED trailers:** documentam defasagem sem deletar conteúdo (append-only invariant)

## §2 — Camadas (placeholder — atualizado no Batch 8)

| Layer | Faixa  | Categoria          | # docs | Status |
|:-----:|:------:|:-------------------|:------:|:-------|
| 0     | 00     | Top-level index    | 1      | ✅ este doc |
| 1     | 01-03  | Topology & narrative | 3    | ⏳ batch 1 |
| 2     | 04-08  | Architecture canvases | 5   | ⏳ batch 2 |
| 3     | 10-19  | Patterns catalog   | 10     | ⏳ batches 3-4 |
| 4     | 20-23  | Forks catalog      | 4      | ⏳ batch 5 |
| 5     | 30-34  | Tokens & components | 5     | ⏳ batch 6 |
| 6     | 40-45  | User journeys & screens | 6  | ⏳ batch 7 |
| 7     | 50-53  | Validation & heuristics | 4   | ⏳ batch 8 |

## §3 — Mapa de dependências (preliminar)

```
Master-branch (01) + dual-layer (02) + roadmap (03)
   ↓
   ├──▶ Architecture canvases (04-08)
   │       ├──▶ Mesh, Contracts, Agents, Sync, Cybernetic loop
   │       └──▶ Cross-link para src/contracts/, src/mesh/, src/ikigai/
   │
   ├──▶ Patterns catalog (10-19)
   │       ├──▶ UEID, Frozen Pydantic, Append-only, ForkAdapter (10-13)
   │       └──▶ Idempotency, Hysteresis, Meta-vector, Reliability, Prompt, Scaffold (14-19)
   │
   ├──▶ Forks catalog (20-23)
   │       ├──▶ INDEX tuiboard/taskdog/solverforge-calendar
   │       └──▶ NEW status-enum mapping (gap #5)
   │
   ├──▶ Tokens & components (30-34)
   │       ├──▶ Canonical tokens deep-agent era (gap #3)
   │       ├──▶ SUPERSEDED PAV-era trailer
   │       ├──▶ UEID visual (gap #4)
   │       └──▶ Naming conventions (gap #7)
   │
   └──▶ User journeys & validation (40-53)
           ├──▶ Cross-link para ux/, vault/ikigai/meta/
           └──▶ Nielsen heuristics + ADR-007 constraint
```

## §4 — Como usar este docset

- **"Como o sistema funciona arquiteturalmente?"** → comece por Layer 1 (master-branch), depois Layer 2 (canvases)
- **"Como implementar fork X?"** → vá para Layer 4 (forks catalog) + Layer 3 patterns aplicáveis
- **"Quais tokens visuais usar?"** → Layer 5 (canônico deep-agent) com cross-link para PAV-era
- **"Como auditar uma feature nova?"** → Layer 7 (validation) + ADR-007 data-first gate
- **"Que padrão usar para Y?"** → Layer 3 (patterns catalog)

## §5 — Fontes principais

- `docs/auto-performance-os/` (template 5-section + 27 docs de matemática — precedent)
- `src/operational/docs/design-system/DESIGN-SYSTEM.md` (676 LOC, PAV-era, SUPERSEDED)
- `src/operational/docs/ux/` (40+ docs: componentes, fluxos, telas, glossário)
- `src/operational/docs/architecture/` (13 docs arquiteturais)
- `docs/diagnostics/2026-08-28-phase2-interface-re/` (3 fork REs + síntese mesh)
- `vault/ikigai/meta/tui-screen-survey.md` (jornada do usuário canônica)
- `code-docs/adr/ADR-007-data-first-methodology.md` (constraint de 5+ logs)
- `docs/diagnostics/2026-08-28-doc-migration/00-INDEX.md` (status de docs)

---

> **Próxima atualização:** Batch 8 — tabela completa das 38 docs, mapa de dependências refinado, exemplos de uso expandidos.
