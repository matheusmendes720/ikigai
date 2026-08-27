"""TaskdogAdapter factory — Task 14."""

from __future__ import annotations

import os

from ikigai.gateway.stdio_adapter import StdioAdapter, StdioAdapterConfig


def TaskdogAdapter(
    *,
    python: str | None = None,
    module: str | None = None,
    taskrc: str | None = None,
) -> StdioAdapter:
    """Adapter for taskdog-mcp — taskwarrior-backed task server.

    Expected tools: taskdog_add, taskdog_done, taskdog_list, taskdog_urgency.
    """
    py = python or os.environ.get("PYTHON", "python")
    mod = module or os.environ.get("TASKDOG_MODULE", "taskdog_mcp.server")
    cmd = [py, "-m", mod]
    env: dict[str, str] = {}
    if taskrc:
        env["TASKRC"] = taskrc
    return StdioAdapter(
        name="taskdog",
        config=StdioAdapterConfig(command=cmd, env=env, call_timeout_s=10.0),
    )
