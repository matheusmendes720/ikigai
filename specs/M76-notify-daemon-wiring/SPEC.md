---
name: M76-notify-daemon-wiring
description: notify-wrap.sh wraps scheduled commands with notify() and an end-to-end test; ready to wire into schedules.json
owner: matheus-mendes
status: DONE
milestone: M76
estimated_cost_usd: 0.30
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
---

# M76 — notify-wrap.sh daemon wrapper

## Context

M75 built the notify router but didn't wire it into the daemon
infrastructure. Loop daemons (loop-tick, hill-climb, cost-dashboard,
streak-tracker, daemon-watchdog, taskdog-server) run on cron schedules
and produce output, but no command in the loop pipes that output to
notify.

## What changed

### NEW .claude/helpers/notify-wrap.sh

A wrapper that runs any command, captures its exit code + elapsed time,
then posts a notify summary so the user gets pinged on success/failure.

Usage:
    bash .claude/helpers/notify-wrap.sh <name> <title> <cmd...>

Where:
- name: schedule identifier (e.g., "loop-tick")
- title: user-visible notification title
- cmd: the actual command to run

Handles three bash edge cases discovered while building tests:
- CRLF line endings (stripped)
- `$@` single-element quirk (`eval "$1"` for n=1)
- explicit PATH lookup (`command -v life` then fallback to python -m)

### NEW tests/loop/test_notify_wrap.sh

4 bash assertions:
1. Successful command writes success notification
2. Failing command writes error notification AND propagates non-zero rc
3. Log contains title + rc + elapsed fields
4. Usage error when no command given

### NEW tests/loop/test_notify_wrap_pytest.py

3 pytest assertions:
1. Wrappers and bash test file exist
2. Bash test runs end-to-end and passes all 4 sub-checks
3. Real command wrapper writes expected TITLE + rc to NOTIFY_FILE

### Bash test now honors NOTIFY_FILE env var

Default path is `$REPO_ROOT/.life/logs/notifications.log` but `NOTIFY_FILE`
env var overrides for test isolation.

## Acceptance

- [x] tests/loop/test_notify_wrap.sh : 4/4 PASS (bash direct)
- [x] tests/loop/test_notify_wrap_pytest.py : 3/3 PASS (pytest collection)
- [x] tests/ root : 313 PASS + 27 SKIP, 0 FAIL (was 310 PASS + 27 SKIP)
- [x] End-to-end: `bash notify-wrap.sh test-name "title" "echo hi"` writes
       notification to NOTIFY_FILE with rc=0, elapsed=Ns

## Usage (next step)

To wire into existing schedules, edit `.claude/loop/schedules.json`:

```json
{
  "name": "loop-tick",
  "interval": "60m",
  "command": "bash .claude/helpers/notify-wrap.sh loop-tick 'Loop tick' 'bash .claude/loop/loop-tick.sh'",
  "cost_cap_usd": 5.0
}
```

(Each schedule now wraps its command in notify-wrap so user gets
a Telegram ping on every tick or failure.)

## Out of scope (M77+)

- Auto-update schedules.json (manual edit for now)
- Per-daemon notification templates (currently uses generic body)
- Notification debouncing (rapid failures could spam)
- Per-user notification preferences

## Lessons

- `eval "$1"` is the safe pattern for `$#=1` case in bash wrappers;
  avoids the "single arg treated as one literal" trap.
- Windows subprocess.CreateProcess can't exec cygwin bash directly;
  use `shell=True` with cmd_str to route through cmd.exe.
- `NOTIFY_FILE` env var override is essential for test isolation
  (production default is `.life/logs/notifications.log`).
