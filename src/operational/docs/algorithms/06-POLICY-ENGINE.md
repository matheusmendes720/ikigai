# 06 — Policy Engine (PUSH / MAINTAIN / REDUCE / RECOVER)

The **policy engine** is the cybernetic **adjuster** of the system.
It reads the day's QHE + energy + infraction count, applies the
hysteresis rules, and emits a `PolicyDecision` that the daily
handler must respect. The 4 regimes form a finite state machine
with **asymmetric hysteresis**: a faster decay than upgrade so the
system reacts quickly to overload and slowly to windfall.

## The 4 regimes

From `enums.PolicyState` (`enums.py:465-580`):

| Regime | Ordinal | Type | `hardwork_hudget_hours` | `max_pomodoros_per_day` | `sleep_target_hours` | `qhe_target` | `break_minutes` | `allowed_phases` |
|--------|---------|------|------------------------|------------------------|----------------------|--------------|-----------------|------------------|
| `PUSH` | 0 | productive | 8.0 | 10 | 7.0 | 0.85 | 10 | DEEP_WORK, SHALLOW_WORK |
| `MAINTAIN` | 1 | productive | 6.0 | 8 | 8.0 | 0.75 | 10 | DEEP_WORK, SHALLOW_WORK |
| `REDUCE` | 2 | protective | 4.0 | 5 | 8.0 | 0.65 | 15 | SHALLOW_WORK, RECOVERY |
| `RECOVER` | 3 | protective (hard stop) | 2.0 | 2 | 9.0 | 0.50 | 20 | RECOVERY |

The **product / preserve trade-off**:

* **PUSH** = max output, accept fatigue, sleep is sacrificed to
  7 h.
* **MAINTAIN** = steady state, balanced sleep at 8 h.
* **REDUCE** = protect recovery, cut deep work, allow shallow
  work and recovery blocks.
* **RECOVER** = hard stop. Only `RECOVERY` phase is allowed. 2 h
  of hard work maximum, 2 pomodoros maximum, sleep pushed to 9 h.

## Hysteresis

The FSM uses **asymmetric hysteresis** to avoid flapping between
adjacent states on noisy QHE readings. From
`core/policy_engine.py:1-65` and `entities/policy.py:30-32`:

* **Upgrade** (toward PUSH) — requires `QHE ≥ push threshold`
  for **3 consecutive days** (`POLICY_UPGRADE_DAYS = 3`).
* **Downgrade** (toward RECOVER) — requires `QHE < recover
  threshold` for **2 consecutive days** (`POLICY_DOWNGRADE_DAYS = 2`).
* **Emergency RECOVER entry** — fires **immediately** (no
  hysteresis) when either:
  * `infraction_count ≥ 3` (Points_of_premisses §4), **or**
  * `QHE < 0.30` (critical cutoff, also from Points_of_premisses §4).
* The **one-step rule** is enforced by `PolicyState.can_step_to`
  (`enums.py:567-580`): a direct PUSH → RECOVER jump is **not**
  allowed; the FSM must traverse MAINTAIN / REDUCE first. The
  emergency entry is the only path that bypasses this.

The decision logic is implemented in `core/policy_engine.py` (see
the module docstring at lines 1-65 for the full transition table).

## Thresholds

From `constants.py:124-153`:

| Constant | Value | Meaning |
|----------|-------|---------|
| `QHE_PUSH_THRESHOLD` | `0.85` | QHE ≥ this value → PUSH candidate |
| `QHE_RECOVER_THRESHOLD` | `0.60` | QHE < this value → RECOVER candidate |
| `POLICY_UPGRADE_DAYS` | `3` | Consecutive days to upgrade |
| `POLICY_DOWNGRADE_DAYS` | `2` | Consecutive days to downgrade |
| `POLICY_RECOVER_ENTRY_DAYS` | `1` | Days to enter RECOVER from non-protective |
| `LAMBDA_LEARNING_DEFAULT` | `0.093` | QHE learning rate (informational) |
| `QHE_ALPHA / BETA / GAMMA` | `0.45 / 0.35 / 0.20` | Alternative weighted QHE form |

The invariants in `constants.py:220-225` enforce
`QHE_PUSH_THRESHOLD > QHE_RECOVER_THRESHOLD`.

The **emergency RECOVER entry** uses two extra constants from
`core/policy_engine.py:100-108`:

* `_RECOVER_QHE_CRITICAL = 0.30` — single-day cutoff.
* `_RECOVER_INFRACTION_THRESHOLD = 3` — three or more violations
  of the routine.

## `PolicyState` enum — `enums.py:465-580`

| Property | Returns |
|----------|---------|
| `ordinal` | 0 (PUSH), 1 (MAINTAIN), 2 (REDUCE), 3 (RECOVER) |
| `is_protective` | True for REDUCE, RECOVER |
| `is_productive` | True for PUSH, MAINTAIN |
| `is_critical` | True only for RECOVER |
| `can_step_to(target)` | True iff `abs(self.ordinal - target.ordinal) == 1` |

The enum also defines full ordering (`__lt__`, `__le__`, `__gt__`,
`__ge__`) based on `ordinal`, so `PolicyState.PUSH < PolicyState.RECOVER`.

## `PolicySetpoints` — `entities/policy.py:95-263`

The Pydantic entity that bundles the regime's setpoints:

| Field | Type | Constraint |
|-------|------|------------|
| `id` | `UEID` | — |
| `state` | `PolicyState` | — |
| `hardwork_budget_hours` | `float` | `[0.0, 16.0]` |
| `max_pomodoros_per_day` | `int` | `[0, 12]` |
| `sleep_target_hours` | `float` | `[4.0, 10.0]` |
| `qhe_target` | `float` | `[0.0, 1.0]` |
| `break_minutes` | `int` | `[1, 30]` |
| `allowed_phases` | `list[Literal["DEEP_WORK", "SHALLOW_WORK", "RECOVERY"]]` | non-empty (validated) |
| `description` | `str` | 0-200 chars |
| `created_at` | `datetime` | — |

**Cross-field invariant** (`entities/policy.py:149-169`):
`allowed_phases` must be non-empty. This guarantees the daily
handler always has a well-defined set of phases to choose from.

## `PolicySetpoints.from_pav_defaults(state)` — `entities/policy.py:172-263`

The factory that returns the canonical setpoints for a given
state. The full table (verbatim from the code, lines 206-255):

| State | `hardwork_budget_hours` | `max_pomodoros_per_day` | `sleep_target_hours` | `qhe_target` | `break_minutes` | `allowed_phases` |
|-------|------------------------|------------------------|----------------------|--------------|-----------------|------------------|
| PUSH | 8.0 | 10 | 7.0 | 0.85 | 10 | DEEP_WORK, SHALLOW_WORK |
| MAINTAIN | 6.0 | 8 | 8.0 | 0.75 | 10 | DEEP_WORK, SHALLOW_WORK |
| REDUCE | 4.0 | 5 | 8.0 | 0.65 | 15 | SHALLOW_WORK, RECOVERY |
| RECOVER | 2.0 | 2 | 9.0 | 0.50 | 20 | RECOVERY |

The description is auto-generated and exposes the values in
prose. Any field can be overridden via `**overrides` — useful
for tests and A/B experiments.

## `PolicyDecision` — `entities/policy.py:271-443`

The Pydantic entity that records **one** decision for **one**
date. This is what the policy engine emits.

| Field | Type | Meaning |
|-------|------|---------|
| `id` | `UEID` | `"pol_<12 hex>"` |
| `date` | `date` | Decision date |
| `state` | `PolicyState` | The chosen state |
| `severity` | `Literal["INFO", "WARNING", "CRITICAL"]` | Tier |
| `rationale` | `str` | 0-500 chars |
| `setpoints` | `PolicySetpoints` | Active setpoints (must match `state`) |
| `days_in_state` | `int` | Consecutive days in current state |
| `previous_state` | `PolicyState \| None` | Prior state, `None` for first record |
| `qhe_input` | `float \| None` | QHE at the moment of the decision |
| `energy_input` | `EnergyLevel \| None` | Self-reported energy |
| `infraction_count` | `int` | Number of violations triggering this decision |
| `created_at` | `datetime` | When the decision was constructed |
| `applied` | `bool` | Whether the setpoints have been pushed to the daily handler |
| `applied_at` | `datetime \| None` | When `applied` flipped to True (auto-filled) |

**Cross-field invariants** (`entities/policy.py:340-362`):

* `setpoints.state` must equal `state` (no state/setpoint mix-ups).
* `applied_at` is auto-filled when `applied=True` without a
  timestamp (`_validate_applied_at`, lines 364-381).

**Severity mapping** (deterministic):

* Entry into `RECOVER` → `CRITICAL`.
* Entry into `REDUCE` → `WARNING`.
* Everything else → `INFO`.

The factory `PolicyDecision.from_state(...)`
(`entities/policy.py:383-443`) wires the matching setpoints
automatically. `overrides` can tweak any other field except
`setpoints` (always derived from `state`).

## `DecisionRecord` — `entities/policy.py:451-565`

The **append-only audit log** entry. Every successful state
change in the policy engine produces exactly one record. The
record is **immutable** (`frozen=True`); corrections are made
by writing a new record.

| Field | Type | Meaning |
|-------|------|---------|
| `id` | `UEID` | `"rec_<12 hex>"` |
| `from_state` | `PolicyState \| None` | Prior state (`None` for the very first decision) |
| `to_state` | `PolicyState` | New state |
| `transition_date` | `date` | When the transition took effect |
| `days_in_previous_state` | `int` | Days spent in `from_state` |
| `trigger` | `str` | 0-200 chars — what triggered the transition |
| `qhe_at_transition` | `float \| None` | QHE at the moment of the transition |
| `created_at` | `datetime` | Wall-clock time the record was written |

**Invariant** (`entities/policy.py:497-517`): `from_state` and
`to_state` must differ. A record for "no change" is meaningless
and is rejected at construction.

## `PolicyEngine` — `core/policy_engine.py`

The stateful orchestrator that holds the decision history and the
transition log. Public surface:

| Symbol | Role |
|--------|------|
| `Severity` (`core/policy_engine.py:169-195`) | `INFO` / `WARNING` / `CRITICAL` subset |
| `PolicyEvaluation` (frozen dataclass) | Result of a single `evaluate_policy` call |
| `evaluate_policy(...)` | Pure FSM evaluation (no I/O) |
| `is_recover_entry_condition(...)` | Predicate: should we emergency-enter RECOVER? |
| `consecutive_days_above_threshold(...)` | Hysteresis helper |
| `consecutive_days_below_threshold(...)` | Hysteresis helper |
| `PolicyEngine` class | Stateful wrapper with `evaluate()`, `reset()`, history |

The pure functions (`evaluate_policy`, helpers) are the canonical
API and are also used by the `PolicyEngine` and by tests.
`PolicyEngine` adds:

* `evaluate(...)` — runs `evaluate_policy` and appends the
  result to history (capped at `max_history`).
* `reset()` — clears the history.

The engine respects the **one-step rule** at every transition:
PUSH → RECOVER is not allowed; the engine must step through
MAINTAIN / REDUCE. The only exception is the **emergency
entry** to RECOVER, which fires immediately on
`infraction_count >= 3` or `QHE < 0.30`.

## UI rendering

The policy state is rendered in two places:

1. **`build_quadrant_caption()`** — `ui/daily_report.py:193-203`
   — a `Text` showing the day's quadrant label.
2. **Policy cards** — composed inline in the daily report. The
   state emoji/color map lives in `ui/components.py:31-44`
   (`COLORS`); the severity-to-color map is in
   `ui/components.py:87-94` (`SEVERITY_COLOR`).
3. **`next_step_panel()`** — `ui/components.py:381-387` —
   renders the recommended action (e.g. "Reduzir distrações" for
   Q4, "Revisão urgente" for Q3).

There is no dedicated `policy_card()` helper in `ui/components.py`
at the time of writing; the cards are built per-call in
`ui/daily_report.py`.

## Examples

### Example 1 — PUSH day

* Day 1: QHE = 0.90, energy = HIGH, infractions = 0.
* `evaluate_policy(state=MAINTAIN, qhe=0.90, …)` → upgrade.
* Decision: `state=PUSH`, `previous_state=MAINTAIN`,
  `setpoints.from_pav_defaults(PUSH)`, `severity=INFO`,
  `rationale="QHE 0.90 ≥ 0.85 for 3 days"`.
* Setpoints applied: 8 h hard work, 10 pomodoros, 7 h sleep.

### Example 2 — REDUCE day

* Day 5: QHE = 0.62, energy = MEDIUM, infractions = 1.
* Below `QHE_PUSH_THRESHOLD` (0.85); only 1 day below
  `QHE_RECOVER_THRESHOLD` (0.60). One-step downgrade MAINTAIN →
  REDUCE is allowed.
* Decision: `state=REDUCE`, `previous_state=MAINTAIN`,
  `severity=WARNING`, rationale cites the energy drop.
* Setpoints: 4 h hard work, 5 pomodoros, 8 h sleep.

### Example 3 — RECOVER day (energy + infractions)

* Day 8: QHE = 0.55, energy = LOW, infractions = 3.
* `is_recover_entry_condition(qhe=0.55, infractions=3)` is
  **True** (3 ≥ 3). Emergency entry fires immediately.
* Decision: `state=RECOVER`, `previous_state=REDUCE`,
  `severity=CRITICAL`, rationale cites the triple violation.
* Setpoints: 2 h hard work, 2 pomodoros, 9 h sleep, only
  `RECOVERY` phase allowed.

### Example 4 — RECOVER day (critical QHE)

* Day 9: QHE = 0.28, energy = LOW, infractions = 0.
* `is_recover_entry_condition(qhe=0.28, infractions=0)` is
  **True** (0.28 < 0.30). Emergency entry fires.
* Decision: `state=RECOVER`, `previous_state=RECOVER` (no
  transition), `severity=INFO`, rationale cites the QHE
  critical threshold.
* A new `DecisionRecord` is **not** written because
  `from_state == to_state`; the engine emits a decision but
  does not append to the audit log.

## Tests

* `tests/unit/entities/test_policy.py` — `PolicySetpoints`
  validation (each canonical state, all fields, cross-field
  invariants, override behaviour),
  `PolicyDecision.from_state`, the
  `setpoints.state == state` invariant, the
  `applied_at` auto-fill, and `DecisionRecord` from-to
  distinctness.
* `tests/unit/core/test_policy_engine.py` — `evaluate_policy`
  (every transition path), `is_recover_entry_condition`,
  `consecutive_days_above_threshold`,
  `consecutive_days_below_threshold`, the one-step rule, the
  emergency RECOVER entry (infractions ≥ 3 and QHE < 0.30),
  the asymmetric hysteresis (3 days up vs 2 days down), and
  the `PolicyEngine` stateful wrapper with history.
