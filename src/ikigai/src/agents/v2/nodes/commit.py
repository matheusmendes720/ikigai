"""commit node — finalize cycle and produce commit_summary (M89).

M89: Real implementation. Produces a commit_summary from the current
cycle state. If a draft_proposal exists with task.create operations,
fires taskdog_create_task via the existing IKIGAI tool
(agents.tools.taskdog_create_task).

Replaces the prior stub that returned an error_channel entry noting
that mcp_bridge.ikigai_commit_summary was deleted in M12.

The commit_summary format is canonical:
    "COMMIT cycle={cycle_id} tier={tier} proposal={proposal_id} ok=True"

This is what downstream nodes (dispatch_sub_agents, surface_intentions)
and tests rely on.
"""

from __future__ import annotations

import logging
from typing import Any

from ..state import IKIGAiStateDict

logger = logging.getLogger(__name__)


def _taskdog_create_task_via_bridge(title: str) -> dict[str, Any]:
    """Lazy proxy to taskdog_create_task tool (M89).

    Uses sys.modules lookup pattern from invoke_skill.py — tests
    monkeypatch the source module, production uses src.ikigai.src.agents.tools.
    """
    import sys

    tools_mod = sys.modules.get("agents.tools") or sys.modules.get("src.ikigai.src.agents.tools")
    if tools_mod is None:
        try:
            from src.ikigai.src.agents import tools as _tools

            tools_mod = _tools
        except ImportError:
            return {"ok": False, "error": "agents.tools not importable"}
    fn = getattr(tools_mod, "taskdog_create_task", None)
    if fn is None:
        return {"ok": False, "error": "taskdog_create_task not found on tools module"}
    try:
        result = fn.invoke({"name": title})
        return {"ok": True, "result": result}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _summarize_cycle(state: IKIGAiStateDict) -> str:
    """Produce canonical commit_summary from cycle state."""
    cycle_id = state.get("cycle_id", "unknown")
    tier = "daily"
    if state.get("active_dream_ueid"):
        tier = "dream"
    elif state.get("active_goal_ueids"):
        tier = "goal"

    proposal = state.get("draft_proposal") or {}
    proposal_id = proposal.get("proposal_id", "none")

    return f"COMMIT cycle={cycle_id} tier={tier} proposal={proposal_id} ok=True"


def commit_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Finalize cycle + produce commit_summary + fire taskdog operations (M89).

    Reads from state:
    - draft_proposal: dict with proposal_id, operations
    - cycle_id, tier markers

    Writes to state:
    - commit_summary: string (canonical format)
    - commit: dict with taskdog_results (if any task.create ops fired)
    - terminated: True (signals graph should wind down)
    - last_step: "commit"
    """
    state = dict(state)
    proposal = state.get("draft_proposal") or {}
    operations = proposal.get("operations") if isinstance(proposal, dict) else None

    commit_summary = _summarize_cycle(state)
    commit_result: dict[str, Any] = {"taskdog_results": []}

    if operations and isinstance(operations, list):
        for op in operations:
            if not isinstance(op, dict):
                continue
            if op.get("type") == "task.create":
                target = op.get("target", "untitled task")
                if isinstance(target, str) and target.strip():
                    td_result = _taskdog_create_task_via_bridge(target.strip())
                    commit_result["taskdog_results"].append({"target": target, **td_result})
                    if not td_result.get("ok"):
                        logger.warning(
                            "taskdog_create_task failed for %r: %s", target, td_result.get("error")
                        )

    return {
        "commit": commit_result,
        "commit_summary": commit_summary,
        "terminated": True,
        "last_step": "commit",
    }
