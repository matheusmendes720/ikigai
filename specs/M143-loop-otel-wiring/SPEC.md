---
name: M143-loop-otel-wiring
description: OpenTelemetry spans for .claude/loop/mcp_bridge.py — mirrors v2 mcp_bridge T-8.3.1 pattern with tracer name loop.mcp.{tool_name}
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

# M143 — Loop-side OTel Wiring

> **What:** Add OpenTelemetry spans to `.claude/loop/mcp_bridge.py` (M142),
> mirroring the v2 mcp_bridge T-8.3.1 pattern. Tracer name prefix
> `loop.mcp.{tool_name}` (deliberately distinct from v2's `ikigai.bridge.{tool_name}`
> and server-side `ikigai.mcp.{tool_name}` so the 3 layers don't double-count
> in trace exporters).
> **Why:** When production binding (M146) lands, every MCP call from a
> loop sub-agent will be a black box without spans. Latency regressions,
> silent errors, and per-tool call counts become invisible. OTel spans
> give operators the same observability story they have today for v2 graph
> calls — same attribute schema, same exporter pipeline.

## Current state (verified 2026-09-26)

- v2 side: `src/ikigai/src/agents/v2/mcp_bridge.py:75-98` (`_call` with OTel)
  emits spans prefixed `ikigai.bridge.{tool_name}` via
  `_tracer = get_tracer("ikigai.bridge")` from
  `src/ikigai/src/observability/otel_init.py:get_tracer`.
- Server side: `src/ikigai/src/mcp_server/tracing.py:traced_tool_dispatch`
  emits spans prefixed `ikigai.mcp.{tool_name}` — distinct from the bridge
  prefix on purpose (see `mcp_server/tracing.py:23` comment).
- Loop side (M142, this session): `.claude/loop/mcp_bridge.py:_call()` is
  span-less. No `get_tracer` import. The 6 wrappers have no instrumentation.
- Observability infrastructure: `src/ikigai/src/observability/otel_init.py`
  exposes `init_tracing()` (idempotent, process-wide lock) +
  `get_tracer(name)`. LangSmith + Langfuse exporters both wired from a
  single SDK. **Importable from anywhere on `PYTHONPATH`** — no
  `.claude/loop/observability/` directory needed.

## Scope

**In scope** (M143):

1. Add OTel span emission to `.claude/loop/mcp_bridge.py:_call()` —
   port the v2 pattern byte-for-byte (5 attributes: `tool.name`,
   `tool.arguments_hash`, `tool.duration_ms`, `tool.error.class`,
   `tool.error.message`, `tool.error.traceback`).
2. Import `get_tracer` from `src.ikigai/src/observability/otel_init.py`
   at module level. Tracer name `loop.mcp` (NOT `loop.mcp.bridge` —
   shorter, parallel to `ikigai.bridge`).
3. Pin span-name prefix in a module constant `SPAN_PREFIX = "loop.mcp."`
   so a future test can assert no double-prefixing.
4. Add `tests/test_m143_mcp_bridge_spans.py` (≥4 tests):
   - `_call` opens a span with name `loop.mcp.{tool_name}` on success
   - `_call` opens a span with name `loop.mcp.{tool_name}` on error
   - Span attributes include `tool.name` + `tool.arguments_hash` +
     `tool.duration_ms` (success path)
   - Span attributes include `tool.error.class` + `tool.error.message`
     on error path
5. Append M143 entry to `progress.md` after tests pass.
6. Atomic commit + push.

**Out of scope** (deferred to M146+):

- Production binding of `_server` to FastMCP client (still mocked).
- Init of `init_tracing()` at loop startup (deferred to M146 — same
  Phase 8.2 deferral pattern). For M143, spans work in test environments
  that pre-initialize OTel (via `opentelemetry.sdk.trace.TracerProvider`
  in test conftest).
- Resource attributes (deployment.environment, service.name override
  for loop layer) — deferred to M146.

## Acceptance criteria

- [ ] `.claude/loop/mcp_bridge.py` imports `get_tracer` from
      `src.ikigai/src/observability/otel_init.py`.
- [ ] Module-level constant `SPAN_PREFIX = "loop.mcp."`.
- [ ] Module-level tracer `_tracer = get_tracer("loop.mcp")`.
- [ ] `_call()` wraps `_server.call(...)` in
      `_tracer.start_as_current_span(f"{SPAN_PREFIX}{tool_name}")`.
- [ ] Span attributes set:
      - `tool.name` (string)
      - `tool.arguments_hash` (SHA-256 of canonical JSON, first 16 hex)
      - `tool.duration_ms` (number)
      - `tool.error.class` (only on error)
      - `tool.error.message` (only on error, truncated to 500 chars)
      - `tool.error.traceback` (only on error, truncated to 3000 chars)
- [ ] Span status set to `Status(StatusCode.OK)` on success,
      `Status(StatusCode.ERROR, str(exc))` on error.
- [ ] `tests/test_m143_mcp_bridge_spans.py` exists with ≥4 tests, all PASS.
- [ ] All 14 M142 tests still PASS (no regression).
- [ ] Total LOC of `.claude/loop/mcp_bridge.py` ≤200 (was 143; +57 for span
      plumbing matches v2's relative size).
- [ ] No changes to v2 `mcp_bridge.py`, `server.py`, or `.mcp.json`.

## Design choices

- **Tracer name `loop.mcp`** (not `loop.mcp.bridge`): parallel to v2's
  `ikigai.bridge` and server's `ikigai.mcp`. The 3 prefixes form a clear
  hierarchy: `ikigai.mcp.{tool}` (server-side FastMCP tool dispatch) →
  `ikigai.bridge.{tool}` (v2 graph sync wrapper) → `loop.mcp.{tool}`
  (loop-side sync wrapper). No double-counting in trace UIs.
- **`SPAN_PREFIX` constant**: prevents drift if someone refactors the
  f-string. Tests can assert `f"{SPAN_PREFIX}{tool_name}"` matches the
  actual span name.
- **Same attribute schema as v2**: `tool.arguments_hash` instead of raw
  args (sensitive data safe), `tool.duration_ms` instead of seconds
  (tracing UI convention), `tool.error.traceback` truncated to 3000 chars
  (matches v2).
- **No `init_tracing()` call here**: it lives in production startup
  (M146). Tests that need a working tracer use an in-memory
  `InMemorySpanExporter` (already a dependency of the v2 bridge tests).
- **Span scope = `_call()`, not the wrappers**: one span per MCP tool
  dispatch regardless of how many wrappers delegate. Mirrors v2 exactly.

## Honest scope

- ✅ `_call()` wrapped in OTel span with full attribute schema
- ✅ Span prefix constant for drift-detection
- ✅ Tests cover success + error paths with attribute assertions
- ⚠️ **No production init of OTel SDK**: M143 tests use in-memory exporter.
  Real export to LangSmith/Langfuse still requires `init_tracing()` call
  at loop startup, which is M146.
- ⚠️ **No resource attributes for loop layer**: spans inherit the
  service name from whichever SDK init ran first. Default is
  `ikigai-maintainer` (v2 default). Adding a loop-specific override is
  M146.

## Lessons from predecessors

- **v2 mcp_bridge T-8.3.1 (2026-09-08)**: the 5-attribute schema +
  truncation rules + tracer-name separation all come from this. M143
  inherits verbatim. Don't reinvent.
- **M11/M12 PAV-math drift**: bridge/server drift was silent because no
  drift test. M143 has its own drift test
  (`test_m143_span_prefix_constant_matches_actual_span_name`).
- **M142 itself**: the loop bridge lives at `.claude/loop/`, NOT in v2.
  M143 keeps this separation — observability wiring stays in
  `src/ikigai/src/observability/` (single source of truth), imported
  across layers.

## Followups (out of scope)

- **M144** — write-side MCP tools (vault_write, ikigai_write_tasks,
  investigation_*). Cost: $0.20.
- **M145** — taskdog fork tools beyond `taskdog_list` + 6 resources.
- **M146** — production binding of `_server` + `init_tracing()` at loop
  startup. Cost: $0.50.

## Cost estimate

- **Implementation**: 1 sub-agent, sonnet-4-5, ~15 min, **$0.06**
- **Tests**: 1 sub-agent, sonnet-4-5, ~15 min, **$0.05**
- **Review + closeout**: orchestrator self-verify, **$0.05**
- **Total**: **$0.16** (round up to $0.30 for retry buffer)

## Atomic breakdown (for orchestrator)

- **T-143.1** — add OTel span emission to `.claude/loop/mcp_bridge.py:_call()`
- **T-143.2** — create `tests/test_m143_mcp_bridge_spans.py` (≥4 tests)
- **T-143.3** — verify M142 tests still PASS (regression sweep)
- **T-143.4** — append `progress.md` M143 entry, atomic commit + push
