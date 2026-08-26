---
ueid: ikigai:project:onda-2026-07-salvador-data-pipeline:54ce7879:ab4020c7
entity_type: project
slug: onda-2026-07-salvador-data-pipeline
parent_ueid: ikigai:objective:q3-2026-primeira-vaga:cbf000ba:c040f222
related_ueids: []
title: "Onda 2026-07 Salvador-Data Pipeline — Tier 1 FALLBACK (parallel to BYD ONDA)"
description: null
status: DRAFT
ikigai_vectors: [market, skill]
vector_weights_snapshot: {passion: 0.05, skill: 0.30, market: 0.50, revenue: 0.10, course: 0.05}
phase_at_creation: fundacao
regime_at_creation: push
horizon_days: 30
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [persona/matheus, horizon/30d, onda/q3-2, workstream/w1, fallback/salvador, mode/data-pipeline]
last_reviewed_at: 2026-07-09T00:00:00Z
tech_stack: [python, polars, duckdb, plotly, sqlite, obsidian, taskwarrior]
repo_url: null
target_revenue_brl: null
actual_revenue_brl: 0.0
created_at: 2026-07-09T00:00:00Z
updated_at: 2026-07-09T00:00:00Z
custom:
  _scope_pivot_from: "BYD ONDA primary; esta é FALLBACK parallel"
  _activation_trigger: "BYD anchor não converteu em 5 wd (≤ 1 response de Yueying Zhang) → escalate Salvador/remote como primary path"
  _horizon_rationale: "30 wd parallelo BYD ONDA; mesmo horizon_days para coordenar cadência"
  _success_criteria:
    - "5+ Salvador/remote applications enviadas em Wd 1-2"
    - "≥ 1 response de empresa Salvador (BairesDev/FullStack/Alignerr)"
    - "Q_HE ≥ 0.65 sustentado (mesmo critério BYD)"
  _deliverables_parallel_to_BYD:
    - "D1: market-research-salvador (já 80% covered em byd-greenfield-map.md tabela expandida)"
    - "D2: portfolio-data-pipeline (Polars/DuckDB focado em Salvador use case — portabilidade BYD)"
    - "D3: outreach-salvador-tier1 (já 100% em byd-outreach-tier1.md)"
    - "D4: tracker compartilhado com BYD (byd-tracker.db)"
  _ab_test_design:
    - "BYD anchor: 1 outreach (Yueying) → mede conversion high-competition"
    - "Salvador tier 1: 5 outreach → mede conversion low-competition Salvador"
    - "Comparar response rate BYD vs Salvador após 5 wd"
  _deferred_to_BYD_priority:
    - "Esta ONDA NÃO substitui BYD — apenas adiciona 5 fallback tracks"
    - "BYD continua sendo anchor #1 absoluto"
    - "Salvador tier 1 ativa em paralelo (volume diversification)"
    - "Se BYD converte (≥ 1 entrevista onsite), Salvador tier 1 vira nice-to-have"
    - "Se BYD não converte em 5 wd, Salvador tier 1 vira primary path"
  _yagni_rationale: "Não duplicar D2 portfolio — usar mesmo notebook BYD, adaptar cover letter para Salvador use cases (e.g. BairesDev data analyst = mesma análise cambial, pitch angle remote-first)"
---

# Onda 2026-07 Salvador-Data Pipeline — Tier 1 FALLBACK

> **Status (2026-07-09):** DRAFT — não ativa como primary ONDA. Funciona
> como **paralelo fallback** ao BYD ONDA. BYD Yueying Zhang permanece
> **#1 absoluto**; Salvador/remote é **TIER 1 FALLBACK** (5 vagas
> Python/data Salvador + remote-friendly companies).

## Contexto estratégico

**Decisão lean registrada em 2026-07-09 Wd 1 deep refresh:** após
descobrir **14 vagas Python/data ativas em Salvador-BA** (sendo 12
fully-remote), o escopo do SONHO Q3-2026 expandiu. Não é mais
"1 empresa BYD focus" — é **"BYD anchor + Salvador/remote
portfolio diversification"**.

Esta ONDA existe para **operacionalizar** o Tier 1 fallback sem
duplicar D2 portfolio. Estratégia: **mesmo D2 notebook** (BYD
análise cambial) + **5 cover letters adaptados** para Salvador
context (remote-first DNA, Salvador location, Python/data stack).

## Activation trigger

- **DEFAULT**: status = draft, paralelo a BYD ONDA, sem ativação
  explícita necessária (cadência automática).
- **ESCALATION**: se BYD anchor (Yueying Zhang) não responder em
  **5 wd** (≤ 0 responses), Salvador tier 1 vira **primary path**
  e BYD vira **secondary**.

## Deliverables (parallel to BYD ONDA, reuse >80%)

### D1 — market research Salvador (já 80% covered)

Já populado em `byd-d1-outputs/byd-greenfield-map.md` tabela
expandida. Top 5 Salvador/remote jobs:

1. FullStack Data Engineer Remoto (90 fit)
2. BairesDev Analista Dados Remoto (85 fit)
3. Jobbol Engenheiro Dados Pleno Salvador (85 fit)
4. INDI Talent Data Analyst Remote (80 fit)
5. Alignerr Engenheiro Software AI training (80 fit)

### D2 — portfolio data pipeline (reuse BYD notebook)

**Estratégia:** mesmo notebook `byd-econometric-vulnerability.ipynb`
(4 seções: cambio/supply/regulatório/concorrência) com **2 customizações**
para Salvador/remote pitch:

1. **Section 1 cambio**: adicionar insight "remote work = BRL/USD
   exposure on cross-border contractor payments" (BairesDev usa
   isso para pricing).
2. **Section 4 concorrência**: adicionar "Brazilian data market
   consolidation" (BairesDev acquiring smaller shops).

**Não criar notebook separado** — YAGNI. Reuse + adapt cover letter.

### D3 — outreach Salvador Tier 1 (já 100% covered)

Já populado em `byd-d3-outputs/byd-outreach-tier1.md`. 5 templates
prontos (A: FullStack, B: BairesDev, C: Jobbol, D: INDI, E: Alignerr).

### D4 — tracker compartilhado (já 100% covered)

Schema em `byd-d4-outputs/byd-tracker-schema.sql` suporta BYD +
Salvador simultaneamente. Único `byd-tracker.db` para ambos.

## Cadência proposta (parallel, Wd 1-4)

| Wd | BYD actions | Salvador/remote actions |
|----|-------------|-------------------------|
| Wd 1 | T0 outreach Yueying + manager survey BYD Campinas | Easy Apply: FullStack + BairesDev + Jobbol (3 applications) |
| Wd 2 | T1 follow-up Yueying + apply BYD Especialista Dados Campinas | Easy Apply: INDI + Alignerr (2 applications) |
| Wd 3 | T2 follow-up + D2 notebook 50% complete | Easy Apply: EY Salvador (1 application) |
| Wd 4 | D2 notebook 100% + send 1-pager as follow-up | Easy Apply: AgileEngine + Alignerr follow-up |

**Total touch:** 5 BYD + 6 Salvador/remote = 11 applications em 4 wd.

## A/B test plan (Wd 5 retro)

- **Variant BYD anchor**: high-competition (200+ applicants) →
  mede conversion rate de "personalized outreach + D2 portfolio".
- **Variant Salvador tier 1**: low-competition (50-150 applicants) →
  mede conversion rate de "volume + remote-first fit".

Comparar response rate após 5 wd → decide scaling (more Salvador
se Salvador converter melhor).

## Riscos

| Risco | Prob | Impact | Mitigation |
|------|------|--------|------------|
| Split focus entre BYD + Salvador = execução fraca em ambos | M | H | cadência paralela clara; BYD anchor tem priorização de horário (manhã) |
| D2 portfolio atende BYD mas não Salvador context | M | M | customização mínima 2 sections (Section 1 + 4) — não recriar notebook |
| Salvador data market saturado em 6-12 meses | L | M | pivot para outras regions (Recife, Florianópolis) com mesmo template |
| 0 responses em 11 applications | L | H | Q3-2 retro (2026-08-07) — hypothesis 2 (timing/market) revision |

## Cross-link

- Parent: `data/matheus/objectives/q3-2026-primeira-vaga.md`
- Parallel (primary ONDA): `onda-2026-07-byd-deep-dive.md`
- Reuse: `byd-greenfield-map.md` (D1), `byd-econometric-vulnerability.ipynb` (D2),
  `byd-outreach-tier1.md` (D3), `byd-tracker-schema.sql` (D4)
- Decision log: `.omo/ikigai/meta/options-exploration-log.md` (DEC-12 pending)
