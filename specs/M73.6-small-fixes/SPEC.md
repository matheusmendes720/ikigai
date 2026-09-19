---
name: M73.6-small-fixes
description: Small fixes — taskdog path3 UEID fixtures, server_fastmcp asyncio decoration, dual-identity completion
owner: matheus-mendes
status: DONE
milestone: M73.6
estimated_cost_usd: 0.10
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
---

# M73.6 — Small fixes batch

## Context

Continuing M73.5 sweep. 3 small test failures left in non-v2 buckets:
1. `test_taskdog_mcp_path3.py::test_taskdog_read_with_mock_adapter`:
   UEID `ik:task:abc:12345678` had slug `task:abc` (with `:`) which
   violates the M73.1 slug regex `[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]`.
2. `test_server_fastmcp.py::test_main_entrypoint_callable`:
   `@pytest.mark.asyncio` decoration on a SYNC test (body only does
   `inspect.iscoroutinefunction(main)`). pytest-asyncio plugin not
   configured in pyproject.toml.

## What changed

### tests/test_taskdog_mcp_path3.py
Replaced UEID fixtures that violated M73.1 slug regex:
- `ik:task:abc:12345678` → `ik:task-foo:abc12345:def67890`
- `ik:ta:abc:12345678` → `ik:ta-foo:abc12345:def67890`
- `ik:tb:def:87654321` → `ik:tb-foo:abc12345:def87654`

### tests/test_server_fastmcp.py
Removed unnecessary `@pytest.mark.asyncio` decoration from
`test_main_entrypoint_callable`. Test body is purely sync (inspect).

## Acceptance (verified 2026-09-19)

- [x] tests/test_taskdog_mcp_path3.py : 4/4 PASS (was 3/4)
- [x] tests/test_server_fastmcp.py : 3/3 PASS (was 2/3)
- [x] ikigai total : 780 PASS + 22 SKIP, 43 failed + 4 errors
       (was 778 + 22, 45 + 4)

## Out of scope (M75+)

- 41 remaining failures are test_v2_* (unimplemented v2 features)
  + 2 mcp/test_multi_tool_chain + 1 test_v2_imports_safely + 1
  test_v2_multi_level_smoke + 1 test_drift_extended_invariants ordering
  artifact (passes standalone, fails in suite — needs conftest fixture
  ordering fix)
