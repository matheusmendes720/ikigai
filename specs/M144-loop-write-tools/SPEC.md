---
name: M144-loop-write-tools
description: 6 write-side IKIGAI MCP wrappers in .claude/loop/mcp_bridge.py — vault_read/write, ikigai_write_tasks, investigation_*.
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

# M144 — Loop-side Write Tools

> **What:** Add 6 write-side IKIGAI MCP wrappers to
> `.claude/loop/mcp_bridge.py` so loop sub-agents can perform writes that
> M142 deferred to keep the read-only invariant clean.
> **Why:** M142 shipped 6 read-only wrappers (acceptance + ADR-013). Workers
> that need to write today fall back to `python -m life.cli ...` (canonical
> path) or escalate to v2 graph (which has its own audit log). That works,
> but it forces a context switch every time a worker wants to:
> - read a vault file (`vault_read`)
> - enqueue / poll / complete an investigation (operator queue)
> - write a task to `data/tasks.jsonl` (Deep Agent output)
> - append a vault note (`vault_write` — only path per ADR-012)

Without these wrappers, the loop layer is **half a citizen** — workers can
inspect IKIGAI state but can't mutate it through the bridge. M144 completes
the surface.

## Current state (verified 2026-09-26)

- `.claude/loop/mcp_bridge.py` (195 LOC): 6 read-only wrappers
  (`ikigai_decompose`, `ikigai_read_tasks`, `ikigai_mesh_show`,
  `ikigai_health`, `ikigai_task_create` with `dry_run=True`, `taskdog_list`).
  Forbidden names enforced by `test_forbidden_tools_not_importable`.
- v2 mcp_bridge (109 LOC): only `ikigai_decompose`. Loop bridge is bigger
  by design (covers more tools; loop agents need broader surface).
- `src/ikigai/src/mcp_server/server.py` (live registry):
  - 8 IKIGAI tools (already bridged: 5 fully + 1 with `dry_run=True` + 2 write ones)
  - 3 investigation tools (`investigation_enqueue`, `investigation_status`,
    `investigation_complete`)
  - 3 taskdog tools (`taskdog_read`, `taskdog_list`, `taskdog_supports_field`)
  - 8 PAV-math stubs (FORBIDDEN per ADR-013; not bridged)
- ADR-013 planner-only boundary: writes are fine through this bridge IF
  the worker explicitly opts in (no `dry_run=True` defaults on writes).
  Audit-log writes (vault) live here; the bridge is the canonical loop-side
  writer. v2 graph still owns its own audit log; loop bridge is separate.

## Scope

**In scope** (M144):

1. Add 6 new sync wrappers to `.claude/loop/mcp_bridge.py`:
   - `vault_read(vault_path: str)` — read-side, mirrors server.py:148-159
   - `ikigai_write_tasks(tasks: list[dict[str, Any]])` — write to
     `data/tasks.jsonl` (Deep Agent output channel)
   - `vault_write(vault_path: str, frontmatter: dict[str, Any], body: str)`
     — canonical vault writer (ADR-012)
   - `investigation_enqueue(inq_id: str, source: str, payload: str,
     tags: list[str] | None = None, actor: str = "loop-agent")` — actor
     defaults to `loop-agent` (distinct from v2 graph's default `agent`)
   - `investigation_status(inq_id: str | None = None)` — read-side
   - `investigation_complete(inq_id: str, final_status: str = "resolved",
     actor: str = "loop-agent", inq_ueid: str | None = None)` — terminal
2. Update `test_m142_mcp_bridge.py::test_drift_count_of_wrapped_tools_is_6`
   → split into:
   - `test_drift_count_of_read_only_wrappers_is_6` (M142 invariant)
   - `test_drift_count_of_write_wrappers_is_6` (M144 invariant)
   - Total surface = 12 wrappers (M142: 6 read-only + M144: 6 write)
3. Remove `vault_write` / `vault_read` / `ikigai_write_tasks` /
   `investigation_*` from `FORBIDDEN_NAMES` set in the M142 test — they
   are now legitimate bridge surface.
4. Add `tests/test_m144_mcp_bridge_write_tools.py` (≥8 tests):
   - Each of 6 wrappers calls `_call()` with the right tool name + args
   - Actor default for `investigation_*` is `"loop-agent"`
   - `investigation_complete` default `final_status="resolved"`
   - `vault_write` requires all 3 kwargs (no defaults)
   - `vault_read` is the only one without any required defaults beyond
     `vault_path`
   - Forbidden 8 PAV-math tools still absent
5. All M142 + M143 tests still PASS (regression sweep).
6. Update `.claude/agents/loop/orchestrator.md` Programmatic Bridge
   subsection: surface goes from 6 → 12, add a write-side bullet list.

**Out of scope** (deferred):

- `taskdog_read` + `taskdog_supports_field` (M145 — taskdog rest + resources)
- 6 resources (M145)
- Production binding of `_server` to FastMCP client (M146)
- `init_tracing()` call at loop startup (M146 — M143 spans work but
  only in tests; real export needs `init_tracing()`)

## Acceptance criteria

- [ ] `.claude/loop/mcp_bridge.py` exposes **12** sync wrappers (6 read + 6 write).
- [ ] All wrappers delegate to `_call(tool_name, args)`.
- [ ] `vault_read(vault_path)` — passes `{"vault_path": vault_path}`.
- [ ] `ikigai_write_tasks(tasks)` — passes `{"tasks": tasks}`.
- [ ] `vault_write(vault_path, frontmatter, body)` — passes all 3 args,
      no defaults (every kwarg required).
- [ ] `investigation_enqueue(inq_id, source, payload, tags=None, actor="loop-agent")`
      — actor default `"loop-agent"` (distinct from v2 `"agent"`).
- [ ] `investigation_status(inq_id=None)` — read-side.
- [ ] `investigation_complete(inq_id, final_status="resolved", actor="loop-agent", inq_ueid=None)`.
- [ ] `tests/test_m144_mcp_bridge_write_tools.py` exists with ≥8 tests, all PASS.
- [ ] `tests/test_m142_mcp_bridge.py` updated: drift test split into
      read-only (6) + write (6) subsets; forbidden set reduced to
      PAV-math (8 names) only.
- [ ] All M142 (14) + M143 (13) tests still PASS — no regression.
- [ ] `.claude/loop/mcp_bridge.py` ≤ 320 LOC (was 195 + ~115 new = ~310).
- [ ] `.claude/agents/loop/orchestrator.md` Programmatic Bridge subsection
      lists all 12 wrappers + 6 NOT-exposed-PAV-math tools.
- [ ] No changes to `server.py`, v2 `mcp_bridge.py`, or `.mcp.json`.

## Design choices

- **`actor="loop-agent"` default** for investigation tools: makes loop
  writes distinguishable from v2-graph writes in the investigation queue
  audit log. v2 graph uses `"agent"`; loop uses `"loop-agent"`; operator
  TUI uses whatever the operator types. Trivial to grep by source.
- **`vault_write` has NO defaults**: every arg is required. This is the
  canonical vault writer; a typo or missing field should fail loud, not
  silently write a half-baked note. Mirrors `vault_write` server-side
  signature exactly.
- **`vault_read` is in M144, not M142**: deferred to M144 because the
  server-side `vault_read` and `vault_write` share security model (path
  validation, atomic writes). Bundling them in one milestone keeps the
  audit-log invariants under one review.
- **`investigation_status` is the only read-side of the 3 investigation
  tools**: `enqueue` and `complete` are write-side. Bundled together
  because the operator-queue use case wants all 3 (worker enqueues,
  later worker checks status, terminal worker completes).
- **Drift detector split into read-only + write subsets**: gives future
  contributors a cleaner migration story. If M147 adds another read
  tool, only the read subset updates. If M148 adds a write tool, only
  the write subset updates.

## Honest scope

- ✅ 12 wrappers exposed (6 read + 6 write) + drift test split
- ✅ Tests cover all 6 new wrappers + actor defaults + required kwargs
- ✅ Orchestrator prompt updated (additive)
- ⚠️ **Production binding still mocked**: `vault_write` calls
  `_server.call("vault_write", {...})` which today is a MagicMock in
  tests. Production needs M146 binding. Until then, the bridge is
  usable in tests but not in production.
- ⚠️ **No audit-log schema for investigation_***: when a worker enqueues,
  the audit log records `actor="loop-agent"`. Existing operator-TUI may
  not filter by this yet (out of scope; M146 follow-up if needed).
- ⚠️ **Worker prompts must guard `vault_write` use**: the orchestrator
  prompt subsection should warn workers that vault_write appends to
  `vault/.vault_events.jsonl` (append-only, no rollback). Same Phase 8.2
  §6 invariant as before.

## Lessons from predecessors

- **M11/M12 PAV-math drift (2026-09-07)**: bridge/server drifted silently.
  M142 pinned alignment via `test_drift_count_of_wrapped_tools_is_6`.
  M144 splits this into read/write subsets — finer-grained drift
  detection, easier migration story.
- **M142 itself**: showed the right pattern for adding wrappers (one
  trivial sync wrapper per server tool, no logic). M144 follows.
- **Phase 8.2 vault_write security model**: VaultLock, atomic writes,
  path validation. M144 wraps; the actual security model lives in
  `src/ikigai/src/mcp_server/tools_vault.py`. Worker that calls
  `vault_write` inherits the security model via the bridge.
- **M143 OTel plumbing**: every new wrapper goes through `_call(...)`
  which is already span-wrapped. M144 inherits span emission for free.

## Followups (out of scope)

- **M145** — taskdog fork tools beyond `taskdog_list` + 6 resources.
- **M146** — production binding of `_server` + `init_tracing()` at loop
  startup. Cost: $0.50.

## Cost estimate

- **Implementation**: 1 sub-agent, sonnet-4-5, ~25 min, **$0.10**
- **Tests**: 1 sub-agent, sonnet-4-5, ~20 min, **$0.08**
- **Drift-test split**: 1 sub-agent, sonnet-4-5, ~10 min, **$0.04**
- **Orchestrator prompt update**: 1 sub-agent, haiku-4-5, ~5 min, **$0.02**
- **Review + closeout**: orchestrator self-verify, **$0.05**
- **Total**: **$0.29** (round up to $0.40 for retry buffer)

## Atomic breakdown (for orchestrator)

- **T-144.1** — add 6 new wrappers to `.claude/loop/mcp_bridge.py`
- **T-144.2** — split M142 drift test into read + write subsets
- **T-144.3** — create `tests/test_m144_mcp_bridge_write_tools.py` (≥8 tests)
- **T-144.4** — update orchestrator prompt Programmatic Bridge subsection
- **T-144.5** — verify regression sweep (M142 14 + M143 13 + M144 ≥8 + contracts/integration)
- **T-144.6** — append `progress.md` M144 entry, atomic commit + push
