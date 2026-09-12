"""Stdio smoke test for the Path 3 taskdog MCP server.

Drives ``taskdog_tools.mcp`` as a real subprocess over line-delimited
JSON-RPC on stdio — the wire protocol MCP stdio transport uses (one
JSON-RPC message per ``\\n``-terminated line). Complements the in-process
tests in test_taskdog_mcp_path3.py which only exercise the tool functions
with mocked adapter.

End-to-end checks:
  1. The server module imports cleanly and exposes its FastMCP instance.
  2. The MCP handshake (initialize → notifications/initialized) completes.
  3. tools/list returns exactly the 3 read-only Path 3 tools.
  4. tools/call round-trips: taskdog_supports_field, taskdog_list,
     taskdog_read (with isolated temp DB so the test does not touch
     data/taskdog/tasks.db on the host).

No pytest fixtures: pytest-asyncio's autouse event_loop walks
AppData\\\\Local\\\\Temp\\\\pytest-of-mathe which is locked on this Windows
host by sibling pytest runs. A plain module-level scratch dir + manual
cleanup is the only reliable path on this host.
"""

from __future__ import annotations

import json
import queue
import shutil
import sqlite3
import sys
import textwrap
import threading
import time
import uuid
from pathlib import Path

PYTHON = sys.executable
REPO = Path(__file__).resolve().parents[3]  # src/ikigai/tests -> repo root
SCRATCH = REPO / ".tmp" / "taskdog_mcp_stdio"
SCRATCH.mkdir(parents=True, exist_ok=True)

# The server-side runner. Lives in a separate file because stdio is the
# JSON-RPC transport — we cannot share it with the test driver's REPL.
# Both REPO and REPO/src must be on sys.path: REPO so ``from src.X`` works
# (taskdog_tools uses dotted-prefix); REPO/src so ``from contracts.X``
# works (the mcp_server package __init__.py eagerly imports
# investigation_complete, which uses the bare prefix).
RUNNER = textwrap.dedent(
    f"""
    import asyncio, sys
    sys.path.insert(0, {str(REPO)!r})
    sys.path.insert(0, {str(REPO / 'src')!r})
    from src.ikigai.src.mcp_server.taskdog_tools import mcp
    asyncio.run(mcp.run_stdio_async())
    """
).strip()


# ──────── Line-delimited JSON helpers ────────


def _write_message(stream, payload: dict) -> None:
    """Write one JSON-RPC message + LF terminator (line-delimited framing)."""
    stream.write(json.dumps(payload, default=str) + "\n")
    stream.flush()


def _read_message(stream, timeout_s: float = 10.0) -> dict:
    """Read one ``\\n``-terminated JSON-RPC message.

    Windows pipes don't accept ``select.select()`` (WinError 10038), so
    we offload the blocking read onto a daemon thread that pushes each
    complete line into a queue. The main thread polls the queue with a
    deadline.

    Returns notifications as ``{"_notification": True, ...}`` and lets
    real responses fall through untouched.
    """
    sentinel = object()

    class _Reader(threading.Thread):
        def __init__(self) -> None:
            super().__init__(daemon=True)
            self.q: queue.Queue = queue.Queue()

        def run(self) -> None:
            try:
                for line in stream:
                    line = line.rstrip("\r\n")
                    if not line:
                        continue
                    self.q.put(line)
            except Exception as exc:  # noqa: BLE001
                self.q.put(exc)
            finally:
                self.q.put(sentinel)

    if not hasattr(stream, "_smoke_reader"):
        reader = _Reader()
        reader.start()
        stream._smoke_reader = reader

    deadline = time.monotonic() + timeout_s
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("stdio smoke: message timeout")
        try:
            item = stream._smoke_reader.q.get(timeout=min(0.1, remaining))
        except queue.Empty:
            continue
        if item is sentinel:
            raise EOFError("stdio smoke: subprocess closed stream")
        if isinstance(item, Exception):
            raise item
        return json.loads(item)


# ──────── Subprocess driver ────────


class StdioMCPClient:
    """Minimal MCP stdio client — enough for the Path 3 surface."""

    def __init__(self, runner_path: Path) -> None:
        import subprocess

        self._proc = subprocess.Popen(
            [PYTHON, "-u", str(runner_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            text=True,  # line-buffered text mode matches stdio_server's TextIOWrapper
        )
        self._next_id = 1
        self._initialize()

    def _initialize(self) -> None:
        """MCP requires initialize → notifications/initialized before any
        other call. ``initialize`` returns the server's capabilities; the
        ``initialized`` notification has no response."""
        self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "stdio-smoke", "version": "0.0.0"},
            },
        )
        self._notify("notifications/initialized", {})

    def _request(self, method: str, params: dict) -> dict:
        assert self._proc.stdin is not None and self._proc.stdout is not None
        req_id = self._next_id
        self._next_id += 1
        _write_message(
            self._proc.stdin,
            {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params},
        )
        # Notifications (server-side errors, etc.) may arrive before the
        # real response. Skip them until we get a response for req_id.
        deadline = time.monotonic() + 10.0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"stdio smoke: {method} timeout")
            msg = _read_message(self._proc.stdout, timeout_s=remaining)
            if msg.get("id") == req_id:
                return msg
            # Server-side notifications or unrelated messages: skip.

    def _notify(self, method: str, params: dict) -> None:
        assert self._proc.stdin is not None
        _write_message(
            self._proc.stdin,
            {"jsonrpc": "2.0", "method": method, "params": params},
        )

    def list_tools(self) -> list[str]:
        resp = self._request("tools/list", {})
        assert "error" not in resp, f"tools/list error: {resp}"
        tools = resp["result"]["tools"]
        return [t["name"] for t in tools]

    def call_tool(self, name: str, arguments: dict) -> dict:
        resp = self._request("tools/call", {"name": name, "arguments": arguments})
        assert "error" not in resp, f"{name} error: {resp}"
        content = resp["result"]["content"]
        text = next(c["text"] for c in content if c.get("type") == "text")
        return json.loads(text)

    def close(self) -> None:
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2.0)
            except Exception:
                self._proc.kill()


def _make_temp_db(rows: list[tuple]) -> Path:
    """Create an isolated taskdog SQLite file with the production schema."""
    d = SCRATCH / uuid.uuid4().hex
    d.mkdir(parents=True, exist_ok=True)
    db = d / "tasks.db"
    conn = sqlite3.connect(db)
    try:
        conn.executescript(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ueid TEXT UNIQUE,
                name TEXT,
                status TEXT,
                priority INTEGER,
                planned_start TEXT,
                planned_end TEXT,
                deadline TEXT,
                created_at TEXT
            );
            CREATE INDEX idx_tasks_ueid ON tasks(ueid);
            """
        )
        for ueid, name, status, prio, deadline, created in rows:
            conn.execute(
                "INSERT INTO tasks (ueid, name, status, priority, deadline, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ueid, name, status, prio, deadline, created),
            )
        conn.commit()
    finally:
        conn.close()
    return db


def _new_runner() -> Path:
    d = SCRATCH / uuid.uuid4().hex
    d.mkdir(parents=True, exist_ok=True)
    p = d / "run_server.py"
    p.write_text(RUNNER, encoding="utf-8")
    return p


# ──────── Tests ────────


def test_server_launches_and_lists_three_read_only_tools() -> None:
    """Real stdio handshake + tools/list — proves the server is runnable."""
    runner = _new_runner()
    client = StdioMCPClient(runner)
    try:
        tools = client.list_tools()
        assert set(tools) == {
            "taskdog_read",
            "taskdog_list",
            "taskdog_supports_field",
        }, f"unexpected tool set: {tools}"
        # Read-only contract: no apply_change / write surface.
        forbidden = [t for t in tools if "apply_change" in t or "write" in t.lower()]
        assert not forbidden, f"read-only contract violated: {forbidden}"
    finally:
        client.close()
        shutil.rmtree(runner.parent, ignore_errors=True)


def test_taskdog_supports_field_roundtrip() -> None:
    """taskdog_supports_field returns {field, supported: true|false}."""
    runner = _new_runner()
    client = StdioMCPClient(runner)
    try:
        ok = client.call_tool("taskdog_supports_field", {"field_name": "title"})
        assert ok == {"field": "title", "supported": True}
        bad = client.call_tool("taskdog_supports_field", {"field_name": "bogus"})
        assert bad == {"field": "bogus", "supported": False}
    finally:
        client.close()
        shutil.rmtree(runner.parent, ignore_errors=True)


def test_taskdog_list_against_isolated_temp_db() -> None:
    """taskdog_list respects db_path override, status filter, and limit."""
    db = _make_temp_db(
        [
            ("ik:ta:aaa:1", "task-a", "planned", 2, "2026-10-01", "2026-09-01T00:00:00"),
            ("ik:tb:bbb:2", "task-b", "done", 1, "2026-09-15", "2026-08-30T00:00:00"),
            ("ik:tc:ccc:3", "task-c", "planned", 3, "2026-10-15", "2026-09-05T00:00:00"),
        ]
    )
    runner = _new_runner()
    client = StdioMCPClient(runner)
    try:
        # Unfiltered list — all 3 rows, newest first by created_at.
        all_rows = client.call_tool(
            "taskdog_list", {"db_path": str(db), "limit": 10}
        )
        assert all_rows["count"] == 3
        assert [t["ueid"] for t in all_rows["tasks"]] == [
            "ik:tc:ccc:3",
            "ik:ta:aaa:1",
            "ik:tb:bbb:2",
        ]
        # Status filter narrows the set.
        planned = client.call_tool(
            "taskdog_list", {"db_path": str(db), "status": "planned", "limit": 10}
        )
        assert planned["count"] == 2
        assert {t["ueid"] for t in planned["tasks"]} == {"ik:ta:aaa:1", "ik:tc:ccc:3"}
        # Limit cap is honored.
        capped = client.call_tool(
            "taskdog_list", {"db_path": str(db), "limit": 1}
        )
        assert capped["count"] == 1
    finally:
        client.close()
        shutil.rmtree(runner.parent, ignore_errors=True)
        shutil.rmtree(db.parent, ignore_errors=True)


def test_taskdog_read_against_isolated_temp_db() -> None:
    """taskdog_read returns slice or found=False, plus UEID validation."""
    db = _make_temp_db(
        # UEID parts 3+4 must be hex per `_UEID_PATTERN = re.compile(
        # r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")`.
        [("ik:td:ab12:cd34", "read-me", "planned", 2, None, "2026-09-09T00:00:00")]
    )
    runner = _new_runner()
    client = StdioMCPClient(runner)
    try:
        hit = client.call_tool(
            "taskdog_read", {"ueid": "ik:td:ab12:cd34", "db_path": str(db)}
        )
        assert hit["found"] is True
        assert hit["slice"]["name"] == "read-me"
        miss = client.call_tool(
            "taskdog_read", {"ueid": "ik:td:ffff:0000", "db_path": str(db)}
        )
        assert miss["found"] is False
        assert miss["slice"] is None
        # Invalid UEID surfaces as JSON error, not a crash.
        bad = client.call_tool(
            "taskdog_read", {"ueid": "not-a-ueid", "db_path": str(db)}
        )
        assert "error" in bad
    finally:
        client.close()
        shutil.rmtree(runner.parent, ignore_errors=True)
        shutil.rmtree(db.parent, ignore_errors=True)