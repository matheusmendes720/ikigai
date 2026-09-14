import sys
sys.path.insert(0, "src/ikigai/src/agents")

from v2.nodes.recall_node import recall_node
from v2.nodes.reason_node import reason_node


def test_recall_populates_context():
    out = recall_node({})
    assert out["context"]["strategics_loaded"] is True


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
