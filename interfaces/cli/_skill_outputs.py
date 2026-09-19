"""_skill_outputs — helpers for skill manifest output parsing (W3.6).

Per skill manifest spec: each skill declares its outputs as a list.
An output entry can be either:
- A bare string: ``"taskdog_create_task"`` (no description)
- A dict mapping tool name to description: ``{"taskdog_create_task": "quarterly OKRs"}``

These helpers extract info from that structure for downstream consumers
(invoke_skill post-processor, MCP skill router, etc.).
"""

from __future__ import annotations

from datetime import date
from typing import Any


def _manifest_declares_taskdog(outputs: list | None) -> str | None:
    """Return the taskdog description if ``outputs`` declares taskdog_create_task.

    Returns:
        - The description string (from a dict entry) if taskdog is declared
          with description
        - "" (empty string) if taskdog is declared as a bare-string entry
        - None if outputs is None / empty / doesn't mention taskdog
    """
    if not outputs:
        return None
    for entry in outputs:
        if isinstance(entry, str) and entry == "taskdog_create_task":
            return ""
        if isinstance(entry, dict) and "taskdog_create_task" in entry:
            return entry["taskdog_create_task"] or ""
    return None


def _derive_taskdog_title(skill_name: str, description: str) -> str:
    """Compose the taskdog title: ``<description or skill_name> <YYYY-MM-DD>``.

    Examples:
        >>> _derive_taskdog_title("ikigai-quarterly", "quarterly OKRs")
        'quarterly OKRs 2026-09-19'
        >>> _derive_taskdog_title("ikigai-x", "")
        'ikigai-x 2026-09-19'
    """
    title = description if description else skill_name
    return f"{title} {date.today().isoformat()}"


__all__ = ["_manifest_declares_taskdog", "_derive_taskdog_title"]
