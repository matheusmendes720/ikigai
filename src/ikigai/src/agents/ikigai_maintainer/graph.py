"""IKIGAi LangGraph — make_ikigai_graph factory.

Assembles observe → score_vectors → heuristics → balance → decompose → plan → reflect → commit
with conditional edges and SqliteSaver checkpointing.

Per audit B5.0-F3: every node is wrapped in `_safe_node` which catches
exceptions and populates error-channel state fields. The terminal `error_node`
is reached via a conditional edge from `commit` when those fields are set.
"""
from __future__ import annotations

import traceback
from typing import Any, Literal

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
from .nodes.error import error_node

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
# Safe-node wrapper (B5.1-F3): catch exceptions, populate error state, return
# partial state instead of crashing. The terminal `error_node` consumes this
# state to produce a failed commit_summary.
# ---------------------------------------------------------------------------
def _safe_node(name: str, fn):
    """Wrap a node function so exceptions populate error-channel state.

    Returns a wrapper with the same signature; when fn() raises, the wrapper
    returns a dict with originating_node/error_type/error_message/traceback_str
    fields. Routing after `commit` checks these fields to decide END vs error.
    """

    def wrapper(state: IKIGAiStateDict) -> dict[str, Any]:
        try:
            return fn(state)
        except Exception as exc:
            return {
                "originating_node": name,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback_str": traceback.format_exc(),
                "last_step": name,
            }

    wrapper.__name__ = f"safe_{name}"
    return wrapper


# ---------------------------------------------------------------------------
# Conditional edge routing
# ---------------------------------------------------------------------------
def _route_after_observe(state: IKIGAiStateDict) -> Literal[
    "score_vectors", "balance", "commit", "error"
]:
    """After observe: always score vectors, unless kill_switch or upstream error.

    Per B5.1-F3: if the safe_node wrapper captured an exception in any prior
    node, route directly to error_node instead of continuing the chain.
    """
    if state.get("error_type"):
        return "error"
    if state.get("kill_switch_triggered"):
        return "commit"
    return "score_vectors"


def _route_after_score_vectors(
    state: IKIGAiStateDict,
) -> Literal["heuristics", "balance", "error"]:
    """After score_vectors: run heuristics unless an upstream error fired."""
    if state.get("error_type"):
        return "error"
    return "heuristics"


def _route_after_heuristics(
    state: IKIGAiStateDict,
) -> Literal["balance", "decompose", "error"]:
    """After heuristics: run balance check unless an upstream error fired."""
    if state.get("error_type"):
        return "error"
    return "balance"


def _route_after_balance(
    state: IKIGAiStateDict,
) -> Literal["decompose", "plan", "error"]:
    """After balance: decompose if hysteresis not blocking, else plan.

    Routes to error_node if any upstream exception was caught.
    """
    if state.get("error_type"):
        return "error"
    if state.get("is_hysteresis_active"):
        return "plan"
    return "decompose"


def _route_after_decompose(
    state: IKIGAiStateDict,
) -> Literal["plan", "reflect", "error"]:
    """After decompose: always proceed to plan unless upstream error fired."""
    if state.get("error_type"):
        return "error"
    return "plan"


def _route_after_plan(
    state: IKIGAiStateDict,
) -> Literal["reflect", "commit", "error"]:
    """After plan: reflect unless upstream error fired."""
    if state.get("error_type"):
        return "error"
    return "reflect"


def _route_after_reflect(
    state: IKIGAiStateDict,
) -> Literal["commit", END, "error"]:
    """After reflect: commit and end unless upstream error fired."""
    if state.get("error_type"):
        return "error"
    return "commit"


def _route_after_commit(state: IKIGAiStateDict) -> Literal["error", END]:
    """After commit: end on success, route to error_node if any node raised.

    The safe_node wrapper populates `error_type` whenever an exception occurs
    upstream. We only need this single check at the end because committed
    state is the last place we'd discover the error before END.
    """
    if state.get("error_type"):
        return "error"
    return END


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------
def make_ikigai_graph(checkpoint_db: str | None = None) -> StateGraph:
    """Build the IKIGAi Maintainer StateGraph.

    Args:
        checkpoint_db: Path to SQLite file for SqliteSaver checkpointing.
                       If None, uses <project_root>/data/ikigai_checkpoints.db
                       (project-local; avoids Windows-lock risk on ~/.ikigai/).

    Returns:
        Compiled StateGraph ready for .invoke()
    """
    import os
    from pathlib import Path

    if checkpoint_db is None:
        # Project-local default — avoids the Windows-locked ~/.ikigai/ path
        # (see memory: life-ops-ikigai-lock-2026-08-27).
        _project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        checkpoint_db = str(_project_root / "data" / "ikigai_checkpoints.db")

    # Ensure directory exists
    Path(checkpoint_db).parent.mkdir(parents=True, exist_ok=True)

    # Build graph (wrapped in a span so each compile call is observable)
    with _graph_tracer.start_as_current_span("ikigai.graph.compile") as span:
        span.set_attribute("checkpoint_db", checkpoint_db)
        builder = StateGraph(IKIGAiStateDict)

        # Add nodes — wrapped in safe_node so exceptions populate error state
        # instead of crashing the whole graph (B5.1-F3).
        builder.add_node("observe", _safe_node("observe", observe_node))
        builder.add_node("score_vectors", _safe_node("score_vectors", score_vectors_node))
        builder.add_node("heuristics", _safe_node("heuristics", heuristics_node))
        builder.add_node("balance", _safe_node("balance", balance_node))
        builder.add_node("decompose", _safe_node("decompose", decompose_node))
        builder.add_node("plan", _safe_node("plan", plan_node))
        builder.add_node("reflect", _safe_node("reflect", reflect_node))
        builder.add_node("commit", _safe_node("commit", commit_node))
        builder.add_node("error", error_node)

        # Sequential edges — each is conditional so any upstream exception
        # routes to error_node instead of continuing the chain (B5.1-F3).
        builder.add_conditional_edges(
            "observe",
            _route_after_observe,
            {
                "score_vectors": "score_vectors",
                "balance": "balance",
                "commit": "commit",
                "error": "error",
            },
        )
        builder.add_conditional_edges(
            "score_vectors",
            _route_after_score_vectors,
            {"heuristics": "heuristics", "error": "error"},
        )
        builder.add_conditional_edges(
            "heuristics",
            _route_after_heuristics,
            {"balance": "balance", "error": "error"},
        )
        builder.add_conditional_edges(
            "balance",
            _route_after_balance,
            {"decompose": "decompose", "plan": "plan", "error": "error"},
        )
        builder.add_conditional_edges(
            "decompose",
            _route_after_decompose,
            {"plan": "plan", "error": "error"},
        )
        builder.add_conditional_edges(
            "plan",
            _route_after_plan,
            {"reflect": "reflect", "error": "error"},
        )
        builder.add_conditional_edges(
            "reflect",
            _route_after_reflect,
            {"commit": "commit", "error": "error"},
        )

        # Conditional edge after commit: route to error_node if any upstream
        # exception was caught, otherwise end.
        builder.add_conditional_edges(
            "commit",
            _route_after_commit,
            {
                "error": "error",
                END: END,
            },
        )

        # error_node is terminal — always goes to END.
        builder.add_edge("error", END)

        # Direct entry point — observe always runs first (per B5.1-F3).
        # Killing or error routing happens AFTER observe executes.
        builder.set_entry_point("observe")

        # Compile with checkpointer — create SqliteSaver directly (not via context manager)
        import sqlite3

        conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
        checkpointer = SqliteSaver(conn)

        compiled = builder.compile(checkpointer=checkpointer)
        # Stash the connection on the compiled graph so close_graph() can find it.
        # Per audit B5.0-F4: SqliteSaver connection was leaking on singleton use.
        setattr(compiled, "_ikigai_checkpoint_conn", conn)
        setattr(compiled, "_ikigai_checkpoint_db", checkpoint_db)
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


def close_graph() -> None:
    """Close the SqliteSaver connection held by the singleton graph.

    Per audit B5.0-F4: connection was leaking on singleton use. Call this on
    process exit (atexit) or before re-creating the singleton.
    Idempotent: no-op if already closed or no singleton exists.
    """
    global _graph_instance
    if _graph_instance is None:
        return
    conn = getattr(_graph_instance, "_ikigai_checkpoint_conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass  # best-effort cleanup
        try:
            delattr(_graph_instance, "_ikigai_checkpoint_conn")
        except Exception:
            pass
    _graph_instance = None


# Register atexit hook so the connection is released on normal process exit.
import atexit
atexit.register(close_graph)
