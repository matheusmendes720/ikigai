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
- **status:** pending
- **spec_ref:** `.claude/loop/constitution.md` (implicit)
- **acceptance:**
  - [ ] `.claude/loop/roadmap.md` exists
  - [ ] `.claude/loop/constitution.md` exists
  - [ ] `.claude/loop/progress.md` exists
  - [ ] `.claude/loop/loop-tick.sh` exists
  - [ ] `.claude/loop/loop-tick.bat` exists
  - [ ] `.claude/skills/loop-engineering/SKILL.md` exists
  - [ ] `.claude/agents/loop/orchestrator.md` exists
  - [ ] `.claude/agents/loop/worker.md` exists
  - [ ] `.claude/agents/loop/verifier.md` exists
  - [ ] `scripts/worktree-helper.sh` exists
- **estimated_cost_usd:** 0.50
- **estimated_minutes:** 2
- **attempts:** 0
- **last_attempt:** —
- **last_verdict:** —
- **notes:** This is the bootstrap check. If files don't exist, orchestrator creates them (or fails the tick if human-action needed).

### T-0.2 — First manual tick
- **status:** pending
- **acceptance:**
  - [ ] Run `bash .claude/loop/loop-tick.sh` (or `.bat`)
  - [ ] Orchestrator reads state, picks T-0.1
  - [ ] Worker runs in worktree, verifies files exist
  - [ ] Verifier returns PASS
  - [ ] `progress.md` has 1 new entry
  - [ ] Tick exits cleanly
- **estimated_cost_usd:** 1.00
- **estimated_minutes:** 5
- **attempts:** 0
- **last_attempt:** —
- **last_verdict:** —
- **notes:** First tick. Expect 1-2 retries to calibrate the prompt.

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

### M1 — Wire loop-tick.sh to claude-flow daemon
- T-1.1: Add `loop-tick` to `daemon-manager.sh` schedules
- T-1.2: Verify schedule shows in `daemon-manager.sh list`
- T-1.3: Wait 1h, confirm tick fired and progress.md updated

### M2 — Fill empty ikigai skills
- T-2.1: `.claude/skills/ikigai-daily/SKILL.md` — daily orchestrator invocation
- T-2.2: `.claude/skills/ikigai-weekly/SKILL.md` — weekly summary + hill-climb trigger
- T-2.3: `.claude/skills/ikigai-monthly/SKILL.md` — monthly review + roadmap adjustment
- T-2.4: `.claude/skills/ikigai-quarterly/SKILL.md` — quarterly re-prioritization

### M3 — First hill-climb cron
- T-3.1: Create `.claude/loop/hill-climb.sh`
- T-3.2: Add weekly schedule to daemon
- T-3.3: First run, review PR, merge

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
