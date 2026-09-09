# M9 — Production Mode

> **Constitution:** .claude/loop/constitution.md
> **Created:** 2026-09-07
> **Owner:** loop-orchestrator
> **Status:** IN-PROGRESS

## Goal

Close the loop: the cron schedule for `loop-tick` must auto-resume after every
session restart, then sustain 7 consecutive days of unattended operation where
the only human intervention needed is on `NEEDS_FIX` / `BLOCKED` / `FAIL` /
`BUDGET_ABORT` (per M8's notification channel). The actual goal of loop
engineering — fire-and-forget.

## Why

- M0–M8 build the loop infrastructure (state machine, agent dispatch, worktrees,
  LangGraph integration, IKIGAI MCP, cost dashboard, notification channel).
- None of it matters if the cron dies when Claude Code exits and doesn't restart
  when the user opens a new session.
- M9 proves the whole stack survives unattended operation: 7 days × ~24 ticks/day
  ≈ 168 ticks without a human in the loop.

## Acceptance Criteria

1. **Auto-resume on session start**
   - When Claude Code starts a new session (new `SessionStart` event), the
     `loop-tick` schedule is restarted if not running.
   - Implementation: a new SessionStart hook in `.claude/settings.json` that
     calls `daemon-manager.sh start-schedule loop-tick` (idempotent — already
     handles `is_running`).
   - Test: kill the loop-tick PID, restart Claude Code, verify PID is recreated
     within ~10s.
   - Currently BROKEN: `claudeFlow.daemon.autoStart: false` in `settings.json`
     and the SessionStart hook only restores memory + session state, not loop
     schedules.

2. **Idempotent auto-start**
   - If the loop-tick is already running when a new session starts, the hook
     is a no-op (no log spam, no PID churn).
   - `daemon-manager.sh start-schedule <name>` already returns 0 if the schedule
     is running, so this is a thin wrapper.

3. **Streak observability**
   - A new `scripts/streak-tracker.sh` reads `.claude/loop/progress.md` and
     computes: consecutive-day PASS streak (max-streak vs current-streak),
     current-streak resets to 0 on any NEEDS_FIX / BLOCKED / FAIL / BUDGET_ABORT
     in the most recent day.
   - Output written to `.claude/loop/logs/streak-report.md` with: current_streak,
     max_streak, last_paused_at, last_tick_at.
   - Cron schedule: 1440m (daily at startup of new Claude Code session, or as
     a fallback cron alongside `cost-dashboard`).
   - This is M7-style: pure bash + awk, exits 0 on healthy / exits 2 on
     streak-break (wires into M8's notification channel via `$? -eq 2`).

4. **7-day unattended streak**
   - The acceptance signal for M9 itself: 7 consecutive days where
     `streak-report.md` shows `current_streak ≥ 7` AND the most recent tick
     verdict is `PASS`.
   - Streak is wall-clock-based (UTC day boundary); each day must contain at
     least 1 PASS entry in `progress.md`.
   - Human intervention during this period is allowed ONLY if a tick returns
     NEEDS_FIX (per M8 → notification fires); the loop itself is unattended.

5. **All prior milestones stable**
   - No regressions in:
     - `bash tests/test_worktree_helper.sh` (M6 regression)
     - `bash tests/test_cost_dashboard.sh` (M7 regression)
     - `bash tests/test_notify.sh` (M8 regression)
     - `bash tests/test_m4_langgraph_integration.py` (M4 regression)
     - `pytest tests/test_loop_infra.py` (M0-M1 infra)
     - `pytest src/ikigai/tests/test_canonical_scope.py` (drift invariants)
   - Acceptable: pre-existing `test_no_write_paths_in_operator_tui` failure
     (flagged in M5; not introduced by M9).

## Sub-tasks

| ID | Name | Estimated cost | Owner |
|----|------|---------------|-------|
| T-9.1 | SPEC.md | $0.00 | orchestrator (state machine) |
| T-9.2 | Wire auto-start into SessionStart hook | $0.00 | worker (bash) |
| T-9.3 | scripts/streak-tracker.sh | $0.00 | worker (bash) |
| T-9.4 | tests/test_streak_tracker.sh | $0.00 | worker (bash) |
| T-9.5 | Streak cron schedule | $0.00 | worker (bash) |
| T-9.6 | Regression + closeout (gated on 7-day streak) | $0.00 | orchestrator (state machine) |

## What M9 does NOT do

- **Does NOT** add new IKIGAI capabilities — M5 sealed that.
- **Does NOT** add new LangGraph graphs — M4 sealed that.
- **Does NOT** add new notification channels — M8 sealed that.
- **Does NOT** modify `constitution.md`, `AGENTS.md`, or `CLAUDE.md`.
- **Does NOT** introduce any new spec sections or PRD docs.

The "production" in M9 means *the existing infrastructure runs unattended*, not
*new infrastructure*.

## Open questions

- Q1: Should the streak tracker also fire on the same exit-2 spike pattern as
  cost-dashboard, OR use a separate `--reason streak_break` notification
  channel mapping? **Decision: separate reason** — clearer semantic for the
  operator ("streak broke at day N") vs ("cost spiked").
- Q2: What counts as a "day" for the 7-day streak — UTC calendar day, local
  calendar day, or rolling 24h window? **Decision: UTC calendar day** — same
  convention as M7's cost-dashboard (which uses `## YYYY-MM-DD` headers).

## Out of scope (backlog)

- Cross-platform cron (Windows Task Scheduler parity) — flagged in
  `~/.claude/projects/.../memory/cross-loop-redundancy.md` (3 redundant cron
  systems currently).
- Persistent PID recovery on Windows reboot — `nohup` does not survive Windows
  reboot the same way it survives POSIX reboots; a future M9.1 may add
  Windows-specific launchd/TaskScheduler integration.
- Distributed loop coordination across multiple `code_space/*` projects — the
  loop is currently single-project.