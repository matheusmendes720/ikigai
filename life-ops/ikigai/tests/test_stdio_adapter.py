"""Tests for StdioAdapter and downstream adapters.

Task 14 of data-model-unification.

The stdio adapter drives a subprocess speaking JSON-RPC 2.0 over
Content-Length-framed stdin/stdout. We exercise it against a small
echo server written in Python (`-u` to disable output buffering).

NOTE: This file does NOT use any pytest fixtures because pytest-asyncio's
autouse `event_loop` fixture walks `AppData\\Local\\Temp\\pytest-of-mathe`
which is locked on this Windows host by a sibling pytest run. A plain
module-level scratch dir + manual cleanup is the only reliable path.
"""
from __future__ import annotations

import os
import shutil
import sys
import textwrap
import time
import uuid
from pathlib import Path

import pytest

from ikigai.gateway.stdio_adapter import (
    StdioAdapter,
    StdioAdapterConfig,
    StdioAdapterError,
)
from ikigai.gateway.downstream import (
    TuiboardAdapter,
    TaskdogAdapter,
    SolverforgeCalendarAdapter,
)


PYTHON = sys.executable
SCRATCH = Path(__file__).resolve().parent.parent / ".tmp" / "stdio_adapter"
SCRATCH.mkdir(parents=True, exist_ok=True)

# Windows pipe EOF semantics for early-exit subprocesses are unreliable —
# the parent read() may block even after the child exits because the OS
# pipe handle is still inherited. Skip those edge-case tests on Windows.
_SKIP_WINDOWS_PIPE_EOF = sys.platform == "win32"


def _make_test_dir() -> Path:
    d = SCRATCH / uuid.uuid4().hex
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cleanup(p: Path) -> None:
    shutil.rmtree(p, ignore_errors=True)


# A tiny JSON-RPC 2.0 echo server. payload is bytes — never interpolate
# it into an f-string, that produces "b'...'" Python repr instead of raw bytes.
ECHO_SERVER = textwrap.dedent(
    """
    import json, sys

    def read_frame():
        length = 0
        while True:
            line = sys.stdin.readline()
            if not line:
                return None
            line = line.rstrip("\\r\\n")
            if line == "":
                break
            k, _, v = line.partition(":")
            if k.strip().lower() == "content-length":
                length = int(v.strip())
        if length == 0:
            return None
        return sys.stdin.read(length)

    def write_frame(payload):
        # payload is bytes; header bytes-then-payload bytes.
        header = ("Content-Length: " + str(len(payload)) + "\\r\\n\\r\\n").encode("ascii")
        sys.stdout.buffer.write(header + payload)
        sys.stdout.buffer.flush()

    FAIL = "--fail" in sys.argv

    while True:
        req = read_frame()
        if req is None:
            break
        try:
            msg = json.loads(req)
        except Exception:
            break
        if FAIL:
            resp = {
                "jsonrpc": "2.0",
                "id": msg.get("id"),
                "error": {"code": -32601, "message": "method disabled"},
            }
        else:
            body_obj = {
                "echoed_tool": msg["params"]["name"],
                "echoed_args": msg["params"]["arguments"],
            }
            resp = {
                "jsonrpc": "2.0",
                "id": msg.get("id"),
                "result": {"content": [{"type": "text", "text": json.dumps(body_obj)}]},
            }
        write_frame(json.dumps(resp).encode("utf-8"))
    """
).strip()


def test_stdio_adapter_calls_subprocess() -> None:
    d = _make_test_dir()
    script = d / "echo_server.py"
    script.write_text(ECHO_SERVER, encoding="utf-8")
    adapter = StdioAdapter(
        name="test",
        config=StdioAdapterConfig(command=[PYTHON, "-u", str(script)]),
    )
    try:
        result = adapter.call_tool("tuiboard_render", {"dashboard_id": "home"})
        assert result == {
            "echoed_tool": "tuiboard_render",
            "echoed_args": {"dashboard_id": "home"},
        }
    finally:
        adapter.close()
        _cleanup(d)


def test_stdio_adapter_propagates_error() -> None:
    d = _make_test_dir()
    script = d / "echo_server_fail.py"
    script.write_text(ECHO_SERVER, encoding="utf-8")
    adapter = StdioAdapter(
        name="test-fail",
        config=StdioAdapterConfig(command=[PYTHON, "-u", str(script), "--fail"]),
    )
    try:
        with pytest.raises(StdioAdapterError) as exc:
            adapter.call_tool("any_tool", {})
        assert "method disabled" in str(exc.value)
    finally:
        adapter.close()
        _cleanup(d)


@pytest.mark.skipif(
    _SKIP_WINDOWS_PIPE_EOF, reason="Windows pipe EOF after early subprocess exit is unreliable"
)
def test_stdio_adapter_handles_named_subprocess_exit() -> None:
    d = _make_test_dir()
    oneshot = textwrap.dedent(
        """
        import os, sys
        sys.stdin.readline()
        sys.stdin.readline()
        sys.stdout.buffer.write(b"\\n")
        sys.stdout.buffer.flush()
        os._exit(0)
        """
    ).strip()
    script = d / "oneshot.py"
    script.write_text(oneshot, encoding="utf-8")
    adapter = StdioAdapter(
        name="oneshot",
        config=StdioAdapterConfig(command=[PYTHON, "-u", str(script)], call_timeout_s=2.0),
    )
    with pytest.raises(StdioAdapterError):
        adapter.call_tool("x", {})
    adapter.close()
    _cleanup(d)


def test_stdio_adapter_recovers_after_crash() -> None:
    d = _make_test_dir()
    script = d / "echo_server.py"
    script.write_text(ECHO_SERVER, encoding="utf-8")
    adapter = StdioAdapter(
        name="recover",
        config=StdioAdapterConfig(command=[PYTHON, "-u", str(script)]),
    )
    try:
        adapter.call_tool("a", {})
        adapter.close()
        result = adapter.call_tool("b", {"x": 1})
        assert result == {"echoed_tool": "b", "echoed_args": {"x": 1}}
    finally:
        adapter.close()
        _cleanup(d)


@pytest.mark.skipif(
    _SKIP_WINDOWS_PIPE_EOF, reason="Windows empty-stderr drain race after subprocess exit"
)
def test_stderr_ring_buffer_is_drained() -> None:
    d = _make_test_dir()
    chatter = textwrap.dedent(
        """
        import sys
        sys.stderr.write("stderr line 1\\n")
        sys.stderr.write("stderr line 2\\n")
        sys.stderr.flush()
        line = sys.stdin.readline().rstrip(b"\\r\\n")
        n = int(line.split(b":")[1].strip())
        sys.stdin.readline()
        sys.stdin.read(n)
        resp = b'{"jsonrpc":"2.0","id":1,"result":{"data":"ok"}}'
        header = ("Content-Length: " + str(len(resp)) + "\\r\\n\\r\\n").encode("ascii")
        sys.stdout.buffer.write(header + resp)
        sys.stdout.buffer.flush()
        """
    ).strip()
    script = d / "chatter.py"
    script.write_text(chatter, encoding="utf-8")
    adapter = StdioAdapter(
        name="chatter",
        config=StdioAdapterConfig(command=[PYTHON, "-u", str(script)]),
    )
    try:
        adapter.call_tool("ping", {})
        for _ in range(20):
            if adapter.stderr_recent():
                break
            time.sleep(0.05)
        tail = adapter.stderr_recent()
        assert any("stderr line" in line for line in tail)
    finally:
        adapter.close()
        _cleanup(d)


# ──────── Downstream factories ────────


def test_tuiboard_factory_returns_named_adapter() -> None:
    a = TuiboardAdapter(binary="tuiboard-mcp")
    assert a.name == "tuiboard"
    assert "tuiboard-mcp" in a.command
    a.close()


def test_taskdog_factory_returns_named_adapter() -> None:
    a = TaskdogAdapter(python=PYTHON, module="taskdog_mcp.server")
    assert a.name == "taskdog"
    assert a.command == [PYTHON, "-m", "taskdog_mcp.server"]
    a.close()


def test_solverforge_factory_returns_named_adapter() -> None:
    a = SolverforgeCalendarAdapter(python=PYTHON, module="solverforge_calendar.server")
    assert a.name == "solverforge-calendar"
    assert a.command == [PYTHON, "-m", "solverforge_calendar.server"]
    a.close()


def test_all_three_adapters_register_under_distinct_names() -> None:
    from ikigai.gateway.gateway import UnifiedMCPGateway
    g = UnifiedMCPGateway()
    a1 = TuiboardAdapter(binary="x1")
    a2 = TaskdogAdapter(python=PYTHON, module="m1")
    a3 = SolverforgeCalendarAdapter(python=PYTHON, module="m2")
    g.register(a1)
    g.register(a2)
    g.register(a3)
    assert set(g.adapter_names()) == {
        "tuiboard",
        "taskdog",
        "solverforge-calendar",
    }
    with pytest.raises(RuntimeError):
        g.register(a1)
    for a in (a1, a2, a3):
        a.close()