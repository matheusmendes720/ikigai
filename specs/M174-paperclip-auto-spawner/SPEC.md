---
name: M174-paperclip-auto-spawner
description: Paperclip self-managed auto-spawner — inbox + CLI queue, sequential adapter dispatch, binary-on-PATH router, cost gate.
status: DONE
owner: matheus-mendes
created: 2026-10-11
constitution_refs:
  - tests_are_the_contract
  - state_on_disk_not_conversation
  - composition_over_inheritance
estimated_cost_usd: 0.00
---

# M174 — Paperclip Auto-Spawner (Config Bundle)

**Status:** 🟢 DONE
**Date:** 2026-10-11
**Author:** matheus-mendes (with Claude Code assist)

---

## TL;DR

M174 wires Paperclip into the **loop's recurring-task fabric** so spec
ingestion stops requiring a human at the keyboard. The bundle ships a
**self-managed auto-spawner** that polls the loop inbox every 300m,
probes AI-binary health via `which <adapter>`, and dispatches each spec
to the cheapest healthy adapter through a new deterministic **router**
(`pick_adapter`). Sequential queue (one ad per tick), binary-on-PATH
health (no daemon polling), and the M173 `CostGate` policy are preserved
unchanged — M174 only adds the entry point and the routing surface.
Auto-throttle, GitBucket PR sync, TUI surface, and fan-out remain
explicitly **deferred** to Waves N+2 through N+5 (per M169 roadmap).

---

## What changed

```
src/ikigai/src/agents/paperclip/router.py        # NEW — 6 exports + 2 helpers
src/ikigai/tests/test_paperclip_drift.py         # +2 tests (test_paperclip_router_importable, test_paperclip_spawner_script_exists)
scripts/paperclip-spawner.sh                     # NEW — bash spawner (executable, #!/usr/bin/env bash)
.claude/loop/schedules.json                      # +1 entry: paperclip-auto-spawner (300m)
specs/M174-paperclip-auto-spawner/SPEC.md        # this file
```

**Total: 2 new files + 2 modified files. Drift net 70 → 72.**

`src/ikigai/src/agents/paperclip/tests/test_router.py` already existed
(5 unit tests for `pick_adapter` / `rank_adapters`) and is unchanged.
The two **new** drift invariants guard:

1. `router.py` exists, parses, and exports the full M174 surface
   (`AdapterHealth`, `SpecContext`, `RouterDecision`, `pick_adapter`,
   `AdapterUnavailableError`, `CostThresholdExceeded`).
2. `scripts/paperclip-spawner.sh` exists, is executable, and starts
   with `#!/usr/bin/env bash`.

The 5 unit tests in `test_router.py` were pre-existing and continue to
PASS unchanged (they exercise the router logic; the new drift invariants
guard the topology).

---

## Architecture decisions

### D6 — Invoke sources: inbox drop-in + CLI `--once`, no daemon polling

Two ways for a spec to reach the spawner:

1. **Inbox drop-in** — `~/.claude/loop/inbox/<task_id>.md` (operator
   `mv`s a file). The script scans the inbox on every tick.
2. **CLI invoke** — `bash scripts/paperclip-spawner.sh --once`
   (idempotent single iteration). Used by the loop schedule.

Rejected: a long-lived daemon polling at sub-second cadence. The 300m
tick interval already covers the loop's contract; faster polling would
burn budget without delivering value (specs are slow — minutes per
implement, not seconds).

### D7 — Sequential queue, not parallel

The spawner processes **at most 1 spec per tick** (`PAPERCLIP_MAX_PER_TICK=1`).
Multi-graph fan-out (one spec → many parallel Paperclip runs) is
explicitly deferred to Wave N+5 (per M169 spec). Sequential keeps the
router's deterministic-pick contract honest (no race between two
adapters writing the same worktree).

### D8 — Binary-on-PATH health, no background probing

Adapter health comes from `which <adapter>` exit code at decision time,
plus the cost-dashboard JSON sidecar (`data/cost-today.json`). No
background daemon probes. Operator installs a binary → next tick
picks it up; uninstalls → next tick skips it. No state to keep in
sync, no clock skew, no zombie probes.

---

## Verification

```bash
# 1. Drift net — must show 72/72 (was 70)
python -m pytest src/ikigai/tests/test_paperclip_drift.py -v
# Expected: 4 passed (2 existing + 2 new)

# 2. Router unit tests — pre-existing suite, must remain green
python -m pytest src/ikigai/src/agents/paperclip/tests/test_router.py -v
# Expected: 5 passed

# 3. schedules.json parses cleanly + paperclip-auto-spawner present
python -c "import json; data = json.load(open('.claude/loop/schedules.json')); names = [s['name'] for s in data]; assert 'paperclip-auto-spawner' in names; print('OK,', len(data), 'entries')"
# Expected: OK, 10 entries

# 4. SPEC.md exists on disk
python -c "import os; assert os.path.exists('specs/M174-paperclip-auto-spawner/SPEC.md'); print('SPEC.md exists')"
# Expected: SPEC.md exists
```

(All 4 verifications were run during implementation; results logged in
the workflow report.)

---

## Acceptance

- [x] `src/ikigai/src/agents/paperclip/router.py` exists with the 6
  required exports (`AdapterHealth`, `SpecContext`, `RouterDecision`,
  `pick_adapter`, `AdapterUnavailableError`, `CostThresholdExceeded`)
  plus `rank_adapters` + 2 cost-threshold constants
- [x] `scripts/paperclip-spawner.sh` exists, is executable (`chmod +x`),
  starts with `#!/usr/bin/env bash`, supports `--once` / `--loop` /
  `--dry-run` flags
- [x] `src/ikigai/tests/test_paperclip_drift.py` extended by +2 tests
  (`test_paperclip_router_importable`,
  `test_paperclip_spawner_script_exists`); existing 2 tests untouched
- [x] `.claude/loop/schedules.json` has a new `paperclip-auto-spawner`
  entry at 300m tick with `cost_cap_usd=0.05`; existing 9 entries
  preserved byte-for-byte
- [x] `specs/M174-paperclip-auto-spawner/SPEC.md` ships with frontmatter
  matching the M169-paperclip template (3 constitution refs;
  `estimated_cost_usd: 0.00`)
- [x] Drift net: **70 → 72** (`+2` new invariants)
- [x] Router unit tests: **5/5 PASS** (pre-existing suite preserved)
- [x] `ruff check src/ikigai/tests/test_paperclip_drift.py` clean
- [x] `schedules.json` parses via `python -c "import json; json.load(...)"`
  (10 entries, including the new one)
- [x] No existing logic modified — tests appended, schedule entries
  preserved, only NEW files + APPEND operations

---

## Lessons

1. **Drift tests are append-only too.** Each `def test_*()` in the
   drift file grows the invariant count by +1. This milestone added
   two tests; future contracts (severity / risk gate / D5 keywords)
   will add more. Resist the urge to consolidate tests into a single
   parametrized function — the per-function count is the load-bearing
   invariant.

2. **`os.access(path, os.X_OK)` is the right shebang-execution check.**
   On Windows the executable bit comes from `git core.fileMode`; CI's
   POSIX runner respects the bit but `Path.stat().st_mode & 0o111`
   silently succeeds on Windows even when the bit is missing. The
   cross-platform helper is `os.access`, not mode-mask inspection.

3. **Sequential queue keeps the router honest.** Picking the cheapest
   healthy adapter is deterministic when there's no contention; the
   moment two specs run in parallel, the priority ordering becomes a
   race condition. M174 picks 1 per tick so the contract stays testable.

---

## Related

* [M169-paperclip SPEC](file:///C:/Users/mathe/code_space/life-oss/life/specs/M169-paperclip/SPEC.md) — the
  4th LangGraph graph that the spawner dispatches to
* [M173 cost gate](file:///C:/Users/mathe/code_space/life-oss/life/specs/M173-paperclip-cost-gate/) (planned)
  — the `policy.CostGate` policy the router respects (`fail-closed`
  when `cost_today_usd > threshold`)
* [M170 Pi / M171 omo / M172 openclaw real adapters](file:///C:/Users/mathe/code_space/life-oss/life/specs/M170-paperclip-pi-adapter/) (planned)
  — the 3 real adapters that fill out `ADAPTER_PRIORITY`
* Memory entry: `M174-paperclip-auto-spawner-shipped-2026-10-11.md`
  (planned, ships alongside this SPEC)