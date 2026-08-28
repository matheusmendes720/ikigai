# 02 — Axioma: Decaimento / Crescimento Exponencial

> **Categoria:** §1 Base axiomática
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** `compute_habit_level` em habit_engine.py, scoring Q_HE do IKIGAi, Lally et al. (2010)

---

## §1 — Intuição em linguagem simples

A primeira vez que você faz algo, custa muito esforço. A décima vez, custa menos. A centésima, quase nada. A curva de "quão difícil isto parece" **se aplaina** — nunca chega a zero, mas se aproxima. Isso é aproximação exponencial.

## §2 — Enunciado formal

```
H(t) = 1 − exp(−λ · t)
```

onde:

| Símbolo | Tipo    | Faixa      | Significado                  |
|:-------:|:-------:|:----------:|:-----------------------------|
| `λ`     | `float` | `[0, 1]`   | Taxa de aprendizado (por dia)|
| `t`     | `int`   | `[0, ∞)`   | Sequência (dias consecutivos)|

**Propriedades:**
- `H(0) = 0` (sem sequência, sem consolidação)
- `H(∞) → 1` (consolidação plena, assíntota)
- `H(t) ∈ [0, 1)` para todo `t ≥ 0`, `λ > 0`
- Monotonicamente não-decrescente em `t` para `λ` fixo
- Monotonicamente não-decrescente em `λ` para `t ≥ 0` fixo

## §3 — Justificativa não-técnica

Hábitos não se formam de modo linear — formam-se com **retornos decrescentes**. O dia 1 é difícil; o dia 7 é muito mais fácil; o dia 90 vs o dia 91 quase não difere. O decaimento exponencial captura essa forma: ganhos rápidos no início (quando a novidade é alta e a fricção é baixa) seguidos de uma assíntota lenta (onde repetições adicionais produzem reduções cada vez menores na carga cognitiva).

No nosso sistema, `λ = 0.093 dia⁻¹` (do ADR-003 §9.2). Isso dá `H(90) ≈ 0.9998` — efetivamente consolidado em 90 dias. A escolha bate com Lally et al. (2010), cujo tempo mediano até a automaticidade foi de 66 dias em 96 participantes formando novos hábitos na vida cotidiana.

## §4 — Referências cruzadas (consumidores downstream)

- **06-postulado-habit-momentum** — claim de domínio construído sobre este axioma
- **13-engine-habit-engine** — implementa `compute_habit_level(λ, streak)`
- **15-meta-ikigai-5-vector-scoring** — vetor paixão usa `(1 − e^(−λ · streak)) · 100`
- **23-meta-qhe-policy-mapping** — Q_HE do IKIGAi = 0.35·H_sono + 0.20·H_med + 0.25·H_workout + 0.10·H_lunch + 0.15·S_streak (cada Hᵢ ∈ [0,1] desta forma)

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/habit_engine.py` — `compute_habit_level`
- `src/ikigai/src/ikigai/core/scoring/qhe.py` — curva de aprendizado de hábito do IKIGAi
- `src/ikigai/src/ikigai/constants.py` — `LAMBDA = 0.093` (NSM congelado)
- `src/operational/docs/adr/PRD-CORE-HABIT-ENGINE.md` §4.1 — derivação matemática completa
- `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` §9.2 — rationale do λ padrão
- Lally, P., van Jaarsveld, C. H. M., Potts, H. W. W., & Wardle, J. (2010). *How are habits formed: Modelling habit formation in the real world*. European Journal of Social Psychology, 40(6), 998–1009.
