---
name: M68-taskdog-server-daemon
description: Schedule taskdog-server via daemon-manager.sh (5min interval); strip CRLF from daemon scripts
owner: matheus-mendes
status: DONE
milestone: M68
estimated_cost_usd: 0.20
constitution_refs:
  - state_on_disk_not_conversation
  - correctness_over_speed
---

# M68 — taskdog-server daemon schedule + daemon-manager CRLF cleanup

## Context

After M67 unlocked deep-agent → taskdog calls returning structured
JSON, the agent still depends on `taskdog-server` running at
http://127.0.0.1:8000 — which the user had to start manually with
`taskdog-server &`. Manual startup is a daily-use blocker.

The `daemon-manager` infrastructure (M56+M62.2) already supports
arbitrary schedules. Adding a taskdog-server cron-keep-alive is the
obvious next step.

## What changed

### .claude/helpers/{daemon-manager.sh, daemon-manager-schedules.sh}

Both files had CRLF line endings (`$`\r` command not found` in stderr
when first invoked). Stripped to LF-only. This was the same Windows-edit
contamination pattern caught earlier in `detect-double-fire.sh` (M62.2).

### .claude/helpers/daemon-manager-schedules.sh

`_py_schedules()` helper hardcoded `python` (the Windows git-bash
default). Switched to `python3` (the only one available in PATH on
this Windows host). Without this, `save()` silently broke — schedule
configs would parse but the LIST output came back empty.

### Schedule added

```
taskdog-server  every 5m  cost_cap=$0
command:  taskdog-server > .claude-flow/logs/taskdog-server.log 2>&1
```

PID 14776. Manual `taskdog-server &` no longer required.

## Acceptance

- [x] `bash .claude/helpers/daemon-manager.sh list` shows all 6/6
  schedules including taskdog-server
- [x] Stripped CRLF: both daemon-manager .sh files parse cleanly
  (no syntax errors at line 33/34 anymore)
- [x] `_py_schedules()` uses python3 (PATH-available)
- [x] Taskdog server binds 127.0.0.1:8000 successfully when daemon
  fires the cron
- [x] Drift invariants preserved (no source code change in IKIGAI)

## Race condition discovered during M68

When I had previously started a `taskdog-server` manually (during M67
testing), the daemon's first fire collided with port 8000 (only one
process can bind). Manual `taskkill /F /IM taskdog-server.exe` clears
the ghost process. Future daemon firings will bind cleanly because no
external process owns the port.

Network effect: daemon-watchdog (30m interval) will keep the server
honest even if the underlying scheduler times out.

## Out of scope (M69+)

- **taskdog-mcp venv broken** (`No module named 'taskdog_client'`) —
  pipx-injection bug in `taskdog-mcp` 0.23.0 venv. Fix is host-side:
  `pipx inject taskdog-mcp taskdog-client`. Not a repo concern but
  blocks the MCP-Path 3 server from starting.
- **strategics module missing** (M67 fallout) — `tools.py` line 438
  imports `.ikigai_read_strategics` which imports `strategics.loader`
  — a module that doesn't exist after the PAV/operational archival.
  Workaround: don't import `tools.py` as a whole; use the per-fork
  imports instead.
- **taskdog-server ports clash** on Windows when multiple instances
  start concurrently — could benefit from PID-lockfile + idempotent
  start logic, but typical single-instance usage works fine.
