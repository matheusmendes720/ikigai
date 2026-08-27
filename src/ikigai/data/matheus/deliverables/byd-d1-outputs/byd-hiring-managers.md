---
ueid: ikigai:artifact:byd-hiring-managers:00000000:00000000
entity_type: artifact
parent_ueid: ikigai:deliverable:byd-market-research:00000000:00000000
slug: byd-hiring-managers
title: "BYD hiring managers map — 5-10 decision makers (W1)"
artifact_type: data
is_public: false
created_at: 2026-07-09T00:00:00Z
updated_at: 2026-07-09T00:00:00Z
source: user
tags: [persona/matheus, deliverable/d1-output, empresa/byd, mode/decision-maker-map]
custom:
  _purpose: "5-10 nomes + LinkedIn + email_pattern + score_alinhamento; gate: ≥ 1 manager por vaga-alvo"
  _tools:
    - "LinkedIn Sales Navigator (free tier 30d trial; ou manual search)"
    - "RocketReach — https://rocketreach.co (free tier 50 lookups/mo)"
    - "Snov.io — https://snov.io (free tier 50 lookups/mo)"
    - "Hunter.io — https://hunter.io (search by domain: byd.com)"
    - "Google search: '[nome] BYD [cargo]' + site:linkedin.com/in/"
---

# BYD Hiring Managers Map — 5-10 decision makers

> **Janela-alvo:** decision makers ativos em BYD Brasil jul-ago 2026.
> **Gate criteria:** ≥ 1 manager identificado por vaga-alvo (do greenfield-map).
> **Preenchimento:** manual, durante W1 (D1, 3 wd).

## Tabela de decision makers

| # | Nome | Cargo | LinkedIn URL | Email pattern | Score (0-10) | Notes |
|---|------|-------|--------------|---------------|--------------|-------|
| **1** ⭐ | **Yueying Zhang** | Hiring Manager — Business Specialist (Camaçari/Supply Chain) | https://linkedin.com/in/yueying-zhang-byh-brasil (buscar) | yueying.zhang@byd.com (hunter.io verify) | **8** | **PRIORITY #1** — hiring manager direta da vaga #1 (Business Specialist Camacari). Nome chinês; ajuda mandarim básico. Posted 1 d ago = fresh. |
| 2 | ___ (TBD via Wd 1 search) | RH BYD Brasil / Talent Acquisition | ___ | ___@byd.com | ___ | secondary outreach se Yueying não responder |
| 3 | ___ | ___ | ___ | ___ | ___ | ___ |
| 4 | ___ | ___ | ___ | ___ | ___ | ___ |
| 5 | ___ | ___ | ___ | ___ | ___ | ___ |

## Score rubrica (alinhamento com vaga-alvo)

- **0-2**: cargo não-relacionado (admin, suporte, facilities)
- **3-5**: cargo tangencial (HR, marketing, vendas)
- **6-7**: cargo diretamente relacionado (hiring manager direto da vaga-alvo)
- **8-10**: cargo top (C-level, VP, Director da área) — high-leverage cold outreach

## Search strategy (cross-reference com greenfield-map)

- **Wd 1-2**:
  - Para cada vaga-alvo (≥ 3 vagas greenfield-map), busca hiring manager via:
    - LinkedIn search: "[empresa] [cargo da vaga]" + filter Brazil
    - RocketReach / Snov.io: lookup por nome + domínio byd.com
    - Hunter.io: search emails por domínio
  - Valida email pattern manualmente (testar 1-2 emails com template neuter)
- **Wd 3**:
  - Cross-reference score vs greenfield-map fit_score
  - Prioriza: high-fit vaga + high-score manager = top 3 outreach (D3)
  - Sub-3 score: drop (não perder tempo)

## Email pattern notes (BYD convention)

- BYD usa padrão: `[primeiro.nome]@byd.com` ou `[primeironome]@byd.com`
- Confirmar via Hunter.io: https://hunter.io/search/byd.com (free)
- Verificar deliverability: 1 email teste antes de batch (YAGNI: teste com 1-2 antes)

## Anti-spam considerations (per Q-003 DEC-05)

- ≤ 2 emails/dia para BYD managers (evita spam flag)
- ≥ 2 wd entre emails para mesmo manager (cadência human-like)
- Personalizar cada email com nome + 1 insight de D2 (não template genérico)

## Decision gate

- **≥ 3 managers high-score (≥ 6)**: enable D3 cold outreach campaign
- **< 3 managers high-score**: D3 vira "broader scope" (10+ emails, mais cadência)
- **0 managers identificáveis**: hypothesis 2 (timing) falha; pivot Q3-2 retro

## Cross-link

- Parent: `data/matheus/deliverables/byd-market-research.md` (D1 entity)
- Parallel: `data/matheus/deliverables/byd-d1-outputs/byd-greenfield-map.md`
- Parallel: `data/matheus/deliverables/byd-d1-outputs/byd-stack-fit-matrix.md`
- Next: alimenta `data/matheus/deliverables/byd-cold-outreach-assets.md` (D3)