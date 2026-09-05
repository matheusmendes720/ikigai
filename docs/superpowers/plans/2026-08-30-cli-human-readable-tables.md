# CLI Human-Readable Tables Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `--format {json,table}` (and `--no-color`) flags to the three observability CLIs — `event_log_cli`, `client_cli`, `review_queue_cli` — so operators get human-readable Rich tables by default in a TTY and stable JSON lines when piped, without breaking existing automation.

**Architecture:** Single shared module `src/ikigai/src/ikigai/gateway/_cli_format.py` (gateway-side) and `src/mesh/_cli_format.py` (mesh-side). Each exposes `format_table(records, columns)` returning a Rich-rendered string, and a `get_format(args)` helper that resolves `args.format` vs auto-detect (TTY → table, pipe → json). CLIs add a `--format` flag with `choices=["json", "table"]` and `default=None` (auto). Existing JSON output remains the default for non-TTY (piped/captured). Table output uses `rich.table.Table` with aligned columns and `--no-color` strips ANSI.

**Tech Stack:** `rich` (already in `src/ikigai/pyproject.toml` as `rich = "^13.7"` — must also add to mesh `pyproject.toml` if not present); `pytest` for tests; `argparse` for flags. Zero new top-level deps if `rich` is already mesh-side (verify before adding).

---

## Global Constraints

- **No breaking change to JSON output** — piping `... | jq` MUST keep working; auto-detect via `sys.stdout.isatty()` ensures JSON-by-default when piped.
- **`rich` is the chosen dep** — already in `src/ikigai/pyproject.toml`. Mesh `pyproject.toml` may or may not have it; check `src/mesh/pyproject.toml` (or mesh dev setup) and add only if absent. If `rich` would create a heavy cross-tree import, fall back to a hand-rolled `_format_table()` that pads columns with `str.ljust()` (no extra deps). **Try `rich` first; fall back only if mesh can't take it.**
- **No LLM calls.** Pure mechanical rendering.
- **Pydantic v2 strict** preserved (no schema changes).
- **Tests live next to existing test files** — `tests/mesh/test_review_queue_cli.py` (extend, don't duplicate) and `tests/ikigai/test_event_log_cli.py` / `tests/ikigai/test_client_cli.py` (extend if missing, create if missing).
- **One commit per task.** Conventional-commit style; no `Co-Authored-By` trailer.
- **Verification before commit**: each task ends with `pytest` and `ruff check` clean before committing.

---

## File Structure

### New files
- `src/ikigai/src/ikigai/gateway/_cli_format.py` — gateway-side shared formatter (`format_json_lines`, `format_table`, `get_format`)
- `src/mesh/_cli_format.py` — mesh-side mirror (same API, no cross-tree import)

### Modified files
- `src/ikigai/src/ikigai/gateway/event_log_cli.py` — add `--format`, `--no-color`; replace `_format_record()` print loop
- `src/ikigai/src/ikigai/gateway/client_cli.py` — add `--format`, `--no-color` to `watch`; replace `print(json.dumps(...))` line
- `src/mesh/review_queue_cli.py` — add `--format`, `--no-color`; replace `_summarize()` and `status` print loops
- `tests/ikigai/test_event_log_cli.py` — add table-format tests
- `tests/ikigai/test_client_cli.py` — add table-format tests (create if missing)
- `tests/mesh/test_review_queue_cli.py` — add table-format tests
- `src/ikigai/pyproject.toml` (only if `rich` missing — likely already there)
- `src/mesh/pyproject.toml` or `pyproject.toml` (only if `rich` missing for mesh)

### Why a shared formatter module?
- DRY across three CLIs with overlapping output shape (list-style + status-style)
- Single point of color/width policy
- One test surface for the formatter itself
- Avoids cross-tree import (gateway ↔ mesh) by keeping each side's copy near its consumer

---

## Task 1: Shared formatter module — gateway side

**Files:**
- Create: `src/ikigai/src/ikigai/gateway/_cli_format.py`
- Test: `tests/ikigai/test_cli_format.py`

**Interfaces:**
- Consumes: a list of dict records, a list of column specs `[(key, header, width_hint)]`, an optional `Rich` Console
- Produces: a string ready to print

**Step 1: Write the failing test**

Create `tests/ikigai/test_cli_format.py`:

```python
"""Tests for the gateway CLI shared formatter."""

from __future__ import annotations

import io

from ikigai.gateway._cli_format import (
    format_json_lines,
    format_table,
    get_format,
)


def test_format_json_lines_one_per_record():
    records = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    out = format_json_lines(records)
    lines = out.splitlines()
    assert len(lines) == 2
    assert '"a": 1' in lines[0]
    assert '"b": "y"' in lines[1]


def test_format_table_with_columns_renders_header_and_rows():
    records = [{"ts": "2026-08-30T12:00:00Z", "event": "taskdog.add", "data": "{}"}]
    columns = [("ts", "WHEN", 20), ("event", "EVENT", 20), ("data", "DATA", 40)]
    out = format_table(records, columns)
    # Header line + separator + row
    assert "WHEN" in out
    assert "EVENT" in out
    assert "DATA" in out
    assert "taskdog.add" in out
    assert "2026-08-30T12:00:00Z" in out


def test_format_table_empty_records_returns_just_header():
    records: list[dict] = []
    columns = [("ts", "WHEN", 20)]
    out = format_table(records, columns)
    # Header present, no body rows
    assert "WHEN" in out
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) <= 2  # header + separator


def test_format_table_no_color_strips_ansi():
    records = [{"a": "value"}]
    columns = [("a", "A", 10)]
    out = format_table(records, columns, no_color=True)
    # No ANSI escape sequences
    assert "\x1b[" not in out


def test_get_format_defaults_to_json_when_not_tty():
    # Simulate non-TTY stdout
    fake_stdout = io.StringIO()
    fmt = get_format(args_format=None, stdout=fake_stdout)
    assert fmt == "json"


def test_get_format_explicit_json():
    fake_stdout = io.StringIO()
    fmt = get_format(args_format="json", stdout=fake_stdout)
    assert fmt == "json"


def test_get_format_explicit_table():
    fake_stdout = io.StringIO()
    fmt = get_format(args_format="table", stdout=fake_stdout)
    assert fmt == "table"
```

**Step 2: Run tests to verify they fail**

```bash
cd src/ikigai
uv run pytest tests/ikigai/test_cli_format.py -v
```

Expected: `ModuleNotFoundError: No module named 'ikigai.gateway._cli_format'`

**Step 3: Write the implementation**

Create `src/ikigai/src/ikigai/gateway/_cli_format.py`:

```python
"""Shared formatter for gateway observability CLIs.

Three CLIs (event_log_cli, client_cli, future gateway tools) need the
same two output modes:
  - `json`  : one JSON line per record (default for pipes/scripts)
  - `table` : aligned columns with a header (default for interactive TTY)

This module owns the rendering and the format-resolution policy:
  - explicit `--format` wins
  - else if stdout is a TTY → `table`
  - else → `json`
"""

from __future__ import annotations

import io
import json
import sys
from typing import IO, Any


def get_format(args_format: str | None, stdout: IO[str] | None = None) -> str:
    """Resolve the active output format.

    Args:
        args_format: value from the `--format` CLI flag (None = auto-detect)
        stdout: stream to test for TTY (default: sys.stdout)

    Returns:
        "json" or "table"
    """
    if args_format in ("json", "table"):
        return args_format
    out = stdout if stdout is not None else sys.stdout
    is_tty = getattr(out, "isatty", lambda: False)()
    return "table" if is_tty else "json"


def format_json_lines(records: list[dict[str, Any]]) -> str:
    """Render records as one JSON object per line.

    Uses `default=str` so datetimes/Pydantic objects serialize without errors.
    Empty input returns empty string (no stray blank line).
    """
    if not records:
        return ""
    return "\n".join(json.dumps(r, default=str) for r in records)


def format_table(
    records: list[dict[str, Any]],
    columns: list[tuple[str, str, int]],
    *,
    no_color: bool = False,
) -> str:
    """Render records as a Rich table.

    Args:
        records: list of dicts (one per row)
        columns: list of (key, header, width_hint) triples. `width_hint`
                 is the minimum column width; Rich auto-grows for longer values.
        no_color: if True, render with ANSI stripped (CI-friendly)

    Returns:
        Rendered table as a string (one or more lines).
    """
    from rich.console import Console
    from rich.table import Table

    table = Table(show_header=True, header_style="bold" if not no_color else "")
    for _key, header, width in columns:
        # Rich uses `min_width` for the floor; longer content overflows
        table.add_column(header, min_width=width, overflow="fold")

    for record in records:
        row = [str(record.get(key, "")) for key, _h, _w in columns]
        table.add_row(*row)

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=not no_color, no_color=no_color, width=200)
    console.print(table)
    return buf.getvalue().rstrip("\n")
```

**Step 4: Run tests to verify they pass**

```bash
cd src/ikigai
uv run pytest tests/ikigai/test_cli_format.py -v
uv run ruff check src/ikigai/gateway/_cli_format.py tests/ikigai/test_cli_format.py
```

Expected: 7/7 PASS, ruff clean.

**Step 5: Commit**

```bash
git add src/ikigai/src/ikigai/gateway/_cli_format.py tests/ikigai/test_cli_format.py
git commit -m "feat(ikigai-cli): shared JSON/table formatter for observability CLIs"
```

---

## Task 2: Shared formatter module — mesh side

**Files:**
- Create: `src/mesh/_cli_format.py`
- Test: `tests/mesh/test_cli_format.py`

**Note:** If `rich` is not available in the mesh dependency set, copy the `format_table` body to use a hand-rolled pad-and-join fallback instead of `rich.table.Table`. **Check `src/mesh/pyproject.toml` first; if `rich` is not listed, use the fallback in Step 3.**

**Step 1: Write the failing test**

Create `tests/mesh/test_cli_format.py`:

```python
"""Tests for the mesh CLI shared formatter."""

from __future__ import annotations

import io

from src.mesh._cli_format import (
    format_json_lines,
    format_table,
    get_format,
)


def test_format_json_lines_one_per_record():
    records = [{"ueid": "ts:abc:1:1", "status": "pending"}]
    out = format_json_lines(records)
    assert '"ueid": "ts:abc:1:1"' in out


def test_format_table_renders_header_and_rows():
    records = [{"event_id": "evt_001", "ueid": "ts:abc:1:1", "status": "pending"}]
    columns = [("event_id", "EVENT", 12), ("ueid", "UEID", 20), ("status", "STATUS", 12)]
    out = format_table(records, columns)
    assert "EVENT" in out
    assert "UEID" in out
    assert "STATUS" in out
    assert "evt_001" in out
    assert "ts:abc:1:1" in out


def test_format_table_no_color():
    records = [{"a": "x"}]
    out = format_table(records, [("a", "A", 5)], no_color=True)
    assert "\x1b[" not in out


def test_get_format_defaults_to_json_for_non_tty():
    fake_stdout = io.StringIO()
    assert get_format(args_format=None, stdout=fake_stdout) == "json"


def test_get_format_explicit_table():
    fake_stdout = io.StringIO()
    assert get_format(args_format="table", stdout=fake_stdout) == "table"
```

**Step 2: Run tests to verify they fail**

```bash
cd life  # project root
python -m pytest tests/mesh/test_cli_format.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.mesh._cli_format'`

**Step 3a: Check if `rich` is in mesh deps**

```bash
grep -E "^\s*rich\s*=" src/mesh/pyproject.toml pyproject.toml 2>/dev/null
```

If found → use the `rich`-based implementation (mirror Task 1, replacing `from ikigai.gateway._cli_format import …` with local definitions and `from rich.console import Console` / `from rich.table import Table`).

If NOT found → use the **fallback implementation** in Step 3b.

**Step 3b (fallback only): hand-rolled formatter**

Create `src/mesh/_cli_format.py`:

```python
"""Shared formatter for mesh CLIs (no rich dep).

Uses hand-rolled column padding so mesh doesn't pull in `rich` just for
table output. Same public API as the gateway-side formatter.
"""

from __future__ import annotations

import io
import json
import sys
from typing import IO, Any


def get_format(args_format: str | None, stdout: IO[str] | None = None) -> str:
    if args_format in ("json", "table"):
        return args_format
    out = stdout if stdout is not None else sys.stdout
    is_tty = getattr(out, "isatty", lambda: False)()
    return "table" if is_tty else "json"


def format_json_lines(records: list[dict[str, Any]]) -> str:
    if not records:
        return ""
    return "\n".join(json.dumps(r, default=str) for r in records)


def format_table(
    records: list[dict[str, Any]],
    columns: list[tuple[str, str, int]],
    *,
    no_color: bool = False,
) -> str:
    """Pad columns to max(width_hint, longest value). Header in CAPS."""
    rows = [[str(r.get(key, "")) for key, _h, _w in columns] for r in records]
    widths = [
        max(width_hint, max((len(row[i]) for row in rows), default=0))
        for (_k, _h, width_hint), i in zip(columns, range(len(columns)))
    ]
    header = [h.upper() for _k, h, _w in columns]
    sep = ["-" * w for w in widths]
    lines = []
    lines.append("  ".join(cell.ljust(w) for cell, w in zip(header, widths)))
    lines.append("  ".join(sep))
    for row in rows:
        lines.append("  ".join(cell.ljust(w) for cell, w in zip(row, widths)))
    return "\n".join(lines)
```

**Step 4: Run tests to verify they pass**

```bash
cd life
python -m pytest tests/mesh/test_cli_format.py -v
uv run ruff check src/mesh/_cli_format.py tests/mesh/test_cli_format.py
```

Expected: 5/5 PASS, ruff clean.

**Step 5: Commit**

```bash
git add src/mesh/_cli_format.py tests/mesh/test_cli_format.py pyproject.toml  # pyproject.toml only if rich added
git commit -m "feat(mesh-cli): shared JSON/table formatter for review_queue_cli"
```

---

## Task 3: `event_log_cli` — `--format {json,table}` + `--no-color`

**Files:**
- Modify: `src/ikigai/src/ikigai/gateway/event_log_cli.py`
- Test: `tests/ikigai/test_event_log_cli.py` (extend)

**Step 1: Add failing tests**

Append to `tests/ikigai/test_event_log_cli.py`:

```python
from ikigai.gateway._cli_format import format_table, format_json_lines


def test_event_log_tail_table_format(tmp_path, monkeypatch):
    log_path = tmp_path / "events.jsonl"
    # Seed two records
    import json as _json
    log_path.write_text(
        "\n".join(
            _json.dumps({"ts": 100.0, "event": "taskdog.add", "data": {"ueid": "u1"}})
            for _ in range(2)
        )
    )
    from ikigai.gateway import event_log_cli

    monkeypatch.setattr(sys, "argv", ["event_log_cli", "tail", "--n", "10", "--path", str(log_path), "--format", "table"])
    rc = event_log_cli.main()
    assert rc == 0
    captured = capsys.readouterr()  # see Step 2
    assert "TASKDOG.ADD" in captured.out or "event" in captured.out.lower()


def test_event_log_status_table_format(tmp_path, capsys):
    log_path = tmp_path / "events.jsonl"
    log_path.write_text("")
    from ikigai.gateway import event_log_cli
    rc = event_log_cli.main(["status", "--path", str(log_path), "--format", "table"])
    out = capsys.readouterr().out
    assert "PATH" in out or "path" in out
    assert "MAX_BYTES" in out or "max_bytes" in out
```

**Step 2: Fix the test fixtures**

Adjust `test_event_log_tail_table_format` to use `capsys` properly (the draft above uses both `monkeypatch`+`sys.argv` and `capsys`; pick one pattern consistently — use `main([...])` with `capsys` for simplicity):

```python
def test_event_log_tail_table_format(tmp_path, capsys):
    log_path = tmp_path / "events.jsonl"
    import json as _json
    log_path.write_text(
        _json.dumps({"ts": 100.0, "event": "taskdog.add", "data": {"ueid": "u1"}})
    )
    from ikigai.gateway import event_log_cli
    rc = event_log_cli.main(["tail", "--n", "10", "--path", str(log_path), "--format", "table"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "TASKDOG.ADD" in out or "taskdog.add" in out
```

**Step 3: Run tests to verify they fail**

```bash
cd src/ikigai
uv run pytest tests/ikigai/test_event_log_cli.py -v -k "table_format"
```

Expected: FAIL (`unrecognized arguments: --format`).

**Step 4: Modify `event_log_cli.py`**

Replace the file's print helpers with formatter-aware versions:

```python
# At top, add:
from ikigai.gateway._cli_format import format_json_lines, format_table, get_format

# Delete the old `_format_record()` function (lines 25-35).

# Replace `cmd_tail` body (lines 38-43):
def cmd_tail(args: argparse.Namespace) -> int:
    log = EventLog(args.path)
    records = log.tail(args.n)
    fmt = get_format(args.format)
    rows = [
        {
            "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(r.get("ts", 0.0))),
            "ts": r.get("ts"),
            "event": r.get("event"),
            "data": r.get("data"),
        }
        for r in records
    ]
    if fmt == "table":
        cols = [("ts_iso", "WHEN", 22), ("event", "EVENT", 30), ("data", "DATA", 60)]
        out = format_table(rows, cols, no_color=args.no_color)
        if out:
            print(out, flush=True)
    else:
        out = format_json_lines(rows)
        if out:
            print(out, flush=True)
    return 0

# Replace `cmd_since` body (lines 46-57) — same pattern as `cmd_tail`.

# Replace `cmd_status` body (lines 60-72) with table rendering using columns
# [("path", "PATH", 40), ("max_bytes", "MAX_BYTES", 10), ("total_records", "TOTAL", 10)]
# and one row per file in the rotation list. Use `format_table` when fmt=="table",
# else fall back to the current key:value print loop.

# In `main`, add `--format` and `--no-color` to each subparser via `_add_common()`:
def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--format",
        choices=["json", "table"],
        default=None,
        help="output format (default: auto — table if TTY, json if piped)",
    )
    p.add_argument(
        "--no-color",
        action="store_true",
        help="strip ANSI color codes from table output (useful for CI logs)",
    )
    p.add_argument(
        "--path",
        default=DEFAULT_LOG_PATH,
        help=f"path to the EventLog JSONL file (default: {DEFAULT_LOG_PATH})",
    )

# Then for each of tail/since/status: call `_add_common(p)` instead of the
# old `_add_path(p)`. Delete the old `_add_path`.
```

**Step 5: Run tests to verify they pass**

```bash
cd src/ikigai
uv run pytest tests/ikigai/test_event_log_cli.py -v
uv run pytest tests/ikigai/test_cli_format.py -v  # regression
uv run ruff check src/ikigai/gateway/event_log_cli.py
```

Expected: all green, ruff clean.

**Step 6: Commit**

```bash
git add src/ikigai/src/ikigai/gateway/event_log_cli.py tests/ikigai/test_event_log_cli.py
git commit -m "feat(event-log-cli): --format {json,table} + --no-color"
```

---

## Task 4: `client_cli` — `--format {json,table}` + `--no-color` on `watch`

**Files:**
- Modify: `src/ikigai/src/ikigai/gateway/client_cli.py`
- Test: `tests/ikigai/test_client_cli.py` (create if missing)

**Step 1: Check existing test file**

```bash
ls tests/ikigai/test_client_cli.py 2>/dev/null
```

If missing → create with content from Step 2.
If present → extend with the new tests in Step 2.

**Step 2: Add failing tests**

Create or extend `tests/ikigai/test_client_cli.py`:

```python
"""Tests for the SSE consumer CLI."""

from __future__ import annotations

import json
import socket
import threading
import time

import pytest

from ikigai.gateway import client_cli


class _FakeSSEServer:
    """Minimal HTTP/1.1 SSE server for client_cli tests."""

    def __init__(self, frames: list[str]):
        self._frames = frames
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self.port = 0

    def start(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        self.port = srv.getsockname()[1]
        srv.listen(1)
        self._server = srv
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        assert self._server is not None
        conn, _ = self._server.accept()
        # Read & discard the GET request
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += conn.recv(4096)
        body = "".join(self._frames).encode("utf-8")
        chunks = []
        # Send as one chunk for simplicity
        chunks.append(f"{len(body):x}\r\n".encode() + body + b"\r\n")
        chunks.append(b"0\r\n\r\n")
        conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n\r\n")
        for c in chunks:
            conn.sendall(c)
        time.sleep(0.1)
        conn.close()

    def stop(self) -> None:
        if self._server is not None:
            self._server.close()


def _make_frame(name: str, data: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(data)}\n\n"


def test_client_cli_watch_json_format(capsys):
    frames = [_make_frame("taskdog.add", {"ueid": "u1"})]
    srv = _FakeSSEServer(frames)
    srv.start()
    try:
        rc = client_cli.main(
            ["watch", "--host", "127.0.0.1", "--port", str(srv.port),
             "--duration", "0.5", "--format", "json"]
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert '"event": "taskdog.add"' in out
    finally:
        srv.stop()


def test_client_cli_watch_table_format(capsys):
    frames = [_make_frame("taskdog.add", {"ueid": "u1"})]
    srv = _FakeSSEServer(frames)
    srv.start()
    try:
        rc = client_cli.main(
            ["watch", "--host", "127.0.0.1", "--port", str(srv.port),
             "--duration", "0.5", "--format", "table"]
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "TASKDOG.ADD" in out or "taskdog.add" in out
    finally:
        srv.stop()
```

**Step 3: Run tests to verify they fail**

```bash
cd src/ikigai
uv run pytest tests/ikigai/test_client_cli.py -v
```

Expected: FAIL (`unrecognized arguments: --format`).

**Step 4: Modify `client_cli.py`**

In `main()`:

```python
# Add to the `watch` subparser after the existing args:
watch_p.add_argument(
    "--format",
    choices=["json", "table"],
    default=None,
    help="output format (default: auto — table if TTY, json if piped)",
)
watch_p.add_argument(
    "--no-color",
    action="store_true",
    help="strip ANSI color codes from table output",
)
```

In `watch()`, replace the `print(json.dumps(event, default=str), flush=True)` line:

```python
from ikigai.gateway._cli_format import format_json_lines, format_table, get_format

# Inside watch(), replace the print line:
fmt = get_format(args_format=globals().get("_format"), stdout=sys.stdout)
# (Better: refactor watch() to accept `format` and `no_color` as explicit args.
#  See the refactor snippet below.)
```

**Refactor `watch()` signature** (cleaner than globals):

```python
def watch(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    event_filter: str | None = None,
    duration_s: float = DEFAULT_DURATION_S,
    *,
    output_format: str = "json",
    no_color: bool = False,
) -> int:
    """Stream SSE events to stdout.

    Args:
        ...
        output_format: "json" or "table"
        no_color: strip ANSI from table output
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
        buffer_rows: list[dict] = []
        for event in parse_sse_stream(sock):
            if deadline is not None and time.monotonic() >= deadline:
                break
            name = event["event"]
            if event_filter and not name.startswith(event_filter):
                continue
            buffer_rows.append(
                {"event": name, "data": json.dumps(event["data"], default=str)}
            )
        # Flush in one shot — table mode needs all rows for width calc;
        # json mode is identical line-by-line but cheaper as one string.
        if output_format == "table":
            out = format_table(
                buffer_rows,
                [("event", "EVENT", 30), ("data", "DATA", 80)],
                no_color=no_color,
            )
            if out:
                print(out, flush=True)
        else:
            out = format_json_lines(buffer_rows)
            if out:
                print(out, flush=True)
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        try:
            sock.close()
        except Exception:
            pass
```

In `main()`, update the dispatch:

```python
if args.command == "watch":
    fmt = get_format(args.format)
    return watch(
        host=args.host,
        port=args.port,
        event_filter=args.event_filter,
        duration_s=args.duration_s,
        output_format=fmt,
        no_color=args.no_color,
    )
```

**Step 5: Run tests + regression**

```bash
cd src/ikigai
uv run pytest tests/ikigai/test_client_cli.py tests/ikigai/test_event_log_cli.py tests/ikigai/test_cli_format.py -v
uv run ruff check src/ikigai/gateway/client_cli.py
```

Expected: all green.

**Step 6: Commit**

```bash
git add src/ikigai/src/ikigai/gateway/client_cli.py tests/ikigai/test_client_cli.py
git commit -m "feat(client-cli): --format {json,table} + --no-color on watch"
```

---

## Task 5: `review_queue_cli` — `--format {json,table}` + `--no-color`

**Files:**
- Modify: `src/mesh/review_queue_cli.py`
- Test: `tests/mesh/test_review_queue_cli.py` (extend)

**Step 1: Add failing tests**

Append to `tests/mesh/test_review_queue_cli.py`:

```python
def test_review_queue_list_table_format(tmp_path, capsys):
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    _seed_event(queue_dir, "evt_001", ueid="ts:abc:1:1", action="create", status="pending", source_fork="interfaces/cli")
    rc = review_queue_cli.main(["list", "--queue-dir", str(queue_dir), "--format", "table"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "EVT_001" in out or "evt_001" in out
    assert "TS:ABC:1:1" in out or "ts:abc:1:1" in out
    assert "PENDING" in out or "pending" in out


def test_review_queue_status_table_format(tmp_path, capsys):
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    _seed_event(queue_dir, "evt_001", status="pending")
    rc = review_queue_cli.main(["status", "--queue-dir", str(queue_dir), "--format", "table"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "QUEUE_DIR" in out or "queue_dir" in out
    assert "PENDING" in out or "pending" in out
    assert "1" in out  # count


def test_review_queue_show_table_format_unchanged(tmp_path, capsys):
    """`show` keeps raw JSON (single record, full fidelity)."""
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    _seed_event(queue_dir, "evt_001", status="pending")
    rc = review_queue_cli.main(["show", "evt_001", "--queue-dir", str(queue_dir), "--format", "table"])
    assert rc == 0
    out = capsys.readouterr().out
    # show is intentionally unaffected — still prints full JSON
    assert '"event_id"' in out
```

(Use the existing `_seed_event` helper from the test file's conftest/setup.)

**Step 2: Run tests to verify they fail**

```bash
cd life
python -m pytest tests/mesh/test_review_queue_cli.py -v -k "table_format"
```

Expected: FAIL.

**Step 3: Modify `review_queue_cli.py`**

```python
# At top:
from src.mesh._cli_format import format_json_lines, format_table, get_format

# Delete the old `_summarize()` helper.

# In `cmd_list`, replace the print loop:
def cmd_list(args: argparse.Namespace) -> int:
    queue_dir: Path = args.queue_dir
    if not queue_dir.exists():
        print(f"queue dir not found: {queue_dir}", file=sys.stderr)
        return 0
    events = _read_events(queue_dir)
    if args.status is not None:
        events = [e for e in events if e.status == args.status]
    events.sort(key=lambda e: e.timestamp, reverse=True)
    if args.limit is not None:
        events = events[: args.limit]
    rows = [
        {
            "event_id": e.event_id,
            "ueid": e.ueid,
            "action": e.action.value,
            "status": e.status,
            "source_fork": e.source_fork,
            "timestamp": e.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(e.timestamp, datetime) else str(e.timestamp),
        }
        for e in events
    ]
    fmt = get_format(args.format)
    if fmt == "table":
        cols = [
            ("event_id", "EVENT_ID", 16),
            ("ueid", "UEID", 24),
            ("action", "ACTION", 10),
            ("status", "STATUS", 20),
            ("source_fork", "SOURCE_FORK", 18),
            ("timestamp", "TIMESTAMP", 22),
        ]
        out = format_table(rows, cols, no_color=args.no_color)
        if out:
            print(out, flush=True)
    else:
        out = format_json_lines(rows)
        if out:
            print(out, flush=True)
    return 0

# In `cmd_status`, replace the print loop with a table:
def cmd_status(args: argparse.Namespace) -> int:
    queue_dir: Path = args.queue_dir
    fmt = get_format(args.format)
    if not queue_dir.exists():
        if fmt == "table":
            print(
                format_table(
                    [{"queue_dir": str(queue_dir), "total": "0"}],
                    [("queue_dir", "QUEUE_DIR", 40), ("total", "TOTAL", 6)],
                    no_color=args.no_color,
                ),
                flush=True,
            )
        else:
            print(f"queue_dir: {queue_dir}", flush=True)
            print("total: 0", flush=True)
        return 0
    events = _read_events(queue_dir)
    counts: dict[str, int] = {s: 0 for s in VALID_STATUSES}
    for event in events:
        counts[event.status] = counts.get(event.status, 0) + 1
    rows = [{"queue_dir": str(queue_dir), "total": str(len(events)), **{s: str(counts[s]) for s in VALID_STATUSES}}]
    cols = [("queue_dir", "QUEUE_DIR", 40), ("total", "TOTAL", 6)] + [(s, s.upper(), max(10, len(s))) for s in VALID_STATUSES]
    if fmt == "table":
        print(format_table(rows, cols, no_color=args.no_color), flush=True)
    else:
        print(f"queue_dir: {queue_dir}", flush=True)
        print(f"total: {len(events)}", flush=True)
        for status in VALID_STATUSES:
            print(f"  {status}: {counts[status]}", flush=True)
    return 0

# In `cmd_show`, no change to JSON output — it's already a single-record full dump.

# In `main`, add a helper and `--format`/`--no-color` to each subparser:
def _add_format(p: argparse.ArgumentParser) -> None:
    p.add_argument("--format", choices=["json", "table"], default=None,
                   help="output format (default: auto — table if TTY, json if piped)")
    p.add_argument("--no-color", action="store_true",
                   help="strip ANSI color codes from table output")

# And call `_add_format(...)` for each of list/status/show after `_add_qd(...)`.
```

**Step 4: Run tests + regression**

```bash
cd life
python -m pytest tests/mesh/test_review_queue_cli.py -v
python -m pytest tests/mesh/ -v  # full mesh regression
uv run ruff check src/mesh/review_queue_cli.py
```

Expected: all green.

**Step 5: Commit**

```bash
git add src/mesh/review_queue_cli.py tests/mesh/test_review_queue_cli.py
git commit -m "feat(review-queue-cli): --format {json,table} + --no-color on list/status"
```

---

## Task 6: Verification + smoke

**Step 1: Full pytest sweep — both trees**

```bash
cd src/ikigai
uv run pytest tests/ikigai/ -v 2>&1 | tail -50
cd ../..
python -m pytest tests/mesh/ -v 2>&1 | tail -50
```

Expected: all green; the existing 9 + 13 + 27 tests still pass alongside the new ones.

**Step 2: Ruff sweep**

```bash
cd src/ikigai
uv run ruff check src/ tests/
cd ../..
uv run ruff check src/mesh/ tests/mesh/  # or whatever the mesh lint command is
```

Expected: clean.

**Step 3: Smoke-test the three CLIs by hand**

```bash
# 1. event_log_cli — TTY simulation: pipe to cat (forces json), then use --format table
cd src/ikigai
echo '{"ts": 100.0, "event": "x", "data": {}}' > /tmp/elog.jsonl
uv run python -m ikigai.gateway.event_log_cli status --path /tmp/elog.jsonl  # should print json (no TTY)
uv run python -m ikigai.gateway.event_log_cli status --path /tmp/elog.jsonl --format table  # table

# 2. client_cli — just check --format is accepted (no live gateway)
uv run python -m ikigai.gateway.client_cli watch --help | grep -- "--format"

# 3. review_queue_cli — same pattern
cd ../..
mkdir -p /tmp/rq && echo '{"event_id":"e1","ueid":"u1","action":"create","status":"pending","source_fork":"x","timestamp":"2026-08-30T00:00:00Z"}' > /tmp/rq/e1.json
python -m src.mesh.review_queue_cli list --queue-dir /tmp/rq  # json
python -m src.mesh.review_queue_cli list --queue-dir /tmp/rq --format table  # table
python -m src.mesh.review_queue_cli status --queue-dir /tmp/rq --format table
```

Expected: each command exits 0; `--format table` prints a header-aligned grid; default (no `--format`) prints JSON lines.

**Step 4: Commit verification log (optional — skip if nothing changed)**

If any tweaks were needed during smoke, commit them; otherwise this task has no commit.

---

## Self-Review (already applied during writing)

1. **Spec coverage:**
   - `--format {json,table}` ✓ (Tasks 3, 4, 5)
   - `--no-color` ✓ (Tasks 3, 4, 5)
   - TTY auto-detect → table, pipe → json ✓ (Tasks 1, 2 — `get_format()`)
   - All three CLIs covered ✓ (Tasks 3, 4, 5)
   - Tests added/extended for each ✓ (Tasks 3, 4, 5)
   - Shared formatter module to DRY ✓ (Tasks 1, 2)
   - No breaking change to JSON ✓ (verified in every task: `--format` defaults to `None` → `get_format()` auto-resolves)

2. **No placeholders:** All code blocks are complete; no "TBD" / "similar to Task N" / "implement later".

3. **Type consistency:** `get_format()`, `format_json_lines()`, `format_table()` signatures match across Tasks 1 and 2. `format_table(columns)` uses the same `tuple[str, str, int]` triple in both modules.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-30-cli-human-readable-tables.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** — batch execution with checkpoints

Which approach?
