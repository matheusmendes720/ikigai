# 00 — Índice: Design System (Híbrido — UI Tokens + Arquitetura)

> **Categoria:** INDEX navegável (Layer 0 — entrypoint)
> **Público:** Eu mesmo + agentes futuros
> **Localização:** `docs/design-system/`
> **Total:** 40 documentos em 9 camadas (38/38 ✅ antes do Batch 8; +4 novos em Batch 8 → 40/40 ✅)

---

## §0 — Visão panorâmica (post-pivot 2026-08-26)

Este docset é o **índice navegável** do design system híbrido do IKIGAi na era **deep-agent canonical** (PAV desativado). Cobre duas dimensões complementares:

1. **UI Tokens** — paleta semântica, tipografia, espaçamento, glifos, componentes visuais (cross-link para `src/operational/docs/ux/` e estende para era deep-agent)
2. **Padrões arquiteturais** — UEID tri-key, hysteresis FSM, ForkAdapter protocol, hybrid meta-vector, etc.

**Modo:** INDEX + cross-link. Não duplica conteúdo existente; preserva single-source-of-truth.

**Stack conceitual (9 camadas):**

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
Layer 7 — Validation & heuristics (Nielsen + checklist + risks + ADR-007 gate)
   ↓
Layer 8 — Critical analysis + unified model (análise segunda ordem + modelo auto-feedback estocástico)
```

---

## §1 — Convenções

- **Idioma:** PT-BR prose + EN technical terms (UEID, FSM, IKIGAi, PAV, deep-agent, fork, regime, MCP, KPI, SCR, FLOW)
- **Naming:** `NN-categoria-nome-kebab.md` (zero-padded 2-digit para ≤99)
- **Template:** 5 seções numeradas (§1-§5) — intuição / enunciado / justificativa / refs cruzadas / fontes (patterns) **OU** §1 Resumo / §2 Inventário / §3 Conteúdo principal / §4 Cross-references / §5 Fontes (validation/journeys/tokens)
- **Math notation:** H(t), Q_HE, UEID preservados verbatim
- **Code references:** paths absolutos preservados sem tradução
- **Padrão de fonte:** paths absolutos do repo (`src/...`, `vault/...`, `vibe-ops/...`)
- **SUPERSEDED trailers:** documentam defasagem sem deletar conteúdo (append-only invariant)

---

## §2 — Inventário completo (40 docs em 9 camadas)

| Layer | Faixa  | Categoria                       | # docs | Docs                                                                                                       | Status         |
|:-----:|:------:|:--------------------------------|:------:|:-----------------------------------------------------------------------------------------------------------|:---------------|
| 0     | 00     | Top-level index                 | 1      | 00-INDEX                                                                                                   | ✅ este doc    |
| 1     | 01-03  | Topology & narrative            | 3      | 01-master-branch-carro-chefe · 02-interfaces-dual-layer · 03-design-system-roadmap                        | ✅ Batch 1     |
| 2     | 04-08  | Architecture canvases           | 5      | 04-canvas-mesh · 05-canvas-contracts · 06-canvas-agents · 07-canvas-sync · 08-canvas-cybernetic-loop        | ✅ Batch 2     |
| 3     | 10-19  | Patterns catalog                | 10     | 10-pattern-ueid-tri-key · 11-pattern-frozen-pydantic-strict · 12-pattern-append-only-queue · 13-pattern-fork-adapter-protocol · 14-pattern-idempotency-upstream-id · 15-pattern-hysteresis-fsm · 16-pattern-hybrid-meta-vector · 17-pattern-reliability-decorators · 18-pattern-system-prompt-layers · 19-pattern-5-stage-scaffold | ✅ Batches 3-4 |
| 4     | 20-23  | Forks catalog                   | 4      | 20-fork-tuiboard · 21-fork-taskdog · 22-fork-solverforge-calendar · 23-fork-status-enum-mapping             | ✅ Batch 5     |
| 5     | 30-34  | Tokens & components             | 5      | 30-tokens-deep-agent-era · 31-ueid-visual-representation · 32-component-naming-conventions · 33-status-matrix-unified · 34-superseded-pav-era-tokens | ✅ Batch 6     |
| 6     | 40-45  | User journeys & screens         | 6      | 40-index-user-journeys · 41-journey-morning-startup · 42-journey-task-create · 43-journey-policy-decision · 44-journey-weekly-review · 45-journey-dataset-switch | ✅ Batch 7     |
| 7     | 50-53  | Validation & heuristics         | 4      | 50-nielsen-heuristics-coverage · 51-usability-checklist · 52-known-risks-mitigations · 53-adr-007-data-first-gate | ✅ Batch 8     |
| 8     | 09-10  | Critical analysis + unified model | 2    | 09-analise-critica-segunda-ordem-arquitetura · 10-modelo-unificado-auto-feedback-estocastico              | ✅ Batch-A     |

**Total:** 1+3+5+10+4+5+6+4+2 = **40 docs ✅**

**Notas sobre numeração ambígua:**
- Doc `docs/design-system/10-pattern-ueid-tri-key.md` (Layer 3) e doc `10-modelo-unificado-auto-feedback-estocastico.md` (Layer 8) compartilham prefixo `10-` mas têm propósitos distintos — patterns catalog vs critical analysis + unified model. A faixa numérica é **independente por camada**; cross-references usam path completo (`docs/design-system/10-pattern-ueid-tri-key.md`) para evitar ambiguidade.
- Doc `09-analise-critica-segunda-ordem-arquitetura.md` (Layer 8) precede os patterns catalog por **decisão editorial** — análise crítica foi escrita antes dos patterns, mas é consumida depois (cross-ref em doc 18 §3).

---

## §3 — Mapa de dependências

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
   │       ├──▶ INDEX tuiboard/taskdog/solverforge-calendar (20-22)
   │       └──▶ NEW status-enum mapping cross-fork (23)
   │
   ├──▶ Tokens & components (30-34)
   │       ├──▶ Canonical tokens deep-agent era (30)
   │       ├──▶ UEID visual representation (31)
   │       ├──▶ Component naming SCR-NNN (32)
   │       ├──▶ Status matrix unificada 6×4 (33)
   │       └──▶ SUPERSEDED PAV-era trailer (34)
   │
   ├──▶ User journeys (40-45)
   │       ├──▶ INDEX navegável (40)
   │       ├──▶ Morning startup, Task create, Policy decision (41-43)
   │       └──▶ Weekly review, Dataset switch (44-45)
   │
   ├──▶ Validation layer (50-53)
   │       ├──▶ Nielsen 10 heurísticas mapeadas (50)
   │       ├──▶ Pre-launch checklist 30 itens (51)
   │       ├──▶ 12 riscos R1-R12 + mitigações (52)
   │       └──▶ ADR-007 data-first gate (53)
   │
   └──▶ Critical analysis + model (09-10)
           └──▶ Análise 2ª ordem + modelo auto-feedback estocástico
```

**Dependências críticas (não-violáveis):**

| Doc load-bearing | Consumido por |
|:-----------------|:--------------|
| 10-pattern-ueid-tri-key | 11, 13, 14, 17, 23, 31, 50, 52, 53 |
| 13-pattern-fork-adapter-protocol | 20, 21, 22, 50, 52 |
| 14-pattern-idempotency-upstream-id | 20, 21, 22, 50, 51, 52 |
| 15-pattern-hysteresis-fsm | 08, 43, 50, 51 |
| 17-pattern-reliability-decorators | 18, 50, 51, 52 |
| 30-tokens-deep-agent-era | 31, 32, 33, 50, 51 |
| 33-status-matrix-unified | 23, 50, 51, 52 |

---

## §4 — Como usar este docset

- **"Como o sistema funciona arquiteturalmente?"** → comece por Layer 1 (master-branch), depois Layer 2 (canvases)
- **"Como implementar fork X?"** → vá para Layer 4 (forks catalog) + Layer 3 patterns aplicáveis
- **"Quais tokens visuais usar?"** → Layer 5 (canônico deep-agent) com cross-link para PAV-era (doc 34)
- **"Como auditar uma feature nova?"** → Layer 7 (validation) + ADR-007 data-first gate (doc 53)
- **"Que padrão usar para Y?"** → Layer 3 (patterns catalog)
- **"Qual jornada canônica segue o user?"** → Layer 6 (journeys) — start com doc 40 (index)
- **"Que heurísticas Nielsen devo aplicar?"** → Layer 7 doc 50 — depois checklist (51) + risks (52)
- **"Posso rodar IKIGAi agent agora?"** → Layer 7 doc 53 — verifica counter SONHO ≥5/5

---

## §5 — Fontes principais

- `docs/auto-performance-os/` (template 5-section + 27 docs de matemática — precedent)
- `src/operational/docs/design-system/DESIGN-SYSTEM.md` (676 LOC, PAV-era, SUPERSEDED via trailer 2026-08-28 — ver Task C)
- `src/operational/docs/ux/` (40+ docs: componentes, fluxos, telas, glossário)
- `src/operational/docs/ux/08-validacao/` (3 docs: heurísticas, checklist, riscos — anchor para Layer 7)
- `src/operational/docs/architecture/` (13 docs arquiteturais)
- `docs/diagnostics/2026-08-28-phase2-interface-re/` (3 fork REs + síntese mesh — anchor para Layer 4 + Layer 7 doc 52)
- `vault/ikigai/meta/tui-screen-survey.md` (jornada do usuário canônica)
- `code-docs/adr/ADR-007-data-first-methodology.md` (constraint de 5+ SONHO logs — anchor para Layer 7 doc 53)
- `docs/diagnostics/2026-08-28-doc-migration/00-INDEX.md` (status de docs PAV-era)
- `[[data-first-methodology]]` (memory canônica — gate counter status)
- `[[docs-superseded-trailer-2026-08-28]]` (memory canônica — trailer pattern)
- `[[master-branch-carro-chefe-2026-08-28]]` (memory canônica — Deep Agent como mediador)

---

## §6 — Status da docset (atualizado Batch 8)

**Conclusão:** **40/40 docs ✅ (9/9 batches committed)** — Layers 0-8 todas preenchidas.

| Layer | Faixa | Status | Última atualização |
|:------|:------|:-------|:-------------------|
| 0     | 00    | ✅ 1/1 | Batch 8 (este update) |
| 1     | 01-03 | ✅ 3/3 | Batch 1 (commit a3621b1) |
| 2     | 04-08 | ✅ 5/5 | Batch 2 (commit b2a0136) |
| 3     | 10-19 | ✅ 10/10 | Batches 3-4 |
| 4     | 20-23 | ✅ 4/4 | Batch 5 |
| 5     | 30-34 | ✅ 5/5 | Batch 6 |
| 6     | 40-45 | ✅ 6/6 | Batch 7 |
| 7     | 50-53 | ✅ 4/4 | **Batch 8 (atual)** |
| 8     | 09-10 | ✅ 2/2 | Batch-análise (commit 0e002f0) |

**Batches fechados:**

- **Batch 1** — Layer 1 (topology & narrative) — commit `a3621b1`
- **Batch 2** — Layer 2 (architecture canvases) — commit `b2a0136`
- **Batches 3-4** — Layer 3 (patterns catalog)
- **Batch 5** — Layer 4 (forks catalog)
- **Batch 6** — Layer 5 (tokens & components)
- **Batch 7** — Layer 6 (user journeys)
- **Batch-análise** — Layer 8 (critical analysis + model) — commit `0e002f0`
- **Batch 8** — Layer 7 (validation & heuristics) ← **commit atual**

**Cobertura de gaps (preenchidos):**

| Gap # | Descrição | Doc que preenche | Status |
|:------|:----------|:-----------------|:-------|
| #1    | Master-branch carro-chefe canônico | doc 01 | ✅ |
| #2    | Dual-layer architecture (forks vs CLI) | doc 02 | ✅ |
| #3    | Canonical tokens deep-agent era | doc 30 | ✅ |
| #4    | UEID visual representation | doc 31 | ✅ |
| #5    | Status matrix unificada + fork-status mapping | doc 33 + doc 23 | ✅ |
| #6    | Architecture canvases (5) | docs 04-08 | ✅ |
| #7    | Component naming SCR-NNN | doc 32 | ✅ |
| #8    | User journeys canônicas (5) | docs 41-45 | ✅ |
| #9    | Validation heuristics + checklist + risks + gate | docs 50-53 | ✅ |

**Open work (pós-Batch 8):**

- Aplicar trailers SUPERSEDED em outros docs PAV-era (campanha contínua — doc 34 já aplicado; `src/operational/docs/design-system/DESIGN-SYSTEM.md` recebe trailer Task C)
- Phase 3 mesh readiness (R1-R5 do doc 52) — depende de fork-pronta + agent coordination
- 4 SONHO logs adicionais para abrir ADR-007 gate (counter 1/5 → 5/5)

**Acesso rápido:**

- **Quem entra no projeto:** §0 → §4 → §2 (inventário)
- **Quem implementa fork:** Layer 4 (20-23) + Layer 3 patterns (10-19) + Layer 5 tokens (30-34)
- **Quem audita fork:** Layer 7 (50-53)
- **Quem quer entender o "porquê":** Layer 8 (09-10) + master-branch (01) + dual-layer (02)
