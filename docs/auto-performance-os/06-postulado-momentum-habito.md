# 06 — Postulado: Momentum do Hábito

> **Categoria:** §2 Primitivos de domínio
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** PRD-CORE-HABIT-ENGINE §4.1, ADR-003 §9.2, Lally et al. (2010)

---

## §1 — Intuição em linguagem simples

O dia 1 de um hábito é difícil. O dia 7 é muito mais fácil. O dia 90 é automático. Isso não é linear — é aproximação exponencial a uma assíntota.

## §2 — Enunciado formal

Do axioma 02 (decaimento exponencial):

```
H(t) = 1 − exp(−λ · t),    λ = 0.093 dia⁻¹
```

**Tempo até limiares de consolidação:**

| Marco                  | Dias  | H(t) ≈  |
|:----------------------:|:-----:|:-------:|
| 50% de consolidação    | ~7    | 0.480   |
| 75% de consolidação    | ~15   | 0.750   |
| Automaticidade mediana | ~66   | 0.998   |
| Consolidação efetiva   | 90    | 0.9998  |

## §3 — Justificativa não-técnica

A forma captura a **carga cognitiva decrescente** conforme a via neural se fortalece. Cada repetição custa menos que a anterior. Depois de ~66 dias, você passou da mediana para automaticidade (Lally 2010); depois de 90 dias, está em H≈0.9998 (efetivamente consolidado).

O cap de 90 dias (streak_max_default) impede multiplicadores runaway no Q_HE composite: depois de 3 meses, o bônus marginal de sequência é zero. Isso bate com achados empíricos sobre platôs de hábitos sustentáveis.

## §4 — Referências cruzadas (consumidores downstream)

- **Axioma 02** — base matemática (decaimento exponencial)
- **13-engine-habit-engine** — implementa `compute_habit_level(λ, streak)`
- **15-meta-ikigai-5-vector-scoring** — vetor paixão usa `(1 − e^(−λ · streak)) · 100`
- **23-meta-qhe-policy-mapping** — peso 0.20 sobre hábito de meditação no Q_HE do IKIGAi

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/habit_engine.py` — `compute_habit_level`, `compute_efficiency_ratio`
- `src/ikigai/src/ikigai/constants.py` — `LAMBDA = 0.093`
- `src/operational/docs/adr/PRD-CORE-HABIT-ENGINE.md` §4.1 — derivação matemática completa
- `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` §9.2 — rationale do λ padrão
- Lally, P., van Jaarsveld, C. H. M., Potts, H. W. W., & Wardle, J. (2010). *How are habits formed: Modelling habit formation in the real world*. European Journal of Social Psychology, 40(6), 998–1009.
