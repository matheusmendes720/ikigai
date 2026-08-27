---
ueid: ikigai:artifact:byd-hiring-managers-salvador:00000000:00000000
entity_type: artifact
parent_ueid: ikigai:deliverable:byd-market-research:00000000:00000000
slug: byd-hiring-managers-salvador
title: "Salvador/remote hiring managers map — Tier 1 fallback (W1)"
artifact_type: data
is_public: false
created_at: 2026-07-09T00:00:00Z
updated_at: 2026-07-09T00:00:00Z
source: user
tags: [persona/matheus, deliverable/d1-output, fallback/salvador, mode/decision-maker-map]
custom:
  _purpose: "Hiring managers para top-3 vagas Salvador/remote (FullStack + BairesDev + Alignerr). BYD Yueying Zhang permanece ANCHOR #1. Salvador/remote é TIER 1 FALLBACK."
  _tools:
    - "LinkedIn search manual (free tier)"
    - "RocketReach free tier (50 lookups/mo)"
    - "Snov.io free tier (50 lookups/mo)"
    - "Hunter.io search by domain"
    - "Google: '[empresa] [vaga] hiring manager'"
---

# Salvador/Remote Hiring Managers Map — Tier 1 Fallback (W1)

> **Prioridade estratégica 2026-07-09:** BYD anchor (Yueying Zhang) é **#1
> absoluto**. Este mapa é **TIER 1 FALLBACK** — só ativa se BYD não converte
> em 5 wd, ou para **paralelo apply** (lean diversification). Geograficamente
> focado em Salvador-BA + remote-friendly empresas.

## Tabela de decision makers (Tier 1)

| # | Empresa | Vaga | Manager | LinkedIn URL | Email pattern | Score (0-10) | Notes |
|---|---------|------|---------|--------------|---------------|--------------|-------|
| **1** ⭐ | **FullStack Labs** | Data Engineer - Remote | ___ (TBD via Wd 1 search) | ___ | recruiter@fullstacklabs.com (verify hunter.io) | **7** | remote-first company; LinkedIn Easy Apply primary path |
| **2** ⭐ | **BairesDev** | Analista de Dados Remoto | ___ (TBD; BairesDev tem TA team SP/LATAM) | ___ | careers@bairesdev.com OR [first.last]@bairesdev.com | **7** | BairesDev = established remote-first; apply via careers portal |
| **3** ⭐ | **Alignerr** | Engenheiro Software AI Training | ___ (TBD; Alignerr é startup AI training) | ___ | careers@alignerr.com OR via LinkedIn | **6** | startup; outreach LinkedIn direto |
| 4 | EY Salvador | Engenheiro IA Pleno | ___ (TBD via LinkedIn search "EY Salvador tech manager") | ___ | [first.last]@br.ey.com OR via EY careers | 6 | big4; standardized process; apply via portal |
| 5 | Jobbol | Engenheiro Dados Pleno | platform (no specific manager) | n/a | n/a (job portal) | 5 | job portal aggregator; no individual outreach |
| 6 | INDI Staffing | Talent Data Analyst | ___ (TBD via LinkedIn "INDI Staffing Brazil recruiter") | ___ | [first.last]@indistaffing.com OR via LinkedIn | 6 | staffing agency; LinkedIn Easy Apply |
| 7 | AgileEngine | Senior Data Scientist | ___ (TBD; AgileEngine LATAM team) | ___ | [first.last]@agileengine.com OR careers@ | 6 | remote-first; LinkedIn Easy Apply |

## Search strategy (Wd 1 — manual search, 30-60 min total)

**Per company (5 min each):**

1. **FullStack Labs recruiter**:
   - LinkedIn search: "FullStack Labs Brazil recruiter" + "FullStack Labs Data Engineer"
   - Hunter.io: search by domain `fullstacklabs.com`
   - Google: `site:linkedin.com "FullStack Labs" "Brazil" OR "Salvador"`
   - Expected: 1-3 recruiter profiles, score ≥ 6

2. **BairesDev TA LATAM**:
   - LinkedIn: "BairesDev Talent Acquisition" + "BairesDev Brazil"
   - BairesDev careers portal: `bairesdev.com/careers` (apply via portal primary)
   - Hunter.io: search `bairesdev.com` (TA emails usually public)
   - Expected: 5-10 TA profiles, score 6-7

3. **Alignerr AI training**:
   - LinkedIn: "Alignerr AI trainer" + "Alignerr Brazil"
   - Alignerr careers: `alignerr.com/careers`
   - Google: `site:linkedin.com "Alignerr" "Brazil"`
   - Expected: 1-3 profiles (startup = small team), score 5-7

4. **EY Salvador tech manager** (secondary):
   - LinkedIn: "EY Salvador tech manager" + "EY Brazil data engineer"
   - EY careers portal (primary path)
   - Lower priority — EY is bureaucratic, hiring via portal

5. **Jobbol platform**: no individual manager — apply via portal.

6. **INDI Staffing**: search INDI Brazil recruiter (staffing agencies have public recruiters).

7. **AgileEngine LATAM**: search "AgileEngine Latin America" + "data science".

## Email pattern notes (verify via Hunter.io)

- **BairesDev**: `[first.last]@bairesdev.com` (verify)
- **FullStack Labs**: `recruiter@fullstacklabs.com` (verify)
- **Alignerr**: `[first.last]@alignerr.com` (verify)
- **EY**: `[first.last]@br.ey.com` (Big4 standard)
- **INDI**: `[first.last]@indistaffing.com`
- **AgileEngine**: `[first.last]@agileengine.com`

## Decision gate

- **≥ 3 managers high-score (≥ 6)** enables parallel outreach alongside BYD anchor
- **< 3 managers** → fallback to Easy Apply only (no personalized outreach)
- **0 managers** → hypothesis: Salvador data market é mais portal-driven do que referral-driven (pivot to volume apply)

## Anti-spam considerations (per Q-003 DEC-05)

- ≤ 5 LinkedIn connections/dia TOTAL (incluindo BYD anchor) — split entre empresas
- ≤ 2 emails/dia para mesma empresa
- ≥ 3 wd entre mensagens para mesma pessoa
- Personalizar cada email com nome + 1 hook técnico (data + Salvador local)

## Cross-link

- Parent: `data/matheus/deliverables/byd-market-research.md` (D1 entity)
- Parallel: `byd-hiring-managers.md` (BYD Yueying Zhang anchor)
- Parallel: `byd-greenfield-map.md` (vagas Salvador/remote table)
- Next: alimenta `byd-d3-outputs/byd-outreach-tier1.md` (templates prontos)
- Project: `onda-2026-07-salvador-data-pipeline.md` (segunda ONDA draft)