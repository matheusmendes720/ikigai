"""Integration tests for the doctor command."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

_TMP_STATE = Path(tempfile.gettempdir()) / "time-tasker-doctor-test-state"
_TMP_STATE.mkdir(parents=True, exist_ok=True)
os.environ["TIME_TASKER_STATE_DIR"] = str(_TMP_STATE)

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from operational.cli.app import app  # noqa: E402
from operational.cli.commands.doctor_cmd import (  # noqa: E402
    _check_console,
    _check_constants,
    _check_datasets,
    _check_files_sanity,
    _check_packages,
    _check_python,
    _check_state_dir,
)

runner = CliRunner()


class TestIndividualChecks:
    def test_python(self) -> None:
        r = _check_python()
        assert r["ok"] is True
        assert "version" in r

    def test_packages(self) -> None:
        r = _check_packages()
        assert r["ok"] is True
        assert "typer" in r["packages"]
        assert "rich" in r["packages"]
        assert "pydantic" in r["packages"]

    def test_state_dir_exists(self) -> None:
        r = _check_state_dir()
        assert r["exists"] is True
        assert r["writable"] is True
        assert "routines.json" in r["files"]

    def test_datasets_active_production_by_default(self, monkeypatch) -> None:
        monkeypatch.delenv("TIME_TASKER_DATASET", raising=False)
        r = _check_datasets()
        assert r["active"] == "production"
        assert "synthetic" in r["available"]

    def test_datasets_active_synthetic(self, monkeypatch) -> None:
        monkeypatch.setenv("TIME_TASKER_DATASET", "synthetic")
        r = _check_datasets()
        assert r["active"] == "synthetic"

    def test_constants(self) -> None:
        r = _check_constants()
        assert r["ok"] is True
        assert r["constants"]["POMODORO_WORK_MIN"] == 50
        assert r["constants"]["LAMBDA_LEARNING_DEFAULT"] == 0.093

    def test_console(self) -> None:
        r = _check_console()
        assert "is_captured" in r
        assert "encoding" in r

    def test_files_sanity_clean(self) -> None:
        r = _check_files_sanity()
        assert r["ok"] is True
        assert r["issues"] == []


class TestDoctorCommand:
    def test_doctor_json(self) -> None:
        result = runner.invoke(app, ["doctor", "doctor", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "checks" in data
        assert "python" in data["checks"]
        assert "state_dir" in data["checks"]
        assert "constants" in data["checks"]
        assert "overall_ok" in data

    def test_doctor_human(self) -> None:
        result = runner.invoke(app, ["doctor", "doctor"])
        assert result.exit_code == 0
        assert "DOCTOR" in result.stdout or "doctor" in result.stdout.lower()


class TestCorruptedState:
    def test_corrupted_json_detected(self, tmp_path, monkeypatch) -> None:
        state_dir = tmp_path / "corrupt-state"
        state_dir.mkdir()
        bad_file = state_dir / "routines.json"
        bad_file.write_text("{ invalid json !!!", encoding="utf-8")
        monkeypatch.setenv("TIME_TASKER_STATE_DIR", str(state_dir))
        r = _check_state_dir()
        assert r["files"]["routines.json"]["parseable"] is False
        assert "error" in r["files"]["routines.json"]
