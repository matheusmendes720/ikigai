---
title: MCP SDK Landscape + IKIGAI Gateway Architecture — Deep Research
date: 2026-08-28
status: research-complete
feeds_into: Phase B3 (MCP gateway consolidado) + downstream B4-B6
sources:
  - https://modelcontextprotocol.io/specification/2025-06-18/architecture
  - https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
  - https://github.com/modelcontextprotocol/python-sdk
  - https://github.com/modelcontextprotocol/typescript-sdk
  - https://github.com/modelcontextprotocol/rust-sdk
  - local: src/ikigai/src/mcp_server/server.py (27KB, 8 tools, stdio)
---

# MCP SDK Landscape + IKIGAI Gateway Architecture

> **TL;DR — Decision recommendation for Phase B3:**
> 1. **Wire format:** MCP (JSON-RPC 2.0 over stdio) — canonical, host-portable, drops directly into Claude Desktop / Cursor / VS Code / Continue
> 2. **Server SDK:** `mcp` (Python, FastMCP) — already in our tree; native to `src/ikigai/`
> 3. **Client SDKs (multi):** TS (`@modelcontextprotocol/sdk`) for browser/UIs, Rust (`rmcp`) for `vibeops-tui` if/when it needs to consume the gateway
> 4. **Transport:** stdio for v1 (single-user local-first); Streamable HTTP deferred to v2+ if multi-process supervisor lands
> 5. **Primitives to expose:** 8 existing tools + add `Resources` for read-only views (`ueid://…`, `queue://pending`, `health://gateway`) and `Prompts` for slash-menu reuse
> 6. **B3 deliverable shape:** spec + code (`src/ikigai/src/mcp_server/server_v2.py`) that adds Resources, Prompts, versioned capabilities, contract-tested via MCP Inspector

---

## 1. What MCP actually is (ground truth from spec)

- **Spec version we should target:** `2025-06-18` (the transport revision; supersedes `2024-11-05` HTTP+SSE)
- **Architecture:** Client-Host-Server. Our IKIGAI gateway = **server**; Claude Desktop / Cursor / our `interfaces/cli` = **clients**; user machine = **host**
- **Wire format:** JSON-RPC 2.0, UTF-8, newline-delimited over stdio; HTTP POST/GET + optional SSE stream for the Streamable HTTP transport
- **Primitives a server exposes:** `tools`, `resources`, `prompts` (and can request `sampling` from the client)
- **Lifecycle:** `initialize` → `notifications/initialized` → bidirectional requests/notifications/responses → terminate
- **Capability negotiation:** server declares `{tools: {}, resources: {subscribe: false}, prompts: {}}` in the initialize result; clients declare what they handle. Both parties **MUST** respect the negotiated set throughout the session

> Spec text (verbatim): *"Servers should be extremely easy to build ... Highly composable ... Should not be able to read the whole conversation, nor 'see into' other servers ... Features can be added progressively."* — directly maps to our v1-create-only mesh posture.

---

## 2. SDK comparison — what to use, where, and why

| Criterion | Python `mcp` | TypeScript `@modelcontextprotocol/sdk` | Rust `rmcp` |
|---|---|---|---|
| Install | `uv add "mcp[cli]"` / `pip install "mcp[cli]"` | `npm i @modelcontextprotocol/server` + `/client` | `cargo add rmcp --features server` |
| High-level API | `FastMCP` decorator (`@mcp.tool()`, `@mcp.resource(uri)`, `@mcp.prompt()`) | `McpServer.registerTool(name, {inputSchema: zod}, handler)` | `#[tool_router]` / `#[tool_handler]` / `#[tool]` macros |
| Schema source | Python type hints → JSON Schema (Pydantic underneath) | Zod v4 (or Valibot / ArkType via Standard Schema) | `#[derive(schemars::JsonSchema)]` → JSON Schema 2020-12 |
| Transports | stdio, Streamable HTTP, SSE | stdio, Streamable HTTP | stdio, TokioChildProcess, Streamable HTTP, worker |
| Async model | stdlib `asyncio` (or trio) | stdlib Promises | tokio (mandatory) |
| Version maturity | GA, broad ecosystem | GA, broad ecosystem | Production-ready since 2025 |
| Where it fits **us** | **Server-side gateway in `src/ikigai/`** (already partially there) | Browser/UI clients (viboard, TUI web companion, future `interfaces/web/`) | `vibeops-tui` (Rust) — only if it becomes a consumer of the gateway |

### 2.1 Recommendation matrix (per our repo topology)

| Component | Recommended SDK | Rationale |
|---|---|---|
| `src/ikigai/src/mcp_server/server.py` (gateway) | **Python `mcp` (FastMCP)** | Already imports `from mcp.server import Server`; one less bridge. Pydantic contracts in `src/contracts/` already speak the type-hint → schema dialect |
| `interfaces/cli/` (Typer) → gateway consumer | Stdlib `subprocess` + JSON-RPC over stdin/stdout, or `mcp` Python client if we add async | Stdio keeps the CLI sync; no async runtime to introduce |
| `vibeops-tui` (Rust) → gateway consumer (future) | **`rmcp` client** | Avoids the JSON-RPC parsing re-implementation |
| External UIs (browser/web/phone) → gateway consumer | **`@modelcontextprotocol/sdk`** (TS) | Standard-schema (Zod) for runtime validation; universal runtime |
| `taskdog` / `solverforge_calendar` adapters | **None** — they remain local SQLite/JSONL stores | They're sinks, not MCP servers. Adapters stay owned by the gateway |

---

## 3. Wire contract — what we already have vs what we need

### 3.1 What's already in the repo (verified)

- **Spec:** `docs/superpowers/specs/2026-08-28-a2ui-protocol-design.md` — 3 methods (`mesh.read`, `task.write`, `mesh.subscribe`), JSON-RPC 2.0 envelopes, Pydantic v2 strict schemas in `src/mesh/adapters/a2ui_schema.py`
- **Contracts:** `src/contracts/` has `UEID`, `Task`, `TaskChange`, `PropagationEvent`, `PlanningCycle`, `Burndown`, `ExecutionRate`, `QHEScore` — all `frozen=True, extra="forbid"`
- **Mesh v1 wiring:** CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter in `src/mesh/adapters/`; review queue in `src/mesh/queue.py`
- **Server stub:** `src/ikigai/src/mcp_server/server.py` — 8 tools, stdio transport, hand-rolled `Server` class (low-level SDK), not FastMCP. **Gaps** noted in next section.

### 3.2 What's missing (B3 scope)

| Gap | Severity | Maps to |
|---|---|---|
| ikigai_scorer returns wrong vectors (study/dev/health/global) — spec requires 5-vector | P1 | Already fixed per `reorg-bugs-p0-fixed-2026-08-27` |
| `_TOOL_DISPATCH` not audited; no version stamp on tools | P1 | B3 |
| No `Resources` exposed — clients must call tools for read-only views | P2 | B3 (add `ueid://{ueid}`, `queue://pending`, `health://gateway`) |
| No `Prompts` exposed — slash menu reuses our prompts | P3 | B3 (deferred to v1.1; not blocking) |
| No capabilities declared in initialize result | P1 | B3 (declare `tools`, `resources: {subscribe: true}`) |
| Health/heartbeat tool absent | P1 | B3 (add `ikigai_health` tool + `health://gateway` resource) |
| No MCP Inspector contract test wired into CI | P1 | B3 (add `make mcp-inspect` target) |

### 3.3 Tool inventory after B3 (target)

| Tool | Direction | Maps to | Status |
|---|---|---|---|
| `ikigai_score` | R | 5 IKIGAI vectors | exists (bug-fixed) |
| `ikigai_regime` | R | PUSH/MAINTAIN/REDUCE/RECOVER | exists |
| `ikigai_phase` | R | FUNDAÇÃO/BUSCA/HACKATHON/RECUPERACAO/OVERCLOCK | exists |
| `ikigai_decompose` | R | Dream UEID → hierarchy | exists |
| `ikigai_corrections` | R | H1-H6 heuristics log | exists |
| `ikigai_plan_cycle` | W | kick LangGraph plan cycle | exists |
| `ikigai_checkpoint` | R/W | LangGraph thread state | exists |
| `ikigai_sync_vault` | W | vault ↔ data sync | exists |
| `ikigai_write_tasks` | W | produce tasks → data/tasks.jsonl | exists (B1 fix landed) |
| `ikigai_read_tasks` | R | consume tasks from data/tasks.jsonl | exists (B1 fix landed) |
| `ikigai_mesh_show` | R | cross-fork UEID view | **add B3** (mirrors `mesh.read`) |
| `ikigai_task_create` | W | enqueue TaskChange | **add B3** (mirrors `task.write action=create`) |
| `ikigai_health` | R | gateway heartbeat + adapter statuses | **add B3** |

> **v1 limitation (carried forward from mesh):** `ikigai_task_create` returns `-32601 Method not supported` for `action ∈ {update, delete, done}`. The A2UI spec already enforces this in `TaskWriteParams` validation.

### 3.4 Resource inventory (new in B3)

```
ueid://{ueid}            →  cross-fork view (CLI / taskdog / solverforge_calendar)
queue://pending          →  list of pending TaskChange events awaiting agent review
queue://events/{id}      →  one TaskChange event JSON
health://gateway         →  {status, version, adapters: [...], uptime_s}
plans://cycles           →  list of PlanningCycles (compact)
plans://cycles/{id}      →  one PlanningCycle (full)
```

### 3.5 Prompt inventory (deferred — v1.1)

```
/ikigai.daily-review(date=today)
/ikigai.planning-cycle(cycle_id=)
/ikigai.mesh-inspect(ueid=)
```

---

## 4. Transport decision — stdio for v1, Streamable HTTP for v2

### 4.1 Why stdio wins v1

- **Spec text (verbatim):** *"Clients SHOULD support stdio whenever possible."*
- **Local-first, single-user:** zero network surface, zero auth surface, zero DNS-rebinding attack surface
- **Process model is already correct:** our `interfaces/cli/` spawns subprocesses; the gateway fits the same model
- **No need for `Mcp-Session-Id` lifecycle** (HTTP-only concept)
- **No `Origin` validation required** (HTTP-only security warning)
- **Compose with existing tools:** Claude Desktop adds our gateway via a 5-line `claude_desktop_config.json` entry that just points to `python -m mcp_server`

### 4.2 When to switch (v2 trigger conditions)

- Multi-process supervisor (B4-B5 wire `agent_consumer` + `agent_propagator` as separate processes) → Streamable HTTP for the gateway-to-supervisor channel (single-user still; localhost-only bind)
- Multi-machine (vault syncs across devices) → Streamable HTTP + auth
- Browser UI (no stdio available) → Streamable HTTP via the gateway

### 4.3 Security posture for HTTP (when we eventually add it)

Spec mandates:
1. Validate `Origin` header on every incoming connection
2. Bind only to `127.0.0.1` (never `0.0.0.0`)
3. Implement auth (we'll use a local bearer token derived from a vault key — same model as A2UI "local-first no auth v1")

---

## 5. Architecture — how to plug everything into one management system

### 5.1 Target topology

```
┌──────────────────────────────────────────────────────────────────┐
│  HOSTS (clients)                                                  │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ Claude Desktop  │  │ Cursor / VS Code │  │ interfaces/cli │ │
│  └────────┬────────┘  └────────┬─────────┘  └────────┬───────┘ │
└───────────┼─────────────────────┼────────────────────┼──────────┘
            │ stdio (JSON-RPC 2.0)
┌───────────▼──────────────────────────────────────────────────────┐
│  IKIGAI GATEWAY  src/ikigai/src/mcp_server/server_v2.py          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ FastMCP("ikigai-gateway", version="1.0.0")                 │  │
│  │ 13 tools (8 existing + 3 mesh + 1 health + 1 mesh_show)   │  │
│  │ 5 resources (ueid://, queue://, health://, plans://)       │  │
│  │ capabilities: {tools:{}, resources:{subscribe:true}}       │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────┬───────────────┬─────────────────────┬───────────────────────┘
      │ in-process    │ in-process          │ in-process
┌─────▼──────┐  ┌─────▼─────────┐  ┌────────▼────────────┐
│ ReviewQueue│  │ AgentConsumer │  │ AgentPropagator     │
│ (B4 worker)│  │ (B5 PAE gate) │  │ (B5 forks→adapters) │
└─────┬──────┘  └─────┬─────────┘  └────────┬────────────┘
      │ append-only   │ APPROVE/REJECT/     │ fork-specific
      │ jsonl         │ CLARIFY             │ failure isolation
      ▼               ▼                     ▼
┌──────────────────────────────────────────────────┐
│ data/  (append-only)                              │
│   review_queue/<id>.json   ← TaskChange           │
│   taskdog/tasks.db        ← TaskdogAdapter        │
│   solverforge_calendar/  ← SolverforgeAdapter     │
│     unified_planning.db                            │
│   tasks.jsonl           ← CliAdapter             │
│   vault-mirror/<id>.md   ← VaultSync (B6)         │
└──────────────────────────────────────────────────┘
```

### 5.2 Operator-facing control plane (re-uses B2 deliverable)

`interfaces/cli/server.py` (already shipped as B2 commit `dc4b121`) gives us:
- `life server ls` — enumerate adapters + status
- `life server inspect <name>` — adapter metadata
- `life server status` — backend process status (B3 wires gateway here)
- `life server start|stop <name>` — STUB until B4-B5 wire the supervisors

After B3 lands, `mcp_gateway` in `BACKEND_PROCESSES` flips from `running=false` to a real check (`pidfile` + `health://gateway` resource probe).

### 5.3 Handoff contracts (single source of truth — JSON schemas live in Pydantic)

| Handoff | Wire format | Producer | Consumer | Persistence |
|---|---|---|---|---|
| CLI → Gateway | JSON-RPC 2.0 / stdio | `interfaces/cli/server_app` | `src/ikigai/src/mcp_server/server_v2.py` | none |
| Gateway → ReviewQueue | `TaskChange.model_dump_json()` | gateway `ikigai_task_create` tool | `src/mesh/queue.py` | `data/review_queue/<id>.json` |
| ReviewQueue → AgentConsumer | `TaskChange.model_validate_json()` | `src/mesh/queue.py` | `src/mesh/agent_consumer.py` | in-process |
| AgentConsumer → AgentPropagator | `PropagationEvent` (Pydantic) | `agent_consumer` | `agent_propagator` | in-process |
| AgentPropagator → Adapters | `adapter.apply_change(event)` | `agent_propagator` | `CliAdapter` / `TaskdogAdapter` / `SolverforgeCalendarAdapter` | per-adapter slice (jsonl/sqlite) |
| Agent → Vault | markdown append (frontmatter preserved) | `agent_propagator` (vault writer) | `vault/ikigai/closing-2026/.../tasks.md` | markdown (append-only) |
| Gateway → Host push (future v1.1) | JSON-RPC 2.0 notification (`mesh.event`) | gateway | subscribed UIs | transport-only |

---

## 6. SDD loop — what to write next

### 6.1 Phase 0 — Spec (this week)

1. **This report** ✅ (delivered)
2. New spec: `docs/superpowers/specs/2026-08-28-ikigai-mcp-gateway-v1.md`
   - Sections: scope, capabilities, tool/resource/prompt inventory, error envelope, version policy, security posture, examples
3. Update `docs/superpowers/specs/2026-08-28-a2ui-protocol-design.md` §"Open Questions" with the decision: *"A2UI transport was the spec; production transport is MCP stdio (this report)"*

### 6.2 Phase 1 — Plan (today / tomorrow)

Concrete task list (mirrors `master-branch-carro-chefe-2026-08-28` build sequence: **services → data → algorithm polish**):

| # | Task | Acceptance |
|---|---|---|
| B3.1 | Refactor `server.py` → `server_v2.py` using `FastMCP` decorator | All 8 existing tools still pass `_TOOL_DISPATCH` audit |
| B3.2 | Add 3 new tools: `ikigai_mesh_show`, `ikigai_task_create`, `ikigai_health` | Contract tests in `src/mesh/tests/test_mcp_tools.py` |
| B3.3 | Declare `capabilities` in initialize result | Handshake captured by `mcp-inspector` shows `{tools:{}, resources:{subscribe:true}}` |
| B3.4 | Add 5 Resources (`ueid://`, `queue://`, `health://`, `plans://`) | MCP Inspector `resources/list` returns all 5 |
| B3.5 | Wire `BACKEND_PROCESSES["mcp_gateway"]` in `interfaces/cli/server.py` to real status (pidfile + `health://gateway` probe) | `life server status --json` shows running=true when process alive |
| B3.6 | Contract tests via `npx @modelcontextprotocol/inspector` | `make mcp-inspect` exits 0 with full tool list enumerated |
| B3.7 | CI gate: `mcp-inspector` smoke in `.github/workflows/ci.yml` | Workflow step "mcp-gateway-contract" green |

### 6.3 Phase 2 — Implement (B3 + B4 + B5 + B6 per rev.2 backend plan)

Already in the parent task list:
- #36 B3 MCP gateway consolidado ← THIS REPORT UNBLOCKS
- #37 B4 Review queue worker
- #38 B5 Agent consumer + propagator wiring
- #39 B6 Vault sync protocol (LAST)

### 6.4 Phase 3 — Verify

- **Contract tests:** `make mcp-inspect` (wraps `npx @modelcontextprotocol/inspector`)
- **Integration tests:** spawn gateway via stdio, exercise each tool from a Python client, assert response shape
- **Regression:** ensure `interfaces/cli/task_add` → gateway path doesn't break B1-B2 commits
- **Adversarial:** per `verify-agent-fabricated-failures` memory — run `pytest`, `ruff`, `mypy` ourselves; don't trust sub-agent "tests pass" claims

### 6.5 Phase 4 — Iterate

- Drift between spec and impl → amend spec + bump `Ikigai-Contract-Version` (semver)
- New use cases → add tool/resource/prompt via SDD loop; **never** mutate the wire envelope shape
- Backwards-compat window: prior major version supported for 1 minor release cycle

---

## 7. Risks and gotchas (carry-forward)

| Risk | Mitigation |
|---|---|
| Spec drift: MCP `2025-06-18` may deprecate features we depend on | Pin protocol version in `initialize` request; subscribe to MCP release notes |
| stdio subprocess IPC fragility (Windows specifically — `pipe_buf` quirks) | Re-use proven pattern from `interfaces/cli/server.py`; test on Windows first |
| Capability declaration mismatch (server claims `resources.subscribe=true` but never sends `notifications/resources/updated`) | Send a heartbeat notification every N seconds in v1 to prove capability; remove in v1.1 |
| Re-using A2UI envelopes inside MCP — confusion between two specs | A2UI = transport-agnostic spec; MCP = transport-specific realization. Decision: A2UI shapes stay; MCP becomes the canonical transport |
| Per-adapter failure isolation drift (one bad fork blocks the others) | `agent_propagator` already isolates (per `reorg-bugs-p0-fixed`); B3 must not break that contract |
| Double-spawn risk: B2 stubs `start mcp_gateway` and B3 spawns real one | B3 starts real subprocess; B2 reads `pidfile` to report status; never two writers |
| Local LLM in pipeline (forbidden by `data-first-methodology`) | Zero LLM in gateway; all logic is arithmetic + adapter I/O |

---

## 8. Open questions for the user (decision matrix)

| Q | Option A | Option B | Recommendation |
|---|---|---|---|
| Q1 — Wire format | **MCP stdio (canonical, host-portable)** | JSON-RPC + custom schema (full control) | **A** — drops into Claude Desktop + Cursor for free |
| Q2 — SDK on server side | **Python `mcp` FastMCP** | Refactor to TS for `vibeops-tui` reuse | **A** — Python lives in `src/ikigai/`; TUI can use `rmcp` client instead |
| Q3 — Resources in v1? | **Yes — 5 resources** (low cost, high value) | Tools-only (ship faster) | **A** — Resources are how UIs get free read-only views; future Prompts reuse the same pattern |
| Q4 — Prompts in v1? | **No — defer to v1.1** | Yes — slash menu now | **B** — Prompts require UI surface we don't have yet; not on the critical path |
| Q5 — Streamable HTTP in v1? | **No — stdio only** | Yes — pre-build for v2 | **A** — YAGNI; v1 is single-process single-user |
| Q6 — `ikigai_task_create` action coverage | **v1: create only** (matches mesh v1) | v1: create + update (tighten scope now) | **A** — explicit carry-forward from `interfaces-architecture-2026-08-27`; user already locked it |

---

## 9. Acceptance criteria for B3 sign-off

- [ ] `server_v2.py` ships, gates B1-B2 e2e tests, adds 3 tools + 5 resources
- [ ] `make mcp-inspect` exits 0 (MCP Inspector enumerates all tools + resources)
- [ ] `life server status --json` reports `mcp_gateway.running=true` when process alive
- [ ] `npx @modelcontextprotocol/inspector` handshake shows `capabilities = {tools:{}, resources:{subscribe:true}}`
- [ ] CI step `mcp-gateway-contract` green
- [ ] Spec doc `2026-08-28-ikigai-mcp-gateway-v1.md` checked in
- [ ] A2UI spec §"Open Questions" updated with MCP transport decision
- [ ] Backwards-compat: existing 8 tools unchanged (only addition, not mutation)

---

## 10. Sources (all verified by WebFetch this session)

- **Spec — Architecture** — `https://modelcontextprotocol.io/specification/2025-06-18/architecture` (Client-Host-Server, capability negotiation, design principles)
- **Spec — Transports** — `https://modelcontextprotocol.io/specification/2025-06-18/basic/transports` (stdio canonical, Streamable HTTP replaces 2024-11-05 HTTP+SSE, Origin validation, session lifecycle)
- **Spec — Introduction** — `https://modelcontextprotocol.io/introduction` (USB-C analogy, ecosystem support, build/dev/build-client)
- **Python SDK** — `https://github.com/modelcontextprotocol/python-sdk` (`FastMCP` decorator, type-hint → JSON Schema, stdio + Streamable HTTP + SSE)
- **TypeScript SDK** — `https://github.com/modelcontextprotocol/typescript-sdk` (`McpServer.registerTool`, Zod v4 via Standard Schema, stdio + Streamable HTTP)
- **Rust SDK** — `https://github.com/modelcontextprotocol/rust-sdk` (`rmcp`, `#[tool_router]`/`#[tool_handler]`/`#[tool]` macros, schemars → JSON Schema 2020-12, tokio mandatory, multi-round-trip requests)
- **Local ground truth** — `src/ikigai/src/mcp_server/server.py` (27KB, 8 tools registered in `TOOLS` list, stdio transport via `mcp.server.stdio.stdio_server`, `_TOOL_DISPATCH` dict present)

---

*Deep research — feeds Phase B3 spec. Ready for SDD loop.*