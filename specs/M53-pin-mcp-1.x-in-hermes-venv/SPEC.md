---
name: M53-pin-mcp-1.x-in-hermes-venv
description: Pin mcp<2 in hermes-agent venv to match project constraint; unblocks 7 tests.
status: DONE
owner: loop-orchestrator
constitution_refs:
  - state_on_disk_not_conversation
  - tests_are_the_contract
estimated_ticks: 1
---

# M53 — Pin mcp<2 in hermes-agent venv

## Problem

The project pins `mcp = "^1.1"` in `src/ikigai/pyproject.toml`, but the
hermes-agent venv (the Python that runs `python scripts/mcp_inspect.py`
and the test suite) had `mcp 2.0.0` installed.

`mcp.server.fastmcp` (the high-level API) was REMOVED in mcp 2.0+
in favor of `mcp.server.MCPServer`. 3 test files (test_chat_system.py,
test_server_fastmcp.py, test_taskdog_mcp_path3.py) had collection
errors because they (transitively) import `from mcp.server.fastmcp
import FastMCP`.

## Fix

`pip install 'mcp<2'` in the hermes-agent venv — installed `mcp 1.30.0`.

This is an **environment-level** change (no repo file modified). Drift
net and loop_infra regression remain green because they don't import
mcp.

## Results

- **Before:** 875 tests collected, 3 collection errors (mcp dep gap)
- **After:** 882 tests collected, 1 collection error (separate issue — see Out of Scope)

7 MCP tests unblocked:
- `test_server_fastmcp.py` — 3 tests, all PASS
- `test_taskdog_mcp_path3.py` — 4 tests, all PASS

## Acceptance

- [x] `mcp<2` installed in hermes-agent venv (T-53.1 — `mcp 1.30.0`)
- [x] `test_server_fastmcp.py` passes (T-53.2 — 3/3)
- [x] `test_taskdog_mcp_path3.py` passes (T-53.3 — 4/4)
- [x] Drift net preserved: 69/69 + 11/11 (T-53.4)
- [x] No repo files modified (env-only change) (T-53.5)

## Out of scope

The remaining 1 collection error is `test_chat_system.py` which imports
`Entry` and `EntryRole` from `src.ikigai.src.chat` — those classes do
NOT exist in the repo (verified: `Entry` / `EntryRole` grep returns 0
matches across `src/` and `sys_ikigai/`). The test is testing schema
classes that were either never implemented or removed during the IKIGAI
refactor. Fixing requires implementing the Entry / EntryRole Pydantic
classes — out of scope for an env-level fix.

## Reversibility

`pip install 'mcp>=2'` to roll back. No repo files affected.

## Note

This change does NOT need to be re-applied on a fresh clone — the
hermes-agent venv is the global host venv, persistent across sessions.
The next time you `pip install` anything that touches mcp, you'll get
the newer version unless you pin it. Consider adding a `.python-version`
+ `requirements-dev.txt` for explicit reproducibility if multi-host
setup becomes a concern.