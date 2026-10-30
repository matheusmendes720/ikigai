# tests/gateway/ — MCP Stdio Transport

**Score:** 8 (15 files, 100% code, 43 module-level symbols, 28 exports)
**Role:** the JSON-RPC 2.0 stdio transport contract and the gateway boot smoke test.

## OVERVIEW

The shared transport layer: `sys_ikigai.gateway.stdio_server_base.StdioServerBase`
is exercised here without any subprocess, and `test_start_gateway.py` boots the real
gateway on a free port and polls `/health`. The fork-server E2E harness lives one level
down in `clients/`.

## STRUCTURE

```
tests/gateway/
├── __init__.py
├── test_stdio_server_base.py   # JSON-RPC 2.0 method dispatch
├── test_start_gateway.py       # boots the gateway, hits /health
└── clients/                    # fork MCP server E2E -> clients/AGENTS.md
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Transport contract | `test_stdio_server_base.py` | `initialize`, `tools/list`, `tools/call`, unknown method -> `-32601` |
| Gateway boot | `test_start_gateway.py` | binds a free port, polls `/health`, tears the process down |
| Fork MCP E2E | `clients/` | real subprocess + hand-rolled JSON-RPC -> `clients/AGENTS.md` |
| Transport implementation | `sys_ikigai/gateway/stdio_server_base.py` | the code under test |

## CONVENTIONS

- `test_stdio_server_base.py` calls `StdioServerBase.handle_request` directly — no
  subprocess, no transport, no framing. It asserts the JSON-RPC envelope:
  `response["jsonrpc"] == "2.0"`, `response["id"]` echoes the request id, results
  live under `result`, and an unknown method returns error code `-32601`.
- Tools are registered on the instance (`server.register_tool(name=..., handler=...,
  schema=...)`) before the request is sent; `tools/call` returns the handler's JSON
  serialized into `result["content"][0]["text"]`.
- `test_start_gateway.py` picks a free port with a socket, launches the gateway as a
  subprocess, and polls `/health` over `urllib.request` until it answers.
- `tests/gateway/` has `__init__.py`, so it is an importable package; the sibling
  `clients/` package is importable too.

## ANTI-PATTERNS

- NEVER assert on a response without checking its `id`. JSON-RPC 2.0 requires the
  response id to echo the request id.
- NEVER let a notification carry an `id` field — `id` is reserved for requests that
  expect a response.
- NEVER spawn the gateway on a fixed port. Bind a free port first; CI runs in
  parallel with other suites.
- NEVER leave the gateway subprocess running. The test kills it in a `finally` block.
- NEVER add a transport assertion here that needs a real process — that belongs in
  `clients/`, which owns the subprocess harness.
