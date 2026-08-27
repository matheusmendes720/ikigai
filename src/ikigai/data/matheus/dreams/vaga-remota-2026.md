---
ueid: ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609
entity_type: dream
slug: vaga-remota-2026
parent_ueid: null
related_ueids: []
title: "Primeira vaga remota em Data/AI até 2026-12-31"
description: null
status: ACTIVE
ikigai_vectors: [passion, skill, market, revenue, course]
vector_weights_snapshot: {passion: 0.20, skill: 0.20, market: 0.20, revenue: 0.20, course: 0.20}
phase_at_creation: fundacao
regime_at_creation: maintain
horizon_days: 547
primary_score: null
is_placeholder: false
placeholder_owner: null
created_at: 2026-07-03T00:00:00Z
updated_at: 2026-07-03T00:00:00Z
custom:
  _intent_vector: revenue
  _horizon_rationale: "18m sonho real (2026-07-06 → 2027-12-31); 547d added to DreamEntity literal set (R1 Option Z)"
  verticals: [data-analytics, ai-llm-tooling, dev-tools]
  pricing_lever: info-asymmetry
  target_roles: [data-engineer, analytics-engineer, bi-analyst, data-analyst, ml-ai-engineer, solutions-consultant, fullstack, backend]
  non_negotiables:
    - "100% remoto primary (Salvador híbrido fallback)"
    - "Python/Polars stack"
    - "Intl-friendly timezone"
    - "Salary floor: 'tanto faz para primeira vaga'"
    - "Weekly budget: 40+ h/semana (definir na SEMANA)"
source_md_path: null
tags: [persona/matheus, horizon/18m, vertical/generalist, target/remote]
last_reviewed_at: 2026-07-03T00:00:00Z
---

# SONHO — Primeira vaga remota em Data/AI até 2026-12-31

> **Hipótese (142 chars):** "Posso conquistar vaga remota em Data/AI até Dez/2026 mantendo sono
> ≥ 7.5h e treino físico 3×/semana" — alocação ~6h/semana SONHO + 4h/semana W1 + 4h/semana W2
> = 40h semanais totais (40+ budget colide com regime de manutenção).

## Narrativa (PT-BR)

A primeira vaga remota em Data/AI é o sonho horizonte-2026. Salvador como fallback híbrido
é aceitável, mas o target é 100% remoto primary. Stack não-negociável: Python + Polars.
Fuso intl-friendly. Salary floor só ativa depois da primeira vaga.

Esse SONHO é o driver de receita do persona. É o vetor `_intent_vector: revenue` — os outros
4 vetores (passion, skill, market, course) servem esse objetivo. Pricing lever é
informação-asimetria: nichos onde a interseção Data + AI + generalista é sub-ofertada.

Vertical estratégico: generalista pipeline — Data/Analytics/BI consulting + AI/LLM tooling
+ Dev tools. Não é especialista profundo em um nicho, é o consultor que conecta.

## Workstreams (W1–W4)

### W1 — Pipeline BI + cold outreach (regime: push)

**Output:** 30 empresas-alvo mapeadas, 20 mensagens enviadas, 5 respostas em 90 dias.

Mecânica: scrape semanal de vagas (LinkedIn, RemoteOK, YC WorkAtAStartup, Climatebase),
filtro por stack (Python/Polars + remote-first), templates frios personalizados por
empresa, sequência de follow-up 3-touch em 14 dias.

### W2 — Portfolio público + demos internas (regime: push)

**Output:** 1 demo interna de 12min gravada até 2026-09-15 + 1 projeto público no GitHub.

Mecânica: escolher 1 vertical (provavelmente BI consulting), construir demo end-to-end
(ingest → transform → serve), gravar Loom de 12min, publicar repo com README + data
sample + reproducible build.

### W3 — Engenharia social (LinkedIn + Twitter/X) (regime: maintain)

**Output:** 2 posts/semana sustentados em LinkedIn + 1 thread técnica/mês em X.

Mecânica: post curto mostrando progresso de SONHO, thread técnica mensal sobre um
problema real (Polars vs Pandas para 10GB+).

### W4 — Vídeos / conteúdo longo (regime: maintain)

**Output:** 1 vídeo técnico longo por trimestre, opcional.

Mecânica: investir se W2 demo der tração; ignorar se W1 + W2 já cobrem o budget.

## Sistemas de apoio (S1–S5)

1. **S1 — Sono ≥ 7.5h**: regime maintain, não negociável. Bedtime 23:00 Salvador.
2. **S2 — Treino físico 3×/semana**: maintain. Academia ou bike indoor.
3. **S3 — Diário / journaling semanal**: 30min/dia + 1h/week review.
4. **S4 — Taskwarrior + GTD**: inboxes → projects → next-actions → waiting-for.
5. **S5 — weekly review**: domingo 18h, OKRs + Q_HE + matriz Eisenhower retro.

## Kill conditions (refazer o SONHO)

- 90 dias sem resposta de nenhuma mensagem → reescrever W1 templates.
- 6 meses sem processo seletivo técnico → reescrever W2 portfolio.
- Q_HE < 0.45 sustentado por 4 semanas → mudar regime para REDUCE.
- Burnout (insônia > 2 semanas) → pausar W3 + W4, manter S1 + S2 + S5.

## Refactor triggers (voltar para o SONHO)

- Receita > R$ 8k/mês → SONHO evoluído para "segunda vaga + senioridade".
- 5+ SONHOs documentados → ADR-008 IKIGAi weight mechanism (Option A/B/C → decisão).
- 2+ processos seletivos técnicos concluídos → vector_weights_snapshot deixa de ser equal.

## Links internos

- Parent SONHO: este arquivo (raiz).
- Próximo nível: `objectives/q3-2026-primeira-vaga.md` (TRIMESTRE 90d).
- Profile snapshot: `ikigai_state/profile-2026-07-03.json`.
- Handoff original: `.omo/ikigai/meta/session-handoff-2026-07-03.md`.

---

*SONHO #1/5+ · bootstrap 2026-07-03 · Matheus Mendes · horizon 547d (R1 Option Z)*