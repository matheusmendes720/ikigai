"""v2 16-node parametrized smoke test — every node callable, returns dict.

Catches regressions where a future contributor:
  - silently breaks the import path (e.g. renames a module)
  - changes a node's return type from dict to None or str
  - adds a new node to NODES but forgets to wire it as a graph node

The test runs each of the 16 v2 nodes (matches the NODES tuple in
src/ikigai/src/agents/v2/graph.py plus the error terminal) against
minimal synthetic state and asserts:

  - the module imports
  - the ``<node>_node`` function exists and is callable
  - the function returns a dict (not None, not a string)

Per-node detailed contract tests live in:
  - test_v2_node_isolation.py        (flow / terminal nodes)
  - test_v2_node_isolation_proposals.py (proposal-emitting nodes)
  - test_v2_node_isolation_stubs.py  (M12 stub nodes)

Constraints:
  - Drift net (canonical_scope + drift_invariants + drift_extended_invariants)
    must stay 66+ PASS / 2 SKIP.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Path setup — match test_v2_graph_smoke.py pattern
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


# ---------------------------------------------------------------------------
# 16 v2 nodes — graph name -> (file module name, function name)
#
# Most nodes have file name == function name (e.g. balance.py exports
# balance_node). Two exceptions:
#   - "reason"   in graph.py NODES  -> reason_node.py   exports reason_node
#   - "recall"   in graph.py NODES  -> recall_node.py  exports recall_node
# ---------------------------------------------------------------------------
NODES: tuple[tuple[str, str, str], ...] = (
    ("balance", "balance", "balance_node"),
    ("commit", "commit", "commit_node"),
    ("decompose", "decompose", "decompose_node"),
    ("dep_graph", "dep_graph", "dep_graph_node"),
    ("error", "error", "error_node"),
    ("gantt_suggest", "gantt_suggest", "gantt_suggest_node"),
    ("heuristics", "heuristics", "heuristics_node"),
    ("observe", "observe", "observe_node"),
    ("plan", "plan", "plan_node"),
    ("reason", "reason_node", "reason_node"),
    ("recall", "recall_node", "recall_node"),
    ("reflect", "reflect", "reflect_node"),
    ("score_vectors", "score_vectors", "score_vectors_node"),
    ("surface_intentions", "surface_intentions", "surface_intentions_node"),
    ("tag_and_persist", "tag_and_persist", "tag_and_persist_node"),
    ("tag_propagation", "tag_propagation", "tag_propagation_node"),
)


def _base_state() -> dict[str, Any]:
    """Minimal IKIGAiStateDict — keys are NotRequired, so this is enough."""
    return {
        "cycle_id": "smoke-test",
        "iteration": 0,
    }


@pytest.mark.parametrize(("graph_name", "module_name", "fn_name"), NODES)
def test_v2_node_callable_returns_dict(graph_name, module_name, fn_name, monkeypatch):
    """Every v2 node imports cleanly and returns a dict for minimal state."""
    import importlib

    # tag_and_persist needs wrap_vault_write on its module — inject a no-op
    # so it doesn't blow up on ImportError for the missing `v2` package.
    if graph_name == "tag_and_persist":
        from src.ikigai.src.agents.v2.nodes import tag_and_persist as tap_mod

        monkeypatch.setattr(
            tap_mod,
            "wrap_vault_write",
            lambda **kw: {"ok": False, "error": "parametrize_mock"},
            raising=False,
        )

    # surface_intentions needs the LLM renderer mocked — without ANTHROPIC_API_KEY
    # the real call hangs/fails and obscures the contract assertion.
    if graph_name == "surface_intentions":
        from src.ikigai.src.agents.v2.nodes import surface_intentions as surf_mod

        monkeypatch.setattr(
            surf_mod,
            "render_surface_pav_intentions",
            lambda state: {"suggestions": [], "language": "pt-BR"},
            raising=False,
        )

    # recall_node graceful fallback requires no memory_db — force the helper.
    if graph_name == "recall":
        from src.ikigai.src.agents.v2.nodes import recall_node as recall_mod

        monkeypatch.setattr(recall_mod, "_resolve_memory_db", lambda: None)
        monkeypatch.delenv("IKIGAI_MEMORY_DB", raising=False)

    mod = importlib.import_module(f"src.ikigai.src.agents.v2.nodes.{module_name}")
    assert hasattr(mod, fn_name), f"{fn_name} missing from {mod}"
    fn = getattr(mod, fn_name)
    assert callable(fn), f"{fn_name} not callable"

    result = fn(_base_state())
    assert isinstance(result, dict), f"{graph_name} returned non-dict: {type(result)}"


def test_v2_node_count_matches_graph_nodes_tuple():
    """Smoke test NODES count matches the canonical NODES tuple in graph.py.

    Per drift invariant: any future change to graph.py NODES tuple
    must update this smoke test (and the per-node detail files).
    """
    from src.ikigai.src.agents.v2.graph import NODES as GRAPH_NODES

    graph_node_names = set(GRAPH_NODES)
    smoke_node_names = {entry[0] for entry in NODES}

    # dispatch_sub_agents is a subgraph, not a node function — it's
    # intentionally absent from NODES. Error is a terminal but lives
    # in nodes/error.py.
    not_covered = {"dispatch_sub_agents"}
    covered = graph_node_names - not_covered

    assert covered.issubset(smoke_node_names), (
        f"graph.NODES has entries not in smoke test NODES: {covered - smoke_node_names}"
    )
    # Sanity: error terminal is in smoke (15 nodes + error = 16)
    assert "error" in smoke_node_names
    assert len(smoke_node_names) == 16
