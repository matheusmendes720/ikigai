---
name: M45-loop-status-card-scaffolding
description: Initialize the OMH loop metadata (loop_status_card/v1 + loop_cycle/v1 + goal_ledger/v1) under .omh/goals/ so the autonomous loop has a persistent state machine independent of progress.md.
status: DONE
owner: loop-orchestrator
constitution_refs:
  - state_on_disk_not_in_conversation
  - spec_driven_not_vibe_driven
  - reversibility_over_cleverness
estimated_ticks: 1
---

# M45 — Loop status card scaffolding

## Problem

The `ulw-loop` skill (loaded 2026-09-15) requires OMH-style metadata
artifacts for autonomous-loop execution:

- `loop_status_card/v1` — current state, next action, failure mode summary
- `loop_cycle/v1` — per-cycle ledger
- `goal_ledger/v1` — completion evidence
- `loop_engineering/v1` — pipeline snapshot

The repo's autonomous loop (`/loop`) was running purely off
`.claude/loop/{roadmap,tasks,progress}.md` — which IS the source of
truth for milestones but doesn't follow OMH's metadata schema.

Without these artifacts, future `ulw-loop` skill invocations will
report "goal_status_card/v1 not found" instead of resuming the loop.

## Disposition applied

Created `.omh/goals/` with 4 metadata files that mirror the existing
loop state:

| File | Purpose | Source |
|---|---|---|
| `goal_ledger/v1.md` | Goal-level completion ledger | derived from `.claude/loop/roadmap.md` |
| `loop_cycle/v1.md` | Per-cycle ledger (kept append-only) | derived from `.claude/loop/progress.md` |
| `loop_status_card/v1.md` | Current state + next action | derived from `.claude/loop/roadmap.md` (Backlog section) |
| `loop_engineering/v1.md` | Pipeline snapshot (M0-M42 milestones) | derived from `.claude/loop/roadmap.md` |

The actual milestone completion evidence continues to live in
`.claude/loop/progress.md` (append-only tick log, 2,500+ entries);
the OMH files are **metadata pointers** to that evidence, not
replacements.

## Acceptance

- [x] `.omh/goals/` directory created
- [x] 4 v1.md metadata files written
- [x] `.omh/goals/` added to `.gitignore` to keep metadata local
      (commit pointers only, not the full state)
- [x] Drift net preserved: 68/68 + 11/11

## Reversibility

Delete `.omh/goals/` + `.gitignore` entry. The canonical state in
`.claude/loop/` is unaffected.

## Note

This milestone does NOT change any behavior of the autonomous loop.
It only adds OMH-schema metadata that future `ulw-loop` skill
invocations will read. The `.claude/loop/` directory remains the
authoritative source of truth.