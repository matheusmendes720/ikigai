"""Integration tests for ``journal interact`` command.

Each test that needs to simulate questionary input patches the relevant
prompt_toolkit output + questionary ask locally per-test (not autouse).
State is isolated per-test via the autouse ``_isolated_state`` fixture in conftest.py.
"""
from __future__ import annotations

import io
import json

from typer.testing import CliRunner

from operational.cli import state as cli_state
from operational.cli.app import app

runner = CliRunner()


def _parse_json_output(output: str) -> dict:
    """Extract JSON from CliRunner output (telemetry lines may precede the payload)."""
    idx = output.find("\n{")
    if idx < 0:
        idx = output.find("{")
    assert idx >= 0, f"No JSON object found in:\n{output!r}"
    return json.loads(output[idx:])


class Answers:
    """Callable that returns one canned answer per call, then None."""

    def __init__(self, answers: list[str | None]) -> None:
        """Initialize with a list of canned answers.

        Args:
            answers: List of strings to return sequentially. When exhausted, returns None.
        """
        self._answers = answers
        self._index = 0

    def __call__(self) -> str | None:
        if self._index >= len(self._answers):
            return None
        val = self._answers[self._index]
        self._index += 1
        return val


def _patch_questionary_ask(monkeypatch, answers: list[str | None]) -> None:
    """Patch prompt_toolkit output + questionary Question.ask to return canned answers."""
    import questionary
    from prompt_toolkit.output.vt100 import Vt100_Output
    from prompt_toolkit.output import defaults

    class _FakeSize:
        def get_size(self):
            return (24, 80)

    def _fake_create_output():
        return Vt100_Output(io.StringIO(), get_size=_FakeSize().get_size)

    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setenv("WT_SESSION", "")
    monkeypatch.setattr(defaults, "create_output", _fake_create_output)
    fake = Answers(answers)
    monkeypatch.setattr(questionary.Question, "ask", fake)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_journal_interact_creates_all_entities(monkeypatch) -> None:
    """Full session creates JournalEntry, SleepRecord, TimeBlock, and RoutineLog."""
    answers = [
        "06:00", "23:00", "7",             # sleep
        "Morning Focus", "05:00 - 08:00",   # block
        "",                                    # no more blocks
        "4", "8", "7", "3", "4",           # pomodoros + metrics
        "test note",                           # note
    ]
    _patch_questionary_ask(monkeypatch, answers)

    result = runner.invoke(app, ["journal", "interact", "--date", "2026-08-01"])

    assert result.exit_code == 0, f"Exit code: {result.exit_code}\nOutput:\n{result.output}"

    journals = cli_state.journals.list()
    assert len(journals) == 1
    j = journals[0]
    assert j.date.year == 2026
    assert j.pomodoros_completos == 4
    assert j.energia_nivel == 8
    assert j.foco_nivel == 7
    assert j.humor_morning == 3
    assert j.humor_evening == 4
    assert "test note" in j.entry_text

    sleep = cli_state.sleep_records.list()
    assert len(sleep) == 1
    assert sleep[0].quality_score == 7

    blocks = cli_state.time_blocks.list()
    assert len(blocks) == 1
    assert blocks[0].label == "Morning Focus"

    rlogs = cli_state.routine_logs.list()
    assert len(rlogs) == 1


def test_journal_interact_with_minimal_input(monkeypatch) -> None:
    """Minimal session (all defaults) still creates a JournalEntry."""
    answers = [
        "06:00", "23:00", "7",  # sleep (defaults)
        "",                         # no blocks
        "0",                        # pomodoros
        "7", "7", "4", "3",      # metrics
        "",                         # no note
    ]
    _patch_questionary_ask(monkeypatch, answers)

    result = runner.invoke(app, ["journal", "interact"])

    assert result.exit_code == 0, f"Exit code: {result.exit_code}\nOutput:\n{result.output}"
    journals = cli_state.journals.list()
    assert len(journals) == 1


def test_journal_interact_json_flag_returns_valid_payload(monkeypatch) -> None:
    """``journal interact --json`` returns parseable JSON with expected keys."""
    answers = ["06:00", "23:00", "7", "", "2", "5", "6", "3", "3", "A short note."]
    _patch_questionary_ask(monkeypatch, answers)

    result = runner.invoke(app, ["journal", "interact", "--json"])

    assert result.exit_code == 0, f"Exit code: {result.exit_code}\nOutput:\n{result.output}"
    data = _parse_json_output(result.output)

    assert "journal_id" in data
    assert "date" in data
    assert data["pomodoros"] == 2
    assert data["energia"] == 5
    assert data["foco"] == 6
    assert data["humor_morning"] == 3
    assert data["humor_evening"] == 3


def test_journal_interact_invalid_date_exits_with_error(monkeypatch) -> None:
    """``journal interact --date invalid`` exits non-zero, no traceback."""
    answers = ["06:00", "23:00", "7", "", "0", "7", "7", "4", "3", ""]
    _patch_questionary_ask(monkeypatch, answers)

    result = runner.invoke(app, ["journal", "interact", "--date", "not-a-date"])

    assert result.exit_code != 0
    assert "Traceback (most recent call last)" not in result.output


def test_journal_interact_empty_answers_do_not_crash(monkeypatch) -> None:
    """Empty-string answers at all prompts produce no traceback."""
    # Empty strings for everything — nothing validates, nothing gets created,
    # but the command should exit cleanly
    answers = ["", "", "", "", "", "", "", "", "", ""]
    _patch_questionary_ask(monkeypatch, answers)

    result = runner.invoke(app, ["journal", "interact"])

    assert "Traceback (most recent call last)" not in result.output


def test_journal_create_still_works() -> None:
    """``journal create`` is unaffected by the interact command."""
    result = runner.invoke(app, ["journal", "create", "--text", "Quick entry"])

    assert result.exit_code == 0, f"Output:\n{result.output}"
    journals = cli_state.journals.list()
    assert len(journals) == 1
    assert "Quick entry" in journals[0].entry_text


def test_journal_list_still_works() -> None:
    """``journal list`` is unaffected by the interact command."""
    runner.invoke(app, ["journal", "create", "--text", "Listed entry"])

    result = runner.invoke(app, ["journal", "list"])

    assert result.exit_code == 0
    journals = cli_state.journals.list()
    assert len(journals) == 1
    assert "Listed entry" in journals[0].entry_text
