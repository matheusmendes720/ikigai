# OTel Integration Plan — 3 External MCP Servers

> **Status:** Draft — 2026-08-28
> **Companion to:** `code-docs/observability/01-server-side-reliability.md` · `02-integration-smoke-test.md` · `03-merge-plan.md` · `04-dissolve-worktree.md` · `05-dashboard-design.md`
> **Scope:** Per-server implementation plan for adding OpenTelemetry tracing to the 3 external MCP servers (tuiboard, taskdog, solverforge-calendar) so dashboards 1.4 (External MCP Server Health) and 1.6 (Retry Patterns) and the dual-export parity alert become observable.

---

## §0 Purpose

Today, IKIGAI spans show the client side of every external MCP call but the **server side** of those calls is dark. This is the gap that master diagnostic §4 calls out: observability is "blind to ~90 % of execution" because the 3 external servers emit zero traces. Each server carries a `feat/otel-tracing` branch (already implemented in code but pending merge), and this doc is the **execution plan** that turns those branches into running observability.

After this plan lands:

| Today (no trace) | After (with trace) |
|---|---|
| LangSmith shows only the IKIGAI client span wrapping the call | LangSmith shows server-side tool spans for `board_list`, `task_create`, `events_create`, etc. with their own duration, error class, and JSON-RPC envelope |
| Dual-export parity alert (D1.4 row 4) cannot fire — no second signal to compare | Parity alert fires only when LangSmith and Langfuse actually diverge |
| SLOs in 05-dashboard §3 for tuiboard/taskdog/solverforge are theoretical | SLOs become measurable per server / per tool |
| Failures inside solverforge's Rust code surface as raw MCP errors only | Failures carry `error.code` (rmcp `ErrorCode` enum) and `error.class` (`ErrorData` classification) |
| Retry amplification (D1.6) shows only IKIGAI-side retries | Retry spans from each server attach to the same `cycle_id` |

The plan is **document-only** — code stubs in §3 are illustrative and not implementation, per the standing instruction `nao vamos codificar nada ainda`.

---

## §1 Current State

| Server | Language / runtime | MCP SDK | OTel branch | Today emits | Branch state |
|---|---|---|---|---|---|
| **tuiboard** | TypeScript on Bun (≥ 1.2.0), hand-rolled JSON-RPC stdio | none — `node:readline` + `sendResponse/sendError` in `src/v3/mcp/server.ts` | `feat/otel-tracing` ✅ | nothing | Open at `2c39867` (`fix(observability): wire both LangSmith and Langfuse exporters`) on top of `590ea60` (`feat(observability): dual OTLP/HTTP exporters`) |
| **taskdog** | Python ≥ 3.12, FastMCP ≥ 1.2.0 | `mcp.server.fastmcp.FastMCP` with `@mcp.tool(name=...)` decorator | `feat/otel-tracing` ✅ | nothing (Python `logging` only, no spans) | **Already merged** to `main` at `d6bebc2d` (`Merge branch 'feat/otel-tracing'`) on top of `5a8b1bb2` (`feat(observability): dual OTLP/HTTP exporters`); `600c92b9` adds `uv.lock` test deps |
| **solverforge-calendar** | Rust (edition 2021) + `tokio` + `rmcp` 3.1 with macros | `#[tool_router]` + `#[tool]` on `McpServer` impl block | `feat/otel-tracing` + `feat/solverforge-otel-wip` | nothing | Open at `3243296` (merged `feat/rust-build-fix` `1716b16` into otel) on top of `064b8c9` (`fix(solverforge-otel): wire MCP_PROTOCOL_VERSION + http feature + no-op observability`) and `cfbf12b` (`feat(observability): dual OTLP/HTTP exporters`) |

Three independent branches with one common shape: each adds an observability module next to the server entry point, gates it on `OTEL_ENABLED`, and wires dual OTLP/HTTP export (LangSmith + Langfuse) keyed off env vars. The deltas between the branches are the SDK choices and the tool-wrap idioms — both are documented below in §3.

---

## §2 Reference Pattern — IKIGAI

IKIGAI already has the dual-export pattern that all 3 externals mirror. Source of truth: `C:\Users\mathe\code_space\life-oss\life\life-ops\ikigai\src\observability\otel_init.py`.

The IKIGAI module:

1. Builds two `OTLPSpanExporter` instances:
   - **LangSmith** → `https://api.smith.langchain.com/api/v1/otel/v1/traces` with `x-api-key` + `Langsmith-Project` headers (default project `ikigai`).
   - **Langfuse** → `{LANGFUSE_HOST}/api/public/otel/v1/traces` (default `https://cloud.langfuse.com`) with `Authorization: Basic base64(public:secret)`.
2. Wraps each in a `BatchSpanProcessor` and adds to a single `TracerProvider`.
3. Resource attributes: `service.name = OTEL_SERVICE_NAME` (default `ikigai-maintainer`) + `deployment.environment = IKIGAI_ENV` (default `local`).
4. Auto-instrumentation: `langchain`, `requests`, `sqlite3`, `logging` — best-effort via `_try_instrument` that swallows failures so observability never blocks startup.
5. Idempotency via a process-wide `threading.Lock` + `_INITIALIZED` flag (the equivalent in tuiboard/taskdog/solverforge is in §3 per language).
6. `get_tracer()` returns a lazy tracer — safe to call before init.
7. `shutdown_tracing()` flushes pending spans (5 s default `BatchSpanProcessor` interval can drop tail spans without this).

Tool-level wraps use `observed_tool(tool_name)` in `C:\Users\mathe\code_space\life-oss\life\life-ops\ikigai\src\observability\error_capture.py`. The decorator:

- Starts span `tool.<tool_name>` with `tool.name` attribute.
- Binds function signature args into `tool.arg.<key>` attributes (truncated to 200 chars to bound span size — this is the cardinality safeguard that the spec in §4 below inherits).
- On `UnicodeDecodeError` / `FileNotFoundError`, sets `span.status = ERROR`, `span.record_exception(e)`, and `error.class` attribute.
- On success, sets `tool.status = ok`.

The 3 external servers **do not** inherit `observed_tool` directly (different languages) but mirror the attribute vocabulary verbatim — `tool.name`, `tool.arg.<key>`, `tool.status`, `error.class`, `mcp.protocol_version`, `tool.duration_ms`, `jsonrpc.method`, `jsonrpc.id`. The cross-language contract is the attribute set, not the API.

---

## §3 Per-Server Plan

### §3.1 tuiboard

**Repo:** `C:\Users\mathe\code_space\apps\kanban\tuiboard`
**Branch to merge:** `feat/otel-tracing` → `main` (per `03-merge-plan.md` Step 3)

**Language / runtime:** TypeScript on Bun ≥ 1.2.0; stdio MCP via hand-rolled `node:readline` in `src/v3/mcp/server.ts`.

**SDK choice:**

| Package | Version | Purpose |
|---|---|---|
| `@opentelemetry/api` | `^1.9.0` | tracer / span / status API |
| `@opentelemetry/sdk-node` | `^0.57.2` | NodeSDK bootstrap, resource wiring, span processors |
| `@opentelemetry/exporter-trace-otlp-http` | `^0.57.2` | `OTLPTraceExporter` over HTTP/proto for LangSmith + Langfuse |
| `@opentelemetry/resources` | `^1.30.1` | `Resource` with `ATTR_SERVICE_NAME` + `ATTR_SERVICE_VERSION` |
| `@opentelemetry/semantic-conventions` | `^1.30.1` | semantic attribute keys |

All four are already declared in `package.json` (lines 55-59) — the branch adds no new dependencies.

**Init point:** `C:\Users\mathe\code_space\apps\kanban\tuiboard\src\v3\observability\init.ts` exports `initObservability()` and `getTracer()`. The branch currently calls init lazily inside `withToolSpan()` (line 110). To make init predictable, the merge should add an explicit `initObservability()` call at the top of `main()` in `src/v3/mcp/server.ts` (around line 165) — this also enables `shutdownObservability()` on process exit.

**Per-tool span wrap:** the existing `withToolSpan(toolName, handler, jsonrpcId, jsonrpcMethod)` wrapper in `init.ts` (lines 130-179) is invoked at line 234 of `server.ts` for every `tools/call`. The 5 tools (`board_list`, `board_tasks_get`, `board_tasks_update`, `board_tasks_create`, `board_tasks_delete`) are already wired through the wrapper — no further wrap changes are needed.

**Dependencies to add:** none — all OTel packages already in `package.json`.

**Code stub (illustrative, 10-30 lines, NOT implementation):**

```typescript
// src/v3/mcp/server.ts (top of main())
import { initObservability, shutdownObservability } from "../observability/init";

async function main() {
  initObservability();
  // ... existing readline / dispatch ...

  process.on("beforeExit", async () => {
    await shutdownObservability();
  });
}
```

**Effort:** ~1.5 hours. Most work is in verifying the existing branch — no new code is required beyond wiring init/shutdown at server entry.

**Risk:** **low.** The branch is already complete (3 commits, tests in `init.test.ts` cover enabled/disabled paths and the dual-export wire fix `2c39867`). Auto-instrumentation is **not** used — only the manual `withToolSpan` wrapper — so there is no risk of unrelated modules being instrumented. The hand-rolled JSON-RPC server does not require any SDK integration.

**Reversibility:** **high.** The merge is a single `feat/otel-tracing` → `main` squash with `OTEL_ENABLED=false` as the default; flipping back to dark requires zero code changes. NodeSDK can be disabled at runtime via env var.

**Verification:**

- `bun test` — existing `init.test.ts` covers 9 cases (4 disabled paths, 2 enabled paths, 3 attribute checks).
- LangSmith span search: filter `service.name = tuiboard` in project `ikigai`.
- Langfuse trace search: filter `service.name = tuiboard`.
- Manual smoke: spawn `bun ./bin/tuiboard-mcp.ts` with `OTEL_ENABLED=true`, send one `tools/call board_list` over stdio, see 1 span in each backend.

---

### §3.2 taskdog

**Repo:** `C:\Users\mathe\code_space\apps\dev-tools\taskdog`
**Branch to merge:** **already merged** at `d6bebc2d` on `main`.

**Language / runtime:** Python ≥ 3.12, FastMCP ≥ 1.2.0 (`from mcp.server.fastmcp import FastMCP`).

**SDK choice:**

| Package | Version | Purpose |
|---|---|---|
| `opentelemetry-api` | `>=1.24.0` | tracer / span / status |
| `opentelemetry-sdk` | `>=1.24.0` | `TracerProvider` + `BatchSpanProcessor` |
| `opentelemetry-exporter-otlp-proto-http` | `>=1.24.0` | OTLP/HTTP exporter |

Already declared in `packages/taskdog-mcp/pyproject.toml` (lines 24-26). No new deps.

**Init point:** `C:\Users\mathe\code_space\apps\dev-tools\taskdog\packages\taskdog-mcp\src\taskdog_mcp\observability.py` exports `init_observability()` + `instrumented_tool()` decorator factory. Called from `main.py` line 28 before `create_mcp_server()`.

**Per-tool span wrap:** the `instrumented_tool(mcp, name)` decorator is already applied to all task handlers via `@instrumented_tool(mcp=mcp, name="...")` in `tools/task_query.py`, `task_crud.py`, `task_lifecycle.py`, `task_decomposition.py`, `task_tags.py`, `task_audit.py`, `task_optimization.py`. Tool wrapper counts in `src/taskdog_mcp/tools/*.py`: `task_audit:3`, `task_crud:7`, `task_decomposition:7`, `task_lifecycle:7`, `task_optimization:3`, `task_query:4`, `task_tags:2` — totaling 33 instrumented tools.

**Known gap (per `taskdog` observability.py review):** the LangSmith endpoint on line 87 is `https://api.lansmith.com/v1/traces` (note: **`lansmith`** not `langsmith`). This appears to be a typo introduced when porting from IKIGAI's `otel_init.py` which uses `https://api.smith.langchain.com/api/v1/otel/v1/traces`. The branch needs a one-line fix **before** the smoke test in `02-integration-smoke-test.md` can pass against the merged `main`.

**Dependencies to add:** none.

**Code stub (illustrative):**

```python
# packages/taskdog-mcp/src/taskdog_mcp/observability.py (line 87 fix)
endpoint = os.getenv(
    "LANGSMITH_OTEL_ENDPOINT",
    "https://api.smith.langchain.com/api/v1/otel/v1/traces",  # was api.lansmith.com
)
```

**Effort:** ~0.5 hours for the endpoint fix + ~1 hour verification. The merge already happened — work is downstream correction + verification.

**Risk:** **low** for the merge itself (it's already on `main`); **medium** for the observability story until the endpoint typo is corrected. Until the typo is fixed, taskdog traces cannot reach LangSmith, which means D1.4's dual-export parity alert will read 100 % Langfuse / 0 % LangSmith and fire constantly.

**Reversibility:** **high.** Setting `OTEL_ENABLED=false` (the default) returns the server to dark with zero overhead per `observability.py` line 48-51.

**Verification:**

- `uv run pytest packages/taskdog-mcp/tests/` — tests added in the merge (per `600c92b9` uv.lock churn).
- LangSmith span search: `service.name = taskdog.mcp`.
- Langfuse trace search: same.
- Manual smoke: spawn `taskdog-mcp` with `OTEL_ENABLED=true` + corrected `LANGSMITH_API_KEY`, invoke any tool, see 1 span in each backend.

---

### §3.3 solverforge-calendar

**Repo:** `C:\Users\mathe\code_space\apps\calendar\solverforge-calendar`
**Branch to merge:** `feat/otel-tracing` (rebased on `feat/rust-build-fix` `1716b16` per `03-merge-plan.md` Step 1-2) → `main`. There is also a `feat/solverforge-otel-wip` branch checked out locally that may be abandoned — verify with the team before deleting.

**Language / runtime:** Rust edition 2021, `rmcp` 3.1 with `macros` + `transport-io` features, `tokio` runtime.

**SDK choice:**

| Crate | Version | Purpose |
|---|---|---|
| `opentelemetry` | `0.32` | trace API |
| `opentelemetry_sdk` | `0.32` | `TracerProvider` + exporters |
| `opentelemetry-otlp` | `0.32` (features: `http-proto`, `reqwest-blocking-client`) | OTLP/HTTP exporter |
| `tracing` | `0.1` | `#[instrument]` attribute macro (the wrap) |
| `tracing-opentelemetry` | `0.32` | bridges `tracing` → `opentelemetry` |
| `tracing-subscriber` | `0.3` (feature: `env-filter`) | subscriber registry |
| `base64` | `0.22` | Langfuse Basic auth encoding |

All seven already declared in `Cargo.toml` (lines 71-77). No new deps.

**Init point:** `C:\Users\mathe\code_space\apps\calendar\solverforge-calendar\src\observability.rs` exports `init_observability() -> bool` (returns `true` if any exporter is wired, `false` if `OTEL_ENABLED=false` or no keys present). Called from `bin/solverforge-calendar-mcp.rs` line 881 at the top of `main()`.

**Known gap:** the current `observability.rs` (full file inspected, 141 lines) **does not actually wire the exporter** — it only prints `eprintln!("[observability] LangSmith enabled: ...")` after reading env vars. The real `opentelemetry-otlp` exporter setup is missing. The branch needs to be completed before merge; the `feat/solverforge-otel-wip` branch likely contains this work — verify.

**Per-tool span wrap:** the `bin/solverforge-calendar-mcp.rs` `impl McpServer` block has `#[tool(name = "...", description = "...")]` paired with `#[instrument(skip(self), fields(tool.name = "...", mcp.protocol_version))]` on **every** tool handler (verified: all 20+ tool methods on lines 272-873 carry `#[instrument]`). The wrap is already in place — only the SDK initialization needs to land.

**Dependencies to add:** none.

**Code stub (illustrative, ~25 lines, NOT implementation):**

```rust
// src/observability.rs (extension to existing init_observability)
use opentelemetry::{global, KeyValue};
use opentelemetry::trace::TracerProvider as _;
use opentelemetry_sdk::{Resource, trace::Config, trace::TracerProvider};
use opentelemetry_otlp::WithExportConfig;
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::util::SubscriberInitExt;

pub fn init_observability() -> bool {
    // ... existing env-var reads ...

    let resource = Resource::new(vec![
        KeyValue::new("service.name", "solverforge-calendar"),
        KeyValue::new("service.version", env!("CARGO_PKG_VERSION")),
    ]);

    let langsmith_exporter = opentelemetry_otlp::SpanExporter::builder()
        .with_http()
        .with_endpoint(langsmith_endpoint)
        .with_headers(langsmith_headers)
        .build()?;

    let provider = TracerProvider::builder()
        .with_config(Config::default().with_resource(resource))
        .with_batch_exporter(langsmith_exporter, runtime::Tokio)
        .build();

    global::set_tracer_provider(provider.clone());
    let tracer = provider.tracer("solverforge-calendar");

    let otel_layer = tracing_opentelemetry::layer().with_tracer(tracer);
    tracing_subscriber::registry()
        .with(otel_layer)
        .with(EnvFilter::from_default_env())
        .try_init()?;
    // ... similar block for Langfuse ...
}
```

**Effort:** ~4-6 hours — the wrap infrastructure (`#[instrument]`) is in place, but the SDK initialization is missing from the current `observability.rs`. This is the only server where real code work is needed.

**Risk:** **medium.** Two risks:

1. **`tracing-opentelemetry` crate version linkage** — `0.32` of `tracing-opentelemetry` may not match `0.32` of `opentelemetry-otlp` exactly; spec 05 §9 (deferred) flags this. If the merge encounters a crate version conflict, pin one side and re-test.
2. **Async runtime overlap** — `rmcp` already runs inside `#[tokio::main]`; the OTel batch processor wants its own runtime. The `runtime::Tokio` bridge is the standard solution but must be wired correctly or `BatchSpanProcessor` will silently drop spans.

**Reversibility:** **medium.** Setting `OTEL_ENABLED=false` returns to dark with zero overhead. However, the unused `opentelemetry-*` crates will still compile, adding ~30 s to the build and ~5 MB to the binary. Mitigation: gate the dependencies behind a Cargo feature `otel` so dark builds skip them.

**Verification:**

- `cargo test` — existing tests in `src/observability.rs` (lines 97-139) cover the env-var-only branch.
- LangSmith span search: `service.name = solverforge-calendar`.
- Langfuse trace search: same.
- Manual smoke: `cargo run --bin solverforge-calendar-mcp` with `OTEL_ENABLED=true`, send one `tools/call calendars_list`, see 1 span in each backend.

---

## §4 Common OTel Strategy

### §4.1 Env-var contract (all 3 servers)

All 3 servers MUST honor the same env-var names so a single `.env.example` in IKIGAI documents the contract for the whole fleet:

| Variable | Default | Used by |
|---|---|---|
| `OTEL_ENABLED` | `false` | gate — when `false`, all 3 servers emit zero spans with zero overhead |
| `LANGSMITH_API_KEY` | unset | LangSmith exporter enablement (any of the 3 servers) |
| `LANGSMITH_PROJECT` | `ikigai` | LangSmith project tag |
| `LANGSMITH_OTEL_ENDPOINT` | LangSmith public OTLP ingest | override endpoint for staging or self-hosted |
| `LANGFUSE_PUBLIC_KEY` | unset | Langfuse exporter enablement (part 1/2) |
| `LANGFUSE_SECRET_KEY` | unset | Langfuse exporter enablement (part 2/2) |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Langfuse base URL |

The endpoint defaults must match exactly across all 3 servers. Today:

- IKIGAI (`otel_init.py:41`): `https://api.smith.langchain.com/api/v1/otel/v1/traces` — **correct**.
- tuiboard (`init.ts:54`): `https://api.smith.langchain.com/api/v1/otel/v1/traces` — **correct**.
- taskdog (`observability.py:87`): `https://api.lansmith.com/v1/traces` — **WRONG**. Must be fixed before the smoke test passes.
- solverforge (`observability.rs:21`): `https://api.smith.langchain.com/api/v1/otel/v1/traces` — **correct**.

### §4.2 API key topology

Three options were considered; recommendation is **per-server keys, same project tag**.

| Option | Pro | Con | Verdict |
|---|---|---|---|
| One shared LangSmith key for all 4 services | Simple .env | One leaked key exposes the whole fleet; per-service rate limits impossible | rejected |
| Per-server LangSmith keys, same `LANGSMITH_PROJECT=ikigai` | Full per-server rate limiting + revoke granularity; one project for unified search | One more secret to manage per server | **recommended** |
| Per-server LangSmith keys, per-server project | Maximum isolation | Splits the trace UI into 4 projects; D1.4 cross-server correlation breaks | rejected |

For Langfuse the same reasoning applies: per-server `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` pairs. Langfuse supports a project-level scope inside a single org, so we keep the Langfuse project name = `ikigai` for the same unified-search benefit.

### §4.3 Auto-instrumentation vs manual spans

| Server | Strategy | Reason |
|---|---|---|
| IKIGAI | **Both** — auto for langchain/requests/sqlite3/logging, manual for tools | I/O-heavy harness |
| tuiboard | **Manual only** (`withToolSpan` wrapper) | Pure JSON-RPC dispatcher; no HTTP/DB in the tool path |
| taskdog | **Manual only** (`instrumented_tool` decorator) | HTTP client is `taskdog-client`; auto-instrumenting it would flood spans. Manual only |
| solverforge | **Manual only** (`#[instrument]` macro on every `#[tool]`) | DB ops are inside `tokio::task::spawn_blocking`; auto-instrumenting rusqlite would create spans on internal queries that are not useful at the tool level |

The rule: **manual spans at the tool boundary, auto-instrumentation disabled.** This keeps cardinality bounded — see §4.4.

### §4.4 Cardinality safeguards

Spec 05 §8 Q4 flagged this. The fix is in place across all 3 externals:

- **`tool.arg.<key>`** truncated to 200 chars (IKIGAI's `error_capture.py:58`); same convention in tuiboard/taskdog/solverforge.
- **`tool.name`** is a closed enum (5 for tuiboard, ~33 for taskdog, ~30 for solverforge) — never user-supplied.
- **`jsonrpc.id`** allowed to be a string OR number — coerced to `""` on null/undefined (tuiboard `init.ts:148`).
- **`error.class`** is the Pythonic class name (taskdog) or `ErrorCode` enum int (solverforge) or `err.message` (tuiboard) — bounded.
- **No PII in span attributes.** The IKIGAI convention is to truncate `tool.arg.*` and never log full payloads. The 3 externals must follow this.

---

## §5 Migration Sequence

Recommendation: **taskdog first, then tuiboard, then solverforge.**

| Order | Server | Why this order |
|---|---|---|
| 1 | **taskdog** | Already merged to `main`. The only remaining work is the `lansmith` → `langsmith` endpoint fix + smoke verification. Lowest risk, fastest path to a measurable dashboard. |
| 2 | **tuiboard** | Branch is complete with tests; only needs the init/shutdown wiring at server entry (1.5 h). After taskdog, the dashboard D1.4 will start populating for `taskdog.mcp` and `tuiboard` simultaneously. |
| 3 | **solverforge** | Branch has `#[instrument]` macros in place but `observability.rs` is incomplete (env-var reads but no SDK init). Requires real code work + crate-version risk. Largest blast radius — the Rust binary is the slowest to build and test. |

**Why not solverforge first?** Spec 01 §"Implementation order" recommends tuiboard → taskdog → solverforge for the **reliability** layer because TypeScript is cleanest to validate. That ordering does not transfer to **OTel** because:

- For OTel, the highest-value server is the one that is **already merged and verified**. That is taskdog.
- The lowest-risk server is the one whose branch is complete with tests. That is tuiboard.
- Solverforge has the largest binary build cost, so it should go last when CI time matters.

**Inter-server verification gates** (each gate must pass before the next server starts):

1. **Gate 1 (taskdog):** smoke test from `02-integration-smoke-test.md` reports ≥ 1 taskdog span in LangSmith AND Langfuse with `tool.name = get_statistics`. D1.4 row 4 (dual-export parity) reads ±0 % for taskdog.
2. **Gate 2 (tuiboard):** same as gate 1 but for `tool.name = board_list`.
3. **Gate 3 (solverforge):** same as gate 1 but for `tool.name = calendars_list`. Includes a 5-minute soak that confirms `BatchSpanProcessor` flushes under sustained load (no dropped spans in the tail).

---

## §6 Verification

### §6.1 Per-server smoke commands

```bash
# tuiboard
cd "C:/Users/mathe/code_space/apps/kanban/tuiboard"
OTEL_ENABLED=true LANGSMITH_API_KEY=$LS_KEY LANGFUSE_PUBLIC_KEY=$LF_PK LANGFUSE_SECRET_KEY=$LF_SK \
  bun ./bin/tuiboard-mcp.ts < /tmp/board-list-request.json
# expected: 1 span in LangSmith (project=ikigai, service=tuiboard)
# expected: 1 span in Langfuse (project=ikigai, service=tuiboard)

# taskdog
cd "C:/Users/mathe/code_space/apps/dev-tools/taskdog"
OTEL_ENABLED=true LANGSMITH_API_KEY=$LS_KEY LANGFUSE_PUBLIC_KEY=$LF_PK LANGFUSE_SECRET_KEY=$LF_SK \
  uv run taskdog-mcp < /tmp/taskdog-list-request.json
# expected: 1 span in LangSmith (project=ikigai, service=taskdog.mcp)
# expected: 1 span in Langfuse (project=ikigai, service=taskdog.mcp)

# solverforge
cd "C:/Users/mathe/code_space/apps/calendar/solverforge-calendar"
OTEL_ENABLED=true LANGSMITH_API_KEY=$LS_KEY LANGFUSE_PUBLIC_KEY=$LF_PK LANGFUSE_SECRET_KEY=$LF_SK \
  cargo run --bin solverforge-calendar-mcp --release < /tmp/calendars-list-request.json
# expected: 1 span in LangSmith (project=ikigai, service=solverforge-calendar)
# expected: 1 span in Langfuse (project=ikigai, service=solverforge-calendar)
```

### §6.2 CI gates (per repo)

- **tuiboard:** add `bun test` step to existing CI — already covers `init.test.ts`. Add a separate `bun test src/v3/observability/` step gated on the observability subdirectory.
- **taskdog:** `uv run pytest packages/taskdog-mcp/tests/` — the merge commit `600c92b9` already updated `uv.lock` with OTel test deps.
- **solverforge:** `cargo test --bin solverforge-calendar-mcp` — extend `src/observability.rs` tests (currently 2 cases at lines 99-139) with an `init_with_both_keys_returns_true` case.

### §6.3 End-to-end gate

Run `pav smoke observability` (per `02-integration-smoke-test.md`). The smoke test must report PASS with span counts:

```
server        LangSmith  Langfuse  delta
ikigai         N          N         0%
tuiboard       ≥1         ≥1        0%
taskdog        ≥1         ≥1        0%
solverforge    ≥1         ≥1        0%
```

Any delta > ±5 % fails the gate and triggers the dual-export parity alert from `05-dashboard-design.md` §3 row 4.

---

## §7 Open Questions

1. **API key topology** (§4.2) — confirmed per-server keys; needs the `.env.example` update in IKIGAI to list all 4 server keypairs. Owner TBD.
2. **`feat/solverforge-otel-wip` branch** — checked out locally, never merged. Is this a continuation of the OTel work that should replace `feat/otel-tracing`, or stale? Owner TBD before any solverforge merge.
3. **Cardinality budget per server** — IKIGAI budgets 200 chars per arg; the 3 externals should match, but `solverforge-calendar-mcp.rs` events_create has 11 fields. Truncation policy is in IKIGAI's `error_capture.py:58` but not yet ported to the 3 externals' tool wrappers.
4. **Coordination with C5 OTel drift counter** — spec 05 §8 references "C5 drift detector"; the `drift_detector.py` exists at `life-ops/ikigai/.claude/worktrees/data-model-unification/life-ops/ikigai/src/ikigai/adapters/drift_detector.py`. Once the 3 externals emit spans, the drift detector needs an updated rule to count `service.name IN {tuiboard, taskdog.mcp, solverforge-calendar}` as "expected services present" — currently it likely only checks for `ikigai-maintainer`. This is a downstream change to be tracked in a follow-up spec.
5. **Spec path inconsistency** — observability specs 01-04 live in `life-ops/ikigai/docs/observability/`; spec 05 lives in `code-docs/observability/`. This doc (06) follows the path the parent task specified. Worth normalizing post-merge — defer to follow-up.
6. **Build time impact** — solverforge OTel deps add ~30 s to `cargo build --release` because of the `opentelemetry-otlp` + `tracing-opentelemetry` + `reqwest` chain. Mitigation is a Cargo feature flag (mentioned in §3.3) — needs a decision before merge.
7. **The `lansmith` typo** — taskdog `observability.py:87` has the wrong endpoint host. This is a one-line fix but it's a regression introduced by the merged branch. The fix should land in a follow-up commit BEFORE the smoke test runs, otherwise D1.4 will fire a false-positive dual-export parity alert.

---

## §8 Cross-references

- **This doc:** `code-docs/observability/06-external-mcp-otel-plan.md`
- **Sibling specs (current path):** `code-docs/observability/05-dashboard-design.md`
- **Sibling specs (legacy path):** `life-ops/ikigai/docs/observability/01-server-side-reliability.md`, `02-integration-smoke-test.md`, `03-merge-plan.md`, `04-dissolve-worktree.md`
- **IKIGAI OTel init (reference):** `life-ops/ikigai/src/observability/otel_init.py` + `error_capture.py`
- **Server-specific OTel modules (target files):**
  - `apps/kanban/tuiboard/src/v3/observability/init.ts` + `init.test.ts`
  - `apps/dev-tools/taskdog/packages/taskdog-mcp/src/taskdog_mcp/observability.py` + `main.py`
  - `apps/calendar/solverforge-calendar/src/observability.rs` + `src/bin/solverforge-calendar-mcp.rs`
- **Server entry points to update with `initObservability()` / `shutdownObservability()`:**
  - `apps/kanban/tuiboard/src/v3/mcp/server.ts:165` (top of `main()`)
  - `apps/dev-tools/taskdog/packages/taskdog-mcp/src/taskdog_mcp/main.py:14` (already calls `init_observability()`; needs `shutdown_observability()` on exit)
  - `apps/calendar/solverforge-calendar/src/bin/solverforge-calendar-mcp.rs:879` (already calls `init_observability()`; needs shutdown hook)
- **Drift counter downstream:** `life-ops/ikigai/.claude/worktrees/data-model-unification/life-ops/ikigai/src/ikigai/adapters/drift_detector.py`
- **Master diagnostic** §4 (referenced in task brief) is the source of the "blind to ~90 % of execution" claim. Not located in this tree — assumed to live in user notes.

---

## §9 Summary Table

| Server | Branch | Effort | Risk | Reversibility | Block on |
|---|---|---|---|---|---|
| taskdog | already merged (`d6bebc2d`) | ~1.5 h (endpoint fix + verify) | low | high | `lansmith` → `langsmith` typo fix at `observability.py:87` |
| tuiboard | open (`2c39867`) | ~1.5 h (init wiring + verify) | low | high | spec 02 smoke gate |
| solverforge | open (`3243296`) + WIP (`feat/solverforge-otel-wip`) | ~4-6 h (real code work) | medium | medium | crate version linkage check + `observability.rs` SDK init completion |