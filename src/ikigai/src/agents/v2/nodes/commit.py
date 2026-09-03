"""commit node — persist IKIGAi state.

MATH/VAULT NOTE: _write_to_sqlite and _append_to_vault are guarded in if False:
as historical artifacts. The vault write in _append_to_vault would violate the
vault_write invariant (only vault_write tool may write vault/).

Phase 8.2: replace with MCP tool calls (vault_write for vault, taskdog
adapter for SQLite).
"""

from __future__ import annotations

import datetime as dt
from typing import Any, cast

from ..state import IKIGAiStateDict

# Kill switch — set to True to block all writes
_KILL_SWITCH = False


def commit_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Persist cycle results.

    STUB: returns commit_summary only. No writes performed.
    Phase 8.2 wires vault_write (MCP) + taskdog adapter for actual persistence.
    """
    if _KILL_SWITCH:
        return {
            "commit_summary": "Kill switch active — no writes performed",
            "last_step": "commit",
        }

    cycle_id = state.get("cycle_id", dt.date.today().isoformat())
    regime = state.get("regime_state", "MAINTAIN")
    q_he = state.get("q_he_score", 0.65)
    vector_scores = cast(dict[str, float], state.get("vector_scores", {}))
    meta_vector = state.get("meta_vector_score", 0.0)
    corrections_raw: list[dict[str, Any]] = cast(list[dict[str, Any]], state.get("corrections", []))

    summary_lines: list[str] = [
        f"[STUB] cycle={cycle_id} regime={regime} q_he={q_he:.4f}",
        f"[STUB] vectors={vector_scores} meta={meta_vector:.2f}",
        f"[STUB] corrections={len(corrections_raw)}",
    ]

    return {
        "commit_summary": "; ".join(summary_lines),
        "cycle_id": cycle_id,
        "last_step": "commit",
    }


# ---------------------------------------------------------------------------
# GUARDED: historical persistence functions (vault write + SQLite adapter)
# Never executed (if False:). Phase 8.2 replaces with MCP tool calls.
# ---------------------------------------------------------------------------
if False:
    # pylint: disable=unused-argument
    def _write_to_sqlite(
        cycle_id: str,
        regime: str,
        q_he: float,
        vector_scores: dict[str, float],
        meta_vector: float,
        corrections: list[dict[str, Any]],
    ) -> str:
        """Write cycle record to plan_entities SQLite table."""
        return f"stub ({cycle_id})"

    def _append_to_vault(
        vault_path: Any,
        cycle_id: str,
        regime: str,
        q_he: float,
        vector_scores: dict[str, float],
        meta_vector: float,
        corrections: list[dict[str, Any]],
    ) -> str:
        """Append cycle summary to markdown vault log."""
        return "stub"

    def _get_vault_path() -> Any:
        """Return vault path from config or env."""
        return None


def set_kill_switch(active: bool) -> None:
    """Toggle kill switch for guarded writes."""
    global _KILL_SWITCH
    _KILL_SWITCH = active
