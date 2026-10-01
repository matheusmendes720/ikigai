---
name: M142-agent-mcp-wiring
description: Loop-side MCP bridge for orchestrator/worker/verifier — READ-ONLY slice (6 IKIGAI tools). Writes deferred to M144.
status: PENDING
owner: loop-orchestrator
created: 2026-09-26
constitution_refs:
  - composition_over_inheritance
  - tests_are_the_contract
  - reversibility_over_cleverness
  - state_on_disk_not_conversation
estimated_cost_usd: 0.30
---

# M142 — Loop-side MCP Bridge (READ-ONLY slice)

> **Scope revision (2026-09-26):** Ship **6 read-only IKIGAI tools** first.
> `ikigai_write_tasks`, `vault_write`, and the 3 `investigation_*` tools
> are deferred to M144 to preserve the planner-only boundary (ADR-013) and
> keep audit-log writes under v2-graph / operator-TUI control. M142 stays
> additive, testable, and reversible — workers get read access to the agent
> layer without gaining write surface.

## Current state (verified 2026-09-26)

- v2 graph side: `src/ikigai/src/agents/v2/mcp_bridge.py` (109 LOC) exposes 1
  sync wrapper (`ikigai_decompose`) + `_call()` helper. Production binds
  `_server` to FastMCP client; tests monkeypatch `_server` to `FakeMcpServer`.
  Phase 8.2 SHIPPED 2026-09-08 covers the v2 side; canonical_scope drift 33/33
  preserved.
- Loop side: zero programmatic MCP wiring. The orchestrator prompt
  (`.claude/agents/loop/orchestrator.md:150-180`) lists the 14 tools + 6
  resources as **LLM-callable** (the model emits JSON-RPC text), but there is
  no Python module a sub-agent can `import` to call them safely.
- `.mcp.json` registers `ikigai` (stdio) + `taskdog` (stdio) — both are
  runtime-registered for Claude Code / MCP-aware clients, not for the loop's
  sub-agent invocations.
- Helpers: `.claude/helpers/` has only `helpers.manifest.json`. No MCP client.

## Scope

**In scope** (M142, READ-ONLY slice):

1. New module `.claude/loop/mcp_bridge.py` (~80 LOC) — port `mcp_bridge.py`
   pattern to the loop side. Same architecture: module-level `_server` handle,
   sync wrappers around async MCP calls. OTel span emission deferred to M143
   (depends on `.claude/loop/observability/` not yet existing).
2. Wrap the **6 read-only IKIGAI tools**: `ikigai_decompose`,
   `ikigai_read_tasks`, `ikigai_mesh_show`, `ikigai_health`,
   `ikigai_task_create` (read-shape via safe default args; planner-side
   helper), and `taskdog_list` (read-only fork).
   **No `vault_write`. No `ikigai_write_tasks`. No `investigation_*`.**
3. Pin **bridge ↔ server alignment** with a small drift test
   `tests/test_m142_mcp_bridge_alignment.py` (counts wrapped tools vs
   `server.py` `@MCP.tool` registry + asserts forbidden tools are absent).
4. Update `.claude/agents/loop/orchestrator.md` "IKIGAI MCP Tool Surface"
   section to point workers at the new bridge import path.

**Out of scope** (deferred to M144+):

- `ikigai_write_tasks`, `vault_write` — write surface, keep under v2-graph /
  operator-TUI control per ADR-012/013. (M144)
- 3 `investigation_*` tools — operator/admin surface, not worker hot path.
  (M144)
- Taskdog fork tools beyond `taskdog_list` + 6 resources — taskdog read path
  already exists via mesh layer (M134); resources are not a worker hot path.
  (M145)
- Production binding of `_server` to FastMCP client (same deferral as
  Phase 8.2 — tests use `FakeMcpServer`, production binding is M146).
- OTel span emission (M143).
- `langgraph_entry.py`-style graph integration (separate workstream).

## Acceptance criteria

- [ ] `.claude/loop/mcp_bridge.py` exists, ≤150 LOC, exposes **6** sync
      wrappers: `ikigai_decompose`, `ikigai_read_tasks`, `ikigai_mesh_show`,
      `ikigai_health`, `ikigai_task_create`, `taskdog_list`.
- [ ] All 6 wrappers delegate to a single `_call(tool_name, args)` helper
      that raises `RuntimeError` when `_server` is unbound (matches
      `mcp_bridge.py` error contract).
- [ ] `tests/test_m142_mcp_bridge_alignment.py` exists with **≥6 tests**:
      - `_call` raises when `_server is None`
      - `_call` propagates exception from `_server`
      - FakeMcpServer returns expected dict for each of the 6 wrappers
      - Drift detector: count of wrapped tools == 6
      - Drift detector: `vault_write` / `ikigai_write_tasks` /
        `investigation_*` are NOT importable from the module
        (greps `dir()` to prove absence)
- [ ] `.claude/agents/loop/orchestrator.md` IKIGAI section adds a
      "Programmatic Bridge (M142 — read-only)" subsection pointing at
      `.claude/loop/mcp_bridge.py` with a one-line import + call example.
      Existing 14-tool table preserved (additive; M144 will add a separate
      "M144 write-side" subsection).
- [ ] Root `pytest tests/` still PASS (no regression).
- [ ] `pytest tests/test_m142_mcp_bridge_alignment.py` **≥6/6 PASS**.
- [ ] Drift detector wired: if a future commit adds an `@MCP.tool` to
      `server.py` without wrapping it here, the drift test fails with
      a clear "wrapped=N, server=M" message.
- [ ] No changes to `server.py`, v2 `mcp_bridge.py`, or `.mcp.json` — loop
      bridge is additive, lives at `.claude/loop/mcp_bridge.py`.

## Design choices

- **6 tools, read-only**: `ikigai_decompose`, `ikigai_read_tasks`,
  `ikigai_mesh_show`, `ikigai_health`, `ikigai_task_create` (read-shape via
  default args), and `taskdog_list` (read-only fork). Total: 6.
  Worker writes go through CLI (`python -m life.cli ...`) or v2 graph.
- **Same `FakeMcpServer` pattern** as v2 mcp_bridge.py: tests monkeypatch
  `_server` to a `MagicMock(spec=MCPClient)`. Production binding is M146.
- **No OTel in M142**: keeps the surface minimal and easy to review. OTel
  tracing on loop MCP is M143 (depends on `.claude/loop/observability/` not
  yet existing).
- **Additive only**: no edits to existing files except the orchestrator prompt
  subsection. Per constitution §2, every change must be reversible — additive
  edits to a 200-line prompt section are easy to `git revert`.
- **Separate module**: `.claude/loop/mcp_bridge.py` is NOT a copy of v2's
  `mcp_bridge.py`. It lives at the loop layer; v2 lives at the agent layer.
  Sharing `_call()` shape by convention, not by import (avoids cross-layer
  coupling that would break if v2 mcp_bridge evolves).

## Honest scope

- ✅ Bridge module exists with 6 read-only wrapped tools + drift detector
- ✅ Tests cover happy path + unbound-server + drift + write-tool absence
- ✅ Orchestrator prompt points at bridge (additive subsection)
- ⚠️ **No production binding** of `_server` to real FastMCP client — mirrors
  Phase 8.2 status. Tests use FakeMcpServer; running `loop-tick.sh` won't
  actually invoke MCP today (workers still use Bash + file tools).
- ⚠️ **No OTel**: span emission deferred to M143.
- ⚠️ **No write tools**: `vault_write`, `ikigai_write_tasks`,
  `investigation_*` deferred to M144. Workers needing to write go through
  `python -m life.cli ...` or `v2 graph invoke` paths, NOT through this bridge.

## Lessons from predecessors

- **M5**: orchestrator-prompt-only layer for IKIGAI tools — worked because
  tools are stable. M142 ports this idea to *programmatic* invocation, not
  just prompt documentation.
- **M11 / M12 PAV-math drift**: bridge and server drifted silently because
  no alignment test existed. M142 pins alignment from day one (acceptance #4).
- **Phase 8.2 (2026-09-08)**: proved the `_server` monkeypatch pattern works
  with `FakeMcpServer` for unit tests + the production binding gap is
  acceptable when deferred explicitly. M142 inherits this pattern.

## Followups (out of scope)

- **M143** — `.claude/loop/observability/` OTel wiring + apply spans to
  `mcp_bridge.py`. Cost: $0.10. Depends on this milestone.
- **M144** — wire `ikigai_write_tasks`, `vault_write`, `investigation_*`
  tools into the bridge. Cost: $0.20. Separate milestone so write surface
  is reviewed under its own constitutional gate (ADR-013 planner-only).
- **M145** — wire taskdog fork tools (beyond `taskdog_list`) + 6 resources.
- **M146** — production binding of `_server` to FastMCP client. Same
  fake→real pattern as Phase 8.2 followup. Cost: $0.50 + integration test.

## Cost estimate

- **Implementation**: 1 sub-agent, sonnet-4-5, ~20 min, **$0.08**
- **Tests**: 1 sub-agent, sonnet-4-5, ~15 min, **$0.05**
- **Review + closeout**: orchestrator self-verify, **$0.05**
- **Total**: **$0.18** (round up to $0.30 for retry buffer)

## Atomic breakdown (for orchestrator)

- **T-142.1** — create `.claude/loop/mcp_bridge.py` (6 wrappers + `_call`)
- **T-142.2** — create `tests/test_m142_mcp_bridge_alignment.py` (≥6 tests)
- **T-142.3** — update `.claude/agents/loop/orchestrator.md` IKIGAI section
- **T-142.4** — verify root `pytest tests/` PASS, append to progress.md,
  atomic commit + push
