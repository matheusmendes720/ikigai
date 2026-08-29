# B3.5 Fix Report — Iteration 1 + 2

## Status
DONE

## Commits Amended
- `78f6ca1`: build: add make mcp-inspect contract test for MCP gateway (B3.5)
  - Iter 1 (`daf1d0e`): added list_resource_templates + server.py latent B3.1 fix
  - Iter 2 (`78f6ca1`): fixed camelCase attribute names on MCP SDK Pydantic models

## Iter 1 Fix Summary

The B3.5 implementer (`035de10`) made 2 unauthorized changes:
1. Modified `src/ikigai/src/mcp_server/server.py:755` — `MCP.run_async(transport="stdio")` → `MCP.run_stdio_async()` (legitimate FastMCP API correction; latent B3.1 bug surfaced by B3.5 contract test)
2. Reduced default `DEFAULT_RESOURCE_COUNT` from 6 to 3 (incorrect — only counted `list_resources()`, missed `list_resource_templates()`)

**Resolution:**
- Kept server.py fix in B3.5 commit (correct API call; documented as latent B3.1 bug)
- Updated `scripts/mcp_inspect.py` to call BOTH `list_resources()` AND `list_resource_templates()`
- Restored `DEFAULT_RESOURCE_COUNT = 6` per A2UI spec §11 R4
- Amended commit `035de10` → `daf1d0e` with extended message

## Iter 2 Fix Summary

After iter 1 amend, smoke test of `scripts/mcp_inspect.py` still FAILED with:
```
[mcp-inspect] FAIL: ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
```

Root cause: MCP Python SDK Pydantic models use camelCase attributes (per JSON-RPC schema), but the iter-1 fix used snake_case:
- `templates_result.resource_templates` ❌ → `templates_result.resourceTemplates` ✅
- `t.uri_template` ❌ → `t.uriTemplate` ✅

This pattern is consistent with `init_result.serverInfo` (already correct in script).

**Resolution (controller-level intervention):**
- Edited `scripts/mcp_inspect.py` lines 112-113 to use `resourceTemplates` + `uriTemplate`
- Added comment explaining camelCase convention for future maintainers
- Amended commit `daf1d0e` → `78f6ca1` with full history in commit message

## Test Results (VERBATIM — post-amend `78f6ca1`)

```
$ /c/Python314/python.exe scripts/mcp_inspect.py 2>&1 | tail -5
[mcp-inspect] initialized: server=ikigai-gateway
[mcp-inspect] tools: 13 -> ['ikigai_score', 'ikigai_regime', 'ikigai_phase', 'ikigai_decompose', 'ikigai_corrections', 'ikigai_plan_cycle', 'ikigai_checkpoint', 'ikigai_sync_vault', 'ikigai_write_tasks', 'ikigai_read_tasks', 'ikigai_mesh_show', 'ikigai_task_create', 'ikigai_health']
[mcp-inspect] resources: 3 -> ['queue://pending', 'health://gateway', 'plans://cycles']
[mcp-inspect] resource_templates: 3 -> ['ueid://{ueid}', 'queue://events/{event_id}', 'plans://cycles/{cycle_id}']
[mcp-inspect] PASS (13 tools, 6 resources = 3 concrete + 3 templates)
```

```
$ PYTHONPATH=. /c/Python314/Scripts/pytest.exe interfaces/cli/tests/test_mcp_inspect.py interfaces/cli/tests/test_mcp_gateway_probe.py interfaces/cli/tests/test_server.py -v 2>&1 | tail -10
interfaces\cli\tests\test_mcp_inspect.py::test_mcp_inspect_script_exists PASSED [ 33%]
interfaces\cli\tests\test_mcp_inspect.py::test_mcp_inspect_script_compiles PASSED [ 66%]
interfaces\cli\tests\test_mcp_inspect.py::test_mcp_inspect_script_help PASSED [100%]
... (33 more tests, all PASSED)
============================= 36 passed in 0.81s ==============================
```

## Fix Verification (both iterations)
- [x] mcp_inspect.py calls BOTH list_resources AND list_resource_templates
- [x] PASS line shows total = 6 (3 concrete + 3 templates) per A2UI spec §11 R4
- [x] MCP SDK Pydantic attribute names use camelCase (resourceTemplates, uriTemplate, serverInfo)
- [x] server.py uses correct FastMCP method (run_stdio_async)
- [x] No Co-Authored-By trailer
- [x] All 36 tests pass + contract test PASS line

## Self-Review
- **Lesson learned:** MCP Python SDK Pydantic models always use camelCase (per JSON-RPC schema). Use `dir()` to verify attribute names, never assume snake_case.
- **Lesson learned:** When a contract test surfaces a latent bug (e.g., `run_async` not existing), it's worth keeping the fix in the same commit if both the test AND the fix are required for the contract to pass.
- **Lesson learned:** Implementer subagents can make "helpful" scope expansions (e.g., reducing resource count to match what they observed). Always cross-check against the original spec/contract before accepting scope changes.

## Notes for Reviewer
- B3.5 required 2 fix iterations to pass the contract test end-to-end
- Both fixes are minimal and well-scoped (no unrelated changes)
- The amended commit message documents both fixes for future archeology