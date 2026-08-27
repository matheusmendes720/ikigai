# 04 — Habit Engine (Q_HE Aggregator)

The **habit engine** is the heart of the daily quality metric. It
implements the three formulas from PRD-02 §3 verbatim, evaluates
them against the day's habit states, and produces a single
`QHEMetrics` snapshot that the policy engine then maps onto an
operational regime.

## The 3 formulas

From `entities/habit.py:30-37` (verbatim, with the same docstring
that the code uses):

```text
H(t)        = 1 - e^(-λ·s)               — habit consolidation
E_req       = R · (1 - H(t))              — energy required
Q_HE        = (Σ w_i H_i / Σ w_i)
              · (E/E_max)
              · (1 + η · S_bonus)         — quality-habit-effectiveness
```

where:

* `s` = consecutive-day streak (`streak_current` on
  `HabitState`).
* `λ` = learning rate (`Habit.lambda_learning`,
  `DEFAULT.LAMBDA_LEARNING_DEFAULT = 0.093`).
* `R` = resistance (`Habit.resistance`, range 0-10).
* `w_i` = relative weight (`Habit.weight_in_qhe`).
* `E/E_max` = energy ratio (`QHEMetrics.energy_ratio`, 0-1).
* `η` = streak-bonus multiplier (`QHEMetrics.eta`, default 0.5).
* `S_bonus = min(s_cur / s_max, 1.0)`.

### The aggregator

The QHE formula above is the **scalar** form. The codebase also
defines a more general **weighted average** in
`core/habit_engine.py:30`:

```text
QHE = H_avg · (E/E_max) · (1 + η · S_bonus)
```

where `H_avg = Σ w_i H_i / Σ w_i` is the weighted consolidation
across all contributing habits. Both forms are equivalent when
`Σ w_i = 1`.

The regime prediction is a **3-band** mapping (REDUCE is never
produced by the QHE predictor alone):

* `QHE >= QHE_PUSH_THRESHOLD` (= 0.85) → `PUSH`
* `QHE < QHE_RECOVER_THRESHOLD` (= 0.60) → `RECOVER`
* else → `MAINTAIN`

## Constants

| Constant | Value | Source | Meaning |
|----------|-------|--------|---------|
| `λ` (`LAMBDA_LEARNING_DEFAULT`) | `0.093` | `constants.py:152` | Default learning rate (ADR-003 / time-lengths §9.2) |
| `η` (`ETA_DEFAULT`) | `0.5` | `core/habit_engine.py:102` | Streak-bonus multiplier |
| `s_max` (`STREAK_MAX_DEFAULT`) | `90` | `core/habit_engine.py:98` | Days to "max streak" (90-day heuristic) |
| `QHE_PUSH_THRESHOLD` | `0.85` | `constants.py:146` | QHE >= 0.85 → PUSH |
| `QHE_RECOVER_THRESHOLD` | `0.60` | `constants.py:149` | QHE < 0.60 → RECOVER |
| `QHE_ALPHA / BETA / GAMMA` | `0.45 / 0.35 / 0.20` | `constants.py:137-144` | Alternative weighted QHE form (sum = 1.0) |
| `R` placeholder | `5.0` | `entities/habit.py:74` | Used by the `HabitState` computed fields when the parent `Habit` is not in scope |

The "streak bonus coefficient" in the docstring is η = 0.5 by
default. The form `(1 + η · S_bonus)` is the QHE **streak
multiplier**: with `S_bonus = 1.0` and `η = 0.5`, the multiplier
is `1.5` (50 % boost at the longest streaks).

## `HabitState` — `entities/habit.py:234-399`

The Pydantic entity that holds one day's state of one habit:

| Field | Type | Meaning |
|-------|------|---------|
| `id` | `UEID` | `"hst_<habit>_<yyyymmdd>"` |
| `habit_id` | `UEID` | FK to the parent `Habit` |
| `date` | `date` | The day this state refers to |
| `completed` | `bool` | Did the user do it? |
| `streak_current` | `int` ≥ 0 | Consecutive days (0+) |
| `streak_broken_count` | `int` ≥ 0 | Lifetime broken-streak count |
| `effort_minutes` | `int` ≥ 0 | Actual minutes spent |

**Computed fields** (use canonical default `λ = 0.093` and `R = 5.0`
when the parent `Habit` is not in scope):

| Field | Formula | Returns |
|-------|---------|---------|
| `habit_level` | `1 - e^(-0.093 · streak)` | `[0.0, 1.0)` |
| `energy_required` | `5.0 · (1 - habit_level)` | `[0.0, 10.0]` |
| `efficiency_ratio` | `habit_level / (1 + energy_required)` | `[0.0, 1.0]` |

Two factory methods exist for convenience: `for_completed(...)`
(`habit_id, on_date, *, streak_current=1, effort_minutes=0`) and
`for_missed(...)` (`habit_id, on_date, *, streak_current=0,
streak_broken_count=0`).

## `HabitEngine` — `core/habit_engine.py:543-667`

A stateless OO wrapper around the module-level functions. It holds
two config parameters (`eta` and `max_streak`) and exposes the same
operations as methods:

| Method | What it does |
|--------|--------------|
| `compute_habit(lambda_learning, streak)` | → `float` (`H(t)`) |
| `compute_energy_required(resistance, habit_level)` | → `float` (`E_req`) |
| `compute_efficiency_ratio(habit_level, energy_required)` | → `float` |
| `compute_habit_avg(habit_states, habits)` | → `float` (`H_avg`) |
| `compute_consistency(habit_states)` | → `float` |
| `compute_streak_bonus(current_streak, max_streak=90)` | → `float` |
| `compute_qhe(habit_states, habits, energy_ratio, current_streak, eta=0.5, max_streak=90)` | → `QHEMetrics` |
| `compute_habit(habit, streak)` | → `HabitComputation` (per-habit snapshot) |
| `predict_regime_from_qhe(qhe_value)` | → `PolicyState` (3-band) |

The aggregator at `compute_habit_avg()` (`core/habit_engine.py:314-361`)
silently **skips** three classes of states:

1. States whose `habit_id` is not present in the `habits` list.
2. Habits with `archived = True`.
3. States where the parent habit has `weight_in_qhe == 0`.

This means the formula is always a true weighted average of the
**active** habit population, and re-archiving a habit does not
contaminate tomorrow's QHE.

## Examples

### Example 1 — fresh habit, streak 0

* `R = 7` (high), `λ = 0.093`, `streak_current = 0`.
* `H(0) = 1 - e^0 = 0.0` (no consolidation).
* `E_req = 7 · 1.0 = 7.0` (full cost).
* `eff = 0.0 / 8.0 = 0.0`.

A brand-new high-resistance habit costs the full resistance
budget. Streak bonuses (`S_bonus = 0`) contribute nothing.

### Example 2 — established habit, streak 30

* `R = 5`, `λ = 0.093`, `streak_current = 30`.
* `H(30) = 1 - e^(-0.093 · 30) = 1 - e^(-2.79) ≈ 0.938`.
* `E_req = 5 · (1 - 0.938) = 0.310` (almost free).
* `eff = 0.938 / 1.310 ≈ 0.716`.

A 30-day streak reduces the energy cost to a third and lifts
efficiency into the 0.7+ band.

### Example 3 — well-consolidated habit, streak 90

* `R = 3`, `λ = 0.093`, `streak_current = 90`.
* `H(90) = 1 - e^(-0.093 · 90) = 1 - e^(-8.37) ≈ 0.99977`.
* `E_req = 3 · (1 - 0.99977) ≈ 0.0007` (effectively zero).
* `eff ≈ 1.0`.

The 90-day "habit-formation" milestone: at this point the habit
is automatic and the energy cost is negligible.

### Example 4 — QHE aggregator (3 habits)

| Habit | `w_i` | `streak` | `H(t)` |
|-------|-------|----------|--------|
| Sleep 8 h | 0.4 | 14 | `1 - e^(-1.302) ≈ 0.728` |
| Workout | 0.3 | 7 | `1 - e^(-0.651) ≈ 0.478` |
| Read 30 min | 0.3 | 0 | `0.000` |

* `H_avg = (0.4·0.728 + 0.3·0.478 + 0.3·0.000) / 1.0 ≈ 0.435`.
* Consistency (3/3 done) = `1.0`.
* `S_bonus = 0.0` (max streak 0).
* With `E/E_max = 0.8`:
  `QHE = 0.435 · 0.8 · (1 + 0.5 · 0.0) = 0.348`.
* `predict_regime_from_qhe(0.348) = RECOVER` (< 0.60).

## Edge cases

* **`w` sum ≠ 1** — the formula is still well-defined (the
  `Σ w_i` denominator normalises it), but the result will not be
  in the canonical `[0, 1]` range. The codebase enforces the
  sum-to-one convention via the `QHE_ALPHA / BETA / GAMMA`
  constants and their tolerance check in
  `constants.py:211-219`.
* **Empty `habit_states`** — `compute_habit_avg` returns `0.0`,
  `compute_consistency` returns `0.0`, and `compute_qhe` produces
  a `QHEMetrics` with `habit_avg = 0.0`. The predicted regime is
  `RECOVER` by default.
* **`E/E_max = 0`** (no energy reported) — `QHE = 0`, regime
  `RECOVER`. The aggregator never throws on `energy_ratio = 0`.
* **Negative streak** — `compute_habit_level` and
  `compute_streak_bonus` raise `ValueError`. The Pydantic
  constraint `Field(ge=0)` on `HabitState.streak_current` makes
  this unreachable through the entity layer.
* **`lambda_learning = 0`** — `compute_habit_level` returns
  `0.0` (degenerate case, the habit never consolidates). The
  constraint `Field(ge=0.0, le=1.0)` allows it; the constant
  validation in `constants.py:249-259` rejects `λ ≥ 0` from the
  default layer (must be in `(0, 1]`).
* **R out of range** — `compute_energy_required` raises
  `ValueError`. Pydantic `Field(ge=0.0, le=10.0)` on
  `Habit.resistance` prevents this through the entity layer.

## Tests

* `tests/unit/core/test_habit_engine.py` — every formula edge
  case, the `HabitEngine` class, regime prediction, and the
  `for_completed` / `for_missed` factories.
* `tests/unit/entities/test_habit.py` — `Habit`, `HabitState`,
  `QHEMetrics` validation, computed fields, factory methods.
