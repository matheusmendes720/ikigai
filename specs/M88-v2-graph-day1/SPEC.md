---
name: M88-v2-graph-day1
description: Fix v2 graph recursion + populate recall/reason stubs - first half of v2 graph recovery
owner: matheus-mendes
status: DONE
milestone: M88
estimated_cost_usd: 0.15
constitution_refs:
  - reversibility_over_cleverness
  - tests_are_the_contract
  - state_on_disk_not_conversation
---

# M88 - v2 graph Day 1: fix recursion + populate stubs

## Context

Per the v2 graph deep-dive, the recursion bug was:

```python
def _route_after_reason(state) -> Literal["reflect", "recall", "error"]:
    draft = state.get("draft_proposal")
    if not draft:
        return "recall"  # → infinite loop because recall_node is a stub
```

Plus `recall_node` was a 10-line stub with hardcoded `recalled_at="2026-09-14"`,
and `reason_node` ignored context entirely.

## What changed

### src/ikigai/src/agents/v2/graph.py

- Added `MAX_REASON_LOOPS = 3` constant
- `_route_after_reason` now checks `iteration >= MAX_REASON_LOOPS` and
  routes to error with diagnostic fields (`originating_node="reason"`,
  `error_type="ReasonLoopExhausted"`, `error_message="..."`)
- Bounded recursion: 2 retries max before graceful termination

### src/ikigai/src/agents/v2/nodes/recall_node.py (rewritten)

- Resolves memory_db via env override or `data/memory.db`/`data/ikigai.db`
- Reads 14 days of daily intentions + weekly aggregations
- Stores context with: `recalled_at`, `recall_attempt`, `strategics_loaded`,
  `daily_intentions_count`, `weekly_aggregations_count`, `recent_intentions`
- Graceful failure: any read error sets context fields + error message,
  never crashes the graph

### src/ikigai/src/agents/v2/nodes/reason_node.py (rewritten)

- Builds proposals grounded in recalled context (last 5 daily intentions)
- Bumps `state['iteration']` counter so route can bound the loop
- Fallback proposal: `reflect.intention` operation if no user_request
  but context is available
- Sets `context_refs` so downstream nodes can trace reasoning

### src/ikigai/src/agents/v2/nodes/error.py

- Now writes `originating_node` / `error_type` / `error_message` back to
  state so tests asserting on these fields pass

### Tests

- `src/ikigai/tests/test_v2_graph_smoke.py`: unskip (was skip-tagged)
  → 20/20 PASS
- `src/ikigai/tests/test_v2_prompt_chains.py`: unskip, 3 re-skipped
  individually for M88 Day-2 work
  → 7/7 PASS + 3 SKIP (Day-2 candidates)
- `tests/test_reasoning_chain.py`: updated `test_recall_populates_context`
  to assert realistic fields instead of stub's `strategics_loaded=True`

## Acceptance

- [x] `_route_after_reason` bounds recursion at MAX_REASON_LOOPS=3
- [x] `recall_node` reads real memory_db (with graceful fallback)
- [x] `reason_node` produces context-grounded proposals
- [x] `error_node` writes originating_node back to state
- [x] Drift 18/18 PASS
- [x] ikigai full: 768 PASS + 16 SKIP (was 753 + 13 — added 15 tests)
- [x] Root: 346 PASS + 27 SKIP, 0 FAIL (was 346 + 1 FAIL)
- [x] taskdog-server restored after metadata corruption (160 tasks live)

## Lessons

- **LangGraph route functions are read-only on state**: setting fields in
  `_route_after_reason` doesn't persist; the node must write them
  back. `error_node` now writes `originating_node` / `error_type` /
  `error_message` so test assertions on these fields pass.
- **Stub assertions in old tests become brittle when stubs become
  real**: `test_recall_populates_context` asserted
  `strategics_loaded is True` (true in stub, false when no memory_db
  in real impl). Updated to assert "field exists with correct type"
  instead of "field has hardcoded value".
- **Memory resolution via convention + env override**: `_resolve_memory_db`
  checks `IKIGAI_MEMORY_DB` env first, then tries canonical paths. Lets
  tests inject a fixture without code changes.
- **Daemon metadata corruption**: `taskdog-server` pipx metadata got
  wiped (probably by daemon-watchdog running during broken install).
  `pipx install --force taskdog-server` recovered. Future-proof:
  skip `taskdog-server` restart in watchdog when venv is locked.

## Discovered: taskdog-server metadata corruption

After M88 changes, `tests/test_taskdog_harness_e2e.py` failed with
"Cannot connect to server at http://127.0.0.1:8000". Investigation:
- `taskdog-server` pipx metadata was missing (`pipx list` showed warning)
- `~/.local/bin/taskdog-server.exe` was gone
- Fix: `pipx install --force taskdog-server` + restart manually
- Server is now back at port 8000 with 160 tasks (was 155 + 5 from M83)

## Out of scope (Day 2)

- `tag_and_persist` real wiring to tools_v2
- `commit_node` real taskdog_create_task invocation
- `dispatch_sub_agents` sub-agent fan-out
- MCP observation wrappers (vault/ikigai/meta/cycle_state reader)
- `_handle_ikigai_sync_vault` function
- Re-register v2 graph in `langgraph.json`

These remain skip-tagged. Estimated ~1.5 days focused work.
