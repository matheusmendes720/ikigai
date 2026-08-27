---
type: period_report
period: onda
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
parent_period: id_da_avaliacao_trimestral_pai
status: draft
tags: [period/onda, ikigai/plan, micro-fase]
---

# Onda: [Tema ou Identificador — ex: "Onda Q3-W1: Fundamentação IA"]

> **Horizonte:** 45 dias úteis (3 semanas × 5 dias) · **Cluster:** PLAN (Tático) · **Vinculado a:** [[Análise (Tático e Operacional)#2.2 Ondas]]
>
> A onda é o ciclo tático onde 3 Rev. Semanais consolidam o progresso. O verdict dispara Correção do Trajeto se necessário.

---

## 1. Identificação da Onda

- **Onda ID:** `[onda-NN-tema]` (ex: `onda-01-fundamentacao-ia`)
- **Período:** [YYYY-MM-DD] → [YYYY-MM-DD] (15 dias úteis)
- **Tema Central:** [Nome claro do foco da onda]
- **Sonho Pai:** [FK para `01-sonho.md`]
- **Trimestre Pai:** [FK para `02-avaliacao-trimestral.md`]
- **IKIGAi Vetor:** [ ] Passion / [ ] Skill / [ ] Market / [ ] Revenue
- **Status:** [ ] Draft / [ ] Em Execução / [ ] Em Revisão / [ ] Fechada

---

## 2. 3 Revisões Semanais Consolidadas

> *Resumir as 3 semanas desta onda. Para detalhes, ver `_periodos/semana-N.md`.*

| Semana | Período | Completion Rate | Verdict Semanal | Policy Estado |
|--------|---------|:---:|:---:|:---:|
| Semana 1 | [YYYY-MM-DD] → [YYYY-MM-DD] | [0.XX] | [PASS] | [PUSH] |
| Semana 2 | [YYYY-MM-DD] → [YYYY-MM-DD] | [0.XX] | [PARTIAL] | [MAINTAIN] |
| Semana 3 | [YYYY-MM-DD] → [YYYY-MM-DD] | [0.XX] | [PASS] | [PUSH] |

**Completion Rate Médio da Onda:** [média das 3 semanas] (0.00 - 1.00)

---

## 3. Diagnóstico de Gaps (por dimensão)

> *Onde a onda perdeu força?*

| Dimensão | Meta | Realizado | Gap | Severidade |
|----------|:---:|:---:|:---:|:---:|
| Execução (pomodoros concluídos) | [X] | [X] | [X] | [H/M/L] |
| Análise (correção de rota) | [X] | [X] | [X] | [H/M/L] |
| Aprendizado (MVK atingido) | [X] | [X] | [X] | [H/M/L] |
| Bem-estar (Q_HE médio) | [0.65] | [X] | [X] | [H/M/L] |

---

## 4. Verdict Computado (Algoritmo da Onda)

> *Aplicar o protocolo "Correção do Trajeto" do [[Planejamento (Estratégico e Tático)#3.2]]*

```
SE completion_medio >= 0.75:
    verdict = CONTINUE_WAVE
ELIF completion_medio >= 0.50:
    verdict = CORRECT_TRAJECTORY
ELSE:
    verdict = KILL_WAVE
```

- **Verdict:** [ ] CONTINUE_WAVE / [ ] CORRECT_TRAJECTORY / [ ] KILL_WAVE
- **Verdict Score:** [0.00 - 1.00]
- **Policy Recommendation para próxima onda:** [ ] PUSH / [ ] MAINTAIN / [ ] REDUCE / [ ] RECOVER

---

## 5. Ações Corretivas (se CORRECT_TRAJECTORY ou KILL_WAVE)

> *Detalhe o que vai mudar na próxima onda.*

- **Causa Raiz:** [Análise: por que o gap apareceu?]
- **Mudanças Estruturais:**
  - [Ex: "Reduzir meta diária de 4 para 3 pomodoros"]
  - [Ex: "Adicionar 1h de revisão semanal"]
  - [Ex: "Trocar MVK de 'domínio pleno' para 'uso supervisionado'"]
- **Política da Próxima Onda:** [Qual estado da PolicyEngine?]

---

## 6. Roadmap da Próxima Onda

> *Top 3 objetivos que movem a agulha na próxima onda.*

1. **[Épico 1]** — [Objetivo Acionável] (IKIGAi: [vetor])
2. **[Épico 2]** — [Objetivo Acionável] (IKIGAi: [vetor])
3. **[Épico 3]** — [Objetivo Acionável] (IKIGAi: [vetor])

---

## 7. Sinais de Alerta (Watchlist)

> *O que monitorar durante a próxima onda?*

- [ ] Queda sustentada de Q_HE < 0.45 por >3 dias
- [ ] Aumento de infrações (Leve/Média/Grave) > 5/semana
- [ ] Burnout sustentado (>2 semanas em RECOVER)
- [ ] Falta de progresso no eixo MVK (pilar não subiu de nível)
- [ ] Refactor trigger externo (mudança de mercado, saúde, família)

---

## 8. Policy Trail da Onda

> *Como o sistema regulou durante a onda?*

```
Estado inicial:    [MAINTAIN]
   ↓
Semana 1: [PUSH] por [X] dias
Semana 2: [MAINTAIN] por [X] dias
Semana 3: [REDUCE] por [X] dias
   ↓
Estado final:      [MAINTAIN]
```

- **Dias em PUSH:** [X]
- **Dias em MAINTAIN:** [X]
- **Dias em REDUCE:** [X]
- **Dias em RECOVER:** [X]
- **Total de transições:** [X]

---

## 9. Consolidação IKIGAi (Delta da Onda)

| Vetor | Score Início | Score Fim | Δ | Comentário |
|-------|:---:|:---:|:---:|---|
| Passion | [0.XX] | [0.XX] | [+0.XX] | [...] |
| Skill | [0.XX] | [0.XX] | [+0.XX] | [...] |
| Market | [0.XX] | [0.XX] | [+0.XX] | [...] |
| Revenue | [0.XX] | [0.XX] | [+0.XX] | [...] |

**IKIGAi Total Δ:** [+0.XX]

---

## Sincronização e Fechamento

- [ ] As 3 Semanais foram consolidadas
- [ ] Completion rate médio calculado (0-1)
- [ ] Diagnóstico de gaps preenchido
- [ ] Verdict computado (CONTINUE / CORRECT / KILL)
- [ ] Ações corretivas definidas (se aplicável)
- [ ] Roadmap da próxima onda definido
- [ ] Sinais de alerta configurados
- [ ] Sync com `vibe_ops.db` via `life sync vault`

---

*Template: Onda · v1.0 · Cluster PLAN (Tático) · IKIGAi Sys-01 · 2026-06-26*
