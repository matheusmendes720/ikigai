"""``read_spec`` node — parse + validate the input spec.

MVP: ``spec_text`` comes inline as an invoke-time kwarg. This node:

* Trims whitespace and rejects empty specs (sets ``error_type=SpecEmptyError``).
* Records the spec length + first 80-char preview for the audit log.
* Leaves HIL / analyzer / implementation for downstream nodes.

Future: when Wave N+2 adds spec persistence (``paperclip/specs/*.md``),
this node will read the file by ``task_id`` and populate ``spec_text``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from src.ikigai.src.agents.paperclip.state import PaperclipStateDict


def read_spec_node(state: PaperclipStateDict) -> dict[str, object]:
    """Validate the inline spec_text input.

    Returns a partial state dict (LangGraph convention). Empty spec →
    error channel populated; downstream ``_route_after_read_spec`` sends
    the graph to END via the ``error`` route.

    M175-paperclip-wall-clock-gate: on first invocation we stamp
    ``task_started_at`` with the current UTC timestamp so the
    :class:`~src.ikigai.src.agents.paperclip.policy.WallClockGate` in
    ``implement_node`` has a reference for elapsed-time calculations.
    The field is ``NotRequired`` + fail-open so replayed checkpoints
    without it degrade gracefully (the gate allows the call and logs
    "no start time").
    """
    spec = (state.get("spec_text") or "").strip()
    task_id = state.get("task_id") or ""

    if not task_id:
        return {
            "originating_node": "read_spec",
            "error_type": "TaskIdMissing",
            "error_message": "task_id is required",
            "last_step": "read_spec",
        }

    if not spec:
        return {
            "originating_node": "read_spec",
            "error_type": "SpecEmptyError",
            "error_message": "spec_text is empty",
            "last_step": "read_spec",
        }

    preview = spec[:80].replace("\n", " ")
    return {
        "spec_text": spec,  # normalized: trimmed
        "last_step": "read_spec",
        "task_started_at": datetime.now(UTC).isoformat(),
        "messages": [
            {
                "role": "system",
                "content": (
                    f"paperclip: read_spec task_id={task_id!r} "
                    f"spec_len={len(spec)} preview={preview!r}"
                ),
            }
        ],
    }
