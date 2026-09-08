# Life-OSS Roadmap — Loop Engineering Edition

> **Source of truth for the autonomous loop.**
> The orchestrator agent reads this file every tick to decide what to do next.
> Add milestones here. Mark them `STATUS: DONE` when verified. Never delete.

## Sequencing rules

- Milestones are sequential by default (M1 → M2 → M3)
- Parallel milestones allowed only with `[P]` tag and no shared dependencies
- Each milestone has a SPEC.md in `specs/M{n}-{slug}/SPEC.md` (create before starting)
- Each milestone passes the constitution gate (`.claude/loop/constitution.md`)

## Current Roadmap

### M0 — Bootstrap (STATUS: DONE)
- **What:** Initialize the loop engineering infrastructure itself
- **Why:** The loop can't run until it has agents, state files, and a constitution
- **Acceptance:**
  - [x] `.claude/loop/roadmap.md` exists (this file)
  - [x] `.claude/loop/tasks.md` exists and is empty
  - [x] `.claude/loop/progress.md` exists with `STATUS: INITIALIZED`
  - [x] `.claude/loop/constitution.md` exists (already done)
  - [x] `.claude/agents/loop/{orchestrator,worker,verifier}.md` exist
  - [x] `.claude/loop/loop-tick.{sh,bat}` exist
  - [x] `.claude/skills/loop-engineering/SKILL.md` exists
  - [x] One manual tick runs end-to-end (no cron)
- **Dependencies:** none
- **Estimated ticks:** 1-2

### M1 — Wire loop-tick.sh to claude-flow daemon (STATUS: DONE)
- **What:** Add `loop-tick` to the existing claude-flow daemon schedules
- **Why:** Today the daemon runs `audit` (4h) and `optimize` (2h) — add a 60m loop-tick
- **Acceptance:**
  - [x] `bash .claude/helpers/daemon-manager.sh list` shows `loop-tick` schedule
  - [x] After 1h, `progress.md` has at least 1 new entry (verified by 2026-09-07T22:14:30Z entry + this tick's entry)
  - [x] No manual intervention required
- **Dependencies:** M0
- **Estimated ticks:** 1

### M2 — Fill empty ikigai skills (STATUS: DONE)
- **What:** The 4 ikigai skills (daily, weekly, monthly, quarterly) are 0 bytes. Build them as loop components.
- **Why:** These are the obvious integration points for the loop engineering pattern
- **Acceptance:**
  - [x] `.claude/skills/ikigai-daily/SKILL.md` has content (invoke orchestrator with daily scope)
  - [x] Same for weekly/monthly/quarterly
  - [x] Each has a clear "what runs when" cadence
- **Dependencies:** M1
- **Estimated ticks:** 2-4
- **Completed:** 2026-09-07 (commit `c3f9251` W3.5 + `3b7b8f6` Phase 8.4 — filled in earlier waves, closed retroactively this tick)

### M3 — First hill-climb cron (STATUS: DONE)
- **What:** Weekly analysis of `progress.md` + `.swarm/memory.db` + `progress.md`
- **Why:** Outer loop 4. Improves the harness itself over time.
- **Acceptance:**
  - [x] `.claude/loop/hill-climb.sh` exists (167L, bug-fixed 2026-09-07)
  - [x] Runs every Sunday 02:00 via daemon (cron `hill-climb` PID 26080, 168h interval, cost_cap=$10)
  - [x] Output: PR with proposed AGENTS.md/SKILL.md updates (branch `hill-climb/YYYYMMDD` + `proposals/hill-climb-YYYYMMDD.md`, ff-merged to master)
  - [x] First run completed and reviewed (2026-09-07T23:15:39Z, rc=0, proposal e4953d7; "No change recommended" across all 5 surfaces — healthy state, no failures/retries)
- **Dependencies:** M2
- **Estimated ticks:** 1-2 (then 1/week)
- **Completed:** 2026-09-07 — cron fired clean after 3-bug fix (commit `770f61e`): awk counters replace grep-double-zero, proposal dir moved from gitignored `logs/` to tracked `proposals/`, stale cp + double-add dropped. Aggregate stats at first review: 10 ticks analyzed, 6 PASS / 0 FAIL / 0 NEEDS_FIX / 0 BLOCKED, $1.80 cumulative cost, 60% pass rate.

### M4 — Integrate with LangGraph graphs (STATUS: DONE)
- **What:** Wrap the 3 graphs actually registered in `langgraph.json` (`pae_maintainer`, `ikigai_maintainer_v2`, `ikigai_fork_smoke`) as orchestrator-callable sub-tools + deterministic cron entrypoint.
- **Why:** Today the graphs are manual-invocation via `make dev-graph NAME=<x>`. Make them dispatchable from the loop orchestrator AND from cron unattended (no LLM cost per tick).
- **Spec:** `specs/M4-langgraph-integration/SPEC.md` (verified 2026-09-07, actual registry — CLAUDE.md table of 5 graphs is stale)
- **Acceptance:**
  - [ ] Orchestrator prompt registers 3 graph names as callable tools with one-line invocation syntax
  - [ ] `SqliteSaver` checkpoint file at `.swarm/langgraph_checkpoint.db` shared across ticks (`thread_id` survives daemon restarts)
  - [ ] `bash .claude/loop/loop-tick.sh --graph <key>` flag added — deterministic gate that runs named graph end-to-end, exits with terminal code, no orchestrator LLM
  - [ ] `tests/test_m4_langgraph_integration.py` (5/5 PASS) exercises each graph + asserts checkpoint DB exists
  - [ ] No regression in `tests/test_loop_infra.py` (11/11), drift 33/33, interfaces 68/68
- **Dependencies:** M3
- **Estimated ticks:** 3-5

### M5 — IKIGAI MCP integration (STATUS: IN-PROGRESS)
- **Spec:** `specs/M5-ikigai-mcp-integration/SPEC.md` (created 2026-09-08; live tool count = 14 tools + 6 resources, NOT 19 as roadmap claimed)
- **What:** Orchestrator uses IKIGAI MCP tools (19 total) for the "research" + "knowledge" + "task" workflow
- **Why:** Today IKIGAI is invoked manually via `ikigai.bat agent`. Make it accessible from the loop.
- **Acceptance:**
  - [ ] Orchestrator prompt includes IKIGAI tool list
  - [ ] One tick completes a task using IKIGAI MCP successfully
- **Dependencies:** M4
- **Estimated ticks:** 2-3

### M6 — Worktree isolation helper (STATUS: PENDING)
- **What:** `scripts/worktree-helper.sh` creates/destroys git worktrees per sub-agent
- **Why:** Prevent parallel sub-agents from stepping on each other
- **Acceptance:**
  - [ ] Script creates worktree at `.worktrees/m-{id}/`
  - [ ] Auto-cleanup post-merge
  - [ ] Tests pass on at least 3 milestone executions
- **Dependencies:** M5
- **Estimated ticks:** 1

### M7 — Cost dashboard (STATUS: PENDING)
- **What:** Daily cron writes a `cost-report.md` to `.claude/loop/logs/`
- **Why:** "Loop brittleness" + "runaway cost" are top risks (Ronacher)
- **Acceptance:**
  - [ ] `cost-report.md` shows ticks/day, $USD/day, $USD/tick avg
  - [ ] Spike detection (>$10/day) triggers alarm
- **Dependencies:** M6
- **Estimated ticks:** 1

### M8 — Notification channel (STATUS: PENDING)
- **What:** Wire Telegram/Feishu/email for FAIL/NEEDS_FIX alerts
- **Why:** "HITL fatigue" mitigation. Only alert when intervention needed.
- **Acceptance:**
  - [ ] One channel configured
  - [ ] Test: trigger NEEDS_FIX, receive notification
- **Dependencies:** M7
- **Estimated ticks:** 1

### M9 — Production mode (STATUS: PENDING)
- **What:** Cron auto-starts on session start, runs 24/7, only needs human on NEEDS_FIX
- **Why:** The actual goal of loop engineering
- **Acceptance:**
  - [ ] 7-day streak of ticks without human intervention
  - [ ] All 8 prior milestones stable
- **Dependencies:** M8
- **Estimated ticks:** 7-14 days of unattended operation

## Backlog (not yet sequenced)

- [ ] Replace bash `loop-tick.sh` with TypeScript version (cross-platform)
- [ ] Add "tier by risk" review depth (per @addyosmani)
- [ ] Cross-loop: Mavis cron + this daemon + Claude Code Schedule = 3 redundant systems — pick one
- [ ] Migrate SPEC.md frontmatter to use `constitution.md` references
- [ ] Add `examples/` directory with 3 working milestones (M0, M1, M5)

## Adding a new milestone

```markdown
### M{n} — {title} (STATUS: PENDING)
- **What:** one sentence
- **Why:** the value it unlocks
- **Acceptance:** bullet list of testable conditions
- **Dependencies:** M{x} (or "none")
- **Estimated ticks:** 1-5
```

Then create `specs/M{n}-{slug}/SPEC.md` with full acceptance criteria.

## Marking DONE

When verifier returns PASS:
1. Orchestrator appends to `progress.md` with verdict + commit SHA
2. Orchestrator edits THIS file: `### M{n} — {title} (STATUS: DONE)`
3. Next tick picks up the next milestone
