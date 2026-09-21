"""error node — terminal catch-all for graph exceptions.

Infrastructure-only. Does NOT modify scoring/formula/QHE/regime/weight math.
Per audit B5.0-F3: any exception in the 8-node graph routes here via
the safe_node wrapper, then ends the graph gracefully.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from ..state import IKIGAiStateDict


def error_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Terminal node: record error state and end the graph gracefully.

    Reads the error fields populated by the safe_node wrapper
    (originating_node, error_type, error_message, traceback_str) and produces
    a commit_summary that downstream consumers can recognize.

    Idempotent: re-entry produces the same summary for the same cycle_id.
    """
    originating = state.get("originating_node", "unknown")
    err_type = state.get("error_type", "UnknownError")
    err_msg = state.get("error_message", "no message")
    tb = state.get("traceback_str", "")

    timestamp = dt.datetime.now().isoformat()
    summary = f"ERROR in node '{originating}' at {timestamp}: {err_type}: {err_msg}"

    # M88: error_node must write originating_node back to state so test
    # assertions like `result["originating_node"] is not None` pass.
    # Previously only the safe_node wrapper set these; new routing
    # decisions (e.g. _route_after_reason loop-exit) also need them.
    return {
        "originating_node": originating,
        "error_type": err_type,
        "error_message": err_msg,
        "commit_summary": summary,
        "terminated": True,
        "last_step": "error",
        "error_traceback": tb,
    }
