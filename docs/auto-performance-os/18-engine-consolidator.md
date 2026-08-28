# 18 — Engine: Consolidator (Diário)

> **Categoria:** §3 Engines
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** consolidator.py, PRD-CORE-POLICY-CONSOLIDATOR §4.5

---

## §1 — Intuição em linguagem simples

Implementa as fórmulas do postulado 12: agrega 4 sub-scores (energia, produtividade, saúde, overall) e decide se o dia foi PASS / PARTIAL / FAIL. O veredito alimenta a Policy Engine FSM do dia seguinte.

## §2 — Enunciado formal

```
energia       = média(H_mapeado, M_mapeado, L_mapeado) − 10 · (8 − sono_horas)
produtividade = base · 60 + bônus_tempo · 25 + bônus_foco · 15
saúde         = sono · 0.5 + exercício · 25 + água · 15
overall       = 0.3 · E + 0.4 · P + 0.3 · S
```

**Mapeamento:**

| Energia autorelatada | H/M/L mapeado |
|:-------------------:|:-------------:|
| HIGH                | 100           |
| MEDIUM              | 60            |
| LOW                 | 30            |

**Veredito (de `overall`):**

| Faixa `overall` | Veredito   | Ação no regime              |
|:---------------:|:----------:|:---------------------------:|
| `[0.70, 1.0]`   | PASS       | upgrade candidato           |
| `[0.50, 0.70)`  | PARTIAL    | mantém regime               |
| `[0.0, 0.50)`   | FAIL       | downgrade candidato         |

## §3 — Justificativa não-técnica

Por que **0.3/0.4/0.3** (produtividade com peso maior): produtividade é a dimensão **observável** — onde pomodoros concluídos, blocos cumpridos e foco mantido se materializam. É o output que o usuário **sente** e que diferencia um dia de progresso de um dia de estagnação.

Por que **penalidade de sono na energia** (`−10 · (8 − sono_horas)`): quem dormiu 6h perde 20 pontos de energia base; quem dormiu 10h ganha 0 (não penaliza oversleep mas também não recompensa — capturando que sono demais pode indicar problema). O `8` é o alvo saudável, não 9 (9 é ideal mas 8 é alcançável).

## §4 — Referências cruzadas (consumidores downstream)

- **12-postulado-consolidacao-diaria** — claim de domínio construído sobre este engine
- **13-engine-habit-engine** — H_mapeado vem de H(t)
- **14-engine-policy-engine-fsm** — veredito alimenta transição de regime
- **22-meta-consolidacao-diaria** — weekly_aggregator agrega 7 desses

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/consolidator.py` — `compute_daily_overall(...)`
- `src/operational/packages/core/src/operational/core/weekly_aggregator.py` — agregação semanal
- `src/operational/docs/adr/PRD-CORE-POLICY-CONSOLIDATOR.md` §4.5 — fórmulas canônicas + veredito
