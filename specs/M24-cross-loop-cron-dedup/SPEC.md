# M24 — Cross-Loop Cron Dedup

**Status:** PENDING
**Created:** 2026-09-15
**Owner:** loop-orchestrator

## Goal

Consolidate 3 alleged redundant cron systems (Mavis cron + claude-flow daemon + Claude Code Schedule) into 1 canonical scheduler. Per backlog item 3 — having 3 parallel scheduling systems is a latent risk (each fires its own tick, drift between them, maintenance burden).

## Why

M1 SHIPPED claude-flow integration 2026-09-07 but didn't retire the other systems. The hypothesis is that 3 separate scheduling mechanisms may fire loop-tick.sh independently, causing:
- Duplicate tick execution
- Drift between systems (different cadences, different cost caps)
- Maintenance burden (changes must be applied to N places)
- Race conditions on shared resources (e.g. worktree cleanup)

## Acceptance Criteria

- [ ] **T-24.1** Investigate current state: enumerate all scheduling systems firing loop-tick.sh on this host (crontab, daemon-manager, Claude Code Schedule, Mavis, Task Scheduler on Windows, etc.). Document each system, its trigger frequency, and which scripts it fires.
- [ ] **T-24.2** Pick canonical scheduler (recommended: claude-flow daemon — has cost-cap + recovery support; already supports all 4 schedules). Document the rationale.
- [ ] **T-24.3** Retire the other 2 systems (if they exist): delete entries, document the canonical choice in CLAUDE.md. **If investigation reveals <3 systems actually exist, formalize this in CLAUDE.md and skip the retirement step (with documented evidence).**
- [ ] **T-24.4** Verify no double-firing for 24h after change (use progress.md timestamp dedup or daemon-manager log inspection)
- [ ] **T-24.5** Drift net 61/61 PASS preserved (config-only change)
- [ ] **T-24.6** All 23 prior milestones stable (regression sweep)

## Sub-tasks

### T-24.1 — Investigation phase
- **Goal:** Enumerate every scheduling system that could fire loop-tick.sh
- **Method:**
  1. `crontab -l` (Unix)
  2. `Get-ScheduledTask | Where-Object {$_.TaskPath -like "*loop-tick*"}` (Windows)
  3. `cat .claude/loop/schedules.json` + `bash .claude/helpers/daemon-manager.sh list`
  4. `grep -r "loop-tick" .claude/ scripts/ src/` for any other entry points
  5. `tasklist /FI "IMAGENAME eq scheduler.exe"` or `pgrep -fl cron` to find external schedulers
  6. Inspect `.claude/settings.json` SessionStart hook chain for any scheduler-triggering logic
  7. Check for Mavis cron (per AGENTS.md, this may or may not be a real system)
- **Deliverable:** `docs/superpowers/specs/2026-09-15-m24-cron-inventory.md` with table of all scheduling systems, their cadence, and what they fire.

### T-24.2 — Canonical selection
- **Goal:** Document which scheduler is canonical and why
- **Default:** claude-flow daemon (has cost-cap + recovery support; already supports all 4 schedules; integrated with M8 notification channel)
- **Decision criteria:**
  - Cost cap enforcement (daemon: ✓; crontab: ✗; Claude Code Schedule: ✗)
  - Recovery on crash (daemon: ✓ auto-restart; crontab: ✗)
  - Notification integration (daemon: ✓ via M8; others: ✗)
  - Cross-platform (daemon: ✓ via bash + WSL2; Claude Code Schedule: ✓; crontab: POSIX-only)
- **Deliverable:** Update SPEC.md §"Canonical Scheduler" with decision + rationale

### T-24.3 — Retirement phase (conditional)
- **If T-24.1 finds <3 systems:** No retirement needed. Document the actual count in CLAUDE.md "Cross-Loop Cron" section + close milestone.
- **If T-24.1 finds 3 systems:** Retire 2 non-canonical systems:
  - Delete crontab entries: `crontab -l | grep -v 'loop-tick\|hill-climb\|cost-dashboard\|streak-tracker' | crontab -`
  - Remove Claude Code Schedule entries (if any): edit `.claude/settings.json` schedule block
  - Document retirement in CLAUDE.md

### T-24.4 — Verification phase (24h no double-fire check)
- **Method:** After T-24.3 (or T-24.2 if no retirement needed), monitor progress.md for 24h. Count `loop-tick` entries per UTC hour — should be exactly 1 (or 0 on idle hours).
- **Acceptable:** ≤1 entry per 60-minute window
- **Failure:** ≥2 entries within a 60-minute window indicates double-firing from retired system not actually removed

### T-24.5 — Drift net preservation
- **Command:** `pytest src/ikigai/tests/test_canonical_scope.py src/ikigai/tests/test_drift_invariants.py src/ikigai/tests/test_drift_extended_invariants.py src/ikigai/tests/test_chat_repl.py`
- **Expected:** 61/61 PASS (35 + 7 + 11 + 8)

### T-24.6 — Regression sweep
- **Command:** `bash tests/test_worktree_helper.sh` + `bash tests/test_cost_dashboard.sh` + `bash tests/test_notify.sh` + `bash tests/test_streak_tracker.sh` + `bash tests/test_dispatch.sh` + `pytest tests/test_loop_infra.py tests/test_m4_langgraph_integration.py src/ikigai/tests/test_canonical_scope.py src/ikigai/tests/test_m5_ikigai_mcp_integration.py`
- **Expected:** All 6 bash suites + all 4 pytest suites PASS

## What M24 does NOT do

- Does NOT add new scheduling systems (no Task Scheduler entries, no new cron daemon)
- Does NOT modify loop-tick.sh / hill-climb.sh / cost-dashboard.sh / streak-tracker.sh (script bodies unchanged)
- Does NOT modify any code in src/ (config-only change + doc-only)
- Does NOT add cron-style logging (use existing progress.md + .claude-flow/logs/)
- Does NOT integrate with Mavis (if it exists, leave it — not in scope for the Life OS loop)

## Open Questions

1. **Does Mavis cron actually exist on this host?** AGENTS.md mentions it but no direct references found. If T-24.1 finds no Mavis, the "3 systems" claim is partially refuted (similar to M21 PROD_LAYERS widening).
2. **Does Claude Code Schedule have a schedule API?** As of 2026-09-15, no direct schedule primitive was observed. SessionStart hooks fire once per session, not on a timer.

## Out of Scope

- Replacing bash loop-tick.sh with TypeScript (backlog item 1 — separate milestone)
- Adding "tier by risk" review depth (backlog item 2)
- Migrating SPEC.md frontmatter (backlog item 4)

## Acceptance Tick Boxes

Mirrors roadmap.md acceptance. All 6 must be ✓ before milestone flips to STATUS: DONE.
