# 08 — Postulado: Blocos de Tempo e Context Switch

> **Categoria:** §2 Primitivos de domínio
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** PRD-CORE-TIME-BLOCKS-AND-REFLECTION §4, break_calculator.py, context_switch.py

---

## §1 — Intuição em linguagem simples

Um "bloco de tempo" é uma unidade de tempo alocada a uma atividade. Blocos têm início, fim e atividade. Entre dois blocos há ou uma **pausa** (gap) ou uma **troca de contexto** (sem gap). Nem todas as trocas custam o mesmo: exercício → trabalho custa mais que admin → admin.

## §2 — Enunciado formal

**BreakCalculator:**

```
pausa_minutos(anterior, proximo) = max(0, (proximo.início − anterior.fim) / 60)
```

**Matriz ContextSwitch — 9 pares de atividades, custo ∈ [0, 30] minutos:**

```
              │ trabalho │ admin │ exercício
──────────────┼──────────┼───────┼──────────
trabalho      │    0     │   5   │    15
admin         │   10     │   0   │    10
exercício     │   20     │  10   │     0
```

Linhas = atividade anterior; colunas = atividade próxima. O custo é adicionado ao `custo_acumulado` do dia.

## §3 — Justificativa não-técnica

Por que uma matriz 9-pares e não um custo único: nem todas as trocas são iguais. Trabalho → trabalho é no-op (0 min); exercício → trabalho (banho, troca de roupa, refoco) custa 20 minutos. Rastrear esses custos permite ao consolid diário penalizar agendas fragmentadas e recompensar blocos contíguos.

A matriz é **simétrica no eixo da diagonal** (troca entre a mesma atividade = 0) mas **assimétrica fora dela** (o custo de "sair" de uma atividade ≠ custo de "entrar"). Isso reflete a realidade: sair do exercício (banho,降温) custa mais do que entrar nele (alongamento rápido).

## §4 — Referências cruzadas (consumidores downstream)

- **18-engine-time-validator** — valida blocos sobrepostos, gaps negativos
- **19-engine-break-calculator** — calcula pausas entre blocos
- **20-engine-context-switch** — aplica matriz 9-pares
- **22-meta-consolidacao-diaria** — penaliza fragmentação via `custo_acumulado`

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/break_calculator.py` — `compute_break_minutes(prev, next)`
- `src/operational/packages/core/src/operational/core/context_switch.py` — matriz 9-pares
- `src/operational/docs/adr/PRD-CORE-TIME-BLOCKS-AND-REFLECTION.md` §4 — BreakCalculator e ContextSwitch
- `src/operational/packages/core/src/operational/core/journal_segmenter.py` — segmentação PT-BR por marcadores narrativos
