from src.ikigai.src.agents.v2 import mcp_bridge

from ..state import IKIGAiStateDict


def score_vectors_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Score priority vectors via MCP bridge."""
    try:
        result = mcp_bridge.ikigai_score_vectors(vectors=state.get("vectors", []))
        return {"score_vectors": result}
    except Exception as e:
        return {"score_vectors": None, "error_type": type(e).__name__, "error_message": f"score_vectors: {e}"}
