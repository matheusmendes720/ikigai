---
name: M86-taskdog-mcp-repair
description: Repair broken pipx venv for taskdog-mcp - reinstall from PyPI restores MCP integration
owner: matheus-mendes
status: DONE
milestone: M86
estimated_cost_usd: 0.05
constitution_refs:
  - reversibility_over_cleverness
  - state_on_disk_not_conversation
---

# M86 - taskdog-mcp pipx repair

## Context

`taskdog-mcp` (0.23.0) was editable-installed from a dead path
`C:\Users\mathe\code_space\apps\dev-tools\taskdog\packages\taskdog-client\src`
(apps/ removed in commit `604d6af`). At runtime, the .pth file pointed
to a non-existent directory, so `from taskdog_client import TaskdogApiClient`
raised `ModuleNotFoundError`.

## What changed

Reinstalled taskdog-mcp from PyPI:

- `pipx uninstall taskdog-mcp` - removes the broken editable install
- `pipx install taskdog-mcp` - installs 0.28.0 from PyPI

Skipped taskdog-server reinstall because it's currently running
(PID 14776, port 8000) and serving 155 tasks. Reinstalling would
require stopping/restarting the daemon. Will be done at next
scheduled restart.

## Verification

- `taskdog-mcp --version` → taskdog-mcp 0.28.0
- `taskdog-mcp --help` → shows usage info (was: ModuleNotFoundError)
- MCP handshake: `initialize` → returns serverInfo
- MCP `tools/list` → exposes list_tasks, get_task, plus more
- taskdog-server still serving: curl /health → `{"status":"ok"}`
- 155 tasks still in DB (no data loss)

## Acceptance

- [x] taskdog-mcp --help works
- [x] MCP initialize + tools/list handshake succeeds
- [x] Drift 18/18 PASS
- [x] Root 334 PASS + 27 SKIP, 0 FAIL
- [x] taskdog-server still healthy

## Lessons

- **Editable installs with dead paths are silent failures**: the
  package shows as "installed" in pipx list, but the .pth file
  pointing to a deleted directory means the module can't import.
  Always verify with `python -c "import <name>"` after install.
- **Editable installs from monorepo submodules break when those
  submodules are archived**: keep editable installs to current
  paths only; use proper installs for production deps.
- **Don't restart running daemons for cosmetic upgrades**: keep
  the working version running until scheduled maintenance window.
- **`pipx inject --force` doesn't override editable installs**:
  the .pth persists. Use `pipx uninstall && pipx install` to fully
  reset.

## Out of scope

- taskdog-server 0.23.0 → 0.28.0 upgrade (requires daemon restart)
- taskdog-ui removed in 0.28.0 (was already non-functional per user
  report, no replacement needed - use life CLI instead)
