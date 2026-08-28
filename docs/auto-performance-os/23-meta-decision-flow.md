# 23 — Meta: Decision Flow (Observar → Recomendar → Decidir → Executar)

> **Categoria:** §4 Meta-orquestração
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** ADR-003 §6, decision_flow.py (planejado)

---

## §1 — Intuição em linguagem simples

O **fluxo de decisão canônico** do sistema. Começa com a observação do estado atual, passa por uma recomendação de regime, valida com o usuário (ou com UCB), e termina executando o regime escolhido. Toda decisão de auto-performance segue este pipeline de 4 etapas — falhas em qualquer etapa viram logging estruturado.

## §2 — Enunciado formal

**Pipeline:**

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 1. OBSERVAR  │───▶│2. RECOMENDAR │───▶│ 3. DECIDIR   │───▶│ 4. EXECUTAR  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
      │                    │                    │                    │
      ▼                    ▼                    ▼                    ▼
   H(t), Q_HE         alvo_bruto         regime_final         pomodoros,
   overall,            (f(Q_HE))          (com histerese       blocos de tempo,
   sono                                       + UCB)         SONHOs do dia
```

**Pseudo-código:**

```
def decidir(data: Date) -> Regime:
    # 1. OBSERVAR
    qhe = habit_engine.compute_qhe(data)
    overall = consolidator.compute_daily_overall(data)
    sono = sleep_validator.classify(data)
    
    # 2. RECOMENDAR
    alvo_bruto = policy_engine.alvo_bruto(qhe)
    
    # 3. DECIDIR (histerese + UCB)
    regime_anterior = state.regime_atual
    regime_com_histerese = policy_engine.aplicar_histerese(
        regime_anterior, alvo_bruto
    )
    regime_final = ucb_recalibrator.argmax(
        [PUSH, MAINTAIN, REDUCE, RECOVER],
        history=state.history[-30]
    )
    
    # 4. EXECUTAR (delegado para outros engines)
    pomodoros = pomodoro_machine.planejar(data, regime_final)
    blocos = budget_classifier.allocate(regime_final, qhe)
    
    return regime_final
```

## §3 — Justificativa não-técnica

Por que **4 etapas explícitas** (e não uma função monolítica): cada etapa tem **dependências distintas** e pode falhar/ser sobreescrita independentemente. (1) Observar é determinístico — lê dados. (2) Recomendar é função pura de Q_HE. (3) Decidir é onde a histerese + UCB filtram oscilação. (4) Executar é onde interage com o usuário real (pomodoros, blocos).

Por que **UCB na etapa 3** (e não na 2): a etapa 2 é uma **recomendação matematicamente ótima** dado o estado atual; a etapa 3 é onde **incerteza histórica** entra (não estamos confiantes no regime atual? UCB sugere explorar). UCB olha para trás, histerese olha para o agora.

Por que **state.regime_anterior como input**: sem essa entrada, a Policy FSM não consegue aplicar histerese (não saberia de onde veio). É o **único estado mutável** do pipeline — todas as outras etapas são funções puras.

## §4 — Referências cruzadas (consumidores downstream)

- **13-engine-habit-engine** — produtor de Q_HE (etapa 1)
- **18-engine-consolidator** — produtor de overall (etapa 1)
- **16-engine-sleep-validator** — produtor de sono (etapa 1)
- **21-meta-qhe-policy-mapping** — produtor de alvo_bruto (etapa 2)
- **20-engine-ucb-recalibrator** — produtor de regime_final (etapa 3)
- **15-engine-pomodoro-machine** — executor (etapa 4)
- **17-engine-budget-classifier** — executor (etapa 4)

## §5 — Fontes

- `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` §6 — decision flow canônico
- `src/ikigai/src/ikigai/core/orchestrator/decision_flow.py` (planejado — ADR-003 §6)
- `vault/ikigai/meta/algorithmic-loop-overview.md` — visão geral do loop