# observe — Q_HE Regime + Workload Balancer

The `observe` node (`src/ikigai/src/agents/v2/nodes/observe.py`) is the
entry point of the IKIGAi v2 graph. It reads sensor state and decides
**regime** (PUSH / MAINTAIN / RECOVER) plus **balancer verdict** (OK /
OVERLOAD / UNDERLOAD / RECOVER). This document is the canonical
prompt-template specification of how those decisions are made.

Per **ADR-019** (forthcoming — see `dcode-harness-TASKS.md` W5.2),
algorithm tuning happens ONLY by editing the JSON values listed in
section "Tunable Constants" below. Drift detector
(`src/ikigai/tests/test_canonical_scope.py :: test_no_algorithm_constants_in_agent_code`)
forbids new Python `DEFAULT_*` constants in `src/ikigai/src/agents/v2/*.py`.

---

## Decision Rules (read by the LLM context; see observe_qhe_observation prompt)

### Regime FSM (Q_HE → regime)

```text
Q_HE ≥ QHE_PUSH_THRESHOLD (0.85)        → PUSH
Q_HE_RECOVER_THRESHOLD (0.60) ≤ Q_HE < QHE_PUSH_THRESHOLD (0.85)  → MAINTAIN
Q_HE < QHE_RECOVER_THRESHOLD (0.60)     → RECOVER
```

Note: the regime FSM is **not** the same as `REDUCE`. `REDUCE` is a
downgrade step triggered by hysteresis logic in `balance.py`, not a
direct function of `Q_HE`.

### Balancer Verdict (Q_HE + workload_ratio)

```text
if Q_HE < QHE_RECOVER_THRESHOLD (0.60)             → RECOVER
elif workload_ratio ≥ WORKLOAD_OVERLOAD_FACTOR (1.20) → OVERLOAD
elif workload_ratio ≤ WORKLOAD_UNDERLOAD_FACTOR (0.50) → UNDERLOAD
else                                                → OK
```

`workload_ratio` is computed in `observe.py:64` as
`workload_estimate / max(capacity_estimate, 1.0)`.

### Capacity Estimate

`capacity_estimate = CAPACITY_HOURS_PER_DAY (8.0)` — currently a constant,
but a future prompt-template can override per-user (per ADR-019).

---

## Tunable Constants (single source of truth: `prompts/algorithm_constants.json`)

| Key                              | Default | Used in                  | Meaning                                  |
|----------------------------------|---------|--------------------------|------------------------------------------|
| `QHE_PUSH_THRESHOLD`             | 0.85    | observe.py:56, heuristics:74 | Q_HE ≥ this → PUSH regime              |
| `QHE_RECOVER_THRESHOLD`          | 0.60    | observe.py:58,65; balance.py:47,70 | Q_HE < this → RECOVER; else MAINTAIN |
| `WORKLOAD_OVERLOAD_FACTOR`       | 1.20    | observe.py:67, balance.py:49,81 | workload_ratio ≥ this → OVERLOAD     |
| `WORKLOAD_UNDERLOAD_FACTOR`      | 0.50    | observe.py:69, balance.py:51 | workload_ratio ≤ this → UNDERLOAD      |
| `CAPACITY_HOURS_PER_DAY`         | 8.0     | observe.py:53              | default capacity estimate                |
| `HYSTERESIS_UPGRADE_DAYS`        | 3       | balance.py:58             | days before MAINTAIN→PUSH promotion      |
| `HYSTERESIS_DOWNGRADE_DAYS`      | 2       | balance.py:60             | days before PUSH→MAINTAIN demotion       |
| `REGIME_TARGETS`                 | dict    | heuristics.py:74          | per-regime Q_HE targets for H2 deviation |
| `HEURISTICS_H2_DEVIATION_WARN`   | 0.15    | heuristics.py:77          | H2 deviation that triggers a warning     |
| `HEURISTICS_H2_DEVIATION_CRITICAL` | 0.30  | heuristics.py:84          | H2 deviation that triggers critical      |
| `HEURISTICS_H3_MAINTAIN_UPGRADE_DAYS` | 14 | heuristics.py:101     | H3 days in MAINTAIN before upgrade cue  |
| `HEURISTICS_H3_PUSH_QHE_THRESHOLD` | 0.80  | heuristics.py:106        | H3 Q_HE cutoff to consider PUSH upgrade  |
| `HEURISTICS_H3_PUSH_DOWNGRADE_DAYS` | 10   | heuristics.py:112        | H3 days in PUSH before downgrade cue     |
| `HEURISTICS_H6_SEVERITY_WARN`    | 0.5     | heuristics.py:137         | H6 severity threshold for warning        |
| `HEURISTICS_H6_SEVERITY_CRITICAL` | 1.0    | heuristics.py:144         | H6 severity threshold for critical      |

---

## Tuning Workflow (per ADR-019)

1. Edit `algorithm_constants.json` with the new values.
2. (Optional) Update this `observe.md` to reflect the new semantics.
3. Run `pytest src/ikigai/tests/test_algorithm_constants_migration.py -v`.
4. Run `pytest src/ikigai/tests/test_canonical_scope.py -v` — must still pass.
5. Reference the SONHO log that motivated the change in the commit body.

NEVER introduce new `DEFAULT_*` constants in `agents/v2/*.py`. If a value
seems algorithm-tunable, add it to `algorithm_constants.json` instead.
