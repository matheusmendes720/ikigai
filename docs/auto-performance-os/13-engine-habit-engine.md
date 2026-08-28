# 13 — Engine: Habit Engine (PAV §6)

> **Categoria:** §3 Engines
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** habit_engine.py, PRD-CORE-HABIT-ENGINE, IKIGAi qhe.py

---

## §1 — Intuição em linguagem simples

Cada hábito é uma sequência independente que **compõe** ao longo do tempo. O Habit Engine é o executor central da fórmula H(t) sobre todos os hábitos ativos, mais as métricas derivadas que alimentam o Q_HE.

## §2 — Enunciado formal

```
H_nível(t)   = 1 − exp(−λ · sequência)
E_req(t)     = R · (1 − H_nível(t))
eficiência   = H_nível / (1 + E_req)
H_médio      = Σᵢ (wᵢ · Hᵢ) / Σᵢ wᵢ
consistência = concluídas / planejadas
bônus_seq    = min(sequência_atual / 90, 1.0)
Q_HE         = H_médio · eficiência · (1 + η · bônus_seq)
```

**Constantes:**

| Símbolo | Valor          | Significado                            |
|:-------:|:--------------:|:---------------------------------------|
| `λ`     | `0.093 dia⁻¹`  | Taxa de aprendizado                    |
| `R`     | por hábito     | Resistência inata da tarefa            |
| `η`     | `0.5`          | Multiplicador do bônus de sequência    |
| `wᵢ`    | por hábito     | Peso do hábito i no agregado           |

## §3 — Justificativa não-técnica

Por que Q_HE é **multiplicativo** e não aditivo: cada componente (maestria, eficiência, bônus de sequência) precisa ser interpretável isoladamente. Se um dia o Q_HE cair, dá pra ver se foi H que caiu (hábito não cumprido), E que caiu (energia baixa) ou bônus de sequência (sequência quebrada). Soma ponderada esconderia isso.

O bônus de sequência entra como `1 + η·S` em vez de `η·S` aditivo: usuário novo com sequência=0 ainda pontua diferente de zero. Isso bate com a intuição de que **começar do zero não é o mesmo que falhar**.

## §4 — Referências cruzadas (consumidores downstream)

- **Axioma 02** (decaimento exponencial) — base matemática de H_nível
- **06-postulado-momentum-habito** — claim de domínio construído sobre este engine
- **14-engine-policy-engine-fsm** — Q_HE governa transições de regime
- **15-meta-ikigai-5-vector-scoring** — vetor paixão consome H(t) do Habit Engine

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/habit_engine.py` — `compute_habit_level`, `compute_efficiency_ratio`, `compute_qhe`
- `src/ikigai/src/ikigai/core/scoring/qhe.py` — Q_HE do IKIGAi
- `src/operational/docs/adr/PRD-CORE-HABIT-ENGINE.md` §4 — derivação completa
- `vibe-ops/base/Produtividade Algorítmica Visual.md` §6 — modelo de energia
