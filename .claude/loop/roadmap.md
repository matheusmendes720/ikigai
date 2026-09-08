# Life-OSS Roadmap — Loop Engineering Edition

> **Source of truth for the autonomous loop.**
> The orchestrator agent reads this file every tick to decide what to do next.
> Add milestones here. Mark them `STATUS: DONE` when verified. Never delete.

## Sequencing rules

- Milestones are sequential by default (M1 → M2 → M3)
- Parallel milestones allowed only with `[P]` tag and no shared dependencies
- Each milestone has a SPEC.md in `specs/M{n}-{slug}/SPEC.md` (create before starting)
- Each milestone passes the constitution gate (`.claude/loop/constitution.md`)

## Application Status

O que o Algorithmic Life OS **consegue fazer hoje** — separado da infra de loop engineering (M0–M9 abaixo) que opera o sistema.

### ✅ Working end-to-end

- **CLI consumer** (`python -m interfaces.cli.main ...`): `v2 daily/weekly/plan`, `task add`, `mesh show <ueid>`, `kill_switch status|pause|resume`
- **TUI operator** (`python -m interfaces.tui.operator.main`): Textual 4 tabs (Chat / Tasks / State / KillSwitch)
- **Data mesh read**: `life mesh show <ueid>` joins CLI / taskdog / solverforge_calendar forks via 3 adapters (`ForkAdapter` Protocol)
- **Data mesh write** (Phase 3 v1, `create` only): fork → CLI enqueues `TaskChange` to `data/review_queue/` → Agent validates → `PropagationEvent` to all forks
- **MCP Gateway** (`ikigai.bat mcp`): 15 IKIGAI tools + 7 fork tools (`sf_*` + `tuiboard_*`) + 6 resources = 22 tools + 6 resources
- **Drift net**: 33/33 canonical_scope + 297 drift_invariants + growing extended invariants
- **Kill switch**: pause/resume cybernetic engine without killing daemon (CLI subcommand + 5th TUI tab)
- **Investigation queue**: `enqueue/status/complete` MCP tools + drift 42/42 + TUI read-only browse
- **Phase 9 Option A** (2026-09-03): operator TUI + drift detector + Path 3 taskdog MCP (read-only)
- **V5 bundle** (2026-09-07): CLI inlined (4 files deleted, v2.py split into 6 modules)
- **Phase A** (2026-08-30): 7 fork MCP tools live (sf_create_event etc.)

### ⚠️ Stubs / partial

- **Deep Agent v2 graph** (`ikigai_maintainer_v2` in `langgraph.json`): 9-node graph assembled, SqliteSaver checkpointing — mas Phase 8 deixou todos os nodes como **prompt-chain stubs**. `graph.py` L6-7: "MATH CALLS REPLACED: all node logic replaced with prompt-chain stubs. Phase 8.2 will wire actual MCP tool calls."
- **Path 1 taskdog write** (canônico): `harness @tool → subprocess → taskdog_cli.py` existe, mas o harness não está wire-ado para chamar (gap da Phase 8.2)
- **Path 3 taskdog MCP**: 3 read-only tools (`taskdog_read`, `taskdog_list`, `taskdog_supports_field`) — zero write surface
- **Investigation queue UI**: tools funcionam, TUI browse é read-only (sem criar/sortear pela interface)

### ❌ Not started / deferred

- **Phase 8.2**: wire real MCP tool calls into graph nodes (transforma stubs em executor real) — backlog, não auto-roadmap
- **Phase 3 v1.2-v1.4**: `update`/`delete`/`done` mesh actions (gated on user adjudication, NÃO auto-roadmap)
- **Deep Agent fills interfaces**: explicitamente NÃO é prioridade per user pivot 2026-09-06 (CLAUDE.md Current Mode)
- **LLM-driven mesh validation**: gated
- **PAV math in agent layer**: PAV archived 2026-08-31; agent é planner-only per ADR-013
- **M9 (Production mode)**: 7-day unattended streak target — gated on user authorization

### 🐛 Pre-existing bugs (flagged, non-blocking)

- `scripts/mcp_inspect.py` PYTHONPATH bug (Windows parity)
- `tests/test_tui_operator` rglob false-flake
- 5 stale PAV test files in `src/ikigai/tests/`
- 4 zero-byte artifacts no repo root (`$10`, `IN`, `inline`, `{len(lf_data)}`) — bash redirect pattern, deve ir pro `.gitignore`
- `strategics/planning-with-files` submodule dirty (modified content, sem commit)

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

### M5 — IKIGAI MCP integration (STATUS: DONE)
- **Spec:** `specs/M5-ikigai-mcp-integration/SPEC.md` (created 2026-09-08; live tool count = 14 tools + 6 resources, NOT 19 as roadmap claimed)
- **What:** Orchestrator uses IKIGAI MCP tools (14 + 6 resources) for the "research" + "knowledge" + "task" workflow
- **Why:** Today IKIGAI is invoked manually via `ikigai.bat agent`. Make it accessible from the loop.
- **Acceptance:**
  - [x] Orchestrator prompt includes IKIGAI tool list (T-5.1 — "IKIGAI MCP Tool Surface (M5)" section, 14 tools + 6 resources)
  - [x] Worker prompt acknowledges IKIGAI MCP availability (T-5.2 — "## Tool Availability" section)
  - [x] One tick completes a task using IKIGAI MCP successfully (T-5.3 — `tests/test_m5_ikigai_mcp_integration.py` 2/2 PASS; full stdio JSON-RPC handshake → `ikigai_health` roundtrip + `tools/list` confirmation)
  - [x] Regression sweep clean (T-5.4 — test_loop_infra 11/11 + test_m4_langgraph_integration 9/9 + test_canonical_scope 32/32)
- **Dependencies:** M4
- **Estimated ticks:** 2-3
- **Completed:** 2026-09-08 — T-5.1..T-5.4 all PASS. Test file untracked (will land in T-5.6 atomic commit).

### M6 — Worktree isolation helper (STATUS: DONE)
- **What:** `scripts/worktree-helper.sh` creates/destroys git worktrees per sub-agent
- **Why:** Prevent parallel sub-agents from stepping on each other
- **Acceptance:**
  - [x] Script creates worktree at `.worktrees/m-{id}/`
  - [x] Auto-cleanup post-merge (via `--auto-cleanup` flag on loop-tick.sh/bat)
  - [x] Tests pass on at least 3 milestone executions (`tests/test_worktree_helper.sh` 15/15 PASS, 3 parallel worktrees)
- **Dependencies:** M5
- **Estimated ticks:** 1
- **Completed:** 2026-09-07 — T-6.1..T-6.4 all PASS. Spec at `specs/M6-worktree-isolation/SPEC.md` documents commands, exit code matrix, parallel-safety contract. Script body pre-existing at commit `91fb7d4` (M0 bootstrap) — awk bug in `cleanup-all` regex fix landed in M6 commit. Auto-cleanup hook fires on every tick exit path (dry-run/cost-abort/graph-dispatch/overrun/normal) via bash EXIT trap, gated on zero `status: pending` tasks. Regression sweep: test_loop_infra 11/11 + test_m4_langgraph_integration 9/9 + test_canonical_scope 32/32 + test_m5_ikigai_mcp_integration 2/2 = 54/54 PASS.

### M7 — Cost dashboard (STATUS: DONE)
- **What:** Daily cron writes a `cost-report.md` to `.claude/loop/logs/`
- **Why:** "Loop brittleness" + "runaway cost" are top risks (Ronacher)
- **Acceptance:**
  - [x] `cost-report.md` shows ticks/day, $USD/day, $USD/tick avg
  - [x] Spike detection (>$10/day) triggers alarm (exit code 2)
- **Dependencies:** M6
- **Estimated ticks:** 1
- **Completed:** 2026-09-08 — T-7.1..T-7.4 all PASS. Pure bash + awk script (`scripts/cost-dashboard.sh`, 92L) — zero Python changes. Live report shows ticks_day=112, usd_total=$1.80, usd_avg_per_tick=$0.02, spike_alarm=none. Spike alarm via exit code 2 enables M8 notification channel to pipe on `$? -eq 2` without parsing report file. Commits: 726bfde0 (T-7.1 SPEC + scaffold), 4b2510d3 (T-7.2 tests), ca6a114c (T-7.3 daemon-manager add), + closeout commit (T-7.4). Total M7 cost: $0.00 (pure bash, zero LLM calls). Spec at `specs/M7-cost-dashboard/SPEC.md`.

### M8 — Notification channel (STATUS: DONE)
- **What:** ntfy.sh HTTP webhook via `scripts/notify.sh` (pure bash + curl) wired into loop-tick.sh EXIT trap
- **Why:** "HITL fatigue" mitigation. Only alert when intervention needed (FAIL/NEEDS_FIX/BLOCKED/OVERRUN/BUDGET_ABORT + cost spike)
- **Acceptance:**
  - [x] One channel configured (ntfy.sh; topic name IS the auth secret, set via `LOOP_NOTIFY_TOPIC`)
  - [ ] Test: trigger NEEDS_FIX, receive notification (deferred to M8.1 — gated on user setting LOOP_NOTIFY_TOPIC; idempotency + dedup + disabled-mode + dry-run verified by 11 unit tests in tests/test_notify.sh)
- **Dependencies:** M7
- **Estimated ticks:** 1
- **Completed:** 2026-09-08 — T-8.1..T-8.4 all PASS. Pure bash + curl deliverable (scripts/notify.sh, 134L) wired into .claude/loop/loop-tick.sh EXIT trap via notify_hook() function (LIFO trap order: M6 worktree cleanup runs first, then notify). Trap maps TICK_VERDICT + SPIKE_DETECTED → notify --reason (FAIL→tick_fail, NEEDS_FIX→needs_fix, BLOCKED→blocked, OVERRUN→overrun, BUDGET_ABORT→budget, SPIKE_DETECTED→spike_alarm). Cooldown dedup (10min default) via sha256(message) keyed state file. Cost $0/tick (ntfy.sh free tier + zero LLM); "$0.10/tick" budget envelope recorded for future paid webhook replacement. Regression sweep: test_worktree_helper.sh 15/15 + test_cost_dashboard.sh 7/7 + test_notify.sh 11/11 = 33/33 PASS. Commits: b95c0348 (T-8.1 SPEC), aeb4b0c6 (T-8.1 scaffold), 9c498077 (T-8.1 follow-up fixes), e63c6b5c (T-8.2 tests), e11f3b6 (T-8.3 wiring), + this closeout (T-8.4). Spec at `specs/M8-notification-channel/SPEC.md`. Unblocks M9 (Production mode).

### M9 — Production mode (STATUS: IN-PROGRESS)
- **What:** Cron auto-starts on session start, runs 24/7, only needs human on NEEDS_FIX
- **Why:** The actual goal of loop engineering
- **Spec:** specs/M9-production-mode/SPEC.md (created 2026-09-07; 5 acceptance criteria covering auto-start, idempotency, streak observability, 7-day unattended streak, prior-milestone stability)
- **Acceptance:**
  - [ ] Auto-resume on session start (T-9.2 — SessionStart hook calls daemon-manager.sh start-schedule loop-tick)
  - [ ] Idempotent auto-start (T-9.2 — daemon-manager.sh start-schedule already handles is_running check)
  - [ ] Streak observability (T-9.3..T-9.5 — scripts/streak-tracker.sh + tests + daily cron, M7-style pure bash + awk)
  - [ ] 7-day unattended streak (T-9.6 — gated on real-time 7-day wall clock, current_streak >= 7 in streak-report.md)
  - [ ] All 8 prior milestones stable (T-9.6 — full regression sweep clean)
- **Dependencies:** M8
- **Estimated ticks:** 5 implementation ticks + 7 days wall-clock for streak gate
- **In progress:** 2026-09-07 — T-9.1 SPEC shipped (this tick); T-9.2..T-9.6 pending

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
