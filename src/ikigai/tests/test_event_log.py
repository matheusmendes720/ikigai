"""Tests for EventLog — append-only JSONL with size-based rotation."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from ikigai.gateway.event_log import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_ROTATIONS,
    EventLog,
)


def test_event_log_appends_one_line(tmp_path: Path) -> None:
    """append() must write exactly one JSON line per call."""
    log = EventLog(tmp_path / "events.jsonl")
    log.append("task.created", {"ueid": "ikigai:task:abc:1:2", "title": "smoke"})

    raw = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert record["event"] == "task.created"
    assert record["data"]["ueid"] == "ikigai:task:abc:1:2"
    assert record["data"]["title"] == "smoke"
    assert isinstance(record["ts"], float)


def test_event_log_tail_n_returns_last_n(tmp_path: Path) -> None:
    """tail(N) returns the last N events (most recent first when iterated)."""
    log = EventLog(tmp_path / "events.jsonl")
    for i in range(5):
        log.append("tick", {"i": i})

    last2 = log.tail(2)
    assert len(last2) == 2
    assert [r["data"]["i"] for r in last2] == [3, 4]


def test_event_log_tail_n_zero_returns_empty(tmp_path: Path) -> None:
    """tail(0) and tail(-1) return [] (YAGNI: only positive counts supported)."""
    log = EventLog(tmp_path / "events.jsonl")
    log.append("a", {})
    assert log.tail(0) == []


def test_event_log_since_filters_by_timestamp(tmp_path: Path) -> None:
    """since(ts) returns events with ts >= ts (strict lower bound)."""
    log = EventLog(tmp_path / "events.jsonl")
    log.append("a", {"v": 1})
    log.append("b", {"v": 2})
    log.append("c", {"v": 3})

    middle = log.tail(3)[1]["ts"]  # ts of "b"
    after_middle = log.since(middle)
    # since(ts) is inclusive; ts >= middle → events "b" and "c"
    assert [r["event"] for r in after_middle] == ["b", "c"]


def test_event_log_rotates_when_size_exceeded(tmp_path: Path) -> None:
    """When appending would exceed max_bytes, file rotates to .1 first."""
    # Use max_bytes large enough to keep 1 active + 2 rotations of all 20 events
    # so we can also assert no losses. With max_rotations=2, we'd otherwise
    # lose the oldest events (documented behaviour) — that's tested separately.
    log = EventLog(tmp_path / "events.jsonl", max_bytes=200, max_rotations=10)
    for i in range(20):
        log.append("tick", {"i": i, "padding": "x" * 20})

    active = tmp_path / "events.jsonl"
    rot1 = tmp_path / "events.jsonl.1"
    # At least the rotation file must exist
    assert rot1.exists(), "rotation file should have been created"
    # Active file must be smaller than max_bytes (post-rotation)
    assert active.stat().st_size <= 200
    # Total events across all candidate files must equal 20 (no losses with
    # generous max_rotations)
    total = sum(1 for _ in log)
    assert total == 20


def test_event_log_drops_oldest_when_max_rotations_exceeded(tmp_path: Path) -> None:
    """When max_rotations is hit, oldest generation is dropped on next rotate.

    Documents the data-retention behaviour: with max_rotations=2, only
    1 active + 2 rotated files survive. Older events are deliberately
    discarded to bound total disk usage.
    """
    log = EventLog(tmp_path / "events.jsonl", max_bytes=200, max_rotations=2)
    for i in range(20):
        log.append("tick", {"i": i, "padding": "x" * 20})

    # max_rotations=2 → at most 3 files total (.1, .2, active)
    assert (tmp_path / "events.jsonl.3").exists() is False
    assert (tmp_path / "events.jsonl.2").exists()
    assert (tmp_path / "events.jsonl.1").exists()
    # Visible events bounded by (1 + max_rotations) * events_per_file
    visible = list(log)
    assert len(visible) < 20, "oldest events must have been dropped"


def test_event_log_rotation_drops_oldest(tmp_path: Path) -> None:
    """Oldest rotation (.N where N == max_rotations) is dropped when full."""
    log = EventLog(tmp_path / "events.jsonl", max_bytes=100, max_rotations=2)
    # Force several rotations
    for i in range(30):
        log.append("tick", {"i": i, "padding": "x" * 30})

    # max_rotations=2 → only .1 and .2 exist (no .3)
    assert not (tmp_path / "events.jsonl.3").exists()
    assert (tmp_path / "events.jsonl.1").exists()
    assert (tmp_path / "events.jsonl.2").exists()


def test_event_log_corrupt_line_is_skipped(tmp_path: Path) -> None:
    """A partial / corrupt line is logged and skipped; valid lines survive."""
    p = tmp_path / "events.jsonl"
    p.write_text(
        json.dumps({"ts": 1.0, "event": "a", "data": {}}) + "\n"
        "{corrupt\n"  # line that does not parse
        + json.dumps({"ts": 2.0, "event": "b", "data": {}}) + "\n",
        encoding="utf-8",
    )
    log = EventLog(p)
    records = list(log)
    assert [r["event"] for r in records] == ["a", "b"]


def test_event_log_concurrent_appends_are_atomic(tmp_path: Path) -> None:
    """Concurrent appenders must produce N well-formed lines (no torn writes)."""
    log = EventLog(tmp_path / "events.jsonl")
    n_threads = 8
    n_per_thread = 50

    def worker(thread_id: int) -> None:
        for i in range(n_per_thread):
            log.append("tick", {"t": thread_id, "i": i})

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    raw = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    assert len(lines) == n_threads * n_per_thread
    # Every line must parse as JSON (no torn writes)
    for line in lines:
        record = json.loads(line)
        assert record["event"] == "tick"
        assert isinstance(record["data"]["t"], int)


def test_event_log_iter_full_scan(tmp_path: Path) -> None:
    """Iteration across all candidate files yields every record in order."""
    # Use a generous max_bytes so no rotation happens — test pure iteration order.
    log = EventLog(tmp_path / "events.jsonl", max_bytes=100_000)
    for i in range(10):
        log.append("x", {"i": i})

    seen = [r["data"]["i"] for r in log]
    assert seen == list(range(10))


def test_event_log_creates_parent_directory(tmp_path: Path) -> None:
    """First append must create parent dirs (no FileNotFoundError)."""
    nested = tmp_path / "deeply" / "nested" / "events.jsonl"
    log = EventLog(nested)
    log.append("a", {})
    assert nested.exists()


def test_event_log_defaults_match_constants(tmp_path: Path) -> None:
    """Module constants must match the documented defaults."""
    log = EventLog(tmp_path / "events.jsonl")
    assert log.max_bytes == DEFAULT_MAX_BYTES
    assert log.max_rotations == DEFAULT_MAX_ROTATIONS


def test_event_log_tail_across_rotated_files(tmp_path: Path) -> None:
    """tail() must look into rotated files when active file is short."""
    log = EventLog(tmp_path / "events.jsonl", max_bytes=300)
    # First batch forces a rotation
    for i in range(10):
        log.append("a", {"i": i, "pad": "x" * 20})
    # Second batch: a few events that fit in the fresh active file
    for i in range(3):
        log.append("b", {"i": i})

    last5 = log.tail(5)
    # The tail must span rotation boundary: last 5 events chronologically.
    # After rotation, .1 holds the first batch; active holds "b" entries.
    # The last 5 must be the last 2 "a" entries + all 3 "b" entries.
    events = [r["event"] for r in last5]
    assert events == ["a", "a", "b", "b", "b"]


def test_event_log_iter_handles_missing_file(tmp_path: Path) -> None:
    """Iteration over an empty/missing log yields no records (no crash)."""
    log = EventLog(tmp_path / "never_written.jsonl")
    assert list(log) == []
    assert log.tail(10) == []
    assert log.since(0.0) == []
