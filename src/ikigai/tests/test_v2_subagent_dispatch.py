"""W4.4 — Sub-agent dispatch node (B-N10) tests.

Per ADR-026 (sub-agent dispatch protocol):
- S1 Spawn: dispatch_plan is read from state and validated per spec
- S2 Context propagation: identity fields + dispatch_context; NEVER error_*
- S3 Collection: merge strategies (replace / merge_dict / append_list / reduce_add)
- S4 Termination: success / partial / failure / timeout
- S5 Failure isolation: parent's error_type is NEVER set by child failures

All tests use a mock _invoke_subagent to avoid real Claude cost.
The graph is only built in the 11-node-graph test (no real invocation).

These tests are the canonical regression suite for the dispatch protocol;
adding any new spec field requires extending test_validate_spec_*.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Path setup — conftest.py also inserts these but tests may run in isolation.
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_IKIGAI_SRC = _THIS.parent.parent / "src"  # <repo-root>/src/ikigai/src/
_REPO_ROOT = _THIS.parent.parent.parent.parent
_SRC_ROOT = _REPO_ROOT / "src"
for _p in (str(_REPO_ROOT), str(_SRC_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_IKIGAI_SRC) not in sys.path:
    sys.path.append(str(_IKIGAI_SRC))


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


def _stub_parent_state(**overrides) -> dict:
    """Build a minimal parent state dict for dispatch_sub_agents tests."""
    base = {
        "cycle_id": "parent-001",
        "cycle_start": "2026-09-04",
        "cycle_end": "2026-09-11",
        "iteration": 0,
        "actor": "user",
        # S2.4 — parent error channel MUST NOT propagate to children.
        "error_type": "ParentError",
        "error_message": "should be stripped before child invocation",
    }
    base.update(overrides)
    return base


def _stub_spec(**overrides) -> dict:
    """Build a valid SubAgentSpec; tests override fields to test edge cases."""
    base = {
        "sub_agent_id": "sa:demo:a1b2c3d4:e5f6a7b8",
        "entry_point": "observe",
        "dispatch_context": {"actor": "agent"},
        "timeout_s": 5.0,
        "merge_strategy": "replace",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Acceptance criterion 1 — 11-node graph (dispatch_sub_agents added to NODES)
# ---------------------------------------------------------------------------


def test_make_v2_graph_has_11_nodes() -> None:
    """make_v2_graph returns an 11-node graph (10 → 11 after W4.4)."""
    from agents.v2.graph import NODES, make_v2_graph

    assert len(NODES) == 11, f"Expected 11 nodes, got {len(NODES)}"
    assert "dispatch_sub_agents" in NODES
    # Verify ordering — dispatch_sub_agents is the 11th node in tuple position 10
    assert NODES.index("dispatch_sub_agents") == 9

    graph = make_v2_graph(checkpoint_db=":memory:")
    # LangGraph compiled graph has a `.nodes` mapping (dict of name → runnable)
    # of the nodes added to the builder. The `error` node + 11 named nodes = 12.
    assert "dispatch_sub_agents" in graph.nodes
    # Confirm both surface_intentions and commit remain reachable.
    assert "commit" in graph.nodes
    assert "surface_intentions" in graph.nodes


def test_nodes_tuple_includes_dispatch_in_correct_position() -> None:
    """NODES tuple is exactly 11 elements with dispatch_sub_agents as the 10th."""
    from agents.v2.graph import NODES

    expected = (
        "observe",
        "score_vectors",
        "heuristics",
        "balance",
        "decompose",
        "plan",
        "tag_and_persist",
        "reflect",
        "commit",
        "dispatch_sub_agents",
        "surface_intentions",
    )
    assert NODES == expected, f"NODES mismatch: {NODES}"


# ---------------------------------------------------------------------------
# Acceptance criterion 2 — Mock sub-agent (avoid real Claude cost)
# ---------------------------------------------------------------------------


def test_mock_subagent_returns_success() -> None:
    """Sub-agent returns status='success' → dispatch succeeds; parent absorbs outputs."""
    from agents.v2 import subgraph

    spec = _stub_spec(entry_point="observe")
    parent_state = _stub_parent_state()

    mock_result = subgraph.SubAgentResult(
        sub_agent_id=spec["sub_agent_id"],
        entry_point="observe",
        status="success",
        duration_s=0.1,
        fields_written=["vector_scores"],
        outputs={"vector_scores": {"passion": 0.9, "skill": 0.8}},
    )

    with mock.patch.object(
        subgraph,
        "_invoke_subagent",
        return_value=mock_result,
    ) as m_invoke:
        updates = subgraph.dispatch_sub_agents(
            {"dispatch_plan": [spec], **parent_state},
        )

    assert m_invoke.call_count == 1
    assert updates["last_step"] == "dispatch_sub_agents"
    assert len(updates["sub_agent_results"]) == 1
    assert updates["sub_agent_results"][0]["status"] == "success"
    # Output merged into parent update via 'replace' strategy
    assert updates["vector_scores"] == {"passion": 0.9, "skill": 0.8}
    # dispatch_plan cleared (ADR-027 R5.13 — ephemeral)
    assert updates["dispatch_plan"] == []


def test_mock_subagent_partial() -> None:
    """Sub-agent returns status='partial' → parent continues; outputs merged."""
    from agents.v2 import subgraph

    spec = _stub_spec(entry_point="observe")
    mock_result = subgraph.SubAgentResult(
        sub_agent_id=spec["sub_agent_id"],
        entry_point="observe",
        status="partial",
        duration_s=0.2,
        fields_written=["user_suggestions"],
        outputs={"user_suggestions": ["suggestion-1", "suggestion-2"]},
    )
    with mock.patch.object(subgraph, "_invoke_subagent", return_value=mock_result):
        updates = subgraph.dispatch_sub_agents(
            {"dispatch_plan": [spec], **_stub_parent_state()},
        )

    result = updates["sub_agent_results"][0]
    assert result["status"] == "partial"
    # Partial outputs ARE merged (per ADR-026 S4.2 — continue with merged + warnings)
    assert updates["user_suggestions"] == ["suggestion-1", "suggestion-2"]


# ---------------------------------------------------------------------------
# Acceptance criterion 3 — Failure modes (timeout, recursion, partial, invalid)
# ---------------------------------------------------------------------------


def test_subagent_timeout_yields_status_timeout() -> None:
    """Sub-agent exceeds timeout → status='timeout'; parent continues (S4.4)."""
    from agents.v2 import subgraph

    spec = _stub_spec(timeout_s=1.0)
    # Mock _invoke_subagent to raise TimeoutError — the function catches and
    # converts to SubAgentResult per the S5 failure-isolation contract.
    with mock.patch.object(
        subgraph,
        "_invoke_subagent",
        side_effect=TimeoutError("wall-clock exceeded"),
    ):
        updates = subgraph.dispatch_sub_agents(
            {"dispatch_plan": [spec], **_stub_parent_state()},
        )

    result = updates["sub_agent_results"][0]
    assert result["status"] == "timeout"
    assert result["error"]["type"] == "TimeoutError"
    # Parent error_type is NOT set (ADR-026 R5 failure isolation).
    assert "error_type" not in updates


def test_recursion_depth_blocked() -> None:
    """Parent depth >= SUBAGENT_MAX_DISPATCH_DEPTH → all dispatches fail."""
    from agents.v2 import subgraph

    # Use thread_id encoding to signal depth=2 (max is 2 → +1=3 would exceed)
    spec = _stub_spec(entry_point="observe")
    parent_state = _stub_parent_state(thread_id="agent-weekly-a3f19c2d-d2")

    with mock.patch.object(subgraph, "_invoke_subagent") as m_invoke:
        updates = subgraph.dispatch_sub_agents(
            {"dispatch_plan": [spec], **parent_state},
        )

    # Recursion guard MUST prevent the invocation — mock should not be called.
    m_invoke.assert_not_called()
    result = updates["sub_agent_results"][0]
    assert result["status"] == "failure"
    assert result["error"]["type"] == "RecursionLimitExceeded"
    assert "recursion" in result["error"]["type"].lower()


def test_recursion_depth_blocked_via_state_field() -> None:
    """Same guard via state['dispatch_depth'] field (no thread_id)."""
    from agents.v2 import subgraph

    spec = _stub_spec()
    parent_state = _stub_parent_state(dispatch_depth=2)
    # Remove the thread_id so the path uses the dispatch_depth field
    parent_state.pop("thread_id", None)

    with mock.patch.object(subgraph, "_invoke_subagent") as m_invoke:
        updates = subgraph.dispatch_sub_agents(
            {"dispatch_plan": [spec], **parent_state},
        )
    m_invoke.assert_not_called()
    assert updates["sub_agent_results"][0]["status"] == "failure"


def test_partial_continues_parent_with_warnings() -> None:
    """1 sub-agent success + 1 sub-agent partial → parent continues with merged."""
    from agents.v2 import subgraph

    spec_a = _stub_spec(sub_agent_id="sa:demo:11111111:11111111", entry_point="observe")
    spec_b = _stub_spec(sub_agent_id="sa:demo:22222222:22222222", entry_point="balance")

    success = subgraph.SubAgentResult(
        sub_agent_id=spec_a["sub_agent_id"],
        entry_point="observe",
        status="success",
        duration_s=0.1,
        fields_written=["vector_scores"],
        outputs={"vector_scores": {"passion": 0.7}},
    )
    partial = subgraph.SubAgentResult(
        sub_agent_id=spec_b["sub_agent_id"],
        entry_point="balance",
        status="partial",
        duration_s=0.2,
        fields_written=["user_suggestions"],
        outputs={"user_suggestions": ["s1"]},
        error={"type": "PartialError", "message": "incomplete"},
    )

    with mock.patch.object(
        subgraph,
        "_invoke_subagent",
        side_effect=[success, partial],
    ):
        updates = subgraph.dispatch_sub_agents(
            {"dispatch_plan": [spec_a, spec_b], **_stub_parent_state()},
        )

    assert len(updates["sub_agent_results"]) == 2
    statuses = {r["status"] for r in updates["sub_agent_results"]}
    assert statuses == {"success", "partial"}
    # Both outputs merged into parent
    assert "vector_scores" in updates
    assert updates["user_suggestions"] == ["s1"]
    # partial child has error dict (typed via TypedDict)
    assert updates["sub_agent_results"][1]["error"]["type"] == "PartialError"


# ---------------------------------------------------------------------------
# ADR-026 S2.4 — Error channel isolation
# ---------------------------------------------------------------------------


class _CapturingMock:
    """Capture the context dict passed to _invoke_subagent for assertions."""

    def __init__(self, return_value=None):
        self.calls: list[tuple] = []
        self._return = return_value

    def __call__(self, spec, initial_state, timeout_s):
        self.calls.append((spec, initial_state, timeout_s))
        return self._return


def test_s24_error_channel_isolation() -> None:
    """Parent's error_* fields are NOT propagated to sub-agent context (S2.4)."""
    from agents.v2 import subgraph

    spec = _stub_spec()
    capture = _CapturingMock(
        return_value=subgraph.SubAgentResult(
            sub_agent_id=spec["sub_agent_id"],
            entry_point="observe",
            status="success",
            duration_s=0.1,
            fields_written=[],
            outputs={},
        ),
    )

    parent_state = _stub_parent_state(
        error_type="ParentError",
        error_message="must be stripped",
        traceback_str="traceback contents",
        error_traceback="error traceback contents",
    )

    with mock.patch.object(subgraph, "_invoke_subagent", side_effect=capture):
        subgraph.dispatch_sub_agents({"dispatch_plan": [spec], **parent_state})

    # capture.calls[0] is (spec, initial_state, timeout_s)
    assert len(capture.calls) == 1, f"Expected 1 call, got {len(capture.calls)}"
    _, initial_state, _ = capture.calls[0]

    # Per S2.4 — error_* fields MUST NOT appear in child initial_state
    for forbidden in ("error_type", "error_message", "traceback_str", "error_traceback"):
        assert forbidden not in initial_state, (
            f"S2.4 violation — {forbidden!r} leaked to sub-agent context. "
            f"initial_state keys: {sorted(initial_state.keys())}"
        )
    # originating_node + commit_summary are also error-channel fields
    assert "originating_node" not in initial_state
    assert "commit_summary" not in initial_state


def test_s22_identity_fields_always_propagate() -> None:
    """Identity fields (cycle_id, cycle_start, cycle_end, iteration, actor) ALWAYS propagate (S2.2)."""
    from agents.v2 import subgraph

    spec = _stub_spec()
    capture = _CapturingMock(
        return_value=subgraph.SubAgentResult(
            sub_agent_id=spec["sub_agent_id"],
            entry_point="observe",
            status="success",
            duration_s=0.1,
            fields_written=[],
            outputs={},
        ),
    )

    parent_state = _stub_parent_state(
        cycle_id="q3-2026",
        cycle_start="2026-07-01",
        cycle_end="2026-09-30",
        iteration=42,
    )

    with mock.patch.object(subgraph, "_invoke_subagent", side_effect=capture):
        subgraph.dispatch_sub_agents({"dispatch_plan": [spec], **parent_state})

    _, initial_state, _ = capture.calls[0]
    # Identity fields must be in child
    assert initial_state["cycle_id"] == "q3-2026"
    assert initial_state["cycle_start"] == "2026-07-01"
    assert initial_state["cycle_end"] == "2026-09-30"
    assert initial_state["iteration"] == 42
    # actor is FORCED to "agent" (never user from sub-agent routes — ADR-025 R2)
    assert initial_state["actor"] == "agent"


def test_dispatch_context_fields_propagate() -> None:
    """Fields in dispatch_context dict are propagated to child (S2.3)."""
    from agents.v2 import subgraph

    spec = _stub_spec(
        dispatch_context={
            "cycle_id": "should-be-overridden",  # identity field — skipped
            "vault_path": "ikigai/test/demo.md",
            "proposed_entity": {"tier": "daily", "title": "demo"},
            "error_type": "should-be-stripped",  # error channel — skipped
        },
    )
    capture = _CapturingMock(
        return_value=subgraph.SubAgentResult(
            sub_agent_id=spec["sub_agent_id"],
            entry_point="observe",
            status="success",
            duration_s=0.1,
            fields_written=[],
            outputs={},
        ),
    )
    with mock.patch.object(subgraph, "_invoke_subagent", side_effect=capture):
        subgraph.dispatch_sub_agents({"dispatch_plan": [spec], **_stub_parent_state()})

    _, initial_state, _ = capture.calls[0]
    assert initial_state["vault_path"] == "ikigai/test/demo.md"
    assert initial_state["proposed_entity"] == {"tier": "daily", "title": "demo"}
    # cycle_id was in dispatch_context but is identity field — taken from parent
    assert initial_state["cycle_id"] == "parent-001"
    # error_type was in dispatch_context but is error channel — STRIPPED
    assert "error_type" not in initial_state


# ---------------------------------------------------------------------------
# UEID validation (ADR-014 + ADR-026 R4)
# ---------------------------------------------------------------------------


def test_invalid_ueid_rejected() -> None:
    """sub_agent_id that is NOT a 4-part UEID is rejected with ValueError status."""
    from agents.v2 import subgraph

    spec = _stub_spec(sub_agent_id="not-a-ueid-format")
    with mock.patch.object(subgraph, "_invoke_subagent") as m_invoke:
        updates = subgraph.dispatch_sub_agents(
            {"dispatch_plan": [spec], **_stub_parent_state()},
        )
    m_invoke.assert_not_called()
    result = updates["sub_agent_results"][0]
    assert result["status"] == "failure"
    assert "UEID" in result["error"]["message"] or "ueid" in result["error"]["message"]


def test_5part_ueid_rejected() -> None:
    """5-part UEIDs are REJECTED (canonical is 4-part per ADR-014)."""
    from agents.v2 import subgraph

    spec = _stub_spec(sub_agent_id="tsk:demo:abc:00000000-0000-0000-0000-000000000000:deadbeef")
    with mock.patch.object(subgraph, "_invoke_subagent") as m_invoke:
        updates = subgraph.dispatch_sub_agents(
            {"dispatch_plan": [spec], **_stub_parent_state()},
        )
    m_invoke.assert_not_called()
    assert updates["sub_agent_results"][0]["status"] == "failure"


def test_invalid_entry_point_rejected() -> None:
    """entry_point NOT in NODES is rejected (R1)."""
    from agents.v2 import subgraph

    spec = _stub_spec(entry_point="not_a_real_node")
    with mock.patch.object(subgraph, "_invoke_subagent") as m_invoke:
        updates = subgraph.dispatch_sub_agents(
            {"dispatch_plan": [spec], **_stub_parent_state()},
        )
    m_invoke.assert_not_called()
    result = updates["sub_agent_results"][0]
    assert result["status"] == "failure"
    assert "NODES" in result["error"]["message"]


# ---------------------------------------------------------------------------
# S3 — Merge strategies (unit-level)
# ---------------------------------------------------------------------------


def test_merge_strategy_replace() -> None:
    """merge_strategy='replace' overwrites parent fields with child outputs."""
    from agents.v2 import subgraph

    updates: dict = {"existing": "parent-value"}
    subgraph._merge_result(
        updates,
        {"new_key": "new-value", "existing": "child-value"},
        "replace",
    )
    assert updates["existing"] == "child-value"
    assert updates["new_key"] == "new-value"


def test_merge_strategy_merge_dict() -> None:
    """merge_strategy='merge_dict' deep-merges dicts; scalars replace."""
    from agents.v2 import subgraph

    updates: dict = {"cfg": {"a": 1, "b": 2}, "scalar": "old"}
    subgraph._merge_result(
        updates,
        {"cfg": {"b": 99, "c": 3}, "scalar": "new"},
        "merge_dict",
    )
    assert updates["cfg"] == {"a": 1, "b": 99, "c": 3}
    assert updates["scalar"] == "new"


def test_merge_strategy_append_list() -> None:
    """merge_strategy='append_list' concatenates lists."""
    from agents.v2 import subgraph

    updates: dict = {"corrections": ["c1", "c2"]}
    subgraph._merge_result(
        updates,
        {"corrections": ["c3"]},
        "append_list",
    )
    assert updates["corrections"] == ["c1", "c2", "c3"]


def test_merge_strategy_reduce_add() -> None:
    """merge_strategy='reduce_add' sums numeric values."""
    from agents.v2 import subgraph

    updates: dict = {"q_he_score": 0.5}
    subgraph._merge_result(
        updates,
        {"q_he_score": 0.3},
        "reduce_add",
    )
    assert updates["q_he_score"] == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# No-op dispatch (empty plan)
# ---------------------------------------------------------------------------


def test_empty_dispatch_plan_is_noop() -> None:
    """Empty dispatch_plan = no-op; passthrough with last_step marker."""
    from agents.v2 import subgraph

    updates = subgraph.dispatch_sub_agents(_stub_parent_state())
    assert updates == {"last_step": "dispatch_sub_agents"}

    updates = subgraph.dispatch_sub_agents({**_stub_parent_state(), "dispatch_plan": []})
    assert updates == {"last_step": "dispatch_sub_agents"}


def test_dispatch_plan_with_multiple_children_collects_all() -> None:
    """All children are dispatched; all results recorded."""
    from agents.v2 import subgraph

    specs = [
        _stub_spec(sub_agent_id="sa:demo:11111111:11111111", entry_point="observe"),
        _stub_spec(sub_agent_id="sa:demo:22222222:22222222", entry_point="balance"),
        _stub_spec(sub_agent_id="sa:demo:33333333:33333333", entry_point="heuristics"),
    ]

    def fake_invoke(spec, state, timeout):
        return subgraph.SubAgentResult(
            sub_agent_id=spec["sub_agent_id"],
            entry_point=spec["entry_point"],
            status="success",
            duration_s=0.05,
            fields_written=[],
            outputs={"marker": spec["entry_point"]},
        )

    with mock.patch.object(subgraph, "_invoke_subagent", side_effect=fake_invoke):
        updates = subgraph.dispatch_sub_agents(
            {"dispatch_plan": specs, **_stub_parent_state()},
        )

    assert len(updates["sub_agent_results"]) == 3
    # 'replace' merge — last child's marker wins
    assert updates["marker"] == "heuristics"
    # dispatch_plan cleared
    assert updates["dispatch_plan"] == []


# ---------------------------------------------------------------------------
# SubAgentSpec validation (UEID + NODES + timeout)
# ---------------------------------------------------------------------------


def test_validate_spec_accepts_valid_spec() -> None:
    """A well-formed SubAgentSpec passes validation."""
    from agents.v2 import subgraph

    spec = _stub_spec()
    err = subgraph._validate_spec(spec)
    assert err is None


def test_validate_spec_rejects_non_positive_timeout() -> None:
    """Non-positive timeout is rejected."""
    from agents.v2 import subgraph

    spec = _stub_spec(timeout_s=0.0)
    err = subgraph._validate_spec(spec)
    assert err is not None
    assert "timeout_s" in err

    spec = _stub_spec(timeout_s=-1.5)
    err = subgraph._validate_spec(spec)
    assert err is not None
    assert "timeout_s" in err


def test_validate_spec_rejects_invalid_merge_strategy() -> None:
    """merge_strategy outside the allowed set is rejected."""
    from agents.v2 import subgraph

    spec = _stub_spec(merge_strategy="merge_dict")  # type: ignore[typeddict-item]
    err = subgraph._validate_spec(spec)
    assert err is None  # merge_dict IS valid

    spec = _stub_spec(merge_strategy="invalid_strategy")  # type: ignore[typeddict-item]
    err = subgraph._validate_spec(spec)
    assert err is not None
    assert "merge_strategy" in err
