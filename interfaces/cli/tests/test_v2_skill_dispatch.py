"""Tests for v2 skill dispatch (daily / weekly CLI commands).

Uses `typer.testing.CliRunner` (in-process, fast — NOT subprocess).
Mocks the MCP bridge with FakeMcpServer to avoid needing a live gateway.

Dual-module identity: we patch BOTH `src.ikigai.src.agents.v2.mcp_bridge`
(bare module import in _v2_skills.py) per the invariant bug class.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure `life/` is on sys.path for `from src.X` and `from interfaces.cli.X`.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src"
for _p in (_SRC_ROOT, _REPO_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from typer.testing import CliRunner

# Import after sys.path setup
from interfaces.cli.v2 import app as v2_app  # noqa: E402

# FakeMcpServer lives in the v2 agents test fixtures
from src.ikigai.src.agents.v2.tests.fixtures.fake_mcp_server import (  # noqa: E402
    FakeMcpServer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_server() -> FakeMcpServer:
    """Return a FakeMcpServer pre-loaded with canned responses for daily/weekly."""
    server = FakeMcpServer()
    # observe node canned responses
    server.canned_response(
        "ikigai_observe_pav_state", date="2026-09-08", pav_state={"regime": "MAINTAIN"}
    )
    # surface_intentions node canned response (daily skill)
    server.canned_response(
        "ikigai_heuristics",
        context={"regime": "MAINTAIN"},
        heuristics={"suggestion": "Revisar tasks pendentes"},
    )
    # weekly skill responses
    server.canned_response(
        "ikigai_score_vectors", vectors=[0.7, 0.6, 0.7, 0.6, 0.7], scores={"passion": 0.7}
    )
    server.canned_response(
        "ikigai_balance", load=4.0, verdict={"verdict": "OK", "adjustment": 0.0}
    )
    server.canned_response("ikigai_decompose", task_id="t001", subtasks=[])
    server.canned_response("ikigai_plan", cycle_id="ikigai-weekly-2026-09-08", plan={})
    server.canned_response(
        "ikigai_reflect", cycle_id="ikigai-weekly-2026-09-08", review={}
    )
    server.canned_response(
        "ikigai_tag_and_persist", ueid="test:weekly:001:001", persisted=True
    )
    server.canned_response(
        "ikigai_commit_summary", cycle_id="ikigai-weekly-2026-09-08", summary="test-summary"
    )
    return server


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_server():
    """Return a FakeMcpServer pre-loaded with canned responses."""
    return _make_fake_server()


@pytest.fixture
def run_v2_cli():
    """Return a CliRunner.invoke helper bound to the v2 app."""
    runner = CliRunner()

    def _run(args: list[str]):
        return runner.invoke(v2_app, args)

    return _run


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_daily_invokes_surface_intentions(monkeypatch, fake_server, run_v2_cli):
    """`v2 daily --json` calls make_v2_graph(entry_point='surface_intentions')."""
    # Patch the dotted-prefix module path that _v2_skills.py imports from
    # (dual-module identity: bare `mcp_bridge` vs `src.ikigai.src.agents.v2.mcp_bridge`)
    import src.ikigai.src.agents.v2.mcp_bridge as _bridge_mod

    monkeypatch.setattr(_bridge_mod, "_server", fake_server)

    result = run_v2_cli(["daily", "--date", "2026-09-08", "--json"])

    assert result.exit_code == 0, f"exit {result.exit_code}: {result.output}"
    payload = json.loads(result.output)

    # Verify skill metadata
    assert payload.get("skill") == "ikigai-daily"
    assert payload.get("date") == "2026-09-08"

    # surface_intentions entry point — graph should return that key
    assert "surface_intentions" in payload

    # Verify the surface_intentions result is well-formed
    surface = payload["surface_intentions"]
    assert surface.get("cycle_id") == "ikigai-daily-2026-09-08"
    assert surface.get("iteration") == 0


def test_weekly_invokes_observe(monkeypatch, fake_server, run_v2_cli):
    """`v2 weekly --json` calls make_v2_graph(entry_point='observe')."""
    import src.ikigai.src.agents.v2.mcp_bridge as _bridge_mod

    monkeypatch.setattr(_bridge_mod, "_server", fake_server)

    result = run_v2_cli(["weekly", "--date", "2026-09-08", "--json"])

    assert result.exit_code == 0, f"exit {result.exit_code}: {result.output}"
    payload = json.loads(result.output)

    # Verify skill metadata
    assert payload.get("skill") == "ikigai-weekly"
    assert payload.get("date") == "2026-09-08"

    # Full pipeline starts at observe
    assert "observe" in payload


def test_daily_non_json_output(monkeypatch, fake_server, run_v2_cli):
    """`v2 daily` (no --json) prints formatted suggestions to stdout."""
    import src.ikigai.src.agents.v2.mcp_bridge as _bridge_mod

    monkeypatch.setattr(_bridge_mod, "_server", fake_server)

    result = run_v2_cli(["daily", "--date", "2026-09-08"])

    assert result.exit_code == 0, f"exit {result.exit_code}: {result.output}"
    # Non-JSON path should print suggestion lines or the "no suggestions" fallback
    output_lower = result.output.lower()
    # Either suggestions were printed OR the empty-fallback was printed
    assert ("sugest" in output_lower or "suggest" in output_lower or "no suggestions" in output_lower)


def test_weekly_non_json_output(monkeypatch, fake_server, run_v2_cli):
    """`v2 weekly` (no --json) prints regime info to stdout."""
    import src.ikigai.src.agents.v2.mcp_bridge as _bridge_mod

    monkeypatch.setattr(_bridge_mod, "_server", fake_server)

    result = run_v2_cli(["weekly", "--date", "2026-09-08"])

    assert result.exit_code == 0, f"exit {result.exit_code}: {result.output}"
    assert "ikigai-weekly" in result.output or "Regime" in result.output
