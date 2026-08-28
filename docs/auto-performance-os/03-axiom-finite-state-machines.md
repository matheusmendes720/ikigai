# 03 — Axioma: Máquinas de Estados Finitos

> **Categoria:** §1 Base axiomática
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** pomodoro_machine.py (7 estados), policy_engine.py (4 estados), 7 FSMs de ciclo de vida do IKIGAi

---

## §1 — Intuição em linguagem simples

Um comportamento complexo é apenas um conjunto de **estados** nomeados — ocioso, trabalhando, em pausa, pausado — e as **regras** para passar de um para outro. Você não pode estar "trabalhando" e "em pausa" ao mesmo tempo, mas pode fazer a transição de um para o outro. Uma máquina de estados é a forma formal de descrever isso.

## §2 — Enunciado formal

Uma máquina de estados finitos (FSM) é uma tupla `(S, Σ, δ, s₀, F)`:

| Símbolo   | Significado                                           |
|:---------:|:------------------------------------------------------|
| `S`       | Conjunto finito de estados (enum fechado)             |
| `Σ`       | Alfabeto de entrada — conjunto de eventos/gatilhos    |
| `δ: S × Σ → S` | Função de transição — para qual estado se vai   |
| `s₀ ∈ S`  | Estado inicial                                        |
| `F ⊆ S`   | Estados de aceitação/finais                           |

Uma transição é **válida** sse `(estado_atual, evento) ∈ transições_válidas`. Transições inválidas são rejeitadas (lançam `ValueError`, registram auditoria ou retornam erro — depende da implementação).

## §3 — Justificativa não-técnica

A vida é em sua maior parte discreta. Você está num bloco de TRABALHO de pomodoro ou numa PAUSA — não "meio a meio". Você está no regime PUSH ou MAINTAIN ou REDUCE ou RECOVER — não "mais ou menos empurrando". Modelar esses estados como **estados explícitos com regras de transição explícitas** torna o sistema:

- **Testável** — cada transição é um teste unitário (PRD-CORE-POMODORO-SCENARIO tem 134 testes só para a SM do pomodoro)
- **Previsível** — o usuário pode raciocinar sobre o que vem a seguir (depois de `WORK → BREAK` sempre volta `WORK`, a menos que seja a última rodada)
- **Auditável** — cada transição emite um registro de evento (a máquina de pomodoro emite 10 eventos por sessão completa)

O custo é a verbosidade: uma FSM de política com 4 estados precisa de 7+ regras de transição. O benefício é que **comportamentos complexos compõem a partir de peças simples e nomeadas**.

## §4 — Referências cruzadas (consumidores downstream)

- **10-postulado-pomodoro-rhythm** — claim de domínio construído sobre este axioma
- **14-engine-policy-engine-fsm** — implementa a FSM de 4 estados PUSH/MAINTAIN/REDUCE/RECOVER
- **15-engine-pomodoro-machine** — implementa a SM de 7 estados IDLE/WORK/BREAK/LONG_BREAK/PAUSED/SKIPPED/COMPLETE
- **16-meta-regime-fsm** — FSM de 4 estados do IKIGAi com histerese
- **17-meta-phase-pivot-fsm** — FSM de 5 fases do IKIGAi com convergência iterativa
- **FSMs de ciclo de vida:** task_sm, project_sm, habit_sm, routine_sm, goal_sm, objective_sm, deliverable_sm, dream_sm (`src/ikigai/src/ikigai/state_machines/`)

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/pomodoro_machine.py` — SM de 7 estados, 11 transições (referência canônica)
- `src/operational/packages/core/src/operational/core/policy_engine.py` — FSM de 4 estados com histerese
- `src/ikigai/src/ikigai/core/heuristics/regime.py` — FSM de regime do IKIGAi
- `src/ikigai/src/ikigai/core/heuristics/phase_pivot.py` — FSM de fase do IKIGAi
- `src/operational/docs/adr/PRD-CORE-POMODORO-SCENARIO.md` §3.1 — diagrama de estados + tabela de transição
- `src/operational/docs/adr/PRD-CORE-POLICY-CONSOLIDATOR.md` §4 — regras de avaliação da FSM
- Hopcroft, J. E., Motwani, R., & Ullman, J. D. (2006). *Introduction to Automata Theory, Languages, and Computation*. 3ª ed. Pearson.
