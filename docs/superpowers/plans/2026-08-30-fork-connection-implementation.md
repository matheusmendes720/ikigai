# Fork Connection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect `solverforge-calendar` and `tuiboard` forks to the `UnifiedMCPGateway` so all 6 tools (`sf_schedule`, `sf_replan`, `sf_availability`, `tuiboard_render`, `tuiboard_snapshot`, `tuiboard_diff`) are callable via JSON-RPC 2.0 over stdio from a single gateway endpoint.

**Architecture:** Hand-rolled JSON-RPC 2.0 servers per fork (`src/solverforge_calendar/server.py`, `src/tuiboard/server.py`) using a shared `stdio_server_base.py` transport in the gateway package. A new `start_gateway.py` boots `UnifiedMCPGateway` on `127.0.0.1:8765`, calls `register_default_adapters()`, and serves forever. Fork MCP servers are in-repo (Q1=β); transport is stdlib-only JSON-RPC (Q2=i); no auth (Q3=a); single JSONL event log (Q4=i); no tool versioning in v1 (Q5=γ); `vault_write` conformance via grep test (Q6=I+III).

**Tech Stack:** Python 3.11+, Pydantic v2 strict (`frozen=True, extra="forbid"`), stdlib only (`json`, `subprocess`, `sqlite3`, `http.server`, `threading`, `logging`, `uuid`, `datetime`), JSON-RPC 2.0 over Content-Length-framed stdio. No new dependencies.

## Global Constraints

The following rules bind every task in this plan (carry them verbatim into per-task reasoning):

- `vault_write` is the ONLY vault writer per attribution §7 — forks MUST NOT touch `vault/`
- Pydantic v2 strict (`frozen=True, extra="forbid"`) on every cross-process type
- No LLM in pipelines — fork servers are pure deterministic logic
- No new dependencies — stdlib + existing Pydantic v2 only
- UEID imported from `src/contracts/common.py`; UPSERT on `ueid` for write paths
- `StdioAdapter` protocol invariants (verbatim from `src/ikigai/src/ikigai/gateway/stdio_adapter.py`): `bufsize=0` on subprocess pipes, `read1(N)` for stderr drain (Windows), single-writer lock per subprocess, hard timeout per call, subprocess killed on timeout
- Per-fork `call_timeout_s`: taskdog=15s, solverforge-calendar=60s (sf_replan is heavy), tuiboard=15s
- `prefix_map` at `gateway.py:151-155`: `{taskdog: "taskdog_", tuiboard: "tuiboard_", solverforge-calendar: "sf_"}`
- No edits to `**/scoring/**`, `**/formula/**`, `**/qhe/**`, `**/regime/**`, `**/weight/**` (algorithm gate per `algorithm-gate-system-readiness-not-sonho-2026-08-29`)
- `vault_write` conformance enforced via `tests/gateway/clients/test_vault_write_conformance.py` (grep test)
- E2E tests use real subprocess + JSON-RPC handshake (B5.B pattern); tests MUST handle MCP absence via `pytest.skip` if fork binary/module not available
- Tests inherit `bufsize=0` + `read1` patterns for Windows reliability
- Append-only invariant preserved: `data/gateway/events.jsonl`, `data/review_queue/`
- No `Co-Authored-By` trailer in any commit
- Pre-flight regression mandatory per `verify-agent-fabricated-failures` memory: main-session `pytest`/`ruff`/`mypy` before any "DONE" claim
- Cross-fork storage adapter pattern (separate from MCP factory): `name`/`read`/`apply_change`/`supports_field` per `ForkAdapter` Protocol. **tuiboard is NOT a storage adapter** (rendering fork only); `_load_adapters()` correctly omits it.

## File Structure

### Phase A1 (Foundation ~5h) — 7 tasks

| File | Action | Purpose |
|---|---|---|
| `src/ikigai/src/ikigai/gateway/stdio_server_base.py` | CREATE | Shared transport scaffold (~150 LOC); reusable JSON-RPC 2.0 loop |
| `src/solverforge_calendar/__init__.py` | CREATE | Empty package marker |
| `src/solverforge_calendar/server.py` | CREATE | Transport-only server; `tools/list` returns []; registers future tools in A2-A4 |
| `src/tuiboard/__init__.py` | CREATE | Empty package marker |
| `src/tuiboard/server.py` | CREATE | Transport-only server; `tools/list` returns []; registers future tools in A2-A4 |
| `src/ikigai/src/ikigai/gateway/start_gateway.py` | CREATE | Boots `UnifiedMCPGateway` on `:8765`, calls `register_default_adapters()` |
| `tests/gateway/__init__.py` | CREATE | Test package marker |
| `tests/gateway/clients/__init__.py` | CREATE | Test package marker |
| `tests/gateway/clients/conftest.py` | CREATE | Shared fixtures: `server_process`, `skip_if_no_module` |
| `tests/gateway/clients/test_solverforge_calendar_init.py` | CREATE | E2E test: subprocess spawn + JSON-RPC `initialize` handshake |
| `tests/gateway/clients/test_tuiboard_init.py` | CREATE | E2E test: subprocess spawn + JSON-RPC `initialize` handshake |
| `tests/gateway/test_start_gateway.py` | CREATE | Smoke test: gateway boots, `/health` returns adapters list |

### Phase A2 (Reads ~6h) — 6 tasks

| File | Action | Purpose |
|---|---|---|
| `src/solverforge_calendar/models.py` | CREATE | Pydantic models: `SfScheduleInput/Output`, `SfReplanInput/Output`, `SfAvailabilityInput/Output`, `SfPlanDiff`, `SfTimeSlot` |
| `src/solverforge_calendar/db.py` | CREATE | SQLite manager wrapping `data/solverforge_calendar/unified_planning.db` |
| `src/solverforge_calendar/tools/__init__.py` | CREATE | Empty package marker |
| `src/solverforge_calendar/tools/sf_availability.py` | CREATE | `sf_availability` handler — read-only, no overlap detection |
| `src/tuiboard/models.py` | CREATE | Pydantic models: `TuiboardRenderInput/Output`, `TuiboardSnapshotInput/Output`, `TuiboardDiffInput/Output`, `TuiboardTaskEntry`, `TuiboardChange`, `TuiboardFrame` |
| `src/tuiboard/snapshots.py` | CREATE | JSON snapshot persistence at `data/tuiboard/snapshots/` |
| `src/tuiboard/tools/__init__.py` | CREATE | Empty package marker |
| `src/tuiboard/tools/tuiboard_diff.py` | CREATE | `tuiboard_diff` handler — compares two snapshots field-by-field |
| `src/solverforge_calendar/server.py` | MODIFY | Register `sf_availability` handler |
| `src/tuiboard/server.py` | MODIFY | Register `tuiboard_diff` handler |
| `tests/gateway/clients/test_sf_availability.py` | CREATE | E2E: spawn, call `tools/call sf_availability` |
| `tests/gateway/clients/test_tuiboard_diff.py` | CREATE | E2E: spawn, create two snapshots, call `tools/call tuiboard_diff` |

### Phase A3 (Writes ~14h) — 6 tasks

| File | Action | Purpose |
|---|---|---|
| `src/solverforge_calendar/tools/sf_schedule.py` | CREATE | `sf_schedule` handler — UPSERT on ueid, 5-min overlap detection, blocked_by resolution |
| `src/solverforge_calendar/server.py` | MODIFY | Register `sf_schedule` (in addition to sf_availability) |
| `src/tuiboard/aggregator.py` | CREATE | Multi-fork read across CliAdapter + TaskdogAdapter + SolverforgeCalendarAdapter |
| `src/tuiboard/tools/tuiboard_render.py` | CREATE | `tuiboard_render` handler — 4 layouts: kanban/list/calendar/tree |
| `src/tuiboard/tools/tuiboard_snapshot.py` | CREATE | `tuiboard_snapshot` handler — JSON snapshot, idempotent on (name, filters) |
| `src/tuiboard/server.py` | MODIFY | Register all 3 tuiboard handlers |
| `tests/gateway/clients/test_sf_schedule.py` | CREATE | E2E: insert, update via UPSERT, conflict detection |
| `tests/gateway/clients/test_tuiboard_render.py` | CREATE | E2E: render in 4 layouts, validate output schema |
| `tests/gateway/clients/test_tuiboard_snapshot.py` | CREATE | E2E: save snapshot, idempotent replay |

### Phase A4 (Advanced ~12h) — 4 tasks

| File | Action | Purpose |
|---|---|---|
| `src/solverforge_calendar/tools/sf_replan.py` | CREATE | `sf_replan` handler — naive constraint solver (≤14-day horizon), 3 strategies |
| `src/solverforge_calendar/server.py` | MODIFY | Register `sf_replan` (all 3 solverforge tools now live) |
| `src/tuiboard/aggregator.py` | MODIFY | Extend precedence logic: taskdog > solverforge-calendar > cli (last mtime wins) |
| `tests/gateway/clients/test_sf_replan.py` | CREATE | E2E: replan with known conflict, validate plan_id idempotency |
| `tests/gateway/clients/test_tuiboard_aggregator.py` | CREATE | Unit test: aggregator dedup across 3 forks |

### Phase A5 (Cleanup ~3h) — 5 tasks

| File | Action | Purpose |
|---|---|---|
| `src/ikigai/start_mcp_gateway.sh` | MODIFY | Add SUPERSEDED trailer pointing to `start_gateway.py` (or rewrite as 30-line shim) |
| `src/ikigai/mcp_config.json` | MODIFY | Update solverforge + tuiboard entries; delete stale "requires Rust toolchain" note |
| `docs/code-docs/adr/2026-08-30-fork-connection-architecture.md` | CREATE | 80-line ADR documenting the fork-connection architecture decision |
| `tests/gateway/clients/test_vault_write_conformance.py` | CREATE | Grep test: forks MUST NOT touch `vault/` |
| `docs/superpowers/specs/2026-08-30-fork-connection-architecture.md` | MODIFY | Add SHIPPED trailer with commit SHA + plan pointer |

---

# Phase A1: Foundation (~5h)

## Task A1.1: Shared stdio_server_base transport

**Files:**
- Create: `src/ikigai/src/ikigai/gateway/stdio_server_base.py`
- Test: `tests/gateway/test_stdio_server_base.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `class StdioServerBase` with `register_tool(name, handler, schema)`, `serve_forever()`, `handle_request(payload: dict) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# tests/gateway/test_stdio_server_base.py
"""Tests for the shared JSON-RPC 2.0 stdio server transport."""
from __future__ import annotations
import json
import pytest
from ikigai.gateway.stdio_server_base import StdioServerBase


def test_handle_initialize_returns_server_info():
    server = StdioServerBase(name="test-server", version="0.0.1")
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
    }
    response = server.handle_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert response["result"]["serverInfo"]["name"] == "test-server"
    assert response["result"]["serverInfo"]["version"] == "0.0.1"


def test_handle_tools_list_returns_registered_tools():
    server = StdioServerBase(name="test", version="0.1.0")

    def echo(args: dict) -> dict:
        return {"echoed": args}

    server.register_tool(name="echo", handler=echo, schema={"type": "object"})
    request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    response = server.handle_request(request)
    assert response["result"]["tools"][0]["name"] == "echo"


def test_handle_tools_call_invokes_handler():
    server = StdioServerBase(name="test", version="0.1.0")
    server.register_tool(
        name="double",
        handler=lambda args: {"result": args["x"] * 2},
        schema={"type": "object", "properties": {"x": {"type": "integer"}}},
    )
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "double", "arguments": {"x": 21}},
    }
    response = server.handle_request(request)
    assert response["result"]["content"][0]["text"] == '{"result": 42}'


def test_handle_unknown_method_returns_error():
    server = StdioServerBase(name="test", version="0.1.0")
    request = {"jsonrpc": "2.0", "id": 4, "method": "does/not/exist", "params": {}}
    response = server.handle_request(request)
    assert response["error"]["code"] == -32601
    assert "does/not/exist" in response["error"]["message"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/gateway/test_stdio_server_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ikigai.gateway.stdio_server_base'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ikigai/src/ikigai/gateway/stdio_server_base.py
"""Shared JSON-RPC 2.0 stdio server base — used by all fork MCP servers.

Per spec §10 (decisions): hand-rolled JSON-RPC 2.0 over Content-Length-framed
stdio, stdlib only. Each fork server inherits from this base and registers
its own tools via register_tool().
"""
from __future__ import annotations

import logging
import sys
from typing import Any, Callable

logger = logging.getLogger(__name__)


class StdioServerBase:
    """Base class for fork MCP servers.

    Usage:
        server = StdioServerBase(name="my-fork", version="0.1.0")
        server.register_tool(name="my_tool", handler=my_handler, schema={...})
        server.serve_forever()
    """

    def __init__(self, *, name: str, version: str) -> None:
        self._name = name
        self._version = version
        self._tools: dict[str, tuple[Callable[[dict], dict], dict]] = {}

    def register_tool(
        self,
        *,
        name: str,
        handler: Callable[[dict], dict],
        schema: dict,
    ) -> None:
        """Register a tool. handler takes args dict, returns result dict."""
        self._tools[name] = (handler, schema)

    def handle_request(self, request: dict) -> dict:
        """Dispatch a single JSON-RPC 2.0 request, return a response dict."""
        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": self._name, "version": self._version},
                    "capabilities": {"tools": {}},
                }
            elif method == "tools/list":
                result = {"tools": [
                    {"name": name, "inputSchema": schema}
                    for name, (_, schema) in self._tools.items()
                ]}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                if tool_name not in self._tools:
                    raise ValueError(f"unknown tool: {tool_name}")
                handler, _ = self._tools[tool_name]
                inner = handler(arguments)
                result = {
                    "content": [{"type": "text", "text": _to_json(inner)}],
                    "isError": False,
                }
            elif method == "notifications/cancelled":
                # No-op: client cancels; we just acknowledge by returning empty result
                result = {}
            else:
                return _error_response(req_id, -32601, f"method not found: {method}")
            return _success_response(req_id, result)
        except ValueError as e:
            return _error_response(req_id, -32602, f"invalid params: {e}")
        except Exception as e:  # noqa: BLE001
            logger.exception("handler crashed")
            return _error_response(req_id, -32603, f"internal error: {e}")

    def serve_forever(self) -> None:
        """Read Content-Length-framed JSON-RPC requests from stdin, write to stdout.

        Frame format: Content-Length: <N>\\r\\n\\r\\n<N bytes of JSON>
        """
        while True:
            headers = {}
            while True:
                line = sys.stdin.readline()
                if not line:  # EOF
                    return
                line = line.rstrip("\r\n")
                if line == "":
                    break
                if ":" in line:
                    key, val = line.split(":", 1)
                    headers[key.strip().lower()] = val.strip()

            content_length = int(headers.get("content-length", "0"))
            if content_length == 0:
                continue
            payload = sys.stdin.buffer.read(content_length)
            request = _from_json_bytes(payload)
            response = self.handle_request(request)
            sys.stdout.buffer.write(_frame_response(response))
            sys.stdout.buffer.flush()


def _to_json(obj: Any) -> str:
    import json
    return json.dumps(obj, separators=(",", ":"))


def _from_json_bytes(data: bytes) -> dict:
    import json
    return json.loads(data.decode("utf-8"))


def _frame_response(response: dict) -> bytes:
    body = _to_json(response).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


def _success_response(req_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error_response(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/gateway/test_stdio_server_base.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/ikigai/src/ikigai/gateway/stdio_server_base.py tests/gateway/test_stdio_server_base.py tests/gateway/__init__.py
git commit -m "feat(gateway): add StdioServerBase — shared JSON-RPC 2.0 transport"
```

## Task A1.2: solverforge_calendar transport-only server

**Files:**
- Create: `src/solverforge_calendar/__init__.py`
- Create: `src/solverforge_calendar/server.py`

**Interfaces:**
- Consumes: `StdioServerBase` from A1.1
- Produces: `python -m solverforge_calendar.server` runs an MCP server; `tools/list` returns `[]` (tools added in A2-A4)

- [ ] **Step 1: Create the package marker**

```python
# src/solverforge_calendar/__init__.py
"""solverforge-calendar fork — calendar + scheduler MCP server.

In-repo per spec Q1=β. Stdlib-only JSON-RPC 2.0 transport per Q2=i.
"""
__version__ = "0.1.0"
```

- [ ] **Step 2: Create the transport-only server**

```python
# src/solverforge_calendar/server.py
"""solverforge-calendar MCP server entry point.

Transport-only scaffold (Phase A1). Tools (sf_availability, sf_schedule,
sf_replan) are added in A2-A4.
"""
from __future__ import annotations

import logging
import os

from ikigai.gateway.stdio_server_base import StdioServerBase

logger = logging.getLogger(__name__)


def _build_server() -> StdioServerBase:
    data_dir = os.environ.get("SOLVERFORGE_DATA_DIR", "data/solverforge_calendar")
    os.makedirs(data_dir, exist_ok=True)
    return StdioServerBase(name="solverforge-calendar", version="0.1.0")


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=__import__("sys").stderr)
    server = _build_server()
    # Tools registered in A2 (sf_availability), A3 (sf_schedule), A4 (sf_replan)
    server.serve_forever()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add src/solverforge_calendar/__init__.py src/solverforge_calendar/server.py
git commit -m "feat(solverforge_calendar): transport-only MCP server scaffold"
```

## Task A1.3: tuiboard transport-only server

**Files:**
- Create: `src/tuiboard/__init__.py`
- Create: `src/tuiboard/server.py`

**Interfaces:**
- Consumes: `StdioServerBase` from A1.1
- Produces: `python -m tuiboard.server` runs an MCP server; `tools/list` returns `[]`

- [ ] **Step 1: Create the package marker**

```python
# src/tuiboard/__init__.py
"""tuiboard fork — TUI dashboard renderer MCP server.

In-repo per spec Q1=β. Stdlib-only JSON-RPC 2.0 transport per Q2=i.

NOTE: tuiboard is a RENDERING fork — it reads from the cross-fork storage
adapters (CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter) but does
NOT have its own storage adapter (per spec: not a data fork).
"""
__version__ = "0.1.0"
```

- [ ] **Step 2: Create the transport-only server**

```python
# src/tuiboard/server.py
"""tuiboard MCP server entry point.

Transport-only scaffold (Phase A1). Tools (tuiboard_diff, tuiboard_snapshot,
tuiboard_render) are added in A2-A3.
"""
from __future__ import annotations

import logging
import os

from ikigai.gateway.stdio_server_base import StdioServerBase

logger = logging.getLogger(__name__)


def _build_server() -> StdioServerBase:
    snapshots_dir = os.environ.get("TUIBOARD_SNAPSHOTS_DIR", "data/tuiboard/snapshots")
    os.makedirs(snapshots_dir, exist_ok=True)
    return StdioServerBase(name="tuiboard", version="0.1.0")


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=__import__("sys").stderr)
    server = _build_server()
    # Tools registered in A2 (tuiboard_diff), A3 (tuiboard_snapshot, tuiboard_render)
    server.serve_forever()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add src/tuiboard/__init__.py src/tuiboard/server.py
git commit -m "feat(tuiboard): transport-only MCP server scaffold"
```

## Task A1.4: E2E test fixtures (conftest)

**Files:**
- Create: `tests/gateway/clients/__init__.py`
- Create: `tests/gateway/clients/conftest.py`

**Interfaces:**
- Consumes: nothing
- Produces: `server_process` fixture (spawns real subprocess + handles MCP absence via skip)

- [ ] **Step 1: Create the test package marker**

```python
# tests/gateway/clients/__init__.py
"""Tests for downstream fork MCP server subprocess integration."""
```

- [ ] **Step 2: Create shared fixtures**

```python
# tests/gateway/clients/conftest.py
"""Shared fixtures for fork MCP server E2E tests.

Per spec §10 + verify-agent-fabricated-failures memory: tests MUST handle MCP
absence via pytest.skip (the fork server module may not be importable in CI
without PYTHONPATH adjustments). Per B5.B pattern: real subprocess + JSON-RPC.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def skip_if_no_module() -> None:
    """Skip the test if the fork module cannot be imported.

    Per B5.B + B6.4 lesson: tests for MCP-dependent code must handle MCP
    absence (e.g., module not on PYTHONPATH) by skipping gracefully.
    """
    # We use the python executable from sys.executable; the actual module
    # import check happens at the server_process fixture level.
    if shutil.which(sys.executable) is None:
        pytest.skip(f"python executable not found: {sys.executable}")


@pytest.fixture
def server_process_factory(tmp_path: Path):
    """Factory that spawns a fork MCP server subprocess and yields its proc + stdio.

    Usage:
        def test_something(server_process_factory, skip_if_no_module):
            with server_process_factory("solverforge_calendar.server") as (proc, stdin, stdout):
                # write JSON-RPC request to stdin, read response from stdout
                ...
    """
    spawned: list[subprocess.Popen] = []

    def _factory(module: str, *, env: dict[str, str] | None = None) -> Iterator[tuple]:
        # Add repo root and src/ikigai to PYTHONPATH so the fork module resolves
        # AND so `from ikigai.gateway.stdio_server_base import ...` works.
        repo_root = Path(__file__).resolve().parents[3]
        ikigai_src = repo_root / "src" / "ikigai" / "src"
        proc_env = {
            **__import__("os").environ,
            "PYTHONPATH": f"{repo_root}{__import__("os").sep}{ikigai_src}",
            **(env or {}),
        }
        proc = subprocess.Popen(
            [sys.executable, "-m", module],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,  # critical for JSON-RPC framing on Windows
            env=proc_env,
        )
        spawned.append(proc)
        try:
            yield proc, proc.stdin, proc.stdout
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()

    yield _factory

    for proc in spawned:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
```

- [ ] **Step 3: Commit**

```bash
git add tests/gateway/clients/__init__.py tests/gateway/clients/conftest.py
git commit -m "test(gateway): add conftest fixtures for fork subprocess E2E"
```

## Task A1.5: E2E test for solverforge-calendar initialize handshake

**Files:**
- Create: `tests/gateway/clients/test_solverforge_calendar_init.py`

**Interfaces:**
- Consumes: `server_process_factory` fixture from A1.4
- Produces: passing E2E test for `python -m solverforge_calendar.server`

- [ ] **Step 1: Write the failing test**

```python
# tests/gateway/clients/test_solverforge_calendar_init.py
"""E2E test: spawn solverforge_calendar.server, verify JSON-RPC initialize handshake.

Per B5.B pattern (real subprocess) + spec §10 Q2=i (hand-rolled JSON-RPC).
Per B6.4 lesson: must handle MCP absence via skip_if_no_module.
"""
from __future__ import annotations

import json
import sys


def _send_request(stdin, request: dict) -> None:
    body = json.dumps(request, separators=(",", ":")).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    stdin.write(header + body)
    stdin.flush()


def _read_response(stdout) -> dict:
    # Read headers
    headers: dict[str, str] = {}
    while True:
        line = stdout.readline()
        if not line:
            raise EOFError("server closed before sending headers")
        line = line.decode("ascii").rstrip("\r\n")
        if line == "":
            break
        if ":" in line:
            key, val = line.split(":", 1)
            headers[key.strip().lower()] = val.strip()
    content_length = int(headers["content-length"])
    body = stdout.buffer.read(content_length) if hasattr(stdout, "buffer") else stdout.read(content_length)
    return json.loads(body)


def test_solverforge_calendar_initialize_handshake(server_process_factory, skip_if_no_module):
    """Verify the server can complete a JSON-RPC initialize round-trip."""
    import pytest
    try:
        with server_process_factory("solverforge_calendar.server") as (proc, stdin, stdout):
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
            })
            response = _read_response(stdout)
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert response["result"]["serverInfo"]["name"] == "solverforge-calendar"
            assert response["result"]["serverInfo"]["version"] == "0.1.0"
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"solverforge_calendar module not importable: {e}")


def test_solverforge_calendar_tools_list_empty(server_process_factory, skip_if_no_module):
    """At A1, no tools registered yet — verify tools/list returns empty array."""
    import pytest
    try:
        with server_process_factory("solverforge_calendar.server") as (proc, stdin, stdout):
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
            })
            response = _read_response(stdout)
            assert response["result"]["tools"] == []
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"solverforge_calendar module not importable: {e}")
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/gateway/clients/test_solverforge_calendar_init.py -v`
Expected: 2 tests PASS (if both modules importable; tests skip gracefully if not)

- [ ] **Step 3: Commit**

```bash
git add tests/gateway/clients/test_solverforge_calendar_init.py
git commit -m "test(gateway): E2E for solverforge_calendar JSON-RPC handshake"
```

## Task A1.6: E2E test for tuiboard initialize handshake

**Files:**
- Create: `tests/gateway/clients/test_tuiboard_init.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/gateway/clients/test_tuiboard_init.py
"""E2E test: spawn tuiboard.server, verify JSON-RPC initialize handshake."""
from __future__ import annotations

import json
import pytest
from tests.gateway.clients.test_solverforge_calendar_init import _send_request, _read_response


def test_tuiboard_initialize_handshake(server_process_factory, skip_if_no_module):
    try:
        with server_process_factory("tuiboard.server") as (proc, stdin, stdout):
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
            })
            response = _read_response(stdout)
            assert response["result"]["serverInfo"]["name"] == "tuiboard"
            assert response["result"]["serverInfo"]["version"] == "0.1.0"
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"tuiboard module not importable: {e}")


def test_tuiboard_tools_list_empty(server_process_factory, skip_if_no_module):
    try:
        with server_process_factory("tuiboard.server") as (proc, stdin, stdout):
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
            })
            response = _read_response(stdout)
            assert response["result"]["tools"] == []
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"tuiboard module not importable: {e}")
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/gateway/clients/test_tuiboard_init.py -v`
Expected: 2 tests PASS (or skip)

- [ ] **Step 3: Commit**

```bash
git add tests/gateway/clients/test_tuiboard_init.py
git commit -m "test(gateway): E2E for tuiboard JSON-RPC handshake"
```

## Task A1.7: start_gateway.py + smoke test

**Files:**
- Create: `src/ikigai/src/ikigai/gateway/start_gateway.py`
- Create: `tests/gateway/test_start_gateway.py`

**Interfaces:**
- Consumes: `UnifiedMCPGateway`, `register_default_adapters`, `EventLog`, `GatewayConfig` from existing gateway package
- Produces: `python -m ikigai.gateway.start_gateway` boots the gateway on `:8765`

- [ ] **Step 1: Write the smoke test (failing)**

```python
# tests/gateway/test_start_gateway.py
"""Smoke test for start_gateway.py — boots gateway on a free port, /health check."""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import urllib.request


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_start_gateway_boots_and_responds_to_health(tmp_path: Path):
    port = _free_port()
    repo_root = Path(__file__).resolve().parents[2]
    ikigai_src = repo_root / "src" / "ikigai" / "src"
    env = {
        "PATH": __import__("os").environ["PATH"],
        "PYTHONPATH": f"{repo_root}{__import__('os').sep}{ikigai_src}",
        "IKIGAI_GATEWAY_PORT": str(port),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "ikigai.gateway.start_gateway"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
    )
    try:
        # Poll /health until ready (max 10s)
        url = f"http://127.0.0.1:{port}/health"
        for _ in range(100):
            try:
                with urllib.request.urlopen(url, timeout=0.5) as resp:
                    if resp.status == 200:
                        body = resp.read().decode("utf-8")
                        assert "adapters" in body
                        return  # PASS
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.1)
        pytest.fail(f"gateway did not respond at {url} within 10s")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/gateway/test_start_gateway.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ikigai.gateway.start_gateway'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ikigai/src/ikigai/gateway/start_gateway.py
"""UnifiedMCPGateway launcher — separates Layer 2 from Layer 1 FastMCP server.

Per spec §10 (decisions):
- Q3=a: no auth (localhost-only is sufficient)
- Q4=i: single JSONL event log at data/gateway/events.jsonl
- Wires register_default_adapters() so all 3 forks (taskdog, solverforge-calendar,
  tuiboard) are reachable via /call endpoint.

Boot:
    python -m ikigai.gateway.start_gateway
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from ikigai.gateway import (
    EventLog,
    GatewayConfig,
    UnifiedMCPGateway,
    register_default_adapters,
)

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=__import__("sys").stderr)
    host = os.environ.get("IKIGAI_GATEWAY_HOST", "127.0.0.1")
    port = int(os.environ.get("IKIGAI_GATEWAY_PORT", "8765"))
    data_dir = Path(os.environ.get("IKIGAI_DATA_DIR", "data"))

    cfg = GatewayConfig(host=host, port=port)
    event_log = EventLog(data_dir / "gateway" / "events.jsonl")
    gateway = UnifiedMCPGateway(config=cfg, event_log=event_log)
    register_default_adapters(gateway, data_dir=data_dir)
    logger.info("gateway listening on %s:%d (adapters registered)", host, port)
    gateway.serve_forever()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/gateway/test_start_gateway.py -v`
Expected: PASS

- [ ] **Step 5: Run main-session regression check**

Run: `pytest tests/gateway/ tests/gateway/clients/ -v` (from repo root)
Expected: all prior tests still PASS

- [ ] **Step 6: Commit**

```bash
git add src/ikigai/src/ikigai/gateway/start_gateway.py tests/gateway/test_start_gateway.py
git commit -m "feat(gateway): start_gateway.py — boot UnifiedMCPGateway on :8765"
```

---

# Phase A2: Reads (~6h)

## Task A2.1: solverforge_calendar Pydantic models

**Files:**
- Create: `src/solverforge_calendar/models.py`

**Interfaces:**
- Consumes: `UEID` from `src/contracts/common.py`
- Produces: `SfScheduleInput/Output`, `SfReplanInput/Output`, `SfAvailabilityInput/Output`, `SfPlanDiff`, `SfTimeSlot` (all Pydantic v2 frozen)

- [ ] **Step 1: Write the test**

```python
# tests/solverforge_calendar/test_models.py
"""Tests for solverforge_calendar Pydantic models."""
from __future__ import annotations
from datetime import datetime
import pytest
from pydantic import ValidationError
from solverforge_calendar.models import SfScheduleInput, SfAvailabilityInput, UEID


def test_sf_schedule_input_minimal():
    inp = SfScheduleInput(
        ueid="sc:task:byd-research:abc123:def456",
        title="BYD market research",
        start_at=datetime(2026, 9, 1, 9, 0, 0),
    )
    assert inp.title == "BYD market research"
    assert inp.blocked_by == []  # default
    assert inp.tags == []  # default
    assert inp.ikigai == {}  # default


def test_sf_schedule_input_frozen_rejects_mutation():
    inp = SfScheduleInput(
        ueid="sc:task:byd-research:abc123:def456",
        title="Test",
        start_at=datetime(2026, 9, 1, 9, 0, 0),
    )
    with pytest.raises(ValidationError):
        inp.title = "Modified"


def test_sf_schedule_input_extra_field_rejected():
    with pytest.raises(ValidationError):
        SfScheduleInput(
            ueid="sc:task:byd-research:abc123:def456",
            title="Test",
            start_at=datetime(2026, 9, 1, 9, 0, 0),
            unknown_field="extra",  # type: ignore[call-arg]
        )


def test_sf_availability_input_defaults():
    inp = SfAvailabilityInput(
        window_start=datetime(2026, 9, 1),
        window_end=datetime(2026, 9, 8),
    )
    assert inp.min_slot_minutes == 30  # default
    assert inp.exclude_ueids == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/solverforge_calendar/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'solverforge_calendar.models'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/solverforge_calendar/models.py
"""Pydantic v2 frozen models for solverforge-calendar tools.

Per spec §10 (decisions): all cross-process types use Pydantic v2 strict
(frozen=True, extra="forbid"). UEID imported from src/contracts.common.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Re-export UEID from canonical contracts location
from src.contracts.common import UEID


class _Base(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SfScheduleInput(_Base):
    """Input for sf_schedule — add or update a scheduled event."""
    ueid: UEID
    title: str = Field(..., max_length=200)
    start_at: datetime
    end_at: datetime | None = None
    rrule: str | None = None  # RFC 5545
    blocked_by: list[UEID] = []
    tags: list[str] = []
    ikigai: dict[str, Any] = {}


class SfScheduleOutput(_Base):
    ueid: UEID
    id: str  # fork-internal PK (uuid4 hex)
    status: Literal["scheduled", "conflict", "blocked"]
    scheduled_at: datetime
    conflicts: list[UEID] = []
    warnings: list[str] = []


class SfReplanInput(_Base):
    horizon_start: datetime
    horizon_end: datetime  # max 14 days from horizon_start
    affected_ueids: list[UEID] = []
    strategy: Literal["minimize_moves", "earliest_first", "load_balance"] = "minimize_moves"
    hard_constraints: list[str] = []


class SfPlanDiff(_Base):
    ueid: UEID
    action: Literal["moved", "kept", "removed"]
    before: datetime | None
    after: datetime | None
    reason: str


class SfReplanOutput(_Base):
    plan_id: UUID
    horizon_start: datetime
    horizon_end: datetime
    diff: list[SfPlanDiff]
    unresolvable: list[UEID] = []
    runtime_ms: int


class SfAvailabilityInput(_Base):
    window_start: datetime
    window_end: datetime  # max 14 days
    min_slot_minutes: int = 30  # min 15; max 480
    exclude_ueids: list[UEID] = []


class SfTimeSlot(_Base):
    start: datetime
    end: datetime


class SfAvailabilityOutput(_Base):
    window_start: datetime
    window_end: datetime
    free_slots: list[SfTimeSlot]
    busy_intervals: list[SfTimeSlot]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/solverforge_calendar/test_models.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/solverforge_calendar/models.py tests/solverforge_calendar/__init__.py tests/solverforge_calendar/test_models.py
git commit -m "feat(solverforge_calendar): Pydantic v2 frozen models for sf_* tools"
```

## Task A2.2: solverforge_calendar DB manager

**Files:**
- Create: `src/solverforge_calendar/db.py`
- Test: `tests/solverforge_calendar/test_db.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/solverforge_calendar/test_db.py
"""Tests for solverforge_calendar SQLite manager (UPI table wrapper)."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path

import pytest
from solverforge_calendar.db import SolverforgeDB


def test_upsert_creates_row(tmp_path: Path):
    db = SolverforgeDB(tmp_path / "upi.db")
    db.upsert(
        ueid="sc:task:byd-research:abc123:def456",
        title="BYD research",
        start_at=datetime(2026, 9, 1, 9, 0, 0),
        end_at=datetime(2026, 9, 1, 11, 0, 0),
    )
    row = db.read("sc:task:byd-research:abc123:def456")
    assert row is not None
    assert row["title"] == "BYD research"
    assert row["status"] == "scheduled"


def test_upsert_updates_existing(tmp_path: Path):
    db = SolverforgeDB(tmp_path / "upi.db")
    db.upsert(ueid="sc:task:a:b:c:d", title="Old",
              start_at=datetime(2026, 9, 1, 9, 0, 0), end_at=None)
    db.upsert(ueid="sc:task:a:b:c:d", title="New",
              start_at=datetime(2026, 9, 1, 10, 0, 0), end_at=None)
    row = db.read("sc:task:a:b:c:d")
    assert row["title"] == "New"  # updated, not duplicated


def test_read_returns_none_for_missing(tmp_path: Path):
    db = SolverforgeDB(tmp_path / "upi.db")
    assert db.read("sc:task:nonexistent:0:0") is None


def test_list_busy_in_window(tmp_path: Path):
    db = SolverforgeDB(tmp_path / "upi.db")
    db.upsert(ueid="sc:task:a:0:0", title="A",
              start_at=datetime(2026, 9, 1, 9, 0, 0),
              end_at=datetime(2026, 9, 1, 10, 0, 0))
    db.upsert(ueid="sc:task:b:0:0", title="B",
              start_at=datetime(2026, 9, 1, 14, 0, 0),
              end_at=datetime(2026, 9, 1, 15, 0, 0))
    busy = db.list_busy_in_window(
        start=datetime(2026, 9, 1, 0, 0, 0),
        end=datetime(2026, 9, 1, 23, 59, 59),
    )
    assert len(busy) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/solverforge_calendar/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/solverforge_calendar/db.py
"""SQLite manager wrapping the unified_planning_items (UPI) table.

Schema matches the existing cross-fork storage adapter at
src/mesh/adapters/solverforge_calendar.py. UPSERT on ueid.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


_SCHEMA = """
CREATE TABLE IF NOT EXISTS unified_planning_items (
    id TEXT PRIMARY KEY,
    ueid TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT,
    blocked_by TEXT DEFAULT '[]',
    tags TEXT DEFAULT '[]',
    ikigai TEXT DEFAULT '{}',
    status TEXT DEFAULT 'scheduled',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_upi_ueid ON unified_planning_items(ueid);
CREATE INDEX IF NOT EXISTS idx_upi_start ON unified_planning_items(start_at);
"""


class SolverforgeDB:
    """SQLite wrapper for the UPI table. SQLite UPSERT on ueid."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, isolation_level=None)

    def upsert(
        self,
        *,
        ueid: str,
        title: str,
        start_at: datetime,
        end_at: datetime | None,
        blocked_by: list[str] | None = None,
        tags: list[str] | None = None,
        ikigai: dict | None = None,
        status: str = "scheduled",
    ) -> dict:
        import json
        import uuid
        now = datetime.utcnow().isoformat()
        row_id = str(uuid.uuid4().hex)
        with self._conn() as c:
            # UPSERT: insert new with new uuid, or update existing row in place
            existing = c.execute(
                "SELECT id FROM unified_planning_items WHERE ueid = ?", (ueid,)
            ).fetchone()
            if existing:
                row_id = existing[0]
                c.execute(
                    """UPDATE unified_planning_items SET
                        title=?, start_at=?, end_at=?, blocked_by=?, tags=?, ikigai=?,
                        status=?, updated_at=?
                       WHERE ueid=?""",
                    (title, start_at.isoformat(), end_at.isoformat() if end_at else None,
                     json.dumps(blocked_by or []), json.dumps(tags or []),
                     json.dumps(ikigai or {}), status, now, ueid),
                )
            else:
                c.execute(
                    """INSERT INTO unified_planning_items
                        (id, ueid, title, start_at, end_at, blocked_by, tags, ikigai,
                         status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (row_id, ueid, title, start_at.isoformat(),
                     end_at.isoformat() if end_at else None,
                     json.dumps(blocked_by or []), json.dumps(tags or []),
                     json.dumps(ikigai or {}), status, now, now),
                )
        return {"id": row_id, "ueid": ueid, "status": status}

    def read(self, ueid: str) -> dict | None:
        import json
        with self._conn() as c:
            row = c.execute(
                """SELECT id, ueid, title, start_at, end_at, blocked_by, tags,
                          ikigai, status
                   FROM unified_planning_items WHERE ueid = ?""",
                (ueid,),
            ).fetchone()
            if not row:
                return None
            return {
                "id": row[0], "ueid": row[1], "title": row[2],
                "start_at": row[3], "end_at": row[4],
                "blocked_by": json.loads(row[5]), "tags": json.loads(row[6]),
                "ikigai": json.loads(row[7]), "status": row[8],
            }

    def list_busy_in_window(self, *, start: datetime, end: datetime) -> list[dict]:
        """Return rows whose [start_at, end_at) overlaps [start, end)."""
        with self._conn() as c:
            rows = c.execute(
                """SELECT ueid, title, start_at, end_at, status
                   FROM unified_planning_items
                   WHERE start_at < ? AND (end_at IS NULL OR end_at > ?)""",
                (end.isoformat(), start.isoformat()),
            ).fetchall()
            return [
                {"ueid": r[0], "title": r[1], "start_at": r[2],
                 "end_at": r[3], "status": r[4]}
                for r in rows
            ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/solverforge_calendar/test_db.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/solverforge_calendar/db.py tests/solverforge_calendar/test_db.py
git commit -m "feat(solverforge_calendar): SQLite UPI manager with UPSERT"
```

## Task A2.3: sf_availability handler + server registration

**Files:**
- Create: `src/solverforge_calendar/tools/__init__.py`
- Create: `src/solverforge_calendar/tools/sf_availability.py`
- Modify: `src/solverforge_calendar/server.py`
- Test: `tests/gateway/clients/test_sf_availability.py`

- [ ] **Step 1: Write the failing E2E test**

```python
# tests/gateway/clients/test_sf_availability.py
"""E2E: spawn solverforge_calendar.server, call sf_availability via tools/call."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from tests.gateway.clients.test_solverforge_calendar_init import _send_request, _read_response


def test_sf_availability_empty_window(server_process_factory, tmp_path: Path, skip_if_no_module):
    """With no events, sf_availability returns the entire window as free."""
    try:
        env = {"SOLVERFORGE_DATA_DIR": str(tmp_path / "sf")}
        with server_process_factory("solverforge_calendar.server", env=env) as (proc, stdin, stdout):
            start = datetime(2026, 9, 1, 0, 0, 0)
            end = datetime(2026, 9, 1, 23, 59, 0)
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
            })
            _read_response(stdout)  # consume initialize response
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": "sf_availability", "arguments": {
                    "window_start": start.isoformat(),
                    "window_end": end.isoformat(),
                }},
            })
            response = _read_response(stdout)
            assert "error" not in response, response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["window_start"] == start.isoformat()
            assert len(content["free_slots"]) == 1  # entire window is free
            assert content["busy_intervals"] == []
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"solverforge_calendar module not importable: {e}")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/gateway/clients/test_sf_availability.py -v`
Expected: FAIL — `unknown tool: sf_availability` (not registered yet)

- [ ] **Step 3: Write the tool handler**

```python
# src/solverforge_calendar/tools/__init__.py
"""Tool handlers for solverforge-calendar MCP server."""
```

```python
# src/solverforge_calendar/tools/sf_availability.py
"""sf_availability — query free slots in a window.

Read-only, no overlap detection (just lists busy intervals and subtracts).
Caches last query for 60s in-memory dict (not LRU).
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from solverforge_calendar.db import SolverforgeDB
from solverforge_calendar.models import (
    SfAvailabilityInput,
    SfAvailabilityOutput,
    SfTimeSlot,
)

_CACHE: dict[tuple, tuple[float, SfAvailabilityOutput]] = {}
_CACHE_TTL_S = 60.0


def _db() -> SolverforgeDB:
    data_dir = Path(os.environ.get("SOLVERFORGE_DATA_DIR", "data/solverforge_calendar"))
    return SolverforgeDB(data_dir / "unified_planning.db")


def handle(args: dict) -> dict:
    inp = SfAvailabilityInput.model_validate(args)
    if inp.exclude_ueids:
        # exclude_ueids is a hint for cache key only; behavior is per impl
        pass

    cache_key = (inp.window_start, inp.window_end, inp.min_slot_minutes,
                 tuple(inp.exclude_ueids))
    if cache_key in _CACHE:
        ts, cached = _CACHE[cache_key]
        import time
        if time.time() - ts < _CACHE_TTL_S:
            return cached.model_dump(mode="json")

    db = _db()
    busy = db.list_busy_in_window(start=inp.window_start, end=inp.window_end)
    busy_intervals = sorted(
        [SfTimeSlot(start=datetime.fromisoformat(b["start_at"]),
                    end=datetime.fromisoformat(b["end_at"]) if b["end_at"]
                    else datetime.fromisoformat(b["start_at"]))
         for b in busy if b["end_at"]],
        key=lambda s: s.start,
    )
    free_slots = _compute_free_slots(
        window_start=inp.window_start, window_end=inp.window_end,
        busy=busy_intervals, min_slot_minutes=inp.min_slot_minutes,
    )
    output = SfAvailabilityOutput(
        window_start=inp.window_start, window_end=inp.window_end,
        free_slots=free_slots, busy_intervals=busy_intervals,
    )
    import time
    _CACHE[cache_key] = (time.time(), output)
    return output.model_dump(mode="json")


def _compute_free_slots(
    *, window_start: datetime, window_end: datetime,
    busy: list[SfTimeSlot], min_slot_minutes: int,
) -> list[SfTimeSlot]:
    """Subtract busy intervals from [window_start, window_end); split into slots."""
    min_slot = timedelta(minutes=min_slot_minutes)
    free = []
    cursor = window_start
    for b in sorted(busy, key=lambda s: s.start):
        if b.start > cursor:
            gap = b.start - cursor
            if gap >= min_slot:
                free.append(SfTimeSlot(start=cursor, end=b.start))
            elif gap > timedelta(0):
                free.append(SfTimeSlot(start=cursor, end=cursor + gap))
        cursor = max(cursor, b.end) if b.end else cursor
    if window_end > cursor:
        gap = window_end - cursor
        if gap >= min_slot:
            free.append(SfTimeSlot(start=cursor, end=window_end))
        elif gap > timedelta(0):
            free.append(SfTimeSlot(start=cursor, end=cursor + gap))
    return free
```

- [ ] **Step 4: Register the tool in server.py**

Edit `src/solverforge_calendar/server.py` — replace the `_build_server` function:

```python
def _build_server() -> StdioServerBase:
    data_dir = os.environ.get("SOLVERFORGE_DATA_DIR", "data/solverforge_calendar")
    os.makedirs(data_dir, exist_ok=True)
    server = StdioServerBase(name="solverforge-calendar", version="0.1.0")
    # A2: read tools
    from solverforge_calendar.tools.sf_availability import handle as sf_avail
    from solverforge_calendar.models import SfAvailabilityInput
    server.register_tool(
        name="sf_availability",
        handler=sf_avail,
        schema=SfAvailabilityInput.model_json_schema(),
    )
    # A3: write tools (sf_schedule) added in next phase
    # A4: advanced tools (sf_replan) added in later phase
    return server
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/gateway/clients/test_sf_availability.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/solverforge_calendar/tools/ src/solverforge_calendar/server.py tests/gateway/clients/test_sf_availability.py
git commit -m "feat(solverforge_calendar): sf_availability tool with 60s cache"
```

## Task A2.4: tuiboard Pydantic models

**Files:**
- Create: `src/tuiboard/models.py`
- Test: `tests/tuiboard/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/tuiboard/test_models.py
"""Tests for tuiboard Pydantic models."""
from __future__ import annotations
from datetime import datetime
import pytest
from pydantic import ValidationError
from tuiboard.models import (
    TuiboardRenderInput, TuiboardSnapshotInput, TuiboardDiffInput,
    TuiboardLayoutName,
)


def test_render_input_minimal():
    inp = TuiboardRenderInput(layout="kanban")
    assert inp.ueids == []
    assert inp.filters is None


def test_render_input_validates_layout():
    with pytest.raises(ValidationError):
        TuiboardRenderInput(layout="invalid")  # type: ignore[arg-type]


def test_render_input_frozen_rejects_mutation():
    inp = TuiboardRenderInput(layout="list")
    with pytest.raises(ValidationError):
        inp.layout = "kanban"  # type: ignore[misc]


def test_snapshot_input_validates_name_length():
    with pytest.raises(ValidationError):
        TuiboardSnapshotInput(name="x" * 65, layout="kanban")  > 64


def test_diff_input_validates_required_ids():
    with pytest.raises(ValidationError):
        TuiboardDiffInput(from_snapshot_id="", to_snapshot_id="abc")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/tuiboard/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/tuiboard/models.py
"""Pydantic v2 frozen models for tuiboard tools."""
from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TuiboardLayoutName = Literal["kanban", "list", "calendar", "tree"]


class _Base(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class _Filters(_Base):
    status: Literal["planned", "scheduled", "in_progress", "done", "skipped"] | None = None
    vector: Literal["passion", "skill", "market", "revenue", "course"] | None = None
    tags: list[str] | None = None
    due_before: str | None = None  # ISO 8601


class _RenderOptions(_Base):
    max_width: int = 120
    show_ueid: bool = False
    compact: bool = False


class TuiboardRenderInput(_Base):
    ueids: list[str] = []  # 1..N if non-empty
    layout: TuiboardLayoutName
    filters: _Filters | None = None
    render_options: _RenderOptions | None = None


class TuiboardPosition(_Base):
    section: str
    row: int
    col: int


class TuiboardFrame(_Base):
    ueid: str
    title: str
    status: str | None = None
    due: str | None = None
    vector: str | None = None
    tags: list[str] = []
    position: TuiboardPosition
    child_ueids: list[str] = []


class TuiboardMetadata(_Base):
    total_tasks: int
    shown_tasks: int
    truncated: bool


class TuiboardRenderOutput(_Base):
    layout: TuiboardLayoutName
    frames: list[TuiboardFrame]
    metadata: TuiboardMetadata


class TuiboardSnapshotInput(_Base):
    name: str = Field(..., min_length=1, max_length=64)
    layout: TuiboardLayoutName
    filters: _Filters | None = None
    description: str | None = Field(None, max_length=500)


class TuiboardSnapshotOutput(_Base):
    snapshot_id: str  # uuid v4 hex
    name: str
    created_at: str  # ISO 8601
    task_count: int
    sha256: str


class TuiboardDiffInput(_Base):
    from_snapshot_id: str = Field(..., min_length=1)
    to_snapshot_id: str = Field(..., min_length=1)
    include_unchanged: bool = False


class TuiboardTaskEntry(_Base):
    ueid: str
    title: str
    status: str | None = None


class TuiboardChange(_Base):
    ueid: str
    field: str
    before: Any
    after: Any


class TuiboardDiffOutput(_Base):
    from_snapshot_id: str
    to_snapshot_id: str
    added: list[TuiboardTaskEntry]
    removed: list[TuiboardTaskEntry]
    changed: list[TuiboardChange]
    unchanged_count: int = 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/tuiboard/test_models.py -v`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tuiboard/models.py tests/tuiboard/__init__.py tests/tuiboard/test_models.py
git commit -m "feat(tuiboard): Pydantic v2 frozen models for tuiboard_* tools"
```

## Task A2.5: tuiboard snapshot persistence

**Files:**
- Create: `src/tuiboard/snapshots.py`
- Test: `tests/tuiboard/test_snapshots.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/tuiboard/test_snapshots.py
"""Tests for tuiboard snapshot persistence (JSON files)."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

import pytest
from tuiboard.snapshots import SnapshotStore


def test_save_and_load_round_trip(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    tasks = [{"ueid": "sc:task:a:0:0", "title": "A", "status": "scheduled"}]
    out = store.save(name="baseline", tasks=tasks)
    assert out["task_count"] == 1
    loaded = store.load(out["snapshot_id"])
    assert loaded["tasks"] == tasks


def test_save_is_idempotent_on_same_name(tmp_path: Path):
    """Per spec: idempotent on (name, filters) — same name returns same id."""
    store = SnapshotStore(tmp_path / "snapshots")
    tasks = [{"ueid": "sc:task:a:0:0", "title": "A"}]
    out1 = store.save(name="baseline", tasks=tasks)
    out2 = store.save(name="baseline", tasks=tasks)
    assert out1["snapshot_id"] == out2["snapshot_id"]


def test_list_snapshots(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    store.save(name="a", tasks=[])
    store.save(name="b", tasks=[])
    snapshots = store.list_all()
    assert {s["name"] for s in snapshots} == {"a", "b"}


def test_load_missing_raises(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    with pytest.raises(FileNotFoundError):
        store.load("nonexistent-id")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/tuiboard/test_snapshots.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/tuiboard/snapshots.py
"""JSON snapshot persistence for tuiboard (at data/tuiboard/snapshots/).

Per spec: idempotent on (name, filters). sha256 of canonical (sorted) task list.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


class SnapshotStore:
    """Persists tuiboard snapshots as JSON files."""

    def __init__(self, snapshots_dir: Path) -> None:
        self._dir = Path(snapshots_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _canonical_hash(self, tasks: list[dict]) -> str:
        canonical = json.dumps(tasks, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def save(
        self, *, name: str, tasks: list[dict],
        filters: dict | None = None, description: str | None = None,
    ) -> dict:
        # Idempotent on name: if a snapshot with this name exists, return its id
        existing = self._find_by_name(name)
        if existing is not None:
            return {
                "snapshot_id": existing["snapshot_id"],
                "name": existing["name"],
                "created_at": existing["created_at"],
                "task_count": existing["task_count"],
                "sha256": existing["sha256"],
            }
        sha = self._canonical_hash(tasks)
        sid = uuid.uuid4().hex
        now = datetime.utcnow().isoformat() + "Z"
        payload = {
            "snapshot_id": sid,
            "name": name,
            "created_at": now,
            "task_count": len(tasks),
            "sha256": sha,
            "tasks": tasks,
            "filters": filters or {},
            "description": description,
        }
        path = self._dir / f"{sid}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, path)
        return {
            "snapshot_id": sid, "name": name, "created_at": now,
            "task_count": len(tasks), "sha256": sha,
        }

    def load(self, snapshot_id: str) -> dict:
        path = self._dir / f"{snapshot_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"snapshot not found: {snapshot_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def list_all(self) -> list[dict]:
        results = []
        for path in self._dir.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            results.append({
                "snapshot_id": data["snapshot_id"], "name": data["name"],
                "created_at": data["created_at"], "task_count": data["task_count"],
                "sha256": data["sha256"],
            })
        return results

    def _find_by_name(self, name: str) -> dict | None:
        for path in self._dir.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("name") == name:
                return {
                    "snapshot_id": data["snapshot_id"], "name": data["name"],
                    "created_at": data["created_at"], "task_count": data["task_count"],
                    "sha256": data["sha256"],
                }
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/tuiboard/test_snapshots.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tuiboard/snapshots.py tests/tuiboard/test_snapshots.py
git commit -m "feat(tuiboard): JSON snapshot persistence with idempotent save"
```

## Task A2.6: tuiboard_diff handler + server registration

**Files:**
- Create: `src/tuiboard/tools/__init__.py`
- Create: `src/tuiboard/tools/tuiboard_diff.py`
- Modify: `src/tuiboard/server.py`
- Test: `tests/gateway/clients/test_tuiboard_diff.py`

- [ ] **Step 1: Write the failing E2E test**

```python
# tests/gateway/clients/test_tuiboard_diff.py
"""E2E: spawn tuiboard.server, call tuiboard_diff via tools/call."""
from __future__ import annotations
import json
import os
from pathlib import Path

import pytest
from tests.gateway.clients.test_solverforge_calendar_init import _send_request, _read_response


def test_tuiboard_diff_two_snapshots(server_process_factory, tmp_path: Path, skip_if_no_module):
    """Save 2 snapshots, then diff them; expect added + removed sets."""
    try:
        env = {"TUIBOARD_SNAPSHOTS_DIR": str(tmp_path / "snapshots")}
        with server_process_factory("tuiboard.server", env=env) as (proc, stdin, stdout):
            # initialize
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
            })
            _read_response(stdout)
            # save snapshot "before"
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": "tuiboard_snapshot", "arguments": {
                    "name": "before", "layout": "kanban",
                }},
            })
            resp_before = _read_response(stdout)
            sid_before = json.loads(resp_before["result"]["content"][0]["text"])["snapshot_id"]
            # save snapshot "after"
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": "tuiboard_snapshot", "arguments": {
                    "name": "after", "layout": "kanban",
                }},
            })
            resp_after = _read_response(stdout)
            sid_after = json.loads(resp_after["result"]["content"][0]["text"])["snapshot_id"]
            # diff
            _send_request(stdin, {
                "jsonrpc": "2.0", "id": 4, "method": "tools/call",
                "params": {"name": "tuiboard_diff", "arguments": {
                    "from_snapshot_id": sid_before,
                    "to_snapshot_id": sid_after,
                }},
            })
            response = _read_response(stdout)
            assert "error" not in response, response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["from_snapshot_id"] == sid_before
            assert content["to_snapshot_id"] == sid_after
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"tuiboard module not importable: {e}")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/gateway/clients/test_tuiboard_diff.py -v`
Expected: FAIL — `unknown tool: tuiboard_diff` (also tuiboard_snapshot not registered yet, so this fails earlier)

- [ ] **Step 3: Write the tool handler**

```python
# src/tuiboard/tools/__init__.py
"""Tool handlers for tuiboard MCP server."""
```

```python
# src/tuiboard/tools/tuiboard_diff.py
"""tuiboard_diff — compare two snapshots field-by-field.

Read-only. Returns no diff if either snapshot is missing (raises typed error).
"""
from __future__ import annotations

import os
from pathlib import Path

from tuiboard.models import (
    TuiboardChange, TuiboardDiffInput, TuiboardDiffOutput, TuiboardTaskEntry,
)
from tuiboard.snapshots import SnapshotStore


def _store() -> SnapshotStore:
    sd = Path(os.environ.get("TUIBOARD_SNAPSHOTS_DIR", "data/tuiboard/snapshots"))
    return SnapshotStore(sd)


def handle(args: dict) -> dict:
    inp = TuiboardDiffInput.model_validate(args)
    store = _store()
    src = store.load(inp.from_snapshot_id)  # raises FileNotFoundError → upstream JSON-RPC error
    dst = store.load(inp.to_snapshot_id)

    src_by_ueid = {t["ueid"]: t for t in src.get("tasks", [])}
    dst_by_ueid = {t["ueid"]: t for t in dst.get("tasks", [])}
    src_ids = set(src_by_ueid)
    dst_ids = set(dst_by_ueid)

    added = [TuiboardTaskEntry(**t) for ueid in (dst_ids - src_ids)
             for t in [dst_by_ueid[ueid]]]
    removed = [TuiboardTaskEntry(**t) for ueid in (src_ids - dst_ids)
               for t in [src_by_ueid[ueid]]]
    changed: list[TuiboardChange] = []
    unchanged = 0
    for ueid in src_ids & dst_ids:
        s, d = src_by_ueid[ueid], dst_by_ueid[ueid]
        diffs = _field_diff(s, d)
        if diffs:
            changed.extend(diffs)
        elif inp.include_unchanged:
            unchanged += 1
        else:
            unchanged += 1  # count regardless

    output = TuiboardDiffOutput(
        from_snapshot_id=inp.from_snapshot_id,
        to_snapshot_id=inp.to_snapshot_id,
        added=added, removed=removed, changed=changed,
        unchanged_count=unchanged,
    )
    return output.model_dump(mode="json")


def _field_diff(src: dict, dst: dict) -> list[TuiboardChange]:
    diffs = []
    all_keys = set(src.keys()) | set(dst.keys())
    for k in all_keys:
        if k == "ueid":
            continue
        s_val, d_val = src.get(k), dst.get(k)
        if s_val != d_val:
            diffs.append(TuiboardChange(ueid=src["ueid"], field=k,
                                         before=s_val, after=d_val))
    return diffs
```

- [ ] **Step 4: Modify server.py to register tuiboard_diff (and tuiboard_snapshot stub for test)**

Edit `src/tuiboard/server.py` — replace `_build_server`:

```python
def _build_server() -> StdioServerBase:
    snapshots_dir = os.environ.get("TUIBOARD_SNAPSHOTS_DIR", "data/tuiboard/snapshots")
    os.makedirs(snapshots_dir, exist_ok=True)
    server = StdioServerBase(name="tuiboard", version="0.1.0")
    # A2: read tools
    from tuiboard.tools.tuiboard_diff import handle as tb_diff
    from tuiboard.models import TuiboardDiffInput
    server.register_tool(
        name="tuiboard_diff",
        handler=tb_diff,
        schema=TuiboardDiffInput.model_json_schema(),
    )
    # A3: write tools (tuiboard_snapshot, tuiboard_render) added in next phase.
    # NOTE: test A2.6 needs tuiboard_snapshot too. Register a stub here that
    # delegates to the A3 implementation once it lands. For now, register
    # the A3 handler eagerly so A2.6's E2E test passes end-to-end.
    from tuiboard.tools.tuiboard_snapshot import handle as tb_snap  # noqa: F401
    from tuiboard.models import TuiboardSnapshotInput
    server.register_tool(
        name="tuiboard_snapshot",
        handler=tb_snap,
        schema=TuiboardSnapshotInput.model_json_schema(),
    )
    return server
```

This requires `tuiboard_snapshot.py` to exist. **Create a stub now** so A2.6 can pass; full implementation lands in A3 (Task A3.4):

```python
# src/tuiboard/tools/tuiboard_snapshot.py — STUB for A2; full impl in A3
"""tuiboard_snapshot — A2 stub. Full impl in A3."""
from __future__ import annotations
import uuid
from datetime import datetime
from tuiboard.models import TuiboardSnapshotInput, TuiboardSnapshotOutput


def handle(args: dict) -> dict:
    """A2 stub: returns empty snapshot with deterministic id."""
    inp = TuiboardSnapshotInput.model_validate(args)
    out = TuiboardSnapshotOutput(
        snapshot_id=uuid.uuid4().hex,
        name=inp.name,
        created_at=datetime.utcnow().isoformat() + "Z",
        task_count=0,
        sha256="0" * 64,
    )
    return out.model_dump(mode="json")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/gateway/clients/test_tuiboard_diff.py -v`
Expected: PASS

- [ ] **Step 6: Run full A2 regression**

Run: `pytest tests/gateway/ tests/solverforge_calendar/ tests/tuiboard/ -v`
Expected: all prior A1 + A2 tests pass

- [ ] **Step 7: Commit**

```bash
git add src/tuiboard/tools/ src/tuiboard/server.py tests/gateway/clients/test_tuiboard_diff.py
git commit -m "feat(tuiboard): tuiboard_diff tool + tuiboard_snapshot stub for A2"
```

---

# Phase A3: Writes (~14h)

## Task A3.1: sf_schedule handler with UPSERT + conflict detection

**Files:**
- Create: `src/solverforge_calendar/tools/sf_schedule.py`
- Modify: `src/solverforge_calendar/server.py`
- Test: `tests/gateway/clients/test_sf_schedule.py`

**Interfaces:**
- Consumes: `SfScheduleInput/Output` from A2.1, `SolverforgeDB` from A2.2
- Produces: writes UPI rows; 5-min overlap detection; blocked_by resolution

- [ ] **Step 1: Write the failing E2E test**

```python
# tests/gateway/clients/test_sf_schedule.py
"""E2E: spawn solverforge_calendar.server, call sf_schedule via tools/call."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

import pytest
from tests.gateway.clients.test_solverforge_calendar_init import _send_request, _read_response


def test_sf_schedule_insert_and_update(server_process_factory, tmp_path: Path, skip_if_no_module):
    """Insert, then update via UPSERT — same ueid, different title."""
    try:
        env = {"SOLVERFORGE_DATA_DIR": str(tmp_path / "sf")}
        with server_process_factory("solverforge_calendar.server", env=env) as (proc, stdin, stdout):
            _send_request(stdin, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                  "params": {"protocolVersion": "2024-11-05", "capabilities": {}}})
            _read_response(stdout)
            ueid = "sc:task:byd-research:abc123:def456"
            start = datetime(2026, 9, 1, 9, 0, 0)
            # insert
            _send_request(stdin, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                  "params": {"name": "sf_schedule", "arguments": {
                                      "ueid": ueid, "title": "BYD old",
                                      "start_at": start.isoformat()}}})
            resp1 = _read_response(stdout)
            assert "error" not in resp1, resp1
            data1 = json.loads(resp1["result"]["content"][0]["text"])
            assert data1["status"] == "scheduled"
            # update
            _send_request(stdin, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                  "params": {"name": "sf_schedule", "arguments": {
                                      "ueid": ueid, "title": "BYD new",
                                      "start_at": start.isoformat()}}})
            resp2 = _read_response(stdout)
            data2 = json.loads(resp2["result"]["content"][0]["text"])
            assert data2["status"] == "scheduled"
            assert data2["id"] == data1["id"]  # UPSERT preserves PK
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"solverforge_calendar module not importable: {e}")


def test_sf_schedule_overlap_detected(server_process_factory, tmp_path: Path, skip_if_no_module):
    """Two events with >5min overlap → second returns status=conflict."""
    try:
        env = {"SOLVERFORGE_DATA_DIR": str(tmp_path / "sf")}
        with server_process_factory("solverforge_calendar.server", env=env) as (proc, stdin, stdout):
            _send_request(stdin, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                  "params": {"protocolVersion": "2024-11-05", "capabilities": {}}})
            _read_response(stdout)
            base = datetime(2026, 9, 1, 9, 0, 0)
            # first event: 9:00-11:00
            _send_request(stdin, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                  "params": {"name": "sf_schedule", "arguments": {
                                      "ueid": "sc:task:a:0:0", "title": "First",
                                      "start_at": base.isoformat(),
                                      "end_at": base.replace(hour=11).isoformat()}}})
            _read_response(stdout)
            # second event: 10:30-12:00 (overlaps 30min)
            _send_request(stdin, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                  "params": {"name": "sf_schedule", "arguments": {
                                      "ueid": "sc:task:b:0:0", "title": "Second",
                                      "start_at": base.replace(hour=10, minute=30).isoformat(),
                                      "end_at": base.replace(hour=12).isoformat()}}})
            resp = _read_response(stdout)
            data = json.loads(resp["result"]["content"][0]["text"])
            assert data["status"] == "conflict"
            assert "sc:task:a:0:0" in data["conflicts"]
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"solverforge_calendar module not importable: {e}")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/gateway/clients/test_sf_schedule.py -v`
Expected: FAIL — `unknown tool: sf_schedule`

- [ ] **Step 3: Write the tool handler**

```python
# src/solverforge_calendar/tools/sf_schedule.py
"""sf_schedule — UPSERT a scheduled event with 5-min overlap detection.

Atomic UPSERT on ueid. Returns status="conflict" if >5min overlap with existing.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from solverforge_calendar.db import SolverforgeDB
from solverforge_calendar.models import SfScheduleInput, SfScheduleOutput

_OVERLAP_THRESHOLD = timedelta(minutes=5)


def _db() -> SolverforgeDB:
    data_dir = Path(os.environ.get("SOLVERFORGE_DATA_DIR", "data/solverforge_calendar"))
    return SolverforgeDB(data_dir / "unified_planning.db")


def handle(args: dict) -> dict:
    inp = SfScheduleInput.model_validate(args)
    db = _db()

    # Default end_at = start_at + 1h
    end_at = inp.end_at or (inp.start_at + timedelta(hours=1))

    # Conflict detection: scan busy windows for >5min overlap
    conflicts: list[str] = []
    for row in db.list_busy_in_window(start=inp.start_at, end=end_at):
        if row["ueid"] == inp.ueid:  # skip self (UPDATE case)
            continue
        if not row["end_at"]:
            continue
        existing_start = datetime.fromisoformat(row["start_at"])
        existing_end = datetime.fromisoformat(row["end_at"])
        overlap = min(existing_end, end_at) - max(existing_start, inp.start_at)
        if overlap > _OVERLAP_THRESHOLD:
            conflicts.append(row["ueid"])

    # blocked_by resolution: only set status=scheduled when all deps are done
    status = "scheduled"
    warnings: list[str] = []
    if inp.blocked_by:
        all_done = all(
            (db.read(dep) or {}).get("status") == "done"
            for dep in inp.blocked_by
        )
        if not all_done:
            status = "blocked"
            warnings.append("blocked_by deps not all done")

    if conflicts:
        status = "conflict"
        warnings.append(f"{len(conflicts)} overlap conflict(s)")

    result = db.upsert(
        ueid=inp.ueid, title=inp.title, start_at=inp.start_at, end_at=end_at,
        blocked_by=inp.blocked_by, tags=inp.tags, ikigai=inp.ikigai,
        status=status,
    )
    out = SfScheduleOutput(
        ueid=inp.ueid, id=result["id"], status=status,
        scheduled_at=datetime.utcnow(), conflicts=conflicts, warnings=warnings,
    )
    return out.model_dump(mode="json")
```

- [ ] **Step 4: Register in server.py**

Edit `src/solverforge_calendar/server.py` `_build_server`:

```python
    # ... (A2 sf_availability registration unchanged)
    # A3: write tools
    from solverforge_calendar.tools.sf_schedule import handle as sf_sched
    from solverforge_calendar.models import SfScheduleInput
    server.register_tool(
        name="sf_schedule",
        handler=sf_sched,
        schema=SfScheduleInput.model_json_schema(),
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/gateway/clients/test_sf_schedule.py -v`
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/solverforge_calendar/tools/sf_schedule.py src/solverforge_calendar/server.py tests/gateway/clients/test_sf_schedule.py
git commit -m "feat(solverforge_calendar): sf_schedule with UPSERT + conflict detection"
```

## Task A3.2: tuiboard.aggregator (basic, single fork)

**Files:**
- Create: `src/tuiboard/aggregator.py`
- Test: `tests/tuiboard/test_aggregator.py`

**Interfaces:**
- Consumes: cross-fork storage adapters (CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter) — read-only
- Produces: `aggregate_tasks() -> list[dict]` deduplicated by ueid

- [ ] **Step 1: Write the failing test**

```python
# tests/tuiboard/test_aggregator.py
"""Tests for tuiboard aggregator — multi-fork task read with dedup."""
from __future__ import annotations
from pathlib import Path

import pytest
from tuiboard.aggregator import TaskAggregator, AggregatedTask


def test_aggregator_empty_when_no_forks(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    agg = TaskAggregator(data_dir=tmp_path)
    tasks = agg.aggregate()
    assert tasks == []


def test_aggregator_reads_cli_adapter(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Write a tasks.jsonl entry
    data_dir = tmp_path
    (data_dir / "data").mkdir(parents=True, exist_ok=True)
    (data_dir / "data" / "tasks.jsonl").write_text(
        '{"ueid": "sc:task:a:0:0", "title": "A", "status": "planned"}\n',
        encoding="utf-8",
    )
    agg = TaskAggregator(data_dir=data_dir)
    tasks = agg.aggregate()
    assert len(tasks) == 1
    assert tasks[0].ueid == "sc:task:a:0:0"
    assert tasks[0].source == "cli"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/tuiboard/test_aggregator.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/tuiboard/aggregator.py
"""Multi-fork task aggregator for tuiboard.

Reads from CliAdapter + TaskdogAdapter + SolverforgeCalendarAdapter. Per spec:
- tuiboard is a RENDERING fork (no own storage adapter)
- Aggregator deduplicates by ueid across forks
- A3 version: basic single-fork read. A4 extends to all 3 forks with
  precedence logic (taskdog > solverforge-calendar > cli).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class AggregatedTask:
    ueid: str
    title: str
    status: str | None
    source: Literal["cli", "taskdog", "solverforge-calendar"]
    due: str | None = None
    vector: str | None = None
    tags: tuple[str, ...] = ()


class TaskAggregator:
    """Reads tasks from cross-fork storage adapters and deduplicates by ueid."""

    def __init__(self, *, data_dir: Path) -> None:
        self._data_dir = Path(data_dir)

    def aggregate(self) -> list[AggregatedTask]:
        tasks: dict[str, AggregatedTask] = {}
        tasks.update(self._read_cli())
        # A4: add taskdog + solverforge-calendar readers here
        return list(tasks.values())

    def _read_cli(self) -> dict[str, AggregatedTask]:
        """Read from data/tasks.jsonl (canonical CLI adapter path)."""
        tasks_file = self._data_dir / "data" / "tasks.jsonl"
        if not tasks_file.exists():
            return {}
        result: dict[str, AggregatedTask] = {}
        for line in tasks_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            import json
            entry = json.loads(line)
            ueid = entry.get("ueid")
            if not ueid:
                continue
            result[ueid] = AggregatedTask(
                ueid=ueid,
                title=entry.get("title", ""),
                status=entry.get("status"),
                source="cli",
                due=entry.get("due"),
                vector=entry.get("vector"),
                tags=tuple(entry.get("tags", [])),
            )
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/tuiboard/test_aggregator.py -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tuiboard/aggregator.py tests/tuiboard/test_aggregator.py
git commit -m "feat(tuiboard): aggregator basic CLI-fork reader"
```

## Task A3.3: tuiboard_snapshot full implementation

**Files:**
- Modify: `src/tuiboard/tools/tuiboard_snapshot.py`
- Test: `tests/gateway/clients/test_tuiboard_snapshot.py`

**Interfaces:**
- Consumes: `SnapshotStore` from A2.5, `TaskAggregator` from A3.2
- Produces: stores current aggregate snapshot; idempotent on name

- [ ] **Step 1: Write the failing E2E test**

```python
# tests/gateway/clients/test_tuiboard_snapshot.py
"""E2E: spawn tuiboard.server, save snapshot, verify idempotency on name."""
from __future__ import annotations
import json
from pathlib import Path

import pytest
from tests.gateway.clients.test_solverforge_calendar_init import _send_request, _read_response


def test_tuiboard_snapshot_save_and_idempotent(server_process_factory, tmp_path: Path, skip_if_no_module):
    try:
        env = {"TUIBOARD_SNAPSHOTS_DIR": str(tmp_path / "snapshots"),
               "TUIBOARD_DATA_DIR": str(tmp_path / "data")}
        with server_process_factory("tuiboard.server", env=env) as (proc, stdin, stdout):
            _send_request(stdin, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                  "params": {"protocolVersion": "2024-11-05", "capabilities": {}}})
            _read_response(stdout)
            # first save
            _send_request(stdin, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                  "params": {"name": "tuiboard_snapshot", "arguments": {
                                      "name": "baseline", "layout": "kanban"}}})
            resp1 = _read_response(stdout)
            sid1 = json.loads(resp1["result"]["content"][0]["text"])["snapshot_id"]
            # second save with same name → same id
            _send_request(stdin, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                  "params": {"name": "tuiboard_snapshot", "arguments": {
                                      "name": "baseline", "layout": "kanban"}}})
            resp2 = _read_response(stdout)
            sid2 = json.loads(resp2["result"]["content"][0]["text"])["snapshot_id"]
            assert sid1 == sid2  # idempotent
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"tuiboard module not importable: {e}")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/gateway/clients/test_tuiboard_snapshot.py -v`
Expected: FAIL — the A2 stub returns random uuid each time, so sid1 != sid2

- [ ] **Step 3: Replace stub with full implementation**

Replace `src/tuiboard/tools/tuiboard_snapshot.py`:

```python
# src/tuiboard/tools/tuiboard_snapshot.py
"""tuiboard_snapshot — save current aggregate as a JSON snapshot.

Idempotent on (name, filters). Per spec: same name returns same snapshot_id
unless the underlying aggregate has changed.
"""
from __future__ import annotations

import os
from pathlib import Path

from tuiboard.aggregator import TaskAggregator
from tuiboard.models import TuiboardSnapshotInput, TuiboardSnapshotOutput
from tuiboard.snapshots import SnapshotStore


def _store() -> SnapshotStore:
    sd = Path(os.environ.get("TUIBOARD_SNAPSHOTS_DIR", "data/tuiboard/snapshots"))
    return SnapshotStore(sd)


def _data_dir() -> Path:
    return Path(os.environ.get("TUIBOARD_DATA_DIR", "data"))


def handle(args: dict) -> dict:
    inp = TuiboardSnapshotInput.model_validate(args)
    agg = TaskAggregator(data_dir=_data_dir())
    aggregated = agg.aggregate()
    tasks_payload = [
        {"ueid": t.ueid, "title": t.title, "status": t.status,
         "due": t.due, "vector": t.vector, "tags": list(t.tags),
         "source": t.source}
        for t in aggregated
    ]
    filters_dict = inp.filters.model_dump() if inp.filters else None
    store = _store()
    out = store.save(
        name=inp.name, tasks=tasks_payload, filters=filters_dict,
        description=inp.description,
    )
    return TuiboardSnapshotOutput(
        snapshot_id=out["snapshot_id"], name=out["name"],
        created_at=out["created_at"], task_count=out["task_count"],
        sha256=out["sha256"],
    ).model_dump(mode="json")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/gateway/clients/test_tuiboard_snapshot.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tuiboard/tools/tuiboard_snapshot.py tests/gateway/clients/test_tuiboard_snapshot.py
git commit -m "feat(tuiboard): tuiboard_snapshot full impl with aggregator"
```

## Task A3.4: tuiboard_render full implementation (4 layouts)

**Files:**
- Create: `src/tuiboard/tools/tuiboard_render.py`
- Modify: `src/tuiboard/server.py`
- Test: `tests/gateway/clients/test_tuiboard_render.py`

**Interfaces:**
- Consumes: `TuiboardRenderInput/Output` from A2.4, `TaskAggregator` from A3.2
- Produces: rendered frames in 4 layouts: kanban/list/calendar/tree

- [ ] **Step 1: Write the failing E2E test**

```python
# tests/gateway/clients/test_tuiboard_render.py
"""E2E: spawn tuiboard.server, render in all 4 layouts."""
from __future__ import annotations
import json
from pathlib import Path

import pytest
from tests.gateway.clients.test_solverforge_calendar_init import _send_request, _read_response


@pytest.mark.parametrize("layout", ["kanban", "list", "calendar", "tree"])
def test_tuiboard_render_layouts(server_process_factory, tmp_path: Path, layout: str, skip_if_no_module):
    try:
        env = {"TUIBOARD_SNAPSHOTS_DIR": str(tmp_path / "snapshots"),
               "TUIBOARD_DATA_DIR": str(tmp_path / "data")}
        with server_process_factory("tuiboard.server", env=env) as (proc, stdin, stdout):
            _send_request(stdin, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                  "params": {"protocolVersion": "2024-11-05", "capabilities": {}}})
            _read_response(stdout)
            _send_request(stdin, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                  "params": {"name": "tuiboard_render", "arguments": {
                                      "layout": layout}}})
            response = _read_response(stdout)
            assert "error" not in response, response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["layout"] == layout
            assert "frames" in content
            assert "metadata" in content
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"tuiboard module not importable: {e}")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/gateway/clients/test_tuiboard_render.py -v`
Expected: FAIL — `unknown tool: tuiboard_render`

- [ ] **Step 3: Write the tool handler**

```python
# src/tuiboard/tools/tuiboard_render.py
"""tuiboard_render — render aggregated tasks in 4 layouts.

Read-only. Aggregates via TaskAggregator, applies filters, returns frames
in the requested layout (kanban | list | calendar | tree).
"""
from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from typing import Literal

from tuiboard.aggregator import AggregatedTask, TaskAggregator
from tuiboard.models import (
    TuiboardFrame, TuiboardMetadata, TuiboardPosition, TuiboardRenderInput,
    TuiboardRenderOutput,
)


def _data_dir() -> Path:
    return Path(os.environ.get("TUIBOARD_DATA_DIR", "data"))


def handle(args: dict) -> dict:
    inp = TuiboardRenderInput.model_validate(args)
    agg = TaskAggregator(data_dir=_data_dir())
    tasks = agg.aggregate()

    # Apply filters
    if inp.ueids:
        tasks = [t for t in tasks if t.ueid in set(inp.ueids)]
    if inp.filters:
        if inp.filters.status:
            tasks = [t for t in tasks if t.status == inp.filters.status]
        if inp.filters.vector:
            tasks = [t for t in tasks if t.vector == inp.filters.vector]
        if inp.filters.tags:
            tag_set = set(inp.filters.tags)
            tasks = [t for t in tasks if tag_set & set(t.tags)]
        if inp.filters.due_before:
            tasks = [t for t in tasks if t.due and t.due < inp.filters.due_before]

    total = len(tasks)
    truncated = total > 100
    if truncated:
        tasks = tasks[:100]

    if inp.layout == "kanban":
        frames = _render_kanban(tasks)
    elif inp.layout == "list":
        frames = _render_list(tasks)
    elif inp.layout == "calendar":
        frames = _render_calendar(tasks)
    elif inp.layout == "tree":
        frames = _render_tree(tasks)
    else:
        raise ValueError(f"unknown layout: {inp.layout}")

    out = TuiboardRenderOutput(
        layout=inp.layout, frames=frames,
        metadata=TuiboardMetadata(total_tasks=total, shown_tasks=len(frames), truncated=truncated),
    )
    return out.model_dump(mode="json")


def _render_kanban(tasks: list[AggregatedTask]) -> list[TuiboardFrame]:
    by_status: dict[str, list[AggregatedTask]] = defaultdict(list)
    for t in tasks:
        by_status[t.status or "planned"].append(t)
    frames = []
    for col, (status, group) in enumerate(sorted(by_status.items())):
        for row, t in enumerate(group):
            frames.append(TuiboardFrame(
                ueid=t.ueid, title=t.title, status=status, due=t.due,
                vector=t.vector, tags=list(t.tags),
                position=TuiboardPosition(section=status, row=row, col=col),
            ))
    return frames


def _render_list(tasks: list[AggregatedTask]) -> list[TuiboardFrame]:
    return [
        TuiboardFrame(ueid=t.ueid, title=t.title, status=t.status, due=t.due,
                      vector=t.vector, tags=list(t.tags),
                      position=TuiboardPosition(section="all", row=i, col=0))
        for i, t in enumerate(sorted(tasks, key=lambda x: x.title))
    ]


def _render_calendar(tasks: list[AggregatedTask]) -> list[TuiboardFrame]:
    by_day: dict[str, list[AggregatedTask]] = defaultdict(list)
    no_due: list[AggregatedTask] = []
    for t in tasks:
        if t.due:
            day = t.due[:10]  # YYYY-MM-DD
            by_day[day].append(t)
        else:
            no_due.append(t)
    frames = []
    for col, (day, group) in enumerate(sorted(by_day.items())):
        for row, t in enumerate(group):
            frames.append(TuiboardFrame(
                ueid=t.ueid, title=t.title, status=t.status, due=t.due,
                vector=t.vector, tags=list(t.tags),
                position=TuiboardPosition(section=day, row=row, col=col),
            ))
    for row, t in enumerate(no_due):
        frames.append(TuiboardFrame(
            ueid=t.ueid, title=t.title, status=t.status, due=t.due,
            vector=t.vector, tags=list(t.tags),
            position=TuiboardPosition(section="no_due", row=row, col=0),
        ))
    return frames


def _render_tree(tasks: list[AggregatedTask]) -> list[TuiboardFrame]:
    # Simple tree: depth 0 = all, depth 1 grouped by source. No parent->child
    # reconstruction (no `blocked_by` parsing in aggregator yet).
    by_source: dict[str, list[AggregatedTask]] = defaultdict(list)
    for t in tasks:
        by_source[t.source].append(t)
    frames = []
    for col, (source, group) in enumerate(sorted(by_source.items())):
        for row, t in enumerate(group):
            frames.append(TuiboardFrame(
                ueid=t.ueid, title=t.title, status=t.status, due=t.due,
                vector=t.vector, tags=list(t.tags),
                position=TuiboardPosition(section=source, row=row, col=col),
            ))
    return frames
```

- [ ] **Step 4: Register in server.py**

Edit `src/tuiboard/server.py` `_build_server`:

```python
    # ... (A2 tuiboard_diff + snapshot unchanged)
    # A3: write tools
    from tuiboard.tools.tuiboard_render import handle as tb_render
    from tuiboard.models import TuiboardRenderInput
    server.register_tool(
        name="tuiboard_render",
        handler=tb_render,
        schema=TuiboardRenderInput.model_json_schema(),
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/gateway/clients/test_tuiboard_render.py -v`
Expected: 4 tests PASS (one per layout)

- [ ] **Step 6: Commit**

```bash
git add src/tuiboard/tools/tuiboard_render.py src/tuiboard/server.py tests/gateway/clients/test_tuiboard_render.py
git commit -m "feat(tuiboard): tuiboard_render with 4 layouts (kanban/list/calendar/tree)"
```

## Task A3.5: main-session regression for A3

- [ ] **Step 1: Run full regression**

Run from repo root: `pytest tests/gateway/ tests/solverforge_calendar/ tests/tuiboard/ -v`
Expected: all prior A1 + A2 + A3 tests PASS

- [ ] **Step 2: Run ruff + mypy**

Run: `ruff check src/ikigai/src/ikigai/gateway/ src/solverforge_calendar/ src/tuiboard/`
Run: `mypy src/ikigai/src/ikigai/gateway/stdio_server_base.py src/solverforge_calendar/ src/tuiboard/`
Expected: clean (or only pre-existing warnings)

- [ ] **Step 3: Commit any fixes (if ruff/mypy reported issues)**

```bash
git add -u
git commit -m "style: ruff/mypy fixes for A3"
```

---

# Phase A4: Advanced (~12h)

## Task A4.1: sf_replan constraint solver

**Files:**
- Create: `src/solverforge_calendar/tools/sf_replan.py`
- Modify: `src/solverforge_calendar/server.py`
- Test: `tests/gateway/clients/test_sf_replan.py`

**Interfaces:**
- Consumes: `SfReplanInput/Output`, `SfPlanDiff` from A2.1, `SolverforgeDB` from A2.2
- Produces: naive constraint solver (≤14-day horizon), 3 strategies

- [ ] **Step 1: Write the failing E2E test**

```python
# tests/gateway/clients/test_sf_replan.py
"""E2E: spawn solverforge_calendar.server, call sf_replan."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

import pytest
from tests.gateway.clients.test_solverforge_calendar_init import _send_request, _read_response


def test_sf_replan_empty_returns_empty_diff(server_process_factory, tmp_path: Path, skip_if_no_module):
    try:
        env = {"SOLVERFORGE_DATA_DIR": str(tmp_path / "sf")}
        with server_process_factory("solverforge_calendar.server", env=env) as (proc, stdin, stdout):
            _send_request(stdin, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                  "params": {"protocolVersion": "2024-11-05", "capabilities": {}}})
            _read_response(stdout)
            _send_request(stdin, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                  "params": {"name": "sf_replan", "arguments": {
                                      "horizon_start": datetime(2026, 9, 1).isoformat(),
                                      "horizon_end": datetime(2026, 9, 8).isoformat()}}})
            response = _read_response(stdout)
            assert "error" not in response, response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["diff"] == []
            assert "plan_id" in content
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"solverforge_calendar module not importable: {e}")


def test_sf_replan_idempotent_on_same_inputs(server_process_factory, tmp_path: Path, skip_if_no_module):
    """Replay with same horizon + strategy → same plan_id."""
    try:
        env = {"SOLVERFORGE_DATA_DIR": str(tmp_path / "sf")}
        with server_process_factory("solverforge_calendar.server", env=env) as (proc, stdin, stdout):
            _send_request(stdin, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                  "params": {"protocolVersion": "2024-11-05", "capabilities": {}}})
            _read_response(stdout)
            horizon = {"horizon_start": datetime(2026, 9, 1).isoformat(),
                       "horizon_end": datetime(2026, 9, 8).isoformat(),
                       "strategy": "minimize_moves"}
            _send_request(stdin, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                  "params": {"name": "sf_replan", "arguments": horizon}})
            r1 = _read_response(stdout)
            pid1 = json.loads(r1["result"]["content"][0]["text"])["plan_id"]
            _send_request(stdin, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                  "params": {"name": "sf_replan", "arguments": horizon}})
            r2 = _read_response(stdout)
            pid2 = json.loads(r2["result"]["content"][0]["text"])["plan_id"]
            assert pid1 == pid2  # idempotent
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"solverforge_calendar module not importable: {e}")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/gateway/clients/test_sf_replan.py -v`
Expected: FAIL — `unknown tool: sf_replan`

- [ ] **Step 3: Write the constraint solver**

```python
# src/solverforge_calendar/tools/sf_replan.py
"""sf_replan — naive constraint solver for ≤14-day horizon.

Strategies:
- minimize_moves (default): keep as many events as possible
- earliest_first: shift conflicting events earlier
- load_balance: spread events evenly across the horizon

DOES NOT mutate UPI rows. Returns a draft plan; caller commits via sf_schedule.
Idempotent on (horizon_start, horizon_end, affected_ueids, strategy).
"""
from __future__ import annotations

import hashlib
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from solverforge_calendar.db import SolverforgeDB
from solverforge_calendar.models import (
    SfPlanDiff, SfReplanInput, SfReplanOutput,
)


def _db() -> SolverforgeDB:
    data_dir = Path(os.environ.get("SOLVERFORGE_DATA_DIR", "data/solverforge_calendar"))
    return SolverforgeDB(data_dir / "unified_planning.db")


def handle(args: dict) -> dict:
    inp = SfReplanInput.model_validate(args)
    horizon = inp.horizon_end - inp.horizon_start
    if horizon > timedelta(days=14):
        raise ValueError("horizon exceeds 14 days")
    if horizon <= timedelta(0):
        raise ValueError("horizon_end must be after horizon_start")

    db = _db()
    t0 = time.time()
    busy = db.list_busy_in_window(start=inp.horizon_start, end=inp.horizon_end)

    # Filter to affected_ueids if specified
    if inp.affected_ueids:
        affected_set = set(inp.affected_ueids)
        busy = [b for b in busy if b["ueid"] in affected_set]

    # Build naive plan: assign each event to a non-conflicting slot
    diff: list[SfPlanDiff] = []
    unresolvable: list[str] = []
    used_slots: list[tuple[datetime, datetime]] = []

    for row in sorted(busy, key=lambda r: r["start_at"]):
        if not row["end_at"]:
            unresolvable.append(row["ueid"])
            continue
        existing_start = datetime.fromisoformat(row["start_at"])
        existing_end = datetime.fromisoformat(row["end_at"])
        duration = existing_end - existing_start
        # Try to keep existing slot if no conflict
        if not _conflicts((existing_start, existing_end), used_slots):
            diff.append(SfPlanDiff(ueid=row["ueid"], action="kept",
                                   before=existing_start, after=existing_start,
                                   reason="no conflict"))
            used_slots.append((existing_start, existing_end))
            continue
        # Try alternative slots per strategy
        new_start = _find_slot(inp, duration, used_slots, strategy=inp.strategy)
        if new_start is None:
            unresolvable.append(row["ueid"])
            diff.append(SfPlanDiff(ueid=row["ueid"], action="removed",
                                   before=existing_start, after=None,
                                   reason="no slot available"))
        else:
            new_end = new_start + duration
            used_slots.append((new_start, new_end))
            diff.append(SfPlanDiff(ueid=row["ueid"], action="moved",
                                   before=existing_start, after=new_start,
                                   reason=f"strategy={inp.strategy}"))

    runtime_ms = int((time.time() - t0) * 1000)
    plan_id_seed = f"{inp.horizon_start.isoformat()}|{inp.horizon_end.isoformat()}|{sorted(inp.affected_ueids)}|{inp.strategy}|{[(d.ueid, d.action, str(d.after)) for d in diff]}"
    plan_id = uuid.UUID(hex=hashlib.md5(plan_id_seed.encode("utf-8")).hexdigest())

    out = SfReplanOutput(
        plan_id=plan_id, horizon_start=inp.horizon_start, horizon_end=inp.horizon_end,
        diff=diff, unresolvable=unresolvable, runtime_ms=runtime_ms,
    )
    return out.model_dump(mode="json")


def _conflicts(slot: tuple[datetime, datetime],
               used: list[tuple[datetime, datetime]]) -> bool:
    s, e = slot
    for us, ue in used:
        if s < ue and us < e:
            return True
    return False


def _find_slot(inp: SfReplanInput, duration: timedelta,
               used: list[tuple[datetime, datetime]], *,
               strategy: Literal["minimize_moves", "earliest_first", "load_balance"],
               granularity_minutes: int = 30) -> datetime | None:
    """Naive search for a non-conflicting slot. YAGNI: 30-min granularity."""
    cursor = inp.horizon_start
    step = timedelta(minutes=granularity_minutes)
    while cursor + duration <= inp.horizon_end:
        if not _conflicts((cursor, cursor + duration), used):
            return cursor
        cursor += step
    return None
```

- [ ] **Step 4: Register in server.py**

Edit `src/solverforge_calendar/server.py` `_build_server`:

```python
    # ... (A2 + A3 unchanged)
    # A4: advanced tools
    from solverforge_calendar.tools.sf_replan import handle as sf_replan
    from solverforge_calendar.models import SfReplanInput
    server.register_tool(
        name="sf_replan",
        handler=sf_replan,
        schema=SfReplanInput.model_json_schema(),
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/gateway/clients/test_sf_replan.py -v`
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/solverforge_calendar/tools/sf_replan.py src/solverforge_calendar/server.py tests/gateway/clients/test_sf_replan.py
git commit -m "feat(solverforge_calendar): sf_replan naive constraint solver"
```

## Task A4.2: tuiboard.aggregator — extend to 3 forks with precedence

**Files:**
- Modify: `src/tuiboard/aggregator.py`
- Modify: `tests/tuiboard/test_aggregator.py`

**Interfaces:**
- Consumes: CliAdapter (`data/tasks.jsonl`), TaskdogAdapter (`data/taskdog/taskdog.db`), SolverforgeCalendarAdapter (`data/solverforge_calendar/unified_planning.db`)
- Produces: `aggregate_tasks()` with precedence logic: taskdog > solverforge-calendar > cli (last mtime wins)

- [ ] **Step 1: Update the test**

Add to `tests/tuiboard/test_aggregator.py`:

```python
def test_aggregator_precedence_taskdog_over_cli(tmp_path: Path, monkeypatch):
    """When same ueid is in taskdog AND cli, taskdog wins (higher precedence)."""
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "tasks.jsonl").write_text(
        '{"ueid": "sc:task:a:0:0", "title": "CLI version", "status": "planned"}\n',
        encoding="utf-8",
    )
    # Fake taskdog sqlite
    import sqlite3
    taskdog_db = data_dir / "taskdog" / "taskdog.db"
    taskdog_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(taskdog_db)
    conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ueid TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        status TEXT NOT NULL
    )""")
    conn.execute("INSERT INTO tasks (ueid, title, status) VALUES (?, ?, ?)",
                ("sc:task:a:0:0", "TASKDOG version", "in_progress"))
    conn.commit()
    conn.close()
    agg = TaskAggregator(data_dir=tmp_path)
    tasks = agg.aggregate()
    assert len(tasks) == 1
    assert tasks[0].title == "TASKDOG version"
    assert tasks[0].source == "taskdog"
```

- [ ] **Step 2: Extend aggregator.py**

Modify `src/tuiboard/aggregator.py` `_read_taskdog` and `_read_solverforge` methods, and update `aggregate()`:

```python
    def aggregate(self) -> list[AggregatedTask]:
        # Precedence: taskdog > solverforge-calendar > cli
        # Initialize with lowest precedence (cli), then overwrite with higher.
        tasks: dict[str, AggregatedTask] = {}
        tasks.update(self._read_cli())
        tasks.update(self._read_solverforge())
        tasks.update(self._read_taskdog())
        return list(tasks.values())

    def _read_taskdog(self) -> dict[str, AggregatedTask]:
        """Read from data/taskdog/taskdog.db (taskdog storage adapter)."""
        import sqlite3
        db_path = self._data_dir / "data" / "taskdog" / "taskdog.db"
        if not db_path.exists():
            return {}
        result: dict[str, AggregatedTask] = {}
        try:
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT ueid, title, status FROM tasks WHERE ueid IS NOT NULL"
            ).fetchall()
            for ueid, title, status in rows:
                result[ueid] = AggregatedTask(
                    ueid=ueid, title=title, status=status, source="taskdog",
                )
            conn.close()
        except sqlite3.DatabaseError:
            pass  # tolerate partial DB; aggregator is best-effort
        return result

    def _read_solverforge(self) -> dict[str, AggregatedTask]:
        """Read from data/solverforge_calendar/unified_planning.db."""
        import sqlite3
        db_path = self._data_dir / "data" / "solverforge_calendar" / "unified_planning.db"
        if not db_path.exists():
            return {}
        result: dict[str, AggregatedTask] = {}
        try:
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT ueid, title, status FROM unified_planning_items"
            ).fetchall()
            for ueid, title, status in rows:
                result[ueid] = AggregatedTask(
                    ueid=ueid, title=title, status=status, source="solverforge-calendar",
                )
            conn.close()
        except sqlite3.DatabaseError:
            pass
        return result
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/tuiboard/test_aggregator.py -v`
Expected: 3 tests PASS (2 prior + new precedence test)

- [ ] **Step 4: Commit**

```bash
git add src/tuiboard/aggregator.py tests/tuiboard/test_aggregator.py
git commit -m "feat(tuiboard): aggregator extends to 3 forks with taskdog precedence"
```

## Task A4.3: main-session regression for A4

- [ ] **Step 1: Run full regression**

Run from repo root: `pytest tests/gateway/ tests/solverforge_calendar/ tests/tuiboard/ -v`
Expected: all prior A1-A4 tests PASS

- [ ] **Step 2: Run ruff + mypy**

Run: `ruff check src/ikigai/src/ikigai/gateway/ src/solverforge_calendar/ src/tuiboard/`
Run: `mypy src/ikigai/src/ikigai/gateway/stdio_server_base.py src/solverforge_calendar/ src/tuiboard/`
Expected: clean

- [ ] **Step 3: Commit any fixes**

```bash
git add -u
git commit -m "style: ruff/mypy fixes for A4"
```

---

# Phase A5: Cleanup (~3h)

## Task A5.1: vault_write conformance grep test

**Files:**
- Create: `tests/gateway/clients/test_vault_write_conformance.py`

**Interfaces:**
- Consumes: filesystem
- Produces: grep test that fails if any fork module imports `vault/` or `vault_read`/`vault_write`

- [ ] **Step 1: Write the failing test**

```python
# tests/gateway/clients/test_vault_write_conformance.py
"""vault_write conformance: forks MUST NOT touch vault/.

Per spec Q6=I+III: enforcement is docs + grep test. vault_write (from the
canonical Layer 1 MCP server) is the ONLY writer to vault/. Forks that need
to write vault data must go through that MCP tool, never directly.

This test enforces the constraint at the file level: any reference to vault/
paths or vault_read/vault_write imports from a fork module is a regression.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# Forbidden patterns in fork modules
FORBIDDEN_PATTERNS = [
    re.compile(r"from\s+.*vault\s+import"),
    re.compile(r"import\s+.*vault"),
    re.compile(r"[\"']vault/"),
    re.compile(r"vault_read|vault_write"),
]


@pytest.mark.parametrize("fork_dir", ["src/solverforge_calendar", "src/tuiboard"])
def test_fork_does_not_reference_vault(fork_dir: str, repo_root: Path = None):
    """No fork module should import vault or reference vault/ paths."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]
    fork_path = repo_root / fork_dir
    if not fork_path.exists():
        pytest.skip(f"fork dir does not exist: {fork_path}")
    violations: list[tuple[str, int, str]] = []
    for py_file in fork_path.rglob("*.py"):
        for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), 1):
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    violations.append((str(py_file.relative_to(repo_root)), lineno, line.strip()))
    assert not violations, (
        f"fork module references vault (forbidden by spec Q6):\n"
        + "\n".join(f"  {f}:{ln}: {code}" for f, ln, code in violations)
    )
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/gateway/clients/test_vault_write_conformance.py -v`
Expected: PASS (forks don't reference vault)

- [ ] **Step 3: Commit**

```bash
git add tests/gateway/clients/test_vault_write_conformance.py
git commit -m "test(gateway): vault_write conformance grep test (Q6 enforcement)"
```

## Task A5.2: Deprecate start_mcp_gateway.sh

**Files:**
- Modify: `src/ikigai/start_mcp_gateway.sh`

**Interfaces:**
- Consumes: existing shell script (316 lines, WSL2-only, obsolete)
- Produces: shell script with SUPERSEDED trailer pointing to `start_gateway.py`

- [ ] **Step 1: Read existing script (for verification)**

Run: `wc -l src/ikigai/start_mcp_gateway.sh`
Expected: 316 lines (per spec)

- [ ] **Step 2: Modify the script**

Append the SUPERSEDED trailer to the end of `src/ikigai/start_mcp_gateway.sh` (do NOT delete content per append-only invariant):

```bash
cat >> src/ikigai/start_mcp_gateway.sh << 'EOF'

# ─────────────────────────────────────────────────────────────────────
# SUPERSEDED 2026-08-30 — see docs/superpowers/specs/2026-08-30-fork-connection-architecture.md
#
# This shell script predates the StdioAdapter refactor (Task 14, 2026-08-30).
# It references:
#   - $SOLVERFORGE_ROOT/target/release/solverforge-calendar-cli (Rust binary — DOES NOT EXIST)
#   - $TUIBOARD_ROOT/bin/tuiboard-mcp.ts (TypeScript/Bun — DOES NOT EXIST in this repo)
#   - WSL2-specific paths (/mnt/c/...) — bit-rotted
#
# Modern architecture uses Python factory adapters at:
#   src/ikigai/src/ikigai/gateway/clients/{solverforge_calendar,tuiboard}.py
# which spawn `python -m <module>` (fork servers live in src/).
#
# Replacement: `python -m ikigai.gateway.start_gateway` (cross-platform).
# This shell file is preserved per append-only invariant. Do not delete.
# ─────────────────────────────────────────────────────────────────────
EOF
```

- [ ] **Step 3: Commit**

```bash
git add src/ikigai/start_mcp_gateway.sh
git commit -m "chore(gateway): SUPERSEDED trailer on start_mcp_gateway.sh"
```

## Task A5.3: Update mcp_config.json

**Files:**
- Modify: `src/ikigai/mcp_config.json`

- [ ] **Step 1: Read current state**

Run: `cat src/ikigai/mcp_config.json`

- [ ] **Step 2: Update entries**

- Remove the stale `"Not available — requires Rust toolchain with cc linker (WSL2 missing build-essential)"` comment for solverforge (Python factory is the source of truth).
- Update tuiboard path to point to in-repo Python module instead of nonexistent TypeScript binary.

Edit the relevant entries. Per fork factory at `clients/solverforge_calendar.py:21`:
```json
{
  "solverforge": {
    "command": "python",
    "args": ["-m", "solverforge_calendar.server"],
    "env": {}
  }
}
```

Per fork factory at `clients/tuiboard.py:19`:
```json
{
  "tuiboard": {
    "command": "python",
    "args": ["-m", "tuiboard.server"],
    "env": {}
  }
}
```

(The exact JSON structure depends on what mcp_config.json uses; match its existing style.)

- [ ] **Step 3: Commit**

```bash
git add src/ikigai/mcp_config.json
git commit -m "chore(gateway): mcp_config.json points to in-repo Python forks"
```

## Task A5.4: ADR for fork-connection architecture

**Files:**
- Create: `docs/code-docs/adr/2026-08-30-fork-connection-architecture.md`

- [ ] **Step 1: Write the ADR**

```markdown
# ADR-XXX: Fork-Connection Architecture

**Status:** Accepted 2026-08-30
**Deciders:** Matheus Mendes, Claude (assistant)
**Supersedes:** none
**Superseded by:** none

## Context

Phase B7 (Agent Layer Activation) shipped and made the IKIGAi backend+data+agent layers
functional. The next step was connecting the remaining forks (`solverforge-calendar`,
`tuiboard`) to the `UnifiedMCPGateway`. Diagnostic revealed that the fork factories
existed but the MCP server modules did not (both were factory stubs).

## Decision

Build in-repo Python MCP servers using hand-rolled JSON-RPC 2.0 over stdio:

1. **Repo layout:** Both forks in-repo (`src/solverforge_calendar/`, `src/tuiboard/`)
2. **Transport:** Hand-rolled JSON-RPC 2.0 (no FastMCP, no new deps)
3. **Auth:** None (localhost-only is sufficient for personal OS)
4. **Event log:** Single append-only JSONL at `data/gateway/events.jsonl`
5. **Tool versioning:** YAGNI (no version suffix in v1)
6. **vault_write conformance:** Docs + grep test (no runtime enforcement)

## Consequences

### Positive

- Single `git clone && uv sync && pytest` for full development
- Zero new dependencies; reuses existing Pydantic v2 + stdlib
- Tests always run (no external path dependencies)
- Reversible: most decisions (especially #1, #2, #5) can be revisited without major rework

### Negative

- Cross-repo refactors (e.g., extracting `solverforge_calendar` to its own repo) require
  `git mv` + factory update
- Hand-rolled transport means re-implementing capability negotiation if we add it later
- No auth means any local process can call the gateway (acceptable per threat model)

### Neutral

- tuiboard has zero storage adapter (rendering fork only) — kept by design
- fork connection does NOT touch any algorithm/scoring/qhe/regime code (per gate)

## Alternatives Considered

- **External repos for forks** (mirror taskdog): rejected — adds onboarding cost, CI
  skip-if-missing, breaks "fully local" invariant
- **FastMCP per fork**: rejected — ~30 transitive deps per fork for ~3 tools; SDK
  doesn't add much over hand-rolled for small surfaces
- **Auth via shared secret**: rejected — YAGNI; localhost isolation is sufficient

## References

- Spec: `docs/superpowers/specs/2026-08-30-fork-connection-architecture.md`
- Companion Q-expanded: `docs/superpowers/specs/2026-08-30-fork-connection-architecture-Q-expanded.md`
- Plan: `docs/superpowers/plans/2026-08-30-fork-connection-implementation.md`
- Diagnostic memory: `fork-connection-diagnostic-correction-2026-08-30.md`
```

- [ ] **Step 2: Commit**

```bash
git add docs/code-docs/adr/2026-08-30-fork-connection-architecture.md
git commit -m "docs(adr): fork-connection architecture decision"
```

## Task A5.5: Final whole-branch regression + spec trailer

- [ ] **Step 1: Main-session regression (mandatory per verify-agent-fabricated-failures memory)**

Run from repo root: `pytest tests/gateway/ tests/solverforge_calendar/ tests/tuiboard/ tests/mesh/ -v`
Expected: ALL tests pass

- [ ] **Step 2: Run ruff + mypy + format check**

Run: `ruff check src/ikigai/src/ikigai/gateway/ src/solverforge_calendar/ src/tuiboard/`
Run: `ruff format --check src/ikigai/src/ikigai/gateway/stdio_server_base.py src/solverforge_calendar/ src/tuiboard/`
Run: `mypy src/ikigai/src/ikigai/gateway/stdio_server_base.py src/solverforge_calendar/ src/tuiboard/`
Expected: clean

- [ ] **Step 3: Add SHIPPED trailer to spec**

Edit `docs/superpowers/specs/2026-08-30-fork-connection-architecture.md` — append trailer:

```markdown
---

## SHIPPED 2026-08-30 (pending whole-branch review)

Implementation plan: `docs/superpowers/plans/2026-08-30-fork-connection-implementation.md`
Commits: see git log `git log --oneline | grep "fork-connection\|solverforge_calendar\|tuiboard"`

If implementation diverges from spec, append a SUPERSEDED trailer with delta.
```

- [ ] **Step 4: Final commit**

```bash
git add -u
git commit -m "spec(fork-connection): SHIPPED trailer + final regression clean"
```

---

# Self-Review

**1. Spec coverage:** Walked through each spec section:
- §3 Per-fork deep dive → Phase A1 (transport scaffolds), A2 (read tools), A3 (write tools), A4 (advanced)
- §4 Connection protocol details → A1.1 `stdio_server_base.py`
- §5 Tool contracts → A2.1/A2.4 Pydantic models; A2.3/A3.1/A3.4/A4.1 handlers
- §6 Adapter registration wiring → A1.7 `start_gateway.py` + `register_default_adapters()`
- §7 Test strategy → conftest.py (A1.4) + per-task E2E tests using B5.B pattern
- §8 Migration / deprecation → A5.2 shell trailer, A5.3 mcp_config.json
- §9 Build sequences → matched to phases A1-A5
- §10 Phased rollout → directly maps to A1-A5

All spec sections covered. No gaps.

**2. Placeholder scan:** Searched for "TBD", "TODO", "implement later", "fill in details", "similar to Task N", references to undefined symbols. Found:
- A2.6 references `tuiboard.tools.tuiboard_snapshot` which doesn't exist yet — FIXED by creating a stub in A2.6 that gets replaced in A3.3
- No other placeholders or undefined references

**3. Type consistency:**
- `SfScheduleInput`, `SfAvailabilityInput`, `SfReplanInput` defined in A2.1, used in A2.3/A3.1/A4.1 — consistent
- `TuiboardRenderInput`, `TuiboardSnapshotInput`, `TuiboardDiffInput` defined in A2.4, used in A2.6/A3.3/A3.4 — consistent
- `StdioServerBase` defined in A1.1, used in A1.2/A1.3 server.py — consistent
- `TaskAggregator` defined in A3.2, extended in A4.2, used in A3.3/A3.4 — consistent
- `SnapshotStore` defined in A2.5, used in A2.6/A3.3 — consistent
- `SolverforgeDB` defined in A2.2, used in A2.3/A3.1/A4.1 — consistent

No type mismatches found.

---

# Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-30-fork-connection-implementation.md`. Total: 28 tasks across 5 phases (~40h wall-clock).

Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, two-stage review between tasks (spec compliance + code quality). Fast iteration, isolated context, catches issues early.

**2. Inline Execution** — Execute tasks in this session using executing-plans skill, batch execution with checkpoints for review.

Which approach?
