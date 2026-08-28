# 11 — Postulado: Dívida Cognitiva

> **Categoria:** §2 Primitivos de domínio
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** PAV §6 (carga cognitiva), habit_engine.py (energy deficit)

---

## §1 — Intuição em linguagem simples

Quando você pula uma tarefa, a "dívida" daquela tarefa carrega para frente. Algumas tarefas custam mais para deixar por fazer do que outras. Uma tarefa crítica atrasada 2 semanas permanece uma dívida mesmo após uma noite de sono.

## §2 — Enunciado formal

```
dívida(t) = decay · dívida(t−1) + Σᵢ (1 − conclusãoᵢ(t)) · custoᵢ
```

onde:

| Símbolo         | Tipo     | Faixa          | Significado                       |
|:---------------:|:--------:|:--------------:|:----------------------------------|
| `decay`         | `float`  | `0.7`          | Fator de decaimento overnight     |
| `conclusãoᵢ(t)`| `bool`   | `{0, 1}`       | 1 se tarefa i foi concluída em t  |
| `custoᵢ`        | `float`  | `[1, 10]`      | Peso por tarefa (crítico/baixo)   |

`dívida(0) = 0`. Acumulação infinita é limitada por saturação em `dívida_max = 100` (evita runaway).

## §3 — Justificativa não-técnica

Por que **decay < 1** (0.7 especificamente): o descanso overnight limpa parte da dívida (postulado 05 — sono), mas tarefas inacabadas de alto custo persistem. Uma tarefa crítica atrasada 14 dias permanece uma dívida não-zero mesmo após uma boa noite de sono — você ainda precisa enfrentá-la, e isso custa.

O parâmetro `custoᵢ ∈ [1, 10]` permite diferenciar entre tarefas triviais (custo=1: "responder 1 email") e tarefas críticas (custo=10: "entregar MVP do projeto"). A dívida ponderada é maior para o que importa mais, refletindo que **deixar o que importa pesa mais**.

## §4 — Referências cruzadas (consumidores downstream)

- **Axioma 04** (ordens parciais) — monotonicidade da dívida em `(1 − conclusãoᵢ)`
- **13-engine-habit-engine** — déficit de energia alimenta a dívida
- **15-meta-ikigai-5-vector-scoring** — vetor de habilidade degrada com dívida alta
- **22-meta-consolidacao-diaria** — dívida entra como penalidade no `overall`
- **23-meta-qhe-policy-mapping** — se `dívida > 50` por 3+ dias → regime REDUCE

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/habit_engine.py` — `compute_cognitive_debt(tasks)`
- `src/operational/docs/adr/PRD-CORE-HABIT-ENGINE.md` §4.6 — derivação da dívida cognitiva
- `vibe-ops/base/Produtividade Algorítmica Visual.md` §6 — modelo de carga cognitiva
