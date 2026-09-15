---
name: M52-fix-mcp-server-import-paths
description: Remove 'src.' prefix from src/ikigai/src/mcp_server/ imports (3 files).
status: DONE
owner: loop-orchestrator
constitution_refs:
  - correctness_over_speed
  - reversibility_over_cleverness
  - tests_are_the_contract
estimated_ticks: 1
---

# M52 — Fix src/ikigai/src/mcp_server/ import paths

## Problem

Same bug class as M47 (src/contracts/) and M48 (src/mesh/), but in the
**third** package location I missed: `src/ikigai/src/mcp_server/`.
8 `from src.contracts.X` and `from src.mesh.X` imports across 3 files
that should use the canonical `from contracts.X` / `from mesh.X` form.

## Files affected

- `src/ikigai/src/mcp_server/resources.py` (1 stale import — `from src.mesh import queue`)
- `src/ikigai/src/mcp_server/taskdog_tools.py` (3 stale imports)
- `src/ikigai/src/mcp_server/tools_mesh.py` (4 stale imports)

Note: each file has a mix of `from src.X.Y` (dotted) and `from src.X import Y`
(non-dotted) patterns — both fixed with targeted sed.

## Why this matters

- Same drift issue as M47/M48: `from src.contracts.X` only works when
  `src/` is on `sys.path`, but the canonical pattern (used in
  `src/ikigai/src/mcp_server/resources.py:21` itself, line just above the
  stale import) is `from contracts.X` with `<repo>` and `src/` both
  on `sys.path`
- The 3 test files that have collection errors (test_chat_system.py,
  test_server_fastmcp.py, test_taskdog_mcp_path3.py) are blocked by the
  separate `mcp.server.fastmcp` dep gap (mcp 2.0 removed it; project
  pins mcp<2). This M52 doesn't fix those — but it removes a layer of
  import-path noise so the dep-gap is the only remaining blocker.

## Fix

Mechanical sed:
- `from src.contracts.X` → `from contracts.X`
- `from src.mesh.X` → `from mesh.X`
- `from src.mesh` → `from mesh` (bare-module variant)

## Acceptance

- [x] Zero `from src.*` imports remain in `src/ikigai/src/mcp_server/` (T-52.1)
- [x] Drift net preserved: 69/69 + 11/11 (T-52.2)
- [x] 1 atomic commit + push (T-52.3)

## Out of scope

The `mcp.server.fastmcp` removal (mcp 2.0+) — separate issue requiring
either `pip install mcp<2` in the hermes-agent venv or a code rewrite
to use `mcp.server.MCPServer`. M50 candidate (already noted in
signal-discovery-2026-09-15-fresh.md #2).

## Reversibility

`git revert HEAD`. Mechanical change.