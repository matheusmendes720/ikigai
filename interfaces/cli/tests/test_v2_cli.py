"""Tests for interfaces/cli/v2.py — IKIGAI v2 sub-app.

Uses click.testing.CliRunner to test the Typer app directly, bypassing
the interfaces.cli.__init__ import chain (which requires full PYTHONPATH
setup involving src/contracts and src/mesh).

Per W2.1 (Wave 2): v2 commands route to prompt-chain renderers (FAKE-LLM
stubs in test mode) with legacy MCP handlers as last-resort fallback when
the renderer returns llm_call_failed. The 5-tuple from _load_handlers is:
    (score_handler, regime_handler, render_score_passion,
     render_heuristics_regime, render_surface_pav)
The graph factory is loaded separately via _load_graph_factory().
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
    # W2.1: graph factory loaded via _load_graph_factory (separate from handlers)
    monkeypatch.setattr(v2, "_load_graph_factory", lambda: mock_make)

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
    monkeypatch.setattr(v2, "_load_graph_factory", lambda: mock_make)

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["cycle", "--json"])

    assert result.exit_code == 0
    output_data = json.loads(result.output)
    assert "graph" in output_data or "ikigai_maintainer_v2" in str(output_data)


# ---------------------------------------------------------------------------
# score command — routes to render_score_passion_observation prompt chain
# ---------------------------------------------------------------------------


def test_v2_score_calls_mcp(monkeypatch) -> None:
    """score command should call render_score_passion_observation with the date."""
    mock_renderer = MagicMock(
        return_value={"passion_score": 80, "rationale": "[mock for test]"}
    )
    # W2.1: 5-tuple (score_handler, regime_handler, render_score_passion, ...)
    monkeypatch.setattr(
        v2,
        "_load_handlers",
        lambda: (None, None, mock_renderer, MagicMock(), MagicMock()),
    )

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["score", "2026-09-03"])

    assert result.exit_code == 0, f"score exited with {result.exit_code}: {result.output}"
    mock_renderer.assert_called_once()
    call_state = mock_renderer.call_args[0][0]
    assert call_state["date"] == "2026-09-03"


def test_v2_score_no_date_uses_today(monkeypatch) -> None:
    """When no date_arg is given, score defaults to today."""
    from datetime import date as _date

    today = _date.today().isoformat()
    mock_renderer = MagicMock(return_value={"passion_score": 80})
    monkeypatch.setattr(
        v2,
        "_load_handlers",
        lambda: (None, None, mock_renderer, MagicMock(), MagicMock()),
    )

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["score"])

    assert result.exit_code == 0
    call_state = mock_renderer.call_args[0][0]
    assert "date" in call_state
    assert call_state["date"] == today


def test_v2_score_error_when_no_cycle_state(monkeypatch) -> None:
    """When renderer returns an error, score should fall back to MCP handler."""
    mock_renderer = MagicMock(
        return_value={"error": "llm_call_failed", "exception": "no API key"}
    )
    # When the renderer returns llm_call_failed, score falls back to MCP handler.
    # The MCP handler is mocked to return a JSON-string error response.
    mock_handler = MagicMock(
        return_value='{"error": "no cycle_state", "hint": "PAV writes cycle_state.md"}'
    )
    monkeypatch.setattr(
        v2,
        "_load_handlers",
        lambda: (mock_handler, None, mock_renderer, MagicMock(), MagicMock()),
    )

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["score", "2026-01-01"])

    # Should not raise — exits 0 and shows hint from fallback handler
    assert result.exit_code == 0
    assert "cycle_state" in result.output.lower() or "pav" in result.output.lower()


# ---------------------------------------------------------------------------
# regime command — routes to render_heuristics_regime_observation prompt chain
# ---------------------------------------------------------------------------


def test_v2_regime_calls_mcp(monkeypatch) -> None:
    """regime command should call render_heuristics_regime_observation with the date."""
    mock_renderer = MagicMock(
        return_value={"regime": "PUSH", "rationale": "[mock for test]"}
    )
    # W2.1: 5-tuple position 3 is render_heuristics_regime
    monkeypatch.setattr(
        v2,
        "_load_handlers",
        lambda: (None, None, MagicMock(), mock_renderer, MagicMock()),
    )

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["regime", "2026-09-03"])

    assert result.exit_code == 0, f"regime exited with {result.exit_code}: {result.output}"
    mock_renderer.assert_called_once()
    call_state = mock_renderer.call_args[0][0]
    assert call_state["date"] == "2026-09-03"


def test_v2_regime_error_when_no_regime_state(monkeypatch) -> None:
    """When renderer returns llm_call_failed, regime falls back to MCP handler."""
    mock_renderer = MagicMock(
        return_value={"error": "llm_call_failed", "exception": "no API key"}
    )
    mock_handler = MagicMock(
        return_value='{"error": "no regime_state", "hint": "PAV writes regime_state.md"}'
    )
    monkeypatch.setattr(
        v2,
        "_load_handlers",
        lambda: (None, mock_handler, MagicMock(), mock_renderer, MagicMock()),
    )

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["regime", "2026-01-01"])

    assert result.exit_code == 0
    assert "regime_state" in result.output.lower() or "pav" in result.output.lower()


# ---------------------------------------------------------------------------
# help rendering
# ---------------------------------------------------------------------------


def test_v2_cli_help_renders() -> None:
    """v2 --help must render all 4 commands (cycle/score/regime/suggest) without error."""
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["--help"])

    assert result.exit_code == 0, f"--help exited with {result.exit_code}: {result.output}"
    assert "cycle" in result.output
    assert "score" in result.output
    assert "regime" in result.output
    assert "suggest" in result.output  # W2.1 — new command


# ---------------------------------------------------------------------------
# W2.3 — per-skill commands (daily/weekly/monthly/quarterly)
# ---------------------------------------------------------------------------


def test_v2_cli_help_renders_all_eight_commands() -> None:
    """W2.3: v2 --help must render all 8 commands including 4 per-skill."""
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["--help"])

    assert result.exit_code == 0
    # Original 4
    assert "cycle" in result.output
    assert "score" in result.output
    assert "regime" in result.output
    assert "suggest" in result.output
    # W2.3 — 4 per-skill
    assert "daily" in result.output
    assert "weekly" in result.output
    assert "monthly" in result.output
    assert "quarterly" in result.output


def test_v2_daily_routes_to_suggest(monkeypatch) -> None:
    """daily command orchestrates ikigai-daily skill via invoke_skill() (W3.5)."""
    import os

    os.environ.setdefault("IKIGAI_FAKE_LLM", "1")

    # Mock invoke_skill — daily.md is surface-only, returns user_suggestions
    captured_skill = []
    def fake_invoke_skill(skill_name, entry_point_override=None):
        captured_skill.append(skill_name)
        return {
            "user_suggestions": ["[mock] test suggestion 1", "[mock] test suggestion 2"],
            "suggestions_language": "pt-BR",
        }
    monkeypatch.setattr(v2, "invoke_skill", fake_invoke_skill)

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["daily", "2026-09-04", "--json"])

    assert result.exit_code == 0, f"daily exited {result.exit_code}: {result.output}"
    output_data = json.loads(result.output)
    assert output_data["skill"] == "ikigai-daily"
    assert output_data["date"] == "2026-09-04"
    assert "surface" in output_data
    assert output_data["surface"]["suggestions"] == [
        "[mock] test suggestion 1",
        "[mock] test suggestion 2",
    ]
    assert output_data["surface"]["language"] == "pt-BR"
    assert captured_skill == ["ikigai-daily"], (
        f"daily MUST route through invoke_skill('ikigai-daily'); got {captured_skill}"
    )


def test_v2_weekly_routes_to_score_and_regime(monkeypatch) -> None:
    """weekly command routes through invoke_skill('ikigai-weekly') (W6.X item 2)."""
    mock_score = {"passion_score": 80, "graph": "ikigai_score_passion_observation", "date": "2026-09-04"}
    mock_regime = {"regime": "PUSH", "graph": "ikigai_heuristics_regime_observation", "date": "2026-09-04"}

    captured_skill = []
    def fake_invoke_skill(skill_name, entry_point_override=None):
        captured_skill.append(skill_name)
        return {"score": mock_score, "regime": mock_regime}
    monkeypatch.setattr(v2, "invoke_skill", fake_invoke_skill)

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["weekly", "2026-09-04", "--json"])

    assert result.exit_code == 0, f"weekly exited {result.exit_code}: {result.output}"
    output_data = json.loads(result.output)
    assert output_data["skill"] == "ikigai-weekly"
    assert output_data["score"] == mock_score
    assert output_data["regime"] == mock_regime
    assert captured_skill == ["ikigai-weekly"], (
        f"weekly MUST route through invoke_skill('ikigai-weekly'); got {captured_skill}"
    )


def test_v2_monthly_routes_to_cycle_dry_run_score_regime(monkeypatch) -> None:
    """monthly command routes through invoke_skill('ikigai-monthly') (W6.X item 2)."""
    mock_cycle = {"graph": "ikigai_maintainer_v2", "entry_point": "observe", "dry_run": True, "compiled": True}
    mock_score = {"passion_score": 75, "graph": "ikigai_score_passion_observation"}
    mock_regime = {"regime": "MAINTAIN", "graph": "ikigai_heuristics_regime_observation"}

    captured_skill = []
    def fake_invoke_skill(skill_name, entry_point_override=None):
        captured_skill.append(skill_name)
        return {"cycle": mock_cycle, "score": mock_score, "regime": mock_regime}
    monkeypatch.setattr(v2, "invoke_skill", fake_invoke_skill)

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["monthly", "2026-09-04", "--json"])

    assert result.exit_code == 0, f"monthly exited {result.exit_code}: {result.output}"
    output_data = json.loads(result.output)
    assert output_data["skill"] == "ikigai-monthly"
    assert output_data["cycle"] == mock_cycle
    assert output_data["score"] == mock_score
    assert output_data["regime"] == mock_regime
    assert captured_skill == ["ikigai-monthly"], (
        f"monthly MUST route through invoke_skill('ikigai-monthly'); got {captured_skill}"
    )


def test_v2_quarterly_routes_to_cycle_dry_run_score_regime(monkeypatch) -> None:
    """quarterly command routes through invoke_skill('ikigai-quarterly') (W6.X item 2)."""
    mock_cycle = {"graph": "ikigai_maintainer_v2", "entry_point": "observe", "dry_run": True, "compiled": True}
    mock_score = {"passion_score": 70, "graph": "ikigai_score_passion_observation"}
    mock_regime = {"regime": "RECOVER", "graph": "ikigai_heuristics_regime_observation"}

    captured_skill = []
    def fake_invoke_skill(skill_name, entry_point_override=None):
        captured_skill.append(skill_name)
        return {"cycle": mock_cycle, "score": mock_score, "regime": mock_regime}
    monkeypatch.setattr(v2, "invoke_skill", fake_invoke_skill)

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["quarterly", "2026-09-04", "--json"])

    assert result.exit_code == 0, f"quarterly exited {result.exit_code}: {result.output}"
    output_data = json.loads(result.output)
    assert output_data["skill"] == "ikigai-quarterly"
    assert output_data["cycle"] == mock_cycle
    assert output_data["score"] == mock_score
    assert output_data["regime"] == mock_regime
    assert captured_skill == ["ikigai-quarterly"], (
        f"quarterly MUST route through invoke_skill('ikigai-quarterly'); got {captured_skill}"
    )


def test_v2_daily_default_date_is_today(monkeypatch) -> None:
    """When no date given, daily defaults to today (date captured by Typer, not invoke_skill)."""
    from datetime import date as _date

    today = _date.today().isoformat()
    monkeypatch.setattr(
        v2,
        "invoke_skill",
        lambda skill_name, entry_point_override=None: {"user_suggestions": [], "suggestions_language": "pt-BR"},
    )

    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2.app, ["daily", "--json"])

    assert result.exit_code == 0, f"daily exited {result.exit_code}: {result.output}"
    output_data = json.loads(result.output)
    assert output_data["date"] == today, (
        f"daily should default to today ({today}); got {output_data.get('date')!r}"
    )


def test_v2_app_imports_cleanly() -> None:
    """v2 module must load without errors (repo root + src on sys.path)."""
    assert hasattr(v2, "app")
    assert hasattr(v2, "v2_app")
    assert v2.app is v2.v2_app
