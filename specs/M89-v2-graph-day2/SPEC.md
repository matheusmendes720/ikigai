---
name: M89-v2-graph-day2
description: v2 graph Day 2 - real tag_and_persist (vault_write) + commit (taskdog) wiring
owner: matheus-mendes
status: DONE
milestone: M89
estimated_cost_usd: 0.10
constitution_refs:
  - composition_over_inheritance
  - reversibility_over_cleverness
  - tests_are_the_contract
---

# M89 - v2 graph Day 2: real tag_and_persist + commit

## Context

After M88 fixed the recursion and populated recall/reason stubs,
the v2 graph still had two terminal stubs that surfaced "mcp_bridge
missing" errors (per M12 deletion of `ikigai_tag_and_persist` and
`ikigai_commit_summary` wrappers).

Day 2 (M89) replaces those stubs with direct calls to:
- `proposal_executor.wrap_vault_write` (ADR-029) for `tag_and_persist_node`
- `agents.tools.taskdog_create_task` for `commit_node`

The MCP bridge layer was bypassed deliberately — adding wrappers back
requires server.py registration changes (drift-detector-enforced
canonical scope). Bypassing means we use the same canonical write
path that proposal_executor.py already uses, which is already
drift-detected and tested.

## What changed

### src/ikigai/src/agents/v2/nodes/tag_and_persist.py (rewritten)

- Reads `proposed_entity`, `vault_path`, `actor` from state
- Falls back to error_channel entry when missing
- Lazy-imports `proposal_executor.wrap_vault_write` (consolidates
  vault_write wiring in one module)
- Serializes entity to dict (handles pydantic v2 `.model_dump()`,
  plain dicts, or stringifies anything else)
- Returns `persisted: bool` + `error_channel: list[str]`

### src/ikigai/src/agents/v2/nodes/commit.py (rewritten)

- Reads `draft_proposal.operations` from state
- Iterates operations; for `task.create`, fires
  `taskdog_create_task` via `sys.modules` lookup pattern
  (same as invoke_skill.py)
- Produces canonical `commit_summary`:
  `"COMMIT cycle={id} tier={tier} proposal={proposal_id} ok=True"`
- Tier detection: `dream` > `goal` > `daily` (from active_dream_ueid
  and active_goal_ueids)
- Sets `terminated: True` to signal graph wind-down
- Captures taskdog results in `commit.taskdog_results`, never crashes
  on failures (graceful degradation)

### tests/test_v2_day2_nodes.py (NEW)

15 tests covering:
- tag_and_persist: missing fields, success path, vault_write failure,
  dict-entity serialization, dict-actor override
- commit: tier detection (daily/dream/goal), missing proposal,
  task.create firing, taskdog failure graceful, non-task ops skipped,
  missing tools module

## Acceptance

- [x] tag_and_persist writes via wrap_vault_write (proposal_executor)
- [x] commit_node fires taskdog_create_task for task.create ops
- [x] Drift 18/18 PASS
- [x] ikigai: 768 PASS + 16 SKIP (unchanged - graph smoke already passing)
- [x] root: 361 PASS + 27 SKIP (was 346, +15 new tests)
- [x] 15/15 unit tests for new tag_and_persist + commit behavior

## Lessons

- **Module consolidation**: Both `wrap_vault_write` and `taskdog_create_task`
  already had canonical lazy-proxy definitions (in proposal_executor.py
  and agents/tools.py respectively). tag_and_persist and commit_node
  just consume those proxies — no new wiring needed.
- **`sys.modules` lookup pattern**: For tools that live behind conditional
  imports, use `sys.modules.get()` at call-time. Tests can monkeypatch
  either `agents.tools` or `src.ikigai.src.agents.tools` and the lookup
  finds the right one.
- **MagicMock with attributes is cleaner than dict returns**: For
  `wrap_vault_write` returning an `ExecutionReport`-like object, use
  `MagicMock(ok=True, error=None)` instead of `{"ok": True}`. Avoids
  fragile `isinstance` checks on result.
- **Tied wiring reduces test fragility**: Both tag_and_persist and
  proposal_executor import `wrap_vault_write` lazily from the same
  module. Tests patch at the source (proposal_executor.wrap_vault_write),
  not the destination, so changes to one path don't break the other.

## Out of scope (still Day-2 candidates)

- 4 additional `@MCP.tool` decorators in server.py (test_v2_mcp_observation_wrappers_registered
  wants 15, currently 11). Requires designing the missing handlers
  (ikigai_observe_pav_state, ikigai_reflect, ikigai_score_vectors, ikigai_heuristics).
- `_handle_ikigai_sync_vault` function (read-only vault sync handler).
- `dispatch_sub_agents` real sub-agent fan-out (currently passthrough).
- `langgraph.json` re-registration of `ikigai_v2_maintainer` graph.
- Unskip `test_v2_daily_skill`, `test_v2_interface_dispatch`,
  `test_v2_e2e_smoke`, `test_v2_invoke_skill_taskdog`, `test_v2_multi_level_smoke`.

These remain skip-tagged for future work.
