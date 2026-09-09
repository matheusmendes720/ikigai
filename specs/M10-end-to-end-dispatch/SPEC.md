# M10 — End-to-End Loop Dispatch

> **Constitution:** .claude/loop/constitution.md
> **Created:** 2026-09-08
> **Owner:** loop-orchestrator
> **Status:** IN-PROGRESS

## Goal

Wire the existing M0–M9 pieces into a **single atomic dispatch primitive** —
`scripts/dispatch.sh <task_id>` — that runs the full chain (read state →
spawn worker in worktree → implement → verifier → promotion → notify →
progress append → tick close) as one terminal unit, so another session can
advance milestones via one CLI call instead of orchestrating 5–6 separate
scripts manually.

## Why

- Today the chain exists as 5–6 separate scripts (`loop-tick.sh`,
  `worktree-helper.sh`, `daemon-manager.sh`, `cost-dashboard.sh`, `notify.sh`,
  `streak-tracker.sh`) wired together by hand in M0–M9.
- The hill-climb cron (M3) and the production-mode auto-start (M9) already
  invoke parts of the chain unattended, but a deliberate "dispatch THIS task
  end-to-end" primitive is missing.
- Without it, every ad-hoc milestone advance requires manual orchestration of
  worktree creation → sub-agent spawn → verifier dispatch → commit → push →
  roadmap flip → notify. This is the loop's own meta-tooling gap.

## Acceptance Criteria

1. **Single-command dispatch**
   - `bash scripts/dispatch.sh <task_id>` (e.g. `T-10.2`) reads
     `.claude/loop/tasks.md`, locates the entry, advances it to terminal
     state, and exits 0 on PASS / non-zero on FAIL.
   - No manual intervention between invocation and terminal state.

2. **Atomic promotion**
   - On verifier PASS: commit + push + roadmap STATUS flip + tasks.md
     status flip happen as one unit. If any step fails, the chain rolls back
     (no partial roadmap flip with no commit, no push with local-only commit).
   - On FAIL: zero state mutation outside `.claude/loop/logs/` and the
     worker's per-tick log.

3. **Idempotent replay**
   - Re-dispatching an already-`status: done` task returns 0 with
     `already_complete` on stdout and does NOT re-run worker / verifier /
     notify / commit.
   - Re-dispatching a `status: in_progress` task picks up from where the
     prior invocation left off (resume, not restart).

4. **Notification integration**
   - `scripts/notify.sh` fires with `reason=tick_pass` on PASS,
     `reason=tick_fail` on FAIL, `reason=needs_fix` on NEEDS_FIX (per M8's
     reason list). Respects M8's idempotency / cooldown.

5. **Determinism gate before LLM**
   - Before invoking any sub-agent, `dispatch.sh` runs the same regression
     sweep as M9 acceptance #5: `bash tests/test_worktree_helper.sh` +
     `test_cost_dashboard.sh` + `test_notify.sh` + `test_streak_tracker.sh` +
     `pytest tests/test_loop_infra.py tests/test_m4_langgraph_integration.py
     src/ikigai/tests/test_canonical_scope.py`.
   - If any sub-suite fails, dispatch exits 1 with `regression_failed` and
     does NOT spawn the worker.

## Sub-tasks

| ID | Name | Estimated cost | Owner |
|----|------|---------------|-------|
| T-10.1 | `scripts/dispatch.sh` scaffold + tests | $0.00 | worker (bash) |
| T-10.2 | Wire M6 / M7 / M8 hooks into dispatch.sh EXIT trap | $0.00 | worker (bash) |
| T-10.3 | Acceptance — single-command dispatch + regression sweep + closeout | $0.00 | orchestrator (state machine) |

## What M10 does NOT do

- **Does NOT** introduce a new orchestrator LLM — uses the existing
  `.claude/agents/loop/orchestrator.md` prompt; dispatch.sh is the bash
  wrapper, not a replacement.
- **Does NOT** add a new notification channel — M8's `notify.sh` is the
  canonical pipe; dispatch.sh adds the `tick_*` reason mappings.
- **Does NOT** modify `constitution.md`, `AGENTS.md`, or `CLAUDE.md`.
- **Does NOT** introduce parallelism that bypasses M6's worktree isolation.

The "dispatch" in M10 means *the existing infrastructure runs as one chain*,
not *new infrastructure*.

## Open questions

- Q1: Should `dispatch.sh` accept a `--dry-run` flag that walks the full
  chain but skips the commit/push/notify step? **Default: yes** — mirrors
  M7's `--dry-run` pattern, lets the orchestrator verify the chain end-to-end
  without leaving artifacts.
- Q2: When the regression sweep fails pre-dispatch, should the failure be
  reported as `BLOCKED` (needs human) or `FAIL` (auto-retry once)? **Default:
  BLOCKED** — pre-existing regression failure is not a dispatch problem, it's
  a state problem.

## Out of scope (backlog)

- Cross-machine dispatch (run worker on a different host) — current dispatch
  is local-only.
- Dispatch UI (TUI panel for "dispatch this task now") — gated on demand.
- Parallel dispatch of multiple tasks — current M10 dispatches ONE task per
  invocation. M6 worktree isolation already covers parallel sub-agents within
  one tick; explicit multi-task dispatch is M10.1+ territory.

## Architecture Notes

- Pure bash wrapper around existing scripts (mirrors M6/M7/M8 style: no
  Python, no new dependencies).
- Single EXIT trap handles all failure modes (worktree cleanup → notify →
  progress append), LIFO order matching M8's pattern.
- Reads `.claude/loop/tasks.md` for task metadata; writes back status flip
  in-place (file is the SOT — same model as M9's state-machine entry).
- `--task-id <id>` is positional (matches `loop-tick.sh --graph <key>`
  pattern from M4).
