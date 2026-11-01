"""Paperclip — make_paperclip_graph factory.

Assembles the 10-node meta-orchestrator graph (M180 added
``hil_apply_user_resolution`` between ``hil_pause`` and
``merge_user_resolution``):

    read_spec → spec_analyzer ⇄ (hil_pause → hil_apply_user_resolution → merge_user_resolution → spec_analyzer)
                           ↘
                            worktree_create → implement ⇄ (test fail → implement)
                                                ↘
                                                 worktree_commit → worktree_merge → worktree_cleanup → END

Patterns reused from v2 graph (``src/ikigai/src/agents/v2/graph.py``):

* ``make_<name>_graph(runtime, config)`` 2-arg signature mandated by
  ``langgraph_api/_factory_utils.py`` (M102).
* Internal ``_build_<name>_graph(checkpoint_db, entry_point)`` keeps
  things testable.
* ``_safe_node(name, fn)`` wrapper (graph.py:88-109 in v2) catches
  exceptions and populates the error channel instead of crashing.
* ``SqliteSaver(conn)`` checkpointer (graph.py:471-473 in v2).

New patterns introduced by Paperclip:

* ``interrupt()`` for true HIL pause (user resumes via
  ``Command(resume=...)``). v2 graph has no HIL — ``kill_switch`` is the
  closest existing pattern and is a binary abort, not user-input.
* Absolute imports per M102 (no relative ``.nodes.X`` which broke under
  ``langgraph dev``).
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
from src.ikigai.src.agents.paperclip.nodes.hil_pause import (
    hil_apply_user_resolution_node,
    hil_pause_node,
    merge_user_resolution_node,
)
from src.ikigai.src.agents.paperclip.nodes.implement import implement_node
from src.ikigai.src.agents.paperclip.nodes.read_spec import read_spec_node
from src.ikigai.src.agents.paperclip.nodes.spec_analyzer import spec_analyzer_node
from src.ikigai.src.agents.paperclip.nodes.worktree import (
    worktree_cleanup_node,
    worktree_commit_node,
    worktree_create_node,
    worktree_merge_node,
)
from src.ikigai.src.agents.paperclip.state import PaperclipStateDict

# ---------------------------------------------------------------------------
# Node names (must match add_node() calls below)
# ---------------------------------------------------------------------------
NODES = (
    "read_spec",
    "spec_analyzer",
    "hil_pause",
    "hil_apply_user_resolution",
    "merge_user_resolution",
    "worktree_create",
    "implement",
    "worktree_commit",
    "worktree_merge",
    "worktree_cleanup",
)


# ---------------------------------------------------------------------------
# _safe_node — mirrors v2/graph.py:88-109
# ---------------------------------------------------------------------------
def _safe_node(name: str, fn: Callable[[PaperclipStateDict], dict[str, Any]]) -> Any:
    """Wrap a node so exceptions populate the error channel."""

    def wrapper(state: PaperclipStateDict) -> dict[str, Any]:
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
def _route_after_read_spec(
    state: PaperclipStateDict,
) -> Literal["spec_analyzer", "error"]:
    if state.get("error_type"):
        return "error"
    return "spec_analyzer"


def _route_after_spec_analyzer(
    state: PaperclipStateDict,
) -> Literal["hil_pause", "worktree_create", "error"]:
    if state.get("error_type"):
        return "error"
    if state.get("spec_gaps"):
        return "hil_pause"
    return "worktree_create"


def _route_after_merge(
    state: PaperclipStateDict,
) -> Literal["spec_analyzer"]:
    # ``merge_user_resolution`` always loops back to ``spec_analyzer``.
    # Errors at this stage are caught by ``_safe_node`` and surface as
    # ``error_type`` — the next spec_analyzer call will see them and
    # route to ``error`` END via its own routing function.
    return "spec_analyzer"


def _route_after_hil_pause(
    state: PaperclipStateDict,
) -> Literal["hil_apply_user_resolution", "error"]:
    if state.get("error_type"):
        return "error"
    return "hil_apply_user_resolution"


def _route_after_hil_apply(
    state: PaperclipStateDict,
) -> Literal["merge_user_resolution", "error"]:
    if state.get("error_type"):
        return "error"
    return "merge_user_resolution"


def _route_after_worktree_create(
    state: PaperclipStateDict,
) -> Literal["implement", "error"]:
    if state.get("error_type"):
        return "error"
    return "implement"


def _route_after_implement(
    state: PaperclipStateDict,
) -> Literal["worktree_commit", "implement", "error"]:
    if state.get("error_type"):
        return "error"
    if state.get("tests_ok"):
        return "worktree_commit"
    # Tests failed (or pytest unavailable) — loop back to implement with
    # the test_output as additional context for the agent.
    return "implement"


def _route_after_commit(
    state: PaperclipStateDict,
) -> Literal["worktree_merge", "error"]:
    if state.get("error_type"):
        return "error"
    return "worktree_merge"


def _route_after_merge_wt(
    state: PaperclipStateDict,
) -> Literal["worktree_cleanup", "error"]:
    if state.get("error_type"):
        return "error"
    return "worktree_cleanup"


def _route_after_cleanup(
    state: PaperclipStateDict,
) -> Literal["__end__"]:
    # END is the literal "__end__" sentinel; cast pins it to the Literal.
    return cast(Literal["__end__"], END)


def _route_error(
    state: PaperclipStateDict,
) -> Literal["__end__"]:
    # Single common error END — all routes that detect error go here.
    return cast(Literal["__end__"], END)


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------
def _implement_with(adapter: Any) -> Callable[[PaperclipStateDict], dict[str, Any]]:
    """Bind an AgentAdapter to the ``implement`` node.

    ``implement_node`` takes the adapter as a keyword argument while the graph
    calls nodes with the state only, so the adapter is bound here. ``None``
    keeps the package default (``ClaudeAdapter``).
    """

    def node(state: PaperclipStateDict) -> dict[str, Any]:
        return implement_node(state, adapter=adapter)

    return node


def _build_paperclip_graph(
    *,
    checkpoint_db: str,
    entry_point: str,
    adapter: Any = None,
) -> Any:
    """Internal builder. The langgraph_api-compatible ``make_paperclip_graph``
    shim extracts ``checkpoint_db`` + ``entry_point`` from the runtime config
    and calls this function (M102 pattern).

    ``adapter`` is the AgentAdapter the ``implement`` node must invoke;
    ``None`` keeps the package default.
    """
    builder: StateGraph[PaperclipStateDict, None, PaperclipStateDict, PaperclipStateDict] = (
        StateGraph(PaperclipStateDict)
    )
    builder.add_node("read_spec", _safe_node("read_spec", read_spec_node))
    builder.add_node("spec_analyzer", _safe_node("spec_analyzer", spec_analyzer_node))
    builder.add_node("hil_pause", _safe_node("hil_pause", hil_pause_node))
    builder.add_node(
        "hil_apply_user_resolution",
        _safe_node("hil_apply_user_resolution", hil_apply_user_resolution_node),
    )
    builder.add_node(
        "merge_user_resolution",
        _safe_node("merge_user_resolution", merge_user_resolution_node),
    )
    builder.add_node(
        "worktree_create",
        _safe_node("worktree_create", worktree_create_node),
    )
    builder.add_node("implement", _safe_node("implement", _implement_with(adapter)))
    builder.add_node(
        "worktree_commit",
        _safe_node("worktree_commit", worktree_commit_node),
    )
    builder.add_node("worktree_merge", _safe_node("worktree_merge", worktree_merge_node))
    builder.add_node(
        "worktree_cleanup",
        _safe_node("worktree_cleanup", worktree_cleanup_node),
    )

    # Edges (each conditional edge has a fallback END via _route_error)
    builder.add_conditional_edges(
        "read_spec",
        _route_after_read_spec,
        {"spec_analyzer": "spec_analyzer", "error": END},
    )
    builder.add_conditional_edges(
        "spec_analyzer",
        _route_after_spec_analyzer,
        {
            "hil_pause": "hil_pause",
            "worktree_create": "worktree_create",
            "error": END,
        },
    )
    builder.add_conditional_edges(
        "hil_pause",
        _route_after_hil_pause,
        {"hil_apply_user_resolution": "hil_apply_user_resolution", "error": END},
    )
    builder.add_conditional_edges(
        "hil_apply_user_resolution",
        _route_after_hil_apply,
        {"merge_user_resolution": "merge_user_resolution", "error": END},
    )
    builder.add_conditional_edges(
        "merge_user_resolution",
        _route_after_merge,
        {"spec_analyzer": "spec_analyzer"},
    )
    builder.add_conditional_edges(
        "worktree_create",
        _route_after_worktree_create,
        {"implement": "implement", "error": END},
    )
    builder.add_conditional_edges(
        "implement",
        _route_after_implement,
        {
            "worktree_commit": "worktree_commit",
            "implement": "implement",
            "error": END,
        },
    )
    builder.add_conditional_edges(
        "worktree_commit",
        _route_after_commit,
        {"worktree_merge": "worktree_merge", "error": END},
    )
    builder.add_conditional_edges(
        "worktree_merge",
        _route_after_merge_wt,
        {"worktree_cleanup": "worktree_cleanup", "error": END},
    )
    builder.add_edge("worktree_cleanup", END)

    builder.set_entry_point(entry_point)

    # SqliteSaver checkpointer (mirrors v2 graph pattern).
    conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    compiled = builder.compile(checkpointer=checkpointer)

    # Attach diagnostics attrs so the runtime can introspect.
    compiled_any: Any = compiled
    compiled_any._paperclip_checkpoint_conn = conn
    compiled_any._paperclip_checkpoint_db = checkpoint_db
    compiled_any._paperclip_entry_point = entry_point
    compiled_any._paperclip_nodes = NODES
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


def make_paperclip_graph(
    runtime: _ServerRuntime | None = None,
    config: _RunnableConfig | None = None,
) -> Any:
    """LangGraph-API-compatible factory for the Paperclip meta-orchestrator.

    2-arg ``(runtime, config)`` signature mandated by ``langgraph_api/_factory_utils.py``.
    The actual graph build is delegated to ``_build_paperclip_graph`` so
    tests / scripts can call it directly with explicit args.

    Args:
        runtime: ``ServerRuntime`` instance (langgraph_api passes this).
        config: ``RunnableConfig`` (langgraph_api passes this). The factory
                looks for ``config["configurable"]["checkpoint_db"]`` and
                ``config["configurable"]["entry_point"]``.

    Returns:
        Compiled ``StateGraph`` ready for ``.invoke()`` / ``.astream()``.
    """
    checkpoint_db: str | None = None
    entry_point: str = "read_spec"
    if config is not None:
        configurable = getattr(config, "configurable", None) or (
            config.get("configurable") if isinstance(config, dict) else None
        )
        if isinstance(configurable, dict):
            checkpoint_db = configurable.get("checkpoint_db") or checkpoint_db
            entry_point = configurable.get("entry_point") or entry_point
    if checkpoint_db is None:
        checkpoint_db = os.environ.get("PAPERCLIP_CHECKPOINT_DB", "data/paperclip.db")
    return _build_paperclip_graph(checkpoint_db=checkpoint_db, entry_point=entry_point)
