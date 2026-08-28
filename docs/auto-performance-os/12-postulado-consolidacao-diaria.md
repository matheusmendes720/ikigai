# 12 — Postulado: Consolidação Diária

> **Categoria:** §2 Primitivos de domínio
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** PRD-CORE-POLICY-CONSOLIDATOR §4.5, consolidator.py

---

## §1 — Intuição em linguagem simples

No fim do dia, o sistema agrega 4 dimensões ortogonais em um único score-resumo para o usuário revisar: energia, produtividade, saúde e overall.

## §2 — Enunciado formal

**Fórmulas do Consolidator** (PRD-CORE-POLICY-CONSOLIDATOR §4.5):

```
energia       = média(H_mapeado, M_mapeado, L_mapeado) − 10 · (8 − sono_horas)
produtividade = base · 60 + bônus_tempo · 25 + bônus_foco · 15
saúde         = sono · 0.5 + exercício · 25 + água · 15
overall       = 0.3 · E + 0.4 · P + 0.3 · S
```

**Mapeamento de energia para score-base:**

| Energia autorelatada | Mapeamento (base 60) |
|:-------------------:|:--------------------:|
| HIGH                | 100                  |
| MEDIUM              | 60                   |
| LOW                 | 30                   |

## §3 — Justificativa não-técnica

Por que **0.3/0.4/0.3** (produtividade com peso maior): produtividade captura tanto execução (tempo investido, `bônus_tempo`) quanto qualidade (foco, `bônus_foco`). É a dimensão mais **acionável** — é onde pomodoros concluídos, blocos cumpridos e foco mantido se materializam.

Energia e saúde são co-protagonistas de suporte: energia alta sem saúde cai em 2-3 dias; saúde boa sem energia produz estagnação. O equilíbrio 30/40/30 reflete que **produtividade é o output observável**, mas precisa de input energético e estrutural para se sustentar.

O **mapeamento HIGH/MEDIUM/LOW → 100/60/30** é uma quantização discreta (ver axioma 01) que permite ao sistema agregar sem precisar de input numérico contínuo.

## §4 — Referências cruzadas (consumidores downstream)

- **Axioma 02** (decaimento exponencial) — H_mapeado vem de H(t)
- **14-engine-policy-engine-fsm** — `overall` governa o regime do dia seguinte
- **22-meta-consolidacao-diaria** — composição canônica
- **23-meta-qhe-policy-mapping** — IKIGAi Q_HE tem pesos análogos (0.35/0.20/0.25/0.10/0.15) sobre constituintes diferentes

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/consolidator.py` — `compute_daily_overall(sleep, exercise, water, pomo_done, focused_blocks)`
- `src/operational/docs/adr/PRD-CORE-POLICY-CONSOLIDATOR.md` §4.5 — fórmulas canônicas
- `src/operational/packages/core/src/operational/core/weekly_aggregator.py` — agregação semanal sobre esses sub-scores
