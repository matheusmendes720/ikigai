"""mcp_bridge unit tests — uses FakeMcpServer, no real MCP daemon."""

from __future__ import annotations

import pytest

from src.ikigai.src.agents.v2.mcp_bridge import (
    ikigai_observe_pav_state,
    ikigai_score_vectors,
    ikigai_heuristics,
    ikigai_balance,
    ikigai_decompose,
    ikigai_plan,
    ikigai_reflect,
    ikigai_tag_and_persist,
    ikigai_commit_summary,
)
from src.ikigai.src.agents.v2.tests.fixtures.fake_mcp_server import FakeMcpServer


# Module-level fixture: install FakeMcpServer into mcp_bridge module
@pytest.fixture
def fake_server(monkeypatch):
    server = FakeMcpServer()
    monkeypatch.setattr("src.ikigai.src.agents.v2.mcp_bridge._server", server)
    return server


def test_observe_pav_state_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_observe_pav_state", qhe_score=0.75, regime="FOCUS")
    result = ikigai_observe_pav_state(date="2026-09-08")
    assert result == {"qhe_score": 0.75, "regime": "FOCUS"}
    assert fake_server.calls == [("ikigai_observe_pav_state", {"date": "2026-09-08"})]


def test_score_vectors_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_score_vectors", priorities=["a", "b", "c"])
    result = ikigai_score_vectors(vectors=[1, 2, 3])
    assert result == {"priorities": ["a", "b", "c"]}


def test_heuristics_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_heuristics", actions=["x", "y"])
    result = ikigai_heuristics(context={"k": "v"})
    assert result == {"actions": ["x", "y"]}


def test_balance_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_balance", delta=0.1)
    result = ikigai_balance(load=5)
    assert result == {"delta": 0.1}


def test_decompose_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_decompose", subtasks=["s1", "s2"])
    result = ikigai_decompose(task_id="t1")
    assert result == {"subtasks": ["s1", "s2"]}


def test_plan_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_plan", plan_id="p1")
    result = ikigai_plan(cycle_id="c1")
    assert result == {"plan_id": "p1"}


def test_reflect_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_reflect", lessons=["l1"])
    result = ikigai_reflect(cycle_id="c1")
    assert result == {"lessons": ["l1"]}


def test_tag_and_persist_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_tag_and_persist", tags=["t1"])
    result = ikigai_tag_and_persist(ueid="u1")
    assert result == {"tags": ["t1"]}


def test_commit_summary_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_commit_summary", verdict="PASS")
    result = ikigai_commit_summary(cycle_id="c1")
    assert result == {"verdict": "PASS"}


def test_degrade_populates_error_type(fake_server):
    """When the bridge raises, the node must populate error_type (not error_channel)."""
    from src.ikigai.src.agents.v2.nodes.observe import observe_node

    # Force a KeyError by calling observe_node with no canned response set up.
    # The fake_server has no canned response, so mcp_bridge raises KeyError.
    result = observe_node({})
    assert "error_type" in result, f"node did not emit error_type on degrade: {result}"
    assert result.get("error_message", "").startswith("observe:"), result
    assert "error_channel" not in result, f"old error_channel still present: {result}"


def test_missing_canned_response_raises(fake_server):
    with pytest.raises(KeyError):
        ikigai_observe_pav_state(date="2026-09-08")
