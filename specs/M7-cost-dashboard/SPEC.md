# M7 — Cost Dashboard

> **Created:** 2026-09-08
> **Owner:** loop-orchestrator
> **Status:** IN-PROGRESS

## Goal

Daily cron writes `.claude/loop/logs/cost-report.md` aggregating the last 24h of
tick entries from `.claude/loop/progress.md`. Detects cost spikes (>$10/day) and
logs an alarm. Loop brittleness + runaway-cost mitigation (per Ronacher).

## Why

- The loop runs 24/7 with `cost_cap_usd=5.0` per tick.
- Without aggregated visibility, a runaway cost loop can accumulate silently.
- The hill-climb cron already runs weekly; a daily cost report is the natural
  cadence for short-loop review.

## Acceptance Criteria

### 1. Aggregation logic

- [ ] Reads `.claude/loop/progress.md`
- [ ] Filters entries where `## YYYY-MM-DD` matches today OR yesterday (UTC)
- [ ] Extracts `cost_usd: <float>` per entry
- [ ] Computes:
  - **ticks_day** = count of matching entries
  - **usd_total** = sum of cost_usd values
  - **usd_avg_per_tick** = usd_total / ticks_day (0.0 if ticks_day == 0)

### 2. Output schema

`.claude/loop/logs/cost-report.md` must contain:

```markdown
# Cost Report — YYYY-MM-DD

- **ticks_day:** N
- **usd_total:** $X.XX
- **usd_avg_per_tick:** $X.XX
- **spike_alarm:** none | SPIKE (>$10/day: $X.XX)
- **generated_at:** ISO8601 UTC timestamp
```

Idempotent: re-running within the same UTC day produces byte-identical content
EXCEPT for the `generated_at` timestamp line (which is a wall-clock metadata,
not a metric). The metric body (ticks / usd_total / usd_avg / spike_alarm)
must be deterministic.

### 3. Spike alarm

- If `usd_total > 10.0` (configurable threshold via `COST_DASHBOARD_SPIKE_USD`
  env var; default 10.0), set `spike_alarm: SPIKE (>$10/day: $X.XX)` AND exit
  code = 2 (alarm signal). Caller can wire notification channel (M8).

### 4. Script interface

```bash
bash scripts/cost-dashboard.sh [--dry-run]
```

- Exit 0: report written, no spike
- Exit 2: report written, spike detected
- Exit 1: fatal error (progress.md missing, unparseable, etc.)
- `--dry-run`: prints report to stdout, does NOT write file

### 5. Tests

`tests/test_cost_dashboard.sh` covers:

1. **Aggregation correctness**: seed a synthetic progress.md with N entries of
   known cost, run dashboard, assert parsed output matches expected metrics.
2. **Spike alarm**: seed entries summing > $10, assert exit code = 2 + alarm
   line present.
3. **Idempotent re-run**: run twice, assert metric body identical (timestamps
   excluded from comparison).

### 6. Dependencies

- M6 (worktree isolation) — DONE
- Daemon schedule wired via `bash .claude/helpers/daemon-manager.sh add --interval 1440m --command 'bash scripts/cost-dashboard.sh' --cost-cap-usd 0.5`

## Files Created

| Path | Purpose | Approx lines |
|------|---------|--------------|
| `scripts/cost-dashboard.sh` | Aggregation + report writer | ~80 |
| `tests/test_cost_dashboard.sh` | 3 test groups, idempotent | ~60 |

## Out of Scope (Future)

- Notification channel wiring (M8 — Telegram/email)
- Per-tick cost distribution histogram
- Cross-day trend (week-over-week delta)
- Automatic cost-cap adjustment when spikes detected

## Architecture Notes

- Pure bash + awk (no Python — keeps the loop's `cost_cap_usd=0.50` headroom
  intact and matches the M6 worktree-helper pattern)
- Reuses `progress.md` as SOT (append-only invariant preserved)
- Output file in `.claude/loop/logs/` is gitignored (line ~315 of `.gitignore`)
- Spike alarm signal via exit code 2 lets M8 notification channel pipe
  `bash cost-dashboard.sh; if [ $? -eq 2 ]; then notify; fi` without parsing
  the report file
