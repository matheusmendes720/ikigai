"""IKIGAi LangGraph v2 — make_v2_graph factory.

Assembles observe → score_vectors → heuristics → balance → decompose → plan → reflect → commit
with conditional edges and SqliteSaver checkpointing.

MATH CALLS REPLACED: all node logic replaced with prompt-chain stubs.
Phase 8.2 will wire actual MCP tool calls.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Observability — real OTel tracer (T-8.3.1 wires Phase 8.2 stubs)
# ---------------------------------------------------------------------------
import logging
import traceback
from collections.abc import Callable
from typing import Any, Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from src.ikigai.src.observability.otel_init import get_tracer, init_tracing


from .nodes.balance import balance_node  # noqa: E402
from .nodes.commit import commit_node  # noqa: E402
from .nodes.decompose import decompose_node  # noqa: E402
from .nodes.error import error_node  # noqa: E402
from .nodes.heuristics import heuristics_node  # noqa: E402
from .nodes.observe import observe_node  # noqa: E402
from .nodes.plan import plan_node  # noqa: E402
from .nodes.reflect import reflect_node  # noqa: E402
from .nodes.score_vectors import score_vectors_node  # noqa: E402
from .nodes.surface_intentions import surface_intentions_node  # noqa: E402
from .nodes.tag_and_persist import tag_and_persist_node  # noqa: E402
from .state import IKIGAiStateDict  # noqa: E402
from .subgraph import dispatch_sub_agents  # noqa: E402

_init_tracing_ok = True
try:
    init_tracing()
except Exception as exc:
    _init_tracing_ok = False
    logging.getLogger(__name__).warning(
        "init_tracing() raised %s: %s — graph will run without spans.",
        type(exc).__name__,
        exc,
    )

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
    "tag_and_persist",
    "reflect",
    "commit",
    "dispatch_sub_agents",
    "surface_intentions",
)


# ---------------------------------------------------------------------------
# Token-budget guard (PROD-3): enforce per-skill max_tokens cap
# ---------------------------------------------------------------------------
def _make_token_guard(max_tokens: int) -> Callable[[IKIGAiStateDict], dict[str, Any]]:
    """Return a node wrapper that enforces a token budget.

    Tracks accumulated tokens in state['_token_budget_used'] and aborts
    with an error if the cap is exceeded. Each node invocation counts as ~50 tokens.
    """

    def guard(state: IKIGAiStateDict) -> dict[str, Any]:
        used = state.get("_token_budget_used", 0)
        node_cost = 50  # rough estimate per node invocation
        if used + node_cost > max_tokens:
            return {
                "originating_node": "token_guard",
                "error_type": "TokenBudgetExceeded",
                "error_message": (
                    f"Token budget exceeded: {used + node_cost} > {max_tokens} "
                    f"(skill cap). Aborting graph execution."
                ),
                "last_step": state.get("last_step", "unknown"),
            }
        return {"_token_budget_used": used + node_cost}

    return guard


# ---------------------------------------------------------------------------
# Safe-node wrapper (B5.1-F3): catch exceptions, populate error state, return
# partial state instead of crashing. The terminal `error_node` consumes this
# state to produce a failed commit_summary.
# ---------------------------------------------------------------------------
def _safe_node(name: str, fn: Callable[[IKIGAiStateDict], dict[str, Any]]) -> Any:
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
def _route_after_observe(
    state: IKIGAiStateDict,
) -> Literal["score_vectors", "balance", "commit", "error"]:
    """After observe: always score vectors, unless kill_switch or upstream error."""
    if state.get("error_type"):
        return "error"
    if state.get("kill_switch_triggered"):
        return "commit"
    return "score_vectors"


def _route_after_score_vectors(
    state: IKIGAiStateDict,
) -> Literal["heuristics", "error"]:
    """After score_vectors: run heuristics unless an upstream error fired."""
    if state.get("error_type"):
        return "error"
    return "heuristics"


def _route_after_heuristics(
    state: IKIGAiStateDict,
) -> Literal["balance", "error"]:
    """After heuristics: run balance check unless an upstream error fired."""
    if state.get("error_type"):
        return "error"
    return "balance"


def _route_after_balance(
    state: IKIGAiStateDict,
) -> Literal["decompose", "plan", "error"]:
    """After balance: decompose if hysteresis not blocking, else plan."""
    if state.get("error_type"):
        return "error"
    if state.get("is_hysteresis_active"):
        return "plan"
    return "decompose"


def _route_after_decompose(
    state: IKIGAiStateDict,
) -> Literal["plan", "error"]:
    """After decompose: always proceed to plan unless upstream error fired."""
    if state.get("error_type"):
        return "error"
    return "plan"


def _route_after_plan(
    state: IKIGAiStateDict,
) -> Literal["tag_and_persist", "error"]:
    """After plan: persist via tag_and_persist unless upstream error fired."""
    if state.get("error_type"):
        return "error"
    return "tag_and_persist"


def _route_after_tag_and_persist(
    state: IKIGAiStateDict,
) -> Literal["reflect", "error"]:
    """After tag_and_persist: reflect unless upstream error fired."""
    if state.get("error_type"):
        return "error"
    return "reflect"


def _route_after_reflect(
    state: IKIGAiStateDict,
) -> Literal["commit", "error"]:
    """After reflect: commit unless upstream error fired."""
    if state.get("error_type"):
        return "error"
    return "commit"


def _route_after_commit(state: IKIGAiStateDict) -> str:
    """After commit: route through dispatch_sub_agents (W4.4 B-N10), then surface_intentions.

    Per ADR-026: a parent node signals sub-agent fan-out by populating
    state['dispatch_plan']. dispatch_sub_agents is a no-op (passthrough)
    when dispatch_plan is empty/absent, so the linear pipeline behavior
    is preserved when no children are scheduled. When dispatch_plan is
    populated, it spawns children, merges outputs, then routes onward.
    """
    if state.get("error_type"):
        return "error"
    return "dispatch_sub_agents"


def _route_after_dispatch_sub_agents(state: IKIGAiStateDict) -> str:
    """After dispatch_sub_agents: surface intentions (dispatcher never errors parent)."""
    if state.get("error_type"):
        return "error"
    return "surface_intentions"


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------
def make_v2_graph(
    checkpoint_db: str | None = None,
    entry_point: str = "observe",
    max_tokens: int = 96_000,
) -> Any:
    """Build the IKIGAi Maintainer StateGraph v2.

    Args:
        checkpoint_db: Path to SQLite file for SqliteSaver checkpointing.
                       If None, uses <project_root>/data/ikigai_checkpoints.db
        entry_point: Name of the node where the graph starts execution.
                     Must be one of NODES. Default: "observe" (full pipeline).
                     Skills (daily/weekly/monthly/quarterly) enter at specific
                     nodes to invoke partial pipelines.
        max_tokens: Per-skill token budget cap (PROD-3 cost guard).
                    Defaults: daily=1k, weekly=8k, monthly=32k, quarterly=96k.
                    Passed from invoke_skill() in _v2_skills.py.

    Returns:
        Compiled StateGraph ready for .invoke()

    Raises:
        ValueError: If entry_point is not one of the valid NODES.
    """
    from pathlib import Path

    if entry_point not in NODES:
        raise ValueError(f"Invalid entry_point {entry_point!r}. Must be one of: {', '.join(NODES)}")

    if checkpoint_db is None:
        _project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        checkpoint_db = str(_project_root / "data" / "ikigai_checkpoints.db")

    # Ensure directory exists
    Path(checkpoint_db).parent.mkdir(parents=True, exist_ok=True)

    with _graph_tracer.start_as_current_span("ikigai.graph.compile") as span:
        span.set_attribute("checkpoint_db", checkpoint_db)
        span.set_attribute("entry_point", entry_point)
        span.set_attribute("max_tokens", max_tokens)
        builder: StateGraph[IKIGAiStateDict, None, IKIGAiStateDict, IKIGAiStateDict] = StateGraph(
            IKIGAiStateDict
        )

        # Token guard node (PROD-3): runs first, checks budget, routes to entry_point or error
        token_guard_fn = _make_token_guard(max_tokens)
        builder.add_node("_token_guard", _safe_node("_token_guard", token_guard_fn))

        # Add nodes — wrapped in safe_node so exceptions populate error state
        builder.add_node("observe", _safe_node("observe", observe_node))
        builder.add_node("score_vectors", _safe_node("score_vectors", score_vectors_node))
        builder.add_node("heuristics", _safe_node("heuristics", heuristics_node))
        builder.add_node("balance", _safe_node("balance", balance_node))
        builder.add_node("decompose", _safe_node("decompose", decompose_node))
        builder.add_node("plan", _safe_node("plan", plan_node))
        builder.add_node("tag_and_persist", _safe_node("tag_and_persist", tag_and_persist_node))
        builder.add_node("reflect", _safe_node("reflect", reflect_node))
        builder.add_node("commit", _safe_node("commit", commit_node))
        # W4.4 B-N10: dispatch_sub_agents is the 11th node (ADR-026 R1 dedicated dispatcher).
        # Wrapped in _safe_node for uniform error-channel semantics; in practice
        # the node catches its own exceptions per ADR-026 R5 (failure isolation).
        builder.add_node(
            "dispatch_sub_agents", _safe_node("dispatch_sub_agents", dispatch_sub_agents)
        )
        builder.add_node(
            "surface_intentions", _safe_node("surface_intentions", surface_intentions_node)
        )
        builder.add_node("error", error_node)

        # Token guard routing: guard → entry_point or error
        def _route_from_token_guard(state: IKIGAiStateDict) -> str:
            if state.get("error_type") == "TokenBudgetExceeded":
                return "error"
            return entry_point

        builder.add_conditional_edges(
            "_token_guard",
            _route_from_token_guard,
            {"error": "error", entry_point: entry_point},
        )

        # Sequential edges
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
            {"tag_and_persist": "tag_and_persist", "error": "error"},
        )
        builder.add_conditional_edges(
            "tag_and_persist",
            _route_after_tag_and_persist,
            {"reflect": "reflect", "error": "error"},
        )
        builder.add_conditional_edges(
            "reflect",
            _route_after_reflect,
            {"commit": "commit", "error": "error"},
        )

        builder.add_conditional_edges(
            "commit",
            _route_after_commit,
            {
                "error": "error",
                "dispatch_sub_agents": "dispatch_sub_agents",
            },
        )
        builder.add_conditional_edges(
            "dispatch_sub_agents",
            _route_after_dispatch_sub_agents,
            {
                "error": "error",
                "surface_intentions": "surface_intentions",
            },
        )

        builder.add_edge("surface_intentions", END)
        builder.add_edge("error", END)
        builder.set_entry_point("_token_guard")

        # Compile with checkpointer
        import sqlite3

        conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
        checkpointer = SqliteSaver(conn)

        compiled = builder.compile(checkpointer=checkpointer)
        compiled_any: Any = compiled
        compiled_any._ikigai_checkpoint_conn = conn
        compiled_any._ikigai_checkpoint_db = checkpoint_db
        compiled_any._ikigai_entry_point = entry_point
        span.set_attribute("nodes", len(NODES))
        return compiled_any


# ---------------------------------------------------------------------------
# Module-level singleton for langgraph dev
# ---------------------------------------------------------------------------
import os  # noqa: E402

_graph_instance = None


def graph() -> Any:
    """Return a singleton compiled graph instance for langgraph dev."""
    global _graph_instance
    if _graph_instance is None:
        db_path = os.environ.get("IKIGAI_CHECKPOINT_DB")
        _graph_instance = make_v2_graph(checkpoint_db=db_path)
    return _graph_instance


def close_graph() -> None:
    """Close the SqliteSaver connection held by the singleton graph."""
    global _graph_instance
    if _graph_instance is None:
        return
    conn = getattr(_graph_instance, "_ikigai_checkpoint_conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        try:
            delattr(_graph_instance, "_ikigai_checkpoint_conn")
        except Exception:
            pass
    _graph_instance = None


import atexit  # noqa: E402

atexit.register(close_graph)
