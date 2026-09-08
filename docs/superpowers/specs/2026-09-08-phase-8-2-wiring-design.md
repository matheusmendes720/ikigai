# Phase 8.2 — Wire Real MCP Tool Calls into v2 Graph Nodes

**Date:** 2026-09-08
**Status:** APPROVED — 7 design decisions locked
**Scope:** Read-only plumbing, no math (ADR-013 boundary preserved)
**Source:** `src/ikigai/src/agents/v2/graph.py` L6-7 — "Phase 8.2 will wire actual MCP tool calls"

## Background

`src/ikigai/src/agents/v2/graph.py` ships 11 v2 nodes that currently call `tools_v2.py` helpers — 8 `@tool` decorated functions wrapping `prompts/*.py` JSON renderers. These render observation JSON but DO NOT execute MCP calls against the gateway. Phase 8.2 transforms prompt-chain stubs into real executor.

## Locked Design Decisions (7)

### 1. Scope: Read-only plumbing, no math
- Wire read-only MCP calls (vault read, state read, observations)
- NO math/policy/scoring writes to vault
- ADR-013 planner-only boundary preserved

### 2. MCP surface: 12 IKIGAI_TOOLS canonical
- Drift-detector in `test_canonical_scope.py` continues to enforce 12 IKIGAI_TOOLS
- Phase 8.2 adds a thin WRAPPER layer (`mcp_bridge.py`) — does NOT add new IKIGAI_TOOLS
- IKIGAI_NODE_TOOLS=8 stays separate (different variable, not drift-scanned)

### 3. Error policy: Graceful degradation
- mcp_bridge raises → caught at node boundary → `error_channel` field populated
- Conditional edge routes to `error_node` via existing `_route_after_*_error` paths
- Partial cycle verdict via existing `error_node` → `commit_summary` flow

### 4. Observability: Stub for Phase 8.3
- `_no_op_tracer` stub stays unchanged in graph.py
- Phase 8.3 will replace with real OTel tracing
- Phase 8.2 only wires MCP calls; observability is deferred

### 5. Rollout: Staged — 3 atomic commits

**T-8.2.1: PAV-observation reads (4 nodes)**
- `observe` → mcp_bridge wrapper around an IKIGAI observation tool
- `score_vectors` → mcp_bridge wrapper
- `heuristics` → mcp_bridge wrapper
- `balance` → mcp_bridge wrapper
- Includes `mcp_bridge.py` + `FakeMcpServer` test fixture

**T-8.2.2: Vault/state reads (4 nodes)**
- `decompose` → mcp_bridge wrapper
- `plan` → mcp_bridge wrapper
- `reflect` → mcp_bridge wrapper
- `tag_and_persist` → read-only tag read via mcp_bridge (vault_write NOT wired here)
- Builds on T-8.2.1 mcp_bridge.py

**T-8.2.3: In-process nodes + e2e (2 nodes)**
- `dispatch_sub_agents` → in-process (no MCP)
- `commit` → in-process commit summary (reads prior node outputs)
- Adds e2e test that runs full graph with FakeMcpServer

### 6. Test strategy: Mock MCP server
- `FakeMcpServer` class in test fixture, canned responses keyed by tool name
- In-process, no daemon, no subprocess
- $0/tick, <1s/run
- Tests patch `mcp_bridge` module via `monkeypatch.setattr`

### 7. Wiring layer: Centralized bridge module
- `src/ikigai/src/agents/v2/mcp_bridge.py` — thin async wrappers, one per canonical IKIGAI_TOOL
- Single test seam: `mcp_bridge.ikigai_X(...)` callable from any node
- Monkeypatch-friendly for tests

## Architecture

```
v2 Node (e.g. observe_node)
   │
   ↓ calls (sync API; underlying bridge is async via asyncio.run)
mcp_bridge.ikigai_observe_pav_state(date)
   │
   ↓ wraps
async mcp_client.call("ikigai_observe_pav_state", {"date": date})
   │
   ↓ routes to (production)
MCP Gateway stdio → tool handler → return JSON

   ↓ routes to (tests via monkeypatch)
FakeMcpServer.canned_response("ikigai_observe_pav_state", date) → return JSON
```

## Files

**Create:**
- `src/ikigai/src/agents/v2/mcp_bridge.py` — 12 thin async wrappers, sync API via `asyncio.run`
- `src/ikigai/src/agents/v2/tests/fixtures/fake_mcp_server.py` — canned-response mock
- `src/ikigai/src/agents/v2/tests/test_mcp_bridge.py` — bridge unit tests
- `src/ikigai/src/agents/v2/tests/test_phase_8_2_wiring.py` — e2e graph test

**Modify (T-8.2.1):**
- `src/ikigai/src/agents/v2/nodes/observe.py` — replace prompt-chain stub with mcp_bridge call
- `src/ikigai/src/agents/v2/nodes/score_vectors.py` — same
- `src/ikigai/src/agents/v2/nodes/heuristics.py` — same
- `src/ikigai/src/agents/v2/nodes/balance.py` — same

**Modify (T-8.2.2):**
- `src/ikigai/src/agents/v2/nodes/decompose.py`
- `src/ikigai/src/agents/v2/nodes/plan.py`
- `src/ikigai/src/agents/v2/nodes/reflect.py`
- `src/ikigai/src/agents/v2/nodes/tag_and_persist.py` — read-only tag read

**Modify (T-8.2.3):**
- `src/ikigai/src/agents/v2/nodes/dispatch_sub_agents.py` — in-process dispatch
- `src/ikigai/src/agents/v2/nodes/commit.py` — in-process commit summary

## Acceptance Criteria (Milestone-Level)

- [ ] All 10/11 v2 nodes wired to mcp_bridge OR in-process observation (tag_and_persist read-only only; surface_intentions deferred)
- [ ] `mcp_bridge.py` exists with 12 async wrappers
- [ ] `FakeMcpServer` fixture exists
- [ ] Drift 32/32 PASS preserved (no IKIGAI_TOOLS count change)
- [ ] All tests under `src/ikigai/tests/` + `src/ikigai/src/agents/v2/tests/` PASS
- [ ] No math/policy/scoring writes to vault (ADR-013)
- [ ] Phase 8.2 commit history = 3 atomic commits

## Out of Scope (Deferred)

- Real observability / OTel tracing — Phase 8.3
- vault_write wiring in `tag_and_persist` — separate work
- PAV math execution — explicitly forbidden per ADR-013
- New IKIGAI_TOOLS additions — drift detector enforces 12
- `surface_intentions` node — deferred (per roadmap, not blocking)

## Risk Notes

- Dual-module identity bug class (per W6.X item 3): if nodes import `from src.contracts.X` but tests monkeypatch `sys.modules["contracts.X"]`, patch silently no-ops. Tests must patch BOTH identities or use dotted-prefix consistently.
- Windows stdio binary mode: any new MCP stdio handshake must use `sys.stdin.buffer.readline()` not `sys.stdin.readline()` (commit `b93a1f3`).
