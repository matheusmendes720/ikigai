---
name: M73.3-bug-sweep
description: Sweep of ikigai test fixes — state_machines dual-identity, sqlite_append_only allowlist, observe_node plan_intent_hint, dual-identity mesh.X imports in 11 files
owner: matheus-mendes
status: DONE
milestone: M73.3
estimated_cost_usd: 0.40
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
  - state_on_disk_not_conversation
---

# M73.3 — Ikigai test bug sweep

## Context

After M73.2 (namespace allowlist rollback), 79 ikigai tests still failed
across multiple files. Bucket analysis showed the failures clustered
around 4 root causes:
1. Dual-identity bug (sys.modules['mesh.X'] vs sys.modules['src.mesh.X'])
2. Lazy-import module path typo (`ikigai.state_machines._sm_base` doesn't
   exist, should be `sys_ikigai.state_machines._sm_base`)
3. SQLite append-only invariant too strict (legitimate retention DELETE
   not on allowlist)
4. observe_node missing `plan_intent_hint` (Plan D Task D.1 unimplemented)

## What changed

### sys_ikigai/state_machines/__init__.py

```python
def __getattr__(name: str):
    if name in ("StateMachine", "Transition"):
-       mod = importlib.import_module("ikigai.state_machines._sm_base")
+       mod = importlib.import_module("sys_ikigai.state_machines._sm_base")
        return getattr(mod, name)
```

The lazy import was looking up the WRONG module path (`ikigai` instead
of `sys_ikigai`), which made `pytest.raises(TransitionError)` fail when
the test imported `TransitionError` from the correct path. Caused 1
failure (`test_guard_blocks_transition`) plus cascading failures in
state-machine-using tests.

### src/ikigai/tests/test_sqlite_append_only.py

Added `src/ikigai/src/agents/v2/checkpoint.py` to `SQLITE_ALLOWLIST`.
Justification: the DELETE statements are inside `IkigaiCheckpointer.prune()`
which performs retention pruning on the `ikigai_subgraph_links` table
ONLY. The state tables (`ikigai_state`, `plan_entities`) remain
append-only.

### src/ikigai/src/agents/v2/nodes/observe.py

Added `_classify_plan_intent()` function with PT/EN planning keyword
list. The `observe_node()` now emits `plan_intent_hint` when user_input
contains keywords like "quero focar", "this week", "my plan", etc.
Plan D Task D.1 (deferred since pre-V5-E) is now implemented.

### Dual-identity fixes (M59 continuation)

11 files had `import mesh.X` / `from mesh.X` instead of `src.mesh.X`:

Production:
- sys_ikigai/vault/sync.py (mesh.queue → src.mesh.queue)
- sys_ikigai/cli/app.py (mesh.adapters.taskdog → src.mesh.adapters.taskdog)
- sys_ikigai/vault/sync_cli.py (same)
- src/ikigai/src/agents/v2/workers/investigation_dispatcher.py
- src/ikigai/src/mcp_server/investigation_complete.py
- src/ikigai/src/mcp_server/investigation_enqueue.py
- src/ikigai/src/mcp_server/investigation_status.py
- src/ikigai/src/mcp_server/resources.py
- src/ikigai/src/mcp_server/taskdog_tools.py
- src/ikigai/src/mcp_server/tools_mesh.py

Each fixed with `from src.mesh.X` pattern.

## Acceptance (verified 2026-09-19)

- [x] tests/test_state_machines.py : 37/37 PASS (was 36/37)
- [x] tests/test_sqlite_append_only.py : 4/4 PASS (was 3/4)
- [x] tests/test_observe_intent_hint.py : 3/3 PASS (was 2/3)
- [x] tests/test_reverse_sync.py : 8/8 PASS (was 4/8)
- [x] **Total ikigai**: 773 PASS + 4 SKIP, 66 failed + 4 errors
       (was 761 PASS + 3 SKIP, 79 failed + 4 errors)
- [x] tests/ root: still 329 PASS + 1 SKIP (no regression)
- [x] Drift net canonical: still 18/18 PASS

## Bug class lessons

1. **Lazy imports via __getattr__ break at import-name resolution time**.
   When the lookup target has a typo (`ikigai` vs `sys_ikigai`), the
   ImportError is deferred until first access, not at module load.
   Tests catch this only when they actually access the lazy attribute.

2. **Append-only invariants need explicit allowlists**. Production
   retention pruning is legitimate; the strict "no DELETE anywhere"
   invariant needs an escape hatch for housekeeping code, with
   justification in the allowlist comment.

3. **Dual-identity imports are sticky**. M59 fixed 8 files but missed
   11 more. A grep audit for `from mesh.` / `import mesh.` in
   production code should be part of the test bucket analysis.

## Out of scope (M74+)

- 66 remaining failures cluster in test_v2_*
  (unimplemented features) and test_ikigai_maintainer_nodes.py
  (LangGraph state machine tests)
- tests/mcp_server/test_investigation_lifecycle + test_vault_read_actor
  pre-existing collector errors
