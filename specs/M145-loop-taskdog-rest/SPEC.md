---
name: M145-loop-taskdog-rest
description: Add taskdog_read + taskdog_supports_field + 6 MCP resource accessors to .claude/loop/mcp_bridge.py
status: PENDING
owner: loop-orchestrator
created: 2026-09-26
constitution_refs:
  - composition_over_inheritance
  - tests_are_the_contract
  - reversibility_over_cleverness
  - state_on_disk_not_conversation
estimated_cost_usd: 0.40
---

# M145 — Loop-side Taskdog Rest + Resources

> **What:** Complete the loop bridge by adding the remaining 2 taskdog fork
> tools (`taskdog_read`, `taskdog_supports_field`) plus 6 MCP resource
> accessors (`ueid://`, `queue://pending`, `queue://events/{event_id}`,
> `health://gateway`, `plans://cycles`, `plans://cycles/{cycle_id}`).
> **Why:** M142 brought 6 read-only tools. M144 added 6 write tools.
> M145 fills the remaining 2 taskdog fork tools and exposes 6 MCP resources
> via the bridge so workers don't have to hand-roll the FastMCP resource
> protocol from inside a worktree. M146 then closes the chain with
> production `_server` binding + `init_tracing()`.

## Current state (verified 2026-09-26)

- `.claude/loop/mcp_bridge.py` (312 LOC): 12 wrappers (6 read + 6 write).
- Server registry (`src/ikigai/src/mcp_server/server.py`):
  - 8 IKIGAI tools (all bridged: 5 fully + 1 with `dry_run=True` + 2 write ones)
  - 3 investigation tools (all bridged)
  - 2 taskdog tools (`taskdog_read`, `taskdog_supports_field`) — **NOT bridged**
  - 1 taskdog tool (`taskdog_list`) — bridged in M142
  - 8 PAV-math stubs — FORBIDDEN per ADR-013
- Server resources (`src/ikigai/src/mcp_server/server.py` + `resources.py`):
  - 6 MCP resources registered via `@MCP.resource(...)` decorator — **NOT
    accessible via the bridge today**. Workers would need to call
    `_server.read_resource(uri)` directly (which the bridge doesn't expose).

## Scope

**In scope** (M145):

1. Add 2 new sync wrappers to `.claude/loop/mcp_bridge.py`:
   - `taskdog_read(ueid: str, db_path: str | None = None)` — get a taskdog
     task slice by UEID. `db_path` is the optional override for tests.
   - `taskdog_supports_field(field_name: str)` — capability check for a
     taskdog field name.
2. Add 6 resource accessors (helper functions, not wrappers) to the same
   module. Resources in FastMCP are read via `read_resource(uri)` not
   `_call(tool_name, args)`, so they get a separate helper:
   - `read_ueid_resource(ueid: str) -> dict[str, Any]`
   - `read_queue_pending_resource() -> dict[str, Any]`
   - `read_queue_event_resource(event_id: str) -> dict[str, Any]`
   - `read_health_resource() -> dict[str, Any]`
   - `read_plans_cycles_resource() -> dict[str, Any]`
   - `read_plans_cycle_resource(cycle_id: str) -> dict[str, Any]`
   Each delegates to `_server.read_resource(uri)`.
3. Update `test_drift_count_of_write_wrappers_is_6` → `is_8` (M145 adds
   2 taskdog tools, total write subset = 6 + 2 = 8 wrappers; total
   bridge surface = 14 wrappers + 6 resource accessors).
   Actually — taskdog_read + taskdog_supports_field are read-side. So
   split is: read subset = 6 (M142) + 2 (M145 taskdog) = 8 read;
   write subset = 6 (M144) unchanged. Total = 14 wrappers.
4. Add `RESOURCE_URIS` module-level dict mapping short names to URIs
   (`{"ueid": "ueid://{ueid}", "queue_pending": "queue://pending", ...}`)
   so the resource accessors and tests stay in sync.
5. Add `tests/test_m145_mcp_bridge_taskdog_rest.py` (≥10 tests):
   - `taskdog_read` and `taskdog_supports_field` delegate to `_call` with
     correct args
   - `taskdog_read` accepts `db_path=None` (default omitted from payload)
   - Each of 6 resource accessors calls `_server.read_resource` with
     correct URI
   - `RESOURCE_URIS` dict has exactly 6 entries with expected URIs
   - `taskdog_read` and `taskdog_supports_field` are in `dir(bridge)`
   - Total wrapper count is now 14 (8 read + 6 write)
   - Resource accessors are functions, not methods on the module
6. All M142 (15) + M143 (14) + M144 (21) tests still PASS.
7. Update orchestrator prompt Programmatic Bridge subsection: surface
   goes from 12 → 14 wrappers + 6 resource accessors; remove the "deferred
   to M145+" line about taskdog_rest + resources.

**Out of scope** (deferred to M146):

- Production binding of `_server` to FastMCP client
- `init_tracing()` call at loop startup
- Resource accessors don't try to parse the FastMCP response format —
  they return whatever `_server.read_resource(...)` returns. Parsing
  belongs in M146 (where the binding layer exposes a richer surface).

## Acceptance criteria

- [ ] `.claude/loop/mcp_bridge.py` exposes **14** sync wrappers (8 read + 6 write).
- [ ] 2 new wrappers added: `taskdog_read(ueid, db_path=None)`,
      `taskdog_supports_field(field_name)`.
- [ ] 6 resource accessors added: `read_ueid_resource(ueid)`,
      `read_queue_pending_resource()`, `read_queue_event_resource(event_id)`,
      `read_health_resource()`, `read_plans_cycles_resource()`,
      `read_plans_cycle_resource(cycle_id)`.
- [ ] Module-level `RESOURCE_URIS` dict with 6 entries mapping short name → URI.
- [ ] `RESOURCE_URIS["ueid"]` is `"ueid://{ueid}"` (placeholder for format()).
- [ ] All wrappers still delegate to `_call(tool_name, args)`.
- [ ] All resource accessors delegate to `_server.read_resource(uri)`.
- [ ] `tests/test_m145_mcp_bridge_taskdog_rest.py` exists with ≥10 tests, all PASS.
- [ ] M142 drift tests updated: total wrappers = 14 (was 12).
- [ ] All M142 (15) + M143 (14) + M144 (21) tests still PASS — no regression.
- [ ] `.claude/loop/mcp_bridge.py` ≤ 420 LOC (was 312 + ~95 new = ~405).
- [ ] Orchestrator prompt Programmatic Bridge subsection lists all 14 wrappers
      + 6 resource accessors; deferred-to-M145 list removed.
- [ ] No changes to `server.py`, v2 `mcp_bridge.py`, or `.mcp.json`.

## Design choices

- **Resource accessors as standalone functions, not method-like `_call` wrappers**:
  FastMCP resources use `read_resource(uri)`, not `call(tool_name, args)`.
  Bundling them in the same module keeps the bridge cohesive (one import
  gives workers everything) without pretending they're tool calls.
- **`RESOURCE_URIS` module-level dict**: prevents URI drift between
  accessors and tests. Format strings use `{placeholder}` (not f-strings)
  so callers can `RESOURCE_URIS["ueid"].format(ueid=...)` cleanly.
- **Total 14 wrappers + 6 accessors**: clear separation between tool-call
  wrappers (counted in drift tests) and resource accessors (separate
  count via `RESOURCE_URIS` dict length).
- **`taskdog_read` `db_path` optional**: matches server signature. Default
  omitted from payload (`if db_path is not None: args["db_path"] = db_path`).
  Same pattern as `investigation_enqueue`'s `tags` omission (M144).

## Honest scope

- ✅ 2 taskdog fork tools + 6 resource accessors + drift test split
- ✅ Tests cover all 8 new surfaces + drift tests + resource URI dict
- ✅ Orchestrator prompt updated (additive)
- ⚠️ **Resource accessors return raw `_server.read_resource(uri)` output**:
  parsing FastMCP's resource envelope (status code + mime type + body)
  belongs to M146. For M145, the helper just delegates. Tests assert
  the URI passed, not the response shape.
- ⚠️ **Production binding still mocked**: same as M144. M146 closes.
- ⚠️ **No integration test against real FastMCP server**: tests use
  MagicMock for `_server.read_resource`. Real binding lives in M146.

## Lessons from predecessors

- **M142 + M144 wrapper pattern**: one trivial sync wrapper per server
  tool, no logic. M145 follows for `taskdog_read` and `taskdog_supports_field`.
- **M143 OTel plumbing**: every `_call(...)` is span-wrapped. M145's
  taskdog wrappers inherit span emission for free. Resource accessors
  do NOT go through `_call` — they go through `_server.read_resource`
  directly. If we want span emission for resources too, M146 should
  add a separate `_read_resource(uri)` helper that wraps `read_resource`
  in a span. M145 deliberately doesn't (out of scope; lessons M143's
  own deferral pattern).
- **M144 omission pattern**: `tags=None` → omit from args dict. M145
  applies same to `db_path=None` for `taskdog_read`.
- **Phase 8.2 wrapper convention**: `*` keyword-only signature. M145
  follows for new wrappers.

## Followups (out of scope)

- **M146** — production binding of `_server` to FastMCP client +
  `init_tracing()` at loop startup + optional resource-envelope parsing.
  Cost: $0.50.

## Cost estimate

- **Implementation**: 1 sub-agent, sonnet-4-5, ~20 min, **$0.08**
- **Tests**: 1 sub-agent, sonnet-4-5, ~15 min, **$0.05**
- **Drift-test update + orchestrator prompt**: 1 sub-agent, haiku-4-5,
  ~10 min, **$0.02**
- **Review + closeout**: orchestrator self-verify, **$0.05**
- **Total**: **$0.20** (round up to $0.40 for retry buffer)

## Atomic breakdown (for orchestrator)

- **T-145.1** — add 2 taskdog wrappers + 6 resource accessors + RESOURCE_URIS dict
- **T-145.2** — update M142 drift tests for 14-wrapper total
- **T-145.3** — create `tests/test_m145_mcp_bridge_taskdog_rest.py` (≥10 tests)
- **T-145.4** — update orchestrator prompt (remove deferred list, add resource accessors)
- **T-145.5** — verify regression sweep (M142+M143+M144+M145 + contracts/integration)
- **T-145.6** — append `progress.md` M145 entry, atomic commit + push
