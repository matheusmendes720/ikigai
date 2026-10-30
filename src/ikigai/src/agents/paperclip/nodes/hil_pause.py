"""``hil_pause`` + ``merge_user_resolution`` + ``hil_apply_user_resolution``
— the HIL pattern in the Paperclip repo (M169, M180).

The repo previously had **zero** ``interrupt()`` usage (per exploration of
2026-10-11). Paperclip introduces it. The pause halts the graph; the user
resumes via ``Command(resume=...)`` (LangGraph API) or via the eventual TUI /
CLI surface (Wave N+4).

API reference: ``langgraph_sdk.interrupt.interrupt(value)`` raises
``langgraph.errors.GraphInterrupt`` carrying ``value``; the resume call's
``Command(resume=...)`` payload is returned from ``interrupt()`` on the
next invocation.

Fallback: if ``langgraph_sdk`` isn't importable (some embedded envs), we
fall back to a poll-based pause via an env-controlled flag —
``PAPERCLIP_HIL_PAYLOAD=/path/to/json`` and the graph raises a custom
exception the harness catches. MVP uses the SDK import; fallback is
future-proofing only.

M180 (``hil_apply_user_resolution``) — sits between ``hil_pause`` (after
resume) and ``merge_user_resolution`` to apply the ``Command(resume=...)``
payload: bumps ``hil_resume_count`` + ``hil_last_resume_at`` for audit, and
writes a structured system message to the ``messages`` channel. The actual
spec-text merge logic is delegated to ``merge_user_resolution_node`` so the
two nodes form a single readable pipeline (apply → merge → spec_analyzer).
"""

from __future__ import annotations

import importlib
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

from src.ikigai.src.agents.paperclip.state import PaperclipStateDict

log = logging.getLogger(__name__)


def _interrupt(payload: dict[str, Any]) -> dict[str, Any]:
    """Call ``langgraph_sdk.interrupt.interrupt(payload)`` with a graceful
    fallback for envs where the SDK isn't installed.

    The fallback raises ``RuntimeError`` carrying the payload as JSON so
    a harness can serialize / resume it. Wave N+4 will wire a proper
    poll-based pause once we have a CLI/TUI surface.
    """
    try:
        # ``langgraph_sdk.interrupt`` is an optional submodule: it is absent
        # from some SDK builds and ships no type information. Resolving it
        # dynamically keeps the optional-dependency behaviour (ImportError
        # → fallback) without a hard import-time dependency on the SDK.
        _sdk_interrupt = cast(
            Callable[[dict[str, Any]], dict[str, Any]],
            importlib.import_module("langgraph_sdk.interrupt").interrupt,
        )
    except (ImportError, AttributeError):
        log.warning("langgraph_sdk.interrupt unavailable — using fallback pause")
        raise RuntimeError("PAPERCLIP_HIL_PAUSE: " + json.dumps(payload, default=str)) from None
    result: dict[str, Any] = _sdk_interrupt(payload)
    return result


def hil_pause_node(state: PaperclipStateDict) -> dict[str, object]:
    """Halt the graph and request user clarification on spec gaps.

    Called by ``_route_after_spec_analyzer`` when ``spec_gaps`` is non-empty.
    The returned ``user_resolution`` flows into ``merge_user_resolution`` →
    back to ``spec_analyzer`` (one iteration of the gap-resolution loop).
    """
    task_id = state.get("task_id") or "<unknown>"
    gaps = list(state.get("spec_gaps") or [])
    spec_excerpt = (state.get("spec_text") or "")[:500]
    iteration = int(state.get("gap_iteration") or 1)

    payload = {
        "kind": "spec_ambiguous",
        "task_id": task_id,
        "iteration": iteration,
        "gaps": gaps,
        "spec_excerpt": spec_excerpt,
        "instructions": (
            "Reply with a JSON object: "
            '{"answer": "<text addressing the gaps>", "rewritten_spec": '
            '"<optional full spec rewrite>"}'
        ),
    }
    log.info("paperclip hil_pause: task_id=%s iteration=%d gaps=%d", task_id, iteration, len(gaps))
    user_response = _interrupt(payload)

    # Normalise: accept either a dict, a JSON string, or None.
    if user_response is None:
        normalised: dict[str, Any] = {"answer": "", "rewritten_spec": ""}
    elif isinstance(user_response, str):
        try:
            normalised = json.loads(user_response)
        except json.JSONDecodeError:
            normalised = {"answer": user_response, "rewritten_spec": ""}
    elif isinstance(user_response, dict):
        normalised = user_response
    else:
        normalised = {"answer": str(user_response), "rewritten_spec": ""}

    return {
        "user_resolution": normalised,
        "last_step": "hil_pause",
    }


def merge_user_resolution_node(state: PaperclipStateDict) -> dict[str, object]:
    """Re-merge the spec_text with the user's clarification, then loop
    back to ``spec_analyzer``.

    If the user provided a full spec rewrite (``rewritten_spec`` non-empty),
    we replace ``spec_text`` with that. Otherwise we append a
    ``## User clarification`` section.
    """
    spec_text = state.get("spec_text") or ""
    resolution = state.get("user_resolution") or {}
    rewrite = (resolution.get("rewritten_spec") or "").strip()
    answer = (resolution.get("answer") or "").strip()

    if rewrite:
        new_spec = rewrite
    elif answer:
        new_spec = (
            f"{spec_text}\n\n## User clarification (iteration "
            f"{state.get('gap_iteration', '?')})\n{answer}"
        ).strip()
    else:
        # Nothing useful — leave spec alone (analyser will loop and hit cap)
        new_spec = spec_text

    return {
        "spec_text": new_spec,
        "user_resolution": {},
        "last_step": "merge_user_resolution",
        "messages": [
            {
                "role": "system",
                "content": (f"paperclip: merge_user_resolution (rewritten={bool(rewrite)})"),
            }
        ],
    }


def hil_apply_user_resolution_node(state: PaperclipStateDict) -> dict[str, object]:
    """Apply the user's ``Command(resume=...)`` payload.

    M180: sits between ``hil_pause_node`` (which called ``interrupt()`` and
    received the user's resume on this invocation) and
    ``merge_user_resolution_node`` (which merges into spec_text).

    Responsibilities (audit trail + counter — does NOT touch spec_text):

    1. Increment ``hil_resume_count`` (start at 1 if missing).
    2. Stamp ``hil_last_resume_at`` with the current UTC ISO timestamp.
    3. Append a structured system message to the ``messages`` channel
       describing the resume payload (``answer`` length, whether
       ``rewritten_spec`` was provided). Operators triaging a paperclip
       run see the resume audit trail in the chat channel.
    4. Mark ``last_step = "hil_apply_user_resolution"`` so the routing
       function can introspect.

    The actual spec-text merge is delegated to ``merge_user_resolution_node``
    — graph wiring is::

        hil_pause → hil_apply_user_resolution → merge_user_resolution
                                                  → spec_analyzer
    """
    current_count = int(state.get("hil_resume_count") or 0)
    resolution = state.get("user_resolution") or {}
    rewrite_provided = bool((resolution.get("rewritten_spec") or "").strip())
    answer_provided = bool((resolution.get("answer") or "").strip())
    timestamp = datetime.now(UTC).isoformat()

    audit_msg = (
        f"paperclip: HIL resume applied at iteration "
        f"{state.get('gap_iteration', '?')} (resume #{current_count + 1}; "
        f"answer_provided={answer_provided}; rewritten={rewrite_provided})"
    )
    log.info(
        "paperclip hil_apply_user_resolution: count=%d->%d task_id=%s",
        current_count,
        current_count + 1,
        state.get("task_id") or "<unknown>",
    )

    return {
        "hil_resume_count": current_count + 1,
        "hil_last_resume_at": timestamp,
        "last_step": "hil_apply_user_resolution",
        "messages": [
            {
                "role": "system",
                "content": audit_msg,
            }
        ],
    }
