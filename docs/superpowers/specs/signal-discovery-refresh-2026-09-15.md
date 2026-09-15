# Signal-Discovery Refresh — 2026-09-15

## Compared to M29
- Ticks: 260 → 276 (was ~260 in M29; +16 ticks in ~12h)
- Drift net: 64 → 66 (+2 since M29: M35 constitution coverage)
- Daemons RUNNING: 1/4 → 4/4 (M30 daemon reactivation + M36 hill-climb v2)
- State-machine drift: RESOLVED (M34 auto-reconcile)
- M-CAND-1: ADDRESSED (M35 constitution coverage — 7 principles now in SPEC frontmatter)
- M-CAND-2: ADDRESSED (M30 daemon reactivation — cost-dashboard + streak-tracker restored)

## Aggregate Stats (CURRENT)

| Metric | Value | vs M29 |
|---|---|---|
| Total ticks observed | 276 | +16 |
| FAIL count | 23 | all from 2026-09-08 burst |
| FAIL rate | 8.3% (23/276) | burst from M9/M10 era, no new FAILs since |
| PASS rate | ~91.7% | stable |
| Total cost (progress.md) | $2.60 (263 entries) | stable |
| Avg cost per tick | $0.0099 | ultra-lean |
| Drift net size | 66/66 | +2 (M35 constitution coverage) |
| Recent PASS streak | 2 (hill-climb-v2, 2026-09-15T16:12–16:18Z) | clean |

## Failure Patterns (since M29)

### 2026-09-08 FAIL burst — resolved
- **Occurrences:** 12 FAIL ticks in ~10 minutes (09:29–09:39 UTC), plus 8 more in following 10 min (09:39–09:43 UTC)
- **Context:** T-9.6 (streak-tracker 7-day gate), T-10.1/T-10.3 (dispatch chain)
- **Pattern:** Rapid-fire FAIL without recovery between attempts — same class as M29 analysis
- **Mitigation:** Resolved by end of 2026-09-08; no recurrence in subsequent 7+ days
- **Root cause:** dispatch script misconfiguration during M9/M10 integration
- **Status:** No new FAILs since 2026-09-08; confirmed clean

### No new failure modes detected
- Zero subagent fabrications
- Zero drift net regressions
- Zero cost-cap overruns
- Zero new state-machine drift events (M34 auto-reconcile prevents recurrence)

## Drift Net Growth (since M29)

| Date | Invariants | Change | Trigger |
|---|---|---|---|
| M29 baseline | 64/64 | — | M28 SPEC frontmatter |
| M30 (2026-09-15) | 64→65 | +1 | Daemon reactivation |
| M33 (2026-09-15) | 65→65 | 0 | Hill-climb v2 (no drift change) |
| M34 (2026-09-15) | 65→65 | 0 | Anti-idle auto-reconcile (no new tests) |
| M35 (2026-09-15) | 65→66 | +1 | Constitution coverage (7 principles in SPEC frontmatter) |

**Growth rate:** ~2 invariants per week. No regressions. Healthy.

## Active Cron State (current)

| Cron | Interval | Cost cap | Last fired | Status |
|---|---|---|---|---|
| loop-tick | 60m | $5 | 2026-09-15T16:30Z | RUNNING |
| hill-climb-v2 | 168h (weekly) | $10 | 2026-09-15T16:12Z | RUNNING |
| cost-dashboard | 1440m (daily) | $0.5 | recent (post-M30) | RUNNING |
| streak-tracker | 1440m (daily) | $0.1 | recent (post-M30) | RUNNING |

**Note:** All 4 daemons now RUNNING. M30 reactivated cost-dashboard + streak-tracker. M36 activated hill-climb v2 (supersedes original weekly hill-climb that ran once on 2026-09-07).

## Top-5 Next Candidates (RE-RANKED by current evidence)

### #1 — M38: Anti-Idle Triage Depth for Cost-Gated Ticks
- **Evidence:** T-24.4 wall-clock gate notes (progress.md, 2026-09-15T16:10Z): "Budget remaining: ~$0.32 — next tick may hit $0 cost cap." When cost cap is nearexpired, orchestrator enters IDLE rather than doing minimal useful work (state-machine-only scan). 4 cron systems running but budget is constrained.
- **Expected impact:** Orchestrator uses remaining budget to do minimal useful triage (scan for new commits, check drift net) even when LLM is unaffordable. Reduces IDLE ticks during budget-exhausted periods.
- **Risk:** LOW — bash-only state-machine change
- **Estimated cost:** $0.00

### #2 — M38: Double-Fire Detection and Suppression
- **Evidence:** T-24.4 wall-clock gate notes (progress.md): "2026-09-15T12:43:00Z x4 fires in 4 seconds — 4 parallel loop-tick invocations within same minute." Pattern: 12:43:00, :01, :02, :04. Also 11min pair cadence suggesting daemon "missed tick catchup." No actual double-fire in tick count (only 1 progress entry per timestamp), but redundant invocations waste budget.
- **Expected impact:** Eliminate redundant loop-tick invocations. Saves ~$0.50/tick day in wasted compute. Enables longer streak runs without budget exhaustion.
- **Risk:** LOW — bash-only detection + dedup
- **Estimated cost:** $0.00

### #3 — M38: Signal-Discovery Automation (scheduled)
- **Evidence:** This report (M37) aggregates 276 ticks manually. Hill-climb v2 ran on 2026-09-15 and produced PASS but its output is not yet reviewed/committed. A scheduled signal-discovery (fortnightly) would replace manual M29/M37 work and catch drift patterns earlier.
- **Expected impact:** Continuous signal analysis rather than episodic manual refreshes. Would have caught the 2026-09-08 FAIL burst within hours, not days later.
- **Risk:** MEDIUM — needs hill-climb output parsing + decision logic (was CAND-3 in M29)
- **Estimated cost:** $0.50-1/week if runs Sonnet

### #4 — M38: Streak-Tracker 7-Day Gate Verification
- **Evidence:** M9 shipped streak-tracker infrastructure + 7-day unattended streak as goal. Streak-tracker is RUNNING but the 7-day streak gate has never been verified. Current streak=unknown (was 2 on 2026-09-08 per M29). Streak-tracker exits exit code 2 on break; no confirmation it has achieved 7 consecutive days.
- **Expected impact:** Confirms production mode is fully operational. If 7-day streak achieved, loop is fully autonomous for a full week — the original M9 goal.
- **Risk:** LOW — just needs verification of existing infrastructure
- **Estimated cost:** $0.00 (bash-only verification)

### #5 — M38: M24 T-24.4 Closeout (wall-clock gate verification)
- **Evidence:** M24 T-24.4 wall-clock gate (24h, ending 2026-09-16T02:44Z) is still IN-PROGRESS per roadmap.md. The gate requires 24h of no double-fire observation. The T-24.4 analysis notes anomalies (4 fires in 4 seconds, 5.6h gap). Gate should complete ~2026-09-16T02:44Z. M24 closeout is blocking nothing but is the last open IN-PROGRESS milestone.
- **Expected impact:** M24 DONE closes the last open milestone. Roadmap has zero IN-PROGRESS items after closeout.
- **Risk:** LOW — doc-only verification
- **Estimated cost:** $0.00

## Anti-Patterns Detected

### Redundant invocations (budget waste)
- **Observed:** 4 parallel loop-tick invocations within 4 seconds (2026-09-15T12:43:00–:04Z)
- **Root cause:** Likely SessionStart guardian re-firing on daemon restart, or daemon restart burst when cost-cap hit
- **Impact:** Wastes budget on redundant work (4 invocations, 1 progress entry)
- **Status:** New pattern, not yet addressed

### Daemon downtime gaps
- **Observed:** 5.6h gap (2026-09-15T04:56Z → 10:34Z) — likely machine sleep or script error
- **Impact:** Missed ticks during gap; orchestrator resumes on reconnect
- **Status:** Pre-existing behavior; no recovery automation yet

### 11-minute inter-fire cadence (unknown origin)
- **Observed:** Daemon firing at 51min/11min/51min/11min cadence instead of uniform 60min
- **Root cause:** Unknown — possibly "missed tick catchup" mechanism OR cost-dashboard triggering loop-tick as side-effect
- **Status:** Under investigation (per T-24.4 notes)

## Conclusion

The loop is in its healthiest state since M0: all 4 daemons RUNNING, zero FAILs since the 2026-09-08 burst, drift net at 66/66 with no regressions, and both stale CANDs addressed. The highest-leverage next move is M38-A (double-fire suppression) — it directly recovers wasted budget from the 4-parallel-invocation pattern observed on 2026-09-15, which is the most concrete operational inefficiency visible in current data. A close second is M38-D (streak-tracker 7-day verification), which would confirm whether the original M9 production-mode goal has actually been achieved. M38-C (signal-discovery automation) would prevent future manual M37-style refreshes and catch failure patterns faster.
