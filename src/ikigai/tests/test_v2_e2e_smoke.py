"""E2E smoke tests for v2 skill dispatch (daily / weekly).

Phase 9.0 (supersedes earlier versions):
- Tests invoke_skill("daily") and invoke_skill("weekly") directly
- Uses FakeMcpServer for in-process graph execution (no live gateway)
- Vault isolation via monkeypatch on _repo_root in _v2_skills
- Taskdog post-processor mocked via importlib

Pattern mirrors interfaces/cli/tests/test_v2_skill_dispatch.py (Phase 8.7).
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — match test_v2_skill_dispatch.py
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent.parent.parent  # <repo-root>
_SRC_ROOT = _REPO_ROOT / "src"  # <repo-root>/src/
_IKIGAI_SRC = _THIS.parent.parent / "src"  # <repo-root>/src/ikigai/src/

for _p in [str(_REPO_ROOT), str(_SRC_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_IKIGAI_SRC) not in sys.path:
    sys.path.append(_IKIGAI_SRC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _TaskdogMock:
    """Stand-in for taskdog_create_task @tool that records invocations."""

    def __init__(self, return_value: str = "Added task 7 quarterly OKRs") -> None:
        self.return_value = return_value
        self.calls: list[dict] = []

    def invoke(self, params: dict) -> str:
        self.calls.append(dict(params))
        return self.return_value


# ---------------------------------------------------------------------------
# E2E smoke tests
# ---------------------------------------------------------------------------


def test_e2e_daily_invokes_skill(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """E2E: invoke_skill('daily') returns skill name + surface_intentions."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")

    from interfaces.cli._v2_skills import invoke_skill

    # Mock make_v2_graph so no real MCP connection is attempted
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"surface_intentions": {"status": "ok"}}
    monkeypatch.setattr(
        "src.ikigai.src.agents.v2.graph.make_v2_graph",
        lambda entry_point: mock_graph,
    )

    start = time.monotonic()
    result = invoke_skill("daily", date_str="2026-09-08")
    elapsed = time.monotonic() - start

    # Verify skill metadata
    assert result.get("skill") == "ikigai-daily", f"Unexpected skill: {result.get('skill')}"
    assert result.get("date") == "2026-09-08"

    # surface_intentions entry point
    assert "surface_intentions" in result, f"Expected surface_intentions key; got: {list(result.keys())}"

    # Latency SLA — < 1s with mocked @tool + FAKE_LLM
    assert elapsed < 1.0, f"Latency {elapsed:.3f}s exceeds 1s SLA"


def test_e2e_weekly_invokes_skill(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """E2E: invoke_skill('weekly') returns skill name + observe entry point."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")

    from interfaces.cli._v2_skills import invoke_skill

    # Mock make_v2_graph so no real MCP connection is attempted
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"observe": {"status": "ok"}}
    monkeypatch.setattr(
        "src.ikigai.src.agents.v2.graph.make_v2_graph",
        lambda entry_point: mock_graph,
    )

    start = time.monotonic()
    result = invoke_skill("weekly", date_str="2026-09-08")
    elapsed = time.monotonic() - start

    # Verify skill metadata
    assert result.get("skill") == "ikigai-weekly", f"Unexpected skill: {result.get('skill')}"
    assert result.get("date") == "2026-09-08"

    # Full pipeline starts at observe
    assert "observe" in result, f"Expected observe key; got: {list(result.keys())}"

    # Latency SLA
    assert elapsed < 1.0, f"Latency {elapsed:.3f}s exceeds 1s SLA"


def test_e2e_daily_does_not_write_vault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E2E: invoke_skill('daily') does not write to vault (vault_write invariant)."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "ikigai" / "meta" / "cycle_state").mkdir(parents=True)
    (vault_root / "ikigai" / "meta" / "cycle_state" / "2026-09-03.md").write_text(
        "---\nregime: MAINTAIN\nq_he: 0.65\n---\n# test cycle state",
        encoding="utf-8",
    )
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(vault_root))

    from interfaces.cli._v2_skills import invoke_skill

    # Mock make_v2_graph so no real MCP connection is attempted
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"surface_intentions": {"status": "ok"}}
    monkeypatch.setattr(
        "src.ikigai.src.agents.v2.graph.make_v2_graph",
        lambda entry_point: mock_graph,
    )

    invoke_skill("daily", date_str="2026-09-03")

    # Vault must not have been written to — only the pre-existing cycle_state file
    all_vault_files = list(vault_root.rglob("*"))
    md_files = [f for f in all_vault_files if f.is_file() and f.suffix == ".md"]
    assert len(md_files) == 1, f"Unexpected vault writes detected: {[f.name for f in md_files]}"


def test_e2e_weekly_does_not_write_vault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E2E: invoke_skill('weekly') does not write to vault (vault_write invariant)."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "ikigai" / "meta" / "cycle_state").mkdir(parents=True)
    (vault_root / "ikigai" / "meta" / "cycle_state" / "2026-09-03.md").write_text(
        "---\nregime: MAINTAIN\nq_he: 0.65\n---\n# test cycle state",
        encoding="utf-8",
    )
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(vault_root))

    from interfaces.cli._v2_skills import invoke_skill

    # Mock make_v2_graph so no real MCP connection is attempted
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"observe": {"status": "ok"}}
    monkeypatch.setattr(
        "src.ikigai.src.agents.v2.graph.make_v2_graph",
        lambda entry_point: mock_graph,
    )

    invoke_skill("weekly", date_str="2026-09-03")

    all_vault_files = list(vault_root.rglob("*"))
    md_files = [f for f in all_vault_files if f.is_file() and f.suffix == ".md"]
    assert len(md_files) == 1, f"Unexpected vault writes detected: {[f.name for f in md_files]}"


def test_load_skill_manifest_returns_name_and_entry_point() -> None:
    """load_skill_manifest returns manifest with name and entry_point fields."""
    from interfaces.cli._v2_skills import load_skill_manifest

    for skill_name, expected_entry in [
        ("daily", "surface_intentions"),
        ("weekly", "observe"),
        ("monthly", "observe"),
        ("quarterly", "observe"),
    ]:
        manifest = load_skill_manifest(skill_name)
        assert "name" in manifest, f"{skill_name}: missing 'name' field"
        assert "entry_point" in manifest, f"{skill_name}: missing 'entry_point' field"
        assert manifest["entry_point"] == expected_entry, (
            f"{skill_name}: expected entry_point={expected_entry!r}, "
            f"got {manifest['entry_point']!r}"
        )
