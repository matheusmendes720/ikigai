---
ueid: ikigai:project:onda-2026-07-byd-deep-dive:c112f3a0:8825d88a
entity_type: project
slug: onda-2026-07-byd-deep-dive
parent_ueid: ikigai:objective:q3-2026-primeira-vaga:cbf000ba:c040f222
related_ueids: []
title: "Onda Jul-2026 — BYD deep-dive (1 empresa, full cycle, 2026-07-09 → 2026-08-08)"
description: null
status: DRAFT
ikigai_vectors: [market, skill, course]
vector_weights_snapshot: {passion: 0.15, skill: 0.30, market: 0.35, revenue: 0.05, course: 0.15}
phase_at_creation: fundacao
regime_at_creation: push
horizon_days: 30
primary_score: null
is_placeholder: false
placeholder_owner: null
custom:
  _horizon_rationale: "Mês calendário (jul/2026) — 30d ProjectEntity bucket matches"
  _scope_pivot_from: "Q3-1 original previa 30 empresas + 2-3 verticals; pivotado em 2026-07-09 para 1 empresa focus + full deep-dive cycle (ver DEC-08 options-exploration-log)"
  _success_criteria:
    - "D1 entregue: market intelligence BYD (greenfield + timing)"
    - "D2 entregue: econometric vulnerability analysis (portfolio piece; pode virar case study público)"
    - "D3 entregue: cold outreach assets (LinkedIn + email PT-BR; LinkedIn EN secondary)"
    - "D4 entregue: process tracker + ≥ 1 resposta recebida (mesmo que 'no-fit')"
    - "Q_HE ≥ 0.65 sustentado (sem burnout)"
  _kill_conditions:
    - "Se D1 mostra BYD não vai abrir vagas em jul/ago → pivotar para próxima empresa-alvo (denúncialist em D1)"
    - "Se regime entrar em RECOVER antes D3 → pausar cold outreach, retomar em MANTAIN"
    - "Se 'pipeline de dados em ampla concorrência' virar distração > 20% esforço → recategorizar como 'learning' fora do onda"
  _deliverable_count: 4
  _pace: "1 deliverable a cada 5-7 wd; overlap permitido W2-W3"
source_md_path: null
tags: [persona/matheus, horizon/30d, onda/2026-07, vertical/quant-finance, workstream/w1-w4, empresa/byd, mode/deep-dive-single]
last_reviewed_at: 2026-07-09T00:00:00Z
tech_stack: [python, polars, statsmodels, scikit-learn, vectorbt, plotly, jupyter, obsidian, taskwarrior]
---

# ONDA Jul-2026 — BYD deep-dive (1 empresa, full cycle)

> **Janela:** 2026-07-09 → 2026-08-08 (≈ 30 d calendário ≈ 22 wd úteis).
> **Regime:** PUSH (budget hardwork 4.0 h/dia, sleep target 7.5 h, Q_HE target 0.85).
> **Foco único:** BYD Brasil + économie + financial markets diagnosis → portfolio + cold outreach + 1 processo.

## Por que este scope (rationale registrado)

A onda original Q3-1 previa 30 empresas-alvo + 2-3 verticals (per
DEC-08 `options-exploration-log.md`). matheus pivotou em 2026-07-09 para
**1 empresa focus (BYD) com deep-dive cycle completo**, com os motivos:

1. **BYD abre vagas no curto prazo** (informação externa; ~jul/ago 2026);
   janela crítica = janela de execução.
2. **Validar processo replicável** em um único alvo antes de escalar
   para 5-10 empresas (Q3-2+).
3. **Aprofundar qualidade** (econometria + markets + vulnerability
   diagnosis) ao invés de dispersar em 30 contatos rasos.
4. **Construir 1 portfolio piece forte** (case study) que serve de âncora
   para próximas empresas, ao invés de N peças superficiais.
5. **Dedicar 1 flanks fully** é compatível com método "validar hipótese
   em um slice antes de generalizar" (lean).

Não-Objetivos (fora desta onda):

- Multi-vertical comeração fria (Q3-2 escopo).
- 2-3 portfolios simultâneos (re-decide em Q3-2 retro).
- Take-home submission público (Q-005 deferred, matheus locka depois).
- LinkedIn EN-only cold campaigns (Q-006 Phase 2; esta onda = PT-primary).

## Hipótese central (testável até 2026-08-08)

> *"BYD Brasil está contratando em jul/ago 2026 para funções de
> financial analyst / data analyst / market intelligence com stack
> Python/SQL/Polars, e meu perfil (Python/Polars sólido + quant bias)
> tem fit ≥ 60% para ≥ 1 das vagas abertas."*

Variáveis a medir:

- **Timing**: BYD publicou ≥ 3 vagas BR-conformity entre 2026-07-09 → 2026-08-08?
- **Stack fit**: ≥ 1 vaga menciona Python/SQL/Polars/quant?
- **Response rate**: ≥ 1 resposta a 5 mensagens enviadas (LinkedIn + email)?
- **Portfolio differentiation**: econometric vulnerability analysis é
  publicável como case study (decide post-D2)?

Se 2 das 4 = "sim" → hipótese validada, escopo replica para Q3-2.
Se 0-1 das 4 = "sim" → pivota vertical ou método em Q3-2 retro.

## 4 Deliverables (children)

| ID | Slug | horizon | W | Status inicial | artifact_type |
|----|------|---------|---|----------------|---------------|
| **D1** | byd-market-research | 3 d | W1 | draft | document |
| **D2** | byd-econometric-vulnerability-analysis | 5 d | W2-W3 | draft | code (jupyter) + data |
| **D3** | byd-cold-outreach-assets | 2 d | W3 | draft | document |
| **D4** | byd-process-tracker | 7 d | W4+ | draft | data (sqlite/obsidian) |

## Workstreams paralelos (W1-W4)

- **W1 (D1)**: BYD market intelligence — greenfield detection, vagas abertas,
  stack requirements, hiring manager map (1 semana, sequential blocking).
- **W2 (D2)**: Econometric vulnerability analysis — Python/Polars/Statsmodels
  notebook analisa vulnerabilidades macro BYD (câmbio, supply chain,
  concorrência). Portfolio piece (1.5 semanas).
- **W3 (D3)**: Cold outreach assets — LinkedIn PT-BR templates + email
  curto; baseada em D1 + D2 findings. Pode começar paralelo a D2.
- **W4 (D4)**: Process tracker — sqlite para tracking de: outreach →
  response → phone screen → take-home → onsite → offer. Rolling forward
  após D3.

Sequenciamento:

```
W1 ─[D1]→ W2 ─[D2─┬─→ W3 ─[D3]→ W4 ─[D4 continues]
                  └─→ D2 done ok → W3 trigger
```

Critical path: D1 → D2 → D3 → D4. Buffer de 5 d entre D3-D4 permite
ajuste based on response rate antes de escalar.

## Cross-cluster UEIDs (forward-compat)

| Cluster | UEID a criar (quando aplicável) | Lock condition |
|---------|---------------------------------|----------------|
| `tw:` | task: byd-action-* | Após D1 + D2 done |
| `obsidian:` | note: byd-research-* | Após cada W close |
| `proj-system:` | project card: BYD-2026-07 | GAP-06 (proj-system live) |

## Métricas & View renderers

Esta onda é o **first real test** dos IKIGAI views (breakdown-files,
gantt, calendar, kanban) — schema já suporta via parent_ueid +
horizon_days + status enum; renderers pendentes (P2 priority).

Sinais a observar durante execução:

- **Q_HE trend** (per `vibe-ops/PolicyEngine`): se cai < 0.65 por 3+ dias,
  escalar para REGIME_REDUCE; se cai < 0.45, RECOVER.
- **Deliverable burndown**: 1 deliverable a cada 5-7 wd; burn rate
  mostra se escopo é realista para 30d.
- **External response signal**: ≥ 1 resposta em D4 = hipótese
  validada; 0 respostas em D4 = hipótese a re-evaluate.

## Out of scope (explícito)

- **Multi-vertical cold outreach** (deferred Q3-2+, DEC-08).
- **Other empresas-alvo** (decision após D1 + D4 read).
- **LinkedIn EN-only campaigns** (Q-006 Phase 2; esta onda = PT-primary).
- **Take-home submission pública** (Q-005 deferred, matheus locka pós-D2).
- **Pipeline de dados em ampla concorrência** (learning track fora desta
  onda — tracked separadamente em `prodapp/learn/tracks/data-pipeline/`).
