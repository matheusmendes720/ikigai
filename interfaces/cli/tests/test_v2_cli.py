"""Tests for interfaces/cli/v2.py — IKIGAI v2 sub-app.

Uses click.testing.CliRunner to test the Typer app directly, bypassing
the interfaces.cli.__init__ import chain (which requires full PYTHONPATH
setup involving src/contracts and src/mesh).

Four tests:
  test_v2_cycle_invokes_graph    — cycle command calls make_v2_graph
  test_v2_score_calls_mcp       — score command calls _handle_ikigai_score
  test_v2_regime_calls_mcp      — regime command calls _handle_ikigai_regime
  test_v2_cli_help_renders       — v2 --help prints all 3 commands without error
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ensure repo root + src/ are on sys.path so `from src.ikigai.src...` resolves.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src"
for p in (_SRC_ROOT, _REPO_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


# ---------------------------------------------------------------------------
# Import v2 app directly (bypasses interfaces.cli.__init__)
# ---------------------------------------------------------------------------

from interfaces.cli import v2  # noqa: E402


# ---------------------------------------------------------------------------
# cycle command
# ---------------------------------------------------------------------------


def test_v2_cycle_invokes_graph(monkeypatch) -> None:
    """cycle command should call make_v2_graph and invoke the compiled graph."""
    mock_compiled = MagicMock()
    mock_compiled._ikigai_entry_point = "observe"
    mock_compiled.invoke.return_value = {
        "observe": {"done": True},
        "commit_summary": "tasks written",
        "error_type": None,
    }

    mock_make = MagicMock(return_value=mock_compiled)
    monkeypatch.setattr(v2, "_load_handlers", lambda: (None, None, mock_make))

    # Use CliRunner to invoke the command
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["cycle"])

    assert result.exit_code == 0, f"cycle exited with {result.exit_code}: {result.output}"
    mock_make.assert_called_once()
    mock_compiled.invoke.assert_called_once_with({})


def test_v2_cycle_json_output(monkeypatch) -> None:
    """cycle --json should return a dict with graph metadata and no error_type."""
    mock_compiled = MagicMock()
    mock_compiled._ikigai_entry_point = "observe"
    mock_compiled.invoke.return_value = {"error_type": None, "nodes": ["observe"]}

    mock_make = MagicMock(return_value=mock_compiled)
    monkeypatch.setattr(v2, "_load_handlers", lambda: (None, None, mock_make))

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["cycle", "--json"])

    assert result.exit_code == 0
    output_data = json.loads(result.output)
    assert "graph" in output_data or "ikigai_maintainer_v2" in str(output_data)


# ---------------------------------------------------------------------------
# score command
# ---------------------------------------------------------------------------


def test_v2_score_calls_mcp(monkeypatch) -> None:
    """score command should call _handle_ikigai_score with the date string."""
    mock_handler = MagicMock(
        return_value='{"date": "2026-09-03", "vector_scores": {"passion": "0.8"}}'
    )
    monkeypatch.setattr(v2, "_load_handlers", lambda: (mock_handler, MagicMock(), None))

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["score", "2026-09-03"])

    assert result.exit_code == 0, f"score exited with {result.exit_code}: {result.output}"
    mock_handler.assert_called_once_with({"date": "2026-09-03"})


def test_v2_score_no_date_uses_today(monkeypatch) -> None:
    """When no date_arg is given, score defaults to today."""
    from datetime import date as _date

    today = _date.today().isoformat()
    mock_handler = MagicMock(return_value=f'{{"date": "{today}", "vector_scores": {{}}}}')
    monkeypatch.setattr(v2, "_load_handlers", lambda: (mock_handler, MagicMock(), None))

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["score"])

    assert result.exit_code == 0
    call_args = mock_handler.call_args[0][0]
    assert "date" in call_args
    assert call_args["date"] == today


def test_v2_score_error_when_no_cycle_state(monkeypatch) -> None:
    """When cycle_state is missing, score should print a hint instead of crashing."""
    mock_handler = MagicMock(
        return_value='{"error": "no cycle_state", "hint": "PAV writes cycle_state.md"}'
    )
    monkeypatch.setattr(v2, "_load_handlers", lambda: (mock_handler, MagicMock(), None))

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["score", "2026-01-01"])

    # Should not raise — exits 0 and shows hint
    assert result.exit_code == 0
    assert "cycle_state" in result.output.lower() or "pav" in result.output.lower()


# ---------------------------------------------------------------------------
# regime command
# ---------------------------------------------------------------------------


def test_v2_regime_calls_mcp(monkeypatch) -> None:
    """regime command should call _handle_ikigai_regime with the date string."""
    mock_handler = MagicMock(
        return_value='{"date": "2026-09-03", "regime_state": "PUSH", "days_in_regime": 3}'
    )
    monkeypatch.setattr(v2, "_load_handlers", lambda: (MagicMock(), mock_handler, None))

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["regime", "2026-09-03"])

    assert result.exit_code == 0, f"regime exited with {result.exit_code}: {result.output}"
    mock_handler.assert_called_once_with({"date": "2026-09-03"})


def test_v2_regime_error_when_no_regime_state(monkeypatch) -> None:
    """When regime_state is missing, regime should print a hint instead of crashing."""
    mock_handler = MagicMock(
        return_value='{"error": "no regime_state", "hint": "PAV writes regime_state.md"}'
    )
    monkeypatch.setattr(v2, "_load_handlers", lambda: (MagicMock(), mock_handler, None))

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["regime", "2026-01-01"])

    assert result.exit_code == 0
    assert "regime_state" in result.output.lower() or "pav" in result.output.lower()


# ---------------------------------------------------------------------------
# help rendering
# ---------------------------------------------------------------------------


def test_v2_cli_help_renders() -> None:
    """v2 --help must render all 3 commands without raising."""
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["--help"])

    assert result.exit_code == 0, f"--help exited with {result.exit_code}: {result.output}"
    assert "cycle" in result.output
    assert "score" in result.output
    assert "regime" in result.output


def test_v2_app_imports_cleanly() -> None:
    """v2 module must load without errors (repo root + src on sys.path)."""
    assert hasattr(v2, "app")
    assert hasattr(v2, "v2_app")
    assert v2.app is v2.v2_app
