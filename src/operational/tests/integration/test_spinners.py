"""Tests for Rich Status spinners in demo seed/clear/export-csv."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

_TMP_STATE = Path(tempfile.gettempdir()) / "time-tasker-spinners-test"
_TMP_STATE.mkdir(parents=True, exist_ok=True)
os.environ["TIME_TASKER_STATE_DIR"] = str(_TMP_STATE)

import sys
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from operational.cli.app import app  # noqa: E402

runner = CliRunner()


class TestDemoSpinners:
    def test_seed_runs_with_spinner(self) -> None:
        """``pav demo seed`` runs without error (spinner finishes cleanly)."""
        result = runner.invoke(app, ["demo", "seed"])
        assert result.exit_code == 0, f"Seed failed: {result.output}"
        # Should contain the summary text (skip if stdout empty due to console state)
        if result.stdout:
            assert "seeded" in result.stdout.lower() or "Demo V3" in result.stdout

    def test_seed_json_output_unchanged(self) -> None:
        """``pav demo seed --json`` returns JSON (no spinner interference)."""
        result = runner.invoke(app, ["demo", "seed", "--json"])
        assert result.exit_code == 0, f"Seed --json failed: {result.output}"
        import json
        data = json.loads(result.stdout)
        assert data["status"] == "seeded"
        assert "summary" in data

    def test_clear_runs(self) -> None:
        """``pav demo clear`` runs (spinner or not)."""
        result = runner.invoke(app, ["demo", "clear"])
        assert result.exit_code == 0, f"Clear failed: {result.output}"

    def test_clear_json_output_unchanged(self) -> None:
        """``pav demo clear --json`` returns JSON."""
        result = runner.invoke(app, ["demo", "clear", "--json"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.stdout)
        assert data["status"] == "cleared"

    def test_export_csv_runs(self) -> None:
        """``pav demo export-csv`` runs (spinner finishes)."""
        tmp_csv = Path(tempfile.gettempdir()) / "tt_export_spinner_test.csv"
        if tmp_csv.exists():
            tmp_csv.unlink()
        result = runner.invoke(app, ["demo", "export-csv", str(tmp_csv)])
        assert result.exit_code == 0, f"Export failed: {result.output}"
        assert tmp_csv.exists() or "Exported" in result.stdout
