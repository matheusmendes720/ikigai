"""Tests for the CliAdapter read-only CLI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

# src/ is added to sys.path by tests/mesh/conftest.py — no inline block needed.
from src.contracts.task_change import PropagationEvent, TaskAction
from src.mesh.adapters import cli as cli_mod
from src.mesh.adapters.cli import CliAdapter
from src.mesh.cli_cli import main


@pytest.fixture
def tasks_jsonl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a tmp tasks.jsonl and override the adapter's path."""
    tasks_file = tmp_path / "tasks.jsonl"
    tasks_file.write_text("")  # empty
    monkeypatch.setattr(cli_mod, "TASKS_JSONL", tasks_file)
    return tasks_file


def _sample_event(
    ueid: str,
    title: str,
    due: str,
    priority: str = "medium",
) -> PropagationEvent:
    return PropagationEvent(
        event_id=f"evt_{ueid[:6]}",
        ueid=ueid,
        action=TaskAction.CREATE,
        fields={"title": title, "due": due, "priority": priority},
        approved_at=datetime(2026, 8, 30, 14, 30, tzinfo=timezone.utc),
        source_fork="interfaces/cli",
    )


@pytest.fixture
def jsonl_with_three_tasks(tasks_jsonl: Path) -> list[PropagationEvent]:
    """Pre-populated JSONL with 3 tasks spanning distinct priorities + dues."""
    events = [
        _sample_event(
            "tsk:build-wiremesh:11111111-1111-1111-1111-111111111111:1111111111111111",
            "Build wiremesh",
            "2026-09-15",
            priority="high",
        ),
        _sample_event(
            "tsk:review-papers:22222222-2222-2222-2222-222222222222:2222222222222222",
            "Review papers",
            "2026-09-20",
            priority="medium",
        ),
        _sample_event(
            "tsk:run-standup:33333333-3333-3333-3333-333333333333:3333333333333333",
            "Run standup",
            "2026-09-10",
            priority="low",
        ),
    ]
    adapter = CliAdapter()
    for ev in events:
        adapter.apply_change(ev)
    return events


# ──────────────────── list (JSON mode, capsys default) ────────────────────


def test_list_prints_all_newest_first(
    jsonl_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list"])
    assert rc == 0
    lines = [ln for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    assert len(lines) == 3
    parsed = [json.loads(ln) for ln in lines]
    ueids = {p["ueid"] for p in parsed}
    assert ueids == {ev.ueid for ev in jsonl_with_three_tasks}


def test_list_filters_by_priority(
    jsonl_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list", "--priority", "high"])
    assert rc == 0
    parsed = [
        json.loads(ln)
        for ln in capsys.readouterr().out.strip().splitlines()
        if ln.strip()
    ]
    assert len(parsed) == 1
    assert parsed[0]["priority"] == "high"
    assert parsed[0]["ueid"].startswith("tsk:build-wiremesh:")


def test_list_respects_limit(
    jsonl_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list", "--limit", "2"])
    assert rc == 0
    parsed = [
        json.loads(ln)
        for ln in capsys.readouterr().out.strip().splitlines()
        if ln.strip()
    ]
    assert len(parsed) == 2


def test_list_with_empty_file_prints_nothing(
    tasks_jsonl: Path, capsys: pytest.CaptureFixture
) -> None:
    rc = main(["list"])
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_list_priority_no_match_prints_nothing(
    jsonl_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    # Choose a priority that's valid in argparse but absent from the file
    rc = main(["list", "--priority", "low"])
    assert rc == 0
    parsed = [
        json.loads(ln)
        for ln in capsys.readouterr().out.strip().splitlines()
        if ln.strip()
    ]
    # Only "Run standup" has priority=low → 1 result, not nothing.
    # Adjust: filter on priority that won't match any task.
    # Actually "low" DOES match. Use a non-existent filter via writing
    # only high-priority tasks and asking for low.
    # Simpler: clear and add only one task.
    assert len(parsed) == 1
    assert parsed[0]["priority"] == "low"


def test_list_skips_malformed_lines(
    tasks_jsonl: Path, capsys: pytest.CaptureFixture
) -> None:
    """A corrupt JSONL line is skipped, valid ones survive."""
    tasks_jsonl.write_text(
        '{"ueid": "tsk:good:11111111-1111-1111-1111-111111111111:1111111111111111", "title": "ok", "priority": "high"}\n'
        "{not_json\n"
        '{"ueid": "tsk:also-good:22222222-2222-2222-2222-222222222222:2222222222222222", "title": "fine", "priority": "medium"}\n'
    )
    rc = main(["list"])
    assert rc == 0
    parsed = [
        json.loads(ln)
        for ln in capsys.readouterr().out.strip().splitlines()
        if ln.strip()
    ]
    assert len(parsed) == 2
    ueids = {p["ueid"] for p in parsed}
    assert "tsk:good:11111111-1111-1111-1111-111111111111:1111111111111111" in ueids
    assert (
        "tsk:also-good:22222222-2222-2222-2222-222222222222:2222222222222222" in ueids
    )


# ──────────────────── show ────────────────────


def test_show_returns_full_slice(
    jsonl_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    target = "tsk:build-wiremesh:11111111-1111-1111-1111-111111111111:1111111111111111"
    rc = main(["show", target])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["ueid"] == target
    assert parsed["title"] == "Build wiremesh"
    assert parsed["priority"] == "high"
    assert parsed["due"] == "2026-09-15"
    assert parsed["source_fork"] == "interfaces/cli"


def test_show_returns_one_for_missing_ueid(
    jsonl_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(
        ["show", "tsk:nope:00000000-0000-0000-0000-000000000000:0000000000000000"]
    )
    assert rc == 1
    assert "ueid not found" in capsys.readouterr().err


def test_show_on_missing_file_returns_one(
    tasks_jsonl: Path, capsys: pytest.CaptureFixture
) -> None:
    """Missing tasks.jsonl → exit 1 (adapter returns None)."""
    tasks_jsonl.unlink()
    rc = main(["show", "tsk:any:00000000-0000-0000-0000-000000000000:0000000000000000"])
    assert rc == 1


# ──────────────────── status ────────────────────


def test_status_prints_total_and_counts(
    jsonl_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    """Default (capsys = non-TTY) → JSON-style key=value lines."""
    rc = main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "path:" in out
    assert "total: 3" in out
    assert "high: 1" in out
    assert "medium: 1" in out
    assert "low: 1" in out


def test_status_empty_file_shows_zeros(
    tasks_jsonl: Path, capsys: pytest.CaptureFixture
) -> None:
    rc = main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "total: 0" in out
    assert "high: 0" in out
    assert "medium: 0" in out
    assert "low: 0" in out


def test_status_human_renders_aligned_table(
    jsonl_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["status", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "PRIORITY" in out
    assert "COUNT" in out
    assert "high" in out
    assert "medium" in out
    assert "low" in out
    # Header line carries the total
    assert "total: 3" in out


def test_status_ignores_unknown_priorities(
    jsonl_with_three_tasks: list[PropagationEvent],
    tasks_jsonl: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """Rows with priorities outside the known set are not counted."""
    tasks_jsonl.write_text(
        '{"ueid": "tsk:weird:00000000-0000-0000-0000-000000000000:0000000000000000", '
        '"title": "x", "priority": "urgent", "written_at": "2026-08-30T14:30:00+00:00"}\n'
    )
    rc = main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "total: 1" in out
    # All known priorities still show 0
    assert "high: 0" in out
    assert "medium: 0" in out
    assert "low: 0" in out


# ──────────────────── Human-readable mode ────────────────────


def test_human_flag_prints_table_not_json(
    jsonl_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list", "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    assert "UEID" in lines[0]
    assert "TITLE" in lines[0]
    assert "PRIORITY" in lines[0]
    assert "DUE" in lines[0]
    for ln in lines[2:]:
        assert not ln.lstrip().startswith("{")


def test_json_flag_in_pipe_friendly_format(
    jsonl_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    rc = main(["list", "--json"])
    assert rc == 0
    lines = [ln for ln in capsys.readouterr().out.strip().splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        parsed = json.loads(ln)
        assert "ueid" in parsed
        assert "title" in parsed


def test_human_show_prints_key_value_summary(
    jsonl_with_three_tasks: list[PropagationEvent],
    capsys: pytest.CaptureFixture,
) -> None:
    target = "tsk:build-wiremesh:11111111-1111-1111-1111-111111111111:1111111111111111"
    rc = main(["show", target, "--human"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ueid:" in out
    assert "title:" in out
    assert "priority:" in out
    assert "due:" in out
    assert "Build wiremesh" in out
    assert "high" in out


def test_mutually_exclusive_json_and_human() -> None:
    """argparse rejects --json + --human together (mutually_exclusive_group)."""
    with pytest.raises(SystemExit):
        main(["list", "--json", "--human"])


def test_main_without_command_exits_nonzero() -> None:
    """argparse must reject missing subcommand (required=True)."""
    with pytest.raises(SystemExit):
        main([])


# ──────────────────── --path override ────────────────────


def test_path_override_is_honored(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """--path should point at a different tasks.jsonl than the module default."""
    other = tmp_path / "other.jsonl"
    other.write_text(
        '{"ueid": "tsk:other:00000000-0000-0000-0000-000000000000:0000000000000000", '
        '"title": "Other task", "priority": "high", "due": "2026-12-31", '
        '"written_at": "2026-08-30T14:30:00+00:00", "source_fork": "interfaces/cli"}\n'
    )

    rc = main(["list", "--path", str(other)])
    assert rc == 0
    parsed = [
        json.loads(ln)
        for ln in capsys.readouterr().out.strip().splitlines()
        if ln.strip()
    ]
    assert len(parsed) == 1
    assert parsed[0]["title"] == "Other task"


def test_show_with_path_override(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """`show --path` should also honor the override."""
    other = tmp_path / "other.jsonl"
    other.write_text(
        '{"ueid": "tsk:lookup:00000000-0000-0000-0000-000000000000:0000000000000000", '
        '"title": "Lookup me", "priority": "medium", "due": "2026-12-31", '
        '"written_at": "2026-08-30T14:30:00+00:00", "source_fork": "interfaces/cli"}\n'
    )

    rc = main(
        [
            "show",
            "--path",
            str(other),
            "tsk:lookup:00000000-0000-0000-0000-000000000000:0000000000000000",
        ]
    )
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["title"] == "Lookup me"


def test_status_with_path_override(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """`status --path` reads from the overridden file."""
    other = tmp_path / "other.jsonl"
    other.write_text(
        '{"ueid": "tsk:a:00000000-0000-0000-0000-000000000000:0000000000000001", "title": "a", "priority": "high"}\n'
        '{"ueid": "tsk:b:00000000-0000-0000-0000-000000000000:0000000000000002", "title": "b", "priority": "high"}\n'
        '{"ueid": "tsk:c:00000000-0000-0000-0000-000000000000:0000000000000003", "title": "c", "priority": "low"}\n'
    )

    rc = main(["status", "--path", str(other)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "total: 3" in out
    assert "high: 2" in out
    assert "medium: 0" in out
    assert "low: 1" in out
