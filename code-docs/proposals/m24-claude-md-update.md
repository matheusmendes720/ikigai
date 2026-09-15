# M24 — CLAUDE.md Update Proposal

**Type:** Doc-only change
**Auto-proposed by:** T-24.2 (loop-orchestrator)
**Status:** PROPOSED — awaiting human review and manual merge
**Date:** 2026-09-15

## Context

M24 investigation (T-24.1) found that only 1.5 scheduling systems exist on this host:
- claude-flow daemon (canonical, PID 1802, loop-tick RUNNING)
- SessionStart auto-start-loop-tick.sh (safety net, not competing scheduler)

The "3 redundant cron systems" claim in `roadmap.md` line 426 (M24 description) was refuted — Mavis cron, Claude Code Schedule, and Windows Task Scheduler do not actively fire `loop-tick.sh`.

## Proposed Addition to CLAUDE.md

Insert the following block after the "Global Conventions" section (after the table of rules, before "Build & Test"):

```markdown
## Cross-Loop Cron (canonical scheduler)

The **claude-flow daemon** (`.claude/helpers/daemon-manager.sh`) is the canonical scheduler for all loop-engineering tasks. It wins on:

- **Cost-cap enforcement** — per-schedule `cost_cap_usd` prevents runaway cost
- **Crash recovery** — nohup daemon + PID file auto-restarts
- **Notification integration** — M8 notify.sh wired on EXIT trap for HITL fatigue mitigation
- **Cross-platform** — works on Windows (Git Bash + WSL2) and POSIX

The SessionStart `auto-start-loop-tick.sh` hook is a **safety net** that delegates to `daemon-manager.sh start-schedule loop-tick` (idempotent). It is NOT a competing scheduler — it only re-starts the daemon if dead.

**No crontab, Mavis cron, or Windows Task Scheduler entries are required.** If you find any, they are stale and should be removed.

Schedules registered (as of 2026-09-15): `loop-tick` (60m, $5), `hill-climb` (168h, $10), `cost-dashboard` (1440m, $0.5), `streak-tracker` (1440m, $0.1).

To add a new schedule:

```bash
bash .claude/helpers/daemon-manager.sh add \
    --name <schedule_name> \
    --interval <duration> \
    --command '<command>' \
    --cost-cap-usd <float>
```

To list / stop / start / remove:

```bash
bash .claude/helpers/daemon-manager.sh list
bash .claude/helpers/daemon-manager.sh stop-schedule <name>
bash .claude/helpers/daemon-manager.sh start-schedule <name>
bash .claude/helpers/daemon-manager.sh remove <name>
```

## Backlog Item Closure

Backlog item 3 ("Cross-loop: Mavis cron + this daemon + Claude Code Schedule = 3 redundant systems — pick one") is **closed** by M24 SHIP. Investigation showed no Mavis cron or Claude Code Schedule actively fire loop-tick.sh. Canonical = claude-flow daemon.
```

## Rationale

Per orchestrator hard rule (`.claude/agents/loop/orchestrator.md`): "Never modify AGENTS.md or CLAUDE.md (propose, don't write)". This proposal respects that boundary — human review and manual merge required.

The proposed addition:

1. **Single source of truth** for canonical scheduler (no drift between roadmap.md / AGENTS.md / CLAUDE.md)
2. **Documents the 4 decision criteria** (cost-cap / recovery / notification / cross-platform) so future contributors don't re-litigate
3. **Closes backlog item 3** (Mavis cron claim was stale)
4. **Provides operator commands** (add/list/stop/start/remove) for new contributors

## Verification of Non-Edit

This proposal does NOT modify CLAUDE.md. The orchestrator created this proposal file only. To apply:

1. Human reviews the proposed text
2. Human edits CLAUDE.md directly (insert the block at the specified anchor)
3. Human commits with message: `docs: declare claude-flow daemon canonical scheduler (M24)`

## References

- `specs/M24-cross-loop-cron-dedup/SPEC.md` §"Canonical Scheduler Decision (T-24.2)"
- `.claude/loop/roadmap.md` M24 entry
- `.claude/loop/progress.md` M24-launch + T-24.1 entries
- `~/.claude/projects/.../memory/MEMORY.md` (loop-engineering infrastructure history)
