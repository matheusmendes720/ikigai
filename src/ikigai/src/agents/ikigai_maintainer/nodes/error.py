"""error node — terminal catch-all for graph exceptions.

Per audit B5.0-F3: any exception in the 8-node IKIGAi-Maintainer graph
(observe → score_vectors → heuristics → balance → decompose → plan → reflect
→ commit) previously caused the graph to crash. This node is wired as a
fallback terminal: when a wrapped node raises, the wrapper short-circuits to
this error_node with state populated, then ends the graph with a failed
commit_summary.

Scope: infrastructure-only. Does NOT modify scoring/formula/QHE/regime/weight
math — see [[b5-0-audit-findings-2026-08-29]] scope fence.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from ..state import IKIGAiStateDict


def error_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Terminal node: record error state and end the graph gracefully.

    Reads the error fields populated by the wrapper (originating_node,
    error_type, error_message, traceback_str) and produces a commit_summary
    that downstream consumers (commit logs, MCP tools) can recognize.

    Idempotent: re-entry produces the same summary for the same cycle_id.
    """
    originating = state.get("originating_node", "unknown")
    err_type = state.get("error_type", "UnknownError")
    err_msg = state.get("error_message", "no message")
    tb = state.get("traceback_str", "")

    timestamp = dt.datetime.now().isoformat()
    summary = f"ERROR in node '{originating}' at {timestamp}: {err_type}: {err_msg}"

    return {
        "commit_summary": summary,
        "terminated": True,
        "last_step": "error",
        "error_traceback": tb,
    }
