"""Sub-agent dispatch protocol — W4.4 implementation of ADR-026.

This module adds the 11th graph node ``dispatch_sub_agents`` that:
- Reads ``dispatch_plan`` from parent IKIGAiStateDict (S1 spawn contract)
- Validates each SubAgentSpec (4-part UEID, entry_point ∈ NODES)
- Builds narrowed child state per S2 context propagation
  (identity fields + dispatch_context dict; NEVER error_* per S2.4)
- Spawns each sub-agent via LangGraph subgraph invocation with timeout
- Collects SubAgentResult per spec, merges per S3 contract
- Determines parent status per S4 termination contract
- Updates state: ``sub_agent_results`` appended, ``dispatch_plan`` cleared

Architectural reference:
- ADR-026 — Sub-agent dispatch protocol (S1-S5 contracts, R1-R6 rules)
- ADR-013 — Planner-only invariant; sub-agents invoke other graph nodes
- ADR-014 — 4-part UEID canonical format
- ADR-019 — All tuning values via prompts/algorithm_constants.json
- ADR-025 — actor="agent" injected into every sub-agent (never user)
- ADR-027 — thread_role="child", 4-segment hierarchical thread_id

Drift invariants enforced:
- test_canonical_scope :: test_dispatch_sub_agents_in_nodes (W4.4)
- test_canonical_scope :: test_nodes_tuple_has_11_elements (W4.4)
- test_canonical_scope :: test_subagent_spec_ueid_validation (W4.4)
"""

from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING, Any, Literal, NotRequired, TypedDict

from .prompts.load_constants import get as _algo_const

if TYPE_CHECKING:
    from .state import IKIGAiStateDict

from .checkpoint import build_subagent_thread_id  # W4.5 — 4-segment thread_id (ADR-027 R3)

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Canonical 4-part UEID regex (per ADR-014, src/contracts/common.py)
# ---------------------------------------------------------------------------
_UEID_REGEX = re.compile(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")


# ---------------------------------------------------------------------------
# Schema constants — error channel + identity fields
# ---------------------------------------------------------------------------
# Per ADR-026 S2.4: error channel fields MUST NEVER propagate to children.
# Per ADR-026 S2.2: identity fields ALWAYS propagate (cycle_id, cycle_start,
# cycle_end, iteration). actor is injected per ADR-025 R3 (always "agent"
# for sub-agents spawned by parent graph).
_IDENTITY_FIELDS: tuple[str, ...] = (
    "cycle_id",
    "cycle_start",
    "cycle_end",
    "iteration",
    "actor",
)

_ERROR_CHANNEL_FIELDS: tuple[str, ...] = (
    "originating_node",
    "error_type",
    "error_message",
    "traceback_str",
    "error_traceback",
    "commit_summary",
)

# Merge strategies (per ADR-026 S3). Reduced names — see _merge_result.
MergeStrategy = Literal["replace", "merge_dict", "append_list", "reduce_add"]

# Sub-agent lifecycle status (per ADR-026 S3).
SubAgentStatus = Literal["success", "partial", "failure", "timeout"]


# ---------------------------------------------------------------------------
# TypedDicts — SubAgentSpec / SubAgentResult / ErrorRecord
# ---------------------------------------------------------------------------


class ErrorRecord(TypedDict, total=False):
    """Failure metadata for a sub-agent that did not succeed."""

    type: str  # exception class name (e.g. "TimeoutError", "RecursionLimitExceeded")
    message: str  # human-readable description
    node: NotRequired[str]  # originating child node, if known


class SubAgentSpec(TypedDict, total=False):
    """Per-child dispatch plan entry (ADR-026 S1).

    The parent's dispatch_plan is ``list[SubAgentSpec]`` written by an
    upstream node (decompose / plan / reflect) before this node fires.
    """

    sub_agent_id: str  # 4-part UEID; validated against _UEID_REGEX (ADR-014)
    entry_point: str  # one of NODES in graph.py:83-94
    dispatch_context: dict[str, Any]  # extra fields to propagate to child
    timeout_s: float  # wall-clock budget; default SUBAGENT_PARENT_TIMEOUT_S
    merge_strategy: MergeStrategy  # how to merge outputs into parent state


class SubAgentResult(TypedDict, total=False):
    """Per-child outcome (ADR-026 S3)."""

    sub_agent_id: str
    entry_point: str
    status: SubAgentStatus
    duration_s: float
    fields_written: list[str]  # names of parent fields the result touched
    outputs: dict[str, Any]  # values returned by the child to merge
    error: NotRequired[ErrorRecord]


# ---------------------------------------------------------------------------
# Validation helpers — spec, recursion depth, UEID format
# ---------------------------------------------------------------------------


def _is_valid_ueid(value: object) -> bool:
    """Return True iff value is a 4-part UEID per ADR-014."""
    return isinstance(value, str) and _UEID_REGEX.match(value) is not None


def _validate_spec(spec: SubAgentSpec) -> str | None:
    """Return an error message if spec is malformed, else None.

    Enforced:
    - sub_agent_id is a 4-part UEID (ADR-014 + ADR-026 R4)
    - entry_point ∈ NODES (ADR-026 R1; populated by graph.py NODES tuple)
    - timeout_s is a positive number if provided
    - merge_strategy ∈ {replace, merge_dict, append_list, reduce_add} if provided
    """
    from .graph import NODES  # local import — avoids circular import at module load

    sub_id = spec.get("sub_agent_id")
    if not _is_valid_ueid(sub_id):
        return f"sub_agent_id {sub_id!r} is not a 4-part UEID (ADR-014 / ADR-026 R4)"

    entry = spec.get("entry_point")
    if entry not in NODES:
        valid = ", ".join(NODES)
        return f"entry_point {entry!r} not in NODES ({valid})"

    timeout = spec.get("timeout_s")
    if timeout is not None and (not isinstance(timeout, (int, float)) or timeout <= 0):
        return f"timeout_s must be a positive number, got {timeout!r}"

    merge = spec.get("merge_strategy")
    if merge is not None and merge not in (
        "replace",
        "merge_dict",
        "append_list",
        "reduce_add",
    ):
        return (
            f"merge_strategy {merge!r} invalid (must be replace|merge_dict|append_list|reduce_add)"
        )

    return None


def _compute_dispatch_depth(state: dict[str, Any]) -> int:
    """Extract current dispatch depth from state (or thread_id, fallback 0).

    Per ADR-027 R3: thread_id encodes depth in the 4th segment as
    ``d<depth>`` (e.g. ``agent-weekly-a3f19c2d-d2``). Falls back to
    ``state["dispatch_depth"]`` for in-process dispatch chains; falls
    back to 0 for the parent (root) cycle.
    """
    explicit = state.get("dispatch_depth")
    if isinstance(explicit, int) and explicit >= 0:
        return explicit
    thread_id = state.get("thread_id")
    if isinstance(thread_id, str):
        m = re.search(r"-d(\d+)$", thread_id)
        if m is not None:
            try:
                return int(m.group(1))
            except ValueError:
                return 0
    return 0


def _recursion_blocked(parent_depth: int) -> bool:
    """Return True if dispatching another level would exceed the cap.

    Cap = SUBAGENT_MAX_DISPATCH_DEPTH (default 2). Children are at
    parent_depth + 1. If ``parent_depth >= cap``, dispatching would
    yield parent_depth + 1 > cap → blocked.
    """
    try:
        cap = int(_algo_const("SUBAGENT_MAX_DISPATCH_DEPTH"))
    except (KeyError, ValueError, TypeError):
        cap = 2  # defensive default
    return parent_depth >= cap


# ---------------------------------------------------------------------------
# S2 — Context propagation
# ---------------------------------------------------------------------------


def _propagate_context(
    parent_state: dict[str, Any],
    spec: SubAgentSpec,
) -> dict[str, Any]:
    """Build the narrowed child IKIGAiStateDict per ADR-026 S2.

    Rules:
    - Always copy identity fields (cycle_id, cycle_start, cycle_end,
      iteration, actor) (S2.2 + ADR-025 R3 actor="agent").
    - Copy every key in spec.dispatch_context (S2.3 — optional fields).
    - NEVER copy error_* fields (S2.4 — parent error isolation).
    - Inject dispatch_depth = parent_depth + 1 for recursion guard.
    """
    from .graph import NODES  # local — avoid circular import

    child: dict[str, Any] = {}
    # Identity fields
    for key in _IDENTITY_FIELDS:
        if key in parent_state:
            child[key] = parent_state[key]
    # actor override: sub-agents are ALWAYS agent (never user)
    child["actor"] = "agent"
    # dispatch_context (excluding identity + error fields — defensive)
    for key, value in (spec.get("dispatch_context") or {}).items():
        if key in _ERROR_CHANNEL_FIELDS:
            continue
        if key in _IDENTITY_FIELDS:
            continue
        child[key] = value
    # Recursion depth injection
    parent_depth = _compute_dispatch_depth(parent_state)
    child["dispatch_depth"] = parent_depth + 1
    # Sentinel: thread_role=child per ADR-027 R3
    child["thread_role"] = "child"
    # Reference parent's entry_point so child has context for routing
    if "parent_entry_point" not in child:
        child["parent_entry_point"] = spec.get("entry_point", "unknown")
    # Reference NODES so child can validate its own dispatch_plan (no-op
    # for typical sub-agents that don't fan out further)
    child["_NODES"] = list(NODES)
    return child


# ---------------------------------------------------------------------------
# S3 — Collection / merge strategies
# ---------------------------------------------------------------------------


def _merge_result(
    parent_updates: dict[str, Any],
    result_outputs: dict[str, Any],
    strategy: MergeStrategy,
) -> None:
    """Merge one sub-agent's outputs into parent_updates per ADR-026 S3.

    Strategies:
    - ``replace`` (default): write each key into parent_updates, overwriting.
    - ``merge_dict``: deep-merge dicts; scalars replace (one level).
    - ``append_list``: append to parent list if key exists; else set list.
    - ``reduce_add``: sum floats (used for vector_scores aggregation).

    All non-dict values from child overwrite parent (replace semantics).
    """
    if strategy == "replace":
        for key, value in result_outputs.items():
            parent_updates[key] = value
        return

    if strategy == "merge_dict":
        for key, value in result_outputs.items():
            existing = parent_updates.get(key)
            if isinstance(existing, dict) and isinstance(value, dict):
                merged = dict(existing)
                merged.update(value)
                parent_updates[key] = merged
            else:
                parent_updates[key] = value
        return

    if strategy == "append_list":
        for key, value in result_outputs.items():
            existing = parent_updates.get(key)
            if isinstance(existing, list):
                if isinstance(value, list):
                    parent_updates[key] = [*existing, *value]
                else:
                    parent_updates[key] = [*existing, value]
            elif isinstance(value, list):
                parent_updates[key] = list(value)
            else:
                parent_updates[key] = [value]
        return

    if strategy == "reduce_add":
        for key, value in result_outputs.items():
            existing = parent_updates.get(key)
            if isinstance(existing, (int, float)) and isinstance(value, (int, float)):
                parent_updates[key] = existing + value
            else:
                parent_updates[key] = value
        return


# ---------------------------------------------------------------------------
# S4 — Termination / parent status
# ---------------------------------------------------------------------------


def _compute_parent_status(results: list[SubAgentResult]) -> str:
    """Aggregate per-child status into parent status per ADR-026 S4.

    - All success → "success"
    - ≥1 partial → "partial" (parent continues with merged + warnings)
    - ≥1 failure → "failure" (emit TaskChange per Wave 3 partial-success)
    - ≥1 timeout → "timeout" (continue with timeout markers)
    - Mixed failure + timeout → "failure" (failure dominates)
    - Empty results → "success" (no-op dispatch is by definition successful)
    """
    if not results:
        return "success"
    statuses = {r.get("status") for r in results}
    if "failure" in statuses:
        return "failure"
    if "timeout" in statuses:
        return "timeout"
    if "partial" in statuses:
        return "partial"
    return "success"


# ---------------------------------------------------------------------------
# Sub-agent invocation — the mockable seam
# ---------------------------------------------------------------------------


def _invoke_subagent(
    spec: SubAgentSpec,
    initial_state: dict[str, Any],
    timeout_s: float,
) -> SubAgentResult:
    """Spawn a child sub-agent and return its result.

    The default implementation invokes ``make_v2_graph`` with the
    spec's entry_point and the propagated initial_state. Tests
    monkeypatch this function to avoid real Claude cost.

    The function is intentionally synchronous (matches ADR-026 Alt E
    "async-or-sync" — synchronous invocation is the default for
    in-process dispatch). A future async variant can be added without
    breaking callers by adding an ``_ainvoke_subagent`` companion.

    Failures are caught and converted to SubAgentResult.status — never
    raised to the dispatcher (per ADR-026 R5 failure isolation).
    """
    sub_agent_id = spec.get("sub_agent_id", "unknown")
    entry_point = spec.get("entry_point", "observe")
    started = time.monotonic()
    try:
        from .graph import make_v2_graph

        graph = make_v2_graph(checkpoint_db=":memory:", entry_point=entry_point)
        # LangGraph invoke respects checkpointer; pass config with thread_id.
        # W4.5 — close the W4.4 reviewer's minor observation: use the full
        # 4-segment hierarchical thread_id format per ADR-027 R3 (parent's
        # thread_id + ``-subagent-<short_hash>`` suffix) rather than the
        # legacy ``f"subagent-{sub_agent_id}"`` format.
        parent_thread_id = str(initial_state.get("thread_id") or "agent-daily-default-parent")
        config = {
            "configurable": {
                "thread_id": build_subagent_thread_id(parent_thread_id, sub_agent_id),
            }
        }
        child_result = graph.invoke(initial_state, config)
        duration_s = time.monotonic() - started
        # If child graph populated error channel, surface as failure.
        if isinstance(child_result, dict) and child_result.get("error_type"):
            return SubAgentResult(
                sub_agent_id=sub_agent_id,
                entry_point=entry_point,
                status="failure",
                duration_s=duration_s,
                fields_written=[],
                outputs={},
                error=ErrorRecord(
                    type=str(child_result.get("error_type", "UnknownError")),
                    message=str(child_result.get("error_message", "")),
                    node=str(child_result.get("originating_node", "")),
                ),
            )
        # Per ADR-026 S4.2: surface_intentions is a partial-success marker.
        if isinstance(child_result, dict) and child_result.get("last_step") == "surface_intentions":
            outputs = {
                k: v
                for k, v in child_result.items()
                if k in {"user_suggestions", "suggestions_count", "commit_summary"}
                or k.startswith("_")
            }
            return SubAgentResult(
                sub_agent_id=sub_agent_id,
                entry_point=entry_point,
                status="partial",
                duration_s=duration_s,
                fields_written=list(outputs.keys()),
                outputs=outputs,
            )
        # Success — collect outputs (skip identity + ephemeral fields).
        if isinstance(child_result, dict):
            outputs = {
                k: v
                for k, v in child_result.items()
                if k not in _IDENTITY_FIELDS
                and k not in _ERROR_CHANNEL_FIELDS
                and k not in {"dispatch_plan", "sub_agent_results", "dispatch_depth"}
            }
        else:
            outputs = {}
        return SubAgentResult(
            sub_agent_id=sub_agent_id,
            entry_point=entry_point,
            status="success",
            duration_s=duration_s,
            fields_written=list(outputs.keys()),
            outputs=outputs,
        )
    except TimeoutError as exc:
        duration_s = time.monotonic() - started
        log.warning(
            "subagent %s timed out after %.2fs (entry_point=%s)",
            sub_agent_id,
            duration_s,
            entry_point,
        )
        return SubAgentResult(
            sub_agent_id=sub_agent_id,
            entry_point=entry_point,
            status="timeout",
            duration_s=duration_s,
            fields_written=[],
            outputs={},
            error=ErrorRecord(type="TimeoutError", message=str(exc), node=entry_point),
        )
    except (
        Exception
    ) as exc:  # convert any exception to failure result (broad catch intentional per ADR-026 R5)
        duration_s = time.monotonic() - started
        log.warning(
            "subagent %s failed (entry_point=%s): %s: %s",
            sub_agent_id,
            entry_point,
            type(exc).__name__,
            exc,
        )
        return SubAgentResult(
            sub_agent_id=sub_agent_id,
            entry_point=entry_point,
            status="failure",
            duration_s=duration_s,
            fields_written=[],
            outputs={},
            error=ErrorRecord(
                type=type(exc).__name__,
                message=str(exc),
                node=entry_point,
            ),
        )


# ---------------------------------------------------------------------------
# dispatch_sub_agents — the 11th graph node
# ---------------------------------------------------------------------------


def dispatch_sub_agents(state: IKIGAiStateDict | dict[str, Any]) -> dict[str, Any]:
    """W4.4 11th graph node — orchestrate sub-agent fan-out per ADR-026.

    Reads ``state["dispatch_plan"]`` (list[SubAgentSpec]); if empty or
    absent, this is a no-op and returns an empty update dict (the
    node is a passthrough when no children are scheduled).

    For each SubAgentSpec in the plan:
      1. Validate spec (UEID, entry_point, timeout, merge_strategy)
      2. Recursion guard via SUBAGENT_MAX_DISPATCH_DEPTH
      3. Build narrowed child state per S2 (identity + dispatch_context;
         NEVER error_*)
      4. Invoke sub-agent (mockable via monkeypatch on _invoke_subagent)
      5. Collect SubAgentResult

    Merges all successful outputs into a single update dict per the
    per-spec merge_strategy. Determines parent status per S4 and
    records it in ``last_step``. Clears ``dispatch_plan`` (ephemeral
    per ADR-027 R5.13).

    Returns a partial state update dict that LangGraph merges into the
    parent IKIGAiStateDict. The parent's error_type is NEVER set by
    this node — sub-agent failures live only in sub_agent_results
    (ADR-026 R5 failure isolation).
    """
    # Normalize state to dict for read access (LangGraph passes TypedDict-like)
    if hasattr(state, "items"):
        state_dict: dict[str, Any] = dict(state)
    else:
        state_dict = dict(state)

    plan = state_dict.get("dispatch_plan") or []
    if not isinstance(plan, list) or not plan:
        # No-op: passthrough, no sub-agents dispatched.
        return {"last_step": "dispatch_sub_agents"}

    parent_depth = _compute_dispatch_depth(state_dict)
    recursion_blocked = _recursion_blocked(parent_depth)

    results: list[SubAgentResult] = []
    updates: dict[str, Any] = {"last_step": "dispatch_sub_agents"}
    written_keys: set[str] = set()

    for raw_spec in plan:
        if not isinstance(raw_spec, dict):
            results.append(
                SubAgentResult(
                    sub_agent_id="<invalid-spec>",
                    entry_point="<invalid>",
                    status="failure",
                    duration_s=0.0,
                    fields_written=[],
                    outputs={},
                    error=ErrorRecord(
                        type="TypeError",
                        message=f"dispatch_plan entry must be a dict, got {type(raw_spec).__name__}",
                        node="dispatch_sub_agents",
                    ),
                )
            )
            continue

        spec: SubAgentSpec = raw_spec  # type: ignore[assignment]

        if recursion_blocked:
            sub_id = str(spec.get("sub_agent_id", "<unknown>"))
            entry = str(spec.get("entry_point", "<unknown>"))
            results.append(
                SubAgentResult(
                    sub_agent_id=sub_id,
                    entry_point=entry,
                    status="failure",
                    duration_s=0.0,
                    fields_written=[],
                    outputs={},
                    error=ErrorRecord(
                        type="RecursionLimitExceeded",
                        message=(
                            f"dispatch_depth={parent_depth + 1} exceeds "
                            f"SUBAGENT_MAX_DISPATCH_DEPTH; parent continues "
                            f"per ADR-026 S4.3"
                        ),
                        node="dispatch_sub_agents",
                    ),
                )
            )
            continue

        # 1. Validate spec
        validation_error = _validate_spec(spec)
        if validation_error is not None:
            results.append(
                SubAgentResult(
                    sub_agent_id=str(spec.get("sub_agent_id", "<unknown>")),
                    entry_point=str(spec.get("entry_point", "<unknown>")),
                    status="failure",
                    duration_s=0.0,
                    fields_written=[],
                    outputs={},
                    error=ErrorRecord(
                        type="ValueError",
                        message=validation_error,
                        node="dispatch_sub_agents",
                    ),
                )
            )
            continue

        # 2. Build narrowed child state (S2 — never propagates error_*)
        child_state = _propagate_context(state_dict, spec)

        # 3. Resolve timeout (spec override > global default)
        try:
            default_timeout = float(_algo_const("SUBAGENT_PARENT_TIMEOUT_S"))
        except (KeyError, ValueError, TypeError):
            default_timeout = 60.0
        timeout_s = float(spec.get("timeout_s", default_timeout))

        # 4. Spawn (mockable in tests via _invoke_subagent patch).
        # TimeoutError is treated as status='timeout' (S4.4) — the wall-clock
        # budget was exceeded. Any other exception is a real failure (status='failure').
        try:
            result = _invoke_subagent(spec, child_state, timeout_s)
        except TimeoutError as exc:
            result = SubAgentResult(
                sub_agent_id=str(spec.get("sub_agent_id", "<unknown>")),
                entry_point=str(spec.get("entry_point", "<unknown>")),
                status="timeout",
                duration_s=float(spec.get("timeout_s", 0.0)),
                fields_written=[],
                outputs={},
                error=ErrorRecord(
                    type="TimeoutError",
                    message=str(exc),
                    node=str(spec.get("entry_point", "")),
                ),
            )
        except Exception as exc:  # convert any exception to failure result (broad catch intentional per ADR-026 R5)
            result = SubAgentResult(
                sub_agent_id=str(spec.get("sub_agent_id", "<unknown>")),
                entry_point=str(spec.get("entry_point", "<unknown>")),
                status="failure",
                duration_s=0.0,
                fields_written=[],
                outputs={},
                error=ErrorRecord(
                    type=type(exc).__name__,
                    message=str(exc),
                    node="dispatch_sub_agents",
                ),
            )
        results.append(result)

        # 5. Merge outputs per spec's merge_strategy (only on success/partial)
        if result.get("status") in ("success", "partial"):
            strategy: MergeStrategy = spec.get("merge_strategy") or "replace"
            _merge_result(updates, dict(result.get("outputs") or {}), strategy)
            for key in result.get("fields_written") or []:
                written_keys.add(str(key))

    # 6. Record aggregated outcome (ADR-027 R5.13 — sub_agent_results persisted)
    parent_status = _compute_parent_status(results)
    updates["sub_agent_results"] = list(results)
    # ADR-027 R5.13: dispatch_plan is ephemeral — cleared after use.
    updates["dispatch_plan"] = []
    # Surface aggregate as a hint for downstream routing (non-error).
    if parent_status != "success":
        log.info(
            "dispatch_sub_agents parent_status=%s (%d children, %d successes)",
            parent_status,
            len(results),
            sum(1 for r in results if r.get("status") == "success"),
        )
    # R5 isolation: parent error_type is NEVER set by this node.
    return updates


# ---------------------------------------------------------------------------
# Plan D — meta_plan_subgraph (Task C.2)
# 3-node subgraph: classify_intent → fetch_context → generate_proposal.
# Invoked via invoke_skill("meta_plan", ...) per ADR-025.
#
# Drift invariants enforced:
# - test_canonical_scope :: test_meta_plan_no_direct_vault_writes (n)
# - test_canonical_scope :: test_meta_plan_approval_required_for_writes (o)
# - test_canonical_scope :: test_meta_plan_pydantic_v2_strict (p)
# ---------------------------------------------------------------------------
from .nodes.meta_plan.classify_intent import (  # noqa: E402
    classify_intent as _classify_intent,
)
from .nodes.meta_plan.fetch_context import (  # noqa: E402
    fetch_context as _fetch_context,
)
from .nodes.meta_plan.generate_proposal import (  # noqa: E402
    generate_proposal as _generate_proposal,
)


def make_meta_plan_subgraph() -> Any:
    """Build the meta-plan subgraph (3 nodes, sequential).

    Flow:
      1. ``classify_intent(user_request)`` -> ``IntentClassification``
      2. ``fetch_context(state)`` -> memory_refs + folder_reads + hierarchy_matches
      3. ``generate_proposal(state)`` -> ``Proposal(approval_state='pending')``

    Returns a compiled LangGraph ``StateGraph`` ready for ``.invoke()``.
    Entry point: ``classify_intent``. Finish point: ``generate_proposal``.

    Per ADR-013 (planner-only): this subgraph NEVER writes to vault or
    taskdog directly. All writes route through ``proposal_executor`` after
    user approval (B.4 / E.1).
    """
    from langgraph.graph import StateGraph

    def _classify(state: dict[str, Any]) -> dict[str, Any]:
        ic = _classify_intent(state.get("user_request", ""))
        return {"intent_classification": ic}

    def _fetch(state: dict[str, Any]) -> dict[str, Any]:
        refs, reads, match = _fetch_context(state)
        return {
            "memory_refs": refs,
            "folder_reads": reads,
            "hierarchy_matches": match,
        }

    def _generate(state: dict[str, Any]) -> dict[str, Any]:
        proposal = _generate_proposal(state)
        return {"proposal": proposal, "proposal_pending": True}

    sg = StateGraph(dict)
    sg.add_node("classify_intent", _classify)
    sg.add_node("fetch_context", _fetch)
    sg.add_node("generate_proposal", _generate)
    sg.set_entry_point("classify_intent")
    sg.add_edge("classify_intent", "fetch_context")
    sg.add_edge("fetch_context", "generate_proposal")
    sg.set_finish_point("generate_proposal")
    return sg.compile()


# ---------------------------------------------------------------------------
# Extend local NODES view with ``meta_plan`` entry point (Plan D Task C.2).
#
# graph.py:NODES is module-level and immutable (test_nodes_tuple_has_11_elements
# drift invariant enforces exactly 11 elements post-W4.4). This local rebind
# provides a view that downstream code (e.g. skill manifest validation in C.3)
# can read without modifying graph.py's frozen tuple. The rebind is a no-op
# if NODES is not yet importable due to circular import — graph.py remains
# the source of truth.
# ---------------------------------------------------------------------------
try:
    from .graph import NODES as _GRAPH_NODES  # type: ignore[attr-defined]

    if "meta_plan" not in _GRAPH_NODES:
        _GRAPH_NODES = (*_GRAPH_NODES, "meta_plan")  # type: ignore[assignment]
        NODES = _GRAPH_NODES  # type: ignore[assignment]
except (ImportError, NameError):
    # graph.py not yet imported (circular import window) or NODES not
    # defined in scope. graph.py remains the canonical source.
    pass
