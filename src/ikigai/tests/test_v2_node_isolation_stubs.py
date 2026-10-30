"""v2 M12-stub node isolation tests — error_channel contract per stub node.

5 of the 16 v2 nodes were converted to M12 stubs after the bridge/server
drift audit (T-12.1): balance, heuristics, plan, reflect, score_vectors.
Each stub:

  - reads minimal state
  - returns a dict with the original node-name key (None), an
    ``error_channel`` list naming the deleted bridge wrapper, and
    ``last_step`` set to the node's name

These tests lock that contract. If a future contributor tries to silently
restore a deleted bridge wrapper via try/except without re-registering
it on server.py, the drift net will trip — but these tests catch the
smaller regression where the error_channel entry goes missing.

See test_v2_node_isolation.py for the real-node isolation tests and the
parametrized smoke test that covers all 16 nodes.
"""

from __future__ import annotations

import sys
from pathlib import Path

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


def _base_state() -> dict:
    """Minimal IKIGAiStateDict — no fields matter for stub nodes."""
    return {
        "cycle_id": "iso-test-001",
        "iteration": 0,
    }


# ---------------------------------------------------------------------------
# balance_node
# ---------------------------------------------------------------------------
def test_balance_node_isolation():
    """balance_node returns dict + error_channel naming ikigai_balance."""
    from src.ikigai.src.agents.v2.nodes.balance import balance_node

    result = balance_node(_base_state())

    assert isinstance(result, dict)
    assert result["balance"] is None
    assert isinstance(result["error_channel"], list)
    assert len(result["error_channel"]) >= 1
    assert "ikigai_balance" in result["error_channel"][0]
    assert result["last_step"] == "balance"


# ---------------------------------------------------------------------------
# heuristics_node
# ---------------------------------------------------------------------------
def test_heuristics_node_isolation():
    """heuristics_node returns dict + error_channel naming ikigai_heuristics."""
    from src.ikigai.src.agents.v2.nodes.heuristics import heuristics_node

    result = heuristics_node(_base_state())

    assert isinstance(result, dict)
    assert result["heuristics"] is None
    assert isinstance(result["error_channel"], list)
    assert len(result["error_channel"]) >= 1
    assert "ikigai_heuristics" in result["error_channel"][0]
    assert result["last_step"] == "heuristics"


# ---------------------------------------------------------------------------
# plan_node
# ---------------------------------------------------------------------------
def test_plan_node_isolation():
    """plan_node returns dict + error_channel naming ikigai_plan."""
    from src.ikigai.src.agents.v2.nodes.plan import plan_node

    result = plan_node(_base_state())

    assert isinstance(result, dict)
    assert result["plan"] is None
    assert isinstance(result["error_channel"], list)
    assert len(result["error_channel"]) >= 1
    assert "ikigai_plan" in result["error_channel"][0]
    assert result["last_step"] == "plan"


# ---------------------------------------------------------------------------
# reflect_node
# ---------------------------------------------------------------------------
def test_reflect_node_isolation():
    """reflect_node returns dict + error_channel naming ikigai_reflect."""
    from src.ikigai.src.agents.v2.nodes.reflect import reflect_node

    result = reflect_node(_base_state())

    assert isinstance(result, dict)
    assert result["reflect"] is None
    assert isinstance(result["error_channel"], list)
    assert len(result["error_channel"]) >= 1
    assert "ikigai_reflect" in result["error_channel"][0]
    assert result["last_step"] == "reflect"


# ---------------------------------------------------------------------------
# score_vectors_node
# ---------------------------------------------------------------------------
def test_score_vectors_node_isolation():
    """score_vectors_node returns dict + error_channel naming ikigai_score_vectors."""
    from src.ikigai.src.agents.v2.nodes.score_vectors import score_vectors_node

    result = score_vectors_node(_base_state())

    assert isinstance(result, dict)
    assert result["score_vectors"] is None
    assert isinstance(result["error_channel"], list)
    assert len(result["error_channel"]) >= 1
    assert "ikigai_score_vectors" in result["error_channel"][0]
    assert result["last_step"] == "score_vectors"
