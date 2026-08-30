"""SSE consumer CLI for the UnifiedMCPGateway.

Streams events from the gateway's /events endpoint as JSON lines on
stdout. Each line is `{"event": <name>, "data": <payload>}` — useful
for piping into `jq`, log aggregators, or shell scripts.

Usage:
    python -m ikigai.gateway.client_cli watch
    python -m ikigai.gateway.client_cli watch --port 8765 --duration 30
    python -m ikigai.gateway.client_cli watch --filter taskdog

Why raw sockets (not urllib / http.client):
- `urllib.request.urlopen` buffers the body and only returns once the
  response ends; SSE never ends without a client close.
- `http.client.HTTPResponse` reads chunks greedily and can block on
  the next chunk-size line.
- a raw socket + explicit `\r\n\r\n` header boundary + manual chunk
  parser gives us full control and matches the gateway's wire format.
"""

from __future__ import annotations

import argparse
import json
import logging
import socket
import sys
import time
from collections.abc import Iterator

logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_DURATION_S = 0.0  # 0 = run until interrupted


def parse_sse_stream(sock: socket.socket) -> Iterator[dict]:
    """Yield parsed SSE events from `sock` until the peer closes.

    SSE wire format (per gateway `_sse_stream`):
        chunk-size-hex CRLF
        chunk-bytes CRLF
        ...
        0 CRLF CRLF            (terminator, only when not using chunked TE)

    For our gateway, the chunked body contains SSE frames:
        event: <name>\\n
        data: <json>\\n
        \\n                     (event terminator)

    Each chunk is one or more SSE frames. We buffer partial frames
    across chunks until we see a blank line.
    """
    pending_data = ""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            return
        # Strip chunked-transfer-encoding framing: `<hex>\\r\\n<body>\\r\\n`
        # The gateway uses chunked TE, so each recv may contain one or
        # more chunks. We strip the size-line and trailing CRLF for each.
        buf = chunk.decode("utf-8", errors="replace")
        buf = _strip_chunked_framing(buf)
        pending_data += buf
        # Split on blank line (SSE event terminator); keep tail if partial
        while "\n\n" in pending_data:
            frame, _, pending_data = pending_data.partition("\n\n")
            event_name, data_payload = _parse_sse_frame(frame)
            if event_name is None:
                continue
            try:
                payload_obj = json.loads(data_payload) if data_payload else {}
            except json.JSONDecodeError:
                payload_obj = {"_raw": data_payload}
            yield {"event": event_name, "data": payload_obj}


def _strip_chunked_framing(buf: str) -> str:
    """Strip HTTP/1.1 chunked transfer-encoding size lines.

    Each chunk in the body is `<size-hex>\\r\\n<data>\\r\\n`. We loop
    until no more size lines are present. If the buffer ends mid-chunk,
    the partial data is returned so the next recv can complete it.
    """
    out: list[str] = []
    pos = 0
    while pos < len(buf):
        # Find end of size line
        nl = buf.find("\r\n", pos)
        if nl == -1:
            # No more complete size lines; append the rest as-is
            out.append(buf[pos:])
            break
        size_str = buf[pos:nl].strip()
        try:
            size = int(size_str, 16)
        except ValueError:
            # Not a chunk-size line (could be the trailing 0 chunk + CRLF)
            # If we see "0\\r\\n\\r\\n" that's the end-of-body marker.
            if size_str == "0":
                # Skip the 0 line + its trailing CRLF + the CRLF that follows
                # (HTTP/1.1 chunked terminator is "0\\r\\n\\r\\n")
                end = nl + 2
                if buf[end:end + 2] == "\r\n":
                    pos = end + 2
                else:
                    pos = end
                continue
            # Garbage — bail out, return what we have
            out.append(buf[pos:])
            break
        if size == 0:
            # End of chunked body
            pos = nl + 2
            # Skip optional trailers + final CRLF CRLF
            if buf[pos:pos + 2] == "\r\n":
                pos += 2
            break
        # Read `size` bytes after the size line
        start = nl + 2
        end = start + size
        if end > len(buf):
            # Partial chunk; emit what we have, expect more on next recv
            out.append(buf[start:])
            break
        out.append(buf[start:end])
        # Skip past data + trailing CRLF
        pos = end + 2
    return "".join(out)


def _parse_sse_frame(frame: str) -> tuple[str | None, str]:
    """Parse one SSE event frame. Returns (event_name, data_payload).

    Lines starting with `:` are SSE comments (used for heartbeats) and
    are skipped. `event:` sets the event name; `data:` accumulates.
    """
    event_name: str | None = None
    data_lines: list[str] = []
    for raw_line in frame.splitlines():
        line = raw_line.rstrip("\r")
        if not line or line.startswith(":"):
            continue
        if ":" in line:
            field, _, value = line.partition(":")
            # SSE spec: leading single space after colon is stripped
            if value.startswith(" "):
                value = value[1:]
            if field == "event":
                event_name = value
            elif field == "data":
                data_lines.append(value)
    return event_name, "\n".join(data_lines)


def _connect(host: str, port: int, timeout: float = 5.0) -> socket.socket:
    sock = socket.create_connection((host, port), timeout=timeout)
    sock.sendall(b"GET /events HTTP/1.1\r\nHost: localhost\r\nAccept: text/event-stream\r\nConnection: close\r\n\r\n")
    return sock


def _validate_sse_headers(sock: socket.socket, deadline: float) -> bytes:
    """Read until \\r\\n\\r\\n. Raise on non-200 or wrong content type."""
    buf = b""
    while b"\r\n\r\n" not in buf:
        if time.monotonic() > deadline:
            raise TimeoutError("header read timed out")
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("peer closed before headers")
        buf += chunk
    header_blob, _, _ = buf.partition(b"\r\n\r\n")
    headers = header_blob.decode("iso-8859-1")
    status_line = headers.splitlines()[0] if headers else ""
    if " 200 " not in status_line:
        raise ConnectionError(f"unexpected response: {status_line!r}")
    if "Content-Type: text/event-stream" not in headers:
        raise ConnectionError(f"not an SSE endpoint: {headers!r}")
    return buf


def watch(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    event_filter: str | None = None,
    duration_s: float = DEFAULT_DURATION_S,
) -> int:
    """Stream SSE events to stdout as JSON lines.

    Args:
        host: gateway host (default 127.0.0.1)
        port: gateway port (default 8765)
        event_filter: if set, only emit events whose name starts with this prefix
        duration_s: auto-exit after N seconds (0 = run until interrupted)

    Returns:
        process exit code (0 = clean exit)
    """
    start = time.monotonic()
    deadline = start + duration_s if duration_s > 0 else None
    try:
        sock = _connect(host, port)
    except (ConnectionRefusedError, OSError) as e:
        print(f"error: cannot connect to {host}:{port}: {e}", file=sys.stderr)
        return 1
    try:
        _validate_sse_headers(sock, time.monotonic() + 5.0)
        for event in parse_sse_stream(sock):
            if deadline is not None and time.monotonic() >= deadline:
                break
            name = event["event"]
            if event_filter and not name.startswith(event_filter):
                continue
            print(json.dumps(event, default=str), flush=True)
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        try:
            sock.close()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ikigai-gateway-client",
        description="Stream SSE events from the UnifiedMCPGateway /events endpoint.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    watch_p = sub.add_parser("watch", help="stream events to stdout as JSON lines")
    watch_p.add_argument("--host", default=DEFAULT_HOST, help="gateway host")
    watch_p.add_argument("--port", type=int, default=DEFAULT_PORT, help="gateway port")
    watch_p.add_argument(
        "--filter",
        dest="event_filter",
        default=None,
        help="only emit events whose name starts with this prefix (e.g. 'taskdog.')",
    )
    watch_p.add_argument(
        "--duration",
        dest="duration_s",
        type=float,
        default=DEFAULT_DURATION_S,
        help="auto-exit after N seconds (0 = run until interrupted)",
    )
    args = parser.parse_args(argv)
    if args.command == "watch":
        return watch(
            host=args.host,
            port=args.port,
            event_filter=args.event_filter,
            duration_s=args.duration_s,
        )
    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
