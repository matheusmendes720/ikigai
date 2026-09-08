"""Interface dispatch tests — verify CLI commands route to correct prompt chains + MCP tools.

Phase 9.0 (supersedes Phase 8.4):
- v2 daily/weekly/monthly/quarterly commands route to correct prompt chains
- Skill files exist with YAML frontmatter + vault_read-only constraint
- vault_write invariant holds (no direct vault writes from interface code)

Pattern mirrors interfaces/cli/tests/test_v2_skill_dispatch.py (Phase 8.7):
- Typer CliRunner for in-process CLI invocation
- FakeMcpServer for canned MCP responses
- Dotted-prefix monkeypatch for dual-module identity

conftest.py sets up sys.path with IKIGAI_PKG_ROOT (src/ikigai/), SRC_ROOT (src/),
and REPO_ROOT. v2 modules live under src/ikigai/src/agents/v2/.
Import style: "from agents.v2.X import Y" (no "ikigai.src." prefix).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure conftest paths are available
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SRC_ROOT = REPO_ROOT / "src"
IKIGAI_ROOT = SRC_ROOT / "ikigai"

for _p in [str(REPO_ROOT), str(SRC_ROOT), str(IKIGAI_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

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
    """Return a FakeMcpServer pre-loaded with canned responses for daily/weekly/monthly/quarterly."""
    server = FakeMcpServer()
    # daily skill — surface_intentions entry point
    server.canned_response(
        "ikigai_heuristics",
        context={"regime": "MAINTAIN"},
        heuristics={"suggestion": "Revisar tasks pendentes"},
    )
    server.canned_response(
        "ikigai_observe_pav_state", date="2026-09-08", pav_state={"regime": "MAINTAIN"}
    )
    # weekly/monthly/quarterly — observe entry point
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
# v2 CLI sub-app — import + help routing
# ---------------------------------------------------------------------------

def test_v2_cli_app_importable():
    """v2 Typer sub-app is importable from interfaces.cli.v2."""
    from interfaces.cli.v2 import v2_app

    assert v2_app is not None


def test_v2_daily_command_help():
    """`life v2 daily --help` exits 0 and documents the command."""
    runner = CliRunner()
    result = runner.invoke(v2_app, ["daily", "--help"])
    assert result.exit_code == 0
    assert "daily" in result.output.lower()


def test_v2_weekly_command_help():
    """`life v2 weekly --help` exits 0 and documents the command."""
    runner = CliRunner()
    result = runner.invoke(v2_app, ["weekly", "--help"])
    assert result.exit_code == 0
    assert "weekly" in result.output.lower()


def test_v2_monthly_command_help():
    """`life v2 monthly --help` exits 0 and documents the command."""
    runner = CliRunner()
    result = runner.invoke(v2_app, ["monthly", "--help"])
    assert result.exit_code == 0
    assert "monthly" in result.output.lower()


def test_v2_quarterly_command_help():
    """`life v2 quarterly --help` exits 0 and documents the command."""
    runner = CliRunner()
    result = runner.invoke(v2_app, ["quarterly", "--help"])
    assert result.exit_code == 0
    assert "quarterly" in result.output.lower()


# ---------------------------------------------------------------------------
# Prompt chain routing — in-process (fake MCP server)
# ---------------------------------------------------------------------------

def test_v2_daily_routes_to_surface_intentions(monkeypatch, fake_server, run_v2_cli):
    """`v2 daily` routes to surface_intentions entry point via FakeMcpServer."""
    import src.ikigai.src.agents.v2.mcp_bridge as _bridge_mod

    monkeypatch.setattr(_bridge_mod, "_server", fake_server)

    result = run_v2_cli(["daily", "--date", "2026-09-08", "--json"])
    assert result.exit_code == 0, f"exit {result.exit_code}: {result.output}"
    payload = json.loads(result.output)
    assert payload.get("skill") == "ikigai-daily"
    assert payload.get("date") == "2026-09-08"
    assert "surface_intentions" in payload


def test_v2_weekly_routes_to_observe(monkeypatch, fake_server, run_v2_cli):
    """`v2 weekly` routes to observe entry point via FakeMcpServer."""
    import src.ikigai.src.agents.v2.mcp_bridge as _bridge_mod

    monkeypatch.setattr(_bridge_mod, "_server", fake_server)

    result = run_v2_cli(["weekly", "--date", "2026-09-08", "--json"])
    assert result.exit_code == 0, f"exit {result.exit_code}: {result.output}"
    payload = json.loads(result.output)
    assert payload.get("skill") == "ikigai-weekly"
    assert payload.get("date") == "2026-09-08"
    assert "observe" in payload


def test_v2_monthly_routes_to_observe(monkeypatch, fake_server, run_v2_cli):
    """`v2 monthly` routes to observe entry point via FakeMcpServer."""
    import src.ikigai.src.agents.v2.mcp_bridge as _bridge_mod

    monkeypatch.setattr(_bridge_mod, "_server", fake_server)

    result = run_v2_cli(["monthly", "--date", "2026-09-08", "--json"])
    assert result.exit_code == 0, f"exit {result.exit_code}: {result.output}"
    payload = json.loads(result.output)
    assert payload.get("skill") == "ikigai-monthly"
    assert payload.get("date") == "2026-09-08"
    assert "observe" in payload


def test_v2_quarterly_routes_to_observe(monkeypatch, fake_server, run_v2_cli):
    """`v2 quarterly` routes to observe entry point via FakeMcpServer."""
    import src.ikigai.src.agents.v2.mcp_bridge as _bridge_mod

    monkeypatch.setattr(_bridge_mod, "_server", fake_server)

    result = run_v2_cli(["quarterly", "--date", "2026-09-08", "--json"])
    assert result.exit_code == 0, f"exit {result.exit_code}: {result.output}"
    payload = json.loads(result.output)
    assert payload.get("skill") == "ikigai-quarterly"
    assert payload.get("date") == "2026-09-08"
    assert "observe" in payload


# ---------------------------------------------------------------------------
# Skill files — existence + frontmatter
# ---------------------------------------------------------------------------

def test_skill_files_exist():
    """All 4 skill files exist under src/agents/v2/skills/."""
    skill_dir = IKIGAI_ROOT / "src" / "agents" / "v2" / "skills"
    expected = ["daily.md", "weekly.md", "monthly.md", "quarterly.md"]
    for name in expected:
        path = skill_dir / name
        assert path.exists(), f"Missing skill: {name}"


def test_skill_files_have_frontmatter():
    """All skill files have YAML frontmatter with name + description fields."""
    import re

    skill_dir = IKIGAI_ROOT / "src" / "agents" / "v2" / "skills"
    for name in ["daily.md", "weekly.md", "monthly.md", "quarterly.md"]:
        content = (skill_dir / name).read_text(encoding="utf-8")
        assert content.startswith("---\n"), f"{name} missing YAML frontmatter"
        assert re.search(r"^name:\s", content, re.MULTILINE), f"{name} missing 'name:' field"
        assert re.search(r"^description:\s", content, re.MULTILINE), f"{name} missing 'description:' field"
        assert re.search(r"^triggers:\s", content, re.MULTILINE), f"{name} missing 'triggers:' field"


def test_skill_files_mention_vault_read_only():
    """All skill files document vault_write as sole vault writer (vault_write invariant).

    The constraint that skills are surface-only is documented in the skill's
    description/body referencing vault_write (the canonical vault writer).
    """
    skill_dir = IKIGAI_ROOT / "src" / "agents" / "v2" / "skills"
    for name in ["daily.md", "weekly.md", "monthly.md", "quarterly.md"]:
        content = (skill_dir / name).read_text(encoding="utf-8")
        assert "vault_write" in content, f"{name} must mention vault_write as sole vault writer"
        assert "vault" in content.lower(), f"{name} must reference vault/"


# ---------------------------------------------------------------------------
# vault_write invariant — interface code never writes vault/
# ---------------------------------------------------------------------------

def test_v2_daily_does_not_write_vault(tmp_path, monkeypatch):
    """v2 daily reads vault but produces no new files in vault_root."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "ikigai" / "meta" / "cycle_state").mkdir(parents=True)
    (vault_root / "ikigai" / "meta" / "cycle_state" / "2026-09-03.md").write_text(
        "---\nregime: MAINTAIN\nq_he: 0.65\n---\n# test cycle state",
        encoding="utf-8",
    )
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(vault_root))

    from interfaces.cli import _v2_skills

    # Mock make_v2_graph so no real MCP connection is attempted
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"surface_intentions": {"status": "ok"}}
    monkeypatch.setattr(
        "src.ikigai.src.agents.v2.graph.make_v2_graph",
        lambda entry_point: mock_graph,
    )

    _v2_skills.invoke_skill("daily", date_str="2026-09-03")

    # Vault dir must not have been written to (no new files created)
    all_vault_files = list(vault_root.rglob("*"))
    md_files = [f for f in all_vault_files if f.is_file() and f.suffix == ".md"]
    assert len(md_files) == 1, f"Unexpected vault writes detected: {[f.name for f in md_files]}"


def test_v2_weekly_does_not_write_vault(tmp_path, monkeypatch):
    """v2 weekly reads vault but produces no new files in vault_root."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "ikigai" / "meta" / "cycle_state").mkdir(parents=True)
    (vault_root / "ikigai" / "meta" / "cycle_state" / "2026-09-03.md").write_text(
        "---\nregime: MAINTAIN\nq_he: 0.65\n---\n# test cycle state",
        encoding="utf-8",
    )
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(vault_root))

    from interfaces.cli import _v2_skills

    # Mock make_v2_graph so no real MCP connection is attempted
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"observe": {"status": "ok"}}
    monkeypatch.setattr(
        "src.ikigai.src.agents.v2.graph.make_v2_graph",
        lambda entry_point: mock_graph,
    )

    _v2_skills.invoke_skill("weekly", date_str="2026-09-03")

    all_vault_files = list(vault_root.rglob("*"))
    md_files = [f for f in all_vault_files if f.is_file() and f.suffix == ".md"]
    assert len(md_files) == 1, f"Unexpected vault writes detected: {[f.name for f in md_files]}"
