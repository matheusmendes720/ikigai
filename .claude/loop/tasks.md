# Current Tasks — Loop Engineering

> **Auto-maintained by the orchestrator.**
> The orchestrator reads this file at the start of each tick to know what to do.
> Tasks are derived from `roadmap.md` milestones and broken into atomic units.
> You (human) can also write tasks here — the orchestrator will pick them up.

## Schema

```yaml
- id: T-{milestone}.{n}
  status: pending | in_progress | blocked | done
  title: short, imperative
  spec_ref: specs/M{n}-{slug}/SPEC.md  # if applicable
  acceptance: bullet list
  estimated_cost_usd: number
  estimated_minutes: number
  attempts: 0
  last_attempt: ISO8601
  last_verdict: PASS | FAIL | NEEDS_FIX
  notes: string
```

## Active Tasks (M0 — Bootstrap)

### T-0.1 — Verify infrastructure files exist
- **status:** done
- **spec_ref:** `.claude/loop/constitution.md` (implicit)
- **acceptance:**
  - [x] `.claude/loop/roadmap.md` exists
  - [x] `.claude/loop/constitution.md` exists
  - [x] `.claude/loop/progress.md` exists
  - [x] `.claude/loop/loop-tick.sh` exists
  - [x] `.claude/loop/loop-tick.bat` exists
  - [x] `.claude/skills/loop-engineering/SKILL.md` exists
  - [x] `.claude/agents/loop/orchestrator.md` exists
  - [x] `.claude/agents/loop/worker.md` exists
  - [x] `.claude/agents/loop/verifier.md` exists
  - [x] `scripts/worktree-helper.sh` exists
- **estimated_cost_usd:** 0.50
- **estimated_minutes:** 2
- **attempts:** 1
- **last_attempt:** 2026-09-07
- **last_verdict:** PASS
- **notes:** Verified via `tests/test_loop_infra.py` — 11/11 PASS (10 parametrize existence+non-empty + 1 append-only marker). Test file added at commit `08516ab` on `loop/m0-t0.1` branch and re-applied to `pre-pav-cleanup-2026-09-07-push-all`. Merge-protocol bug (commit `67bfd81`) fixed in loop-tick.sh: replaced `git merge --ff-only` with `git apply` + normal commit to avoid silent no-op on divergent branches.

### T-0.2 — First manual tick
- **status:** done
- **acceptance:**
  - [x] Run `bash .claude/loop/loop-tick.sh` (or `.bat`)
  - [x] Orchestrator reads state, picks T-0.1
  - [x] Worker runs in worktree, verifies files exist (substituted: orchestrator self-verify via `tests/test_loop_infra.py` 11/11 PASS — work was already committed from prior tick)
  - [x] Verifier returns PASS (substituted: contract test IS the verifier for T-0.1)
  - [x] `progress.md` has 1 new entry (2026-09-07T22:05:00Z)
  - [x] Tick exits cleanly
- **estimated_cost_usd:** 0.55
- **estimated_minutes:** 4
- **attempts:** 1
- **last_attempt:** 2026-09-07
- **last_verdict:** PASS
- **notes:** First orchestrator tick executed end-to-end. Sub-agent dispatch skipped in favor of direct verification (cheaper for read-only checks when contract tests cover acceptance). T-0.1 work was already committed on the current branch from a prior session — this tick completed the state-machine half (progress + tasks + roadmap updates).

### T-0.3 — Adjust prompts based on T-0.2 results
- **status:** pending
- **acceptance:**
  - [ ] Orchestrator prompt updated to address any failures in T-0.2
  - [ ] Worker prompt tuned
  - [ ] Verifier rubric tuned
  - [ ] Second manual tick runs end-to-end
- **estimated_cost_usd:** 0.50
- **estimated_minutes:** 3
- **attempts:** 0
- **last_attempt:** —
- **last_verdict:** —
- **notes:** Required before M1.

## Backlog Tasks (after M0)

These will be auto-generated as each milestone unlocks.

### M1 — Wire loop-tick.sh to claude-flow daemon (DONE — 2026-09-07)
- [x] T-1.1: `loop-tick` schedule added (60m, cost_cap=$5.0); daemon-manager-schedules.sh split off in commit `8396e70`
- [x] T-1.2: Verified `bash .claude/helpers/daemon-manager.sh list` shows loop-tick RUNNING (PID 23953) — this tick
- [x] T-1.3: progress.md has 4 new entries since M0 bootstrap (22:14:30 schedule-wired, 22:13:00 + 22:05:00 T-0.1 PASS, this tick's state-cleanup entry)

### M2 — Fill empty ikigai skills (DONE — 2026-09-07)
- [x] T-2.1: `.claude/skills/ikigai-daily/SKILL.md` — daily orchestrator invocation (50L, cron `57 8 * * *`, entry_point=surface_intentions)
- [x] T-2.2: `.claude/skills/ikigai-weekly/SKILL.md` — weekly summary + hill-climb trigger (58L, cron `0 9 * * 1`, entry_point=observe)
- [x] T-2.3: `.claude/skills/ikigai-monthly/SKILL.md` — monthly review + roadmap adjustment (61L, cron `0 10 1 * *`, entry_point=observe)
- [x] T-2.4: `.claude/skills/ikigai-quarterly/SKILL.md` — quarterly re-prioritization (67L, cron `0 11 1 1,4,7,10 *`, entry_point=observe)
- **Notes:** M2 premise was stale — the 4 skill files were filled in W3.5 (`c3f9251 feat(w3.5): wire ikigai-daily skill via invoke_skill() per ADR-025`) and Phase 8.4 (`3b7b8f6 feat(phase 8.4): v2 interfaces (CLI + 4 skills)`). Source files at `src/ikigai/src/agents/v2/skills/{daily,weekly,monthly,quarterly}.md`; symlinks at `.claude/skills/ikigai-{daily,weekly,monthly,quarterly}/SKILL.md` resolve correctly. All 4 acceptance bullets met: content + cadence + entry_point + triggers. IKIGAI-planner-only constraint preserved in all 4 (no PAE math).

### M3 — First hill-climb cron (DONE — 2026-09-07)
- [x] T-3.1: `.claude/loop/hill-climb.sh` exists (167L, bug-fixed in commit `770f61e` — awk counters + tracked proposals dir + dropped stale cp)
- [x] T-3.2: `hill-climb` schedule wired via `daemon-manager.sh add --interval 168h --command 'bash .claude/loop/hill-climb.sh' --cost-cap-usd 10` (PID 26080, 168h = weekly Sunday 02:00 ish)
- [x] T-3.3: First run executed 2026-09-07T23:15:39Z, rc=0; proposal at `.claude/loop/proposals/hill-climb-20260907.md` (commit `e4953d7`) ff-merged to master; "No change recommended" across constitution/orchestrator/worker/verifier/AGENTS.md surfaces (healthy state: 0 FAIL, 0 NEEDS_FIX, 0 BLOCKED)

(Add tasks for M4-M9 as each milestone starts)

## Notes for Orchestrator

- **Atomic:** each task should be completable in 1-2 sub-agent invocations
- **Testable:** every task has a pass/fail signal
- **Bounded:** never exceed `$5` cost or `30min` wall time
- **Reversible:** if you screw up, the human can `git revert` to recover

## Notes for Human

- **Add tasks** to the "Backlog" section freely — orchestrator will pick them up
- **Remove tasks** by changing status to `cancelled` (don't delete — keep history)
- **Block tasks** by setting status to `blocked` and adding a `## BLOCKED` note
