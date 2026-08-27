# ADR-011 — HTTP+SSE Transport for IKIGAI MCP Server

**Status:** Proposta
**Date:** 2026-08-27
**Deciders:** human (Matheus) + IKIGAI team
**Consulted:** `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` §2 S-H1; `life-ops/ikigai/src/mcp_server/server.py:534`
**Informed:** dcode users, all MCP clients
**Scope:** whether to add HTTP+SSE transport alongside stdio for the IKIGAI MCP server

---

## Status

**Proposta** — recommended for acceptance (Sprint 3, after Sprint 1+2 close). This ADR is the canonical decision record.

---

## Context

The IKIGAI MCP server (`src/mcp_server/server.py:534`) currently exposes transport **stdio only**:

```python
# server.py:534
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
```

This works for some clients (Claude Code, direct stdio) but blocks others:

1. **LangChain deep agents** — need HTTP or SSE to connect programmatically; stdio is awkward
2. **Web-based UIs** — browser cannot speak stdio; need HTTP or WebSocket
3. **Multiple concurrent clients** — stdio is one-client-at-a-time per server process
4. **Long-running observability** — HTTP+SSE allows spans to flow continuously; stdio is request-response
5. **Cross-network access** — HTTP allows remote MCP clients (with auth); stdio is local only

Other MCP servers in the ecosystem (tuiboard, taskdog, solverforge) all use stdio only. solverforge has an HTTP+SSE stub feature-gated but never enabled.

The IKIGAI MCP server exposes 8 tools:
- `ikigai_score`, `ikigai_regime`, `ikigai_phase`, `ikigai_decompose`
- `ikigai_corrections`, `ikigai_plan_cycle`, `ikigai_checkpoint`, `ikigai_sync_vault`

These are read-only and write-state; they have varying observability needs.

---

## Decision

**Recommended:** Add HTTP+SSE transport alongside stdio. Use FastAPI or `starlette` for the HTTP layer; SSE for streaming responses. Keep stdio as the default for backward compatibility.

### Concrete proposal

```python
# server.py — add at top
TRANSPORT = os.getenv("IKIGAI_MCP_TRANSPORT", "stdio")  # stdio | http

# server.py:534 — branch on transport
async def main():
    if TRANSPORT == "http":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        # ... HTTP+SSE setup
    else:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
```

### Default port

`127.0.0.1:3737` (matches solverforge's HTTP feature port; no collision since IKIGAI doesn't run on the same host as solverforge in production).

### Toggle

- `IKIGAI_MCP_TRANSPORT=stdio` (default) → current behavior
- `IKIGAI_MCP_TRANSPORT=http` → HTTP+SSE on port 3737
- `IKIGAI_MCP_PORT=3737` → env-var override

### Auth

For local dev: no auth (bind to 127.0.0.1 only). For prod: bearer token via `IKIGAI_MCP_AUTH_TOKEN` env var. Document in README.

---

## Consequences

### Positive

- **Unblocks LangChain deep agents** to connect to IKIGAI without stdio workaround
- **Enables web UIs** to consume IKIGAI tools (e.g., future IKIGAI web dashboard)
- **Better observability** — SSE allows continuous span streaming instead of request-response
- **Multi-client support** — HTTP can serve multiple concurrent clients
- **Aligns with solverforge** — uses same `127.0.0.1:3737` port convention
- **Backward compatible** — stdio remains default; no breakage for existing clients

### Negative

- **New attack surface** — HTTP transport is network-accessible (mitigated by 127.0.0.1 bind + optional auth)
- **Resource leak risk** — HTTP server needs explicit lifecycle management; stdio lifecycle is process-bound
- **Two code paths to maintain** — stdio and HTTP branches must both work
- **Test coverage doubles** — both transports need integration tests
- **Migration cost** — ~3-5 days for the HTTP layer + 2 days for tests

### Neutral

- **MCP SDK support** — `mcp.server.sse` is stable but newer than stdio_server
- **Documentation** — needs a new section in IKIGAI README + ARCHITECTURE_INDEX.md

---

## Alternatives Considered

### A1 — stdio only (status quo)

**Rejected because.** Blocks deep agent integration, web UI, multi-client. Decision deferred since observability sprint.

### A2 — HTTP+SSE only (drop stdio)

**Rejected because.** Breaks existing stdio clients (Claude Code, dcode). Migration cost high; benefit low.

### A3 — WebSocket transport

**Rejected because.** WebSocket is more complex than SSE for this use case (one-way streaming is sufficient). MCP spec is converging on stdio + SSE.

### A4 — gRPC transport

**Rejected because.** gRPC adds significant tool complexity (protobuf, codegen). HTTP+SSE is the MCP standard.

### A5 — Use solverforge's existing HTTP feature

**Rejected because.** solverforge is calendar-specific; IKIGAI is meta-brain. Different concerns, different tools. Shared port (3737) is fine, shared code is not.

---

## Implementation Rules

1. **Add transport toggle** to `server.py` (env var `IKIGAI_MCP_TRANSPORT`)
2. **Branch on transport** in `main()` — stdio vs HTTP+SSE
3. **HTTP layer** uses FastAPI + `mcp.server.sse.SseServerTransport`
4. **Bind to 127.0.0.1** by default; allow `0.0.0.0` override for prod with auth
5. **Add lifecycle hooks** — graceful shutdown on SIGTERM, in-flight request draining
6. **Add auth middleware** — bearer token check when `IKIGAI_MCP_AUTH_TOKEN` is set
7. **Update tests** — parametrize over both transports
8. **Update docs** — IKIGAI README + ARCHITECTURE_INDEX.md
9. **Verification:**
   ```bash
   IKIGAI_MCP_TRANSPORT=http ikigai.bat mcp
   curl -X POST http://127.0.0.1:3737/sse -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
   # should return 8 tools
   ```

---

## Roll-back Criteria

Reversible until prod deployment. The HTTP path is opt-in via env var; reverting to stdio default is a one-line change.

If 3 months after deployment the user reports "HTTP transport has too many edge cases" or "stdio is sufficient", schedule a re-evaluation. Likely the HTTP path stays for prod, stdio for local dev.

---

## Related Decisions

- **Master diagnostic S-H1:** the source of this ADR
- **Master diagnostic S-C2 (dcode MCP registration):** depends on this — once HTTP+SSE exists, dcode can connect via either transport
- **Observability sprint Spec 03 (merge plan):** the OTel work in 3 external repos converges toward needing HTTP+SSE for span flow
- **`life-ops/ikigai/src/mcp_server/server.py:534`:** the implementation point
- **`life-ops/ikigai/start_mcp_gateway.sh`:** the launcher; needs env-var awareness

---

## Notes

- The solverforge calendar MCP server has an HTTP feature stub (`#[features] http = []`); the convention is `127.0.0.1:3737`. IKIGAI can reuse the same port pattern without collision (different processes, different default hosts).
- HTTP+SSE is the MCP standard for streaming; stdio is the legacy path. Long-term, the project may converge on HTTP+SSE only, but that's out of scope.
- This ADR unblocks the dcode MCP registration (S-C2) and the deep-agents LangGraph integration (already running but via stdio only).

---

*ADR-011 — Proposta (recommended acceptance) — 2026-08-27 — HTTP+SSE transport for IKIGAI MCP*
