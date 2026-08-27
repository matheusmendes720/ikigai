# Algorithms — Master Index

The **Algorithmic Life OS — operational** project runs on **6 core algorithms**.
They are pure functions in `src/operational/core/` (plus a few formulas baked
into Pydantic entities in `src/operational/entities/`). They are
deterministic, mostly O(1), and side-effect-free — the cybernetic core
that turns daily behaviour into a self-correcting loop.

## Why algorithms matter

This is the **cybernetic core**. The whole product — Typer CLI, Rich UI,
SQLite persistence, Markdown reports — is a thin presentation layer
over the 6 formulas below. Every "daily report", every "policy
decision", every "habit streak" is, at heart, an evaluation of one of
these functions against today's data.

The algorithms implement the **Target — Sensor — Adjuster** loop
described in the PAV (Produtividade Algorítmica Visual) spec:

1. **Target** — what does an excellent day look like? (`classify_quadrant`, `PolicySetpoints.from_pav_defaults`).
2. **Sensor** — what did today actually produce? (`productivity_pct`, `efficiency_pct`, `compute_qhe`).
3. **Adjuster** — should the regime change? (`PolicyEngine.evaluate_policy`).

The cartesian-plane algorithm (`classify_quadrant`) is the canonical
**visual feedback channel**: it is what the user sees on screen. The
policy engine is the canonical **decision channel**: it is what
changes tomorrow's setpoints. The two are connected by the QHE
metric — the scalar value the user is optimising for.

## Algorithm catalog

| # | Name | Source | Complexity | Inputs | Output |
|---|------|--------|------------|--------|--------|
| 1 | **Cartesian plane** (productivity / efficiency / quadrant) | `core/budget.py:73-123` | O(1) | `(realizado, orcado)`, `(foco, total)`, `(x, y)` | percentages + `(Q-code, label, action)` |
| 2 | **Day-budget classifier** (orcado vs realizado) | `core/budget.py:18-46` | O(1) | `TipoDia` / `date` / `(realizado, orcado)` | minutes + 5-bucket label (`MUITO_ACIMA`…`MUITO_ABAIXO`) |
| 3 | **Sleep calculator** (duration, quality, matrix) | `core/sleep_calculator.py:170-309`, `entities/metric.py:154-174` | O(1) | bed-hour, wake-hour, quality-score 1-10 | hours, `QualityLabel`, boolean |
| 4 | **Habit engine** (Q_HE aggregator) | `entities/habit.py:30-37`, `core/habit_engine.py:198-535` | O(N) over habits | `HabitState[]`, `Habit[]`, energy_ratio, streak | `QHEMetrics` snapshot + regime |
| 5 | **Pomodoro machine** (state machine + session distribution) | `entities/pomodoro.py:48-176`, `core/pomodoro_machine.py:51-59`, `core/services.py:365-371` | O(1) | config, total count, state | next state, `(s1, s2, s3)` triple |
| 6 | **Policy engine** (PUSH / MAINTAIN / REDUCE / RECOVER FSM) | `entities/policy.py:95-263`, `core/policy_engine.py:100-535` | O(D) over D days of history | current state, QHE, energy, infractions | `PolicyDecision` + `DecisionRecord` |

(N = number of tracked habits, D = depth of the decision history used
for hysteresis, typically 3.)

## Algorithm dependency graph

```
                           ┌────────────────────────┐
                           │  daily handler (CLI)   │
                           └──────────┬─────────────┘
                                      │ orchestrates
              ┌───────────────────────┼────────────────────────┐
              ▼                       ▼                        ▼
   ┌──────────────────┐   ┌──────────────────┐    ┌────────────────────┐
   │ 2. Budget        │   │ 6. Policy engine │    │ 4. Habit engine    │
   │ classifier       │   │  (FSM, histerese)│    │  (Q_HE aggregator) │
   └────────┬─────────┘   └────────┬─────────┘    └─────────┬──────────┘
            │                      │                         │
            │ produces X (prod%)   │ reads QHE              │ produces QHE
            │ and Y (eff%)         │ and energy             │
            ▼                      │                         │
   ┌──────────────────┐            │                         │
   │ 1. Cartesian     │            │                         │
   │ plane            │            │                         │
   │ (quadrant class) │◀───────────┴─────────────────────────┘
   └────────┬─────────┘
            │ produces quadrant + label
            ▼
   ┌──────────────────┐         ┌──────────────────┐
   │  Rich UI         │         │ 5. Pomodoro      │
   │ (daily_report)   │         │ machine          │
   └──────────────────┘         └────────┬─────────┘
                                        │ produces (s1, s2, s3)
                                        ▼
                                ┌──────────────────┐
                                │  Rich UI         │
                                │ (pomodoros_grid) │
                                └──────────────────┘

   ┌──────────────────┐   (independent — runs in parallel to the main loop)
   │ 3. Sleep calc.   │
   │ (PAV §7 matrix)  │
   └──────────────────┘
```

Read this as: **the budget classifier and the habit engine feed into
the cartesian plane; the cartesian plane's quadrant is rendered by
the UI; the policy engine reads QHE + energy and emits regime
decisions; the pomodoro machine distributes total daily pomodoros
into the three sessions; sleep is computed independently.**

## Where to find tests

| Algorithm | Unit tests | Entity tests |
|-----------|-----------|--------------|
| Cartesian plane | `tests/unit/core/test_scenario_classifier.py`, `tests/core/test_services.py` (quadrant) | — |
| Budget classifier | `tests/core/test_services.py` (budget defaults) | — |
| Sleep calculator | `tests/unit/core/test_sleep_calculator.py` | `tests/unit/entities/test_metric.py` |
| Habit engine | `tests/unit/core/test_habit_engine.py` | `tests/unit/entities/test_habit.py` |
| Pomodoro machine | `tests/unit/core/test_pomodoro_plugin.py` | `tests/unit/entities/test_pomodoro.py` |
| Policy engine | `tests/unit/core/test_policy_engine.py` | `tests/unit/entities/test_policy.py` |

> Note: there is no `test_budget.py` file in the test tree — the
> cartesian-plane functions in `core/budget.py` are exercised
> indirectly through `test_scenario_classifier.py` and
> `test_services.py`.

## Per-algorithm documents

1. [`01-PRODUCTIVITY-PLANE.md`](01-PRODUCTIVITY-PLANE.md) — cartesian plane, quadrants Q1-Q4, infraction buckets.
2. [`02-BUDGET-CLASSIFIER.md`](02-BUDGET-CLASSIFIER.md) — day types, orcado vs realizado, day-type inference.
3. [`03-SLEEP-CALCULATOR.md`](03-SLEEP-CALCULATOR.md) — sleep duration, quality bands, PAV §7 decision matrix.
4. [`04-HABIT-ENGINE.md`](04-HABIT-ENGINE.md) — habit consolidation, energy required, QHE aggregator.
5. [`05-POMODORO-MACHINE.md`](05-POMODORO-MACHINE.md) — 7-state FSM, config, session distribution.
6. [`06-POLICY-ENGINE.md`](06-POLICY-ENGINE.md) — 4-regime FSM with hysteresis, setpoint table, decision record.
