"""IKIGAi LangGraph — make_ikigai_graph factory.

Assembles observe → score_vectors → heuristics → balance → decompose → plan → reflect → commit
with conditional edges and SqliteSaver checkpointing.
"""
from __future__ import annotations

from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END

from .state import IKIGAiStateDict
from .nodes.observe import observe_node
from .nodes.score_vectors import score_vectors_node
from .nodes.heuristics import heuristics_node
from .nodes.balance import balance_node
from .nodes.decompose import decompose_node
from .nodes.plan import plan_node
from .nodes.reflect import reflect_node
from .nodes.commit import commit_node

# ---------------------------------------------------------------------------
# Observability — init at module load; manual span on the graph factory.
# ---------------------------------------------------------------------------
from observability import init_tracing, get_tracer

init_tracing()
_graph_tracer = get_tracer("ikigai.graph")


# ---------------------------------------------------------------------------
# Node names (must match function names)
# ---------------------------------------------------------------------------
NODES = (
    "observe",
    "score_vectors",
    "heuristics",
    "balance",
    "decompose",
    "plan",
    "reflect",
    "commit",
)


# ---------------------------------------------------------------------------
# Conditional edge routing
# ---------------------------------------------------------------------------
def _route_after_observe(state: IKIGAiStateDict) -> Literal[
    "score_vectors", "balance", "commit"
]:
    """After observe: always score vectors, unless kill_switch."""
    if state.get("kill_switch_triggered"):
        return "commit"
    return "score_vectors"


def _route_after_score_vectors(state: IKIGAiStateDict) -> Literal["heuristics", "balance"]:
    """After score_vectors: run heuristics."""
    return "heuristics"


def _route_after_heuristics(state: IKIGAiStateDict) -> Literal["balance", "decompose"]:
    """After heuristics: run balance check."""
    return "balance"


def _route_after_balance(state: IKIGAiStateDict) -> Literal["decompose", "plan"]:
    """After balance: decompose if hysteresis not blocking, else plan."""
    if state.get("is_hysteresis_active"):
        return "plan"
    return "decompose"


def _route_after_decompose(state: IKIGAiStateDict) -> Literal["plan", "reflect"]:
    """After decompose: always proceed to plan."""
    return "plan"


def _route_after_plan(state: IKIGAiStateDict) -> Literal["reflect", "commit"]:
    """After plan: reflect then commit."""
    return "reflect"


def _route_after_reflect(state: IKIGAiStateDict) -> Literal["commit", END]:
    """After reflect: commit and end."""
    return "commit"


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------
def make_ikigai_graph(checkpoint_db: str | None = None) -> StateGraph:
    """Build the IKIGAi Maintainer StateGraph.

    Args:
        checkpoint_db: Path to SQLite file for SqliteSaver checkpointing.
                       If None, uses ~/.ikigai/ikigai_checkpoints.db

    Returns:
        Compiled StateGraph ready for .invoke()
    """
    import os
    from pathlib import Path

    if checkpoint_db is None:
        checkpoint_db = str(Path.home() / ".ikigai" / "ikigai_checkpoints.db")

    # Ensure directory exists
    Path(checkpoint_db).parent.mkdir(parents=True, exist_ok=True)

    # Build graph (wrapped in a span so each compile call is observable)
    with _graph_tracer.start_as_current_span("ikigai.graph.compile") as span:
        span.set_attribute("checkpoint_db", checkpoint_db)
        builder = StateGraph(IKIGAiStateDict)

        # Add nodes
        builder.add_node("observe", observe_node)
        builder.add_node("score_vectors", score_vectors_node)
        builder.add_node("heuristics", heuristics_node)
        builder.add_node("balance", balance_node)
        builder.add_node("decompose", decompose_node)
        builder.add_node("plan", plan_node)
        builder.add_node("reflect", reflect_node)
        builder.add_node("commit", commit_node)

        # Sequential edges (linear chain)
        builder.add_edge("observe", "score_vectors")
        builder.add_edge("score_vectors", "heuristics")
        builder.add_edge("heuristics", "balance")
        builder.add_edge("balance", "decompose")
        builder.add_edge("decompose", "plan")
        builder.add_edge("plan", "reflect")
        builder.add_edge("reflect", "commit")
        builder.add_edge("commit", END)

        # Conditional entry point
        builder.set_conditional_entry_point(
            _route_after_observe,
            {
                "score_vectors": "score_vectors",
                "balance": "balance",
                "commit": "commit",
            },
        )

        # Compile with checkpointer — create SqliteSaver directly (not via context manager)
        import sqlite3

        conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
        checkpointer = SqliteSaver(conn)

        compiled = builder.compile(checkpointer=checkpointer)
        span.set_attribute("nodes", len(NODES))
        return compiled


# ---------------------------------------------------------------------------
# Module-level singleton for langgraph dev / langgraph.json
# ---------------------------------------------------------------------------
import os
_graph_instance = None

def graph():
    """Return a singleton compiled graph instance for langgraph dev."""
    global _graph_instance
    if _graph_instance is None:
        db_path = os.environ.get("IKIGAI_CHECKPOINT_DB")
        _graph_instance = make_ikigai_graph(checkpoint_db=db_path)
    return _graph_instance
