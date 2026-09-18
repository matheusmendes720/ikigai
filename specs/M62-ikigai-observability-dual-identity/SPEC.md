---
name: M62-ikigai-observability-dual-identity
description: IKIGAI observability dual-identity swap — unblock tests/test_reasoning_chain.py
owner: matheus-mendes
status: DONE
milestone: M62
estimated_cost_usd: 0.30
constitution_refs:
  - tests_are_the_contract
  - state_on_disk_not_conversation
---

# M62 — IKIGAI observability dual-identity (narrow scope)

## Context

After M59 (which fixed the mesh `src.mesh.X` vs `mesh.X` dual-identity),
the same pattern persists inside `src/ikigai/`: callers import
`from observability.X` while the conftest + production paths import
`from src.ikigai.src.observability.X`. Python loaded two distinct
module entries, the live test fixture monkeypatched only one, and
tests that walked the deepagents graph (specifically
`tests/test_reasoning_chain.py`) were collection-errors.

## What changed (M62.1)

5 files rewritten `from observability.X import Y` →
`from src.ikigai.src.observability.X import Y`:
- `src/ikigai/src/agents/deepagents_harness.py`
- `src/ikigai/src/agents/v2/graph.py`
- `src/ikigai/src/agents/v2/harness_legacy_reference.py`
- `src/ikigai/src/agents/v2/mcp_bridge.py`
- `src/ikigai/src/mcp_server/tracing.py`

## Acceptance

- [x] `tests/test_reasoning_chain.py` 3/3 PASS (was collection error)
- [x] `tests/test_v2_imports_safely.py` 8/8 PASS (preserved)
- [x] Drift net 69/69 PASS (preserved)
- [x] Phase 3 mesh 136/136 PASS (preserved)

## Out of scope (M62.2+ if user requests)

1. 8 dangling `from sys_ikigai.X import Y` imports where `sys_ikigai.*`
   modules do not exist on disk. Implementation would require recreating
   vault wrappers + UnifiedMCPGateway per ADR-012.
2. `from interfaces.cli.v2 import invoke_skill` ImportErrors in
   `tests/test_v2_daily_skill.py` (W3.5 spec was written but never
   implemented).
