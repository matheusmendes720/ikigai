"""Tests for the review queue inspector CLI."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Ensure src/ is on sys.path so `from src.mesh...` resolves when pytest is
# invoked from the project root with no explicit PYTHONPATH. The conftest.py
# in tests/mesh/ also adds this path; this is a belt-and-braces fallback.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC = _PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from src.contracts.task_change import TaskAction, TaskChange
from src.mesh import queue as queue_mod
from src.mesh.review_queue_cli import _read_events, _summarize, main


@pytest.fixture
def queue_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a tmp queue dir and override the module's QUEUE_DIR."""
    qdir = tmp_path / "review_queue"
    qdir.mkdir()
    monkeypatch.setattr(queue_mod, "QUEUE_DIR", qdir)
    return qdir


def _sample_event(
    event_id: str = "evt_001",
    ueid: str = "tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000",
    status: str = "pending",
    ts: datetime | None = None,
) -> TaskChange:
    return TaskChange(
        event_id=event_id,
        ueid=ueid,
        action=TaskAction.CREATE,
        fields={"title": "Test"},
        source_fork="interfaces/cli",
        timestamp=ts or datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc),
        status=status,  # type: ignore[arg-type]
    )


@pytest.fixture
def queue_with_events(queue_dir: Path) -> list[TaskChange]:
    """Queue pre-populated with 5 events spanning all key statuses."""
    base_ts = datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc)
    events = [
        _sample_event("evt_001", status="pending", ts=base_ts.replace(hour=14)),
        _sample_event("evt_002", status="pending", ts=base_ts.replace(hour=15)),
        _sample_event("evt_003", status="approved", ts=base_ts.replace(hour=16)),
        _sample_event("evt_004", status="rejected", ts=base_ts.replace(hour=17)),
        _sample_event("evt_005", status="propagated", ts=base_ts.replace(hour=18)),
    ]
    for event in events:
        queue_mod.enqueue(event)
    return events


def test_read_events_returns_empty_for_missing_dir(tmp_path: Path) -> None:
    """Missing dir must yield empty list (not raise)."""
    missing = tmp_path / "never_existed"
    assert _read_events(missing) == []


def test_read_events_skips_malformed_files(queue_dir: Path) -> None:
    """Corrupt JSON files are skipped, valid ones survive."""
    (queue_dir / "good.json").write_text(
        _sample_event("evt_ok").model_dump_json(), encoding="utf-8"
    )
    (queue_dir / "bad.json").write_text("{corrupt\n", encoding="utf-8")
    events = _read_events(queue_dir)
    assert [e.event_id for e in events] == ["evt_ok"]


def test_summarize_includes_required_fields() -> None:
    summary = json.loads(_summarize(_sample_event("evt_x")))
    assert summary["event_id"] == "evt_x"
    assert summary["action"] == "create"
    assert summary["status"] == "pending"
    assert summary["source_fork"] == "interfaces/cli"
    assert summary["timestamp"] == "2026-08-28T14:30:00Z"


def test_list_subcommand_prints_all_newest_first(
    queue_with_events: list[TaskChange],
    queue_dir: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list", "--queue-dir", str(queue_dir)])
    assert rc == 0
    lines = [ln for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    assert len(lines) == 5
    parsed = [json.loads(ln) for ln in lines]
    # Newest first → evt_005 (18h) before evt_001 (14h)
    assert [p["event_id"] for p in parsed] == [
        "evt_005",
        "evt_004",
        "evt_003",
        "evt_002",
        "evt_001",
    ]


def test_list_subcommand_filters_by_status(
    queue_with_events: list[TaskChange],
    queue_dir: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list", "--queue-dir", str(queue_dir), "--status", "pending"])
    assert rc == 0
    parsed = [json.loads(ln) for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    assert len(parsed) == 2
    assert all(p["status"] == "pending" for p in parsed)


def test_list_subcommand_respects_limit(
    queue_with_events: list[TaskChange],
    queue_dir: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list", "--queue-dir", str(queue_dir), "--limit", "2"])
    assert rc == 0
    parsed = [json.loads(ln) for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    assert len(parsed) == 2


def test_status_subcommand_shows_counts(
    queue_with_events: list[TaskChange],
    queue_dir: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["status", "--queue-dir", str(queue_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "queue_dir:" in out
    assert "total: 5" in out
    assert "pending: 2" in out
    assert "approved: 1" in out
    assert "rejected: 1" in out
    assert "propagated: 1" in out
    # Zero-count statuses are also printed (full breakdown)
    assert "partial_propagation: 0" in out
    assert "clarified: 0" in out


def test_status_subcommand_handles_missing_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Missing dir prints total: 0 + zeros for all statuses."""
    rc = main(["status", "--queue-dir", str(tmp_path / "never_existed")])
    assert rc == 0
    out = capsys.readouterr().out
    assert "total: 0" in out
    assert "pending: 0" in out


def test_show_subcommand_prints_full_event(
    queue_with_events: list[TaskChange],
    queue_dir: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["show", "--queue-dir", str(queue_dir), "evt_003"])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["event_id"] == "evt_003"
    assert parsed["status"] == "approved"
    assert parsed["action"] == "create"


def test_show_subcommand_returns_one_for_missing_event(
    queue_with_events: list[TaskChange],
    queue_dir: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["show", "--queue-dir", str(queue_dir), "evt_does_not_exist"])
    assert rc == 1
    assert "event not found" in capsys.readouterr().err


def test_show_subcommand_returns_one_for_malformed_file(
    queue_dir: Path, capsys: pytest.CaptureFixture
) -> None:
    (queue_dir / "evt_bad.json").write_text("{not_json", encoding="utf-8")
    rc = main(["show", "--queue-dir", str(queue_dir), "evt_bad"])
    assert rc == 1


def test_main_without_command_exits_nonzero() -> None:
    """argparse must reject missing subcommand (required=True)."""
    with pytest.raises(SystemExit):
        main([])


def test_list_subcommand_skips_malformed_files(
    queue_dir: Path, capsys: pytest.CaptureFixture
) -> None:
    """list must not crash on a malformed file mixed with valid ones."""
    queue_mod.enqueue(_sample_event("evt_good"))
    (queue_dir / "evt_corrupt.json").write_text("garbage\n", encoding="utf-8")
    rc = main(["list", "--queue-dir", str(queue_dir)])
    assert rc == 0
    parsed = [
        json.loads(ln)
        for ln in capsys.readouterr().out.strip().splitlines()
        if ln.strip()
    ]
    assert [p["event_id"] for p in parsed] == ["evt_good"]


# ─────────────────── Human-readable table mode ───────────────────


def test_human_flag_prints_table_not_json(
    queue_with_events: list[TaskChange],
    queue_dir: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """`--human` forces aligned ASCII table even when capsys (non-TTY)."""
    rc = main(["list", "--queue-dir", str(queue_dir), "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    # First line is the uppercase header row
    assert "STATUS" in lines[0] and "EVENT_ID" in lines[0] and "ACTION" in lines[0]
    # Body lines are NOT valid JSON
    for ln in lines[2:]:
        assert not ln.lstrip().startswith("{")


def test_json_flag_in_pipe_friendly_format(
    queue_with_events: list[TaskChange],
    queue_dir: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """`--json` forces JSON-per-line even when stdout would be a TTY."""
    rc = main(["list", "--queue-dir", str(queue_dir), "--json"])
    assert rc == 0
    lines = [ln for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    parsed = [json.loads(ln) for ln in lines]
    assert len(parsed) == 5
    assert {p["event_id"] for p in parsed} == {"evt_001", "evt_002", "evt_003", "evt_004", "evt_005"}


def test_default_mode_with_capsys_is_json(
    queue_with_events: list[TaskChange],
    queue_dir: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """Without --json/--human, capsys is non-TTY → JSON mode preserved."""
    rc = main(["list", "--queue-dir", str(queue_dir)])
    assert rc == 0
    lines = [ln for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    parsed = [json.loads(ln) for ln in lines]
    assert len(parsed) == 5


def test_human_status_shows_aligned_columns(
    queue_with_events: list[TaskChange],
    queue_dir: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """`status --human` renders status rows as an aligned table."""
    rc = main(["status", "--queue-dir", str(queue_dir), "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS" in out and "COUNT" in out
    # Total appears in the header line
    assert "total: 5" in out


def test_human_status_handles_missing_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """`status --human` on missing dir prints queue_dir header + aligned zero rows."""
    rc = main(["status", "--queue-dir", str(tmp_path / "never_existed"), "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS" in out and "COUNT" in out
    # Each status row: '<status-padded>  0    ' — verify by line starts + 0 presence.
    for status in ("pending", "approved", "rejected", "propagated", "partial_propagation", "clarified"):
        line = next(ln for ln in out.splitlines() if ln.lstrip().startswith(status))
        assert "0" in line


def test_human_show_prints_summary_and_fields(
    queue_with_events: list[TaskChange],
    queue_dir: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """`show <id> --human` prints key=value summary block + indented JSON fields."""
    rc = main(["show", "--queue-dir", str(queue_dir), "evt_001", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "event_id:   evt_001" in out
    assert "action:     create" in out
    assert "status:     pending" in out
    assert "fields:" in out


def test_mutually_exclusive_json_and_human() -> None:
    """argparse rejects --json + --human together (mutually_exclusive_group)."""
    with pytest.raises(SystemExit):
        main(["list", "--json", "--human"])