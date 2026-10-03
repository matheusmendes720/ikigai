"""v2 node isolation tests — proposal-emitting nodes.

Covers the 4 v2 nodes whose output is a ``proposal`` dict intended for
the review queue (per ADR-013 — never auto-execute writes):

  - dep_graph_node   — proposes dep additions among cluster siblings
  - gantt_suggest_node — topological + priority-weighted task order
  - tag_and_persist_node — wraps wrap_vault_write (vault write path)
  - tag_propagation_node — BFS-walks dep graph, proposes tag set

Each node is a pure-ish function: state_in -> state_out (LangGraph merges
the returned dict into state). These tests call the node functions directly
(no graph, no checkpointing) with minimal synthetic state and assert:

  - the call does not raise
  - the return value is a dict
  - the proposal shape matches the documented review-queue contract
  - missing/invalid input falls back to empty proposal gracefully

The M12 STUB nodes live in test_v2_node_isolation_stubs.py.
The FLOW / TERMINAL nodes live in test_v2_node_isolation.py.
The 16-node parametrized smoke test lives in test_v2_node_isolation_smoke.py.

Constraints:
  - DO NOT modify node code; tests are read-only over node contracts.
  - Mock wrap_vault_write for tag_and_persist_node so the test is hermetic.
  - Drift net (canonical_scope + drift_invariants + drift_extended_invariants)
    must stay 66+ PASS / 2 SKIP.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup — match test_v2_graph_smoke.py pattern (the working v2 tests)
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent.parent.parent
_SRC_ROOT = _REPO_ROOT / "src"
_IKIGAI_SRC = _THIS.parent.parent / "src"

for _p in [str(_REPO_ROOT), str(_SRC_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_IKIGAI_SRC) not in sys.path:
    sys.path.append(str(_IKIGAI_SRC))


def _base_state(**overrides: Any) -> dict[str, Any]:
    """Minimal IKIGAiStateDict with sensible defaults."""
    state: dict[str, Any] = {
        "cycle_id": "iso-test-001",
        "iteration": 0,
        "draft_proposal": {},
        "proposed_entity": None,
        "vault_path": None,
        "actor": "agent",
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# dep_graph_node (pure Python: cluster + cycle check)
# ---------------------------------------------------------------------------
def test_dep_graph_node_isolation_with_safe_cluster():
    """dep_graph_node proposes dep additions for an acyclic 3-task cluster."""
    from src.ikigai.src.agents.v2.nodes.dep_graph import dep_graph_node

    state = _base_state(
        dep_graph_input={
            "project_prefix": "ts:prj:abcd",
            "tasks": {
                "ts:prj:abcd:0001": {"priority": 2},
                "ts:prj:abcd:0002": {"priority": 1},
                "ts:prj:abcd:0003": {"priority": 3},
            },
            "existing_deps": {},
        }
    )
    result = dep_graph_node(state)

    proposal = result["proposal"]
    assert proposal["action"] == "add_deps"
    assert proposal["node"] == "dep_graph"
    # Sorted deterministic pick: first UEID alphabetically gets a dep proposal.
    assert proposal["from_ueid"] == "ts:prj:abcd:0001"
    assert set(proposal["to_ueids"]) == {"ts:prj:abcd:0002", "ts:prj:abcd:0003"}
    assert result["last_step"] == "dep_graph"


def test_dep_graph_node_isolation_missing_prefix():
    """dep_graph_node returns empty proposal when project_prefix is missing."""
    from src.ikigai.src.agents.v2.nodes.dep_graph import dep_graph_node

    result = dep_graph_node(_base_state(dep_graph_input={"tasks": {}}))

    assert result["proposal"]["from_ueid"] is None
    assert result["proposal"]["to_ueids"] == []
    assert "missing" in result["proposal"]["reason"]


# ---------------------------------------------------------------------------
# gantt_suggest_node (pure Python: Kahn's algo + priority heap)
# ---------------------------------------------------------------------------
def test_gantt_suggest_node_isolation_with_dag():
    """gantt_suggest_node emits topological + priority-weighted order."""
    from src.ikigai.src.agents.v2.nodes.gantt_suggest import gantt_suggest_node

    state = _base_state(
        gantt_input={
            "tasks": {
                "u-a": {"priority": 2, "deps": []},
                "u-b": {"priority": 1, "deps": ["u-a"]},
                "u-c": {"priority": 3, "deps": ["u-a"]},
            }
        }
    )
    result = gantt_suggest_node(state)

    proposal = result["proposal"]
    assert proposal["action"] == "reorder"
    assert proposal["node"] == "gantt_suggest"
    # u-a must come before u-b and u-c (dependency order).
    order = proposal["suggestion"]
    assert order.index("u-a") < order.index("u-b")
    assert order.index("u-a") < order.index("u-c")
    # Two parallel batches: [u-a], then [u-b, u-c].
    assert len(proposal["batches"]) == 2
    assert result["last_step"] == "gantt_suggest"


def test_gantt_suggest_node_isolation_missing_tasks():
    """gantt_suggest_node falls back to empty proposal on missing tasks."""
    from src.ikigai.src.agents.v2.nodes.gantt_suggest import gantt_suggest_node

    result = gantt_suggest_node(_base_state(gantt_input={}))

    assert result["proposal"]["suggestion"] == []
    assert result["proposal"]["batches"] == []
    assert result["last_step"] == "gantt_suggest"


# ---------------------------------------------------------------------------
# tag_and_persist_node (vault write: mock wrap_vault_write)
# ---------------------------------------------------------------------------
def test_tag_and_persist_node_isolation_missing_inputs():
    """tag_and_persist_node returns error_channel when inputs are missing."""
    from src.ikigai.src.agents.v2.nodes.tag_and_persist import tag_and_persist_node

    result = tag_and_persist_node(_base_state())

    assert result["persisted"] is False
    assert result["last_step"] == "tag_and_persist"
    assert len(result["error_channel"]) >= 1
    assert "missing" in result["error_channel"][0].lower()


def _register_fake_v2_proposal_executor(monkeypatch):
    """Register a fake ``v2.nodes.proposal_executor`` in sys.modules.

    tag_and_persist_node does ``from v2.nodes.proposal_executor import
    wrap_vault_write`` inside the function. ``v2`` is not a real top-level
    package in this repo (the real path is
    ``src.ikigai.src.agents.v2``), so the import always fails with
    ``No module named 'v2'`` and the node returns error_channel without
    ever calling wrap_vault_write. Registering fake entries in sys.modules
    lets the import succeed, and we then inject wrap_vault_write on the
    fake module to control its return value per case.
    """
    import types

    if "v2" not in sys.modules:
        v2_pkg = types.ModuleType("v2")
        v2_pkg.__path__ = []  # mark as package
        v2_nodes_pkg = types.ModuleType("v2.nodes")
        v2_nodes_pkg.__path__ = []
        pe_mod = types.ModuleType("v2.nodes.proposal_executor")
        v2_nodes_pkg.proposal_executor = pe_mod
        monkeypatch.setitem(sys.modules, "v2", v2_pkg)
        monkeypatch.setitem(sys.modules, "v2.nodes", v2_nodes_pkg)
        monkeypatch.setitem(sys.modules, "v2.nodes.proposal_executor", pe_mod)
    return sys.modules["v2.nodes.proposal_executor"]


def test_tag_and_persist_node_isolation_with_vault_write(monkeypatch):
    """tag_and_persist_node invokes wrap_vault_write and reports ok=True."""
    from src.ikigai.src.agents.v2.nodes import proposal_executor as real_pe
    fake_report = {"ok": True, "error": ""}
    monkeypatch.setattr(
        real_pe, "wrap_vault_write", lambda **kw: fake_report, raising=False
    )

    from src.ikigai.src.agents.v2.nodes import tag_and_persist as tap_mod

    state = _base_state(
        proposed_entity={"tier": "daily", "title": "iso test", "ueid": "ts:dia:iso:0001"},
        vault_path="ikigai/iso-test.md",
        actor="agent",
        user_request="isolation test request",
    )
    result = tap_mod.tag_and_persist_node(state)

    assert result["persisted"] is True
    assert result["vault_path"] == "ikigai/iso-test.md"
    assert result["actor"] == "agent"
    assert result["last_step"] == "tag_and_persist"
    assert result["error_channel"] == []


def test_tag_and_persist_node_isolation_vault_write_fails(monkeypatch):
    """tag_and_persist_node surfaces error when wrap_vault_write returns ok=False."""
    from src.ikigai.src.agents.v2.nodes import proposal_executor as real_pe
    fake_report = {"ok": False, "error": "rate_limit_exceeded"}
    monkeypatch.setattr(
        real_pe, "wrap_vault_write", lambda **kw: fake_report, raising=False
    )

    from src.ikigai.src.agents.v2.nodes import tag_and_persist as tap_mod

    state = _base_state(
        proposed_entity={"tier": "daily", "title": "iso test"},
        vault_path="ikigai/iso-test.md",
    )
    result = tap_mod.tag_and_persist_node(state)

    assert result["persisted"] is False
    assert len(result["error_channel"]) >= 1
    assert "rate_limit_exceeded" in result["error_channel"][0]


def test_tag_and_persist_node_isolation_real_import_works(monkeypatch):
    """Regression: tag_and_persist_node imports wrap_vault_write via the canonical
    src.ikigai.src.agents.v2.nodes.proposal_executor path (NOT a fake v2 module).

    Before the fix, the node used `from v2.nodes.proposal_executor import ...`
    which fails because v2 is not a top-level package in this repo. This test
    asserts that the real import path works without sys.modules hacks.
    """
    import importlib
    import src.ikigai.src.agents.v2.nodes.tag_and_persist as tap_mod
    from src.ikigai.src.agents.v2.nodes import proposal_executor as real_pe

    # Mock the REAL wrap_vault_write so we don't write to the real vault.
    fake_report = {"ok": True, "error": ""}
    monkeypatch.setattr(
        real_pe, "wrap_vault_write", lambda **kw: fake_report, raising=False
    )

    # Force re-evaluation of the inner `from ... import wrap_vault_write`:
    # the node does the import inside the function, so as long as the module
    # attribute is patched, the next call sees the patch. No sys.modules fake.
    state = _base_state(
        proposed_entity={"tier": "daily", "title": "real-import test", "ueid": "ts:dia:iso:0002"},
        vault_path="ikigai/real-import-test.md",
        actor="agent",
        user_request="regression: real import path",
    )
    result = tap_mod.tag_and_persist_node(state)

    # If the import was wrong, the node would return error_channel = [...'No module named v2'...]
    # and persisted would be False. Assert the real path actually ran.
    assert result["persisted"] is True, (
        f"tag_and_persist_node should have imported wrap_vault_write via the canonical "
        f"path, but got: {result.get('error_channel')}"
    )
    assert result["vault_path"] == "ikigai/real-import-test.md"
    assert result["last_step"] == "tag_and_persist"
    assert result["error_channel"] == []

    # Also verify the real module is importable from the canonical path
    assert hasattr(real_pe, "wrap_vault_write"), (
        "proposal_executor module should export wrap_vault_write"
    )


# ---------------------------------------------------------------------------
# tag_propagation_node (pure Python: BFS over dep graph)
# ---------------------------------------------------------------------------
def test_tag_propagation_node_isolation_bfs_walk():
    """tag_propagation_node BFS-walks the dep graph + emits deterministic targets."""
    from src.ikigai.src.agents.v2.nodes.tag_propagation import tag_propagation_node

    state = _base_state(
        tag_propagation_input={
            "source_ueid": "ts:prj:abcd:0001",
            "tags": ["weekly", "p0"],
            "graph": {
                "ts:prj:abcd:0001": ["ts:prj:abcd:0002", "ts:prj:abcd:0003"],
                "ts:prj:abcd:0002": ["ts:prj:abcd:0004"],
                "ts:prj:abcd:0003": [],
                "ts:prj:abcd:0004": [],
            },
        }
    )
    result = tag_propagation_node(state)

    proposal = result["proposal"]
    assert proposal["action"] == "tag_propagate"
    assert proposal["node"] == "tag_propagation"
    assert proposal["source_ueid"] == "ts:prj:abcd:0001"
    assert set(proposal["target_ueids"]) == {
        "ts:prj:abcd:0002",
        "ts:prj:abcd:0003",
        "ts:prj:abcd:0004",
    }
    # Tags deduped + sorted
    assert proposal["tags"] == ["p0", "weekly"]
    # target_ueids sorted deterministically (not BFS-discovery order)
    assert proposal["target_ueids"] == sorted(proposal["target_ueids"])
    assert result["last_step"] == "tag_propagation"


def test_tag_propagation_node_isolation_missing_input():
    """tag_propagation_node falls back to empty proposal on missing payload."""
    from src.ikigai.src.agents.v2.nodes.tag_propagation import tag_propagation_node

    result = tag_propagation_node(_base_state(tag_propagation_input={}))

    proposal = result["proposal"]
    assert proposal["target_ueids"] == []
    assert proposal["tags"] == []
    assert "missing" in proposal["reason"]
    assert result["last_step"] == "tag_propagation"
