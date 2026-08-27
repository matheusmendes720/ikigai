---
type: period_report
period: daily
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
parent_period: id_da_semana_pai
status: draft
tags: [period/daily, ikigai/plan, relatorio-diario]
---

# Relatório Diário: [YYYY-MM-DD]

> **Horizonte:** 1 dia · **Cluster:** PLAN (Operacional) · **Vinculado a:** [[Análise (Tático e Operacional)#2.4 Relatórios e Supervisões]]
>
> O relatório diário é a unidade atômica do sistema. Consolida blocos, hábitos, métricas e PolicyEngine. Alimenta a Revisão Semanal.

---

## 1. Identificação

- **Data:** [YYYY-MM-DD]
- **Dia da Semana:** [ ] Seg / [ ] Ter / [ ] Qua / [ ] Qui / [ ] Sex / [ ] Sáb / [ ] Dom
- **Tipo de Dia:** [ ] Workday / [ ] Weekend / [ ] Holiday / [ ] Sick
- **Semana Pai:** [FK para `04-revisao-semanal.md`]
- **Onda Pai:** [FK para `03-onda.md`]
- **Status:** [ ] Draft / [ ] Fechado

---

## 2. Estado Fisiológico

> *Snapshot matinal do corpo.*

- **Hora de Acordar:** [HH:MM]
- **Qualidade do Sono (1-10):** [X]
- **Horas de Sono:** [X.X]h (meta ≥ 7.5h)
- **Energia Inicial (1-10):** [X]
- **Treino Matinal:** [ ] Sim ([X]min) / [ ] Não
- **Meditação:** [ ] Sim ([X]min) / [ ] Não
- **Café da Manhã:** [ ] Sim / [ ] Não

---

## 3. Blocos Executados (Pomodoros)

> *Um bloco = 1 Pomodoro de 50min foco + 10min pausa. Meta: 8 rounds/dia ideal.*

| # | Início | Fim | Atividade | IKIGAi Vetor | Status |
|---|--------|-----|-----------|:---:|:---:|
| 1 | [HH:MM] | [HH:MM] | [Ex: Deep Work — código projeto X] | [Skill] | [✓] |
| 2 | [HH:MM] | [HH:MM] | [Ex: Leitura — paper Y] | [Skill] | [✓] |
| 3 | [HH:MM] | [HH:MM] | [Ex: Networking outreach] | [Market] | [✗] |
| 4 | [HH:MM] | [HH:MM] | [...] | [...] | [...] |
| 5-8 | [...] | [...] | [...] | [...] | [...] |

**Pomodoros Concluídos:** [X] / [X planejados]
**Pomodoros Planejados:** [X] (meta: 8)
**Completion Rate do Dia:** [X / Y] (0.00 - 1.00)

---

## 4. Hábitos (Status do Dia)

> *Marcar ✓ para cumprido, ✗ para não cumprido, ~ para parcial.*

| Hábito | Categoria | Meta | Status | Streak (dias) |
|--------|:---:|:---:|:---:|:---:|
| [Ex: Treino físico] | [physiological] | [30min] | [✓] | [X] |
| [Ex: Meditação] | [mental] | [15min] | [✓] | [X] |
| [Ex: Leitura 30min] | [learning] | [30min] | [~] | [X] |
| [Ex: Sono ≥ 7.5h] | [recovery] | [7.5h] | [✗] | [X] |
| [Ex: Sem redes sociais AM] | [focus] | [100%] | [✓] | [X] |

**Hábitos Cumpridos:** [X] / [X total]
**Consistência do Dia:** [X / Y] (0.00 - 1.00)

---

## 5. Métricas do Dia

> *Métricas operacionais do [[Planejamento (Estratégico e Tático)#2.2.1 Sistema de Blocagem Temporal]].*

| Métrica | Valor | Meta |
|---------|:---:|:---:|
| Horas de Foco Profundo (Deep Work) | [X.X]h | ≥ 4h |
| Tempo Total em Pausas | [X]min | 50-100min |
| Eventos de Foco Quebrado (context switches) | [X] | ≤ 3 |
| Infrações Cometidas | [X] | 0 |
| Severidade da Pior Infração | [Leve/Média/Grave/Gravíssima] | Leve |
| Q_HE Computado (Habit Engine) | [0.XX] | ≥ 0.65 |
| Pomodoros Concluídos / Planejados | [X/Y] | ≥ 0.80 |

---

## 6. PolicyEngine Decision (do dia)

> *Saída do motor de decisão PUSH/MAINTAIN/REDUCE/RECOVER.*

- **Severidade do Desvio:** [ ] LOW / [ ] MEDIUM / [ ] HIGH / [ ] CRITICAL
- **Policy Atual:** [ ] PUSH / [ ] MAINTAIN / [ ] REDUCE / [ ] RECOVER
- **Setpoints Aplicados:**
  - hardwork_budget: [X.X]h
  - pause_minutes: [X]min
  - sleep_target: [X.X]h
  - qhe_target: [0.XX]
  - c_comp_target: [0.XX]
- **Alertas:** [Lista de alertas do dia, se houver]
- **Recomendações:** [Lista de recomendações]

---

## 7. Verdict Computado (Algoritmo Diário)

> *Fórmula: completion_rate + sono + Q_HE. Verdict binário derivado.*

```
SE completion_rate >= 0.80 AND sono_horas >= 7.5 AND qhe >= 0.65:
    verdict = PASS  → policy_recommendation = PUSH (amanhã)
ELIF completion_rate >= 0.50 OR sono_horas >= 6.5 OR qhe >= 0.45:
    verdict = PARTIAL  → policy_recommendation = MAINTAIN (amanhã)
ELSE:
    verdict = FAIL  → policy_recommendation = REDUCE ou RECOVER (amanhã)
```

- **Completion Rate:** [0.XX]
- **Verdict:** [ ] PASS / [ ] PARTIAL / [ ] FAIL
- **Verdict Score:** [0.00 - 1.00] (= 0.5 × completion_rate + 0.3 × (sono_horas/8) + 0.2 × qhe)
- **Policy Recommendation para amanhã:** [ ] PUSH / [ ] MAINTAIN / [ ] REDUCE / [ ] RECOVER

---

## 8. Bloqueios e Impedimentos

> *O que impediu um score melhor?*

- [Bloqueio 1 — ex: "API do GitHub caiu, perdi 2h"]
- [Bloqueio 2 — ex: "Reunião não-planejada consumiu bloco matinal"]
- [Bloqueio 3 — ex: "Energia caiu por sono ruim"]

---

## 9. Aprendizados do Dia (Knowledge Capture)

> *O que aprendi hoje que merece virar nota atômica (5_atomicas/)?*

- [Aprendizado 1 — ex: "TypeScript narrowing funciona melhor com discriminated unions"]
- [Aprendizado 2 — ex: "Pomodoros consecutivos > 4 = queda exponencial de foco"]
- [Aprendizado 3 — ex: "Q_HE correlaciona mais com sono do que com horas de estudo"]

---

## 10. Plano para Amanhã (Forward-Looking)

> *Os must-haves de amanhã, definidos no Shutdown Ritual.*

1. **[Must-Have 1]** — [Atividade Acionável] (IKIGAi: [vetor])
2. **[Must-Have 2]** — [Atividade Acionável] (IKIGAi: [vetor])
3. **[Must-Have 3]** — [Atividade Acionável] (IKIGAi: [vetor])

**Política Alocada:** [Estado previsto da PolicyEngine amanhã]
**Setpoint Alvo:** [X.X]h de foco profundo

---

## Sincronização e Fechamento

- [ ] Estado fisiológico registrado (sono, energia, treino)
- [ ] Pomodoros registrados com timestamps
- [ ] Hábitos marcados (✓ / ✗ / ~)
- [ ] Métricas calculadas (7 indicadores)
- [ ] PolicyEngine decision registrada
- [ ] Verdict + recommendation computados
- [ ] Bloqueios documentados
- [ ] Aprendizados capturados (≥ 1)
- [ ] Plano de amanhã definido
- [ ] Sync com `vibe_ops.db` via `life sync vault`

---

*Template: Relatório Diário · v1.0 · Cluster PLAN (Operacional) · IKIGAi Sys-01 · 2026-06-26*
