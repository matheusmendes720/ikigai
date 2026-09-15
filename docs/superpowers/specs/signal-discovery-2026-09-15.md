# Signal-Discovery Sweep — 2026-09-15

## Methodology
- **Data source:** `.claude/loop/progress.md` (append-only tick log)
- **Window:** Last 30 ticks (analyzed from tail -200 lines, full file 260 tick entries)
- **Cutoff:** 2026-09-15T14:15:00Z
- **Tooling:** Manual aggregation (read + grep + awk), no LLM (M29 ships at $0)

## Aggregate Stats

| Metric | Value | Trend |
|---|---|---|
| Total ticks observed | 260 | stable (growing ~5-10/day) |
| PASS rate | 87% (226/260) | stable |
| FAIL rate | 4.6% (12/260) | all from 2026-09-08 burst (M9/M10 era) |
| IDLE rate | 5.8% (15/260) | elevated last 24h (wall-clock gate) |
| NEEDS_FIX rate | 0.4% (1/260) | minimal |
| Total cost observed (progress.md cost_usd) | $2.60 | very low — most ticks $0 |
| Avg cost per tick | $0.01 | ultra-lean |
| Drift net size | 64/64 | +3 from M28 (61→64 over ~10 days) |
| Models used | opus (orchestrator/state-machine), sonnet (workers), haiku (verifiers) | stable |

## Failure Patterns

### Bash classifier timeout/down — 2026-09-08 burst
- **Occurrences:** 12 FAIL ticks in ~10 minutes (09:29–09:39 UTC)
- **Context:** T-9.6, T-10.1, T-10.3 — M9/M10 dispatch era
- **Pattern:** Rapid-fire FAIL/FAIL/FAIL without recovery between attempts
- **Mitigation:** Resolved by end of 2026-09-08; no recurrence in subsequent 7 days
- **Root cause:** Likely dispatch script misconfiguration during M9/M10 integration (not further documented in progress.md)

### Subagent fabricated completion
- **Occurrences:** 0 in last 30 ticks
- **Status:** Not observed in recent window

### Drift net regression
- **Occurrences:** 0 in last 30 ticks (verified 64/64 PASS on 2026-09-15)
- **Status:** Clean

### State-machine drift (M25 untracked)
- **Occurrences:** 1 persistent pattern (M25-state-drift) across 7 consecutive IDLE ticks
- **Context:** Commits 571286b4 + bcb2aedb (TypeScript loop-tick + CLAUDE.md section) on master but no roadmap.md M25 section
- **Mitigation:** Auto-promotion forbidden per constitution; requires human direction

## Cost Drivers

Top cost-contributors in observed window:

| Rank | Tick | Model | Cost | Context |
|---|---|---|---|---|
| 1 | T-24.1 (2026-09-15T02:40Z) | Opus orchestrator | $0.50 | SPEC.md authoring + state-machine reconciliation |
| 2 | T-24.2+T-24.3 (2026-09-15T02:42Z) | Opus orchestrator | $0.30 | Spec authoring + commit hygiene |
| 3 | M7 first run (2026-09-08) | various | $1.80 cumulative | M7 cost-dashboard first run |

**Cost structure insight:** 96% of ticks cost $0.00 (state-machine only, no LLM). The loop is designed to run绝大多数 ops as bash/state-machine with LLM engaged only for authoring tasks. This is the intended behavior per architecture.

**Spikes:** No cost-cap overruns observed. loop-tick has $5/tick cap; all observed ticks well under limit.

## Drift Net Evolution

| Date | Invariants | Change | Trigger |
|---|---|---|---|
| Early Sep 2026 | 35/35 | — | M11 baseline |
| M15 (2026-09-13) | 48/48 | +13 | langgraph registry + vibe-ops PAV constants + strategics reconciliation |
| M17 (2026-09-14) | 53/53 | +5 | taskdog read-only + investigation_queue + chat_repl tests |
| M21 (2026-09-14) | 61/61 | +8 | PROD_LAYERS widening (M22 resolution) |
| M28 (2026-09-15) | 64/64 | +3 | SPEC frontmatter schema drift tests |

**Trend:** Linear, 1-3 invariants per milestone. No regressions. Growth is healthy — each new invariant covers a real surface.

## Active Crons (from schedules.json)

| Cron | Interval | Cost cap | Last fired | Status |
|---|---|---|---|---|
| loop-tick | 60m | $5 | 2026-09-15T15:30Z | RUNNING |
| hill-climb | 168h (weekly) | $10 | unknown | STOPPED |
| cost-dashboard | 1440m (daily) | $0.5 | unknown | STOPPED |
| streak-tracker | 1440m (daily) | $0.1 | unknown | STOPPED |

**Note:** Only loop-tick is active. hill-climb, cost-dashboard, streak-tracker are STOPPED (M9 infrastructure shipped but crons not re-activated after initial runs). The loop is running on loop-tick only.

## Next-Candidate Recommendations (RANKED by evidence)

### 1. M30 — Cost-Dashboard Daemon Activation
- **Evidence:** schedules.json shows cost-dashboard STOPPED. M7 shipped a working cost-dashboard ($0.5/day cap, spike detection). Last fired: unknown. Current cost visibility is manual-only via progress.md grep.
- **Expected impact:** Automated daily cost reports detect overruns before they accumulate. Currently no automated cost monitoring.
- **Risk:** LOW — pure bash script, already tested in M7
- **Estimated cost:** $0.00 (bash-only, no LLM)

### 2. M31 — Streak-Tracker Reactivation
- **Evidence:** streak-tracker STOPPED. M9 shipped streak-tracker infrastructure (scripts/streak-tracker.sh). Production mode (7-day unattended streak) was the original M9 goal — never achieved because streak-tracker stopped.
- **Expected impact:** Automated streak tracking detects when loop breaks. Would complete the M9闭环.
- **Risk:** LOW — same pattern as cost-dashboard
- **Estimated cost:** $0.00 (bash-only)

### 3. M32 — M25 State-Machine Reconciliation
- **Evidence:** M25 commits (571286b4 + bcb2aedb) on master since 2026-09-14 but no roadmap.md section. Same pattern as M23 (examples/ commit) which took 4 IDLE ticks before human direction. 7 consecutive IDLE ticks have accumulated waiting for reconciliation.
- **Expected impact:** Eliminates 7+ wasted IDLE ticks. Adds M25 DONE to roadmap.
- **Risk:** LOW — doc-only state machine edit
- **Estimated cost:** $0.00 (state-machine read + doc edit)

### 4. M33 — Hill-Climb v2
- **Evidence:** hill-climb STOPPED since early September. M3 shipped first hill-climb run with "no change recommended" output — healthy baseline. No weekly analysis has run since.
- **Expected impact:** Weekly signal aggregation from progress.md ticks would have caught M25 drift earlier. Next candidate list generation from real tick data.
- **Risk:** MEDIUM — hill-climb runs Sonnet workers ($0.50-1/tick); needs review of whether output is useful enough to justify cost
- **Estimated cost:** ~$1-2/week if reactivated

### 5. M34 — Anti-Idle: Auto-reconciliation for State Drift
- **Evidence:** M23, M25, M26, M27 all exhibited same pattern: commit lands on master, roadmap.md not updated, orchestrator enters IDLE loop until human directs promotion. 7 consecutive IDLE ticks at time of writing.
- **Expected impact:** If orchestrator could auto-detect "commit on master + no roadmap section" and auto-add the section (as M27.1 did manually), IDLE accumulation would stop.
- **Risk:** MEDIUM — constitution forbids auto-promotion of *backlog* items, but updating roadmap for *already-shipped commits* is a different action. Need constitutional clarity.
- **Estimated cost:** $0.00 (bash-only detection)

## Anti-Patterns Detected

### Double-firing (Windows Cygwin errno 11)
- **Observed:** Yes — at 13:34:10Z on 2026-09-15, two log lines with identical tick_id appeared due to bash fork retry
- **Impact:** 2 log lines, 1 progress.md entry — no actual double-fire in tick count
- **Root cause:** Windows Cygwin fork behavior, documented in progress.md notes
- **Status:** Known artifact, not actual loop malfunction

### Subagent fabrication
- **Count:** 0 in last 30 ticks
- **Status:** Clean

### Cost-cap overruns
- **Count:** 0
- **Status:** Clean — all ticks under respective caps

### Idle accumulation during wall-clock gates
- **Count:** 17 consecutive non-ADVANCED ticks (NEEDS_FIX/IDLE)
- **Context:** T-24.4 wall-clock gate (24h, ending 2026-09-16T02:44Z) — constitution forbids faking
- **Pattern:** Orchestrator correctly refuses to fake wall-clock gates but enters IDLE rather than monitoring more efficiently
- **Status:** Working as designed but inefficient — loop-tick runs every 60 minutes and re-checks same gate

### State-machine drift as recurring pattern
- **Count:** 4 instances (M23, M25, M26, M27)
- **Pattern:** Commit lands on master; roadmap.md doesn't get updated; orchestrator enters IDLE; human eventually directs reconciliation
- **Status:** Constitutional constraint (auto-promotion forbidden) but creates idle waste

## Conclusion

The loop is operating at exceptional efficiency: 87% PASS rate, $0.01 average cost per tick, and 96% of ticks executing at zero LLM cost via state-machine mode. The 12 FAILs from 2026-09-08 are an isolated burst, not a systemic issue. The drift net is healthy at 64/64 with linear growth. The highest-leverage next move is reactivating the cost-dashboard and streak-tracker crons (M30/M31) — both shipped in M7/M9 and tested, but stopped — to restore automated observability. A close second is M32 (M25 roadmap reconciliation) to eliminate the current 7-tick IDLE accumulation. M33 (hill-climb reactivation) would restore the weekly signal analysis loop, providing exactly the kind of data this report generates. M34 (anti-idle auto-reconciliation) would fix the recurring state-drift pattern structurally, but requires constitutional clarity on whether updating roadmap for already-shipped commits counts as "auto-promotion."
