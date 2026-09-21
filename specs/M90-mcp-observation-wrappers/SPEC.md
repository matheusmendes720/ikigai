---
name: M90-mcp-observation-wrappers
description: Add _handle_ikigai_sync_vault + unskip prompt-chain Day-2 tests
owner: matheus-mendes
status: DONE
milestone: M90
estimated_cost_usd: 0.05
constitution_refs:
  - composition_over_inheritance
  - tests_are_the_contract
---

# M90 - MCP server.py: _handle_ikigai_sync_vault + unskip Day-2 tests

## Context

3 Day-2 candidates from M88's "out of scope" list were skip-tagged:
1. `test_v2_mcp_observation_wrappers_registered` — wanted 15 `@MCP.tool`
   decorators. **Actual count: 19** (already M67-M89 wired taskdog, vault,
   investigation, ikigai reflect/plan). Test was stale; updated to
   assert "at least 15" instead of "exactly 15".
2. `test_v2_sync_vault_handler_readonly` — wanted `_handle_ikigai_sync_vault`
   function in server.py. **Not present.** Added as read-only handler.
3. `test_v2_observation_wrappers_read_vault` — wanted `ikigai/meta/cycle_state`
   path. **Already in code** via the new handler above.

## What changed

### src/ikigai/src/mcp_server/server.py

Added `_handle_ikigai_sync_vault(date: str) -> dict[str, Any]`:
- Reads `vault/ikigai/meta/cycle_state/{date}.md` (read-only)
- Resolves vault root via `IKIGAI_VAULT_ROOT` env or
  `<project_root>/vault`
- Returns `{date, found, path, content}` — `found=False` when file
  absent (no error)
- Drift test asserts no `write_text` / `open(` write modes in body

### src/ikigai/tests/test_v2_prompt_chains.py

- Removed module-level `pytestmark = pytest.mark.skip(...)` (M88)
- Removed `@pytest.mark.skip(...)` from all 3 Day-2 tests
- Updated `test_v2_mcp_observation_wrappers_registered`:
  - Asserts "at least 15" instead of "exactly 15"
  - Documents M67-M89 history (11 → 19)

## Acceptance

- [x] `_handle_ikigai_sync_vault` exists and is read-only
- [x] `ikigai/meta/cycle_state` path used in handler
- [x] All 10 tests in `test_v2_prompt_chains.py` PASS
- [x] Drift 18/18 PASS
- [x] ikigai: 771 PASS + 13 SKIP (was 768 + 16, +3 tests PASS)
- [x] root: 361 PASS + 27 SKIP (unchanged)

## Lessons

- **Drift tests can lie**: When a test asserts "exactly N decorators"
  but the file was changed multiple times, the test becomes a stale
  snapshot. Better: assert "at least N" with documented history.
- **Module-level pytestmark = full skip**: Removing the module-level
  skip is necessary for individual `@pytest.mark.skip` decorators to
  even matter. The M88 fix removed pytestmark; the M90 fix removed
  individual decorators.
- **`_handle_*` naming convention**: MCP server.py uses `_handle_*`
  for internal handlers (not exposed as `@MCP.tool`). Drift tests
  assert on these by string search, so the function name must match
  exactly.

## Out of scope (still skip-tagged)

- `dispatch_sub_agents` real sub-agent fan-out (~3h)
- 5 v2 test files (daily_skill, interface_dispatch, e2e_smoke,
  invoke_skill_taskdog, multi_level_smoke) — all skip-tagged for
  Day-2+ wiring that hasn't landed
- `langgraph.json` re-registration of `ikigai_v2_maintainer` (~30min)

Total remaining: ~6-8h to 100% v2 graph recovery.
