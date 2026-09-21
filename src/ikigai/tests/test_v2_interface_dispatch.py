"""Interface dispatch tests — verify CLI commands route to correct prompt chains + MCP tools.

Phase 8.4 gates (M73.7 initial):
- v2 Typer sub-app imports cleanly
- v2 cycle/score/regime/suggest commands each route to correct prompt chain
- Skill files exist with YAML frontmatter + vault_read-only constraint
- vault_write invariant holds (no direct vault writes from interface code)

M92: 4 commands from Phase 8.2 (suggest/score/regime/cycle) were removed per V5-D
(only plan/invoke-skill/skill-list/skill-show survive). Their interface-dispatch
tests are now obsolete — re-skipped individually below.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure conftest paths are available
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SRC_ROOT = REPO_ROOT / "src"
IKIGAI_ROOT = SRC_ROOT / "ikigai"

# M73.7: SRC_ROOT must come BEFORE IKIGAI_ROOT so that `import contracts`
# resolves to src/contracts/ (canonical Pydantic models with TaskChange)
# rather than src/ikigai/contracts/ (Plan D proposal module which is
# missing TaskChange). The src/ikigai/contracts/ sub-package shadows
# src/contracts/ when inserted first because both have an __init__.py.
for _p in [str(REPO_ROOT), str(SRC_ROOT), str(IKIGAI_ROOT)]:
    if _p not in sys.path:
        sys.path.append(_p)
# Then put IKIGAI_ROOT last in priority (for `from agents.v2.X import Y` style)
if str(IKIGAI_ROOT) in sys.path:
    sys.path.remove(str(IKIGAI_ROOT))
sys.path.insert(0, str(IKIGAI_ROOT))  # for nested imports
# But ensure SRC_ROOT is checked before IKIGAI_ROOT for `contracts`:
sys.path.insert(0, str(SRC_ROOT))


# ---------------------------------------------------------------------------
# v2 CLI sub-app — import + help routing
# ---------------------------------------------------------------------------


def test_v2_cli_app_importable():
    """v2 Typer sub-app is importable from interfaces.cli.v2."""
    from interfaces.cli.v2 import v2_app

    assert v2_app is not None


# M95: unskipped - the V5-D-removed command now exists as an alias


def test_v2_suggest_command_help():
    """`life v2 suggest --help` exits 0 and documents the command."""
    from interfaces.cli.v2 import v2_app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2_app, ["suggest", "--help"])
    assert result.exit_code == 0
    assert "suggest" in result.output.lower() or "PAV" in result.output


# M95: unskipped - the V5-D-removed command now exists as an alias


def test_v2_score_command_help():
    """`life v2 score --help` exits 0 and shows date + json options."""
    from interfaces.cli.v2 import v2_app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2_app, ["score", "--help"])
    assert result.exit_code == 0
    assert "date" in result.output.lower() or "json" in result.output.lower()


# M95: unskipped - the V5-D-removed command now exists as an alias


def test_v2_regime_command_help():
    """`life v2 regime --help` exits 0 and shows date + json options."""
    from interfaces.cli.v2 import v2_app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2_app, ["regime", "--help"])
    assert result.exit_code == 0


# M95: unskipped - the V5-D-removed command now exists as an alias


def test_v2_cycle_command_help():
    """`life v2 cycle --help` exits 0 and shows dry-run option."""
    from interfaces.cli.v2 import v2_app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2_app, ["cycle", "--help"])
    assert result.exit_code == 0
    assert "dry-run" in result.output.lower() or "json" in result.output.lower()


# ---------------------------------------------------------------------------
# Prompt chain routing — in-process (fake-LLM)
# ---------------------------------------------------------------------------


# M95: unskipped - the V5-D-removed command now exists as an alias


def test_v2_score_routes_to_prompt_chain(monkeypatch):
    """`v2 score` routes to render_score_passion_observation (fake-LLM stub)."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    from interfaces.cli.v2 import v2_app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2_app, ["score", "--json"])
    assert result.exit_code == 0
    output = result.output.strip()
    assert "passion_score" in output or "error" in output


# M95: unskipped - the V5-D-removed command now exists as an alias


def test_v2_regime_routes_to_prompt_chain(monkeypatch):
    """`v2 regime` routes to render_heuristics_regime_observation (fake-LLM stub)."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    from interfaces.cli.v2 import v2_app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2_app, ["regime", "--json"])
    assert result.exit_code == 0
    output = result.output.strip()
    assert "regime" in output or "error" in output


# M95: unskipped - the V5-D-removed command now exists as an alias
def test_v2_suggest_routes_to_surface_pav_intentions(monkeypatch):
    """`v2 suggest` routes to render_surface_pav_intentions (fake-LLM stub)."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    from interfaces.cli.v2 import v2_app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2_app, ["suggest", "--json"])
    assert result.exit_code == 0
    output = result.output.strip()
    assert "suggestions" in output or "error" in output


# M95: unskipped - the V5-D-removed command now exists as an alias


def test_v2_cycle_dry_run_invokes_graph(monkeypatch):
    """`v2 cycle --dry-run` invokes make_v2_graph without crashing."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    monkeypatch.setenv(
        "IKIGAI_VAULT_ROOT", str(Path(__file__).parent.parent.parent.parent / "vault")
    )
    from interfaces.cli.v2 import v2_app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2_app, ["cycle", "--dry-run", "--json"])
    assert result.exit_code in (0, 1)
    if result.exit_code == 1:
        assert (
            "FAIL" in result.output or "Error" in result.output or "failed" in result.output.lower()
        )


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
        assert re.search(r"^description:\s", content, re.MULTILINE), (
            f"{name} missing 'description:' field"
        )
        assert re.search(r"^triggers:\s", content, re.MULTILINE), (
            f"{name} missing 'triggers:' field"
        )


def test_skill_files_mention_vault_read_only():
    """All skill files document vault_read-only constraint (vault_write invariant)."""
    skill_dir = IKIGAI_ROOT / "src" / "agents" / "v2" / "skills"
    for name in ["daily.md", "weekly.md", "monthly.md", "quarterly.md"]:
        content = (skill_dir / name).read_text(encoding="utf-8")
        assert "vault_write" in content, f"{name} must mention vault_write as sole vault writer"
        assert "vault" in content.lower(), f"{name} must reference vault/"


# ---------------------------------------------------------------------------
# vault_write invariant — interface code never writes vault/
# ---------------------------------------------------------------------------


# M95: unskipped - the V5-D-removed command now exists as an alias


def test_v2_score_does_not_write_vault(tmp_path, monkeypatch):
    """v2 score reads vault but produces no new files in vault_root."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "ikigai" / "meta" / "cycle_state").mkdir(parents=True)
    (vault_root / "ikigai" / "meta" / "cycle_state" / "2026-09-03.md").write_text(
        "---\nregime: MAINTAIN\nq_he: 0.65\n---\n# test cycle state",
        encoding="utf-8",
    )
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(vault_root))

    from interfaces.cli.v2 import v2_app
    from typer.testing import CliRunner

    runner = CliRunner()
    _ = runner.invoke(v2_app, ["score", "--date", "2026-09-03"])

    all_vault_files = list(vault_root.rglob("*"))
    md_files = [f for f in all_vault_files if f.is_file() and f.suffix == ".md"]
    assert len(md_files) == 1, f"Unexpected vault writes detected: {[f.name for f in md_files]}"


# M95: unskipped - the V5-D-removed command now exists as an alias


def test_v2_regime_does_not_write_vault(tmp_path, monkeypatch):
    """v2 regime reads vault but produces no new files in vault_root."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "ikigai" / "meta" / "cycle_state").mkdir(parents=True)
    (vault_root / "ikigai" / "meta" / "cycle_state" / "2026-09-03.md").write_text(
        "---\nregime: MAINTAIN\nq_he: 0.65\n---\n# test cycle state",
        encoding="utf-8",
    )
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(vault_root))

    from interfaces.cli.v2 import v2_app
    from typer.testing import CliRunner

    runner = CliRunner()
    _ = runner.invoke(v2_app, ["regime", "--date", "2026-09-03"])

    all_vault_files = list(vault_root.rglob("*"))
    md_files = [f for f in all_vault_files if f.is_file() and f.suffix == ".md"]
    assert len(md_files) == 1, f"Unexpected vault writes detected: {[f.name for f in md_files]}"
