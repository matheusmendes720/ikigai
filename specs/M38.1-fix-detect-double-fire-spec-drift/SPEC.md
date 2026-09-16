---
name: M38.1-fix-detect-double-fire-spec-drift
description: Implement the ≥2-seconds-apart filter that M38 spec documented but detect-double-fire.sh didn't code (false positives on rapid-fire cron).
status: DONE
owner: loop-orchestrator
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
estimated_ticks: 1
---

# M38.1 — Fix detect-double-fire.sh spec drift

## Problem

M38 (`specs/M38-double-fire-detection-and-suppression/SPEC.md`) documented
the rule:

> **Legitimate rapid-fire** = same `task_id` within 5 minutes BUT
> different timestamps (≥2 seconds apart)
> **Real double-fire** = same `task_id` AND same timestamp (same minute)
> with different content

…but `scripts/detect-double-fire.sh` didn't implement the **≥2 seconds
apart** filter. It counted ANY 2+ entries with same task_id within the
same minute as a double-fire, including legitimate rapid-fire cron
catchup.

This caused the drift gate `test_progress_md_has_no_double_fires` to fail
whenever `loop-tick.sh --graph <key>` was invoked 2+ times in quick
succession (e.g., during test_m4_langgraph_integration.py verification
runs that legitimately exercise the graph dispatch path).

## Discovered via

M24.2 verification (2026-09-16T02:38Z): ran `loop-tick.sh --graph
ikigai_fork_smoke` 5 times in ~2 minutes; drift gate failed with:

```
ikigai_fork_smoke @ 2026-09-16T02:36: 3 entries, span=35s, verdicts=['PASS', 'PASS', 'PASS']
ikigai_fork_smoke @ 2026-09-16T02:38: 2 entries, span=6s, verdicts=['PASS', 'PASS']
```

Both are legitimate rapid-fire cron catchup (per M38 spec), NOT true
double-fires. The detector flagged them anyway.

## Fix

`.claude/loop/scripts/detect-double-fire.sh` lines 65-87 — added the
≥2-seconds-apart filter inside the double-fire loop:

```python
# M38.1: rapid-fire catchup (≥2s apart) is legitimate cron behavior
if delta >= 2.0:
    continue
```

Updated the script header to reflect the corrected definition.

## Verified

After fix, detector correctly distinguishes:

- ❌ EXCLUDED (legitimate rapid-fire): `ikigai_fork_smoke` entries with
  span=35s and span=6s — these are sequential `--graph` test runs, not
  concurrent invocations.
- ✅ STILL FLAGGED (true concurrent):
  - `M5 @ 2026-09-08T01:15: 2 entries, span=0s` — exact concurrent invocation
  - `T-9.6 @ 2026-09-08T09:39: 2 entries, span=1s` — near-concurrent
    (within the 2s window)

Drift net: 69/69 PASS preserved.

## Acceptance

- [x] `bash .claude/loop/scripts/detect-double-fire.sh .claude/loop/progress.md` no longer flags rapid-fire cron catchup (T-38.1.1)
- [x] Detector STILL flags true concurrent double-fires (span < 2s) — verified against historical data (T-38.1.2)
- [x] Drift net 69/69 PASS (ikigai) preserved (T-38.1.3)
- [x] 1 atomic commit + push (T-38.1.4)

## Why M38 ship-time review missed this

M38's commit message and progress.md entry both reference the spec's
filter language ("Legitimate rapid-fire ≥2 seconds apart") but the
detection script didn't actually code it. Ship-time review likely ran
the detector on a clean progress.md (where 2+ entries within the same
minute from the same task_id are rare without test runs) and saw PASS,
without realizing the filter was missing.

## Reversibility

`git revert HEAD`. Single-file change to `.claude/loop/scripts/detect-double-fire.sh`.
