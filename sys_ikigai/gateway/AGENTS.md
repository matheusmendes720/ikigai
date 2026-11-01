# sys_ikigai/gateway

MCP gateway: HTTP+SSE front, stdio back, stdlib only. Earns its file: distinct
domain (transport layer), complexity score 11, 22 importing files.

## OVERVIEW
`UnifiedMCPGateway` serves `POST /call`, `GET /health` and `GET /events`
(SSE), dispatching to registered `MCPClientAdapter` implementations.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| HTTP/SSE server | `gateway.py` | `GatewayConfig`, default `127.0.0.1:8765` |
| Adapter protocol | `client_adapter.py` | `MCPClientAdapter` |
| Spawn an MCP server | `stdio_adapter.py` | `StdioAdapter`, `StdioAdapterConfig` |
| Serve a fork as MCP | `stdio_server_base.py` | binary-mode stdin reader |
| Event log | `event_log.py` | `EventLog`, append-only |
| One factory per fork | `clients/` | `cli`, `taskdog`, `solverforge_calendar`, `tuiboard` |
| MCP-callable fork adapters | `adapters/` | taskdog is real, the rest are stubs |
| Legacy re-export shim | `downstream.py` | forwards to `clients/` |
| Operator CLIs | `client_cli.py`, `event_log_cli.py` | `argparse`, `--json` / `--human` |
| Launcher | `start_gateway.py` | `IKIGAI_GATEWAY_HOST`, `IKIGAI_GATEWAY_PORT` |

## CONVENTIONS
- Pure stdlib (`http.server`, `socketserver`, `threading`, `queue`): no
  starlette, no fastapi. JSON-RPC 2.0 is hand-rolled with `Content-Length`
  framing.
- `stdio_server_base.serve_forever` reads `sys.stdin.buffer` in binary mode —
  text-mode `readline()` hangs on Windows subprocess pipes.
- SSE: `/events` holds the connection open, emits `gateway.ready`, then
  heartbeats every 15s. Each subscriber gets a bounded queue; a slow consumer
  loses events rather than stalling the publisher.
- Client timeouts differ per fork: taskdog 10s, cli/tuiboard 15s,
  solverforge-calendar 60s.
- `EventLog` is append-only; rotation renames the active file aside (`.1`,
  `.2`) and keeps the bytes.
- The gateway CLIs use mutually exclusive `--json` / `--human` with TTY
  auto-detection: `--json` wins, else `--human`, else `sys.stdout.isatty()`.
  Piped output is JSON by default.
- `sys_ikigai/gateway/__init__.py` re-exports the full public surface through
  an explicit `__all__`.

## ANTI-PATTERNS
- The gateway has no auth, by decision (localhost-only is sufficient). Bind to
  `127.0.0.1`.
- Do not assume every adapter is implemented: only
  `adapters/taskdog_adapter.py` delegates to a real mesh adapter, and taskdog
  supports only `taskdog_list_tasks` and `taskdog_create_task`. The others
  return stub payloads.
- `EventLog` never deletes events — do not add a prune path.
- Do not add starlette/fastapi to this package.
- `gateway/adapters/` holds hyphenated legacy filenames plus underscore
  aliases of the same stubs; prefer the underscore name when adding one.
- `clients/__init__.py` sets `cli_adapter = None` when the CLI import fails —
  guard for `None` before using it.

## COMMANDS
```bash
python -m sys_ikigai.gateway.start_gateway
python -m sys_ikigai.gateway.client_cli watch --event-filter <name>
python -m sys_ikigai.gateway.event_log_cli tail --n 20
```
