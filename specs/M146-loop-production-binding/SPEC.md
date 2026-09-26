---
name: M146-loop-production-binding
description: Production binding for .claude/loop/mcp_bridge.py — start FastMCP stdio client + init_tracing() at loop startup. Closes the bridge chain.
status: PENDING
owner: loop-orchestrator
created: 2026-09-26
constitution_refs:
  - composition_over_inheritance
  - tests_are_the_contract
  - reversibility_over_cleverness
  - state_on_disk_not_conversation
estimated_cost_usd: 0.50
---

# M146 — Loop-side Production Binding

> **What:** Make the loop MCP bridge work in production. Start a FastMCP
> stdio client, point `_server` at it, and call `init_tracing()` at loop
> startup so M143 spans actually export to LangSmith/Langfuse. Also parse
> the FastMCP resource envelope so the 6 M145 resource accessors return
> useful data (not raw server payload).
> **Why:** M142-M145 shipped 14 wrappers + 6 resource accessors all bound
> to `MagicMock`. Without production binding, running `loop-tick.sh` does
> not invoke any real MCP tools. M146 closes the loop-bridge chain and
> makes the entire M142-M145 work actually useful.

## Current state (verified 2026-09-26)

- `.claude/loop/mcp_bridge.py` (405 LOC, 14 wrappers + 6 accessors):
  `_server = None` at module level. Tests monkeypatch to MagicMock.
  M143 spans emit to whatever OTel SDK is initialized — in tests, the
  test fixture installs an in-memory exporter.
- v2 `src/ikigai/src/agents/v2/mcp_bridge.py` (109 LOC): same pattern,
  also `_server = None`, monkeypatched in tests. Production binding
  ALSO deferred (see Phase 8.2 SPEC §3).
- `src/ikigai/src/mcp_server/server.py`: `MCP = FastMCP("ikigai-gateway")`,
  `main()` calls `MCP.run_stdio_async()`. Started by `ikigai.bat mcp` /
  `python -m mcp_server`.
- `.mcp.json` (Claude Code runtime): already configures stdio client
  pointing at the same ikigai server. We're porting that pattern to Python.
- `src/ikigai/src/observability/otel_init.py:72`: `init_tracing()` —
  idempotent, no-op if called twice, each exporter only enabled when
  its env credentials are present (works local-only without creds).
- `loop-tick.sh` (root `.claude/loop/`): the entry point. Today does
  NOT call `init_tracing()` or start any MCP client. Per-tick invocation.

## Scope

**In scope** (M146):

1. **New module `.claude/loop/mcp_runtime.py`** (~150 LOC):
   - `bind_server() -> None` — starts a stdio MCP client (subprocess
     running `python -u -m mcp_server` per `.mcp.json` config), wraps
     it in a `ClientSession`, exposes a synchronous `.call(tool, args)`
     and `.read_resource(uri)` interface, and assigns the wrapper to
     `mcp_bridge._server` (mutates the module attribute).
   - `init_observability() -> None` — calls `init_tracing()` from
     `src.ikigai.src.observability.otel_init`. Idempotent.
   - `unbind_server() -> None` — clean shutdown for graceful exit
     (terminates subprocess, awaits pending reads, sets `_server = None`).
2. **Resource envelope parsing** in `mcp_bridge.py` — the 6 M145
   resource accessors currently return raw server payload. Add a small
   helper `_parse_resource_envelope(payload)` that handles the FastMCP
   shape (list of `(uri, mime_type, body)` tuples or single blob).
   Falls back to raw payload if envelope shape unrecognized.
3. **Loop startup integration** — `.claude/loop/loop-tick.sh` calls
   `python -c "from .claude.loop.mcp_runtime import bind_server, init_observability; init_observability(); bind_server()"`
   before the orchestrator prompt runs. Mirrors how `.mcp.json` is
   pre-loaded by Claude Code at session start.
4. **`tests/test_m146_production_binding.py`** (≥8 tests):
   - `init_observability()` is idempotent (call twice → no error)
   - `init_observability()` is safe without LangSmith/Langfuse creds
     (env vars unset → no exporter added, but call succeeds)
   - `bind_server()` raises a clear error if subprocess can't start
     (Python not on PATH, mcp_server missing, etc.)
   - `unbind_server()` sets `_server = None` after a successful bind
   - `_parse_resource_envelope()` handles the 3 expected shapes:
     single blob, list of (uri, mime, body), list of ReadResourceContents
   - End-to-end smoke (xfail if `python -m mcp_server` not reachable
     on test machine): bind → call `ikigai_health()` → returns dict.
5. **All M142-M145 tests still PASS** (regression sweep).
6. **Update orchestrator prompt** Programmatic Bridge subsection: mark
   M146 as "SHIPPED", point workers at the production bind helper.

**Out of scope** (deferred to M147+):

- **v2 mcp_bridge production binding** — same pattern as M146, but for
  the v2 graph layer. Out of scope per M146 §Lessons (avoid cross-layer
  coupling; v2 should have its own milestone M147 if/when needed).
- **Real connection pooling / multi-server fanout** — M146 binds one
  client per loop-tick. Pooling is optimization, not correctness.
- **OAuth / auth flow** — IKIGAI server has no auth today; stdio
  transport is process-local. Adding auth is a separate concern.
- **Persistent MCP connection across ticks** — each loop-tick.sh
  invocation is a new Python process. If persistent connection is
  needed, that becomes a daemon process (M148+).
- **Resource envelope parsing for v2 / other clients** — M146 only
  handles the FastMCP stdio client shape.

## Acceptance criteria

- [ ] `.claude/loop/mcp_runtime.py` exists, ≤320 LOC, exports
      `bind_server`, `unbind_server`, `init_observability`.
- [ ] `bind_server()` starts `python -u -m mcp_server` as subprocess,
      wraps in `ClientSession` over stdio, builds a sync adapter that
      exposes `.call(tool, args)` and `.read_resource(uri)`, assigns
      to `mcp_bridge._server`.
- [ ] `init_observability()` calls `init_tracing()` exactly once per
      process (idempotent flag inside `otel_init.py:36`).
- [ ] `unbind_server()` terminates subprocess, awaits cleanup, sets
      `_server = None`.
- [ ] `_parse_resource_envelope(payload)` in `mcp_bridge.py` returns
      a `dict[str, Any]` (not raw list/blob) for the 3 expected shapes.
- [ ] All 6 M145 resource accessors go through `_parse_resource_envelope`.
- [ ] `.claude/loop/loop-tick.sh` invokes `init_observability()` +
      `bind_server()` before orchestrator prompt (one new line +
      one-line import).
- [ ] `tests/test_m146_production_binding.py` exists with ≥8 tests, all PASS.
- [ ] All M142 (15) + M143 (14) + M144 (21) + M145 (19) tests still PASS.
- [ ] End-to-end smoke test (`bind → call ikigai_health → returns dict`)
      is **xfail** if `python -m mcp_server` unreachable (so test suite
      stays green on machines without the IKIGAI venv installed).
- [ ] `.claude/loop/mcp_bridge.py` ≤ 510 LOC (was 405 + ~95 envelope parsing).
- [ ] No changes to v2 `mcp_bridge.py`, `server.py`, or `.mcp.json`
      (production binding is loop-layer concern; v2 gets its own M147).

## Design choices

- **Subprocess stdio client** (matches `.mcp.json` exactly): the loop
  bridge starts `python -u -m mcp_server` as a child process and
  talks JSON-RPC over stdin/stdout. This is what Claude Code already
  does for `.mcp.json`, so we're not introducing a new transport.
- **`-u` flag** (unbuffered stdout): same Windows pipe fix as commit
  `b93a1f3` referenced in orchestrator prompt. Required for stdio MCP
  to work on Windows.
- **`init_observability()` separate from `bind_server()`**: observability
  initialization is optional and safe to call even without MCP. Lets
  workers that don't need MCP still get OTel spans.
- **Resource envelope parsing in `mcp_bridge.py`** (not in
  `mcp_runtime.py`): keeps runtime layer thin (just transport) and
  parsing layer in the bridge module where the resource accessors live.
- **`bind_server()` mutates `mcp_bridge._server`** (not a parameter):
  matches the existing module-level pattern from M142. Callers don't
  pass `_server=`; they call `bind_server()` at startup.
- **xfail smoke test** (not skip): distinguishes "test machine doesn't
  have IKIGAI venv" (xfail — known limitation) from "binding is broken"
  (fail — real regression). Production users see the smoke pass.

## Honest scope

- ✅ Production binding module + envelope parsing + loop-tick integration
- ✅ Tests cover happy paths + idempotency + error contracts
- ✅ xfail smoke test for real-server round-trip
- ⚠️ **Real-server smoke is xfail on most test machines**: requires
  the IKIGAI venv at `src/ikigai/.venv/Scripts/python.exe` with
  `mcp` installed. Most CI doesn't have this. M146 ships working code
  with the smoke test as a known gap.
- ⚠️ **One subprocess per loop-tick.sh invocation**: not pooled. Acceptable
  per constitution §2 (reversibility over cleverness) — simple is correct.
- ⚠️ **No OTel init for resource accessors**: M143 deferred to M146; if
  M146 ships and you want spans on resource reads, that's M147.

## Lessons from predecessors

- **M142-M145 FakeMcpServer pattern**: tests monkeypatch `_server`.
  M146's production binding must NOT break this pattern. We mutate
  `_server` to the real client; tests still monkeypatch it. The test
  fixture for `bridge` in M142 just does `bridge._server = None` at
  load — M146 doesn't change that contract.
- **Phase 8.2 (2026-09-08)**: v2 mcp_bridge production binding was
  also deferred. M146 intentionally does NOT cross the boundary into
  v2's mcp_bridge — same pattern, separate workstream (M147 if/when).
- **M143 OTel plumbing**: M143's spans work in tests. M146's
  `init_observability()` is what makes them export in production.
  Without M143, M146 would have nothing to export. Without M146,
  M143's exports go nowhere. The two are complementary halves.
- **`.mcp.json` stdio pattern**: M146 copies the exact subprocess args
  from `.mcp.json` for the `ikigai` server (command, args, cwd, env).
  No new transport, no new auth, no new dependency.
- **Windows pipe fix (commit b93a1f3)**: stdio MCP hangs on Windows
  without `-u` (unbuffered). M146 uses `-u` explicitly.

## Followups (out of scope)

- **M147** — v2 graph mcp_bridge production binding (mirrors M146 for
  the v2 layer). Cost: $0.40.
- **M148** — persistent MCP connection daemon (replaces per-tick
  subprocess with one long-lived client). Optimization; M146 ships
  correctness first.
- **M149** — MCP resource span emission (OTel on resource reads;
  M143+M145 deferred this to M146 "if it lands at all" → moving
  to M149 because M146 chose not to).
- **M139 unblock** — real-LLM smoke test (independent of M146;
  needs `ANTHROPIC_API_KEY` direct or running hermes-agent proxy).

## Cost estimate

- **Implementation**: 1 sub-agent, sonnet-4-5, ~45 min, **$0.20**
- **Tests**: 1 sub-agent, sonnet-4-5, ~20 min, **$0.08**
- **Envelope parsing**: 1 sub-agent, sonnet-4-5, ~15 min, **$0.06**
- **Loop-tick integration**: 1 sub-agent, haiku-4-5, ~5 min, **$0.02**
- **Review + closeout**: orchestrator self-verify, **$0.05**
- **Total**: **$0.41** (round up to $0.50 for retry buffer)

## Atomic breakdown (for orchestrator)

- **T-146.1** — create `.claude/loop/mcp_runtime.py` (bind / unbind / init_observability)
- **T-146.2** — add `_parse_resource_envelope` to `mcp_bridge.py` + use in 6 accessors
- **T-146.3** — create `tests/test_m146_production_binding.py` (≥8 tests, xfail smoke)
- **T-146.4** — wire `loop-tick.sh` to call `init_observability()` + `bind_server()`
- **T-146.5** — update orchestrator prompt M146 references
- **T-146.6** — verify regression sweep (M142+M143+M144+M145+M146 + contracts/integration)
- **T-146.7** — append `progress.md` M146 entry, atomic commit + push
