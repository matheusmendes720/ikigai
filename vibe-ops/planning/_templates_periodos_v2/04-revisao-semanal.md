---
type: period_report
period: weekly
template_version: 1.0
ikigai_cluster: plan
entity_type: period_report
date_start: YYYY-MM-DD
date_end: YYYY-MM-DD
sonho_id:
ikigai_vector:
xp_gained:
mastery_delta:
verdict:
verdict_score:
policy_recommendation:
parent_period: id_da_onda_pai
status: draft
tags: [period/weekly, ikigai/plan, revisao-semanal]
---

# Revisão Semanal: [Semana N da Onda Y]

> **Horizonte:** 7 dias (1 semana) · **Cluster:** PLAN (Tático) · **Vinculado a:** [[Hierarquia de Objetivos#1. Revisão Semanal]]
>
> A revisão semanal é o sensor/adjuster do loop cibernético. Mede 7 dias, recomenda a PolicyEngine para a próxima semana.

---

## 1. Identificação

- **Semana ID:** `[semana-NN]` (ex: `semana-01`)
- **Período:** [YYYY-MM-DD] → [YYYY-MM-DD] (7 dias)
- **Onda Pai:** [FK para `03-onda.md`]
- **Sonho Pai:** [FK para `01-sonho.md`]
- **Status:** [ ] Draft / [ ] Em Revisão / [ ] Fechada

---

## 2. KPIs da Semana

> *Consolidar os 7 Relatórios Diários. Para detalhes, ver `_periodos/dia-NN.md`.*

| Indicador | Meta (Set-point) | Realizado | Desvio (Gap) |
|-----------|:---:|:---:|:---:|
| Horas de Estudo (Deep Work) | [X]h | [Y]h | [Y-X] |
| Pomodoros Concluídos (Velocity) | [X] | [Y] | [Y-X] |
| Completion Rate (Relatórios Diários) | ≥ 0.80 | [Y] | [Y-0.80] |
| Consistência de Hábitos (% dias cumpridos) | ≥ 80% | [Y]% | [Y-80] |
| Q_HE Médio (Bem-estar) | ≥ 0.65 | [Y] | [Y-0.65] |
| Horas de Sono Médias | ≥ 7.5h | [Y]h | [Y-7.5] |
| Eventos de Foco Quebrado | ≤ 3 | [Y] | [3-Y] |
| Infrações (Leve/Média/Grave) | ≤ 2 | [Y] | [2-Y] |

---

## 3. Completion Rate Semanal

> *Média aritmética simples dos 7 Relatórios Diários desta semana.*

**Completion Rate Semanal:** [0.00 - 1.00]

- [ ] ≥ 0.80 → EXCELENTE
- [ ] 0.65 - 0.79 → BOM
- [ ] 0.50 - 0.64 → RAZOÁVEL
- [ ] < 0.50 → CRÍTICO (acionar alerta)

---

## 4. PolicyEngine Trail (Semanal)

> *Como o sistema regulou o esforço durante a semana?*

```
Segunda: [MAINTAIN]
Terça:   [PUSH]
Quarta:  [PUSH]
Quinta:  [MAINTAIN]
Sexta:   [REDUCE]
Sábado:  [RECOVER]
Domingo: [RECOVER]
```

- **Estado Dominante:** [A que mais dias o sistema ficou]
- **Dias em PUSH:** [X]
- **Dias em MAINTAIN:** [X]
- **Dias em REDUCE:** [X]
- **Dias em RECOVER:** [X]
- **Total de Transições:** [X]

---

## 5. Verdict Computado (Algoritmo da Revisão Semanal)

> *Verdict = policy state recomendada para a próxima semana.*

```
SE completion >= 0.80 AND sono_medio >= 7.5 AND qhe_medio >= 0.65:
    verdict = PASS  → policy_recommendation = PUSH
ELIF completion >= 0.65 OR sono_medio >= 6.5 OR qhe_medio >= 0.55:
    verdict = PARTIAL  → policy_recommendation = MAINTAIN
ELIF completion < 0.50 OR sono_medio < 6.0 OR qhe_medio < 0.45:
    verdict = FAIL  → policy_recommendation = REDUCE ou RECOVER
```

- **Verdict:** [ ] PASS / [ ] PARTIAL / [ ] FAIL
- **Verdict Score:** [0.00 - 1.00]
- **Policy Recommendation:** [ ] PUSH / [ ] MAINTAIN / [ ] REDUCE / [ ] RECOVER

---

## 6. Retrospectiva (O que funcionou, o que quebrou)

> *Foco em processos, não apenas em resultados.*

### 6.1 O que acelerou a execução
- [Item 1 — ex: "Time blocking matinal funcionou bem"]
- [Item 2 — ex: "Pomodoro de 50+10 melhor que 25+5"]

### 6.2 O que gerou fricção / Dívida Cognitiva
- [Item 1 — ex: "Reuniões não-planejadas consumiram 2 blocos"]
- [Item 2 — ex: "API do Taskwarrior quebrou terça"]

### 6.3 ADR Pessoal (Architectural Decision Record)
- **Decisão:** [O que vamos mudar no processo para a próxima semana?]
- **Contexto:** [Por que essa decisão agora?]
- **Consequências:** [O que esperamos que melhore/piorar?]

---

## 7. Top 3 Must-Haves da Próxima Semana

> *Os 3 objetivos irrevogáveis — se nenhum for cumprido, a semana fracassou.*

1. **[Épico/Atividade]** — [Objetivo Claro e Acionável] (IKIGAi: [passion/skill/market/revenue])
2. **[Épico/Atividade]** — [Objetivo Claro e Acionável] (IKIGAi: [passion/skill/market/revenue])
3. **[Épico/Atividade]** — [Objetivo Claro e Acionável] (IKIGAi: [passion/skill/market/revenue])

---

## 8. Sincronização Taskwarrior

- [ ] Tarefas não concluídas foram movidas ou descartadas (Taskwarrior)
- [ ] Log de tempo processado (Timewarrior)
- [ ] Dívida Cognitiva avaliada e repriorizada (Micro-ciclos)
- [ ] Novos Épicos quebrados em tarefas < 4h
- [ ] Pomodoros registrados e consolidados no DB

---

## 9. Aprendizados e Insights (Knowledge Capture)

> *O que aprendi nesta semana que merece virar nota atômica?*

- [Insight 1 — ex: "PolicyEngine funciona melhor com hysteresis ≥ 3 dias"]
- [Insight 2 — ex: "Q_HE correlaciona com sono, não com horas de estudo"]
- [Insight 3 — ex: "MVK nível 2 → 3 leva ~15h de prática deliberada"]

---

## 10. Próxima Onda / Onda Atual — Continuidade

- **Onda Atual:** [FK]
- **Status da Onda:** [ ] No início / [ ] No meio / [ ] Próxima semana é a última
- **Meta da Onda:** [Reforçar a meta]

---

## Sincronização e Fechamento

- [ ] Os 7 Relatórios Diários consolidados
- [ ] KPIs preenchidos (8 indicadores)
- [ ] Completion rate calculado
- [ ] Policy trail semanal registrado
- [ ] Verdict + recommendation computados
- [ ] Retrospectiva + ADR pessoal
- [ ] Top 3 must-haves da próxima semana definidos
- [ ] Sincronização Taskwarrior feita
- [ ] Sync com `vibe_ops.db` via `life sync vault`

---

*Template: Revisão Semanal · v1.0 · Cluster PLAN (Tático) · IKIGAi Sys-01 · 2026-06-26*
