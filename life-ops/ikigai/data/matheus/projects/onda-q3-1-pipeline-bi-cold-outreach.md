---
ueid: ikigai:project:onda-q3-1-pipeline-bi-cold-outreach:82e0b0aa:86d28f99
entity_type: project
slug: onda-q3-1-pipeline-bi-cold-outreach
parent_ueid: ikigai:objective:q3-2026-primeira-vaga:cbf000ba:c040f222
related_ueids: []
title: "Onda Q3-1 — Pipeline BI + cold outreach (15 wd, 2026-07-06 → 2026-07-24)"
description: null
status: ARCHIVED
ikigai_vectors: [market, skill]
vector_weights_snapshot: {passion: 0.05, skill: 0.35, market: 0.45, revenue: 0.10, course: 0.05}
phase_at_creation: fundacao
regime_at_creation: push
horizon_days: 30
primary_score: null
is_placeholder: false
placeholder_owner: null
created_at: 2026-07-06T00:00:00Z
updated_at: 2026-09-15T00:00:00Z
custom:
  _status_resolution: "ARCHIVED — deadline 2026-08-05 elapsed. All 7 UNDs remained in DRAFT status; no lead scraping, filtering, cold outreach, or pipeline work was executed. Project was superseded by onda-2026-07-byd-deep-dive which executed successfully with 3/4 deliverables completed. BYD CV Campaign work (2026-08-26 updates) was parallel workstream, not ONDA Q3-1 execution."
  _archived_reason: "scope_pivot — BYD deep-dive became primary path per DEC-08; Q3-1 original 30-company scope abandoned"
  _horizon_rationale: "15 wd ONDA; rounded to 30d ProjectEntity bucket (next literal above 15)"
  _und_count: 7
  _pace: "~2 UNDs/semana"
  _updates:
    - date: 2026-09-15
      event: "Project archived — scope pivot to BYD deep-dive"
      detail: "Original ONDA Q3-1 scope (30 companies + pipeline) superseded by BYD deep-dive. All UNDs remained in DRAFT. Archived per project review."
      next_action: "none"
    - date: 2026-08-26
      event: "BYD CV Campaign executed (parallel workstream — ONDA internal)"
      detail: "4 CV variants patched (v8 fullstack, v9 bigdata, v10 ops, v11 ITAM) — Group 5 patches applied; B3/B5 auto-fixes applied; H3 cap identified (band D 49pt); B1 graduation years is single unblock to band A (87-91pt)"
      artifact: "job_hunter/base/cv-versions/BYD-CV-Campaign-Report.md"
      next_action: "candidate supplies B1 graduation years → all 4 CVs cross 65pt threshold"
    - date: 2026-08-25
      event: "soft-rule audit + scoring pass completed"
      detail: "42 violations catalogued; H3 dominant cap confirmed; projected post-B1 scores A-band (85-89pt)"
      artifact: "job_hunter/base/cv-versions/post-task29-rescore.md"
source_md_path: null
tags: [persona/matheus, horizon/15wd, onda/q3-1, workstream/w1]
last_reviewed_at: 2026-09-15T00:00:00Z
tech_stack: [python, polars, sqlite, obsidian, taskwarrior]
---

# ONDA Q3-1 — Pipeline BI + cold outreach

> **Janela:** 2026-07-06 → 2026-07-24 (15 wd úteis).
> **horizon_days no schema:** 30 (ProjectEntity literal set mínimo — 15 wd foi arredondado
>   para o bucket de 30d conforme R-decision; rationale em `custom._horizon_rationale`).
> **Status:** draft (R3: bootstrap, não "active").
> **Regime:** PUSH (4.0h hardwork/dia).
> **ARCHIVED** — 2026-09-15 per project review. Superseded by BYD deep-dive.

Esta ONDA é o kick-off do KR1 do TRIMESTRE Q3-2026. Se em 15 wd não tivermos ao menos
10 empresas-alvo + 7 mensagens enviadas + 2 respostas, o KR1 inteiro está em risco.

## UNDs (Unidades de Software)

| # | UND | Estimativa | Status |
|---|-----|------------|--------|
| 1 | UND-01 — Leads scrape (RemoteOK + LinkedIn) | 8h | draft |
| 2 | UND-02 — Filtro stack (Python/Polars + remote-first) | 6h | draft |
| 3 | UND-03 — Cold outreach template v1 | 4h | draft |
| 4 | UND-04 — First 10 mensagens enviadas | 12h | draft |
| 5 | UND-05 — Demo storyboard (12min, W2 prep) | 16h | draft |
| 6 | UND-06 — GitHub repo skeleton + README | 8h | draft |
| 7 | UND-07 — Q_HE retro + ajuste semana 3 | 6h | draft |

**Total:** 60h ÷ 15 wd = 4.0h/dia — bate com regime PUSH.

## Sequenciamento

- **Semana 1 (jul 06-12):** UND-01 + UND-02 + UND-03 (fundação de dados + templates).
- **Semana 2 (jul 13-19):** UND-04 + UND-05 (execução + preparação W2).
- **Semana 3 (jul 20-24):** UND-06 + UND-07 (repositório público + retro).

## Vector weights

Market domina porque o output primário é pipeline (não skill, não revenue direto):

- Passion: 0.05 (só não burnout)
- Skill: 0.35 (UND-01-03 são skill de scraping + filter)
- Market: 0.45 (UND-04 é cold outreach puro)
- Revenue: 0.10 (sem oferta ainda)
- Course: 0.05 (estudo mínimo necessário)

## Regime + transitions

Mesma lógica do TRIMESTRE, mas gatilhos são diários:

- Q_HE daily < 0.45 → pular UND-04 (cold outreach requer cognição fresh).
- Q_HE daily < 0.25 → cancelar UNDs do dia, foco em S1+S2.

## Métricas de saída (gates para ONDA Q3-2)

- ≥ 10 empresas-alvo no pipeline (lead list).
- ≥ 7 mensagens efetivamente enviadas.
- ≥ 2 respostas (positivas ou neutras).
- 1 demo storyboard pronto.
- 1 repo GitHub público inicializado.

Se algum gate falhar → ONDA Q3-2 começa em modo de recuperação (REDUCE).

## Links internos

- Parent: `objectives/q3-2026-primeira-vaga.md` (TRIMESTRE).
