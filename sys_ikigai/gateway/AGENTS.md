# sys_ikigai/gateway

Local MCP gateway: HTTP+SSE front, stdlib only. Earns its file: distinct
domain (transport layer), complexity score 11.

## OVERVIEW
`UnifiedMCPGateway` serves `POST /call`, `GET /health` and `GET /events`
(SSE), dispatching to registered `MCPClientAdapter` implementations.

**Serverless scope (ADR-037, 2026-11-01):** the stdio MCP clients
(`taskdog-mcp`, `tuiboard`, `solverforge-calendar`) were PC-only and are not
published. What remains are the **data-mesh** adapters — the CLI fork and the
taskdog SQLite fork — which read files/SQLite directly instead of spawning a
local MCP server process. The canonical agent surface is the MCP transport at
`src/transport/mcp_server.py` (repo root); this gateway is the local
JSON-RPC bridge over the same data layer.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| HTTP/SSE server | `gateway.py` | `GatewayConfig`, default `127.0.0.1:8765` |
| Adapter protocol | `client_adapter.py` | `MCPClientAdapter` |
| Adapter registry | `downstream.py` | `register_default_adapters()` -> `CliAdapter`, `TaskdogAdapter` |
| Event log | `event_log.py` | `EventLog`, append-only |
| Mesh adapters | `adapters/` | `cli_adapter.py`, `taskdog_adapter.py` |
| Operator CLIs | `client_cli.py`, `event_log_cli.py` | `argparse`, `--json` / `--human` |
| Launcher | `start_gateway.py` | `IKIGAI_GATEWAY_HOST`, `IKIGAI_GATEWAY_PORT` |

**Not published (ADR-037):** `clients/`, `stdio_adapter.py`,
`stdio_server_base.py`, `adapters/tuiboard*`, `adapters/solverforge*`.

## CONVENTIONS
- Pure stdlib (`http.server`, `socketserver`, `threading`, `queue`): no
  starlette, no fastapi. JSON-RPC 2.0 is hand-rolled with `Content-Length`
  framing.
- SSE: `/events` holds the connection open, emits `gateway.ready`, then
  heartbeats every 15s. Each subscriber gets a bounded queue; a slow consumer
  loses events rather than stalling the publisher.
- `EventLog` is append-only; rotation renames the active file aside (`.1`,
  `.2`) and keeps the bytes.
- The gateway CLIs use mutually exclusive `--json` / `--human` with TTY
  auto-detection: `--json` wins, else `--human`, else `sys.stdout.isatty()`.
  Piped output is JSON by default.
- `sys_ikigai/gateway/__init__.py` re-exports the full public surface through
  an explicit `__all__`.
- `emit_adapter_call` strips a known namespace prefix from the tool name
  (`taskdog_add` -> `add`) before publishing the SSE event.

## ANTI-PATTERNS
- The gateway has no auth, by decision (localhost-only is sufficient). Bind to
  `127.0.0.1`.
- Do not assume every adapter is implemented: only `taskdog_adapter.py`
  delegates to a real mesh adapter, and taskdog supports only
  `taskdog_list_tasks` and `taskdog_create_task`. The others return stub
  payloads.
- `EventLog` never deletes events — do not add a prune path.
- Do not add starlette/fastapi to this package.
- Never re-introduce a stdio MCP fork client (ADR-037): a fork that needs no
  local server binary is an adapter over `data/`, not a subprocess.
- Never add a new client surface here — the published client boundary is
  `src/transport/`.

## COMMANDS
```bash
python -m sys_ikigai.gateway.start_gateway
python -m sys_ikigai.gateway.client_cli watch --event-filter <name>
python -m sys_ikigai.gateway.event_log_cli tail --n 20
```
