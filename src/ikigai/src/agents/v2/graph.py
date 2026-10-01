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

# Absolute imports (M102) so langgraph_api can load graph.py standalone
# without parent package. Previously used relative imports (`.nodes.X`)
# which broke under `langgraph dev` because the loader has no parent.
from src.ikigai.src.agents.v2.nodes.balance import balance_node
from src.ikigai.src.agents.v2.nodes.commit import commit_node
from src.ikigai.src.agents.v2.nodes.decompose import decompose_node
from src.ikigai.src.agents.v2.nodes.dep_graph import dep_graph_node
from src.ikigai.src.agents.v2.nodes.error import error_node
from src.ikigai.src.agents.v2.nodes.gantt_suggest import gantt_suggest_node
from src.ikigai.src.agents.v2.nodes.heuristics import heuristics_node
from src.ikigai.src.agents.v2.nodes.observe import observe_node
from src.ikigai.src.agents.v2.nodes.plan import plan_node
from src.ikigai.src.agents.v2.nodes.reason_node import reason_node
from src.ikigai.src.agents.v2.nodes.recall_node import recall_node
from src.ikigai.src.agents.v2.nodes.reflect import reflect_node
from src.ikigai.src.agents.v2.nodes.score_vectors import score_vectors_node
from src.ikigai.src.agents.v2.nodes.surface_intentions import surface_intentions_node
from src.ikigai.src.agents.v2.nodes.tag_and_persist import tag_and_persist_node
from src.ikigai.src.agents.v2.nodes.tag_propagation import tag_propagation_node
from src.ikigai.src.agents.v2.state import IKIGAiStateDict
from src.ikigai.src.agents.v2.subgraph import dispatch_sub_agents

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
    "recall",
    "reason",
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
    "tag_propagation",
    "dep_graph",
    "gantt_suggest",
)


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
) -> Literal["recall", "balance", "commit", "error"]:
    """After observe: recall context (per decision #9 — observe -> recall -> reason
    -> reflect -> commit chain), unless kill_switch or upstream error."""
    if state.get("error_type"):
        return "error"
    if state.get("kill_switch_triggered"):
        return "commit"
    return "recall"


def _route_after_recall(
    state: IKIGAiStateDict,
) -> Literal["reason", "error"]:
    """After recall: always proceed to reason unless upstream error fired."""
    if state.get("error_type"):
        return "error"
    return "reason"


def _route_after_reason(
    state: IKIGAiStateDict,
) -> Literal["reflect", "recall", "error"]:
    """After reason: proceed to reflect on validated proposal, otherwise loop back
    to recall to gather more context (reason->recall validation-failure loop).

    M88: Bound the recall<->reason loop. After MAX_REASON_LOOPS iterations,
    route to error (graceful failure) so the graph terminates. The
    originating_node + error_type fields let upstream callers diagnose
    why reason never produced a proposal.

    Note: route functions return a node name; error_node reads error
    fields from state. So we set them here as a side effect on the
    routing decision (only when we're routing to error).
    """
    if state.get("error_type"):
        return "error"
    draft = state.get("draft_proposal")
    if not draft:
        iteration = state.get("iteration", 0)
        if iteration >= MAX_REASON_LOOPS:
            # M88: populate error fields so error_node can produce a
            # useful commit_summary. These fields are normally set by
            # the safe_node wrapper; here we set them manually because
            # the loop-exit is a routing decision, not a node exception.
            state["originating_node"] = "reason"
            state["error_type"] = "ReasonLoopExhausted"
            state["error_message"] = (
                f"reason_node failed to produce draft_proposal after "
                f"{MAX_REASON_LOOPS} iterations (recall_node context "
                f"insufficient)"
            )
            return "error"
        return "recall"
    return "reflect"


# M88: cap on reason<->recall bounces before graceful termination.
# Without this, the v2 graph hangs because recall_node is a stub that
# never populates draft_proposal. Bound chosen at 3: gives 2 retries
# before forcing termination (matches LangGraph typical patterns).
MAX_REASON_LOOPS = 3


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
# M256: Optional taskdog-graph proposal nodes.
# Each is triggered by an explicit intent marker in state (set by observe
# or by an upstream planning skill). They run AFTER surface_intentions
# (the terminal for the standard pipeline) and only fire when the
# corresponding marker is present. Per ADR-013 they only PROPOSE — they
# never auto-execute writes; proposals go to the review queue.
# ---------------------------------------------------------------------------
def _has_taskdog_proposal_intent(state: IKIGAiStateDict, key: str) -> bool:
    """True if state carries a non-empty payload under `key`."""
    payload = state.get(key)
    return bool(payload) and isinstance(payload, dict)


def _route_after_surface_intentions(
    state: IKIGAiStateDict,
) -> Literal[
    "tag_propagation", "dep_graph", "gantt_suggest", "error"
]:
    """After surface_intentions: dispatch to the appropriate proposal node
    based on which intent marker is populated. Marker precedence:
      1. tag_propagation_input → tag_propagation
      2. dep_graph_input       → dep_graph
      3. gantt_input           → gantt_suggest
    Falls through (returns the first matching node, or routes via
    conditional map) — graph terminates via error→END if none match.
    """
    if state.get("error_type"):
        return "error"
    if _has_taskdog_proposal_intent(state, "tag_propagation_input"):
        return "tag_propagation"
    if _has_taskdog_proposal_intent(state, "dep_graph_input"):
        return "dep_graph"
    if _has_taskdog_proposal_intent(state, "gantt_input"):
        return "gantt_suggest"
    return "error"


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------
def _build_v2_graph(
    checkpoint_db: str | None = None,
    entry_point: str = "observe",
) -> Any:
    """Build the IKIGAi Maintainer StateGraph v2 (internal).

    Args:
        checkpoint_db: Path to SQLite file for SqliteSaver checkpointing.
                       If None, uses <project_root>/data/ikigai_checkpoints.db
        entry_point: Name of the node where the graph starts execution.
                     Must be one of NODES. Default: "observe" (full pipeline).
                     Skills (daily/weekly/monthly/quarterly) enter at specific
                     nodes to invoke partial pipelines.

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
        builder: StateGraph[IKIGAiStateDict, None, IKIGAiStateDict, IKIGAiStateDict] = StateGraph(
            IKIGAiStateDict
        )

        # Add nodes — wrapped in safe_node so exceptions populate error state
        builder.add_node("observe", _safe_node("observe", observe_node))
        builder.add_node("recall", _safe_node("recall", recall_node))
        builder.add_node("reason", _safe_node("reason", reason_node))
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
        # M256: optional taskdog-graph proposal nodes (tag_propagation,
        # dep_graph, gantt_suggest) — pure-Python, ADR-013 compliant.
        builder.add_node("tag_propagation", _safe_node("tag_propagation", tag_propagation_node))
        builder.add_node("dep_graph", _safe_node("dep_graph", dep_graph_node))
        builder.add_node("gantt_suggest", _safe_node("gantt_suggest", gantt_suggest_node))

        # Sequential edges
        builder.add_conditional_edges(
            "observe",
            _route_after_observe,
            {
                "recall": "recall",
                "balance": "balance",
                "commit": "commit",
                "error": "error",
            },
        )
        builder.add_conditional_edges(
            "recall",
            _route_after_recall,
            {"reason": "reason", "error": "error"},
        )
        builder.add_conditional_edges(
            "reason",
            _route_after_reason,
            {"reflect": "reflect", "recall": "recall", "error": "error"},
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
        # M256: route from surface_intentions to a taskdog-graph proposal
        # node only when an intent marker is populated. Otherwise END.
        builder.add_conditional_edges(
            "surface_intentions",
            _route_after_surface_intentions,
            {
                "tag_propagation": "tag_propagation",
                "dep_graph": "dep_graph",
                "gantt_suggest": "gantt_suggest",
                "error": "error",
            },
        )
        builder.add_edge("tag_propagation", END)
        builder.add_edge("dep_graph", END)
        builder.add_edge("gantt_suggest", END)
        builder.add_edge("error", END)
        builder.set_entry_point(entry_point)

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
# M102: `make_v2_graph` langgraph-api-compatible factory shim.
# langgraph_api (_factory_utils.py) requires graph factories to accept ONLY
# ServerRuntime and/or RunnableConfig (0/1/2 args). Our internal
# _build_v2_graph takes (checkpoint_db, entry_point), which is incompatible.
#
# This shim preserves backward compatibility with v2.py / invoke_skill.py
# (which still call _build_v2_graph(checkpoint_db=..., entry_point=...))
# while exposing make_v2_graph() to langgraph_api in the expected shape.
# ---------------------------------------------------------------------------


# Import concrete types up-front so langgraph_api can resolve annotations.
try:
    from langgraph_sdk.runtime import ServerRuntime as _ServerRuntime  # noqa: E402
    from langgraph_sdk.schema import Config as _RunnableConfig  # noqa: E402
    _HAS_SDK_TYPES = True
except ImportError:  # langgraph_sdk not installed in some envs
    _ServerRuntime = None  # type: ignore[assignment]
    _RunnableConfig = None  # type: ignore[assignment]
    _HAS_SDK_TYPES = False


# M102: `os` needed by make_v2_graph (was imported later for the singleton).
import os  # noqa: E402


def make_v2_graph(
    runtime: "_ServerRuntime | None" = None,
    config: "_RunnableConfig | None" = None,
) -> Any:
    """LangGraph-API-compatible factory for the IKIGAi Maintainer v2 graph.

    Per langgraph_api/_factory_utils.py: signature must accept ServerRuntime
    and/or RunnableConfig. Args are 0/1/2 (no more). The actual graph build
    is delegated to _build_v2_graph(checkpoint_db, entry_point).

    Args:
        runtime: ServerRuntime instance (langgraph_api passes this). Used
                 to extract config if not provided.
        config: RunnableConfig (langgraph_api passes this).

    Returns:
        Compiled StateGraph ready for .invoke() / .astream().
    """
    checkpoint_db = None
    entry_point = "observe"
    # Prefer config["configurable"] if available (langgraph_api convention).
    if config is not None:
        configurable = getattr(config, "configurable", None) or (
            config.get("configurable") if isinstance(config, dict) else None
        )
        if isinstance(configurable, dict):
            checkpoint_db = configurable.get("checkpoint_db") or checkpoint_db
            entry_point = configurable.get("entry_point") or entry_point
    if checkpoint_db is None:
        checkpoint_db = os.environ.get("IKIGAI_CHECKPOINT_DB")
    return _build_v2_graph(checkpoint_db=checkpoint_db, entry_point=entry_point)


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
        _graph_instance = make_v2_graph(config={"configurable": {"checkpoint_db": db_path}})
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
