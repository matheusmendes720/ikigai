# 07 — Postulado: Orçamento de Energia

> **Categoria:** §2 Primitivos de domínio
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** PRD-CORE-POLICY-CONSOLIDATOR §4.2, budget.py, Day Quadrant

---

## §1 — Intuição em linguagem simples

Você tem ~16 horas acordadas. A energia não é ilimitada — esgota ao longo do dia, e tarefas de alta intensidade custam mais que as de baixa intensidade. O orçamento é particionado em 4 quadrantes (manhã profunda, manhã rasa, tarde profunda, tarde rasa).

## §2 — Enunciado formal

Day Quadrant (PRD-CORE-POLICY-CONSOLIDATOR §4.2):

```
Q(momento, intensidade) ∈ {MANHÃ_PROFUNDA, MANHÃ_RASA, TARDE_PROFUNDA, TARDE_RASA}
E_orcamento(momento) = base(momento) · (1 + α · intensidade) − β · custo_acumulado
```

**Bases por quadrante:**

| Quadrante          | Hora local    | base  | α (sensibilidade a intensidade) | β (custo acumulado) |
|:------------------:|:-------------:|:-----:|:-------------------------------:|:-------------------:|
| MANHÃ_PROFUNDA     | 06:00 – 11:00 | 1.00  | 0.30                            | 0.05                |
| MANHÃ_RASA         | 06:00 – 11:00 | 0.65  | 0.20                            | 0.05                |
| TARDE_PROFUNDA     | 14:00 – 18:00 | 0.85  | 0.25                            | 0.08                |
| TARDE_RASA         | 14:00 – 18:00 | 0.55  | 0.15                            | 0.08                |

## §3 — Justificativa não-técnica

O dia tem 4 partições naturais que alinham com o ritmo circadiano: manhã profunda (alta atenção, corpo descansado), manhã rasa (tarefas administrativas), tarde profunda (atenção pós-almoço), tarde rasa (wind-down). Cada uma tem um orçamento base que se esvota conforme o dia progride.

A manhã profunda tem a maior base (1.00) porque coincide com o pico de cortisol e temperatura corporal. A tarde rasa tem a menor (0.55) porque coincide com o vale pós-almoço e a queda de alerta circadiano. O parâmetro β é maior à tarde porque o custo acumulado pesa mais conforme o dia avança.

## §4 — Referências cruzadas (consumidores downstream)

- **17-engine-budget-classifier** — classifica cada tarefa num quadrante + custo
- **22-meta-consolidacao-diaria** — compõe o sub-score de energia
- **23-meta-qhe-policy-mapping** — alimenta o Q_HE via modificadores de regime

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/budget.py` — `classify_budget(moment, intensity)`
- `src/operational/docs/adr/PRD-CORE-POLICY-CONSOLIDATOR.md` §4.2 — bases e parâmetros do Day Quadrant
- `vibe-ops/base/Produtividade Algorítmica Visual.md` §6 — modelo de energia derivado
- `strategics/Planejamento (Estratégico e Tático).md` — bloco tarde focado em trabalho profundo (Blocos Diários)
