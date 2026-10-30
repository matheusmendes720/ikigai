"""Paperclip Dynamic — ``make_dynamic_graph`` factory.

Assembles the 9-node meta-orchestrator graph (M191):

    classify → planner → harness_builder → subagent_1 ─┐
                                                   subagent_2 ─→ per_subagent_verifier
                                                   subagent_3 ─┘                          ─→ global_evaluator
                                                                                              ─→ synthesizer
                                                                                                  ─→ END

Patterns reused from Paperclip (``src/ikigai/src/agents/paperclip/graph.py``):

* ``make_<name>_graph(runtime, config)`` 2-arg signature mandated by
  ``langgraph_api/_factory_utils.py`` (M102).
* Internal ``_build_<name>_graph(checkpoint_db, entry_point)`` keeps
  things testable.
* ``_safe_node`` wrapper catches exceptions and populates the error
  channel instead of crashing.
* ``SqliteSaver(conn)`` checkpointer.

New patterns introduced by M191:

* **Static fan-out** with 3 sub-agent slots. The harness builder emits
  up to ``DEFAULT_MAX_SUBAGENTS`` tasks; the graph wires those slots
  into fixed nodes. Real dynamic graphs would use LangGraph's ``Send``
  API or subgraph injection; the MVP keeps a fixed skeleton.
* The sub-agent factory ``make_subagent_node(index)`` mirrors the
  pattern from ``v2/graph.py`` for prompt-chain nodes: one closure
  per slot, same code path, three different graph nodes.
"""

from __future__ import annotations

import os
import sqlite3
import traceback
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, cast

# M102: absolute paths so the factory loads without parent-package imports.
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from src.ikigai.src.agents.paperclip_dynamic.nodes.classify import classify_node
from src.ikigai.src.agents.paperclip_dynamic.nodes.global_evaluator import (
    global_evaluator_node,
)
from src.ikigai.src.agents.paperclip_dynamic.nodes.harness_builder import (
    harness_builder_node,
)
from src.ikigai.src.agents.paperclip_dynamic.nodes.per_subagent_verifier import (
    per_subagent_verifier_node,
)
from src.ikigai.src.agents.paperclip_dynamic.nodes.planner import (
    get_default_subagent_count,
    planner_node,
)
from src.ikigai.src.agents.paperclip_dynamic.nodes.subagent import make_subagent_node
from src.ikigai.src.agents.paperclip_dynamic.nodes.synthesizer import synthesizer_node
from src.ikigai.src.agents.paperclip_dynamic.state import DynamicWorkflowState

# ---------------------------------------------------------------------------
# Node names (must match add_node() calls below)
# ---------------------------------------------------------------------------
# Static fan-out: 3 sub-agent slots in MVP. The planner caps at this
# count; extras are warned + dropped.
_MAX_SUBAGENT_SLOTS = 3
SUBAGENT_SLOT_NAMES: tuple[str, ...] = tuple(
    f"subagent_{i + 1}" for i in range(_MAX_SUBAGENT_SLOTS)
)

NODES: tuple[str, ...] = (
    "classify",
    "planner",
    "harness_builder",
    *SUBAGENT_SLOT_NAMES,
    "per_subagent_verifier",
    "global_evaluator",
    "synthesizer",
)


# ---------------------------------------------------------------------------
# _safe_node — mirrors paperclip/graph.py and v2/graph.py:88-109
# ---------------------------------------------------------------------------
def _safe_node(name: str, fn: Callable[[DynamicWorkflowState], dict[str, Any]]) -> Any:
    """Wrap a node so exceptions populate the error channel."""

    def wrapper(state: DynamicWorkflowState) -> dict[str, Any]:
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
# Conditional-edge routing
# ---------------------------------------------------------------------------
def _route_after_classify(
    state: DynamicWorkflowState,
) -> Literal["planner", "error"]:
    if state.get("error_type"):
        return "error"
    return "planner"


def _route_after_planner(
    state: DynamicWorkflowState,
) -> Literal["harness_builder", "error"]:
    if state.get("error_type"):
        return "error"
    return "harness_builder"


def _route_after_harness_builder(
    state: DynamicWorkflowState,
) -> Literal["subagent_1", "error"]:
    if state.get("error_type"):
        return "error"
    # Always advance to slot 1 first; the other slots are dispatched
    # via the _route_after_subagent_N edges.
    return "subagent_1"


def _route_after_subagent(
    slot_index: int,
) -> Callable[[DynamicWorkflowState], Literal["per_subagent_verifier", "subagent_loop", "error"]]:
    """Build the post-sub-agent routing function for slot ``slot_index``.

    Final slot (last one) → ``per_subagent_verifier``. Earlier slots →
    next slot (``subagent_<slot_index + 1>``). Linear chain, not
    parallel — the static fan-out is sequential because LangGraph
    single-threaded runtime advances one node at a time.
    """

    def route(
        state: DynamicWorkflowState,
    ) -> Literal["per_subagent_verifier", "subagent_loop", "error"]:
        if state.get("error_type"):
            return "error"
        if slot_index >= _MAX_SUBAGENT_SLOTS - 1:
            return "per_subagent_verifier"
        # 1-indexed labels — the dynamic slot name is cast to the declared
        # Literal so the conditional-edge map keeps a statically-known set
        # of possible destinations.
        return cast(
            Literal["per_subagent_verifier", "subagent_loop", "error"],
            f"subagent_{slot_index + 2}",
        )

    return route


def _route_after_verifier(
    state: DynamicWorkflowState,
) -> Literal["global_evaluator", "error"]:
    if state.get("error_type"):
        return "error"
    return "global_evaluator"


def _route_after_global_evaluator(
    state: DynamicWorkflowState,
) -> Literal["synthesizer", "error"]:
    if state.get("error_type"):
        return "error"
    return "synthesizer"


def _route_after_synthesizer(
    state: DynamicWorkflowState,
) -> Literal["__end__"]:
    # END is the literal "__end__" sentinel; cast pins it to the Literal.
    return cast(Literal["__end__"], END)


def _route_error(
    state: DynamicWorkflowState,
) -> Literal["__end__"]:
    return cast(Literal["__end__"], END)


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------
def _build_dynamic_graph(
    *,
    checkpoint_db: str,
    entry_point: str,
) -> Any:
    """Internal builder. The langgraph_api-compatible ``make_dynamic_graph``
    shim extracts ``checkpoint_db`` + ``entry_point`` from the runtime
    config and calls this function (M102 pattern).
    """
    builder: StateGraph[DynamicWorkflowState, None, DynamicWorkflowState, DynamicWorkflowState] = (
        StateGraph(DynamicWorkflowState)
    )
    builder.add_node("classify", _safe_node("classify", classify_node))
    builder.add_node("planner", _safe_node("planner", planner_node))
    builder.add_node("harness_builder", _safe_node("harness_builder", harness_builder_node))

    # Sub-agent slots — one node per slot index, all wired through
    # ``make_subagent_node``. Real dynamic graphs would use Send API
    # or subgraph injection; MVP keeps a fixed skeleton of 3 slots.
    for i, slot_name in enumerate(SUBAGENT_SLOT_NAMES):
        builder.add_node(slot_name, _safe_node(slot_name, make_subagent_node(i)))

    builder.add_node(
        "per_subagent_verifier",
        _safe_node("per_subagent_verifier", per_subagent_verifier_node),
    )
    builder.add_node(
        "global_evaluator",
        _safe_node("global_evaluator", global_evaluator_node),
    )
    builder.add_node("synthesizer", _safe_node("synthesizer", synthesizer_node))

    # Edges
    builder.add_conditional_edges(
        "classify",
        _route_after_classify,
        {"planner": "planner", "error": END},
    )
    builder.add_conditional_edges(
        "planner",
        _route_after_planner,
        {"harness_builder": "harness_builder", "error": END},
    )
    builder.add_conditional_edges(
        "harness_builder",
        _route_after_harness_builder,
        {"subagent_1": "subagent_1", "error": END},
    )

    # Sub-agent chain — slot N routes to slot N+1 until the final
    # slot routes to the per-subagent verifier.
    for i in range(_MAX_SUBAGENT_SLOTS):
        if i < _MAX_SUBAGENT_SLOTS - 1:
            # Not the last slot — chain to next slot.
            next_slot = SUBAGENT_SLOT_NAMES[i + 1]
            builder.add_conditional_edges(
                SUBAGENT_SLOT_NAMES[i],
                _route_after_subagent(i),
                {
                    "per_subagent_verifier": "per_subagent_verifier",
                    "subagent_loop": next_slot,
                    "error": END,
                },
            )
        else:
            # Last slot — chain to verifier.
            builder.add_conditional_edges(
                SUBAGENT_SLOT_NAMES[i],
                _route_after_subagent(i),
                {
                    "per_subagent_verifier": "per_subagent_verifier",
                    "error": END,
                },
            )

    builder.add_conditional_edges(
        "per_subagent_verifier",
        _route_after_verifier,
        {"global_evaluator": "global_evaluator", "error": END},
    )
    builder.add_conditional_edges(
        "global_evaluator",
        _route_after_global_evaluator,
        {"synthesizer": "synthesizer", "error": END},
    )
    builder.add_edge("synthesizer", END)

    builder.set_entry_point(entry_point)

    # SqliteSaver checkpointer (mirrors paperclip + v2 graph pattern).
    conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    compiled = builder.compile(checkpointer=checkpointer)

    # Attach diagnostics attrs so the runtime can introspect.
    compiled_any: Any = compiled
    compiled_any._paperclip_dynamic_checkpoint_conn = conn
    compiled_any._paperclip_dynamic_checkpoint_db = checkpoint_db
    compiled_any._paperclip_dynamic_entry_point = entry_point
    compiled_any._paperclip_dynamic_nodes = NODES
    return compiled_any


# ---------------------------------------------------------------------------
# LangGraph-API-compatible factory shim (M102 pattern)
# ---------------------------------------------------------------------------
# Import concrete types up-front so langgraph_api can resolve annotations.
#
# TYPE_CHECKING branch: give mypy a concrete, fully-parameterized
# `ServerRuntime` alias (`ServerRuntime` is a generic TypeAliasType, so a
# bare `_ServerRuntime | None` annotation trips the type-arg check). The
# runtime branch keeps the original try/except so an env without
# langgraph_sdk still imports cleanly.
if TYPE_CHECKING:
    from langgraph_sdk.runtime import ServerRuntime as _ServerRuntimeT
    from langgraph_sdk.schema import Config as _RunnableConfig

    _ServerRuntime = _ServerRuntimeT[Any]
    _HAS_SDK_TYPES = True
else:
    try:
        from langgraph_sdk.runtime import ServerRuntime as _ServerRuntime
        from langgraph_sdk.schema import Config as _RunnableConfig

        _HAS_SDK_TYPES = True
    except ImportError:  # langgraph_sdk not installed in some envs
        _ServerRuntime = None
        _RunnableConfig = None
        _HAS_SDK_TYPES = False


def make_dynamic_graph(
    runtime: _ServerRuntime | None = None,
    config: _RunnableConfig | None = None,
) -> Any:
    """LangGraph-API-compatible factory for the Paperclip Dynamic graph.

    2-arg ``(runtime, config)`` signature mandated by ``langgraph_api/
    _factory_utils.py``. The actual graph build is delegated to
    ``_build_dynamic_graph`` so tests / scripts can call it directly
    with explicit args.

    Args:
        runtime: ``ServerRuntime`` instance (langgraph_api passes this).
        config: ``RunnableConfig`` (langgraph_api passes this). The factory
                looks for ``config["configurable"]["checkpoint_db"]`` and
                ``config["configurable"]["entry_point"]``.

    Returns:
        Compiled ``StateGraph`` ready for ``.invoke()`` / ``.astream()``.
    """
    checkpoint_db: str | None = None
    entry_point: str = "classify"
    if config is not None:
        configurable = getattr(config, "configurable", None) or (
            config.get("configurable") if isinstance(config, dict) else None
        )
        if isinstance(configurable, dict):
            checkpoint_db = configurable.get("checkpoint_db") or checkpoint_db
            entry_point = configurable.get("entry_point") or entry_point
    if checkpoint_db is None:
        checkpoint_db = os.environ.get(
            "PAPERCLIP_DYNAMIC_CHECKPOINT_DB", "data/paperclip_dynamic.db"
        )
    return _build_dynamic_graph(checkpoint_db=checkpoint_db, entry_point=entry_point)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------
def get_subagent_slot_names() -> tuple[str, ...]:
    """Return the static sub-agent slot names in registration order."""
    return SUBAGENT_SLOT_NAMES


def get_max_subagent_slots() -> int:
    """Return the static fan-out count for the MVP skeleton."""
    return _MAX_SUBAGENT_SLOTS


def get_planner_max_subagents() -> int:
    """Return the planner's default max sub-agent count.

    Both the planner's default and the graph's static slot count
    must stay in sync; the planner caps to ``get_max_subagent_slots()``
    so the fan-out math is consistent.
    """
    return min(get_default_subagent_count(), _MAX_SUBAGENT_SLOTS)
