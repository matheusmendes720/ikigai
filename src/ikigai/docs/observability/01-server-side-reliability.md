# Spec: Server-Side Reliability in 3 External MCP Servers

**Status:** Proposed
**Date:** 2026-08-27
**Owner:** IKIGAI
**Related work:** Task 4 (IKIGAI-side reliability, landed `87f6ef9`)

## Goal

Mirror the IKIGAI-side reliability layer (retry + circuit breaker + scoped cache invalidation) onto the **server side** of the 3 external MCP servers (tuiboard, taskdog, solverforge-calendar). Currently these servers are pass-through — any downstream failure (DB write, network call, schema validation) propagates raw to the client. With this spec, each server gets:

- A retry loop with exponential backoff for transient failures (DB timeouts, network blips)
- A circuit breaker that opens after N consecutive failures and short-circuits fast for `reset_timeout_s`
- A `try/except` boundary that converts internal exceptions into structured MCP error responses (instead of bare stderr)

## Background

What we have today:

| Server | Stack | Retry | Circuit breaker | Error → MCP |
|---|---|---|---|---|
| tuiboard | TypeScript/Bun stdio MCP | ❌ | ❌ | bare stderr |
| taskdog | Python FastMCP stdio | ❌ | ❌ | bare stderr |
| solverforge-calendar | Rust rmcp stdio | ❌ | ❌ | bare stderr |

IKIGAI's `src/agents/tools.py` already wraps each call site with `@circuit_breaker + @retry_with_backoff` (Task 4, `87f6ef9`). But that protection only helps IKIGAI — if a client connects to solverforge-calendar directly (e.g. via Claude Desktop MCP), it gets no resilience.

## Proposed approach

Each server gets a thin reliability layer applied at the **tool dispatch boundary** — i.e. the function that receives `(name, arguments)` and routes to the handler.

### Common contract (all 3 servers)

1. **Retry config:** 3 attempts, exponential backoff `0.1s → 0.2s → 0.4s`, ±20% jitter, retryable exceptions: `TimeoutError`, `ConnectionError`, transient DB errors (SQLITE_BUSY, deadlocks). Non-retryable: `ValueError`, `KeyError`, validation errors.

2. **Circuit breaker config:** opens after 5 consecutive failures, `reset_timeout_s = 30s`. Half-open probe after timeout.

3. **Error → MCP envelope:** retryable errors stay `isError=true` with `error.class` and `error.message` set. Non-retryable errors return immediately. Circuit-open returns a stable error code so clients can implement their own back-pressure.

### Per-server implementation

| Server | File | Pattern |
|---|---|---|
| tuiboard | `src/v3/observability/reliability.ts` (new) | wrap `mcp/server.ts` dispatch table with `withRetryAndBreaker(name, handler)` |
| taskdog | `packages/taskdog-mcp/src/taskdog_mcp/reliability.py` (new) | wrap `register_tool` decorator chain with `instrumented_tool` + `retried_tool` + `circuit_broken_tool` |
| solverforge-calendar | `src/observability.rs` (extend) | add a `#[retry]` + `#[circuit_breaker]` proc-macro pair, apply to each `#[tool]` handler |

### Acceptance criteria

1. Each server has a `withRetryAndBreaker` (or equivalent) helper applied uniformly to all tool handlers
2. Configurable via env vars: `RETRY_MAX_ATTEMPTS`, `RETRY_INITIAL_BACKOFF_S`, `CB_FAILURE_THRESHOLD`, `CB_RESET_TIMEOUT_S` (defaults: 3, 0.1, 5, 30)
3. Unit tests: retry succeeds after N transient failures; CB opens after 5; half-open recovery; non-retryable exceptions don't trigger retry
4. Existing tool behavior unchanged when `RETRY_ENABLED=false` (zero overhead)
5. Wraps OTel spans added in Task 1 (each retry attempt = child span with `retry.attempt=N`)

### Out of scope

- Bulkhead (concurrency limits) — separate spec
- Rate limiting per client — separate spec
- IKIGAI-side changes — already done in Task 4
- The 4th interface (IKIGAI MCP server itself) — its handlers are mostly pure compute; server-side retry is unnecessary

## Risks

1. **Retry amplification**: a tool that mutates state (e.g. `task_create`) could be retried after partial success → duplicate creation. Mitigation: only retry idempotent tools or tools where the underlying call is wrapped in a transaction that rolls back on retry. The 3 mutation tools in solverforge (`calendars_create`, `projects_create`, `events_create`) need explicit `idempotency_key` support.
2. **CB observation count**: same risk as Task 4 — if retry is outer, CB counts attempts not logical calls. Mitigation: stack retry inner, CB outer. Mirror the Task 4 fix brief exactly.
3. **Span fan-out**: each retry attempt emits a child span. Heavy retries (3 attempts × 100 req/s) = 300 spans/s. Mitigation: keep retry attempts ≤ 3 and add `retry.exhausted` boolean on parent span.

## Open questions

1. Should the reliability config live in env vars or in a config file (`~/.config/<server>/reliability.toml`)?
2. Should there be a per-tool override (e.g. `task_create` retries never, since mutations are unsafe)?
3. Should CB state be persisted across restarts (in which case each tool needs a CB per remote dependency, not per server)?

## Implementation order

1. **tuiboard first** (smallest, TypeScript pattern is cleanest to validate)
2. **taskdog second** (FastMCP decorator chain is well-trodden)
3. **solverforge last** (Rust proc macros require the most upfront design)

Estimated effort: ~3-5 days per server = 1.5 weeks total.

---

*Spec generated 2026-08-27 as part of the observability follow-up work.*
