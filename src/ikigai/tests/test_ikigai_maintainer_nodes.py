"""Per-node smoke tests for the 8-node IKIGAi-Maintainer LangGraph.

Per audit B5.0-F14: zero per-node tests for the IKIGAi-Maintainer graph meant
any regression in any node was invisible. Each main node gets a smoke test
that calls the node with a minimal valid state and asserts:

  1. The node does not raise.
  2. It returns a dict containing `last_step` set to the node name.
  3. It returns a dict of the correct shape (state-channel keys present).

Plus infrastructure tests:
  - 8 main nodes + error terminal wired into the graph (graph build smoke).
  - safe_node wrapper converts exceptions into populated error state.
  - error_node produces commit_summary from error fields.
  - Conditional edge routers return correct literals for representative states.

The smoke tests are NOT integration tests — they verify each node in
isolation against a minimal state. Nodes that try live subprocess calls
(observe / decompose / reflect → solverforge-calendar-mcp) have try/except
fallbacks that return sensible defaults when the MCP is absent, so the smoke
runs cleanly in CI without that fork installed.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

# Ensure repo root on sys.path so absolute imports like
# `src.ikigai.src.mcp_server.server` resolve during this module's tests.
# Pattern matches test_bidirectional_vault_sync_e2e.py.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# === Fixtures ================================================================


@pytest.fixture
def minimal_state() -> dict[str, Any]:
    """Minimal valid IKIGAiStateDict — only required identity fields."""
    return {
        "cycle_id": "2026-08-30-smoke",
        "cycle_start": "2026-08-30",
        "cycle_end": "2026-09-06",
        "iteration": 0,
    }


@pytest.fixture
def state_with_vectors(minimal_state: dict[str, Any]) -> dict[str, Any]:
    """State with IKIGAi vector scores — used by nodes downstream of score_vectors."""
    return {
        **minimal_state,
        "vector_scores": {
            "passion": 60.0,
            "skill": 55.0,
            "market": 70.0,
            "revenue": 50.0,
            "course": 65.0,
        },
    }


# === Per-node smoke tests (8 main nodes) =====================================


def test_observe_node_runs(minimal_state: dict[str, Any]) -> None:
    """observe_node: read Q_HE/workload, populate regime + balancer verdict."""
    from agents.ikigai_maintainer.nodes import observe_node

    result = observe_node(minimal_state)

    assert isinstance(result, dict)
    assert result["last_step"] == "observe"
    # observe must populate regime + balancer verdict
    assert result["regime_state"] in {"PUSH", "MAINTAIN", "REDUCE", "RECOVER"}
    assert result["balancer_verdict"] in {"OK", "OVERLOAD", "UNDERLOAD", "RECOVER"}
    # q_he/workload/capacity are required outputs
    assert "q_he_score" in result
    assert "workload_estimate" in result
    assert "capacity_estimate" in result


def test_score_vectors_node_runs(minimal_state: dict[str, Any]) -> None:
    """score_vectors_node: compute 5-vector scores + meta-vector."""
    from agents.ikigai_maintainer.nodes import score_vectors_node

    result = score_vectors_node(minimal_state)

    assert isinstance(result, dict)
    assert result["last_step"] == "score_vectors"
    # vector_scores should be a dict (possibly empty when no upstream data)
    assert "vector_scores" in result
    assert isinstance(result["vector_scores"], dict)
    # meta_vector_score should be set (or default to 0)
    assert "meta_vector_score" in result


def test_heuristics_node_runs(state_with_vectors: dict[str, Any]) -> None:
    """heuristics_node: emit H1-H6 corrections deterministically."""
    from agents.ikigai_maintainer.nodes import heuristics_node

    result = heuristics_node(state_with_vectors)

    assert isinstance(result, dict)
    assert result["last_step"] == "heuristics"
    # corrections should be a list (accumulator via operator.add)
    assert "corrections" in result
    assert isinstance(result["corrections"], list)


def test_balance_node_runs(state_with_vectors: dict[str, Any]) -> None:
    """balance_node: workload/capacity check + hysteresis logic."""
    from agents.ikigai_maintainer.nodes import balance_node

    result = balance_node(state_with_vectors)

    assert isinstance(result, dict)
    assert result["last_step"] == "balance"
    assert "balancer_verdict" in result
    assert "is_hysteresis_active" in result
    assert isinstance(result["is_hysteresis_active"], bool)


def test_decompose_node_runs(state_with_vectors: dict[str, Any]) -> None:
    """decompose_node: traverse UEID hierarchy, propose decomposition."""
    from agents.ikigai_maintainer.nodes import decompose_node

    result = decompose_node(state_with_vectors)

    assert isinstance(result, dict)
    assert result["last_step"] == "decompose"


def test_plan_node_runs(state_with_vectors: dict[str, Any]) -> None:
    """plan_node: prospective channel — draft next actions for current tier."""
    from agents.ikigai_maintainer.nodes import plan_node

    result = plan_node(state_with_vectors)

    assert isinstance(result, dict)
    assert result["last_step"] == "plan"
    # prospective_buffer is the accumulator
    assert "prospective_buffer" in result
    assert isinstance(result["prospective_buffer"], list)


def test_reflect_node_runs(state_with_vectors: dict[str, Any]) -> None:
    """reflect_node: retrospective channel — aggregate completed work."""
    from agents.ikigai_maintainer.nodes import reflect_node

    result = reflect_node(state_with_vectors)

    assert isinstance(result, dict)
    assert result["last_step"] == "reflect"
    # retrospective_log is the accumulator
    assert "retrospective_log" in result
    assert isinstance(result["retrospective_log"], list)


def test_commit_node_runs(
    state_with_vectors: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """commit_node: persist to SQLite + vault; mocked here to avoid filesystem coupling."""
    from agents.ikigai_maintainer import nodes
    from agents.ikigai_maintainer.nodes import commit_node

    # Mock the I/O helpers so the smoke doesn't touch real filesystem / DB.
    # The real implementations are exercised by integration tests.
    monkeypatch.setattr(nodes.commit, "_write_to_sqlite", lambda *a, **kw: "ok (mocked)")
    monkeypatch.setattr(nodes.commit, "_append_to_vault", lambda *a, **kw: "ok (mocked)")
    # structured_tasks is empty in minimal state — _write_tasks_to_data is skipped.

    result = commit_node(state_with_vectors)

    assert isinstance(result, dict)
    assert result["last_step"] == "commit"
    # commit_summary is the human-readable report
    assert "commit_summary" in result
    assert "mocked" in result["commit_summary"]


# === Infrastructure tests ====================================================


def test_error_node_terminal(minimal_state: dict[str, Any]) -> None:
    """error_node: terminal — produces commit_summary from error fields."""
    from agents.ikigai_maintainer.nodes import error_node

    state_with_error = {
        **minimal_state,
        "originating_node": "decompose",
        "error_type": "ValueError",
        "error_message": "smoke test",
        "traceback_str": "Traceback ...",
    }

    result = error_node(state_with_error)

    assert isinstance(result, dict)
    assert result["last_step"] == "error"
    assert result["terminated"] is True
    assert "decompose" in result["commit_summary"]
    assert "ValueError" in result["commit_summary"]
    assert "smoke test" in result["commit_summary"]
    # Traceback must be preserved verbatim for debugging
    assert result["error_traceback"] == "Traceback ..."


def test_safe_node_wrapper_catches_exception() -> None:
    """safe_node wrapper converts exceptions into error-channel state, not raise."""
    from agents.ikigai_maintainer.graph import _safe_node

    def boom(state: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("kaboom")

    wrapped = _safe_node("test_boom", boom)
    result = wrapped({"cycle_id": "x", "cycle_start": "y", "cycle_end": "z", "iteration": 0})

    assert result["originating_node"] == "test_boom"
    assert result["error_type"] == "RuntimeError"
    assert result["error_message"] == "kaboom"
    assert "Traceback" in result["traceback_str"]
    assert result["last_step"] == "test_boom"


def test_safe_node_wrapper_returns_clean_state_on_success() -> None:
    """safe_node wrapper must pass through normal results without modification."""
    from agents.ikigai_maintainer.graph import _safe_node

    def ok(state: dict[str, Any]) -> dict[str, Any]:
        return {"last_step": "test_ok", "value": 42}

    wrapped = _safe_node("test_ok", ok)
    result = wrapped({"cycle_id": "x", "cycle_start": "y", "cycle_end": "z", "iteration": 0})

    assert result == {"last_step": "test_ok", "value": 42}


# === Graph build smoke =======================================================


def test_make_ikigai_graph_wires_all_8_nodes() -> None:
    """make_ikigai_graph: 8 main nodes + error terminal compiled into a graph."""
    from agents.ikigai_maintainer.graph import NODES, make_ikigai_graph

    assert len(NODES) == 8, f"expected 8 main nodes, got {len(NODES)}"
    assert NODES == (
        "observe",
        "score_vectors",
        "heuristics",
        "balance",
        "decompose",
        "plan",
        "reflect",
        "commit",
    )

    # Use a fresh tempdir (avoids pytest-of-mathe Windows lock on the
    # pytest tmp_path fixture, which lives under AppData\Local\Temp\pytest-of-mathe).
    tmp_root = Path(tempfile.mkdtemp(prefix="ikigai_smoke_"))
    db_path = tmp_root / "smoke_checkpoints.db"
    compiled = make_ikigai_graph(checkpoint_db=str(db_path))

    # Stash per audit B5.0-F4 closure
    assert hasattr(compiled, "_ikigai_checkpoint_conn")
    conn = compiled._ikigai_checkpoint_conn  # type: ignore[attr-defined]
    conn.close()


# === Routing smoke ===========================================================


def test_route_after_observe_clean_state() -> None:
    """_route_after_observe: clean state → 'score_vectors'."""
    from agents.ikigai_maintainer.graph import _route_after_observe

    state = {"cycle_id": "x", "cycle_start": "y", "cycle_end": "z", "iteration": 0}
    assert _route_after_observe(state) == "score_vectors"


def test_route_after_observe_kill_switch() -> None:
    """_route_after_observe: kill_switch_triggered → 'commit'."""
    from agents.ikigai_maintainer.graph import _route_after_observe

    state = {
        "cycle_id": "x",
        "cycle_start": "y",
        "cycle_end": "z",
        "iteration": 0,
        "kill_switch_triggered": True,
    }
    assert _route_after_observe(state) == "commit"


def test_route_after_observe_upstream_error() -> None:
    """_route_after_observe: error_type set → 'error'."""
    from agents.ikigai_maintainer.graph import _route_after_observe

    state = {
        "cycle_id": "x",
        "cycle_start": "y",
        "cycle_end": "z",
        "iteration": 0,
        "error_type": "SomeError",
    }
    assert _route_after_observe(state) == "error"


def test_route_after_balance_hysteresis() -> None:
    """_route_after_balance: hysteresis active → 'plan', else → 'decompose'."""
    from agents.ikigai_maintainer.graph import _route_after_balance

    base = {"cycle_id": "x", "cycle_start": "y", "cycle_end": "z", "iteration": 0}
    assert _route_after_balance({**base, "is_hysteresis_active": False}) == "decompose"
    assert _route_after_balance({**base, "is_hysteresis_active": True}) == "plan"


def test_route_after_commit_end_on_clean() -> None:
    """_route_after_commit: clean state → END, error_type → 'error'."""
    from langgraph.graph import END

    from agents.ikigai_maintainer.graph import _route_after_commit

    base = {"cycle_id": "x", "cycle_start": "y", "cycle_end": "z", "iteration": 0}
    assert _route_after_commit(base) == END
    assert _route_after_commit({**base, "error_type": "Boom"}) == "error"
