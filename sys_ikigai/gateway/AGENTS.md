# AGENTS.md — `sys_ikigai/gateway`

> Earned its file: score 11/20 — distinct domain (the MCP gateway and its fork clients).
> Parent: `sys_ikigai/AGENTS.md`. Scope: this directory only.

## OVERVIEW

HTTP+SSE front, stdio back. `UnifiedMCPGateway` routes MCP tool calls to downstream fork
servers and streams events out over SSE. Pure stdlib — no FastAPI, no MCP SDK. 10 modules +
`clients/` and `adapters/`, ~1.6k LOC.

## WHERE TO LOOK

| File | Role |
|------|------|
| `gateway.py` | `UnifiedMCPGateway` + `GatewayConfig`. Routes: `POST /call` `{namespace, tool, arguments}`, `GET /health`, `GET /events` (SSE, chunked transfer). Unknown namespace → 404; adapter exception → 502. `register(adapter)` binds a namespace, `publish_event(event, data)` fans out to SSE subscribers. |
| `client_adapter.py` | `MCPClientAdapter` ABC — the only thing the gateway depends on downstream: `call_tool(name, arguments)`. |
| `stdio_adapter.py` | `StdioAdapter` — generic MCP stdio client. Lazy subprocess spawn, `Content-Length`-framed JSON-RPC 2.0, monotonic request ids, single-writer lock per subprocess, stderr ring buffer, hard per-call timeout (subprocess killed on timeout). |
| `stdio_server_base.py` | `StdioServerBase` — hand-rolled JSON-RPC 2.0 **server** with `Content-Length` framing, for exposing local tools over stdio. |
| `event_log.py` | `EventLog` — append-only JSONL mirror of published events. Rotation renames to `<path>.1`; it never deletes events. Thread-safe via a single-writer lock. |
| `clients/` | The 4 live fork client factories (`taskdog`, `solverforge_calendar`, `tuiboard`, `cli`) + `README.md` with the connectivity matrix (binary, default location, wrapper module). |
| `adapters/` | 9 of 10 files are ~12-line **stubs**; only `taskdog_adapter.py` is real (delegates to `src/mesh/adapters/taskdog.py`). |
| `downstream.py` | Backward-compat re-export of the 4 factories from `clients/`. |
| `start_gateway.py` / `client_cli.py` / `event_log_cli.py` | Entry points: server, SSE consumer (NDJSON), event-log reader. |

## CONVENTIONS (deviations from parent)

- **Two CLI frameworks.** `client_cli.py` and `event_log_cli.py` use argparse; the sibling `cli/`
  package uses Typer.
- Published event payloads are sanitized — consumers re-fetch through `/call` when they need the
  full object.

## ANTI-PATTERNS

- **Do not add a dependency to `gateway.py`.** It is stdlib-only on purpose (CI installs neither
  starlette nor fastapi).
- **Never delete from `EventLog`.** Rotation renames files; that is the only eviction path.
- **`gateway/adapters/` is dead weight.** `solverforge-calendar.py` and
  `solverforge-calendar_adapter.py` have hyphens and are **not importable**; the working files
  are `solverforge_calendar_adapter.py` and `taskdog_adapter.py`. Real implementations live in
  `clients/` and `src/mesh/adapters/`.
- Do not use `Path.rename()` for file swaps here — use `os.replace()` (Windows).

## COMMANDS

```bash
python -m sys_ikigai.gateway.start_gateway --host 127.0.0.1 --port 8765
python -m sys_ikigai.gateway.client_cli          # SSE consumer, NDJSON output
python -m sys_ikigai.gateway.event_log_cli tail --json
```
