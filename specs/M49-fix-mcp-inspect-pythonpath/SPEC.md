---
name: M49-fix-mcp-inspect-pythonpath
description: Add <repo> to scripts/mcp_inspect.py build_pythonpath() so sys_ikigai package is importable.
status: DONE
owner: loop-orchestrator
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
estimated_ticks: 1
---

# M49 — Fix scripts/mcp_inspect.py PYTHONPATH for sys_ikigai

## Problem

`scripts/mcp_inspect.py:build_pythonpath()` only added 2 paths to
PYTHONPATH: `<repo>/src` and `<repo>/src/ikigai/src`. It missed
`<repo>` itself, which is needed for the `sys_ikigai` package (the
renamed ikigai package at repo root).

`src/ikigai/tests/conftest.py:_REPO_ROOT` adds `<repo>` to sys.path
explicitly (the canonical pattern post the 2026-09-05 namespace
rename), but the inspect script predated that change.

Result: `scripts/mcp_inspect.py` failed with `ModuleNotFoundError: No
module named 'sys_ikigai'` at `src/ikigai/src/mcp_server/server.py:46`
because `sys_ikigai.vault.task_io` couldn't be located.

## Fix

Add `<repo>` as the first path in `build_pythonpath()`. Mirrors
`src/ikigai/tests/conftest.py` pattern.

## Out of scope (M50 candidate)

After this fix, the next failure is `ModuleNotFoundError: No module
named 'mcp.server.fastmcp'` from `server.py:31`. The `mcp.server.fastmcp`
symbol was REMOVED in mcp 2.0+; the project pins `mcp = "^1.1"` in
`src/ikigai/pyproject.toml`. The dependency gap is a venv setup issue
(`uv sync` should pin mcp<2; hermes-agent venv has mcp 2.0.0 installed
without the project pin). Documented as M50 candidate.

## Acceptance

- [x] `build_pythonpath()` adds `<repo>` as the first path (T-49.1)
- [x] `sys_ikigai` imports successfully with the new PYTHONPATH (T-49.2 — verified via `python -c "import sys_ikigai; ..."`)
- [x] Drift net preserved: 69/69 + 11/11 (T-49.3)
- [x] 1 atomic commit + push

## Reversibility

`git revert HEAD`. Single-file change.