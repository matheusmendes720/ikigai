# 20 — Engine: UCB Recalibrator

> **Categoria:** §3 Engines
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** ucb_recalibrator.py (planejado em ADR-003 §7), bandit literature

---

## §1 — Intuição em linguagem simples

Quando o sistema precisa decidir entre **explorar** (tentar regime novo) e **explotar** (ficar no regime que está funcionando), usa Upper Confidence Bound (UCB1) para balancear. Sem essa balanço, o sistema ficaria preso no primeiro regime que pareceu funcionar.

## §2 — Enunciado formal

**Fórmula UCB1:**

```
UCB(regime) = Q_HE_médio(regime) + c · √(2 · ln(N_total) / N_regime)
```

onde:

| Símbolo          | Significado                                          |
|:----------------:|:-----------------------------------------------------|
| `Q_HE_médio`     | Recompensa média observada do regime                 |
| `c`              | Constante de exploração (padrão `√2`)                |
| `N_total`        | Total de dias observados                             |
| `N_regime`       | Dias nesse regime específico                         |

**Decisão:**

```
regime_escolhido = argmax_regime UCB(regime)
```

## §3 — Justificativa não-técnica

Por que **UCB1** em vez de ε-greedy: UCB1 tem garantia teórica de regret logarítmico, e a intuição é simples — "tente regimes que você conhece pouco **se** a incerteza justifica o custo". Isso é perfeito para regime FSM porque:

1. **Poucos dias** no regime PUSH → alta incerteza → UCB convida a experimentar
2. **Muitos dias** no regime MAINTAIN → baixa incerteza → UCB confirma a escolha atual
3. **Mau desempenho** sustentado → Q_HE_médio cai → UCB naturalmente migra para outros regimes

A constante `c = √2` é o default da literatura (Auer, Cesa-Bianchi & Fischer 2002); pode ser ajustada para ser mais ou menos conservadora.

## §4 — Referências cruzadas (consumidores downstream)

- **14-engine-policy-engine-fsm** — UCB escolhe o regime-alvo antes da FSM decidir viabilidade
- **16-meta-regime-fsm** — versão IKIGAi pode usar UCB análogo
- **23-meta-decision-flow** — pipeline completo: observar → recomendar → decidir → executar

## §5 — Fontes

- `src/ikigai/src/ikigai/core/heuristics/ucb_recalibrator.py` (planejado — ADR-003 §7)
- Auer, P., Cesa-Bianchi, N., & Fischer, P. (2002). *Finite-time Analysis of the Multiarmed Bandit Problem*. Machine Learning, 47(2), 235–256.
- `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` §7 — quando UCB entra em jogo
