"""v2 node isolation tests — flow/terminal nodes (synthetic state in/out).

Each v2 node is a pure-ish function: state_in -> state_out (LangGraph merges
the returned dict into state). These tests call the node functions directly
(no graph, no checkpointing) with minimal synthetic state and assert:

  - the call does not raise
  - the return value is a dict
  - the dict has the expected keys (each node's documented contract)
  - shape invariants hold (terminated=True for terminal nodes, etc.)

This file covers the FLOW / TERMINAL nodes: commit, decompose, error,
observe, reason_node, recall_node, surface_intentions.

The PROPOSAL-EMITTING nodes (dep_graph, gantt_suggest, tag_and_persist,
tag_propagation) live in test_v2_node_isolation_proposals.py.
The M12 STUB nodes (balance, heuristics, plan, reflect, score_vectors)
live in test_v2_node_isolation_stubs.py.
The 16-node smoke test (parametrized) lives in
test_v2_node_isolation_smoke.py.

Constraints:
  - DO NOT modify node code; tests are read-only over node contracts.
  - Mock external dependencies when the node would otherwise touch them.
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
_REPO_ROOT = _THIS.parent.parent.parent.parent  # <repo-root>
_SRC_ROOT = _REPO_ROOT / "src"
_IKIGAI_SRC = _THIS.parent.parent / "src"

for _p in [str(_REPO_ROOT), str(_SRC_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_IKIGAI_SRC) not in sys.path:
    sys.path.append(str(_IKIGAI_SRC))


def _base_state(**overrides: Any) -> dict[str, Any]:
    """Minimal IKIGAiStateDict with sensible defaults.

    OPEN-3 (2026-10-02): cycle_id / cycle_start / cycle_end / iteration were
    promoted to NotRequired on IKIGAiStateDict. Tests still pass them so
    commit_node's commit_summary has identifiable values.
    """
    state: dict[str, Any] = {
        "cycle_id": "iso-test-001",
        "cycle_start": "2026-10-02",
        "cycle_end": "2026-10-02",
        "iteration": 0,
        "user_input": None,
        "user_request": "",
        "context": {},
        "draft_proposal": {},
        "proposed_entity": None,
        "vault_path": None,
        "actor": "agent",
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# commit_node (M89 real: produces commit_summary, fires taskdog)
# ---------------------------------------------------------------------------
def test_commit_node_isolation_no_operations():
    """commit_node with no task.create operations returns dict + terminated=True."""
    from src.ikigai.src.agents.v2.nodes.commit import commit_node

    result = commit_node(_base_state())

    assert isinstance(result, dict)
    assert "COMMIT cycle=iso-test-001" in result["commit_summary"]
    assert result["terminated"] is True
    assert result["last_step"] == "commit"
    # Empty draft_proposal → no taskdog calls
    assert result["commit"]["taskdog_results"] == []


def test_commit_node_isolation_with_task_create(monkeypatch):
    """commit_node with task.create op invokes taskdog_create_task via bridge."""
    calls: list[str] = []

    class _FakeTaskdog:
        def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
            calls.append(payload.get("name", ""))
            return {"id": "fake-uuid", "name": payload.get("name", "")}

    # Patch the agents.tools module that commit_node resolves at call time.
    fake_tools = type(sys)("agents.tools")
    fake_tools.taskdog_create_task = _FakeTaskdog()
    monkeypatch.setitem(sys.modules, "agents.tools", fake_tools)

    state = _base_state(
        draft_proposal={
            "proposal_id": "ikigai:proposal:abc12345:short",
            "operations": [{"type": "task.create", "target": "isolation test task"}],
        }
    )
    from src.ikigai.src.agents.v2.nodes.commit import commit_node

    result = commit_node(state)

    assert calls == ["isolation test task"]
    assert result["commit"]["taskdog_results"][0]["ok"] is True
    assert result["terminated"] is True
    assert "proposal=ikigai:proposal:abc12345:short" in result["commit_summary"]


# ---------------------------------------------------------------------------
# decompose_node (mcp_bridge.ikigai_decompose; node catches + error_channel)
# ---------------------------------------------------------------------------
def test_decompose_node_isolation():
    """decompose_node catches unbound _server, returns error_channel gracefully."""
    from src.ikigai.src.agents.v2.nodes.decompose import decompose_node

    result = decompose_node(_base_state())

    assert isinstance(result, dict)
    assert "decompose" in result
    assert "error_channel" in result
    assert len(result["error_channel"]) >= 1
    assert "decompose" in result["error_channel"][0].lower()


# ---------------------------------------------------------------------------
# error_node (terminal: produces commit_summary + error fields)
# ---------------------------------------------------------------------------
def test_error_node_isolation():
    """error_node produces commit_summary naming the originating node."""
    from src.ikigai.src.agents.v2.nodes.error import error_node

    state = _base_state(
        originating_node="commit",
        error_type="RuntimeError",
        error_message="synthetic isolation failure",
        traceback_str="Traceback (most recent call last):\n  ...\nRuntimeError: x",
    )
    result = error_node(state)

    assert "ERROR in node 'commit'" in result["commit_summary"]
    assert "RuntimeError" in result["commit_summary"]
    assert result["terminated"] is True
    assert result["last_step"] == "error"
    assert result["originating_node"] == "commit"
    assert result["error_type"] == "RuntimeError"
    assert result["error_traceback"].startswith("Traceback")


def test_error_node_isolation_idempotent_with_defaults():
    """error_node handles missing error fields with safe defaults."""
    from src.ikigai.src.agents.v2.nodes.error import error_node

    result = error_node(_base_state())

    assert "ERROR in node 'unknown'" in result["commit_summary"]
    assert result["originating_node"] == "unknown"
    assert result["terminated"] is True


# ---------------------------------------------------------------------------
# observe_node (intent classification: pt-BR + en keywords)
# ---------------------------------------------------------------------------
def test_observe_node_isolation_no_user_input():
    """observe_node with no user_input returns observation + error_channel."""
    from src.ikigai.src.agents.v2.nodes.observe import observe_node

    result = observe_node(_base_state())

    assert isinstance(result, dict)
    assert result["observation"] is None
    assert "error_channel" in result
    assert len(result["error_channel"]) >= 1
    assert result["last_step"] == "observe"
    # No plan keyword → no plan_intent_hint
    assert "plan_intent_hint" not in result


def test_observe_node_isolation_planning_keyword_pt():
    """observe_node surfaces plan_intent_hint on PT planning keyword."""
    from src.ikigai.src.agents.v2.nodes.observe import observe_node

    result = observe_node(_base_state(user_input="quero focar em BYD"))

    assert result["plan_intent_hint"].startswith("/plan")
    assert "quero focar" in result["plan_intent_hint"]
    assert result["last_step"] == "observe"


def test_observe_node_isolation_planning_keyword_en():
    """observe_node surfaces plan_intent_hint on EN planning keyword."""
    from src.ikigai.src.agents.v2.nodes.observe import observe_node

    result = observe_node(_base_state(user_input="I want to focus this week"))

    assert "plan_intent_hint" in result
    assert "i want to focus" in result["plan_intent_hint"]


# ---------------------------------------------------------------------------
# reason_node (M88 real: builds proposal from context)
# ---------------------------------------------------------------------------
def test_reason_node_isolation_no_context():
    """reason_node with empty context returns draft_proposal + bumps iteration."""
    from src.ikigai.src.agents.v2.nodes.reason_node import reason_node

    state = _base_state(context={}, user_request="isolation test")
    result = reason_node(state)

    proposal = result["draft_proposal"]
    assert proposal["status"] == "draft"
    assert proposal["reasoning"]  # non-empty reasoning string
    assert len(proposal["operations"]) >= 1
    assert proposal["operations"][0]["type"] == "task.create"
    assert proposal["operations"][0]["target"] == "isolation test"
    assert result["iteration"] == 1
    assert result["last_step"] == "reason"
    assert result["reasoning_chain_stage"] == "reason_complete"


def test_reason_node_isolation_with_recent_intentions():
    """reason_node grounds proposal in recent_intentions from context."""
    from src.ikigai.src.agents.v2.nodes.reason_node import reason_node

    state = _base_state(
        user_request="",
        context={
            "recent_intentions": [
                {
                    "ueid": "ts:dia:0001:0001",
                    "body_markdown": "BYD case study analysis",
                }
            ]
        },
    )
    result = reason_node(state)

    proposal = result["draft_proposal"]
    op_types = [op["type"] for op in proposal["operations"]]
    assert "reflect.intention" in op_types
    assert "ts:dia:0001:0001" in proposal["reasoning"]
    assert proposal["context_refs"] == ["ts:dia:0001:0001"]


# ---------------------------------------------------------------------------
# recall_node (M88 real: graceful fallback when no memory_db)
# ---------------------------------------------------------------------------
def test_recall_node_isolation_no_memory_db(monkeypatch):
    """recall_node with no IKIGAI_MEMORY_DB returns graceful empty context."""
    from src.ikigai.src.agents.v2.nodes import recall_node as recall_mod

    monkeypatch.setattr(recall_mod, "_resolve_memory_db", lambda: None)
    monkeypatch.delenv("IKIGAI_MEMORY_DB", raising=False)

    result = recall_mod.recall_node(_base_state())

    ctx = result["context"]
    assert ctx["strategics_loaded"] is False
    assert ctx["daily_intentions_count"] == 0
    assert ctx["weekly_aggregations_count"] == 0
    assert "recall_error" in ctx
    assert ctx["recall_attempt"] == 1
    assert result["last_step"] == "recall"


# ---------------------------------------------------------------------------
# surface_intentions_node (LLM-bound: mock render_surface_pav_intentions)
# ---------------------------------------------------------------------------
def test_surface_intentions_node_isolation(monkeypatch):
    """surface_intentions_node emits user_suggestions from the mocked renderer.

    Without mocking, render_surface_pav_intentions attempts an LLM call
    that fails in this environment (no ANTHROPIC_API_KEY, IKIGAI_FAKE_LLM
    is documented but not actually wired) and returns empty suggestions.
    We patch the renderer to a known 3-suggestion payload so the test
    asserts on the node's CONTRACT, not LLM connectivity.
    """
    from src.ikigai.src.agents.v2.nodes import surface_intentions as surf_mod

    fake_renderer = lambda state: {  # noqa: E731
        "suggestions": ["sugestao 1", "sugestao 2", "sugestao 3"],
        "language": "pt-BR",
    }
    monkeypatch.setattr(surf_mod, "render_surface_pav_intentions", fake_renderer)

    result = surf_mod.surface_intentions_node(_base_state())

    assert result["user_suggestions"] == ["sugestao 1", "sugestao 2", "sugestao 3"]
    assert result["suggestions_count"] == 3
    assert result["suggestions_language"] == "pt-BR"
    assert result["last_step"] == "surface_intentions"
