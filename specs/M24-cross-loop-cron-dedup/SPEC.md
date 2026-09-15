# M24 — Cross-Loop Cron Dedup

## Goal
Consolidate 3 redundant cron systems into 1 canonical scheduler.

## Investigation Findings (T-24.1)

### System 1: claude-flow daemon
- **Entry point:** `bash .claude/helpers/daemon-manager.sh`
- **Current schedule (schedules.json):** `loop-tick` runs `bash .claude/loop/loop-tick.sh` every 60m (3600s), cost_cap=$5.00
- **Live status (daemon-manager list):** RUNNING (PID 1802)
- **Recovery:** nohup daemon loop with PID file at `.claude-flow/schedules/loop-tick.pid`
- **Loop-tick fires:** YES — this is the canonical scheduler

### System 2: Mavis cron
- **Status:** NOT FOUND
- **Evidence:** Case-insensitive search across `.claude/` for `mavis|Mavis|MAVIS` returned zero live cron entries. Only mentions are:
  - `.claude/loop/roadmap.md` (line 287, 408, 426) — backlog item describing the problem
  - `.claude/loop/CURATED-TECHNIQUES.md` (lines 32, 66) — references to MiniMax-Mavis as a third-party tool
  - `.claude/loop/logs/*.log` — historical tick logs referencing the dedup backlog item
- **Conclusion:** Mavis cron does not exist as a live scheduled task. The 3-redundant-systems claim in roadmap.md is stale/inaccurate as of T-24.1.

### System 3: Claude Code Schedule
- **Hooks in settings.json:** `SessionStart` hook at line 58-76 fires `bash scripts/auto-start-loop-tick.sh`
- **Trigger:** Fires once per Claude Code session start (not on a timer)
- **auto-start-loop-tick.sh behavior:** Calls `daemon-manager.sh start-schedule loop-tick` (idempotent — exits 0 if already running). This is a **safety net** that ensures the daemon schedule is alive after a session restart, NOT an independent cron.
- **Loop-tick fires:** INDIRECT — only if the daemon is dead, this re-starts it
- **Conclusion:** Not a competing cron. This is a session-start guardian that delegates to the daemon.

### System 4: Windows Task Scheduler
- **Tasks found:** None fire `loop-tick.sh`
- **Evidence:** `schtasks /query /fo LIST` shows 30+ tasks (Brave, NVIDIA, Git for Windows, etc.). Zero references to `loop-tick` or `.claude/loop/`.
- **Conclusion:** Windows Task Scheduler is not involved.

## Recommendation
Canonical scheduler = **claude-flow daemon** (has cost-cap + recovery support per M1).

The `auto-start-loop-tick.sh` hook in `SessionStart` should be **retained** as a session-start guardian that ensures the daemon is alive — it is not a competing scheduler, but rather a safety net.

The claim of "3 redundant systems" in roadmap.md line 426 and the backlog item are **stale** — Mavis cron was never a live system in this repo. Only 1.5 systems exist: the daemon (canonical) + the session-start guardian (safety net).

## Acceptance Criteria (for T-24.2..T-24.4)
- [ ] T-24.2: Confirm daemon-manager is canonical (daemon-manager.sh list confirms loop-tick RUNNING)
- [ ] T-24.3: Retire other systems — N/A (Mavis cron not found; auto-start-loop-tick.sh retained as guardian)
- [ ] T-24.4: Verify no double-firing for 24h after change
- [ ] Drift net preserved
- [ ] All 23 prior milestones stable

## Out of Scope
- Adding new cron systems
- Changing schedule frequency
- Cost-cap modifications
- Mavis cron (not present in this codebase)
