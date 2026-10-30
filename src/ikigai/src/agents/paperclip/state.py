"""Paperclip — canonical state TypedDict.

Mirrors the OPEN-3 lesson from `v2/state.py:115-206`: every field is
``NotRequired`` so Cloud Studio's chat input detection stays enabled, and the
``messages`` channel carries the ``Annotated[list[dict], operator.add]``
reducer required by LangGraph chat semantics.

Lives in its own module so other Paperclip nodes / tests can import the type
without pulling the v2 graph (which has heavy OTel init at import time).
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, NotRequired, TypedDict


class PaperclipStateDict(TypedDict):
    """Canonical state for the Paperclip meta-orchestrator graph.

    All fields ``NotRequired`` per OPEN-3 (Cloud Studio chat input requires
    this). Defaults are applied inside nodes via ``state.get(...)`` so a
    partial invoke with just ``{"task_id": ..., "spec_text": ...}`` works.
    """

    # ---- Inputs (set by caller at invoke time) ----------------------------
    task_id: NotRequired[str]
    spec_text: NotRequired[str]

    # ---- Spec analysis output --------------------------------------------
    # Populated by `spec_analyzer_node`. Non-empty list triggers HIL pause.
    spec_gaps: NotRequired[list[str]]
    # Populated by `hil_pause` resume. Merged into spec_text for re-analysis.
    user_resolution: NotRequired[dict[str, Any]]

    # ---- Worktree (state of the git workspace) ----------------------------
    # ``worktree_path`` and ``branch_name`` are str (not Path) for serialisation
    # into the SqliteSaver checkpointer.
    worktree_path: NotRequired[str]
    branch_name: NotRequired[str]

    # ---- Implementation ---------------------------------------------------
    # Spec-gap loop counter — caps at MAX_GAP_LOOPS=5 to prevent infinite
    # gap → HIL → gap loops. Incremented by ``spec_analyzer_node``.
    gap_iteration: NotRequired[int]
    # Implement retry counter — caps at MAX_IMPLEMENT_ITERS=3. Incremented
    # by ``implement_node`` when tests fail.
    implement_iteration: NotRequired[int]
    # Tail of the last test run output, for debug.
    test_output: NotRequired[str]
    # ``True`` if pytest passed (or no pytest config found); ``False`` if
    # pytest failed. Routing after ``implement_node`` reads this to decide
    # ``worktree_commit`` (pass) vs loop-back to ``implement`` (fail).
    tests_ok: NotRequired[bool]

    # ---- Git results ------------------------------------------------------
    commit_sha: NotRequired[str]
    # Reserved for Wave N+3 (GitBucket PR sync); MVP: always None.
    pr_url: NotRequired[str | None]

    # ---- Wall-clock gate (M175) -------------------------------------------
    # Set by read_spec_node on first invocation; consulted by
    # WallClockGate in implement_node. Optional (fail-open if missing).
    task_started_at: NotRequired[str | None]

    # ---- HIL resume audit trail (M180) -----------------------------------
    # ``hil_resume_count`` is bumped by ``hil_apply_user_resolution_node``
    # every time the user resumes from ``hil_pause`` via ``Command(resume=...)``.
    # ``hil_last_resume_at`` is the ISO timestamp of the most recent resume.
    # Optional: missing means no resume has happened yet.
    hil_resume_count: NotRequired[int]
    hil_last_resume_at: NotRequired[str | None]

    # ---- Error channel (mirrors v2 graph's pattern at state.py:192-198) ---
    # Populated by `_safe_node` wrapper when a node raises.
    originating_node: NotRequired[str]
    error_type: NotRequired[str]
    error_message: NotRequired[str]
    traceback_str: NotRequired[str]
    last_step: NotRequired[str]

    # ---- LangGraph chat (required for Cloud Studio input detection) -------
    # Without this field declared with the list-deduce-append reducer, the
    # Studio chat input is greyed out. OPEN-3 lesson, kept here.
    messages: NotRequired[Annotated[list[dict[str, Any]], operator.add]]
