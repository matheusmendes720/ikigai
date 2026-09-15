---
name: M54-fix-daemon-watchdog-heartbeat-path
description: Fix daemon-watchdog.sh heartbeat path resolution so watchdog can read real heartbeat (was reading phantom path).
status: DONE
owner: loop-orchestrator
constitution_refs:
  - correctness_over_speed
  - reversibility_over_cleverness
  - tests_are_the_contract
  - state_on_disk_not_conversation
estimated_ticks: 1
---

# M54 — Fix daemon-watchdog.sh heartbeat path resolution

## Problem (discovered 2026-09-15T21:39:46Z via watchdog self-test)

The watchdog script's `PROJECT_ROOT` computation has an off-by-one error.
M39 SHIPPED on 2026-09-15, but the watchdog has been unable to read the
real heartbeat file since ship date — it has been looking at a phantom path.

### Root cause

`scripts/daemon-watchdog.sh:22`:

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # life/.claude/loop/scripts
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"              # life/.claude   ← WRONG (off by one)
LOOP_DIR="$PROJECT_ROOT/.claude/loop"                        # life/.claude/.claude/loop
HEARTBEAT_FILE="$LOOP_DIR/.daemon-heartbeat.json"            # life/.claude/.claude/loop/.daemon-heartbeat.json
```

`loop-tick.sh` writes to `life/.claude/loop/.daemon-heartbeat.json` (correct,
because `LOOP_DIR` is set directly from `BASH_SOURCE[0]` — script sits in
the loop dir itself).

Watchdog needs to resolve PROJECT_ROOT to `life/` (3 levels up from script),
but the script goes 2 levels up, landing in `life/.claude` instead. Then it
prepends `.claude/loop` again → nested `.claude/.claude/loop` → 404 on
heartbeat read.

### Symptom (today, 2026-09-15T21:39Z)

```
$ bash .claude/loop/scripts/daemon-watchdog.sh
[2026-09-15T21:39:46Z] watchdog: WARN: no heartbeat file at
  /c/Users/mathe/code_space/life-oss/life/.claude/.claude/loop/.daemon-heartbeat.json
  — daemon has never fired
```

The real heartbeat is at:
`/c/Users/mathe/code_space/life-oss/life/.claude/loop/.daemon-heartbeat.json`
(content: `{"last_heartbeat":"2026-09-15T21:36:09Z","tick_id":"20260915-183609"}`)

## Fix

`scripts/daemon-watchdog.sh:22` — change `../..` to `../../..`:

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"    # life/.claude/loop/scripts
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"            # life/   ← CORRECT
LOOP_DIR="$PROJECT_ROOT/.claude/loop"                         # life/.claude/loop
HEARTBEAT_FILE="$LOOP_DIR/.daemon-heartbeat.json"             # life/.claude/loop/.daemon-heartbeat.json
```

Also `SCHEDULES_DIR="$PROJECT_ROOT/.claude-flow/schedules"` and
`NOTIFY="$PROJECT_ROOT/scripts/notify.sh"` will resolve correctly with the
fix.

## Acceptance criteria

1. `bash .claude/loop/scripts/daemon-watchdog.sh` exits 0 and emits
   `OK: daemon heartbeat fresh (<N>s < 5400s)` (positive healthy signal)
   OR — if watch threshold genuinely exceeded — emits `ALERT:` with
   correct delta seconds. **NEVER emits** `WARN: no heartbeat file at ...`.
2. After fix, `du -sh .claude/.claude/` reports 0 or is removed.
3. Drift net preserved: 69/69 + 11/11.
4. Full regression sweep preserved: bash 56/56 (worktree 15 + cost 7 +
   notify 11 + streak 11 + daemon-watchdog 12) + pytest 63/63 (loop_infra
   11 + m4 9 + canonical_scope 35 + m5 11 + drift_extended 11 + chat_repl 8).
5. Atomic commit + push to origin master (no Co-Authored-By trailer).

## Out of scope

- Watchdog SCHEDULES_DIR resolution — fixing PROJECT_ROOT also fixes this
  transitively (no separate change needed).
- Adding a drift test for heartbeat path — possible followup M54.1, but
  the fix itself is so minimal that adding drift test infra for a
  one-line off-by-one is overengineering.

## Risks + reversibility

- Risk: 1-line change to script; if mis-copied, watchdog still broken.
  Mitigation: regression sweep includes re-running watchdog with
  `--dry-run` and asserting positive output.
- Reversibility: `git revert` restores previous broken state.
