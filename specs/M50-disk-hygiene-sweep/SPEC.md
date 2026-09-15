---
name: M50-disk-hygiene-sweep
description: Reclaim 13MB disk by clearing accumulated pytest-tmp fixtures from tests/data/pytest-tmp/ (already gitignored).
status: DONE
owner: loop-orchestrator
constitution_refs:
  - state_on_disk_not_conversation
  - tests_are_the_contract
estimated_ticks: 1
---

# M50 — Disk hygiene sweep

## Problem

`tests/data/pytest-tmp/` accumulated 13MB of pytest fixture artifacts
(2,345 files across 867 subdirectories like `bridge_test_*`) from
recent test runs. The directory is **already gitignored** (M46 added
the pattern), so the files never entered the index — they just sat
on disk taking up space.

## Disposition applied

`rm -rf tests/data/pytest-tmp/` — reclaims 13MB. Next test run will
recreate the directory as needed; the `.gitignore` pattern will keep
it from being tracked.

## Acceptance

- [x] `rm -rf tests/data/pytest-tmp/` (T-50.1)
- [x] `du -sh tests/data/` reports 0 after cleanup (T-50.2)
- [x] Drift net preserved: 69/69 + 11/11 (T-50.3)
- [x] `.gitignore` confirmed covering the path (T-50.4 — `git check-ignore tests/data/pytest-tmp/bridge_test_0ntu_wu8/mirror.db` returns the gitignored path)

## Note

This is a **filesystem-only** cleanup. No git change is needed (the
files were never tracked). The git status before + after is identical.

If disk pressure recurs (test runs accumulate fast), this could become
a cron-driven sweep — but for now manual cleanup on memory triggers is fine.