---
ueid: ikigai:project:onda-2026-07-salvador-data-pipeline:54ce7879:ab4020c7
entity_type: project
slug: onda-2026-07-salvador-data-pipeline
parent_ueid: ikigai:objective:q3-2026-primeira-vaga:cbf000ba:c040f222
related_ueids: []
title: "Onda 2026-07 Salvador-Data Pipeline — Tier 1 FALLBACK (parallel to BYD ONDA)"
description: null
status: ARCHIVED
ikigai_vectors: [market, skill]
vector_weights_snapshot: {passion: 0.05, skill: 0.30, market: 0.50, revenue: 0.10, course: 0.05}
phase_at_creation: fundacao
regime_at_creation: push
horizon_days: 30
primary_score: null
is_placeholder: false
placeholder_owner: null
custom:
  _status_resolution: "ARCHIVED — activation trigger not met. BYD anchor (Yueying Zhang) response was sufficient, so Salvador tier-1 fallback was never activated. Project was designed as conditional parallel; since BYD ONDA succeeded (D1-D4 completed), this fallback was unnecessary. No deliverables produced under this project."
  _archived_reason: "trigger_not_met — fallback condition (BYD failure within 5 wd) did not occur"
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
source_md_path: null
tags: [persona/matheus, horizon/30d, onda/q3-2, workstream/w1, fallback/salvador, mode/data-pipeline]
last_reviewed_at: 2026-09-15T00:00:00Z
tech_stack: [python, polars, duckdb, plotly, sqlite, obsidian, taskwarrior]
repo_url: null
target_revenue_brl: null
actual_revenue_brl: 0.0
created_at: 2026-07-09T00:00:00Z
updated_at: 2026-09-15T00:00:00Z
---

# Onda 2026-07 Salvador-Data Pipeline — Tier 1 FALLBACK

> **Status:** ARCHIVED — 2026-09-15 per project review.
> **Reason:** Activation trigger not met. BYD ONDA succeeded; Salvador fallback was never activated.
> **This was a FALLBACK project** — only activated if BYD anchor failed within 5 wd.

## Contexto estratégico

**Decisão lean registrada em 2026-07-09 Wd 1 deep refresh:** após
descobrir **14 vagas Python/data ativas em Salvador-BA** (sendo 12
fully-remote), o escopo do SONHO Q3-2026 expandiu. Não é mais
"1 empresa BYD focus" — é **"BYD anchor + Salvador/remote
portfolio diversification"**.

Esta ONDA existiria para **operacionalizar** o Tier 1 fallback sem
duplicar D2 portfolio. Estratégia: **mesmo D2 notebook** (BYD
análise cambial) + **5 cover letters adaptados** para Salvador
context (remote-first DNA, Salvador location, Python/data stack).

## Activation trigger (não acionado)

- **DEFAULT**: status = draft, paralelo a BYD ONDA, sem ativação
  explícita necessária (cadência automática).
- **ESCALATION**: se BYD anchor (Yueying Zhang) não responder em
  **5 wd** (≤ 0 responses), Salvador tier 1 vira **primary path**
  e BYD vira **secondary**.

**Result:** BYD ONDA succeeded. Trigger was never met. Project archived.

## Top 5 Salvador/remote jobs (from byd-greenfield-map.md)

1. FullStack Data Engineer Remoto (90 fit)
2. BairesDev Analista Dados Remoto (85 fit)
3. Jobbol Engenheiro Dados Pleno Salvador (85 fit)
4. INDI Talent Data Analyst Remote (80 fit)
5. Alignerr Engenheiro Software AI training (80 fit)

## Links internos

- Parent: `objectives/q3-2026-primeira-vaga.md` (TRIMESTRE).
- BYD ONDA: `projects/onda-2026-07-byd-deep-dive.md`
