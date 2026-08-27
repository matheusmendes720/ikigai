---
ueid: ikigai:deliverable:byd-cold-outreach-assets:704b61c1:2c2603f2
entity_type: deliverable
parent_ueid: ikigai:project:onda-2026-07-byd-deep-dive:c112f3a0:8825d88a
slug: byd-cold-outreach-assets
title: "D3 — Cold outreach assets (LinkedIn + email PT-BR)"
status: DONE
ikigai_vectors: [market, course]
vector_weights_snapshot: {passion: 0.10, skill: 0.15, market: 0.55, revenue: 0.10, course: 0.10}
phase_at_creation: fundacao
regime_at_creation: push
horizon_days: 2
artifact_path: byd-d3-outputs/byd-outreach-tier1.md
artifact_type: document
is_public: false
created_at: 2026-07-09T00:00:00Z
updated_at: 2026-08-26T00:00:00Z
tags: [persona/matheus, horizon/2d, deliverable/d3, workstream/w3, empresa/byd, mode/cold-outreach, lang/pt-br]
last_reviewed_at: 2026-08-26T00:00:00Z
custom:
  _completion_date: 2026-07-09
  _horizon_rationale: "2 wd sprint (W3); D1 + D2 são pré-requisitos — overlap permitido"
  _deliverable_role: "action-oriented (W3 gates D4)"
  _language_strategy: "PT-BR primary (per Q-006 DEC-07 phased rollout, Phase 1); EN secondary só para intl hiring managers"
  _priority_target_2026-07-09: "Yueying Zhang — Hiring Manager Business Specialist Camacari (vaga posted 1 d ago). Lean T0 first-outreach recomendado ANTES de D2 portfolio pronto (janela crítica). Ver DEC-12 pending log."
  _outputs:
    - "templates/linkedin-pt-connection.md — 300 char PT-BR conexão (≤ 5 vagas-alvo templates)"
    - "templates/linkedin-pt-followup-d2.md — follow-up D+2 (curto)"
    - "templates/email-pt-curriculo-attach.md — email curto + CV anexo (D2 PDF)"
    - "templates/email-en-followup.md — fallback EN se manager intl"
    - "templates/lean-first-outreach-t0.md — T0 pitch sem portfolio (acelerado) — NOVO 2026-07-09"
    - "tracker/outreach-log.md — template para D4 sqlite ingest"
  _success_criteria:
    - "≥ 4 templates prontos (≥ 1 por canal/language)"
    - "Cada template ≤ 300 chars corpo (cold outreach best practice)"
    - "Cada template menciona 1 insight de D2 (ex: 'análise cambial BYD' como hook)"
    - "Templates A/B testáveis (variação A vs B para 1 template)"
  _a_b_test_plan:
    - "A: 'análise quantitativa' (hook D2)"
    - "B: 'fit para vaga X específica' (mais direto)"
    - "Métrica: response rate (rastreado em D4)"
---

# D3 — Cold outreach assets (W3, 2 wd)

> **Objetivo:** produzir templates prontos para enviar primeiro batch
> de 5-10 mensagens (LinkedIn + email) em W3-W4, baseado em findings
> de D1 + D2.

## Language strategy (rationale)

- **PT-BR primary** (per Q-006 DEC-07 Phase 1, BR-focused Q3 validar método).
- **EN secondary**: só para intl hiring managers (e.g., hiring manager
  chinês baseado em SP office, comum em multinacionais).
- **Sem ES** (Phase 2 evaluation pós-Q3 — Q-006 DEC-07).

## Templates (4 mínimo)

### T1 — LinkedIn conexão PT-BR (300 char) — **LEVERAGE FIRST: Yueying Zhang (Business Specialist Camacari)**

```
Olá Yueying, vi que a BYD abriu vaga de Business Specialist em
Camaçari. Sou Matheus, trabalho com análise de vulnerabilidades
econômicas (Python + dados macro BR) — analisei exposição cambial e
supply chain BYD recentemente. Posso compartilhar em 2 min e ver se
faz sentido conversar?
```

**Persona adapt (quando D2 portfolio pronto):**
```
Olá Yueying, vi a vaga de Business Specialist em Camaçari. Sou
Matheus, analisei a vulnerabilidade cambial da BYD recentemente
([1-pager PDF]) e tenho interesse genuíno em contribuir. Posso
compartilhar? Abraço.
```

### T2 — LinkedIn follow-up D+2 PT-BR

```
[Nome], segue o link do estudo: [D2-writeup link curto]. Se fizer
sentido para [vaga X], adoraria conversar 15 min sobre como posso
contribuir para [time Y]. — Matheus
```

### T3 — Email PT-BR + CV anexo

```
Assunto: Análise quant BYD + interesse [Vaga X]

[Nome],

Sou Matheus Mendes, trabalho com Python/Polars aplicado a financial
markets. Fiz uma análise das vulnerabilidades macro BYD ([1-page PDF
anexo]) que talvez seja útil para [desafio Y que vi na vaga].

Fico à disposição para 15 min de conversa.

— Matheus
```

### T4 — Email EN (fallback intl managers)

```
Subject: BYD macro vulnerability analysis + [Role X] interest

[Name],

I'm Matheus, quant analyst (Python/Polars). I built a short study on
BYD's macro vulnerabilities ([1-page PDF]) that may be relevant to
[challenge Y from job description]. Happy to share + discuss 15 min.

Best,
Matheus
```

### T0 — **Lean First Outreach (acelera D3 antes de D2 pronto)** ⭐ NOVO 2026-07-09

**Context**: Business Specialist Camacari posted 1 dia atrás = janela
crítica. Lean option: outreach AGORA sem D2 portfolio completo, focado
no pitch de "I studied your company" + oferecer análise como
diferenciador. D2 vira follow-up subseqüente.

**T0 LinkedIn (≤ 300 char)**:
```
Olá Yueying, vi a vaga de Business Specialist em Camaçari (postada
ontem). Sou Matheus, Salvador-BA, trabalho com análise quantitativa
(análise de vulnerabilidades cambiais e supply chain). Estou
começando um estudo focado em BYD Brasil esse mês. Posso contribuir
para essa posição? Abraço.
```

**T0 Email curto (≤ 120 words PT-BR)**:
```
Assunto: Business Specialist Camaçari — análise de vulnerabilidade cambial

Yueying,

Vi a vaga de Business Specialist postada ontem em Camaçari (LinkedIn
[URL]). Sou Matheus Mendes, Salvador-BA, atuo com análise quantitativa
em mercados financeiros e estou iniciando um estudo focado em
vulnerabilidades macro da BYD Brasil este mês.

A vaga menciona ênfase em "data-driven insights for supplier
negotiations" — minha stack (Python/Polars + análise cambial)
alinha diretamente.

Posso compartilhar meu approach em 15 min e enviar 1-pager quando
pronto?

— Matheus Mendes
Salvador, BA · matheus.mendes@[email provider]
```

**T0 strategy**: outreach FIRST (Wd 1), pitch differentiates vs 200+
candidatos pela (a) localização Salvador-BA (= Mata Atlântica worker,
não SP/RJ usual suspects) + (b) abordagem "estudo focado em BYD"
(signal real, não generic recruiter-speak).

## A/B test (D4 measurement)

- **A (insight-led)**: T1 e T3 com hook D2 ("análise quantitativa").
- **B (fit-led)**: variação com "fit para vaga X" mais direto.

Rastreia response rate em D4; após 5-10 envios decide winner.

## Lean First-Outreach strategy (2026-07-09 pivot)

**Rationale**: prioridade BYD Business Specialist Camacari posted 1 dia
= janela crítica. Lean recommendation: **manda T0 hoje**, D2 portfolio
segue como follow-up (T1/T3 persona adapt). Não esperar D2 = perder
janela. Decisão registrada em options-exploration-log.md (DEC-2026-07-09-12,
pending write-up após esta execução).

**Riscos lean first-outreach** (registrados):

| Risco | Prob | Impact | Mitigation |
|------|------|--------|------------|
| T0 sem portfolio = "pretender" perception | M | H | ser honesto: "estou INICIANDO estudo este mês" (não fingir portfolio pronto) |
| 200+ applicants = noise | H | M | diferenciação via localização + pitch específico |
| Hiring manager bilíngue mandarim | L | M | pedir ajuda básico (1-2 frases no email: 你好, 我对...) se quiser |

## Anti-bot considerations (Q-003 DEC-05)

- **LinkedIn**: máx 5 connection requests/dia (sob limite free); backoff
  manual se rate-limit warning.
- **Email**: máx 2 emails/dia para BYD managers (evita spam flag).
- **Cold outreach honest**: envia contexto (não pitch genérico).

## Cross-link

- Alimenta D4: tracker/outreach-log.md é o template para sqlite ingest
  de cada mensagem enviada.
- Referência D2: cada template menciona 1 insight de D2 como hook
  (rationale: cold outreach com "I studied your company" tem 3-5x
  response rate vs genérico per Backlinko 2024).

## Riscos

| Risco | Prob | Impact | Mitigation |
|------|------|--------|------------|
| Templates muito longos | M | M | template review antes de enviar; > 300 char → rewrite |
| 0 responses em 10 envios | H | M | D4 regista; decision gate Q3-2 retro (DEC-08) |
| BYD spam filter rejeita email | L | H | usa Gmail + domínio BYD + SPF correto (testar manualmente) |
| **T0 lean first-outreach perceived as premature** | M | H | ser honesto sobre timing; oferecer valor real (estudo em curso) |

