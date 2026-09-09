# M6 — Worktree Isolation Helper

> **Constitution:** .claude/loop/constitution.md
> **What:** Make `scripts/worktree-helper.sh` the canonical gate for parallel sub-agent dispatch. Today the script exists (96 lines, commit `91fb7d4`) but lacks (a) a documented contract, (b) end-to-end tests proving parallel safety, (c) auto-cleanup hooks tied to milestone closeout.
>
> **Why:** M5 made IKIGAI MCP reachable from the loop. M6 makes it safe to fan out parallel sub-agents without stepping on each other. M7–M9 (cost dashboard, notification, production mode) all assume worktree isolation works.

## Current state (verified 2026-09-07)

- Script lives at `scripts/worktree-helper.sh` (96 lines, executable, committed at `91fb7d4`)
- Commands: `create <name>`, `list`, `cleanup <name>`, `cleanup-all`
- Default location: `.worktrees/<name>/` with branch `loop/<name>` based off current HEAD
- Idempotency: `create` exits 1 if worktree exists (correct fail-fast)
- Cleanup removes worktree dir + deletes `loop/<name>` branch (line 63–67)
- 3 stale worktrees already on disk (`.worktrees/m-0-T-0.1`, `.worktrees/m4-T-4.1`, plus 2 opencode worktrees outside our scope)

## Scope

**This milestone is contract + tests + auto-cleanup wiring.** The script body is already adequate — we add:

1. **SPEC.md** (this file) — the contract the loop orchestrator can rely on
2. **Test script** — `tests/test_worktree_helper.sh` proves parallel safety on 3+ concurrent worktrees
3. **`--auto-cleanup` flag** — when set, `cleanup-all` is invoked at the end of every tick if all PENDING tasks are done (gates M7 cost dashboard on cheap cleanup)
4. **Memory entry** — pattern for future loop-engineering work

## Acceptance criteria

1. **Spec exists** — `specs/M6-worktree-isolation/SPEC.md` documents commands, exit codes, idempotency guarantees, and the parallel-safety contract
2. **Script contract documented** — every command's exit code matrix is explicit:
   - `create <name>`: 0 on success, 1 if name missing, 1 if worktree exists, propagates `git worktree add` failures
   - `list`: 0 always (read-only)
   - `cleanup <name>`: 0 on success, 1 if name missing or not found, propagates `git worktree remove` failures
   - `cleanup-all`: 0 always (uses `|| true` to absorb individual failures)
3. **End-to-end test** — `tests/test_worktree_helper.sh` exercises:
   - 3 parallel worktrees (`m6-test-a`, `m6-test-b`, `m6-test-c`)
   - Each makes a non-conflicting change to a distinct file
   - All 3 worktrees commit cleanly without conflict
   - `cleanup-all` removes all 3 + their `loop/m6-test-*` branches
   - Verifies `.worktrees/` is empty post-cleanup
   - Test runs in <60s and is shell-only (no Python deps)
4. **Auto-cleanup hook** — `loop-tick.sh` + `loop-tick.bat` gain a `--auto-cleanup` flag that calls `worktree-helper.sh cleanup-all` when the tick ends with no PENDING tasks. Default off (opt-in for safety). When off, behavior is unchanged.
5. **No regression** — `test_loop_infra.py` (11/11), `test_m4_langgraph_integration.py` (9/9), `test_canonical_scope.py` (32/32), `test_m5_ikigai_mcp_integration.py` (2/2) all still PASS.

## Sub-tasks

### T-6.1 — Write M6 SPEC.md
- **status:** in_progress
- **spec_ref:** acceptance criteria #1 + #2
- **acceptance:**
  - [ ] This file exists
  - [ ] Commands section lists all 4 commands with exit code matrix
  - [ ] "Parallel safety contract" section explicit about non-overlapping edits
- **estimated_cost_usd:** 0
- **estimated_minutes:** 5

### T-6.2 — Scaffold scripts/worktree-helper.sh
- **status:** done (pre-existing, verified functional)
- **spec_ref:** acceptance criteria #2
- **acceptance:**
  - [x] `bash scripts/worktree-helper.sh list` runs cleanly
  - [x] `create <name>` makes worktree at `.worktrees/<name>/` on branch `loop/<name>`
  - [x] `cleanup <name>` removes worktree + branch
  - [x] `cleanup-all` clears all `loop/*` worktrees
- **notes:** script was committed at `91fb7d4` during M0 bootstrap; verified 2026-09-07 still functional.

### T-6.3 — End-to-end test
- **status:** pending
- **spec_ref:** acceptance criterion #3
- **acceptance:**
  - [ ] `tests/test_worktree_helper.sh` exists and runs in <60s
  - [ ] Test passes on 3+ concurrent worktrees without conflict
  - [ ] Cleanup restores empty `.worktrees/` + zero `loop/*` branches
  - [ ] Test is idempotent (re-runnable from clean state)
- **estimated_cost_usd:** 0
- **estimated_minutes:** 10

### T-6.4 — Auto-cleanup hook in loop-tick
- **status:** pending
- **spec_ref:** acceptance criterion #4
- **acceptance:**
  - [ ] `loop-tick.sh` + `loop-tick.bat` gain `--auto-cleanup` flag
  - [ ] Default off (no behavior change)
  - [ ] When on + zero PENDING tasks → calls `worktree-helper.sh cleanup-all`
  - [ ] When on + PENDING tasks present → logs skip reason, no cleanup
- **estimated_cost_usd:** 0
- **estimated_minutes:** 8

### T-6.5 — State machine closeout + push
- **status:** pending
- **spec_ref:** acceptance criterion #5
- **acceptance:**
  - [ ] `roadmap.md` M6 STATUS:DONE
  - [ ] `tasks.md` T-6.1..T-6.4 done, T-6.5 pending → done
  - [ ] `progress.md` append-only M6 closeout entry
  - [ ] Atomic commit covering all M6 file changes
  - [ ] Pushed to origin master
  - [ ] Memory entry at `~/.claude/projects/.../memory/m6-worktree-isolation-shipped-2026-09-07.md`
  - [ ] MEMORY.md pointer added
- **estimated_cost_usd:** 0
- **estimated_minutes:** 5

## Non-goals

- **Not adding Windows parity for the script itself** — `worktree-helper.sh` is POSIX-only. Windows sub-agents use Git Bash (already available per W5.3). A `.bat` wrapper is a separate micro-task, NOT M6 scope.
- **Not changing the script body** — the existing 96-line implementation is sufficient. Adding new flags would expand scope beyond M6.
- **Not touching `tests/conftest.py`** — the new test is shell-only, lives at `tests/test_worktree_helper.sh`, and uses `set -e` + `trap` for cleanup. No Python sys.path tricks needed.

## Parallel safety contract

The script guarantees that **worktrees with distinct names never collide**. The orchestrator MUST observe these constraints when dispatching parallel sub-agents:

1. **One worktree per sub-agent** — never reuse a name across concurrent ticks
2. **Distinct file targets** — sub-agents sharing a worktree MUST write to non-overlapping paths. The script does NOT enforce this (it can't know the agent's intent). Drift on this = human-mediated conflict resolution.
3. **Branch isolation** — each worktree's branch (`loop/<name>`) is unique. `git worktree add -b` (line 40) refuses to overwrite.
4. **Cleanup is idempotent** — `cleanup-all` uses `|| true` to absorb per-worktree failures. Safe to invoke from cron.

## Risks

- **Disk leak** — orphaned `.worktrees/<name>/` dirs if a tick crashes between `create` and `cleanup`. Mitigated by `cleanup-all` being idempotent and the new `--auto-cleanup` flag.
- **Branch leak** — `loop/<name>` branches if `cleanup <name>` is interrupted mid-step. Mitigated by `cleanup-all` sweeping both worktree dir AND branch.
- **Stale worktrees** — 3 already on disk from M0/M4 (`.worktrees/m-0-T-0.1`, `.worktrees/m4-T-4.1`). Documented as pre-existing, will be cleared by first `cleanup-all` invocation post-M6 merge.
