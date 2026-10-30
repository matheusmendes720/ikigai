"""Tests for the three taskdog-graph proposal nodes (M256).

Covers:
  - tag_propagation_node: BFS through dep graph, deterministic order
  - dep_graph_node: cluster-grouping + cycle rejection
  - gantt_suggest_node: topological sort + parallel-group batching

All nodes are pure-Python — no MCP, no LLM, no I/O — so tests call
them directly with hand-crafted state dicts.

Drift gate: each node file < 200 LOC (asserted in test_size_gate).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup — match the pattern used by test_v2_graph_smoke.py.
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent.parent.parent  # <repo-root>
_IKIGAI_SRC = _REPO_ROOT / "src" / "ikigai" / "src"

for _p in [str(_REPO_ROOT), str(_REPO_ROOT / "src")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_IKIGAI_SRC) not in sys.path:
    sys.path.append(str(_IKIGAI_SRC))


# ---------------------------------------------------------------------------
# Imports — done after path setup.
# ---------------------------------------------------------------------------
from src.ikigai.src.agents.v2.nodes.dep_graph import (  # noqa: E402
    _detect_cycle as _detect_cycle_helper,
)
from src.ikigai.src.agents.v2.nodes.dep_graph import (  # noqa: E402
    dep_graph_node as _dep_graph,
)
from src.ikigai.src.agents.v2.nodes.gantt_suggest import (  # noqa: E402
    gantt_suggest_node as _gantt,
)
from src.ikigai.src.agents.v2.nodes.tag_propagation import (  # noqa: E402
    tag_propagation_node as _tag_prop,
)

tag_propagation_node = _tag_prop
dep_graph_node = _dep_graph
gantt_suggest_node = _gantt


# ---------------------------------------------------------------------------
# tag_propagation_node
# ---------------------------------------------------------------------------
class TestTagPropagationNode:
    def test_returns_proposal_with_correct_shape(self) -> None:
        state = {
            "tag_propagation_input": {
                "source_ueid": "ts:prj:abcd:0001",
                "tags": ["weekly", "p0"],
                "graph": {
                    "ts:prj:abcd:0001": ["ts:prj:abcd:0002"],
                    "ts:prj:abcd:0002": ["ts:prj:abcd:0003"],
                },
            }
        }
        out = tag_propagation_node(state)
        prop = out["proposal"]
        assert prop["action"] == "tag_propagate"
        assert prop["source_ueid"] == "ts:prj:abcd:0001"
        assert prop["tags"] == ["p0", "weekly"]  # sorted, deduped
        assert prop["target_ueids"] == [
            "ts:prj:abcd:0002",
            "ts:prj:abcd:0003",
        ]
        assert prop["node"] == "tag_propagation"
        assert out["last_step"] == "tag_propagation"

    def test_excludes_source_ueid_from_targets(self) -> None:
        state = {
            "tag_propagation_input": {
                "source_ueid": "ts:prj:abcd:0001",
                "tags": ["x"],
                "graph": {
                    "ts:prj:abcd:0001": ["ts:prj:abcd:0001"],  # self-loop
                },
            }
        }
        out = tag_propagation_node(state)
        assert out["proposal"]["target_ueids"] == []  # self excluded

    def test_handles_cycle_in_graph(self) -> None:
        # 0001 -> 0002 -> 0001 (cycle). BFS must terminate.
        state = {
            "tag_propagation_input": {
                "source_ueid": "ts:prj:abcd:0001",
                "tags": ["y"],
                "graph": {
                    "ts:prj:abcd:0001": ["ts:prj:abcd:0002"],
                    "ts:prj:abcd:0002": ["ts:prj:abcd:0001"],
                    "ts:prj:abcd:0003": [],  # disconnected
                },
            }
        }
        out = tag_propagation_node(state)
        # BFS visits both 0001 and 0002, plus 0003 if reachable from 0001.
        # 0003 is not in 0001's dep list, so it's NOT a target.
        assert out["proposal"]["target_ueids"] == ["ts:prj:abcd:0002"]

    def test_missing_input_returns_empty_proposal(self) -> None:
        out = tag_propagation_node({})
        assert out["proposal"]["action"] == "tag_propagate"
        assert out["proposal"]["target_ueids"] == []
        assert "missing" in out["proposal"]["reason"]

    def test_bfs_is_deterministic(self) -> None:
        # Multiple runs must yield identical proposals.
        state = {
            "tag_propagation_input": {
                "source_ueid": "ts:prj:abcd:0001",
                "tags": ["a", "b"],
                "graph": {
                    "ts:prj:abcd:0001": ["ts:prj:abcd:0002", "ts:prj:abcd:0003"],
                    "ts:prj:abcd:0002": ["ts:prj:abcd:0004"],
                    "ts:prj:abcd:0003": ["ts:prj:abcd:0004"],
                },
            }
        }
        out1 = tag_propagation_node(state)
        out2 = tag_propagation_node(dict(state))
        assert out1["proposal"]["target_ueids"] == out2["proposal"]["target_ueids"]


# ---------------------------------------------------------------------------
# dep_graph_node
# ---------------------------------------------------------------------------
class TestDepGraphNode:
    def test_proposes_deps_for_isolated_tasks_in_same_cluster(self) -> None:
        state = {
            "dep_graph_input": {
                "project_prefix": "ts:prj:abcd",
                "tasks": {
                    "ts:prj:abcd:0001": {"priority": 1},
                    "ts:prj:abcd:0002": {"priority": 2},
                    "ts:prj:abcd:0003": {"priority": 3},
                },
                "existing_deps": {},
            }
        }
        out = dep_graph_node(state)
        prop = out["proposal"]
        assert prop["action"] == "add_deps"
        assert prop["from_ueid"] in {
            "ts:prj:abcd:0001",
            "ts:prj:abcd:0002",
            "ts:prj:abcd:0003",
        }
        # Siblings must NOT include self.
        assert prop["from_ueid"] not in prop["to_ueids"]
        # Two siblings per isolated task.
        assert len(prop["to_ueids"]) == 2

    def test_rejects_proposal_that_would_create_cycle(self) -> None:
        # 0001 depends on 0002. If 0002 added 0001 as dep, cycle.
        state = {
            "dep_graph_input": {
                "project_prefix": "ts:prj:abcd",
                "tasks": {
                    "ts:prj:abcd:0001": {"priority": 1},
                    "ts:prj:abcd:0002": {"priority": 2},
                },
                "existing_deps": {
                    "ts:prj:abcd:0001": ["ts:prj:abcd:0002"],
                },
            }
        }
        out = dep_graph_node(state)
        # Either empty proposal (cycle rejected) or proposal only for the
        # non-cycling source. Verify no cycle exists in any proposed edge.
        for prop in out.get("proposals", [out["proposal"]]):
            if prop.get("from_ueid") is None:
                continue
            sim = {
                u: list(existing)
                for u, existing in state["dep_graph_input"]["existing_deps"].items()
            }
            sim[prop["from_ueid"]] = prop["to_ueids"]
            assert _detect_cycle_helper(sim, prop["from_ueid"]) is False

    def test_cycle_detect_helper_returns_true_on_cycle(self) -> None:
        graph = {"a": ["b"], "b": ["a"]}
        assert _detect_cycle_helper(graph, "a") is True
        assert _detect_cycle_helper(graph, "b") is True

    def test_cycle_detect_helper_returns_false_on_dag(self) -> None:
        graph = {"a": ["b"], "b": ["c"], "c": []}
        assert _detect_cycle_helper(graph, "a") is False

    def test_excludes_tasks_outside_project_cluster(self) -> None:
        state = {
            "dep_graph_input": {
                "project_prefix": "ts:prj:abcd",
                "tasks": {
                    "ts:prj:abcd:0001": {"priority": 1},
                    "ts:other:efgh:9999": {"priority": 1},  # other cluster
                },
                "existing_deps": {},
            }
        }
        out = dep_graph_node(state)
        # Only one in-cluster task; no candidate to add, so empty proposal.
        if out["proposal"]["from_ueid"] is None:
            assert out["proposal"]["to_ueids"] == []
        else:
            assert "ts:other:efgh:9999" not in out["proposal"]["to_ueids"]

    def test_skips_existing_deps(self) -> None:
        state = {
            "dep_graph_input": {
                "project_prefix": "ts:prj:abcd",
                "tasks": {
                    "ts:prj:abcd:0001": {"priority": 1},
                    "ts:prj:abcd:0002": {"priority": 2},
                },
                "existing_deps": {
                    "ts:prj:abcd:0001": ["ts:prj:abcd:0002"],
                },
            }
        }
        out = dep_graph_node(state)
        # 0001 already links to 0002, so it has nothing to propose.
        # 0002 also can't propose (only 1 sibling = itself).
        assert out["proposal"]["from_ueid"] is None or out["proposal"]["to_ueids"] == []

    def test_missing_input_returns_empty_proposal(self) -> None:
        out = dep_graph_node({})
        assert out["proposal"]["action"] == "add_deps"
        assert out["proposal"]["from_ueid"] is None
        assert "missing" in out["proposal"]["reason"]


# ---------------------------------------------------------------------------
# gantt_suggest_node
# ---------------------------------------------------------------------------
class TestGanttSuggestNode:
    def test_produces_valid_topological_order(self) -> None:
        # 0001 depends on 0002 depends on 0003. 0001 must come last.
        state = {
            "gantt_input": {
                "tasks": {
                    "ts:prj:abcd:0001": {
                        "priority": 1,
                        "deps": ["ts:prj:abcd:0002"],
                    },
                    "ts:prj:abcd:0002": {
                        "priority": 2,
                        "deps": ["ts:prj:abcd:0003"],
                    },
                    "ts:prj:abcd:0003": {"priority": 3, "deps": []},
                }
            }
        }
        out = gantt_suggest_node(state)
        prop = out["proposal"]
        assert prop["action"] == "reorder"
        suggestion = prop["suggestion"]
        # Topological: 0003 first, then 0002, then 0001.
        assert suggestion.index("ts:prj:abcd:0003") < suggestion.index("ts:prj:abcd:0002")
        assert suggestion.index("ts:prj:abcd:0002") < suggestion.index("ts:prj:abcd:0001")

    def test_priority_weight_orders_high_priority_first(self) -> None:
        # All deps satisfied. Lower priority value (= more important) first.
        state = {
            "gantt_input": {
                "tasks": {
                    "ts:prj:abcd:0001": {"priority": 5, "deps": []},
                    "ts:prj:abcd:0002": {"priority": 1, "deps": []},
                    "ts:prj:abcd:0003": {"priority": 3, "deps": []},
                }
            }
        }
        out = gantt_suggest_node(state)
        suggestion = out["proposal"]["suggestion"]
        assert suggestion[0] == "ts:prj:abcd:0002"  # priority 1
        assert suggestion[1] == "ts:prj:abcd:0003"  # priority 3
        assert suggestion[2] == "ts:prj:abcd:0001"  # priority 5

    def test_groups_independent_tasks_into_parallel_batches(self) -> None:
        # Three leaf tasks with no deps; they should be in batch 0.
        state = {
            "gantt_input": {
                "tasks": {
                    "ts:prj:abcd:0001": {"priority": 1, "deps": []},
                    "ts:prj:abcd:0002": {"priority": 2, "deps": []},
                    "ts:prj:abcd:0003": {"priority": 3, "deps": []},
                }
            }
        }
        out = gantt_suggest_node(state)
        batches = out["proposal"]["batches"]
        # First (and only) batch contains all three (after priority sort).
        assert len(batches) == 1
        assert sorted(batches[0]) == [
            "ts:prj:abcd:0001",
            "ts:prj:abcd:0002",
            "ts:prj:abcd:0003",
        ]

    def test_detects_cycle_and_excludes_culprits(self) -> None:
        # 0001 -> 0002 -> 0001 cycle.
        state = {
            "gantt_input": {
                "tasks": {
                    "ts:prj:abcd:0001": {
                        "priority": 1,
                        "deps": ["ts:prj:abcd:0002"],
                    },
                    "ts:prj:abcd:0002": {
                        "priority": 2,
                        "deps": ["ts:prj:abcd:0001"],
                    },
                    "ts:prj:abcd:0003": {"priority": 3, "deps": []},  # free
                }
            }
        }
        out = gantt_suggest_node(state)
        prop = out["proposal"]
        assert "ts:prj:abcd:0003" in prop["suggestion"]
        assert set(prop["unscheduled"]) == {
            "ts:prj:abcd:0001",
            "ts:prj:abcd:0002",
        }
        assert "cycle" in prop["reason"].lower()

    def test_ignores_deps_outside_scope(self) -> None:
        # 0001 depends on an out-of-scope ueid — must be treated as no dep.
        state = {
            "gantt_input": {
                "tasks": {
                    "ts:prj:abcd:0001": {
                        "priority": 1,
                        "deps": ["ts:other:efgh:9999"],
                    },
                    "ts:prj:abcd:0002": {"priority": 2, "deps": []},
                }
            }
        }
        out = gantt_suggest_node(state)
        # Both should be schedulable (the out-of-scope dep is ignored).
        assert sorted(out["proposal"]["suggestion"]) == [
            "ts:prj:abcd:0001",
            "ts:prj:abcd:0002",
        ]
        assert out["proposal"]["unscheduled"] == []

    def test_empty_input_returns_empty_proposal(self) -> None:
        out = gantt_suggest_node({})
        prop = out["proposal"]
        assert prop["action"] == "reorder"
        assert prop["suggestion"] == []
        assert prop["batches"] == []
        assert "missing" in prop["reason"].lower()


# ---------------------------------------------------------------------------
# Drift gate — each node file < 200 LOC.
# ---------------------------------------------------------------------------
class TestSizeGate:
    @pytest.mark.parametrize(
        ("filename", "limit"),
        [
            ("tag_propagation.py", 200),
            ("dep_graph.py", 200),
            ("gantt_suggest.py", 200),
        ],
    )
    def test_node_file_under_loc_cap(self, filename: str, limit: int) -> None:
        path = _REPO_ROOT / "src" / "ikigai" / "src" / "agents" / "v2" / "nodes" / filename
        line_count = sum(1 for _ in path.open(encoding="utf-8"))
        assert line_count < limit, (
            f"{filename} is {line_count} LOC (limit {limit}); split per <200 LOC drift gate"
        )
