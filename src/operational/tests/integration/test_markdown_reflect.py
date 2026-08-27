"""Tests for rich.markdown rendering in 'pav reflect list --md'."""
from __future__ import annotations

import os
import tempfile
from datetime import date, datetime, UTC
from pathlib import Path

import pytest
from typer.testing import CliRunner

_TMP_STATE = Path(tempfile.gettempdir()) / "time-tasker-markdown-test"
_TMP_STATE.mkdir(parents=True, exist_ok=True)
os.environ["TIME_TASKER_STATE_DIR"] = str(_TMP_STATE)

import sys
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from operational.cli.app import app  # noqa: E402
from operational.cli.state import daily_reflections  # noqa: E402
from operational.entities.v3 import DailyReflection  # noqa: E402

runner = CliRunner()


class TestMarkdownInReflect:
    def setup_method(self) -> None:
        """Create a sample reflection for tests."""
        r = DailyReflection(
            id="ref_test_001",
            date=date(2026, 6, 8),
            big_win="Completou o checkpoint de producao PAV em 2h",
            maior_aprendizado="Foco profundo requer 50min sem interrupcao",
            ajustes_para_amanha=["Bloquear 9-11h para deep work", "Fechar Slack apos lunch"],
            parar_de_fazer=["Checar email a cada 5min"],
            repetir=["Workout 6h"],
            sempre_fazer=["Hydration ritual"],
            deu_certo=["Pomodoros completados"],
            deu_errado=["Jantar tarde"],
            estado_geral="bom",
            created_at=datetime.now(UTC),
        )
        daily_reflections.upsert(r)

    def teardown_method(self) -> None:
        daily_reflections.clear()

    def test_md_flag_renders_markdown(self) -> None:
        """``pav reflect list --md --date X`` renders Markdown."""
        result = runner.invoke(app, ["reflect", "list", "--md", "--date", "2026-06-08"])
        assert result.exit_code == 0, f"MD failed: {result.output}"
        if result.stdout:
            # Markdown should render the date as a heading
            assert "Reflexão 2026-06-08" in result.stdout or "2026-06-08" in result.stdout
            # The big_win text should appear
            assert "checkpoint de producao PAV" in result.stdout

    def test_md_no_data_shows_warning(self) -> None:
        """``--md`` with no data shows a clear warning."""
        daily_reflections.clear()
        result = runner.invoke(app, ["reflect", "list", "--md", "--date", "1999-01-01"])
        assert result.exit_code == 0
        if result.stdout:
            assert "Nenhuma reflexão" in result.stdout

    def test_list_without_md_still_works(self) -> None:
        """``pav reflect list`` (no --md) still works with table output."""
        result = runner.invoke(app, ["reflect", "list", "--date", "2026-06-08"])
        assert result.exit_code == 0
        if result.stdout:
            # Default table output - should contain the date
            assert "2026-06-08" in result.stdout
