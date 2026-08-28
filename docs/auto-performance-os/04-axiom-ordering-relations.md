# 04 — Axiom: Ordering Relations & Monotonicity

> **Category:** §1 Axiomatic base
> **Audience:** Self + future agents
> **Source material:** habit_engine.py monotonicity tests, PRD-CORE-POLICY-CONSOLIDATOR §4.4 hysteresis

---

## §1 — Plain-language intuition

Some things can be **ordered**; others can't. A streak of 30 days is "more than" a streak of 10. But "I want to be an engineer" and "I want to be a designer" don't have a clear ordering — they're just different. **Partial orders** capture "ordered enough" without forcing total comparisons; **monotonicity** is the property that "more input → more output" (or vice versa).

## §2 — Formal statement

A **partial order** `(≤)` on a set `S` satisfies three axioms:

| Axiom | Statement |
|:------|:----------|
| Reflexivity | `a ≤ a` for all `a ∈ S` |
| Antisymmetry | if `a ≤ b` and `b ≤ a` then `a = b` |
| Transitivity | if `a ≤ b` and `b ≤ c` then `a ≤ c` |

A **total order** additionally requires **comparability**: for all `a, b ∈ S`, either `a ≤ b` or `b ≤ a`.

A function `f: S → T` is **monotonically non-decreasing** in `x` iff `x ≤ y ⟹ f(x) ≤ f(y)`.

## §3 — Non-technical rationale

The system needs to track "did this get better or worse" over time. That's **monotonicity** — a partial order on the metric space. Concretely:

- **QHE** is monotonically non-decreasing in `H_avg` (more habits done → higher QHE) and in `E/E_max` (more energy → higher QHE)
- **H(t)** is monotonically non-decreasing in streak `t` (longer streak → more consolidation) and in learning rate `λ`
- **Efficiency ratio** is monotonically non-decreasing in `H(t)` for fixed `R`
- **Time** is a total order (any two days have a clear ordering)

This guarantees the system responds **predictably** to user actions: do more habits → QHE goes up; sleep more → energy goes up. If the math were non-monotonic, small improvements could paradoxically make the score worse — breaking user trust.

In the policy FSM, **asymmetric hysteresis** (3 days to upgrade, 2 to downgrade) is a partial-order property on regime transitions: the system requires stronger evidence to promote than to demote. This biases the system toward caution, which matters when recommendations change the user's day.

## §4 — Cross-references (downstream consumers)

- **13-engine-habit-engine** — every function has monotonicity proofs in tests
- **14-engine-policy-engine-fsm** — asymmetric hysteresis = partial-order on regime transitions
- **16-meta-regime-fsm** — IKIGAi 4-state FSM with same hysteresis pattern
- **All scoring engines** — QHE, vectors, RICE: monotonic in their inputs

## §5 — Sources

- `src/operational/packages/core/src/operational/core/habit_engine.py` — monotonicity tests (parametric over `H(s)` and `efficiency(H)`)
- `src/operational/docs/adr/PRD-CORE-HABIT-ENGINE.md` §4.1 — `H(s)` properties (H(0)=0, H(∞)→1, monotonic)
- `src/operational/docs/adr/PRD-CORE-POLICY-CONSOLIDATOR.md` §4.4 — "asymmetric histerese" design rationale
- `src/ikigai/src/ikigai/core/heuristics/regime.py` — IKIGAi hysteresis constants `HYSTERESIS_UPGRADE_DAYS=3`, `HYSTERESIS_DOWNGRADE_DAYS=2`
- Davey, B. A., & Priestley, H. A. (2002). *Introduction to Lattices and Order*. 2nd ed. Cambridge University Press.