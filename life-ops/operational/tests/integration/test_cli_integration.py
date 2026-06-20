"""CLI integration tests — exercise the Typer app via CliRunner.

Focus areas:
  * Happy-path command invocation
  * Error handling on bad inputs (no raw traceback leaks)
  * --json output shape validation
  * monkeypatch on repos for canned data
  * Domain exception hierarchy
  * Validator functions
  * error_panel_v2 UI component

All tests use :class:`typer.testing.CliRunner` and run in-process
(``catch_exceptions=True`` is the default). State is isolated per-test
via the autouse ``_isolated_state`` fixture in ``conftest.py``.
"""
from __future__ import annotations

import json
from datetime import date, time
from types import SimpleNamespace
from typing import Any

import pytest
from rich.panel import Panel
from typer.testing import CliRunner

from operational.cli import state as cli_state
from operational.cli.app import app
from operational.core.exceptions import (
    DataInvalidaError,
    DomainError,
    FaltaDadosError,
    LimitePomodoroExcedidoError,
    RepositorioVazioError,
    ValorForaRangeError,
)
from operational.cli.services import (
    parse_iso_date,
    validate_pomodoro_count,
    validate_required_fields,
)
from operational.ui.components_v2 import error_panel_v2


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

runner = CliRunner()

ESC = "\x1b["  # ANSI escape introducer


# ---------------------------------------------------------------------------
# A. Happy paths
# ---------------------------------------------------------------------------


def test_app_help_runs() -> None:
    """``--help`` exits 0 and surfaces the app description."""
    # Act
    result = runner.invoke(app, ["--help"])

    # Assert
    assert result.exit_code == 0
    assert "PAV-OS" in result.output


def test_report_help_shows_subcommands() -> None:
    """``report --help`` lists daily + weekly subcommands."""
    # Act
    result = runner.invoke(app, ["report", "--help"])

    # Assert
    assert result.exit_code == 0
    assert "daily" in result.output
    assert "weekly" in result.output


def test_metric_sleep_creates_record() -> None:
    """``metric sleep`` writes a SleepRecord to the repo."""
    # Act
    result = runner.invoke(app, [
        "metric", "sleep",
        "-q", "8",
        "-bh", "22",
        "-bm", "30",
        "-wh", "6",
        "-wm", "0",
    ])

    # Assert — command succeeded and the record was persisted
    assert result.exit_code == 0
    records = cli_state.sleep_records.list()
    assert len(records) == 1
    assert records[0].quality_score == 8


def test_state_show_runs_without_crash() -> None:
    """``state show`` renders the dashboard even with zero data."""
    # Act
    result = runner.invoke(app, ["state", "show"])

    # Assert
    assert result.exit_code == 0
    assert len(result.output) > 0
    assert "STATE" in result.output


# ---------------------------------------------------------------------------
# B. Error handling — bad inputs
# ---------------------------------------------------------------------------


def test_metric_sleep_with_invalid_date_does_not_crash() -> None:
    """``metric sleep --date not-a-date`` fails gracefully, no raw traceback."""
    # Act
    result = runner.invoke(app, [
        "metric", "sleep",
        "--date", "not-a-date",
        "--quality", "8",
    ])

    # Assert — command failed but did not leak a Python traceback to stdout
    assert result.exit_code != 0
    assert "Traceback (most recent call last)" not in result.output


def test_report_daily_with_empty_data_does_not_crash() -> None:
    """``report daily --date 1999-01-01`` renders without crashing on empty data."""
    # Act
    result = runner.invoke(app, ["report", "daily", "--date", "1999-01-01"])

    # Assert
    assert result.exit_code in (0, 1)
    assert len(result.output) > 0


def test_journal_list_handles_empty_repo() -> None:
    """``journal list`` on empty repo prints the empty-state warning."""
    # Act
    result = runner.invoke(app, ["journal", "list"])

    # Assert
    assert result.exit_code == 0
    assert "Nenhuma" in result.output


# ---------------------------------------------------------------------------
# C. JSON output
# ---------------------------------------------------------------------------


def test_report_daily_json_returns_valid_json() -> None:
    """``report daily --json`` returns parseable JSON with 'date' key."""
    # Act
    result = runner.invoke(app, ["report", "daily", "--json"])

    # Assert
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "date" in data
    assert "tipo_dia" in data


def test_state_show_json_returns_valid_json() -> None:
    """``state show --json`` returns parseable JSON with 'period_now' key."""
    # Act
    result = runner.invoke(app, ["state", "show", "--json"])

    # Assert
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "date" in data
    assert "period_now" in data


# ---------------------------------------------------------------------------
# D. Usage errors
# ---------------------------------------------------------------------------


def test_routine_create_missing_args_prints_usage() -> None:
    """``routine create`` without required arg prints Usage and exits non-zero."""
    # Act
    result = runner.invoke(app, ["routine", "create"])

    # Assert
    assert result.exit_code != 0
    assert "Usage:" in result.output


# ---------------------------------------------------------------------------
# E. End-to-end workflow
# ---------------------------------------------------------------------------


def test_full_daily_flow_simulation() -> None:
    """Simulate ``metric sleep`` → ``journal create`` → ``report daily`` in one test."""
    # Act
    r1 = runner.invoke(app, ["metric", "sleep", "-q", "8", "-bh", "22", "-bm", "30", "-wh", "6", "-wm", "0"])
    r2 = runner.invoke(app, ["journal", "create", "--text", "Integration test entry"])
    r3 = runner.invoke(app, ["report", "daily"])

    # Assert — no command crashed
    assert r1.exit_code == 0
    assert r2.exit_code == 0
    assert r3.exit_code in (0, 1)
    # And the data was actually persisted
    assert len(cli_state.sleep_records.list()) == 1
    assert len(cli_state.journals.list()) == 1


# ---------------------------------------------------------------------------
# F. ANSI / Rich markup hygiene
# ---------------------------------------------------------------------------


def test_output_has_no_raw_ansi_codes() -> None:
    """Captured output (no TTY) must not leak raw ANSI or Rich markup."""
    # Act
    result = runner.invoke(app, ["state", "show"])

    # Assert — no raw ANSI escapes, no literal color codes, no leaked tags
    assert ESC not in result.output
    assert "[36m" not in result.output
    assert "[bold" not in result.output
    assert "[/bold" not in result.output


# ---------------------------------------------------------------------------
# G. Domain exception hierarchy
# ---------------------------------------------------------------------------


def test_domain_error_inherits_from_exception() -> None:
    """Every domain error subclasses ``DomainError`` → ``Exception``."""
    # Assert — full hierarchy chain
    assert issubclass(DomainError, Exception)
    assert issubclass(FaltaDadosError, DomainError)
    assert issubclass(DataInvalidaError, DomainError)
    assert issubclass(ValorForaRangeError, DomainError)
    assert issubclass(LimitePomodoroExcedidoError, DomainError)
    assert issubclass(RepositorioVazioError, DomainError)


# ---------------------------------------------------------------------------
# H. Validators
# ---------------------------------------------------------------------------


def test_parse_iso_date_happy_and_sad() -> None:
    """``parse_iso_date`` accepts ``YYYY-MM-DD`` and rejects everything else."""
    # Happy
    assert parse_iso_date("2026-06-07") == date(2026, 6, 7)

    # Sad — Brazilian format
    with pytest.raises(DataInvalidaError):
        parse_iso_date("01/06/2026")
    # Sad — garbage
    with pytest.raises(DataInvalidaError):
        parse_iso_date("not-a-date")


def test_validate_pomodoro_count_raises() -> None:
    """``validate_pomodoro_count`` raises domain errors on out-of-range input."""
    # Negative
    with pytest.raises(ValorForaRangeError):
        validate_pomodoro_count(-1)
    # Excessive
    with pytest.raises(LimitePomodoroExcedidoError):
        validate_pomodoro_count(100)
    # Boundary — exactly 0 and exactly max are OK
    assert validate_pomodoro_count(0) == 0
    assert validate_pomodoro_count(24) == 24


def test_validate_required_fields_raises() -> None:
    """``validate_required_fields`` raises ``FaltaDadosError`` on missing keys."""
    # Sad
    with pytest.raises(FaltaDadosError):
        validate_required_fields({}, ["data", "foco"])

    # Happy — does not raise
    validate_required_fields({"data": "x", "foco": 5}, ["data", "foco"])


# ---------------------------------------------------------------------------
# I. monkeypatch on repos (canned-data pattern)
# ---------------------------------------------------------------------------


def test_state_show_json_with_mocked_sleep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``monkeypatch`` ``sleep_records.list`` to return a fake record."""
    # Arrange — a duck-typed sleep record (state_cmd only reads these fields)
    # Use date.today() so the record is found when state show runs without --date
    today = date.today()
    fake = SimpleNamespace(
        date=today,
        bedtime=time(22, 30),
        wake_time=time(6, 0),
        quality_score=9,
        duration_hours=7.5,
    )
    monkeypatch.setattr(
        cli_state.sleep_records,
        "list",
        lambda *_a: [fake],  # type: ignore[arg-type]
    )

    # Act
    result = runner.invoke(app, ["state", "show", "--json"])

    # Assert — the mocked data flows through to the JSON payload
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["sleep"] is not None
    assert data["sleep"]["quality"] == 9
    assert data["sleep"]["duration_hours"] == 7.5


# ---------------------------------------------------------------------------
# J. error_panel_v2 UI component
# ---------------------------------------------------------------------------


def test_error_panel_v2_returns_rich_panel() -> None:
    """``error_panel_v2`` is a pure factory — returns a ``rich.panel.Panel``."""
    # Act
    panel = error_panel_v2(
        "Algo deu errado",
        context="pav test --help",
        expected="valid args",
        suggestion="pav test --json",
    )

    # Assert
    assert isinstance(panel, Panel)
    rendered = str(panel.renderable)
    assert "Algo deu errado" in rendered
    assert "pav test --help" in rendered
    assert "pav test --json" in rendered


def test_error_panel_v2_contains_erro_title() -> None:
    """``error_panel_v2`` always renders the ERRO title bar."""
    # Act
    panel = error_panel_v2("Be careful")

    # Assert
    assert isinstance(panel, Panel)
    # The title contains the 'ERRO' marker
    title_str = str(panel.title) if panel.title else ""
    assert "ERRO" in title_str
