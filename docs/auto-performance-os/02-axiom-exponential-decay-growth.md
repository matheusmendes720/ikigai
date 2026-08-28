# 02 — Axiom: Exponential Decay / Growth

> **Category:** §1 Axiomatic base
> **Audience:** Self + future agents
> **Source material:** habit_engine.py `compute_habit_level`, IKIGAi QHE scoring, Lally et al. (2010)

---

## §1 — Plain-language intuition

The first time you do something, it costs a lot of effort. The tenth time, less. The hundredth, almost nothing. The curve of "how hard does this feel" **flattens out** — it never quite reaches zero, but it gets close. That's exponential approach.

## §2 — Formal statement

```
H(t) = 1 − exp(−λ · t)
```

where:

| Symbol | Type | Range | Meaning |
|:------:|:----:|:-----:|:--------|
| `λ` | `float` | `[0, 1]` | Learning rate (per-day) |
| `t` | `int` | `[0, ∞)` | Streak (consecutive days) |

**Properties:**
- `H(0) = 0` (no streak, no consolidation)
- `H(∞) → 1` (full consolidation, asymptote)
- `H(t) ∈ [0, 1)` for all `t ≥ 0`, `λ > 0`
- Monotonically non-decreasing in `t` for fixed `λ`
- Monotonically non-decreasing in `λ` for fixed `t ≥ 0`

## §3 — Non-technical rationale

Habits don't form linearly — they form with **diminishing returns**. Day 1 is hard; day 7 is much easier; day 90 vs day 91 is barely different. Exponential decay captures this shape: rapid early gains (when novelty is high and friction is low) followed by slow asymptote (where additional repetitions yield smaller reductions in cognitive load).

In our system, `λ = 0.093 day⁻¹` (from ADR-003 §9.2). This gives `H(90) ≈ 0.9998` — effectively consolidated at 90 days. The choice matches Lally et al. (2010), whose median time-to-automaticity was 66 days across 96 participants forming new habits in everyday life.

## §4 — Cross-references (downstream consumers)

- **06-postulate-habit-momentum** — domain claim built on this axiom
- **13-engine-habit-engine** — implements `compute_habit_level(λ, streak)`
- **15-meta-ikigai-5-vector-scoring** — passion vector uses `(1 - e^(-λ · streak)) · 100`
- **23-meta-qhe-policy-mapping** — IKIGAi QHE = 0.35·H_sono + 0.20·H_med + 0.25·H_workout + 0.10·H_lunch + 0.15·S_streak (each Hᵢ ∈ [0,1] from this shape)

## §5 — Sources

- `src/operational/packages/core/src/operational/core/habit_engine.py` — `compute_habit_level`
- `src/ikigai/src/ikigai/core/scoring/qhe.py` — IKIGAi habit-learning curve
- `src/ikigai/src/ikigai/constants.py` — `LAMBDA = 0.093` (frozen NSM)
- `src/operational/docs/adr/PRD-CORE-HABIT-ENGINE.md` §4.1 — full mathematical derivation
- `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` §9.2 — λ default rationale
- Lally, P., van Jaarsveld, C. H. M., Potts, H. W. W., & Wardle, J. (2010). *How are habits formed: Modelling habit formation in the real world*. European Journal of Social Psychology, 40(6), 998–1009.