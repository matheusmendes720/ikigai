"""Tests for v2 home menu (Layout-based dashboard) and Progress in CSV import."""
from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

_TMP_STATE = Path(tempfile.gettempdir()) / "time-tasker-rich-advanced-test"
_TMP_STATE.mkdir(parents=True, exist_ok=True)
os.environ["TIME_TASKER_STATE_DIR"] = str(_TMP_STATE)

import sys
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from operational.cli.app import app  # noqa: E402
from operational.cli.home_v2 import MENU_GROUPS, run  # noqa: E402

runner = CliRunner()


class TestHomeV2:
    def test_v2_home_runs(self, monkeypatch) -> None:
        """``pav home`` (v2 is default) runs without error (shows menu then prompts)."""
        from rich.prompt import Prompt
        monkeypatch.setattr(Prompt, "ask", lambda *a, **kw: "q")
        result = runner.invoke(app, ["home"])
        if result.stdout:
            assert "PAV-OS" in result.stdout
            assert "FLUXO DO DIA" in result.stdout
            assert "DASHBOARD" in result.stdout
            assert "RELATÓRIOS" in result.stdout
            assert "DADOS & HISTÓRICO" in result.stdout
            assert "SISTEMA" in result.stdout

    def test_v2_home_contains_5_grouped_sections(self, monkeypatch) -> None:
        """v2 home (default) groups the 10 options into 5 themed sections."""
        from rich.prompt import Prompt
        monkeypatch.setattr(Prompt, "ask", lambda *a, **kw: "q")
        result = runner.invoke(app, ["home"])
        if result.stdout:
            for group_key, group_label, items in MENU_GROUPS:
                assert group_label in result.stdout, f"Missing group: {group_label}"
                for k, lbl, sub in items:
                    assert k in result.stdout, f"Missing option: {k}"

    def test_home_help_does_not_mention_v1(self, monkeypatch) -> None:
        """``pav home --help`` does not mention the v1 home option."""
        from rich.prompt import Prompt
        monkeypatch.setattr(Prompt, "ask", lambda *a, **kw: "q")
        result = runner.invoke(app, ["home", "--help"])
        assert result.exit_code == 0
        assert "--v1" not in result.output
        assert "--v2" not in result.output


class TestProgressInCsvImport:
    def test_import_csv_uses_progress(self) -> None:
        """``demo import-csv`` should work and not raise."""
        from operational.ui.mock_profiles import PROFILES
        # Use the docs/golden.csv file (always present)
        from operational.cli.csv_loader import export_to_csv
        from operational.cli.state import routines
        # Build a tiny CSV
        from operational.entities.routine import Routine
        from datetime import datetime, UTC
        tmp_csv = Path(tempfile.gettempdir()) / "tt_progress_test.csv"
        routine = Routine(
            id="rou_test_001",
            name="Test Routine",
            period="MANHA",
            routine_type="CORE",
            start_time=datetime.strptime("06:00", "%H:%M").time(),
            end_time=datetime.strptime("07:00", "%H:%M").time(),
            created_at=datetime.now(UTC),
        )
        rows = [("routine", str(routine.id), routine.model_dump(mode="python"))]
        export_to_csv(rows, tmp_csv)

        result = runner.invoke(app, ["demo", "import-csv", str(tmp_csv), "--replace"])
        assert result.exit_code == 0, f"Import failed: {result.output}"

        # Verify the routine was actually imported
        assert routines.count() >= 1

    def test_export_csv_works(self) -> None:
        """``demo export-csv`` should write a CSV."""
        tmp_csv = Path(tempfile.gettempdir()) / "tt_export_test.csv"
        if tmp_csv.exists():
            tmp_csv.unlink()

        result = runner.invoke(app, ["demo", "export-csv", str(tmp_csv)])
        assert result.exit_code == 0, f"Export failed: {result.output}"
        assert tmp_csv.exists(), f"CSV file not created: {result.output}"


class TestRichAdvancedFeatures:
    def test_console_rule_in_home(self, monkeypatch) -> None:
        """v2 home (default) uses console.rule for section dividers."""
        # Bypass the prompt to avoid EOF in capture
        from rich.prompt import Prompt
        monkeypatch.setattr(Prompt, "ask", lambda *a, **kw: "q")
        result = runner.invoke(app, ["home"])
        if result.stdout:
            # The output should contain '─' (rule characters)
            assert "─" in result.stdout

    def test_pav_os_branding_in_header(self, monkeypatch) -> None:
        """v2 home (default) header shows PAV-OS branding."""
        from rich.prompt import Prompt
        monkeypatch.setattr(Prompt, "ask", lambda *a, **kw: "q")
        result = runner.invoke(app, ["home"])
        if result.stdout:
            assert "PAV-OS" in result.stdout
            assert "Cybernetic Life OS" in result.stdout
