"""PAV intention surfacing tests — verify 9th v2 node + pt-BR suggestions."""

from __future__ import annotations

# conftest.py sets up sys.path with IKIGAI_PKG_ROOT (src/ikigai/), SRC_ROOT (src/),
# and REPO_ROOT. The v2 modules live under src/ikigai/src/agents/v2/, which
# resolves via the IKIGAI_PKG_ROOT sys.path entry. Import style matches
# test_v2_prompt_chains.py: "from agents.v2.prompts import ..." not
# "from sys_ikigai.src.agents.v2.prompts import ...".


def test_prompt_template_imports():
    """surface_pav_intentions prompt template is importable."""
    from agents.v2.prompts.surface_pav_intentions import (
        render_surface_pav_intentions,
    )

    assert render_surface_pav_intentions is not None


def test_node_imports():
    """surface_intentions node is importable."""
    from agents.v2.nodes.surface_intentions import surface_intentions_node

    assert surface_intentions_node is not None


def test_graph_has_11_nodes():
    """v2 graph now has 11 nodes (was 9 pre-W4.4; +1 for dispatch_sub_agents).

    Phase history: 8 (pre-8.4) -> 9 (added surface_intentions) -> 10 (added
    tag_and_persist via Plan A) -> 11 (added dispatch_sub_agents via W4.4).
    """
    # graph.py lives in agents/v2/ so it resolves via the sys.path entry
    from agents.v2.graph import NODES

    assert len(NODES) == 11
    assert "surface_intentions" in NODES
    assert "dispatch_sub_agents" in NODES


def test_fake_llm_emits_suggestions(monkeypatch):
    """With IKIGAI_FAKE_LLM=1, render returns >=3 pt-BR suggestions."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    from agents.v2.prompts.surface_pav_intentions import (
        render_surface_pav_intentions,
    )

    state = {"vault_root": "vault"}
    result = render_surface_pav_intentions(state)
    assert "suggestions" in result
    assert len(result["suggestions"]) >= 3
    assert result["language"] == "pt-BR"


def test_node_returns_user_suggestions(monkeypatch):
    """surface_intentions_node populates state[user_suggestions]."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    from agents.v2.nodes.surface_intentions import surface_intentions_node

    state = {"vault_root": "vault", "last_step": "commit"}
    result = surface_intentions_node(state)
    assert "user_suggestions" in result
    assert len(result["user_suggestions"]) >= 3
    assert result["last_step"] == "surface_intentions"


def test_vault_read_only_no_writes(tmp_path, monkeypatch):
    """surface_intentions must NOT write to vault (vault_write invariant)."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")

    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "ikigai" / "meta" / "cycle_state").mkdir(parents=True)
    (vault_root / "ikigai" / "meta" / "cycle_state" / "2026-09-03.md").write_text(
        "---\nregime: MAINTAIN\nq_he: 0.65\n---\n# test",
        encoding="utf-8",
    )

    from agents.v2.prompts.surface_pav_intentions import (
        render_surface_pav_intentions,
    )

    state = {"vault_root": str(vault_root)}
    render_surface_pav_intentions(state)

    # Verify vault directory was NOT modified (only read)
    cycle_state_files = list((vault_root / "ikigai" / "meta" / "cycle_state").iterdir())
    assert len(cycle_state_files) == 1
    assert cycle_state_files[0].name == "2026-09-03.md"
