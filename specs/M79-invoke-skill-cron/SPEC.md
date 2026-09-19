---
name: M79-invoke-skill-cron
description: invoke-skill-ikigai-daily schedule wired + MSYS path bug fix
owner: matheus-mendes
status: DONE
milestone: M79
estimated_cost_usd: 0.10
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
  - state_on_disk_not_conversation
---

# M79 invoke-skill cron wiring + MSYS path bug fix

## Context

M78 built `life invoke-skill`. M79 wires it to a cron schedule so the
daily cycle runs automatically every 24h. Discovered (and fixed) a
Windows MSYS path duplication bug that was hiding the schedule from
the daemon-manager.

## What changed

### .claude/loop/schedules.json

Added 7th schedule entry (invoke-skill-ikigai-daily, 1440m interval).
The schedule runs daily, fires `invoke-skill ikigai-daily`
(FAKE_LLM mode for now), and notifies via the M76 notify-wrap
pipeline.

### MSYS path bug discovered + fixed

Windows git-bash MSYS path translation creates a duplicate file at:
`C:\\c\\Users\\mathe\\code_space\\life-oss\\life\\.claude\\loop\\schedules.json`
when scripts use `/c/Users/...` paths. Python via this path sees the
OLD schedule (with `taskdog-server` instead of `invoke-skill-ikigai-daily`).

**Fix:** Synced the canonical Windows path over the MSYS-mangled one.

### .claude/helpers/daemon-manager-schedules.sh

Changed `python3` to `python` in the heredoc helper. The `python3`
on Windows PATH (WindowsApps stub) opens REPL on `-`, not executing
the heredoc.

## Acceptance

- [x] bash .claude/helpers/daemon-manager.sh list : 7/7 daemons RUNNING
- [x] invoke-skill-ikigai-daily cron fires daily (one-shot test: rc=0)
- [x] Output appears in .life/logs/notifications.log

## Lessons

- MSYS path duplication: bash `/c/Users/...` is not the same as
  Windows `C:\\Users\\...`. Always use canonical Windows paths.
- WindowsApps python3 is a REPL stub - use `python` for heredocs.
- Schedule commands must be self-contained: include env vars
  (IKIGAI_FAKE_LLM, NOTIFY_VERBOSE, PYTHONPATH) inline.
