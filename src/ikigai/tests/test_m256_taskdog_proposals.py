"""M256 taskdog-proposal node behavior tests.

Covers the 3 pure-Python nodes classified as WORKS in
``docs/diagnostics/M154-v2-graph-inventory.md``: tag_propagation
(BFS), dep_graph (cluster-prefix + DFS cycle detection), gantt_suggest
(Kahn + batching). Per ADR-013 the nodes only COMPUTE a proposal; the
review queue handles writes. Tests call ``*_node(state)`` directly —
not ``graph.invoke(...)`` (separate worker's job).
"""
from __future__ import annotations

from typing import Any

from src.ikigai.src.agents.v2.nodes.dep_graph import dep_graph_node
from src.ikigai.src.agents.v2.nodes.gantt_suggest import gantt_suggest_node
from src.ikigai.src.agents.v2.nodes.tag_propagation import tag_propagation_node

# 4-part UEID canonical per ADR-014.
_C = "ts:prj:abcd"
_A, _B, _C2, _D = f"{_C}:0001", f"{_C}:0002", f"{_C}:0003", f"{_C}:0004"


def _p(state: dict[str, Any]) -> dict[str, Any]:
    return state["proposal"]


class TestTagPropagation:
    """BFS over dep graph; produces sorted target_ueids."""

    def test_empty_input_returns_missing_reason(self) -> None:
        p = _p(tag_propagation_node({}))
        assert p["action"] == "tag_propagate"
        assert p["target_ueids"] == []
        assert p["source_ueid"] is None
        assert "missing" in p["reason"]

    def test_missing_source_ueid_returns_empty_proposal(self) -> None:
        p = _p(tag_propagation_node({"tag_propagation_input": {"tags": ["p0"], "graph": {}}}))
        assert p["target_ueids"] == []
        assert p["source_ueid"] is None
        assert "missing" in p["reason"]

    def test_missing_tags_returns_empty_proposal(self) -> None:
        p = _p(tag_propagation_node({"tag_propagation_input": {"source_ueid": _A, "graph": {}}}))
        assert p["target_ueids"] == []
        assert p["source_ueid"] == _A  # echoed even on guard
        assert "missing" in p["reason"]

    def test_non_dict_graph_returns_empty_proposal(self) -> None:
        # Absent/empty-dict graph coerces to {} (still a dict, BFS runs).
        # Only a TRUTHY non-dict (e.g. a list) trips the early-return guard.
        p = _p(tag_propagation_node({"tag_propagation_input": {
            "source_ueid": _A, "tags": ["p0"], "graph": ["not", "a", "dict"],
        }}))
        assert p["target_ueids"] == []
        assert "missing" in p["reason"]

    def test_single_node_graph_has_no_targets(self) -> None:
        p = _p(tag_propagation_node({"tag_propagation_input": {
            "source_ueid": _A, "tags": ["weekly"], "graph": {_A: []},
        }}))
        assert p["target_ueids"] == []
        assert p["source_ueid"] == _A
        assert "0 reachable" in p["reason"]

    def test_linear_graph_walks_chain(self) -> None:
        p = _p(tag_propagation_node({"tag_propagation_input": {
            "source_ueid": _A, "tags": ["p0"], "graph": {_A: [_B], _B: [_D]},
        }}))
        assert p["target_ueids"] == [_B, _D]

    def test_diamond_graph_walks_all_branches(self) -> None:
        p = _p(tag_propagation_node({"tag_propagation_input": {
            "source_ueid": _A, "tags": ["p0"],
            "graph": {_A: [_B, _C2], _B: [_D], _C2: [_D]},
        }}))
        assert p["target_ueids"] == [_B, _C2, _D]

    def test_two_node_cycle_target_is_other(self) -> None:
        # Visit-set prevents re-enqueue; source excluded; other survives.
        p = _p(tag_propagation_node({"tag_propagation_input": {
            "source_ueid": _A, "tags": ["p0"], "graph": {_A: [_B], _B: [_A]},
        }}))
        assert p["target_ueids"] == [_B]

    def test_targets_sorted_deterministically(self) -> None:
        p = _p(tag_propagation_node({"tag_propagation_input": {
            "source_ueid": _A,
            "tags": ["p0", "p0", "q0"],  # also test dedupe
            "graph": {_A: ["z", "x", "y", "w"]},
        }}))
        assert p["target_ueids"] == ["w", "x", "y", "z"]
        assert p["tags"] == ["p0", "q0"]

    def test_bfs_visit_cap_terminates_on_large_graph(self) -> None:
        children = [f"n{i:04d}" for i in range(600)]
        p = _p(tag_propagation_node({"tag_propagation_input": {
            "source_ueid": _A, "tags": ["p0"], "graph": {_A: children},
        }}))
        assert isinstance(p["target_ueids"], list)
        assert _A not in p["target_ueids"]
        assert p["target_ueids"] == sorted(p["target_ueids"])
        assert 0 < len(p["target_ueids"]) < len(children)


class TestDepGraph:
    """Cluster-prefix dep inference with DFS cycle detection."""

    def test_empty_project_prefix_returns_empty_proposal(self) -> None:
        p = _p(dep_graph_node({}))
        assert p["action"] == "add_deps"
        assert p["from_ueid"] is None
        assert p["to_ueids"] == []
        assert "missing" in p["reason"]

    def test_missing_tasks_returns_empty_proposal(self) -> None:
        # tasks=None coerces to {} via `or {}`; isinstance({}, dict)=True,
        # so we fall through to the "no safe additions" path (still empty).
        p = _p(dep_graph_node({"dep_graph_input": {"project_prefix": _C}}))
        assert p["from_ueid"] is None
        assert p["to_ueids"] == []

    def test_tasks_not_in_cluster_are_excluded(self) -> None:
        p = _p(dep_graph_node({"dep_graph_input": {
            "project_prefix": _C,
            "tasks": {"other:cluster:0001": {}, "another:prj:0002": {}},
        }}))
        assert p["from_ueid"] is None
        assert p["to_ueids"] == []

    def test_two_task_cluster_proposes_both_ways(self) -> None:
        out = dep_graph_node({"dep_graph_input": {
            "project_prefix": _C, "tasks": {_A: {}, _B: {}},
        }})
        p = _p(out)
        assert p["from_ueid"] == _A
        assert p["to_ueids"] == [_B]
        assert len(out["proposals"]) == 2

    def test_three_task_cluster_each_proposes_others(self) -> None:
        out = dep_graph_node({"dep_graph_input": {
            "project_prefix": _C, "tasks": {_A: {}, _B: {}, _C2: {}},
        }})
        p = _p(out)
        assert p["from_ueid"] == _A
        assert p["to_ueids"] == [_B, _C2]
        assert len(out["proposals"]) == 3
        assert sorted(pr["from_ueid"] for pr in out["proposals"]) == [_A, _B, _C2]

    def test_existing_deps_are_respected(self) -> None:
        # existing_deps={a:[b]} in 3-task cluster:
        #   a→[c]   (b already linked)
        #   b→[a,c] (would cycle via a→b; SKIPPED)
        #   c→[a,b] (no cycle, kept)
        out = dep_graph_node({"dep_graph_input": {
            "project_prefix": _C,
            "tasks": {_A: {}, _B: {}, _C2: {}},
            "existing_deps": {_A: [_B]},
        }})
        p = _p(out)
        assert p["from_ueid"] == _A
        assert p["to_ueids"] == [_C2]
        src_to_targets = {pr["from_ueid"]: pr["to_ueids"] for pr in out["proposals"]}
        assert src_to_targets[_C2] == [_A, _B]

    def test_cycle_detection_skips_cyclic_proposal(self) -> None:
        # existing_deps={a:[b]} in 2-task cluster:
        #   a: candidates {} (b already linked) → SKIP
        #   b: candidates [a] → cycle (b→a→b)  → SKIP
        # proposals=[] → "no safe additions" fallthrough.
        p = _p(dep_graph_node({"dep_graph_input": {
            "project_prefix": _C,
            "tasks": {_A: {}, _B: {}},
            "existing_deps": {_A: [_B]},
        }}))
        assert p["from_ueid"] is None
        assert p["to_ueids"] == []
        assert "no safe additions" in p["reason"]
        assert "skipped cycles" in p["reason"]

    def test_cluster_prefix_match_filters_other_clusters(self) -> None:
        other = "other:cluster:9999"
        out = dep_graph_node({"dep_graph_input": {
            "project_prefix": _C, "tasks": {_A: {}, _B: {}, other: {}},
            "existing_deps": {},
        }})
        p = _p(out)
        assert p["from_ueid"] == _A
        assert p["to_ueids"] == [_B]
        for pr in out["proposals"]:
            assert other not in pr["to_ueids"]


class TestGanttSuggest:
    """Kahn's topological sort + priority weighting + batching."""

    def test_empty_tasks_returns_empty_proposal(self) -> None:
        p = _p(gantt_suggest_node({}))
        assert p["action"] == "reorder"
        assert p["suggestion"] == []
        assert p["batches"] == []
        assert "missing" in p["reason"]

    def test_single_task_single_batch(self) -> None:
        p = _p(gantt_suggest_node({"gantt_input": {
            "tasks": {_A: {"priority": 1, "deps": []}},
        }}))
        assert p["suggestion"] == [_A]
        assert p["batches"] == [[_A]]

    def test_linear_chain_three_batches(self) -> None:
        # a→b→c: b depends on a, c depends on b (a precedes b precedes c).
        p = _p(gantt_suggest_node({"gantt_input": {
            "tasks": {
                _A: {"priority": 1, "deps": []},
                _B: {"priority": 1, "deps": [_A]},
                _C2: {"priority": 1, "deps": [_B]},
            },
        }}))
        assert p["suggestion"] == [_A, _B, _C2]
        assert p["batches"] == [[_A], [_B], [_C2]]

    def test_diamond_three_batches_parallel_middle(self) -> None:
        # Diamond a→{b,c}→d. Both b/c have priority 1; alphabetical
        # tiebreak means b precedes c in the parallel batch.
        p = _p(gantt_suggest_node({"gantt_input": {
            "tasks": {
                _A: {"priority": 1, "deps": []},
                _B: {"priority": 1, "deps": [_A]},
                _C2: {"priority": 1, "deps": [_A]},
                _D: {"priority": 1, "deps": [_B, _C2]},
            },
        }}))
        assert p["suggestion"] == [_A, _B, _C2, _D]
        assert p["batches"] == [[_A], [_B, _C2], [_D]]
        assert p["unscheduled"] == []

    def test_priority_tiebreak_emits_lower_value_first(self) -> None:
        # No deps → all runnable. Smaller priority value = more important.
        p = _p(gantt_suggest_node({"gantt_input": {
            "tasks": {
                _A: {"priority": 1, "deps": []},
                _B: {"priority": 2, "deps": []},
                _C2: {"priority": 3, "deps": []},
            },
        }}))
        assert p["suggestion"] == [_A, _B, _C2]
        assert p["batches"] == [[_A, _B, _C2]]

    def test_cycle_detection_unscheduled(self) -> None:
        # a→b→a: both in_degree=1; heap never seeded → all unscheduled.
        p = _p(gantt_suggest_node({"gantt_input": {
            "tasks": {
                _A: {"priority": 1, "deps": [_B]},
                _B: {"priority": 1, "deps": [_A]},
            },
        }}))
        assert p["suggestion"] == []
        assert p["batches"] == []
        assert sorted(p["unscheduled"]) == [_A, _B]
        assert "cycle" in p["reason"]

    def test_dep_outside_scope_is_ignored(self) -> None:
        # external_x dropped via `set(deps[u]) & in_scope`.
        p = _p(gantt_suggest_node({"gantt_input": {
            "tasks": {
                _A: {"priority": 1, "deps": ["external_x"]},
                _B: {"priority": 1, "deps": [_A]},
            },
        }}))
        assert p["suggestion"] == [_A, _B]
        assert p["batches"] == [[_A], [_B]]

    def test_deterministic_output_for_same_input(self) -> None:
        state = {"gantt_input": {"tasks": {
            _A: {"priority": 2, "deps": []},
            _B: {"priority": 1, "deps": [_A]},
            _C2: {"priority": 3, "deps": [_A]},
            _D: {"priority": 1, "deps": [_B, _C2]},
        }}}
        p1 = _p(gantt_suggest_node(state))
        p2 = _p(gantt_suggest_node(state))
        # Strict equality — no timestamps / random IDs / hidden state.
        assert p1 == p2
        assert p1["suggestion"] == [_A, _B, _C2, _D]


def test_nodes_do_not_mutate_input_state() -> None:
    """Each node must return a fresh dict (no shared state mutation)."""
    payload = {"source_ueid": _A, "tags": ["p0"], "graph": {_A: [_B], _B: []}}
    state_in = {"tag_propagation_input": payload}
    snapshot = dict(state_in)
    out = tag_propagation_node(state_in)
    assert out is not state_in
    assert state_in == snapshot  # input untouched