---
name: M94-invoke-skill-real-graph
description: invoke_skill actually runs the v2 graph + v2 daily alias command + CLI error handling
owner: matheus-mendes
status: DONE
milestone: M94
estimated_cost_usd: 0.10
constitution_refs:
  - tests_are_the_contract
  - reversibility_over_cleverness
---

# M94 - invoke_skill real graph execution + v2 daily command

## Context

After M92, 4 v2_daily_skill tests were still skip-tagged because
`invoke_skill` only stub-dispatched and never ran the actual graph.
M94 makes `invoke_skill` truly execute `make_v2_graph().invoke()`,
and re-introduces the `v2 daily` command as a thin alias.

## What changed

### interfaces/cli/invoke_skill.py

- `invoke_skill()` now:
  - **Validates entry_point against `graph.NODES`** → raises ValueError
    with "Invalid entry_point" message
  - **Logs WARNING** when `entry_point_override` differs from manifest default
  - **Runs the actual graph** via `make_v2_graph(checkpoint_db=":memory:", ...)`,
    passing `thread_id` config (required by SqliteSaver)
  - **Promotes user-facing fields** (user_suggestions, suggestions_count,
    suggestions_language, commit_summary, last_step, iteration) from graph
    result into top-level result
  - **Falls back gracefully** on graph errors — captures exception as
    `graph_run_error` field in graph_state; doesn't crash
  - Returns raised `ValueError("manifest not found")` instead of empty
    state dict (cleaner API; CLI catches ValueError)

### interfaces/cli/v2.py

- New `register_daily(app)` registers `v2 daily` command as alias for
  `v2 invoke-skill ikigai-daily`. Output shape:
  ```
  {"surface": {"skill": ..., "entry_point": ..., "suggestions": [...],
                "suggestions_count": N, "language": "pt-BR"}}
  ```
- `register_invoke_skill(app)` now catches `ValueError` from the inner
  `invoke_skill()` and returns structured error dict (preserves
  `test_invoke_skill_unknown_returns_empty_state` contract: exit 0).

### src/ikigai/tests/test_v2_daily_skill.py

- Removed all 4 M92 skip-tags for tests that need full graph execution
- All 9 tests now PASS

## Acceptance

- [x] `test_invoke_skill_with_override_different_logs_warning` PASS (warning logged)
- [x] `test_invoke_skill_unknown_entry_point_raises` PASS (ValueError)
- [x] `test_invoke_skill_daily_returns_user_suggestions` PASS (graph populates)
- [x] `test_daily_command_surface_suggestions_via_skill` PASS (alias works)
- [x] `test_invoke_skill_importable/loads_daily_manifest/uses_default` PASS (unchanged)
- [x] ikigai 804 PASS + 23 SKIP, 0 FAIL (was 800 + 27, +4 tests PASS)
- [x] root 368 PASS + 27 SKIP, 0 FAIL (was 367 + 1 FAIL, +1 PASS)
- [x] drift 18/18 PASS

## Lessons

- **Graph result promotion is verbose but necessary**: surface-level
  fields (user_suggestions, commit_summary) need to appear at top level
  for CLI consumers. Nested under `graph_state` works internally but
  bloats the surface contract.
- **SqliteSaver requires `thread_id` config**: discovered via
  `Checkpointer requires one or more of the following 'configurable'
  keys: thread_id, checkpoint_ns, checkpoint_id`. Use stable per-skill
  thread_id for checkpoint continuity.
- **CLI vs Python API split**: Python `invoke_skill()` raises
  ValueError (cleaner API for test asserts). CLI catches ValueError
  and surfaces it as a structured error dict (preserves backward-compat
  with `test_invoke_skill_unknown_returns_empty_state`).
- **Thin command aliases are cheap**: `register_daily()` is 12 LOC
  including docstring + output shape. Restoring deleted commands as
  aliases costs nothing.

## Out of scope

- `v2 suggest/score/regime/cycle` commands (8 tests still skip-tagged
  because they reference V5-D-removed commands). Adding them as
  aliases for the corresponding graph entry_points would unskip those
  tests but doesn't add new functionality.
- Migrating `invoke_skill` to use real LangGraph server (would need
  `langgraph dev` running, requires `langgraph_cli` install)
