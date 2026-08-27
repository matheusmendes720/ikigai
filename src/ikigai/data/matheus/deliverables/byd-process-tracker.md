---
ueid: ikigai:deliverable:byd-process-tracker:693ebfb6:6c641956
entity_type: deliverable
slug: byd-process-tracker
parent_ueid: ikigai:project:onda-2026-07-byd-deep-dive:c112f3a0:8825d88a
related_ueids: []
title: "D4 — Process tracker (outreach → response → processo)"
description: null
status: IN_PROGRESS
ikigai_vectors: [market, revenue]
vector_weights_snapshot: {passion: 0.10, skill: 0.10, market: 0.50, revenue: 0.25, course: 0.05}
phase_at_creation: fundacao
regime_at_creation: push
horizon_days: 7
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [persona/matheus, horizon/7d, deliverable/d4, workstream/w4, empresa/byd, mode/process-tracking]
last_reviewed_at: 2026-08-26T00:00:00Z
artifact_path: byd-d4-outputs/byd-tracker.db
artifact_type: data
is_public: false
created_at: 2026-07-09T00:00:00Z
updated_at: 2026-08-26T00:00:00Z
custom:
  _horizon_rationale: "7 wd sprint (rolling); W4 + extensão pós-onda se D3 gera respostas iniciais"
  _deliverable_role: "measurement (rolling forward; outcome signal para validar hipótese central)"
  _completion_date: 2026-08-26
  _updates:
    - date: 2026-08-26
      event: "BYD CV Campaign completed — auto-applicable patches applied"
      detail: "All 4 BYD CV variants (v8 fullstack, v9 bigdata, v10 ops, v11 ITAM) patched: 17 patches applied (P-A to P-M, B3, B5); H3 cap identified as dominant blocker; projected post-B1 scores 87-91pt (band A)"
      artifact: "job_hunter/base/cv-versions/BYD-CV-Campaign-Report.md"
      next_action: "candidate supplies B1 graduation years → all 4 CVs cross 65pt threshold for submission"
    - date: 2026-08-25
      event: "soft-rule audit + scoring pass"
      detail: "42 violations across 4 CVs; H3 graduation years clamps all to 49pt (D); B1 is single unblock"
  _outputs:
    - "tracker/byd-outreach-log.sqlite — schema + 5-10 rows iniciais"
    - "tracker/byd-funnel-dashboard.md — métricas agregadas (response_rate, time_to_response, conversion)"
    - "tracker/q3-2026-wave-report.md — final report (1-page TL;DR + tabela de status por vaga)"
  _success_criteria:
    - "Schema sqlite idempotente (rerun = no-op)"
    - "≥ 5 outreaches registrados com timestamps + outcome"
    - "≥ 1 response registrada (mesmo 'no-fit' conta como data point)"
    - "Dashboard weekly auto-generated (script)"
  _b1_blocker:
    description: "H3 graduation year cap — all 4 CVs at 49pt (D)"
    fix: "candidate supplies 3 graduation years"
    impact: "removes H3 cap → all 4 CVs jump to ~87-91pt (A)"
  _sqlite_schema:
    - "outreach(id, date_sent, channel, target_name, target_role, template_used, status, response_date, notes)"
    - "response(id, outreach_id, date, type, content_summary, next_action)"
    - "process(id, response_id, stage, stage_date, notes)"
  _funnel_stages:
    - "1. outreach_sent"
    - "2. response_received"
    - "3. phone_screen"
    - "4. take_home_assigned"
    - "5. take_home_submitted"
    - "6. onsite"
    - "7. offer"
---

# D4 — Process tracker (W4+, 7 wd rolling)

> **Objetivo:** medir taxa de conversão do funil outreach → processo
> → offer; fornecer data points para validar hipótese central da onda
> (≥ 1 resposta em 5 envios).

## Métricas-alvo da onda (validation criteria)

| Métrica | Target | Lock condition |
|---------|--------|----------------|
| Outreach_sent | ≥ 5 | abaixo = sub-utilização; re-evaluate escopo |
| Response_rate | ≥ 20% | ≥ 1 resposta em 5 envios = hipótese válida |
| Phone_screen | ≥ 1 (best case) | bonus, não bloqueador |
| Time_to_response | ≤ 5 wd | outlier = hiring freeze; flag Q3-2 retro |

## Schema sqlite (idempotente)

```sql
CREATE TABLE IF NOT EXISTS outreach (
  id INTEGER PRIMARY KEY,
  date_sent TEXT NOT NULL,
  channel TEXT CHECK(channel IN ('linkedin', 'email')),
  target_name TEXT,
  target_role TEXT,
  template_used TEXT,
  status TEXT CHECK(status IN ('sent', 'opened', 'response', 'no_response')),
  response_date TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS response (
  id INTEGER PRIMARY KEY,
  outreach_id INTEGER REFERENCES outreach(id),
  date TEXT,
  type TEXT CHECK(type IN ('positive', 'neutral', 'negative', 'no_fit')),
  content_summary TEXT,
  next_action TEXT
);

CREATE TABLE IF NOT EXISTS process (
  id INTEGER PRIMARY KEY,
  response_id INTEGER REFERENCES response(id),
  stage TEXT CHECK(stage IN ('phone_screen', 'take_home', 'onsite', 'offer', 'rejected')),
  stage_date TEXT,
  notes TEXT
);
```

## Weekly dashboard (auto-gen)

Script `tracker/build_dashboard.py`:

- COUNT(*) outreach per week
- COUNT(response) / COUNT(outreach) response_rate
- AVG(time_to_response in days)
- Funnel stages counts

Output: `tracker/byd-funnel-dashboard.md` (markdown para fácil leitura).

## Final wave report (entrega D4 done)

Após 30 d (fim da onda), `tracker/q3-2026-wave-report.md`:

```markdown
# BYD Wave Report — Jul-2026

## TL;DR
[1 parágrafo: hipótese validada? sim/não + 1 métrica chave]

## Funnel outcome
[Tabela: outreach → response → phone_screen → take_home → onsite → offer]

## Learnings
[3-5 bullets: o que funcionou, o que não, o que mudar Q3-2]

## Q3-2 implications
[Decision gate: replica? pivota? nova empresa-alvo?]

## Cross-link
- D1 (market research): [link]
- D2 (econometric analysis): [link]
- D3 (cold outreach assets): [link]
```

## Decisão gate (Q3-2 retro 2026-08-07)

A partir deste D4 data, decide:

- (a) Hipótese validada → replica método para 5-10 outras empresas (Q3-2)
- (b) Hipótese parcial → pivota 1 elemento (ex: muda stack, muda empresa-alvo)
- (c) Hipótese invalidada → Q3-2 escopo broader (volta 30 empresas + 2-3 verticals)

## Riscos

| Risco | Prob | Impact | Mitigation |
|------|------|--------|------------|
| 0 responses em 10 envios | M | H | data point honest; pivot Q3-2 |
| BYD hiring freeze mid-onda | L | H | flag em D4 dashboard; pause W4 |
| Schema sqlite quebra (mudança D3) | L | M | migrations versionadas; CI check antes de "done" |

## Cross-link forward-compat

- Q3-2 (próxima onda) referencia este D4 como baseline de response_rate
  esperado para deep-dive em 1 empresa.
- profile-2026-07-03.json vector scores atualizam após D4 done
  (revenue vector +0.10 se offer, +0.05 se entrevista técnica, +0.02 se response).

