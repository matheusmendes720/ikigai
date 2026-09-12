# Review L4 — MCP Gateway

**Task:** T-11.5 (M11 IKIGAI Agentic System Top-Down Review)
**Branch:** master
**Date:** 2026-09-12
**Scope:** `src/ikigai/src/mcp_server/` + `src/ikigai/src/agents/{tools,tools_sf,tools_taskdog,tools_tuiboard}.py` + `src/ikigai/src/agents/v2/mcp_bridge.py`

---

## Summary

| Check | Result |
|------|--------|
| IKIGAI_TOOLS count | exactly **12** (drift net enforces — `test_ikigai_tools_count_is_12` PASSING) |
| MCP gateway `@MCP.tool` count | **11** (8 IKIGAI + 3 Plan C investigation) — DOWN from 15 in Diag 02 2026-09-04 |
| MCP gateway `@MCP.resource` count | **6** (unchanged from Diag 02) |
| Separate taskdog FastMCP instance | **3 read-only tools** (Path 3 — NOT wired into `ikigai-gateway`) |
| Total MCP gateway surface | **11 tools + 6 resources = 17** (DOWN from 21 in Diag 02) |
| Fork subprocess tools (LangChain `@tool`) | **10** bound to `IKIGAI_TOOLS` (2 solverforge + 4 tuiboard + 4 taskdog) |
| v2 graph mcp_bridge wrappers | **9 wired + 3 unwired** = 12 candidates (names diverge from MCP gateway) |
| Provisional gaps | 5 (see §6) |

---

## 1. File Inventory — `src/ikigai/src/mcp_server/`

| File | LOC | Role |
|------|-----|------|
| `__init__.py` | 6 | Re-exports the 3 investigation helpers |
| `__main__.py` | 9 | Entrypoint for `python -m mcp_server` |
| `server.py` | 260 | `ikigai-gateway` FastMCP instance, 11 `@MCP.tool` + 6 `@MCP.resource` |
| `tools_mesh.py` | 176 | Handlers for `ikigai_mesh_show`, `ikigai_task_create`, `ikigai_health` |
| `tools_vault.py` | 100 | Handlers for `vault_write`, `vault_read` (sole vault writer per ADR-012) |
| `resources.py` | 165 | Handlers for all 6 MCP resources |
| `handlers.py` | 131 | Single surviving handler `_handle_ikigai_decompose` (V5-E trimmed 5 doomed handlers) |
| `investigation_enqueue.py` | 54 | Plan C Task 3 handler |
| `investigation_status.py` | 43 | Plan C Task 3 handler |
| `investigation_complete.py` | 56 | Plan C Task 3 handler |
| `taskdog_tools.py` | 101 | SEPARATE FastMCP instance `mcp = FastMCP(name="taskdog")` with 3 read-only Path-3 tools |
| `tracing.py` | 100 | OpenTelemetry dispatcher (`init_mcp_tracing` + `traced_tool_dispatch` + dict-vs-kwargs protocol detection) |

---

## 2. MCP Gateway Tool Inventory (server.py)

### 2.1 `@MCP.tool` decorators — **11 total**

| # | Tool name | Source module | Category | Actor-gated | Status |
|---|-----------|---------------|----------|-------------|--------|
| 1 | `ikigai_decompose` | `handlers.py:_handle_ikigai_decompose` | IKIGAI data | no | active |
| 2 | `ikigai_write_tasks` | `sys_ikigai.vault.task_io._write_tasks_to_data` | IKIGAI data | no | active |
| 3 | `ikigai_read_tasks` | `sys_ikigai.vault.task_io._read_tasks_from_data` | IKIGAI data | no | active |
| 4 | `ikigai_mesh_show` | `tools_mesh.py:ikigai_mesh_show` | IKIGAI data (cross-fork join) | no | active |
| 5 | `ikigai_task_create` | `tools_mesh.py:ikigai_task_create` | IKIGAI data (create-only v1) | no | active |
| 6 | `ikigai_health` | `tools_mesh.py:ikigai_health` | IKIGI heartbeat | no | active |
| 7 | `vault_write` | `tools_vault.py:vault_write` | Vault (sole writer per ADR-012) | yes (`actor: Literal["user","agent","system"]`) | active |
| 8 | `vault_read` | `tools_vault.py:vault_read` | Vault (read-side mirror of `vault_write`) | no | active |
| 9 | `investigation_enqueue` | `investigation_enqueue.py` | Plan C investigation | no | active |
| 10 | `investigation_status` | `investigation_status.py` | Plan C investigation | no | active |
| 11 | `investigation_complete` | `investigation_complete.py` | Plan C investigation | no | active |

**Breakdown: 8 IKIGAI (5 data-plane + 2 vault + 1 decompose) + 3 Plan C investigation = 11.**

### 2.2 `@MCP.resource` decorators — **6 total**

| # | URI | Handler | Purpose |
|---|-----|---------|---------|
| 1 | `ueid://{ueid}` | `resources.py:ueid_resource` | Cross-fork view (4-key contract: cli/taskdog/solverforge_calendar/a2ui) |
| 2 | `queue://pending` | `resources.py:queue_pending_resource` | List pending TaskChange events |
| 3 | `queue://events/{event_id}` | `resources.py:queue_event_resource` | One TaskChange event JSON |
| 4 | `health://gateway` | `resources.py:health_resource` | Gateway heartbeat (mirrors `ikigai_health` tool) |
| 5 | `plans://cycles` | `resources.py:plans_cycles_resource` | List recent PlanningCycles from `~/.ikigai/plan_entities.db` |
| 6 | `plans://cycles/{cycle_id}` | `resources.py:plans_cycle_resource` | One PlanningCycle full record |

### 2.3 Tools deleted by V5-E ("Opção B-A — radical-máxima")

V5-E (commit `b960e852`, 2026-09-07) removed 7 `@MCP.tool` decorators reclassified as anti-patterns per ADR-013 (planner-only, no PAV math execution):

| Deleted tool | Reason |
|--------------|--------|
| `ikigai_score` | read PAV-written vault artifact |
| `ikigai_regime` | read PAV-written vault artifact |
| `ikigai_phase` | read PAV-written vault artifact |
| `ikigai_corrections` | read PAV-written vault artifact |
| `ikigai_plan_cycle` | read PAV-written vault artifact |
| `ikigai_checkpoint` | read PAV-written vault artifact |
| `ikigai_sync_vault` | read PAV-written vault artifact |

Also removed from `handlers.py`: `_handle_ikigai_score`, `_handle_ikigai_sync_vault`, plus 4 orphan helpers (`_db_path`, `_vault_root`, `_extract_frontmatter_field`, `_read_checkpoint`).

The drift-net retest (`test_v2_mcp_observation_wrappers_registered` in `test_v2_prompt_chains.py`) was retired alongside its source.

---

## 3. IKIGAI_TOOLS Registry — **12 entries (drift net enforced)**

**File:** `src/ikigai/src/agents/tools.py:556-584`

### 3.1 Initial list — 10 tools (lines 556-570)

| Category | Tool name | Source module |
|----------|-----------|---------------|
| Solverforge Calendar | `solverforge_list_events` | `tools_sf.py:67` |
| Solverforge Calendar | `solverforge_create_event` | `tools_sf.py:103` |
| Tuiboard Kanban | `tuiboard_list_boards` | `tools_tuiboard.py:111` |
| Tuiboard Kanban | `tuiboard_get_tasks` | `tools_tuiboard.py:141` |
| Tuiboard Kanban | `tuiboard_update_task` | `tools_tuiboard.py:213` |
| Tuiboard Kanban | `tuiboard_create_task` | `tools_tuiboard.py:181` |
| Taskdog (Path 1 subprocess) | `taskdog_list_tasks` | `tools_taskdog.py:73` |
| Taskdog (Path 1 subprocess) | `taskdog_create_task` | `tools_taskdog.py:109` |
| Taskdog (Path 1 subprocess) | `taskdog_complete_task` | `tools_taskdog.py:148` |
| Taskdog (Path 1 subprocess) | `taskdog_get_task` | `tools_taskdog.py:183` |

### 3.2 B7.3 extension — 2 tools (lines 579-584)

| Category | Tool name | Source module |
|----------|-----------|---------------|
| Vault read | `ikigai_read_strategics` | `agents/ikigai_read_strategics.py` |
| Vault read | `ikigai_read_vault` | `agents/ikigai_read_vault.py` |

**Total: 10 + 2 = 12.** `vault_write` is NOT in `IKIGAI_TOOLS` (the agent cannot self-write — only the human/agent-explicit `vault_write` MCP tool can).

### 3.3 Drift net enforcement

```python
def test_ikigai_tools_count_is_12() -> None:
    """IKIGAI_TOOLS list MUST have exactly 12 entries (data + vault reads).
    Adding any math/policy/scoring tool violates ADR-013.
    """
    # AST-scans tools.py for both `IKIGAI_TOOLS = [...]` and
    # `IKIGAI_TOOLS.extend([...])` calls — counts both
    assert total_count == 12, (
        f"IKIGAI_TOOLS must contain exactly 12 entries per ADR-013; "
        f"found {total_count}. Adding/removing requires updating ADR-013."
    )
```

**Verified at 2026-09-12: `pytest src/ikigai/tests/test_canonical_scope.py::test_ikigai_tools_count_is_12` → 1 passed.**

---

## 4. Fork MCP Tools — separate FastMCP instance

### 4.1 `taskdog_tools.py` — Path 3 read-only

| # | Tool name | Module | Purpose | Wired to `ikigai-gateway`? |
|---|-----------|--------|---------|---------------------------|
| 1 | `taskdog_read` | `taskdog_tools.py:48` | Read taskdog slice by UEID | **NO** — separate FastMCP instance |
| 2 | `taskdog_list` | `taskdog_tools.py:66` | List taskdog slices (filterable) | **NO** — separate FastMCP instance |
| 3 | `taskdog_supports_field` | `taskdog_tools.py:89` | Capability check | **NO** — separate FastMCP instance |

**Why separate?** `taskdog_tools.py` declares `mcp = FastMCP(name="taskdog")` (line 32) — a different FastMCP instance from the global `MCP = FastMCP("ikigai-gateway")` in `server.py`. Per the module docstring, this is to avoid cross-talk with ADR-013 canonical-scope enforcement. Path 1 (the 4 `taskdog_*` tools bound to `IKIGAI_TOOLS`) remains canonical per `taskdog-3-paths-architecture-canonical-2026-08-31`. Path 3 write-path (`apply_change`) stays out of MCP until v1.2 (gated on 5+ SONHO logs).

### 4.2 Phase 4.1.A vendored-taskdog bridge — **NOT a tool, NOT on master**

The vendored `taskdog-core` (and 4 sibling packages) live on the `loop/phase-4-vendor-taskdog` branch at `vendor/taskdog/`. Per `docs/superpowers/plans/2026-09-10-phase-4-vendor-upstream.md`:
- Phase 4 vendor: SHIPPED on branch (5 pkgs, ~790 files, 106k LOC)
- **Phase 4.1.A bridge** (IKIGAI customizations as thin wrappers): **deferred** — not on master
- **Phase 4.3** (wire upstream `taskdog-mcp` into UnifiedMCPGateway): **deferred**

The vendored tree is private infrastructure for now; it does NOT contribute to the master-branch MCP tool count.

### 4.3 Downstream adapters (`sys_ikigai/gateway/clients/`) — non-tool clients

The 4 client adapters (`tuiboard_adapter`, `taskdog_adapter`, `solverforge_calendar_adapter`, `cli_adapter`) live in `sys_ikigai/gateway/clients/` and are registered via `register_default_adapters` in `sys_ikigai/gateway/downstream.py:18-30`. These are **client-side MCP protocol adapters** that call downstream MCP servers — they are NOT tools exposed by the IKIGAI gateway.

---

## 5. v2 Graph MCP Bridge — **9 wired + 3 mentioned = 12 candidates**

**File:** `src/ikigai/src/agents/v2/mcp_bridge.py`

The v2 LangGraph nodes call MCP tools via this bridge. The bridge wraps each call in a sync `_call()` helper that opens an OTel span `ikigai.bridge.{tool_name}` (distinct from the server-side `ikigai.mcp.{tool_name}`).

| # | Bridge wrapper | `_call("ikigai_X", …)` | Wired in v2 graph? | Source location |
|---|----------------|------------------------|--------------------|-----------------|
| 1 | `ikigai_observe_pav_state` | yes | yes | `mcp_bridge.py:88-90` |
| 2 | `ikigai_score_vectors` | yes | yes | `mcp_bridge.py:93-95` |
| 3 | `ikigai_heuristics` | yes | yes | `mcp_bridge.py:98-100` |
| 4 | `ikigai_balance` | yes | yes | `mcp_bridge.py:103-105` |
| 5 | `ikigai_decompose` | yes | yes | `mcp_bridge.py:108-110` |
| 6 | `ikigai_plan` | yes | yes | `mcp_bridge.py:113-115` |
| 7 | `ikigai_reflect` | yes | yes | `mcp_bridge.py:118-120` |
| 8 | `ikigai_tag_and_persist` | yes | yes | `mcp_bridge.py:123-125` |
| 9 | `ikigai_commit_summary` | yes | yes | `mcp_bridge.py:128-130` |
| 10 | (vault_write) | n/a | NO — infra-level | mentioned in mcp_bridge.py:133-135 comment |
| 11 | (investigation_enqueue) | n/a | NO — infra-level | mentioned in mcp_bridge.py:133-135 comment |
| 12 | (sync_vault) | n/a | NO — infra-level | mentioned in mcp_bridge.py:133-135 comment |

**Critical observation (gap G-1):** The 9 wired bridge wrappers (`ikigai_observe_pav_state`, `ikigai_score_vectors`, `ikigai_heuristics`, `ikigai_balance`, etc.) have **PAV-flavored names** that imply PAV math execution — explicitly contrary to ADR-013 (planner-only). These names are NOT in `server.py`'s `@MCP.tool` registry. The bridge assumes a remote MCP server exposes these tools, but the server has been slimmed down to 11 tools that don't include them. **Phase 8.2 SPEC §2 says only 9 tools are wired; the remote server side may or may not actually serve these names** — this is the core attribution-leak gap to flag.

---

## 6. Provisional Gaps

| # | Gap | Severity | Notes |
|---|-----|----------|-------|
| G-1 | `mcp_bridge.py` defines 9 wrappers with **PAV-flavored names** (`ikigai_observe_pav_state`, `ikigai_score_vectors`, `ikigai_heuristics`, `ikigai_balance`) that are **NOT registered on the MCP gateway server** (server.py has 11 tools, none match). Per ADR-013 planner-only, the agent layer must NOT execute PAV math; these names imply it does. The drift net does NOT pin these bridge names. | **P0 (attribution violated)** | Phase 8.2 SPEC §2 says only 9 tools are wired — names on the server side may have changed during V5-E. Bridge should call the canonical 11 server tools or be renamed to match. |
| G-2 | `IKIGAI_TOOLS = 12` drift net (`test_ikigai_tools_count_is_12`) enforces the LangChain `@tool` registry but does NOT cover the **bridge-wrapper count** (9 wired + 3 mentioned = 12 in `mcp_bridge.py`). Adding a bridge wrapper silently grows the agent surface without tripping drift detection. | **P1 (drift detection missing)** | Recommend adding `test_mcp_bridge_wrapped_tool_count_is_12` (or whatever the agreed count is post-rename) in `test_drift_extended_invariants.py`. |
| G-3 | `taskdog_tools.py` declares a **separate FastMCP instance** (`FastMCP(name="taskdog")`) that is NOT wired into `ikigai-gateway`. The 3 Path-3 tools (`taskdog_read`, `taskdog_list`, `taskdog_supports_field`) are discoverable only if an external MCP client explicitly registers the second instance. This is intentional per the module docstring (avoid ADR-013 cross-talk), but the **de-facto MCP gateway surface is split into 2 instances** without a unified registry. | **P2 (UX/inconsistency)** | Document the multi-instance model in `MCP_GATEWAY.md`; consider a unified `MCPGateway.register(server)` wrapper if Phase 4.3 needs it. |
| G-4 | `taskdog_tools.py` exposes 3 read-only Path-3 tools, but **write-path (`apply_change`) is intentionally deferred to v1.2** (gated on 5+ SONHO logs). The drift net does NOT enforce the read-only contract — a contributor could add a write tool here without tripping a detector. | **P2 (UX/inconsistency)** | Add a targeted test in `test_drift_extended_invariants.py` asserting all `taskdog_*` tools in `taskdog_tools.py` are read-only (return JSON without side-effect enum). |
| G-5 | The vendored taskdog at `vendor/taskdog/` is on `loop/phase-4-vendor-taskdog` (NOT on master). Phase 4.1.A (thin wrappers) and Phase 4.3 (wire into UnifiedMCPGateway) are deferred. **Master branch's MCP gateway does NOT yet benefit from the vendored upstream** — the 10 fork subprocess tools still call the in-tree `taskdog.exe` binary. | **P3 (cosmetic / planning)** | Track in `2026-09-10-phase-4-vendor-upstream.md` future-phases list; not blocking for this review. |

---

## 7. Drift Net Coverage

| Drift test | Coverage |
|------------|----------|
| `test_canonical_scope.py :: test_ikigai_tools_count_is_12` | AST-scan enforces 12 entries in `IKIGAI_TOOLS` (LangChain `@tool` registry). Currently PASSING. |
| `test_canonical_scope.py` (rest) | Enforces no PAE math tools imported in agent/MCP/gateway layers — covers G-1 at the import-symbol level (not at the call-site name level). |
| `test_drift_invariants.py` | UEID 4-part regex + append-only invariants. Does NOT cover MCP gateway surface. |
| `test_drift_extended_invariants.py` | cross_pollution + dual_module_identity. Does NOT cover mcp_bridge wrapper count (G-2) or taskdog_tools.py read-only contract (G-4). |

**Net:** 1 of 5 provisional gaps (none, actually — the drift net covers the 12-entry count but doesn't pin bridge names). G-1 / G-2 / G-4 are NOT drift-covered and recommend targeted follow-up tests in `test_drift_extended_invariants.py`.

---

## 8. Verdict

**Layer 4 MCP gateway is in conformance with the canonical-scope design after V5-E.** The 11 `@MCP.tool` + 6 `@MCP.resource` surface is smaller than Diag 02 (2026-09-04) claimed because V5-E removed 7 doomed PAV-math wrappers — this is intentional and documented in `server.py:1-25`. The drift net (`test_ikigai_tools_count_is_12`) is the canonical enforcement point and is currently PASSING.

**The dominant gap is G-1: `mcp_bridge.py` references 9 PAV-flavored tool names that are not registered on the gateway server.** This is the attribution-leak signal the system-review spec flagged. Bridge wrappers exist to call the gateway; if the gateway doesn't expose those names, the bridge either (a) fails at runtime, (b) silently no-ops via the dict-protocol detector, or (c) calls tools that have been renamed (e.g., `ikigai_score` → `ikigai_observe_pav_state`). Triage required before Phase 8.2 production cutover.

---

## Files Referenced

- `src/ikigai/src/mcp_server/__init__.py`
- `src/ikigai/src/mcp_server/__main__.py`
- `src/ikigai/src/mcp_server/server.py`
- `src/ikigai/src/mcp_server/tools_mesh.py`
- `src/ikigai/src/mcp_server/tools_vault.py`
- `src/ikigai/src/mcp_server/resources.py`
- `src/ikigai/src/mcp_server/handlers.py`
- `src/ikigai/src/mcp_server/investigation_enqueue.py`
- `src/ikigai/src/mcp_server/investigation_status.py`
- `src/ikigai/src/mcp_server/investigation_complete.py`
- `src/ikigai/src/mcp_server/taskdog_tools.py`
- `src/ikigai/src/mcp_server/tracing.py`
- `src/ikigai/src/agents/tools.py` (`IKIGAI_TOOLS`)
- `src/ikigai/src/agents/tools_sf.py` (2 solverforge tools)
- `src/ikigai/src/agents/tools_taskdog.py` (4 taskdog Path-1 tools)
- `src/ikigai/src/agents/tools_tuiboard.py` (4 tuiboard tools)
- `src/ikigai/src/agents/ikigai_read_strategics.py`
- `src/ikigai/src/agents/ikigai_read_vault.py`
- `src/ikigai/src/agents/v2/mcp_bridge.py` (9 wired + 3 mentioned = 12)
- `sys_ikigai/gateway/downstream.py` (`register_default_adapters`)
- `sys_ikigai/gateway/clients/{taskdog,tuiboard,solverforge_calendar,cli}.py` (4 client adapters)
- `src/ikigai/tests/test_canonical_scope.py :: test_ikigai_tools_count_is_12` (drift net, PASSING)
- `docs/superpowers/specs/2026-09-04-diag-02-mesh-taskdog-mcp.md` (Diag 02 baseline — 15 tools)
- `docs/superpowers/plans/2026-09-10-phase-4-vendor-upstream.md` (Phase 4.1.A deferred)
