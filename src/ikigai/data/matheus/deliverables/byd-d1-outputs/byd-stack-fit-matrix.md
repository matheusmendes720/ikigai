---
ueid: ikigai:artifact:byd-stack-fit-matrix:00000000:00000000
entity_type: artifact
parent_ueid: ikigai:deliverable:byd-market-research:00000000:00000000
slug: byd-stack-fit-matrix
title: "BYD stack-fit matrix — vaga × stack × meu match (W1)"
artifact_type: data
is_public: false
created_at: 2026-07-09T00:00:00Z
updated_at: 2026-07-09T00:00:00Z
source: user
tags: [persona/matheus, deliverable/d1-output, empresa/byd, mode/stack-fit-analysis]
custom:
  _purpose: "Matriz qualitativa vaga × stack_required × meu_match; gate: ≥ 1 vaga com fit ≥ 60%"
  _my_stack_profile:
    core: [python, polars, pandas, sql, statsmodels, scikit-learn]
    intermediate: [plotly, jupyter, duckdb, numpy, scipy]
    learning: [spark, dbt, airflow, kubernetes, cloud (aws/gcp)]
    soft: [financial markets, econometria, vulnerability analysis]
  _vaga_columns_reference:
    - "Linguagem principal (Python/R/SQL/Excel/etc.)"
    - "Stack data (Polars/Pandas/Spark/dbt/etc.)"
    - "Domínio (finanças/operacional/marketing/etc.)"
    - "Seniority (junior/pleno/senior)"
    - "Soft skills (comunicação, ownership, etc.)"
---

# BYD Stack-Fit Matrix — vaga × stack × meu match

> **Janela-alvo:** cross-reference entre greenfield-map (≥ 3 vagas) +
> meu stack profile.
> **Gate criteria:** ≥ 1 vaga com fit ≥ 60% (matheus consegue entregar
> valor em ≤ 1 mês ramp-up).

## Matriz qualitativa (preencher durante W1-Wd 2)

| # | Vaga (link greenfield-map) | Linguagem | Stack data | Domínio | Seniority | Fit (0-100) | Ramp-up estimate | Notes |
|---|---------------------------|-----------|------------|---------|-----------|-------------|------------------|-------|
| 1 | ___ | ___ | ___ | ___ | ___ | ___ | ___ | ___ |
| 2 | ___ | ___ | ___ | ___ | ___ | ___ | ___ | ___ |
| 3 | ___ | ___ | ___ | ___ | ___ | ___ | ___ | ___ |
| 4 | ___ | ___ | ___ | ___ | ___ | ___ | ___ | ___ |
| 5 | ___ | ___ | ___ | ___ | ___ | ___ | ___ | ___ |

## Fit scoring (rubrica composta)

| Componente | Peso | Score 0-100 | Reasoning |
|------------|------|-------------|-----------|
| Linguagem match | 25% | ___ | ___ |
| Stack data match | 30% | ___ | ___ |
| Domínio match | 20% | ___ | ___ |
| Seniority match | 15% | ___ | ___ |
| Soft skills match | 10% | ___ | ___ |
| **TOTAL** | **100%** | **___** | weighted sum |

## Ramp-up estimate (semanas até produtividade 80%)

- **≤ 1 wd**: fit ≥ 80% (uso direto do meu stack)
- **1-2 wd**: fit 60-80% (precisa aprender 1 lib específica)
- **2-4 wd**: fit 40-60% (precisa aprender 1 framework novo)
- **> 4 wd**: fit < 40% (escopo novo; re-evaluate)

## Decision gate (synthesis com greenfield-map + hiring-managers)

| Vaga | Stack fit | Manager score | Outreach priority (1-3) |
|------|-----------|---------------|-------------------------|
| Vaga 1 | ___ | ___ | ___ |
| Vaga 2 | ___ | ___ | ___ |
| Vaga 3 | ___ | ___ | ___ |

- **Priority 1** (alta fit + high-score manager): first batch D3 cold outreach (Wd 3)
- **Priority 2** (média fit OR manager): second batch (rolling)
- **Priority 3** (baixa fit OR no manager): drop ou follow-up tardio

## Cross-link

- Parent: `data/matheus/deliverables/byd-market-research.md` (D1 entity)
- Parallel: `data/matheus/deliverables/byd-d1-outputs/byd-greenfield-map.md`
- Parallel: `data/matheus/deliverables/byd-d1-outputs/byd-hiring-managers.md`
- Next: alimenta `data/matheus/deliverables/byd-cold-outreach-assets.md` (D3)

## Notes for future iterations

- Se BYD mudar stack (e.g., migrar para Snowflake), update esta matriz
- Se eu aprender nova lib/framework (e.g., dbt), update `_my_stack_profile`
- Manter disciplina de 1 fonte por stack claim (LinkedIn job description
  é ground truth; não inventar stack required)