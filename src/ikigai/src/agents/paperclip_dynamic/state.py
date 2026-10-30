"""Paperclip Dynamic — canonical state TypedDict.

Mirrors the OPEN-3 lesson from Paperclip (``paperclip/state.py``): every
field is ``NotRequired`` so Cloud Studio's chat input detection stays
enabled, and the ``messages`` channel carries the ``Annotated[list[dict],
operator.add]`` reducer required by LangGraph chat semantics.

Lives in its own module so other Dynamic nodes / tests can import the
type without pulling the heavy graph machinery (which pulls SqliteSaver,
LangGraph runtime, etc.).

Per ``deep-dive-dynamic-workflows.md`` §4 (state model): input,
planner output, harness builder output, per-sub-agent running state,
global evaluator output, synthesizer output, meta/observability.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, NotRequired, TypedDict


class DynamicWorkflowState(TypedDict):
    """Canonical state for the Paperclip Dynamic meta-orchestrator graph.

    All fields ``NotRequired`` per OPEN-3 (Cloud Studio chat input
    requires this). Defaults are applied inside nodes via
    ``state.get(...)`` so a partial invoke with just ``{"user_query": ...}``
    works through the skeleton.
    """

    # ---- Inputs (set by caller at invoke time) -----------------------------
    user_query: NotRequired[str]
    command: NotRequired[str]  # "research" | "audit" | "fix"

    # ---- Planner output ---------------------------------------------------
    # Goal + ordered sub-agent task list + max_attempts ceiling.
    plan: NotRequired[dict[str, Any]]
    # First-class list of tasks (mirrors ``plan["tasks"]`` but flat for
    # the harness builder + dynamic fan-out).
    subagent_tasks: NotRequired[list[dict[str, Any]]]
    # Default bounded-retries per sub-agent (emitted by the planner, can
    # be overridden per-task).
    max_attempts: NotRequired[int]

    # ---- Harness builder output -------------------------------------------
    # ``workflow_spec_md`` — the dynamic part. Markdown document the
    # runtime materialises into a sub-graph topology (or, in MVP, into
    # the static 3-slot fan-out we ship).
    workflow_spec_md: NotRequired[str]
    # Per-sub-agent results (keyed by task id).
    subagent_results: NotRequired[dict[str, Any]]
    # Per-sub-agent running retry state (keyed by task id).
    subagent_retries: NotRequired[dict[str, int]]
    # Warnings collected across the run (verifier failures, oversize
    # sub-agent lists, etc.).
    subagent_warnings: NotRequired[list[str]]

    # ---- Global evaluator output -----------------------------------------
    cross_check_findings: NotRequired[list[str]]
    # Aggregate confidence in [0.0, 1.0].
    confidence: NotRequired[float]

    # ---- Synthesizer output ----------------------------------------------
    final_report_md: NotRequired[str]

    # ---- Meta / observability --------------------------------------------
    # Append-only trace of every node the run touched.
    trace: NotRequired[list[dict[str, Any]]]
    # OPEN-3 — required for Cloud Studio chat input detection.
    messages: NotRequired[Annotated[list[dict[str, Any]], operator.add]]
    # Last node that wrote state — mirrors Paperclip's `last_step` field.
    last_step: NotRequired[str]

    # ---- Error channel (mirrors Paperclip + v2 graph's pattern) ---------
    # Populated by ``_safe_node`` wrapper when a node raises.
    originating_node: NotRequired[str]
    error_type: NotRequired[str]
    error_message: NotRequired[str]
    traceback_str: NotRequired[str]
