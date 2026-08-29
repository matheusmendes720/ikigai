# A2UI Protocol — Agent-to-UI Standard Protocol — Design Spec

**Date:** 2026-08-28
**Phase:** B1 of `2026-08-28-backend-phase-reordering`
**Status:** Design — pending spec self-review + user approval before any implementation
**Inputs:**
- Phase A foundation: `interfaces/cli` + `src/mesh/adapters/` (commit bff5455)
- Master branch architecture: `memory/master-branch-carro-chefe-2026-08-28.md`
- CLI command-palette pivot: `memory/cli-command-palette-pivot-2026-08-28.md`
- Phase 3 data mesh design: `docs/superpowers/specs/2026-08-28-phase3-data-mesh-design.md`

---

## 1. Scope

**A2UI** is a wire-protocol standard that any UI client can implement against to consume and produce IKIGAI domain events through the data mesh. It is **not** a concrete UI (chat, TUI, web dashboard); it is the contract that any of those UIs must speak.

**Goal:** decouple IKIGAI's agent + data layer from the UI surface, so UIs can be replaced without touching the kernel.

**Out of scope (this spec):**
- Any reference implementation of `A2uiAdapter` class (deferred per user decision 2026-08-28)
- Concrete UIs (chat, TUI, web, mobile)
- Authentication for remote clients (out-of-scope: single-user local-first; deferred for v1.1)
- Bidirectional vault sync protocol (Phase B6, separate spec)

---

## 2. Design Decisions

### D1. JSON-RPC 2.0 over stdio as canonical transport

- **Transport:** newline-delimited JSON over stdin/stdout (stdio). Each line is one JSON-RPC 2.0 message.
- **Why:** Matches MCP (Model Context Protocol) semantics; works with any subprocess-based UI; zero network setup; works offline.
- **Alt transports (future):** HTTP+SSE for browser clients, WebSocket for persistent web UIs. Spec is transport-agnostic — only the envelope is JSON-RPC.

### D2. Bidirectional, event-driven

- UI sends **requests** (read, write, subscribe).
- Server (IKIGAI gateway) sends **responses** (success/error) and **notifications** (push events from queue).
- This mirrors MCP's request/response + notification split.

### D3. Three top-level methods

| Method | Direction | Purpose |
|---|---|---|
| `mesh.read` | UI → server | Cross-fork view for one UEID (joins CliAdapter + TaskdogAdapter + SolverforgeCalendarAdapter + A2uiAdapter) |
| `task.write` | UI → server | Emit a `TaskChange` (create/update/delete/done) to `data/review_queue/<id>.json`. Returns event_id immediately; agent processes async. |
| `mesh.subscribe` | UI → server | Open a notification stream of new events (server pushes as they arrive in review queue). |

### D4. UEID is the join key

All task references use UEID (`^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`). Same UEID is canonical across forks. New `a2ui:` fork-prefix reserved for A2UI client-side slices (when implementations exist).

### D5. Pydantic v2 strict schemas

All message types are Pydantic v2 strict (`frozen=True`, `extra="forbid"`). Schemas live in `src/mesh/adapters/a2ui_schema.py`.

### D6. Local-first, no auth (v1)

stdio transport assumes the client is a child process of the gateway. No tokens, no TLS. v1.1 may add bearer-token auth for HTTP transport.

### D7. Append-only invariant preserved

UIs never write directly to vault or to fork slices. Writes flow through `task.write` → review queue → agent validation → fork propagation. UIs can only READ fork slices (via `mesh.read`).

---

## 3. Wire Protocol

### 3.1 Request envelope (UI → server)

```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "method": "mesh.read",
  "params": { "ueid": "tsk:fix-typo:7f3a-...:9c1b..." }
}
```

### 3.2 Response envelope (server → UI, success)

```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "result": {
    "ueid": "tsk:fix-typo:7f3a-...:9c1b...",
    "view": {
      "cli": {"title": "Fix typo", "priority": "high", "source_fork": "interfaces/cli"},
      "taskdog": {"name": "Fix typo", "status": "pending"},
      "solverforge_calendar": null,
      "a2ui": null
    },
    "mismatches": []
  }
}
```

### 3.3 Response envelope (server → UI, error)

```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "error": {"code": -32602, "message": "Invalid UEID format", "data": {"ueid": "bad-input"}}
}
```

Standard JSON-RPC error codes:
- `-32700` Parse error (invalid JSON)
- `-32600` Invalid Request (missing jsonrpc/method)
- `-32601` Method not found
- `-32602` Invalid params (e.g. malformed UEID)
- `-32603` Internal error

### 3.4 Notification envelope (server → UI, push)

```json
{
  "jsonrpc": "2.0",
  "method": "mesh.event",
  "params": {
    "event_id": "evt_a1b2c3",
    "ueid": "tsk:fix-typo:...",
    "action": "create",
    "status": "pending",
    "source_fork": "interfaces/cli"
  }
}
```

Notifications have NO `id` field. Server pushes these as new events land in the review queue (Layer 4 agent consumer publishes them).

---

## 4. Method Specifications

### 4.1 `mesh.read`

**Params:** `{ "ueid": str }`
**Result:** `{ "ueid": str, "view": dict[str, dict | None], "mismatches": list[str] }`
- `view` keys: `cli`, `taskdog`, `solverforge_calendar`, `a2ui`
- Each value is the fork's record, or `null` if not present
- `mismatches` lists any inconsistencies (e.g. status differs across forks)

**Errors:**
- `-32602` Invalid UEID
- `-32603` Adapter failure (one or more forks unreachable; partial result still returned if possible)

### 4.2 `task.write`

**Params:** `{ "action": "create"|"update"|"delete"|"done", "ueid": str, "fields": dict, "source_fork": str }`
**Result:** `{ "event_id": str, "status": "pending" }`

`fields` content depends on action:
- `create`: `{ "title": str, "due": str | None, "priority": str, ... }`
- `update`: `{ "<field>": <new_value>, ... }`
- `delete`: `{}`
- `done`: `{ "completed_at": str (ISO) }`

**v1 limitation:** only `create` is implemented (per Phase 3 v1 spec D2). Other actions return `-32601` Method not found until v1.2+ ships.

**Errors:**
- `-32602` Invalid params (unknown action, missing required field)
- `-32603` Queue write failure

### 4.3 `mesh.subscribe`

**Params:** `{ "filters": { "actions": list[str] | None, "ueid_prefix": str | None } }`
**Result:** `{ "subscription_id": str }` (returned immediately; subsequent notifications use the same id)

After successful subscription, server sends `mesh.event` notifications as new events land in the review queue.

**Filters:**
- `actions`: only push events with these actions (default: all)
- `ueid_prefix`: only push events for UEIDs starting with this string

**Errors:**
- `-32602` Invalid filter values
- `-32603` Subscription registry unavailable

---

## 5. Schemas (`src/mesh/adapters/a2ui_schema.py`)

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from src.contracts.common import UEID


class A2UIRequest(BaseModel):
    """JSON-RPC 2.0 request envelope."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    jsonrpc: Literal["2.0"] = "2.0"
    id: str = Field(min_length=1, max_length=64)
    method: Literal["mesh.read", "task.write", "mesh.subscribe"]
    params: dict


class A2UIResponse(BaseModel):
    """JSON-RPC 2.0 response envelope."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    jsonrpc: Literal["2.0"] = "2.0"
    id: str = Field(min_length=1, max_length=64)
    result: dict | None = None
    error: A2UIError | None = None


class A2UIError(BaseModel):
    """JSON-RPC 2.0 error object."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    code: int  # -32700 to -32603 (standard JSON-RPC)
    message: str = Field(min_length=1, max_length=512)
    data: dict | None = None


class A2UINotification(BaseModel):
    """JSON-RPC 2.0 server-pushed notification."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    jsonrpc: Literal["2.0"] = "2.0"
    method: Literal["mesh.event"]
    params: dict


class MeshReadParams(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    ueid: UEID


class TaskWriteParams(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    action: Literal["create", "update", "delete", "done"]
    ueid: UEID
    fields: dict
    source_fork: str = Field(min_length=2, max_length=64)


class MeshSubscribeParams(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    filters: dict = Field(default_factory=dict)
```

---

## 6. Transport Bindings

### 6.1 stdio (canonical, v1)

- UI spawns gateway as subprocess
- Stdin: UI writes request JSON lines
- Stdout: server writes response/notification JSON lines
- Stderr: server logs (UI redirects to journal/console)
- Termination: UI closes stdin → server shuts down gracefully

**Realization (resolved 2026-08-28):** the wire envelope and lifecycle
specified in Sections 3 + 6.1 are realized by **Model Context Protocol (MCP)
over stdio**, protocol version `2025-06-18`. MCP's primitives map onto
A2UI's three methods:

| A2UI method | MCP primitive |
|---|---|
| `mesh.read` | `tools/call` with tool `ikigai_mesh_show` (or `resources/read` for `ueid://{ueid}`) |
| `task.write` | `tools/call` with tool `ikigai_task_create` |
| `mesh.subscribe` | `resources/subscribe` on `queue://pending` |

The A2UI method names above remain the **logical contract** that UI
authors read; the wire-level method names follow MCP. Both surfaces speak
JSON-RPC 2.0, so the schemas in `src/mesh/adapters/a2ui_schema.py` are
reused as the Pydantic shapes for MCP tool inputs/outputs. See Section 12
for the full binding decision and rationale.

### 6.2 HTTP+SSE (future v1.1)

- `POST /a2ui/v1/rpc` — JSON-RPC request body, response body
- `GET /a2ui/v1/events` — SSE stream of `mesh.event` notifications
- Auth: Bearer token in `Authorization` header (out of scope for v1)

### 6.3 WebSocket (future v1.2)

- `ws://host/a2ui/v1/ws`
- Full-duplex JSON-RPC
- Same auth as HTTP

---

## 7. Versioning

- Wire format versioned via `A2UI-Version: 1` header (stdio) or `A2UI-Version` query param (HTTP).
- Backward compat: additive changes only within v1.x.
- Breaking changes bump to v2.

---

## 8. Security Considerations

- **Local stdio = process boundary is the trust boundary.** UI and server share UID. Acceptable for single-user local-first.
- **Future HTTP transport MUST use TLS** even if auth is minimal.
- **Append-only invariant** is enforced server-side; UI cannot bypass it.

---

## 9. Example Client Pseudocode (NOT IMPLEMENTATION)

```python
# Pseudo-code only — does not exist as code yet
async with subprocess_a2ui_gateway() as gw:
    resp = await gw.request("mesh.read", {"ueid": "tsk:foo:..."})
    if "error" in resp:
        handle_error(resp["error"])
    else:
        render_view(resp["result"]["view"])

    # Subscribe to live events
    await gw.request("mesh.subscribe", {"filters": {"actions": ["create"]}})

    async for notification in gw.notifications():
        if notification["method"] == "mesh.event":
            enqueue_for_ui_render(notification["params"])
```

---

## 10. Open Questions / Future Work

| # | Question | Defer to |
|---|---|---|
| Q1 | HTTP transport auth scheme | v1.1 |
| Q2 | Subscription reconnection / resume tokens | v1.2 |
| Q3 | Compression for large views (chunked response) | v1.3 |
| Q4 | Reference implementation: chat UI consuming A2UI | Phase B6 (vault sync era) |
| Q5 | Reference implementation: TUI dashboard consuming A2UI | After B2 (server-mgmt CLI) |
| Q6 | Federation: multiple IKIGAI instances talking via A2UI | v2.0 |

## 11. Resolved Decisions

| # | Decision | Resolved | Rationale |
|---|---|---|---|
| R1 | **Transport realization:** stdio JSON-RPC 2.0 is realized via **MCP protocol `2025-06-18`** (FastMCP server SDK). A2UI method names (`mesh.read`, `task.write`, `mesh.subscribe`) remain as the **logical contract**; wire-level method names follow MCP primitives (`tools/call`, `resources/subscribe`). | 2026-08-28 (Hybrid option per AskUserQuestion) | MCP gives free host-portability (Claude Desktop, Cursor, VS Code, Continue). Pydantic schemas in `src/mesh/adapters/a2ui_schema.py` are reused as MCP tool input/output shapes. See `docs/research/2026-08-28-mcp-sdk-landscape.md` for SDK/transport decision matrix. |
| R2 | **Server SDK:** Python `mcp` (FastMCP). Implementation: `src/ikigai/src/mcp_server/server_v2.py` (refactor of existing `server.py`). | 2026-08-28 | Already partial in tree; native Pydantic contracts in `src/contracts/`. |
| R3 | **UI client SDKs (multi-language):** Python `mcp` for our CLI bridge; TypeScript `@modelcontextprotocol/sdk` for browser/web UIs (v2); Rust `rmcp` for `vibeops-tui` consumer (v2, when TUI needs IPC). | 2026-08-28 | Per SDK landscape research, each language has a Tier-1 official MCP SDK. |
| R4 | **Resources exposed in v1:** `ueid://{ueid}`, `queue://pending`, `queue://events/{id}`, `health://gateway`, `plans://cycles`, `plans://cycles/{id}`. **Prompts deferred to v1.1.** | 2026-08-28 | Resources give UIs free read-only views; Prompts require UI surface we don't have yet. |

---

## 11. Verification (when implementation lands)

Future verification plan (NOT this phase):
- Unit tests for schema validation (Pydantic roundtrip)
- Integration tests with mock gateway process
- Contract tests: capture real request/response pairs, replay against impl

---

## Spec Self-Review Checklist

- [x] **Placeholder scan:** no TBD/TODO in spec body (Q1-Q6 are explicitly deferred, not stubs)
- [x] **Internal consistency:** D1-D7 align with wire protocol and schemas
- [x] **Scope check:** single deliverable (protocol spec + Pydantic schemas). Implementation deferred.
- [x] **Ambiguity check:** UEID format referenced but not redefined; points to existing `src/contracts/common.py`

---

## User Review Gate

This spec is ready for user review. After approval:
- B1 implementation = spec-only (markdown + Pydantic schemas + tests for schemas)
- No `A2uiAdapter` class yet (user decision 2026-08-28)
- B2 (server-mgmt CLI) can reference the schemas without depending on a runtime adapter