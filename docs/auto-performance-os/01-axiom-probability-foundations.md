# 01 — Axiom: Probability Foundations

> **Category:** §1 Axiomatic base
> **Audience:** Self + future agents
> **Source material:** habit_engine.py `EnergyLevel` map, IKIGAi vector scoring, PAV §6 energy model

---

## §1 — Plain-language intuition

Some measurements are noisy. A user reports "HIGH energy" today, but the underlying signal could be anywhere from 70 to 95. We need a way to talk about **expectations** without knowing the exact outcome — that's what expected value gives us. **Variance** then tells us how much the answer can wobble.

## §2 — Formal statement

For a discrete random variable X with values {xᵢ} and probabilities {pᵢ}:

```
E[X]   = Σᵢ pᵢ · xᵢ
Var(X) = E[(X − E[X])²] = E[X²] − (E[X])²
```

For continuous X with density f(x):

```
E[X] = ∫ x · f(x) dx
Var(X) = ∫ (x − E[X])² · f(x) dx
```

Conditional probability: `P(A|B) = P(A ∩ B) / P(B)`.

## §3 — Non-technical rationale

Imagine your self-reported energy as a noisy gauge. You say "HIGH" today, but yesterday you said "MEDIUM" even though both days felt similar. The system treats HIGH/MEDIUM/LOW as discrete tiers mapped to {1.0, 0.6, 0.3} ratios — that's a **quantized expected value** under the user's reporting noise. Even an imprecise reading has a useful average; variance just reminds us that the answer can wobble.

This is why the system can act on a single daily reading: we trust the **expected value** is close to the true signal even if we can't observe it directly.

## §4 — Cross-references (downstream consumers)

- **06-postulate-habit-momentum** — uses E/E_max as the energy term of QHE
- **13-engine-habit-engine** — maps `EnergyLevel` enum to ratio via discrete distribution
- **15-meta-ikigai-5-vector-scoring** — 5 vectors each aggregate noisy per-habit signals

## §5 — Sources

- `src/operational/packages/core/src/operational/core/habit_engine.py` — `EnergyLevel` → ratio map
- `src/ikigai/src/ikigai/core/scoring/vector_scores.py` — 5-vector expected-value scoring
- `src/operational/docs/adr/PRD-CORE-HABIT-ENGINE.md` §4.5 — streak-bonus distribution
- `vibe-ops/base/Produtividade Algorítmica Visual.md` §6 — energy model derivation