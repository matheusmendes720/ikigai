"""W3.6 — Skill `outputs` post-processor (taskdog_create_task bridge).

Per ADR-013 the v2 graph itself stays pure: it reads vault, applies prompt
chains, returns state. Side-effect tools (taskdog_create_task) live in the
CLI orchestrator so the graph remains a planner. This module owns the
post-processor that consults a skill's manifest `outputs` list and fires
the declared tools AFTER the graph returns.

Current contract (Wave 3, W3.6):
  - manifest.outputs entries can be:
      * a bare string "taskdog_create_task", or
      * a mapping {"taskdog_create_task": "<description>"}
  - When declared, the existing Path-1 ``taskdog_create_task`` @tool
    (src/ikigai/src/agents/tools.py:423) is invoked with name =
    "<description> <YYYY-MM-DD>" (or the skill name if no description).
  - On success the caller gets ``taskdog_result`` in the returned dict.
  - On failure a TaskChange is enqueued to ``data/review_queue/`` via the
    canonical mesh.queue.enqueue() writer and ``taskdog_pending_review_queue:
    True`` is set on the returned dict. No exception ever propagates here
    (Wave 3 partial-success invariant).

Future outputs (vault_write, etc.) can be added by extending ``_post_process``.
"""

from __future__ import annotations

import logging
from datetime import date

log = logging.getLogger(__name__)


def _manifest_declares_taskdog(outputs: object) -> str | None:
    """Return the manifest's taskdog_create_task description, or None.

    The manifest's ``outputs`` is a list. Each entry is either:
      - a bare string (e.g. ``"taskdog_create_task"``), or
      - a mapping (e.g. ``{"taskdog_create_task": "quarterly OKRs"}``).

    Returns the description string when taskdog is declared; None otherwise.
    """
    if not isinstance(outputs, list):
        return None
    for entry in outputs:
        if isinstance(entry, str) and entry == "taskdog_create_task":
            return ""  # declared without description
        if isinstance(entry, dict) and "taskdog_create_task" in entry:
            value = entry["taskdog_create_task"]
            return value if isinstance(value, str) else ""
    return None


def _derive_taskdog_title(skill_name: str, description: str) -> str:
    """Compose the taskdog task name passed to taskdog_create_task.invoke().

    Path-1 harness invokes ``taskdog.exe add <name>`` — name must be a single
    CLI-safe string. Today + skill description keeps it traceable to the
    skill invocation that produced it.
    """
    today = date.today().isoformat()
    base = description.strip() if description else skill_name
    return f"{base} {today}"


def _enqueue_taskdog_failure(
    skill_name: str,
    taskdog_params: dict,
    error_message: str,
) -> None:
    """Append a TaskChange to data/review_queue/ marking the taskdog failure.

    The file is written via mesh.queue.enqueue() so the canonical writer
    invariant (``test_review_queue_append_only``) holds. Downstream the
    review_queue_worker can pick it up for manual replay.

    Persisted fields encode the W3.6 brief's record shape:
      action: "create"      → TaskAction.CREATE
      target_fork: "taskdog" → fields.target_fork
      error: <message>      → fields.error
      original_params: {...}→ fields.original_params
      actor: "agent"        → fields.actor
      created_at: <ISO>     → fields.created_at
    """
    from datetime import UTC, datetime
    import uuid

    from contracts.common import UEID
    from contracts.task_change import TaskAction, TaskChange
    from src.mesh import queue as _queue

    short = skill_name.replace("ikigai-", "")
    placeholder_ueid = UEID(
        f"tsk:{short}-pending:00000000-0000-0000-0000-000000000000:0000000000000000"
    )
    now_utc = datetime.now(UTC)
    event = TaskChange(
        event_id=str(uuid.uuid4()),
        ueid=placeholder_ueid,
        action=TaskAction.CREATE,
        fields={
            "title": taskdog_params.get("name", ""),
            "actor": "agent",
            "created_at": now_utc.isoformat(),
            "target_fork": "taskdog",
            "error": error_message,
            "original_params": taskdog_params,
        },
        source_fork="taskdog",
        timestamp=now_utc.replace(tzinfo=None),
    )
    _queue.enqueue(event)


def post_process_skill_outputs(
    skill_name: str,
    manifest: dict,
    graph_result: dict,
) -> dict:
    """Fire declared outputs (currently: taskdog_create_task) after graph runs.

    Returns the graph result, extended with:
      - ``taskdog_result``: the @tool's stdout on success
      - ``taskdog_pending_review_queue: True``: enqueued failure marker

    The function never raises — per Wave 3 partial-success invariant, a
    taskdog failure becomes a warning + review_queue entry, not a CLI crash.
    """
    description = _manifest_declares_taskdog(manifest.get("outputs"))
    if description is None:
        return graph_result  # surface-only skill — nothing to fire

    title = _derive_taskdog_title(skill_name, description)
    taskdog_params = {"name": title}

    try:
        # Resolve via importlib so the patched module reference is reused
        # even when the dotted path (`src.ikigai.src.agents.tools`) is what
        # CLI hands import. This makes monkeypatch.setattr on either module
        # alias take effect deterministically.
        import importlib

        try:
            tools_mod = importlib.import_module("agents.tools")
        except ImportError:
            tools_mod = importlib.import_module("src.ikigai.src.agents.tools")
        taskdog_create_task = getattr(tools_mod, "taskdog_create_task")

        taskdog_result = taskdog_create_task.invoke(taskdog_params)
    except Exception as exc:
        log.warning(
            "taskdog_create_task failed for skill %s (params=%s): %s: %s",
            skill_name,
            taskdog_params,
            type(exc).__name__,
            exc,
        )
        try:
            _enqueue_taskdog_failure(skill_name, taskdog_params, str(exc))
        except Exception as enq_exc:
            log.warning(
                "Could not enqueue taskdog failure for skill %s: %s: %s",
                skill_name,
                type(enq_exc).__name__,
                enq_exc,
            )
        return {**graph_result, "taskdog_pending_review_queue": True}

    return {**graph_result, "taskdog_result": taskdog_result}
