"""Sub-agent dispatch types — typed contracts + validation per ADR-026.

This module owns the data shapes for the sub-agent dispatch protocol
(ADR-026 S1-S5 contracts) and the validation helpers that enforce them:

- Canonical 4-part UEID regex (ADR-014 + ADR-026 R4)
- Identity fields that ALWAYS propagate (ADR-026 S2.2 + ADR-025 R3 actor="agent")
- Error channel fields that NEVER propagate (ADR-026 S2.4)
- TypedDicts: ``ErrorRecord`` / ``SubAgentSpec`` / ``SubAgentResult``
- Spec validation: UEID, entry_point ∈ VALID_ENTRY_POINTS, timeout_s, merge_strategy

The actual sub-agent invocation + merge logic lives in ``subagent_invoke.py``;
the main ``dispatch_sub_agents`` graph node lives in ``subgraph.py``.

Architectural reference:
- ADR-026 — Sub-agent dispatch protocol (S1-S5 contracts, R1-R6 rules)
- ADR-013 — Planner-only invariant; sub-agents invoke other graph nodes
- ADR-014 — 4-part UEID canonical format
- ADR-025 — actor="agent" injected into every sub-agent (never user)

Drift invariants enforced:
- test_canonical_scope :: test_subagent_spec_ueid_validation (W4.4)
"""

from __future__ import annotations

import re
from typing import Any, Literal, NotRequired, TypedDict

# Canonical 4-part UEID regex (per ADR-014, src/contracts/common.py).
# Must match the production regex byte-for-byte — drift detector enforces.
_UEID_REGEX = re.compile(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")


# Valid entry points (post V5-D radical cleanup — graph.py deleted).
# These are the canonical node names a sub-agent may target. Keep in sync
# with the surviving v2/nodes/ module exports (error, observe, score_vectors,
# heuristics, balance, plan, decompose, reflect, commit, surface_intentions,
# tag_and_persist, proposal_executor) plus the meta_plan subgraph entry
# point. Subset chosen for sub-agent dispatch (ADR-026 R1):
# - error / tag_and_persist / proposal_executor: terminal/write ops
# - surface_intentions / observe: read-only observation nodes
# - meta_plan: subgraph entry (Plan D)
VALID_ENTRY_POINTS: tuple[str, ...] = (
    "error",
    "observe",
    "surface_intentions",
    "tag_and_persist",
    "proposal_executor",
    "meta_plan",
)


# Identity fields — ALWAYS propagate from parent to child (ADR-026 S2.2).
# ``actor`` is included per ADR-025 R3 (always "agent" for sub-agents).
_IDENTITY_FIELDS: tuple[str, ...] = (
    "cycle_id",
    "cycle_start",
    "cycle_end",
    "iteration",
    "actor",
)


# Error channel fields — MUST NEVER propagate to children (ADR-026 S2.4).
# Parent error isolation: a failing parent must not poison child state.
_ERROR_CHANNEL_FIELDS: tuple[str, ...] = (
    "originating_node",
    "error_type",
    "error_message",
    "traceback_str",
    "error_traceback",
    "commit_summary",
)


# Merge strategies (per ADR-026 S3). Reduced names — see subagent_invoke._merge_result.
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
    entry_point: str  # one of VALID_ENTRY_POINTS in this module
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
# Validation helpers
# ---------------------------------------------------------------------------


def is_valid_ueid(value: object) -> bool:
    """Return True iff value is a 4-part UEID per ADR-014."""
    return isinstance(value, str) and _UEID_REGEX.match(value) is not None


def validate_spec(spec: SubAgentSpec) -> str | None:
    """Return an error message if spec is malformed, else None.

    Enforced:
    - sub_agent_id is a 4-part UEID (ADR-014 + ADR-026 R4)
    - entry_point ∈ VALID_ENTRY_POINTS (ADR-026 R1)
    - timeout_s is a positive number if provided
    - merge_strategy ∈ {replace, merge_dict, append_list, reduce_add} if provided
    """
    sub_id = spec.get("sub_agent_id")
    if not is_valid_ueid(sub_id):
        return f"sub_agent_id {sub_id!r} is not a 4-part UEID (ADR-014 / ADR-026 R4)"

    entry = spec.get("entry_point")
    if entry not in VALID_ENTRY_POINTS:
        valid = ", ".join(VALID_ENTRY_POINTS)
        return f"entry_point {entry!r} not in VALID_ENTRY_POINTS ({valid})"

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
