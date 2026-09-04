"""W3.5 — invoke_skill() + daily skill wiring tests.

Per W3.5 brief:
- invoke_skill("ikigai-daily") runs the graph and returns surface_intentions output
- invoke_skill uses manifest entry_point by default
- invoke_skill logs warning when entry_point_override differs from manifest
- invoke_skill raises ValueError on unknown entry_point
- Full pipeline daily entry returns user_suggestions populated (FAKE_LLM mode)

conftest.py sets up sys.path with IKIGAI_PKG_ROOT (src/ikigai/), SRC_ROOT (src/),
and REPO_ROOT. v2 modules live under src/ikigai/src/agents/v2/.
Import style: "from agents.v2.X import Y" (no "ikigai.src." prefix).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup — match test_v2_graph_smoke.py pattern
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent.parent.parent  # <repo-root>
_SRC_ROOT = _REPO_ROOT / "src"  # <repo-root>/src/
_IKIGAI_SRC = _THIS.parent.parent / "src"  # <repo-root>/src/ikigai/src/ (nested!)

for _p in [str(_REPO_ROOT), str(_SRC_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_IKIGAI_SRC) not in sys.path:
    sys.path.append(_IKIGAI_SRC)


# ---------------------------------------------------------------------------
# Tests — invoke_skill helper
# ---------------------------------------------------------------------------

def test_invoke_skill_importable():
    """invoke_skill is importable from interfaces.cli.v2."""
    from interfaces.cli.v2 import invoke_skill

    assert callable(invoke_skill)


def test_invoke_skill_loads_daily_manifest():
    """invoke_skill loads ikigai-daily manifest with entry_point + actor fields."""
    from interfaces.cli.v2 import load_skill_manifest

    manifest = load_skill_manifest("ikigai-daily")
    assert "entry_point" in manifest, "daily.md must have entry_point field"
    assert "actor" in manifest, "daily.md must have actor field"
    assert manifest["entry_point"] == "surface_intentions"
    assert manifest["actor"] == "user"


def test_invoke_skill_with_override_different_logs_warning(caplog, monkeypatch):
    """invoke_skill(entry_point_override=...) different from manifest logs warning.

    Note: when entry_point_override="observe", the graph runs the full pipeline
    (observe → ... → surface_intentions) and may error at tag_and_persist if
    required state fields (e.g. proposed_entity) are missing from initial_state.
    This is expected — the test verifies the warning is logged, not the result.
    """
    import logging

    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    from interfaces.cli.v2 import invoke_skill

    # Use a valid entry_point different from manifest's "surface_intentions"
    with caplog.at_level(logging.WARNING):
        result = invoke_skill("ikigai-daily", entry_point_override="observe")
    # Should have logged the warning
    assert any("entry_point override" in r.message for r in caplog.records), (
        "Warning should be logged when override differs from manifest"
    )
    # Result is a dict (graph may error due to missing state fields in full pipeline)
    assert isinstance(result, dict)


def test_invoke_skill_with_override_same_uses_override(monkeypatch):
    """invoke_skill uses the override when it matches manifest entry_point."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    from interfaces.cli.v2 import invoke_skill

    # "surface_intentions" is the manifest entry_point, so override==manifest
    result = invoke_skill("ikigai-daily", entry_point_override="surface_intentions")
    assert isinstance(result, dict)


def test_invoke_skill_unknown_entry_point_raises():
    """invoke_skill raises ValueError for unknown entry_point."""
    from interfaces.cli.v2 import invoke_skill

    with pytest.raises(ValueError, match="Invalid entry_point"):
        invoke_skill("ikigai-daily", entry_point_override="not_a_real_node")


def test_invoke_skill_daily_returns_user_suggestions(tmp_path, monkeypatch):
    """invoke_skill('ikigai-daily') returns dict with user_suggestions (FAKE_LLM)."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(tmp_path / "vault"))
    from interfaces.cli.v2 import invoke_skill

    result = invoke_skill("ikigai-daily")
    assert isinstance(result, dict)
    assert "user_suggestions" in result
    assert len(result["user_suggestions"]) >= 3
    assert result.get("suggestions_language") == "pt-BR"


def test_invoke_skill_uses_manifest_entry_point_by_default(tmp_path, monkeypatch):
    """Without override, invoke_skill uses the entry_point from daily.md manifest."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(tmp_path / "vault"))
    from interfaces.cli.v2 import invoke_skill

    # Manifest for ikigai-daily has entry_point: surface_intentions
    result = invoke_skill("ikigai-daily")
    # surface_intentions_node sets last_step = "surface_intentions" on success
    assert result.get("last_step") == "surface_intentions"


# ---------------------------------------------------------------------------
# Tests — daily command via Typer runner
# ---------------------------------------------------------------------------

def test_daily_command_surface_suggestions_via_skill(tmp_path, monkeypatch):
    """`life v2 daily` via invoke_skill returns suggestions in surface (FAKE_LLM)."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(vault_root))

    from interfaces.cli.v2 import v2_app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(v2_app, ["daily", "--json"])
    assert result.exit_code == 0
    import json

    output = json.loads(result.output)
    surface = output.get("surface", {})
    assert "suggestions" in surface, f"daily output must have surface.suggestions; got {output}"
    assert len(surface["suggestions"]) >= 3
    assert surface.get("language") == "pt-BR"


def test_daily_command_no_vault_write(tmp_path, monkeypatch):
    """`life v2 daily` does not write to vault (surface-only per daily.md)."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(vault_root))

    from interfaces.cli.v2 import v2_app
    from typer.testing import CliRunner

    runner = CliRunner()
    _ = runner.invoke(v2_app, ["daily"])

    # Vault must not have been written to
    md_files = [f for f in vault_root.rglob("*.md") if f.is_file()]
    assert len(md_files) == 0, f"daily skill must not write vault; found: {[f.name for f in md_files]}"
