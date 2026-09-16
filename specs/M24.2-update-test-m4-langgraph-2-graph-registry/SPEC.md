---
name: M24.2-update-test-m4-langgraph-2-graph-registry
description: Update test_m4_langgraph_integration.py to match the post-M22 2-graph langgraph.json registry (pae_maintainer archived per ADR-024).
status: DONE
owner: loop-orchestrator
constitution_refs:
  - correctness_over_speed
  - reversibility_over_cleverness
  - tests_are_the_contract
estimated_ticks: 1
---

# M24.2 — Update test_m4_langgraph_integration.py to match 2-graph registry

## Problem (M24 closeout documented, 2026-09-16T01:00Z)

`tests/test_m4_langgraph_integration.py` had 3 failing tests because it
was written for the pre-M22 3-graph `langgraph.json` registry:

| Test | Pre-M22 expected | Post-M22 actual | Result |
|---|---|---|---|
| `test_graph_dispatch_exits_zero[pae_maintainer]` | graph exists, exit 0 | graph archived | FAIL rc=1 |
| `test_checkpoint_db_persists_rows[pae_maintainer]` | graph runs, checkpoint persists | graph archived | FAIL rc=1 |
| `test_langgraph_registry_has_exactly_three_graphs` | 3 graphs in langgraph.json | 2 graphs | FAIL |

Plus a 4th failure: `test_graph_dispatch_exits_zero[ikigai_fork_smoke]`
and `test_checkpoint_db_persists_rows[ikigai_fork_smoke]` failed with
`ModuleNotFoundError: No module named 'langgraph.checkpoint.sqlite'` —
**a dep-gap**, not a test logic bug.

## Disposition applied

### Test-only changes

1. `VALID_GRAPHS` reduced from 3 to 2:
   ```python
   VALID_GRAPHS = ["ikigai_maintainer_v2", "ikigai_fork_smoke"]
   ```
2. `VALID_DISPATCH_GRAPHS` reduced from 2 to 1 (pae_maintainer removed):
   ```python
   VALID_DISPATCH_GRAPHS = ["ikigai_fork_smoke"]
   ```
3. Renamed registry test:
   ```python
   def test_langgraph_registry_has_exactly_two_graphs()
   ```
4. Updated module docstring + inline comments to reflect the M22 archival
   context.

### Dependency fix (M24.2 co-shipped with the test changes)

Installed `langgraph-checkpoint-sqlite` into the hermes-agent venv:
```
pip install langgraph-checkpoint-sqlite
```
This is the package that exposes `from langgraph.checkpoint.sqlite
import SqliteSaver` (which `v2/fork_smoke_graph.py` imports). Same
dep-gap family as M53 (`pip install "mcp<2"`).

## Acceptance

- [x] `pytest tests/test_m4_langgraph_integration.py` 5/5 PASS
      (was: 2 PASS, 3 FAIL) (T-24.2.1)
- [x] `langgraph-checkpoint-sqlite` installed in hermes-agent venv
      (T-24.2.2)
- [x] Drift net 69/69 PASS preserved (T-24.2.3 — required co-ship
      with M38.1 which fixed the false-positive double-fire detector
      triggered by M24.2 verification runs)
- [x] Full regression sweep: 7/7 PASS
      (worktree_helper 15/15, cost_dashboard 7/7, notify 11/11,
       streak_tracker 11/11, dispatch 24/24, loop_infra 11/11,
       m4 5/5) (T-24.2.4)
- [x] 1 atomic commit + push (T-24.2.5)

## What did NOT need fixing

- `loop-tick.sh --graph ikigai_maintainer_v2` dispatch is still broken
  (separate v2 parallel code path issue from commit `fb41578`); the
  `VALID_DISPATCH_GRAPHS` exclusion of `ikigai_maintainer_v2` was
  already in place pre-M24.2. The `VALID_GRAPHS` registry list still
  includes both graphs because both ARE registered in `langgraph.json`.
- Production code (`vibe-ops/src/`) was NOT touched — only test + dep.

## Why M22 ship-time review missed this

M22's commit message explicitly mentioned "removed pae_maintainer
graph from langgraph.json (was registered as a third entry)" but did
NOT update `test_m4_langgraph_integration.py`. The test was failing
from M22 ship date (2026-09-14) until M24.2 (2026-09-16) — same
2-day silent regression window as the M54 daemon-watchdog bug.

## Reversibility

`git revert HEAD`. Test-only changes + dep install (dep is reversible
via `pip uninstall` if needed).
