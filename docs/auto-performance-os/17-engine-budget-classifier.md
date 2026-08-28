# 17 — Engine: Budget Classifier

> **Categoria:** §3 Engines
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** budget.py, PRD-CORE-POLICY-CONSOLIDATOR §4.2

---

## §1 — Intuição em linguagem simples

Classifica cada tarefa em um **quadrante** do dia + estima seu **custo**. O quadrante determina o tipo de trabalho esperado (profundo vs raso); o custo modula o orçamento restante do dia.

## §2 — Enunciado formal

```
classificar(tarefa, hora_início) → (quadrante, custo_estimado)
quadrante ∈ {MANHÃ_PROFUNDA, MANHÃ_RASA, TARDE_PROFUNDA, TARDE_RASA}
custo_estimado ∈ [1, 10]
```

**Regras de classificação:**

| Hora de início   | Tipo de tarefa         | Quadrante        | Custo base |
|:----------------:|:----------------------:|:----------------:|:----------:|
| 06:00 – 11:00    | cognitiva profunda     | MANHÃ_PROFUNDA   | 7          |
| 06:00 – 11:00    | administrativa         | MANHÃ_RASA       | 3          |
| 14:00 – 18:00    | cognitiva profunda     | TARDE_PROFUNDA   | 6          |
| 14:00 – 18:00    | administrativa         | TARDE_RASA       | 3          |
| 11:00 – 14:00    | qualquer               | ALMOÇO           | (sem slot) |
| 18:00 – 23:00    | qualquer               | NOITE            | 2          |

**Modificador de custo:**

```
custo_final = custo_base · (1 + dificuldade · 0.1)
```

`dificuldade ∈ [0, 10]` (autoavaliação 0-10).

## §3 — Justificativa não-técnica

Por que **4 quadrantes** em vez de contínuo: o dia tem pontos de inflexão naturais (almoço, noite) que dividem em regimes de produtividade distintos. Tratar o dia como contínuo forçaria a estimar "estou 73% produtivo agora" — uma quantização que é arbitrária. Os 4 quadrantes são **observáveis** (manhã/tarde + profunda/rasa) e alinham com o ritmo circadiano conhecido.

O **ALMOÇO** é excluído como quadrante: durante almoço, não há trabalho produtivo a classificar. Tarefas que caem nesse slot são flagadas como **scheduling error** (forçar reagendamento).

## §4 — Referências cruzadas (consumidores downstream)

- **07-postulado-orcamento-energia** — Day Quadrant canônico
- **18-engine-consolidator** — custo alimenta `bônus_tempo` inversamente
- **14-engine-policy-engine-fsm** — tarefas em quadrante errado baixam regime

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/budget.py` — `classify_budget(task, start_time)`
- `src/operational/docs/adr/PRD-CORE-POLICY-CONSOLIDATOR.md` §4.2 — bases do Day Quadrant
- `vibe-ops/base/Produtividade Algorítmica Visual.md` §6 — modelo de energia
