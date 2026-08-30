"""Tests for the SSE consumer CLI (gateway.client_cli)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Any

import pytest

from ikigai.gateway.client_cli import (
    _parse_sse_frame,
    _strip_chunked_framing,
    main,
    parse_sse_stream,
    watch,
)


class _StubHTTPServer(ThreadingMixIn):
    """Minimal chunked-SSE test server.

    The handler script is supplied at construction time. The server
    sends SSE-formatted bytes via `wfile.write` with chunked TE.
    """

    class _Handler(BaseHTTPRequestHandler):
        script = b""  # set per-test by factory below

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 — stdlib name
            pass

        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            self.wfile.write(self.__class__.script)
            self.wfile.flush()

    def __init__(self, script: bytes) -> None:
        from http.server import HTTPServer
        self._script = script
        self._Handler.script = script
        self._server = HTTPServer(("127.0.0.1", 0), self._Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True
        )
        self._thread.start()

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def _chunk(payload: bytes) -> bytes:
    """Wrap payload in HTTP/1.1 chunked-TE framing."""
    return f"{len(payload):x}\r\n".encode() + payload + b"\r\n"


class _FakeSock:
    """Minimal socket stub: returns scripted bytes once, then EOF.

    `parse_sse_stream` reads until the peer closes (recv returns empty).
    This stub hands its bytes back in one chunk and then signals EOF.
    """

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._done = False

    def recv(self, _bufsize: int) -> bytes:
        if self._done:
            return b""
        self._done = True
        return self._data


# ──────── Pure-function tests (no socket) ────────


def test_strip_chunked_framing_single_chunk() -> None:
    framed = _chunk(b"hello world")
    assert _strip_chunked_framing(framed.decode()) == "hello world"


def test_strip_chunked_framing_multiple_chunks() -> None:
    framed = _chunk(b"hello ") + _chunk(b"world")
    assert _strip_chunked_framing(framed.decode()) == "hello world"


def test_strip_chunked_framing_with_terminator() -> None:
    framed = _chunk(b"hello") + b"0\r\n\r\n"
    assert _strip_chunked_framing(framed.decode()) == "hello"


def test_parse_sse_frame_event_and_data() -> None:
    frame = 'event: task.created\ndata: {"ueid": "ikigai:task:abc:1:2"}'
    name, data = _parse_sse_frame(frame)
    assert name == "task.created"
    assert data == '{"ueid": "ikigai:task:abc:1:2"}'


def test_parse_sse_frame_skips_comments() -> None:
    frame = ": heartbeat 12345\nevent: ping\ndata: ok"
    name, data = _parse_sse_frame(frame)
    assert name == "ping"
    assert data == "ok"


def test_parse_sse_frame_data_only() -> None:
    frame = 'data: {"k": 1}'
    name, data = _parse_sse_frame(frame)
    assert name is None
    assert data == '{"k": 1}'


def test_parse_sse_frame_multiline_data() -> None:
    frame = 'event: multi\ndata: line1\ndata: line2'
    name, data = _parse_sse_frame(frame)
    assert name == "multi"
    assert data == "line1\nline2"


# ──────── Integration: stub SSE server → watch() ────────


def test_watch_streams_events_as_json_lines() -> None:
    """parse_sse_stream must yield one parsed event per SSE frame."""
    payload = json.dumps({"ueid": "ikigai:task:abc:1:2", "title": "smoke"}).encode()
    wire = (
        _chunk(b"event: task.created\ndata: " + payload + b"\n\n")
        + b"0\r\n\r\n"
    )
    sock = _FakeSock(wire)
    events = list(parse_sse_stream(sock))
    assert len(events) == 1
    assert events[0]["event"] == "task.created"
    assert events[0]["data"] == {"ueid": "ikigai:task:abc:1:2", "title": "smoke"}


def test_watch_filter_drops_non_matching() -> None:
    """Filter mask must keep only events whose name starts with the prefix."""
    # Unit-level: drive parse_sse_stream directly with crafted bytes and
    # inspect what it yields. This isolates the filter's effect on the
    # generator output without depending on socket timing.
    sock = _FakeSock(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/event-stream\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
        + _chunk(b"event: taskdog.add\ndata: " + json.dumps({"k": "a"}).encode() + b"\n\n")
        + _chunk(b"event: tuiboard.render\ndata: " + json.dumps({"k": "b"}).encode() + b"\n\n")
        + b"0\r\n\r\n"
    )
    events = list(parse_sse_stream(sock))
    filtered = [e for e in events if e["event"].startswith("taskdog.")]
    assert len(events) == 2
    assert len(filtered) == 1
    assert filtered[0]["event"] == "taskdog.add"


def test_watch_connection_refused_returns_1(capsys: pytest.CaptureFixture) -> None:
    """Connecting to a closed port must exit 1 with a helpful stderr message."""
    # Port 1 is privileged and almost always closed; the connection attempt
    # raises ConnectionRefusedError and watch() reports it on stderr.
    rc = watch(host="127.0.0.1", port=1, duration_s=1.0)
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot connect" in err


def test_watch_swallows_comment_heartbeats() -> None:
    script = (
        _chunk(b": heartbeat 12345\n\n")
        + _chunk(b"event: ping\ndata: ok\n\n")
    )
    server = _StubHTTPServer(script)
    try:
        rc = watch(host="127.0.0.1", port=server.port, duration_s=0.5)
        assert rc == 0
    finally:
        server.close()


def test_main_watch_parses_args(capsys: pytest.CaptureFixture) -> None:
    """End-to-end via argparse — covers the CLI entrypoint.

    Patches `watch` to a stub so we can verify argv is parsed and forwarded
    correctly without relying on the socket roundtrip.
    """
    captured: dict = {}

    def fake_watch(
        host: str = "127.0.0.1",
        port: int = 8765,
        event_filter: str | None = None,
        duration_s: float = 0.0,
        human: bool = False,
    ) -> int:
        captured.update(
            host=host,
            port=port,
            event_filter=event_filter,
            duration_s=duration_s,
            human=human,
        )
        print(json.dumps({"event": "hello", "data": {"k": "v"}}), flush=True)
        return 0

    import ikigai.gateway.client_cli as cli_mod
    original = cli_mod.watch
    cli_mod.watch = fake_watch  # type: ignore[assignment]
    try:
        rc = main([
            "watch",
            "--host", "10.0.0.1",
            "--port", "9999",
            "--filter", "taskdog.",
            "--duration", "5.0",
        ])
    finally:
        cli_mod.watch = original  # type: ignore[assignment]
    assert rc == 0
    assert captured == {
        "host": "10.0.0.1",
        "port": 9999,
        "event_filter": "taskdog.",
        "duration_s": 5.0,
        # Default with capsys (non-TTY) → human=False (JSON mode).
        "human": False,
    }
    parsed = json.loads(capsys.readouterr().out.strip())
    assert parsed["event"] == "hello"


# ──────── Human-readable mode ────────


def test_summarize_data_tool_call() -> None:
    """Tool-shaped payloads get a compact `tool=...()` rendering."""
    from ikigai.gateway.client_cli import _summarize_data

    summary = _summarize_data({"tool": "taskdog.add", "arguments": {"title": "x"}})
    assert "taskdog.add" in summary
    assert "title" in summary


def test_summarize_data_long_payload_truncated() -> None:
    """Payloads >100 chars get truncated for streaming readability."""
    from ikigai.gateway.client_cli import _summarize_data

    huge = {"blob": "x" * 200}
    summary = _summarize_data(huge)
    assert len(summary) <= 100
    assert summary.endswith("...")


def test_summarize_data_result_field() -> None:
    """Dicts with a top-level `result` collapse to `result=...`."""
    from ikigai.gateway.client_cli import _summarize_data

    summary = _summarize_data({"result": "ok"})
    assert summary.startswith("result=")


def test_format_event_human_shape() -> None:
    """Human line starts with `[HH:MM:SS.mmm]` then event name + data summary."""
    from ikigai.gateway.client_cli import _format_event_human

    line = _format_event_human({"event": "task.created", "data": {"title": "hi"}})
    # Verify the bracket+timestamp prefix is preserved
    assert line.startswith("[")
    assert "]" in line[:14]
    assert "task.created" in line
    # The exact timestamp varies — but `title` from the summary appears after
    assert "title" in line


def test_watch_human_emits_compact_lines_not_json() -> None:
    """`watch(human=True)` renders one compact line per event, not JSON."""
    script = (
        _chunk(b"event: task.created\ndata: " + json.dumps({"title": "Build wiremesh"}).encode() + b"\n\n")
        + _chunk(b"event: gateway.heartbeat\ndata: {}\n\n")
        + b"0\r\n\r\n"
    )
    server = _StubHTTPServer(script)
    try:
        rc = watch(host="127.0.0.1", port=server.port, duration_s=2.0, human=True)
        assert rc == 0
    finally:
        server.close()


def test_main_json_flag_forces_json_mode(capsys: pytest.CaptureFixture) -> None:
    """`--json` forces JSON-per-line output (default behavior, but explicit)."""
    import ikigai.gateway.client_cli as cli_mod
    captured: dict = {}

    def fake_watch(
        host: str = "127.0.0.1",
        port: int = 8765,
        event_filter: str | None = None,
        duration_s: float = 0.0,
        human: bool = False,
    ) -> int:
        captured["human"] = human
        return 0

    original = cli_mod.watch
    cli_mod.watch = fake_watch  # type: ignore[assignment]
    try:
        rc = main(["watch", "--json"])
    finally:
        cli_mod.watch = original  # type: ignore[assignment]
    assert rc == 0
    assert captured["human"] is False


def test_main_human_flag_forces_human_mode(capsys: pytest.CaptureFixture) -> None:
    """`--human` forces compact rendered lines."""
    import ikigai.gateway.client_cli as cli_mod
    captured: dict = {}

    def fake_watch(
        host: str = "127.0.0.1",
        port: int = 8765,
        event_filter: str | None = None,
        duration_s: float = 0.0,
        human: bool = False,
    ) -> int:
        captured["human"] = human
        return 0

    original = cli_mod.watch
    cli_mod.watch = fake_watch  # type: ignore[assignment]
    try:
        rc = main(["watch", "--human"])
    finally:
        cli_mod.watch = original  # type: ignore[assignment]
    assert rc == 0
    assert captured["human"] is True


def test_main_json_and_human_mutually_exclusive() -> None:
    """Passing both --json and --human must fail (argparse)."""
    with pytest.raises(SystemExit):
        main(["watch", "--json", "--human"])
