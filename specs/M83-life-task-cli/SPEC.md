---
name: M83-life-task-cli
description: Wrap taskdog CLI as life task {add,start,done,ls} - removes last daily-use friction
owner: matheus-mendes
status: DONE
milestone: M83
estimated_cost_usd: 0.10
constitution_refs:
  - composition_over_inheritance
  - correctness_over_speed
  - tests_are_the_contract
---

# M83 - life task {add,start,done,ls} CLI alias

## Context

After M80 (invoke-skill all-cadences cron wiring), the only remaining
daily-use friction was the absence of `life task add`. User had to
use `taskdog add` directly, which breaks the "one CLI" experience.

## What changed

### life/centrals/task.py

- Added 4 new commands wrapping taskdog CLI:
  - `life task add <name> [--priority N] [--tag TAG]... [--estimate H] [--deadline TS]`
  - `life task start <id>` (PENDING → IN_PROGRESS)
  - `life task done <id>` (IN_PROGRESS → COMPLETED)
  - `life task ls [--q QUERY]` (list all with optional filter)
- `_run_taskdog(args)` helper: subprocess.run with FileNotFoundError
  fallback (gives helpful install message if taskdog not on PATH).
- All commands support `--json` for machine-readable output.

### tests/test_life_task_cli.py (NEW)

8 tests covering:
- Basic invocation (add, start, done, ls)
- Flag handling (--priority, --tag, --q)
- JSON output format
- Failure path (non-zero exit code on taskdog failure)

## Acceptance

- [x] `life task add "X" --priority 8 --tag daily` creates task
- [x] `life task start <id>` → IN_PROGRESS
- [x] `life task done <id>` → COMPLETED (full E2E verified)
- [x] `life task ls` lists all 155 tasks
- [x] 8/8 unit tests PASS
- [x] Drift 18/18 PASS, root 326 PASS + 27 SKIP, 0 FAIL (was 318)

## Lessons

- **Subprocess.run with FileNotFoundError fallback** beats try/except
  around the whole call: gives precise error message when binary
  is missing without masking other errors (timeout, permissions).
- **Typer `list[str]` option with default=[]** is the canonical
  pattern for repeatable flags (`--tag foo --tag bar`).
- **--json flag everywhere** is a project convention (matches other
  centrals like knowledge/research).

## Out of scope

- `life task cancel/delete` (low frequency, user uses taskdog direct)
- `life task show <id>` (single task lookup, use taskdog)
- Wrapper for `taskwarrior` (out of scope per user direction)
