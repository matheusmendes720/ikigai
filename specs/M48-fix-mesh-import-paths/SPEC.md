---
name: M48-fix-mesh-import-paths
description: Remove 'src.' prefix from src/mesh/ import paths (16 files, 43 imports) — same bug class as M47 but in the mesh package.
status: DONE
owner: loop-orchestrator
constitution_refs:
  - correctness_over_speed
  - reversibility_over_cleverness
  - tests_are_the_contract
estimated_ticks: 1
---

# M48 — Fix src/mesh/ import paths

## Problem

Same bug class as M47 but in the `src/mesh/` package: every file
used `from src.contracts.X import ...` and `from src.mesh.X import ...`
when the canonical pattern (used by working code in
`src/ikigai/src/mcp_server/`) is `from contracts.X` and `from mesh.X`
without the `src.` prefix.

Counts (M47 missed this):
- `src/mesh/*.py`: 28 stale imports
- `src/mesh/adapters/*.py`: 15 stale imports
- **Total: 43 imports across 16 files**

## Why this matters

- `scripts/mcp_inspect.py` still fails even after M47 (verified:
  `ModuleNotFoundError: No module named 'src'` is gone, but the
  script then hits `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`
  — that's a missing dependency, not our problem)
- Any script that imports `mesh.*` directly (e.g.,
  `from mesh.adapters import CliAdapter`) silently fails
- The Phase 3 v1 mesh layer (the user-facing API per
  AGENTS.md "Phase 3 v1 Data Mesh") is technically broken on master

## Fix

Mechanical replacement of `src.` prefix in `src/mesh/`:
- `from src.contracts.X` → `from contracts.X`
- `from src.mesh.X` → `from mesh.X`

Done via `sed -i` for both module-level and indented function-internal
imports.

## Acceptance

- [x] Zero `from src.*` imports remain in `src/mesh/` (T-48.1)
- [x] `python -c "import mesh; from mesh.agent_consumer import ..."` succeeds (T-48.2)
- [x] Drift net preserved: 69/69 + 11/11 (T-48.3)
- [x] 1 atomic commit + push (T-48.4)

## Out of scope

The mcp_inspect.py still fails because `mcp.server.fastmcp` is not
installed (M14 migration removed `mcp>=2` but left imports referencing
`fastmcp`). This is a dependency gap, not a code bug — M49 candidate.

## Reversibility

`git revert HEAD`. Pure mechanical change.