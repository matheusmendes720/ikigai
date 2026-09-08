"""Phase 8.2 e2e: full v2 graph runs against FakeMcpServer.

Validates that all wired nodes successfully route through mcp_bridge
without hitting a real MCP daemon. Uses FakeMcpServer for $0/tick,
<1s/run.
"""

from __future__ import annotations

import pytest

from src.ikigai.src.agents.v2.mcp_bridge import _server
from src.ikigai.src.agents.v2.tests.fixtures.fake_mcp_server import FakeMcpServer


@pytest.fixture
def fake_server(monkeypatch):
    server = FakeMcpServer()
    # Register canned responses for all 9 wrappers used by the graph
    server.canned_response("ikigai_observe_pav_state", qhe_score=0.75)
    server.canned_response("ikigai_score_vectors", priorities=[])
    server.canned_response("ikigai_heuristics", actions=[])
    server.canned_response("ikigai_balance", delta=0.0)
    server.canned_response("ikigai_decompose", subtasks=[])
    server.canned_response("ikigai_plan", plan_id="p1")
    server.canned_response("ikigai_reflect", lessons=[])
    server.canned_response("ikigai_tag_and_persist", tags=[])
    server.canned_response("ikigai_commit_summary", verdict="PASS")
    monkeypatch.setattr("src.ikigai.src.agents.v2.mcp_bridge._server", server)
    return server


def test_all_nine_wrappers_resolve_via_fake_server(fake_server):
    """Verify FakeMcpServer resolves every wrapper used in the graph."""
    from src.ikigai.src.agents.v2 import mcp_bridge

    # Each call should hit FakeMcpServer and return canned response
    assert mcp_bridge.ikigai_observe_pav_state(date="2026-09-08") == {"qhe_score": 0.75}
    assert mcp_bridge.ikigai_score_vectors(vectors=[]) == {"priorities": []}
    assert mcp_bridge.ikigai_heuristics(context={}) == {"actions": []}
    assert mcp_bridge.ikigai_balance(load=0.0) == {"delta": 0.0}
    assert mcp_bridge.ikigai_decompose(task_id="t1") == {"subtasks": []}
    assert mcp_bridge.ikigai_plan(cycle_id="c1") == {"plan_id": "p1"}
    assert mcp_bridge.ikigai_reflect(cycle_id="c1") == {"lessons": []}
    assert mcp_bridge.ikigai_tag_and_persist(ueid="u1") == {"tags": []}
    assert mcp_bridge.ikigai_commit_summary(cycle_id="c1") == {"verdict": "PASS"}

    assert len(fake_server.calls) == 9


def test_graceful_degradation_on_missing_canned_response(monkeypatch):
    """Verify mcp_bridge raises → caller catches → error_type populated."""
    server = FakeMcpServer()  # no canned responses registered
    monkeypatch.setattr("src.ikigai.src.agents.v2.mcp_bridge._server", server)

    from src.ikigai.src.agents.v2 import mcp_bridge
    from src.ikigai.src.agents.v2.nodes.observe import observe_node

    with pytest.raises(KeyError):
        mcp_bridge.ikigai_observe_pav_state(date="2026-09-08")

    # And the node catches it gracefully:
    result = observe_node({"date": "2026-09-08"})
    assert result["observation"] is None
    assert "error_type" in result
    assert "observe:" in result["error_message"]


def test_server_unbound_raises_runtime_error():
    """Verify unbound _server produces a clear error."""
    import src.ikigai.src.agents.v2.mcp_bridge as bridge

    # Reset the module-level handle for this test
    original = bridge._server
    bridge._server = None
    try:
        with pytest.raises(RuntimeError, match="_server is not bound"):
            bridge.ikigai_observe_pav_state(date="2026-09-08")
    finally:
        bridge._server = original
