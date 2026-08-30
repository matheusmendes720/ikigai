"""Tests for the EventLog inspector CLI."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from ikigai.gateway.event_log import EventLog
from ikigai.gateway.event_log_cli import _format_record, main


@pytest.fixture
def log_with_events(tmp_path: Path) -> EventLog:
    """Pre-populated EventLog with 5 known events."""
    log = EventLog(tmp_path / "events.jsonl")
    for i in range(5):
        log.append("tick", {"i": i, "label": f"event-{i}"})
    return log


def test_format_record_includes_iso_timestamp() -> None:
    record = {"ts": 1700000000.0, "event": "x", "data": {"k": 1}}
    out = json.loads(_format_record(record))
    assert out["ts_iso"] == "2023-11-14T22:13:20Z"
    assert out["event"] == "x"
    assert out["data"] == {"k": 1}


def test_tail_subcommand_prints_last_n(
    log_with_events: EventLog, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    rc = main([
        "tail", "--path", str(tmp_path / "events.jsonl"), "--n", "3",
    ])
    assert rc == 0
    lines = [ln for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    assert len(lines) == 3
    parsed = [json.loads(ln) for ln in lines]
    assert [p["data"]["i"] for p in parsed] == [2, 3, 4]


def test_since_subcommand_with_relative_seconds(
    log_with_events: EventLog, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """since --seconds-ago 60 must yield all events appended in the test."""
    rc = main([
        "since", "--path", str(tmp_path / "events.jsonl"), "--seconds-ago", "60",
    ])
    assert rc == 0
    lines = [ln for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    assert len(lines) == 5


def test_since_subcommand_with_absolute_timestamp(
    log_with_events: EventLog, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """since --timestamp must filter to events with ts >= timestamp."""
    time.sleep(0.01)
    cutoff = time.time()
    time.sleep(0.01)
    log_with_events.append("late", {"i": 99})

    rc = main([
        "since", "--path", str(tmp_path / "events.jsonl"), "--timestamp", str(cutoff),
    ])
    assert rc == 0
    parsed = [json.loads(ln) for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    assert all(p["ts"] >= cutoff for p in parsed)
    assert any(p["event"] == "late" for p in parsed)


def test_status_subcommand_shows_metadata(
    log_with_events: EventLog, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    rc = main([
        "status", "--path", str(tmp_path / "events.jsonl"),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "path:" in out
    assert "max_bytes:" in out
    assert "max_rotations:" in out
    assert "total_records: 5" in out
    assert "active:" in out


def test_missing_log_file_returns_empty_for_tail(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    rc = main([
        "tail", "--path", str(tmp_path / "never_written.jsonl"), "--n", "5",
    ])
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_missing_log_file_returns_empty_for_since(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    rc = main([
        "since", "--path", str(tmp_path / "never_written.jsonl"), "--seconds-ago", "60",
    ])
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_missing_log_file_returns_zero_records_for_status(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    rc = main([
        "status", "--path", str(tmp_path / "never_written.jsonl"),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "total_records: 0" in out


def test_main_without_command_exits_nonzero() -> None:
    """argparse must reject missing subcommand (required=True)."""
    with pytest.raises(SystemExit):
        main([])


# ─────────────────── Human-readable table mode (B6 enhancement) ───────────────────


def test_human_flag_prints_table_not_json(
    log_with_events: EventLog, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """`--human` forces aligned table with column headers, even when capsys (not a TTY)."""
    rc = main([
        "tail", "--path", str(tmp_path / "events.jsonl"), "--n", "3", "--human",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    # JSON mode test would parse each line as JSON — here the first line is the header.
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    assert lines[0].startswith("TS")
    assert "EVENT" in lines[0]
    assert "DATA" in lines[0]
    # Separator line
    assert set(lines[1]) <= {"-", " "}
    # Body rows are NOT valid JSON (no leading brace)
    for ln in lines[2:]:
        assert not ln.lstrip().startswith("{")


def test_json_flag_in_pipe_friendly_format(
    log_with_events: EventLog, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """`--json` forces JSON lines even when stdout would be detected as TTY."""
    rc = main([
        "tail", "--path", str(tmp_path / "events.jsonl"), "--n", "2", "--json",
    ])
    assert rc == 0
    lines = [ln for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    assert len(lines) == 2
    # Each line is valid JSON with ts_iso field
    for ln in lines:
        parsed = json.loads(ln)
        assert "ts_iso" in parsed
        assert parsed["event"] == "tick"


def test_default_mode_with_capsys_is_json(
    log_with_events: EventLog, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Without --json/--human, capsys redirects to non-TTY → defaults to JSON.

    Confirms the TTY auto-detect path: piped automation gets JSON, the operator's
    terminal gets tables.
    """
    rc = main([
        "tail", "--path", str(tmp_path / "events.jsonl"), "--n", "2",
    ])
    assert rc == 0
    lines = [ln for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    parsed = [json.loads(ln) for ln in lines]
    assert len(parsed) == 2


def test_human_status_shows_aligned_columns(
    log_with_events: EventLog, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """`status --human` renders the candidate-file rows as an aligned table."""
    rc = main([
        "status", "--path", str(tmp_path / "events.jsonl"), "--human",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "LABEL" in out
    assert "FILE" in out
    assert "SIZE_BYTES" in out
    # Body row labelled 'active'
    assert "active" in out


def test_summarize_data_tool_call() -> None:
    """Tool-shaped data summaries are kept short for table readability."""
    from ikigai.gateway.event_log_cli import _summarize_data
    summary = _summarize_data({"tool": "taskdog.add", "arguments": {"title": "x"}})
    assert "taskdog.add" in summary
    assert "title" in summary


def test_summarize_data_long_payload_is_truncated() -> None:
    """Payloads >80 chars get truncated so the table stays readable."""
    from ikigai.gateway.event_log_cli import _summarize_data
    huge = {"k": "x" * 200}
    summary = _summarize_data(huge)
    assert len(summary) <= 80
    assert summary.endswith("...")


def test_mutually_exclusive_json_and_human() -> None:
    """Passing both --json and --human must fail (argparse mutually_exclusive_group)."""
    with pytest.raises(SystemExit):
        main(["tail", "--json", "--human"])
