---
name: M175-paperclip-wall-clock-gate
description: Wall-clock auto-throttle #2 — refuses agent invocation when task > threshold (default 3600s = 1h). Parallels CostGate.
status: DONE
owner: matheus-mendes
created: 2026-10-11
constitution_refs:
  - tests_are_the_contract
  - state_on_disk_not_conversation
  - composition_over_inheritance
estimated_cost_usd: 0.00
---

# M175 — Paperclip Wall-Clock Gate (Auto-Throttle #2)

**Status:** DONE
**Date:** 2026-10-11
**Author:** matheus-mendes (with Claude Code assist)

---

## TL;DR

M175 adds a **wall-clock gate** as the second auto-throttle in the
Paperclip architecture, complementing `CostGate` (M173). The gate refuses
to invoke the AI agent if a Paperclip task has been running for more
than a configured duration (default **3600s = 1 hour**, override via
env `PAPERCLIP_WALL_CLOCK_THRESHOLD_S`). The gate is **fail-open** when
timing data is missing or malformed — same invariant as the cost gate.
Drift net grows **72 → 73** (+1 new invariant).

The wall-clock gate complements the cost gate by catching a different
failure mode:

| Gate | Catches |
|---|---|
| `CostGate` (M173) | Daily spend is over budget — burn-rate ceiling. |
| `WallClockGate` (M175) | Single task has been running too long — runaway / infinite-retry ceiling. |

Both gates consult `state[]` (or filesystem) and refuse to invoke the
agent when the corresponding ceiling is exceeded; the graph surfaces
`error_type="CostGateExceeded"` or `error_type="WallClockGateExceeded"`
to the operator for triage.

---

## What changed

```
src/ikigai/src/agents/paperclip/policy.py          # +WallClockGate, +2 constants
src/ikigai/src/agents/paperclip/state.py           # +task_started_at field
src/ikigai/src/agents/paperclip/nodes/read_spec.py # sets task_started_at
src/ikigai/src/agents/paperclip/nodes/implement.py # consults WallClockGate after CostGate
src/ikigai/src/agents/paperclip/tests/test_wall_clock_gate.py  # NEW (5 tests)
src/ikigai/tests/test_paperclip_drift.py           # +1 drift invariant
.claude/loop/roadmap.md                            # +M175 entry
specs/M175-paperclip-wall-clock-gate/SPEC.md       # this file
```

**Total: 1 new test file + 5 modified files. Drift net 72 → 73.**

The `CostGate` class is **untouched** — `WallClockGate` is appended to
`policy.py` at module-bottom and re-exported via `__all__`. The two
gates coexist; node `implement.py` calls them sequentially (cost first,
wall-clock second).

---

## Architecture decisions

### D9 — Wall-clock gate is independent from cost gate (complementary, not entangled)

The wall-clock gate reads **state** (`state["task_started_at"]`); the
cost gate reads **filesystem** (`data/cost-today.json`). They share no
state, no env var, and no I/O path. This means:

* A future milestone can disable one without affecting the other
  (`PAPERCLIP_COST_THRESHOLD_USD=99999` to effectively disable the cost
  gate; `PAPERCLIP_WALL_CLOCK_THRESHOLD_S=999999` to effectively disable
  the wall-clock gate).
* Tests exercise the gates in isolation — no fixture pollution between
  `test_cost_gate.py` and `test_wall_clock_gate.py`.

Rejected: a single "policy.py" facade with `check_all()` orchestrating
both gates. The split-by-concern keeps each gate testable in 5 focused
unit tests and lets callers reason about each independently.

### D10 — Fail-open when `task_started_at` is missing

If `state["task_started_at"]` is `None`, missing, or unparseable ISO
8601, the gate returns `allowed=True` with a descriptive reason. The
rationale is identical to the cost gate's fail-open story: older
clients (pre-M175) and replayed checkpoints may not carry the field,
and breaking the Paperclip graph because a field is missing is the
wrong default.

The drift test (`test_paperclip_wall_clock_gate_exists`) verifies the
default `threshold_seconds=3600` so a builder who forgets to pass a
threshold gets the documented default — not a sentinel error or a
silent coercion to `0`.

### D11 — Threshold from env, captured at `__init__`

`PAPERCLIP_WALL_CLOCK_THRESHOLD_S` (int, seconds). Read once at
`WallClockGate.__init__` so the value is captured in the gate instance
— tests that mutate the env get a fresh gate. Invalid values
(non-int, negative) fall back silently to `DEFAULT_THRESHOLD_S=3600`
with a `log.warning` so the operator can spot misconfiguration.

---

## Verification

```bash
# 1. Wall-clock gate tests — must show 5/5 PASS
python -m pytest src/ikigai/src/agents/paperclip/tests/test_wall_clock_gate.py -v

# 2. Full paperclip suite + drift — must show 43 PASS (37 prior + 5 new + 1 drift)
python -m pytest src/ikigai/src/agents/paperclip/tests/ src/ikigai/tests/test_paperclip_drift.py -v

# 3. Drift net — must show 73/73 (was 72/72 + 1 new M175)
python -m pytest src/ikigai/tests/test_drift_invariants.py \
                  src/ikigai/tests/test_drift_extended_invariants.py \
                  src/ikigai/tests/test_canonical_scope.py \
                  src/ikigai/tests/test_paperclip_drift.py

# 4. Lint + format
python -m ruff check src/ikigai/src/agents/paperclip/ src/ikigai/tests/test_paperclip_drift.py
python -m ruff format --check src/ikigai/src/agents/paperclip/ src/ikigai/tests/test_paperclip_drift.py

# 5. Sanity: importable, default threshold correct
python -c "from src.ikigai.src.agents.paperclip.policy import WallClockGate; g = WallClockGate(); print('threshold_s:', g.threshold_seconds)"
```

---

## Acceptance

- [x] `src/ikigai/src/agents/paperclip/policy.py` extended with
      `WallClockGate` class — fail-open, env-driven threshold,
      default 3600s — **without modifying `CostGate`**
- [x] `policy.__all__` exports `WallClockGate`, `DEFAULT_THRESHOLD_S`,
      `ENV_WALL_CLOCK_THRESHOLD`
- [x] `state.py` adds `task_started_at: NotRequired[str | None]` field
- [x] `nodes/read_spec.py` stamps `task_started_at` on first invocation
      (via `datetime.now(timezone.utc).isoformat()`)
- [x] `nodes/implement.py` consults `WallClockGate` AFTER `CostGate`
      and BEFORE the agent invocation; on block returns
      `error_type="WallClockGateExceeded"`
- [x] 5 new tests in `test_wall_clock_gate.py` covering: no start
      time, under threshold, over threshold, malformed ISO, env override
- [x] 1 new drift invariant in `test_paperclip_drift.py`:
      `test_paperclip_wall_clock_gate_exists`
- [x] Drift net: **72 → 73** (+1)
- [x] `ruff check` + `ruff format --check` clean on changed files
- [x] `WallClockGate` importable from
      `src.ikigai.src.agents.paperclip.policy` with default
      `threshold_seconds=3600`
- [x] No existing logic modified — `CostGate` untouched, `implement`
      wire-up appends a new block (does not edit the existing
      cost-gate block), state field is new, read_spec's timestamp is
      additive

---

## Lessons

1. **Fail-open gates mirror each other.** `CostGate` and `WallClockGate`
   share the same fail-open philosophy, the same env-override pattern,
   and the same operator-decision surface (the reason string contains
   both current value + threshold so the operator can decide what to
   do). Mirroring an existing pattern is cheaper to reason about than
   inventing a new one — and easier to drift-test.

2. **`now_iso` injection beats `monkeypatch.setattr(datetime, ...)`.**
   The "deterministic time" problem is universal in tests; the cleanest
   pattern is to make `now_iso` a constructor argument and default to
   `datetime.now(UTC)` in the production path. Tests pass explicit
   strings; production code stays one-line.

3. **Drift net +1 per `def test_*()`.** The new `test_paperclip_wall_clock_gate_exists`
   is intentionally minimal (1 import + 2 assertions) — enough to
   catch accidental removal of `WallClockGate` from `__all__` or
   rename of the class. Composite coverage (under/over/malformed/env)
   lives in `test_wall_clock_gate.py`, not in the drift file, because
   drift tests must run in <1s and stay parseable from `policy.py`'s
   AST alone.

---

## Related

* [M173 cost gate](file:///C:/Users/mathe/code_space/life-oss/life/specs/M169-paperclip/SPEC.md)
  — the first auto-throttle, same fail-open pattern
* [M169 Paperclip spec](file:///C:/Users/mathe/code_space/life-oss/life/specs/M169-paperclip/SPEC.md)
  — the 4th LangGraph graph that owns both gates
* [M174 auto-spawner](file:///C:/Users/mathe/code_space/life-oss/life/specs/M174-paperclip-auto-spawner/SPEC.md)
  — the spawner script that may eventually trigger the gates (M175
  gates do not yet block the spawner's `--once` path; that's a future
  wiring — the spawner dispatches to the graph which then runs the
  gates inside `implement_node`)
