"""taskdog adapter — thin wrapper that delegates to the real mesh adapter.

The real SQLite-backed adapter lives at ``src/mesh/adapters/taskdog.py``
(Phase 3 v1 mesh). This gateway adapter is the MCP-callable surface that
forks / external MCP clients use; it translates MCP tool calls into the
real adapter's methods.

Routing:
- ``taskdog_list_tasks``  -> ``TaskdogAdapter.list_all`` (honours ``limit`` / ``status``)
- ``taskdog_create_task`` -> ``TaskdogAdapter.apply_change`` (synthesizes a ``PropagationEvent``)
- everything else         -> ``{"result": "not_supported", ...}`` stub

Path 3 taskdog MCP (``src/ikigai/src/mcp_server/taskdog_tools.py``) is the
canonical read surface; this gateway adapter is the write-equivalent for
the same ``data/taskdog/tasks.db`` SQLite file.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from src.contracts.common import UEID
from src.contracts.task_change import PropagationEvent, TaskAction
from src.mesh.adapters.taskdog import TaskdogAdapter as _RealTaskdogAdapter


class TaskdogAdapter:
    """Gateway-facing taskdog adapter that delegates to the mesh v1 adapter."""

    name = "taskdog"

    def __init__(self) -> None:
        self._real = _RealTaskdogAdapter()

    # ----- public surface (MCP-style call_tool) -----

    def call_tool(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        args = args or {}

        if tool == "taskdog_list_tasks":
            return self._list_tasks(args)
        if tool == "taskdog_create_task":
            return self._create_task(args)

        return {
            "result": "not_supported",
            "adapter": self.name,
            "tool": tool,
            "args": args,
        }

    # ----- delegated methods -----

    def _list_tasks(self, args: dict[str, Any]) -> dict[str, Any]:
        tasks = list(self._real.list_all())
        status = args.get("status")
        if status is not None:
            tasks = [t for t in tasks if t.get("status") == status]
        tasks.sort(key=lambda t: t.get("created_at") or "", reverse=True)
        limit = args.get("limit")
        if isinstance(limit, int) and limit > 0:
            tasks = tasks[:limit]
        return {
            "result": "ok",
            "adapter": self.name,
            "tool": "taskdog_list_tasks",
            "count": len(tasks),
            "tasks": tasks,
        }

    def _create_task(self, args: dict[str, Any]) -> dict[str, Any]:
        try:
            ueid = UEID(args["ueid"])
        except (KeyError, ValueError) as exc:
            return {
                "result": "error",
                "adapter": self.name,
                "tool": "taskdog_create_task",
                "error": f"invalid ueid: {exc}",
            }

        fields = {
            "title": args.get("title"),
            "due": args.get("due"),
            "priority": args.get("priority"),
        }
        now = datetime.now(timezone.utc)
        event = PropagationEvent(
            event_id=str(uuid.uuid4()),
            ueid=ueid,
            action=TaskAction.CREATE,
            fields=fields,
            approved_at=now,
            source_fork="taskdog_gateway",
        )
        try:
            self._real.apply_change(event)
        except Exception as exc:  # noqa: BLE001 — surface adapter errors verbatim
            return {
                "result": "error",
                "adapter": self.name,
                "tool": "taskdog_create_task",
                "error": str(exc),
            }
        return {
            "result": "ok",
            "adapter": self.name,
            "tool": "taskdog_create_task",
            "ueid": str(ueid),
            "slice": self._real.read(ueid),
        }

    # ----- direct passthroughs for callers that prefer attribute-style access -----

    def read(self, ueid: UEID) -> dict[str, Any] | None:
        return self._real.read(ueid)

    def list_all(self) -> list[dict[str, Any]]:
        return self._real.list_all()

    def supports_field(self, field_name: str) -> bool:
        return self._real.supports_field(field_name)
