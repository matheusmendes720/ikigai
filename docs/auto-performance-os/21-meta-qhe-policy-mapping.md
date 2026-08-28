# 21 — Meta: Mapeamento Q_HE → Policy FSM

> **Categoria:** §4 Meta-orquestração
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** ADR-003 §5, qhe.py, regime.py

---

## §1 — Intuição em linguagem simples

Esta é a camada que **conecta** o score Q_HE (calculado pelo Habit Engine) ao regime FSM (executado pela Policy Engine). Sem ela, teríamos dois sistemas isolados. O mapeamento define **faixas de score** que disparam **regimes específicos**, considerando também o histórico recente (histerese) para evitar oscilação.

## §2 — Enunciado formal

**Faixas canônicas de Q_HE:**

| Faixa Q_HE | Regime alvo (sem histerese) |
|:----------:|:---------------------------:|
| `[0.85, 1.0]` | PUSH (carga máxima)          |
| `[0.70, 0.85)` | MAINTAIN (carga nominal)    |
| `[0.60, 0.70)` | REDUCE (carga reduzida)     |
| `[0.0, 0.60)`  | RECOVER (carga mínima)      |

**Com histerese assimétrica:**

```
alvo_bruto = f(qhe_imediato)
            ⎧ PUSH      se qhe_imediato ≥ 0.85
            ⎨ MAINTAIN  se 0.70 ≤ qhe_imediato < 0.85
f(q) =      ⎪ REDUCE    se 0.60 ≤ qhe_imediato < 0.70
            ⎩ RECOVER   se qhe_imediato < 0.60

# Aplicar histerese:
regime_anterior = last_state
regime_final    = aplicar_histerese(regime_anterior, alvo_bruto, qhe_history)
```

**Regras de transição (replicando §14):**

| Transição              | Dias sustentados |
|:----------------------:|:---------------:|
| RECOVER → REDUCE       | 3               |
| REDUCE → MAINTAIN      | 3               |
| MAINTAIN → PUSH        | 3               |
| PUSH → MAINTAIN        | 2               |
| MAINTAIN → REDUCE      | 2               |
| REDUCE → RECOVER       | 2               |
| qualquer → RECOVER     | 1 (emergência)  |

## §3 — Justificativa não-técnica

Por que **mapeamento em camadas** (sem-histerese + com-histerese): o primeiro mapeamento (alvo_bruto) é o que **deveria** ser aplicado em regime permanente. O segundo (regime_final) é o que **realmente** é aplicado considerando inércia. Essa separação torna visível **duas decisões distintas**: (a) qual regime o score sugere, (b) se vale a pena mudar do regime atual.

Por que **histerese assimétrica** (3 dias subindo, 2 descendo): promover intensidade é mais arriscado que reduzir. Se o Q_HE subir para 0.86 por um único dia (anomalia), aplicar PUSH imediatamente seria desperdício. Mas se cair para 0.55 (fadiga real), esperar 3 dias seria prejudicial. A assimetria reflete **viés conservador para upgrade**.

## §4 — Referências cruzadas (consumidores downstream)

- **13-engine-habit-engine** — produtor de Q_HE
- **14-engine-policy-engine-fsm** — consumidor de regime_final
- **18-engine-consolidator** — overall alimenta qhe_imediato
- **Axioma 04** (ordens parciais) — base matemática de histerese

## §5 — Fontes

- `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` §5 — INNER GUIDELINES Q_HE → regime mapping
- `src/ikigai/src/ikigai/core/heuristics/regime.py` — constantes HYSTERESIS_UPGRADE_DAYS=3, HYSTERESIS_DOWNGRADE_DAYS=2
- `src/operational/packages/core/src/operational/core/policy_engine.py` — função `transition`
- `vault/ikigai/meta/algorithm-issues-registry.md` — A02 debate sobre RECOVER threshold