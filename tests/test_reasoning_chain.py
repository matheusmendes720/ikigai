import sys
sys.path.insert(0, "src/ikigai/src/agents")

from v2.nodes.recall_node import recall_node
from v2.nodes.reason_node import reason_node


def test_recall_populates_context() -> None:
    """M88: recall_node populates context with realistic fields.

    The old stub always set strategics_loaded=True with a hardcoded
    recalled_at date. The real implementation reads memory_db; if no
    memory_db is found, it sets strategics_loaded=False. Either is
    acceptable — what matters is that context is populated with the
    documented fields.
    """
    out = recall_node({})
    assert "context" in out
    ctx = out["context"]
    assert "recalled_at" in ctx
    assert "strategics_loaded" in ctx
    assert isinstance(ctx["strategics_loaded"], bool)
    assert "daily_intentions_count" in ctx
    assert "weekly_aggregations_count" in ctx
    assert isinstance(ctx["daily_intentions_count"], int)
    assert isinstance(ctx["weekly_aggregations_count"], int)
    assert "last_step" in out
    assert out["last_step"] == "recall"


def test_reason_proposes_draft():
    out = reason_node({"user_request": "ship feature X"})
    p = out["draft_proposal"]
    assert p["status"] == "draft"
    assert p["operations"][0]["target"] == "ship feature X"


def test_chain_recall_then_reason():
    s = {}
    s = recall_node(s)
    s = reason_node({**s, "user_request": "test"})
    assert s["reasoning_chain_stage"] == "reason_complete"
