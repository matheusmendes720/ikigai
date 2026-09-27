---
name: M147-fix-windows-stdio
description: Replace mcp.client.stdio.stdio_client with raw subprocess.Popen + thread-based reader in mcp_runtime. Fixes Windows BrokenResourceError in M146 handshake.
status: PENDING
---

# M147 — Fix Windows MCP stdio transport

## Problem (from M146 §Honest scope)

M146 shipped with a working architecture but the production smoke test was
marked `xfail` because the MCP stdio handshake hangs on Windows. Root
cause discovered: `mcp.client.stdio.stdio_client` uses `anyio.open_process`
+ `FileReadStream`, which calls `to_thread.run_sync(file.read)` on the
subprocess pipe. On Windows, the pipe uses overlapped I/O (because
`CREATE_NO_WINDOW` is passed), and reads from worker threads fail with
`BrokenResourceError`.

The MCP server IS healthy (proven by raw `subprocess.Popen` + thread-based
reader returning a valid initialize response in <2s). The bug is purely in
the MCP client's Windows transport.

## Approach

Replace `stdio_client` with a **raw `subprocess.Popen` + thread-based
transport** inside `mcp_runtime.py`. This is the same pattern MCP itself
uses as a fallback (`FallbackProcess`), but we'll implement it directly
because we want full control over the encoding and thread lifecycle.

### Transport design

```
┌─ mcp_bridge (sync API) ────────────────────────────────────────────┐
│                                                                     │
│  ikigai_health() ──► _call("ikigai_health", {})                     │
│                         │                                           │
│                         ▼                                           │
│                    _SyncAdapter.call()                              │
│                         │                                           │
│                         ▼                                           │
│         ┌─── _SyncAdapter._submit_coro(...) ───┐                    │
│         │                                       │                    │
│         ▼                                       ▼                    │
│  asyncio.run_coroutine_threadsafe(...)   background event loop      │
│         │                                       │                    │
│         ▼                                       │                    │
│    _AsyncClient.call_tool(name, args)            │                    │
│         │                                       │                    │
│         ▼                                       │                    │
│    ┌────────────────────────────────────────────┴───────────┐         │
│    │ Raw subprocess.Popen (python -u -m mcp_server)         │         │
│    │   stdin: write JSON-RPC request line                   │         │
│    │   stdout: read JSON-RPC response lines                 │         │
│    │   stderr: capture for diagnostics                      │         │
│    └────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
```

### Why this works

- Raw `subprocess.Popen` gives us synchronous file handles (binary mode).
- A dedicated reader thread (started at process spawn) reads bytes from
  `proc.stdout` and pushes them into an `asyncio.Queue` (via
  `loop.call_soon_threadsafe`).
- The async client (`_AsyncClient`) is a small wrapper that:
  1. Writes a JSON-RPC request to `proc.stdin` (via `loop.run_in_executor`)
  2. Waits for the matching response from the queue
  3. Returns the parsed JSON to the sync caller

This sidesteps anyio + ProactorEventLoop + FileReadStream entirely.

## Acceptance criteria

- [ ] `mcp_runtime.bind_server()` actually completes the MCP handshake
      against the real `python -m mcp_server` subprocess on Windows.
- [ ] `tests/test_m146_production_binding.py::test_real_mcp_handshake_against_live_server`
      flips from `xfail` to PASSING.
- [ ] At least 5 new tests in `tests/test_m147_windows_stdio.py`:
      - subprocess spawns cleanly (no BrokenResourceError)
      - initialize handshake completes <5s
      - tools/list returns ≥19 tools
      - tool call (ikigai_health) returns valid response
      - teardown is clean (no orphaned subprocesses after unbind_server)
- [ ] `bind_server()` still degrades gracefully when:
      - IKIGAI venv missing (FileNotFoundError)
      - subprocess fails to start (RuntimeError)
      - handshake times out (RuntimeError after 30s)
- [ ] `.claude/loop/mcp_runtime.py` ≤ 450 LOC (was 303, expect +120 for transport).
- [ ] Full regression sweep ≥ 158 PASSED (was 154 + 4 new).

## Out of scope

- Fixing MCP's own `stdio_client` (upstream issue).
- Switching to SSE/HTTP transport (would require server changes too).
- Adding retries / circuit breaker (deferred to M148+).

## Honest scope

This is a **real implementation milestone**, not a doc/spec exercise. The
fix is ~120 LOC of transport code. Cost: ~$0.30 (one session, no
sub-agents needed). Risk: medium — Windows subprocess pipe semantics
have edge cases we may not catch until user runs it.

## Atomic breakdown

- **T-147.1** — write `specs/M147-fix-windows-stdio/SPEC.md` (DONE in this commit).
- **T-147.2** — implement raw transport in `mcp_runtime.py`:
  - Replace `stdio_client(params)` with `_RawTransport.start()`.
  - Replace `ClientSession(read, write)` with `_RawClient` class.
  - Implement `_RawClient.call_tool(name, args)` and `.read_resource(uri)`.
  - Update `_SyncAdapter` to call `_RawClient` instead of `loop._mcp_session`.
- **T-147.3** — write `tests/test_m147_windows_stdio.py` with 5 tests.
- **T-147.4** — flip the M146 xfail test to PASSING (or split it).
- **T-147.5** — full regression sweep + commit.
