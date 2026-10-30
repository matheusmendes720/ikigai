"""Paperclip HIL flow tests — verify the interrupt-based pause works.

The HIL pattern is novel in this repo (M169-paperclip introduces it). These
tests verify:

* ``hil_pause_node`` invokes ``interrupt()`` with a structured payload (task_id,
  iteration, gaps, spec_excerpt, instructions).
* ``merge_user_resolution_node`` correctly merges user-provided clarifications
  back into ``spec_text`` (supports both ``rewritten_spec`` and ``answer``
  shapes).
* ``_extract_gaps`` JSON parser handles the three accepted shapes (whole JSON,
  trailing JSON block, newline-split fallback).

The graph-level HIL test (``interrupt_before=["hil_pause"]``) is exercised
manually in the verification section of the M169-paperclip SPEC — LangGraph's
test helper requires ``langgraph_sdk`` which is not always installed in CI.

Tests are unit-level (don't need to invoke the full graph) so they run
fast and don't depend on the SqliteSaver checkpointer being writable.
"""

from __future__ import annotations

import json
from typing import Any, cast

import pytest
from src.ikigai.src.agents.paperclip.nodes.hil_pause import (
    hil_apply_user_resolution_node,
    hil_pause_node,
    merge_user_resolution_node,
)
from src.ikigai.src.agents.paperclip.nodes.spec_analyzer import (
    MAX_GAP_LOOPS,
    _extract_gaps,
)
from src.ikigai.src.agents.paperclip.state import PaperclipStateDict


# ---------------------------------------------------------------------------
# _extract_gaps JSON parsing
# ---------------------------------------------------------------------------
def test_extract_gaps_whole_json_array() -> None:
    """A bare JSON array is parsed as the gap list."""
    out = json.dumps(["missing acceptance criteria", "ambiguous type hints"])
    assert _extract_gaps(out) == ["missing acceptance criteria", "ambiguous type hints"]


def test_extract_gaps_json_object_with_gaps_key() -> None:
    """``{"gaps": [...]}`` is unwrapped to the inner list."""
    out = json.dumps({"gaps": ["needs error type", "no return doc"]})
    assert _extract_gaps(out) == ["needs error type", "no return doc"]


def test_extract_gaps_prose_with_trailing_json() -> None:
    """When the output has prose + a trailing JSON block, the JSON wins."""
    out = "Here's my analysis:\nThe spec could be clearer.\n\n" + json.dumps(["gap A", "gap B"])
    assert _extract_gaps(out) == ["gap A", "gap B"]


def test_extract_gaps_empty_output() -> None:
    """Empty output → empty gap list (clean spec)."""
    assert _extract_gaps("") == []
    assert _extract_gaps("   \n  ") == []


def test_extract_gaps_newline_fallback() -> None:
    """Newline-split is the fallback when JSON parsing fails."""
    out = "- missing edge cases\n- wrong return type\n"
    # The fallback strips leading "- " and digits; both gap strings should remain.
    result = _extract_gaps(out)
    assert result == ["missing edge cases", "wrong return type"]


# ---------------------------------------------------------------------------
# hil_pause_node — interrupt() payload shape
# ---------------------------------------------------------------------------
def test_hil_pause_calls_interrupt_with_structured_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``hil_pause_node`` invokes ``interrupt(...)`` with a payload containing
    task_id, iteration, gaps, spec_excerpt, and instructions.

    Uses ``monkeypatch`` to replace the inner ``_interrupt`` helper so we
    can capture the call without needing ``langgraph_sdk`` installed.
    """
    from src.ikigai.src.agents.paperclip.nodes import hil_pause as hil_mod

    captured: list[dict[str, Any]] = []

    def fake_interrupt(payload: dict[str, Any]) -> dict[str, Any]:
        captured.append(payload)
        return {"answer": "clarified", "rewritten_spec": ""}

    monkeypatch.setattr(hil_mod, "_interrupt", fake_interrupt)

    state: PaperclipStateDict = {
        "task_id": "task-123",
        "spec_text": "Add a hello world function.",
        "spec_gaps": ["missing return type", "needs docstring"],
        "gap_iteration": 2,
    }
    result = hil_pause_node(state)

    # interrupt was called once with a structured payload
    assert len(captured) == 1
    payload = captured[0]
    assert payload["kind"] == "spec_ambiguous"
    assert payload["task_id"] == "task-123"
    assert payload["iteration"] == 2
    assert payload["gaps"] == ["missing return type", "needs docstring"]
    assert "Add a hello world" in payload["spec_excerpt"]
    assert "JSON object" in payload["instructions"]

    # and the result has the user_resolution merged
    assert result["user_resolution"] == {"answer": "clarified", "rewritten_spec": ""}
    assert result["last_step"] == "hil_pause"


def test_hil_pause_handles_string_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """A plain string response (not JSON) is stored under ``answer``."""
    from src.ikigai.src.agents.paperclip.nodes import hil_pause as hil_mod

    def fake_interrupt(payload: dict[str, Any]) -> str:
        return "just use FastAPI for the API layer"

    monkeypatch.setattr(hil_mod, "_interrupt", fake_interrupt)

    state: PaperclipStateDict = {
        "task_id": "task-str",
        "spec_gaps": ["which framework"],
    }
    result = hil_pause_node(state)
    assert result["user_resolution"] == {
        "answer": "just use FastAPI for the API layer",
        "rewritten_spec": "",
    }


# ---------------------------------------------------------------------------
# merge_user_resolution_node — merging back into spec_text
# ---------------------------------------------------------------------------
def test_merge_user_resolution_prefers_rewrite() -> None:
    """When the response has ``rewritten_spec``, it replaces spec_text entirely."""
    state: PaperclipStateDict = {
        "spec_text": "original spec",
        "user_resolution": {
            "answer": "use FastAPI",
            "rewritten_spec": "Add a FastAPI endpoint at /hello that returns 'world'.",
        },
    }
    result = merge_user_resolution_node(state)
    assert result["spec_text"] == "Add a FastAPI endpoint at /hello that returns 'world'."
    assert result["user_resolution"] == {}  # consumed


def test_merge_user_resolution_appends_answer() -> None:
    """When only ``answer`` is given, append a User clarification section."""
    state: PaperclipStateDict = {
        "spec_text": "Add a hello world function.",
        "user_resolution": {"answer": "Use Type hints.", "rewritten_spec": ""},
        "gap_iteration": 1,
    }
    result = merge_user_resolution_node(state)
    spec_text = cast(str, result["spec_text"])
    assert spec_text.startswith("Add a hello world function.")
    assert "## User clarification (iteration 1)" in spec_text
    assert "Use Type hints." in spec_text


def test_merge_user_resolution_handles_empty_resolution() -> None:
    """An empty resolution leaves spec_text unchanged (graph loops to cap)."""
    state: PaperclipStateDict = {
        "spec_text": "unchanged",
        "user_resolution": {},
    }
    result = merge_user_resolution_node(state)
    assert result["spec_text"] == "unchanged"


# ---------------------------------------------------------------------------
# spec_analyzer_node — gap-loop cap
# ---------------------------------------------------------------------------
def test_spec_analyzer_caps_at_max_gap_loops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After MAX_GAP_LOOPS iterations the analyzer emits SpecAmbiguousError
    instead of invoking the Claude adapter."""
    from src.ikigai.src.agents.paperclip.nodes import spec_analyzer as sa_mod

    called: list[bool] = []

    class _ExplodingAdapter:
        name = "explode"

        def run(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - guard
            called.append(True)
            raise AssertionError("must not be called after MAX_GAP_LOOPS")

    state: PaperclipStateDict = {
        "task_id": "cap-test",
        "spec_text": "anything",
        "gap_iteration": MAX_GAP_LOOPS,  # already at the cap
    }
    result = sa_mod.spec_analyzer_node(state, claude_adapter=_ExplodingAdapter())
    assert result["error_type"] == "SpecAmbiguousError"
    assert "spec_ambiguous" in cast(str, result["error_message"])
    assert called == []  # adapter never invoked


def test_spec_analyzer_adapter_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """NotImplementedError from the adapter → AnalyzerUnavailable."""
    from src.ikigai.src.agents.paperclip.nodes import spec_analyzer as sa_mod

    class _StubAdapter:
        name = "stub"

        def run(self, prompt: str, cwd: str, *, timeout_s: int | None = None) -> None:
            raise NotImplementedError("Paperclip: pi adapter pending")

    state: PaperclipStateDict = {"task_id": "t", "spec_text": "anything"}
    result = sa_mod.spec_analyzer_node(state, claude_adapter=_StubAdapter())
    assert result["error_type"] == "AnalyzerUnavailable"
    assert "pi adapter pending" in cast(str, result["error_message"])


# ---------------------------------------------------------------------------
# hil_apply_user_resolution_node — M180 audit-trail node
# ---------------------------------------------------------------------------
def test_hil_apply_user_resolution_increments_count() -> None:
    """``hil_apply_user_resolution_node`` increments ``hil_resume_count`` by 1.

    Mirrors the pattern of the existing ``merge_user_resolution`` tests: a
    fresh state (no prior count) should land at count=1 after one apply.
    A second invocation (simulating a second resume cycle) should land at
    count=2. This guards against accidental reset / off-by-one bugs in the
    M180 audit trail.
    """
    base_state: PaperclipStateDict = {
        "task_id": "task-resume-1",
        "spec_text": "anything",
        "user_resolution": {"answer": "use FastAPI", "rewritten_spec": ""},
        "gap_iteration": 1,
    }
    first = hil_apply_user_resolution_node(base_state)
    assert first["hil_resume_count"] == 1
    assert first["last_step"] == "hil_apply_user_resolution"

    # Second resume (caller passes the updated state)
    state_2: PaperclipStateDict = {
        **base_state,
        "hil_resume_count": 1,
        "user_resolution": {"answer": "ok switch to Flask", "rewritten_spec": ""},
        "gap_iteration": 2,
    }
    second = hil_apply_user_resolution_node(state_2)
    assert second["hil_resume_count"] == 2
    assert second["last_step"] == "hil_apply_user_resolution"


def test_hil_apply_user_resolution_audit_message() -> None:
    """A system message describing the resume payload is appended to ``messages``.

    The audit message must include the iteration number, the new resume
    count, and flags for ``answer_provided`` + ``rewritten`` so a triager
    inspecting the chat channel can reconstruct what happened without
    walking the code.
    """
    state: PaperclipStateDict = {
        "task_id": "task-audit",
        "spec_text": "anything",
        "user_resolution": {
            "answer": "Use FastAPI with port 8000.",
            "rewritten_spec": "",
        },
        "gap_iteration": 3,
        "hil_resume_count": 0,
    }
    result = hil_apply_user_resolution_node(state)
    messages = result["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 1
    msg = messages[0]
    assert msg["role"] == "system"
    content = msg["content"]
    assert "paperclip: HIL resume applied" in content
    assert "iteration 3" in content
    assert "answer_provided=True" in content
    assert "rewritten=False" in content


def test_hil_apply_user_resolution_spec_rewrite() -> None:
    """When ``rewritten_spec`` is non-empty, the audit trail records the
    rewrite flag (this node does NOT touch spec_text — that's
    ``merge_user_resolution``'s job).
    """
    state: PaperclipStateDict = {
        "task_id": "task-rewrite",
        "spec_text": "ORIGINAL spec — must NOT be replaced here",
        "user_resolution": {
            "answer": "",
            "rewritten_spec": "Full FastAPI rewrite",
        },
        "gap_iteration": 1,
    }
    result = hil_apply_user_resolution_node(state)
    # The new node does not touch spec_text; merge_user_resolution does.
    assert "spec_text" not in result
    messages = result["messages"]
    assert isinstance(messages, list)
    msg_list = cast(list[dict[str, Any]], messages)
    assert msg_list[0]["content"].endswith("rewritten=True)")
    assert result["hil_resume_count"] == 1


def test_hil_apply_user_resolution_uses_answer() -> None:
    """When only ``answer`` is given, the audit message flags
    ``answer_provided=True, rewritten=False``.
    """
    state: PaperclipStateDict = {
        "task_id": "task-answer",
        "spec_text": "any",
        "user_resolution": {"answer": "clarify auth flow", "rewritten_spec": ""},
        "gap_iteration": 2,
        "hil_resume_count": 1,
    }
    result = hil_apply_user_resolution_node(state)
    # count bumped from 1 -> 2
    assert result["hil_resume_count"] == 2
    content = cast(list[dict[str, Any]], result["messages"])[0]["content"]
    assert "answer_provided=True" in content
    assert "rewritten=False" in content


def test_graph_hil_apply_node_registered() -> None:
    """``hil_apply_user_resolution`` is wired into ``graph.NODES`` between
    ``hil_pause`` and ``merge_user_resolution``.

    The position in the NODES tuple also matters for readability (the
    audit node sits in the HIL cluster, not the worktree cluster). Locks
    in the M180 graph topology against accidental rename / re-ordering.
    """
    from src.ikigai.src.agents.paperclip import graph as graph_mod

    nodes = graph_mod.NODES
    assert "hil_apply_user_resolution" in nodes, (
        "hil_apply_user_resolution missing from graph.NODES — was the M180 "
        "wiring undone? Re-add per M180-paperclip-hil-resume."
    )
    # Position: must sit AFTER hil_pause and BEFORE merge_user_resolution
    idx_hil_pause = nodes.index("hil_pause")
    idx_apply = nodes.index("hil_apply_user_resolution")
    idx_merge = nodes.index("merge_user_resolution")
    assert idx_hil_pause < idx_apply < idx_merge, (
        f"hil_apply_user_resolution must sit between hil_pause and "
        f"merge_user_resolution in NODES, got order: "
        f"{list(nodes)}"
    )
