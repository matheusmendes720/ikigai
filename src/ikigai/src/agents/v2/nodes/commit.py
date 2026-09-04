"""commit node — persist IKIGAi state to vault.

Per ADR-012 + attribution §7: vault_write is the ONLY vault writer.
This node routes all summary writes through vault_write (with
actor="agent") — direct file I/O is forbidden.

Phase 8.2: replaces historical `_write_to_sqlite` / `_append_to_vault`
stubs (now deleted) with the canonical vault_write MCP tool call.

If tag_and_persist already wrote the proposed entity to vault
(state has `persisted=True`), this node writes only the cycle summary
to avoid double-writing the same frontmatter block.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any, cast

from src.ikigai.src.agents.v2.state import IKIGAiStateDict
from src.ikigai.src.mcp_server.tools_vault import vault_write

# Kill switch — set to True to block all writes (safety guard)
_KILL_SWITCH = False


def commit_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Persist cycle results via vault_write MCP tool.

    Reads ``cycle_id``, ``regime_state``, ``q_he_score``,
    ``vector_scores``, ``meta_vector_score``, ``corrections`` from
    state. Builds a cycle-summary frontmatter and writes to
    ``ikigai/cycles/<cycle_id>.md`` via ``vault_write``.

    If state already has ``persisted=True`` (set by tag_and_persist),
    skips re-writing the proposed entity frontmatter and writes only
    the summary.

    Args:
        state: IKIGAiStateDict from LangGraph.

    Returns:
        State update dict with ``commit_summary``, ``cycle_id``,
        ``vault_path``, ``last_step`` set. On failure, ``commit_summary``
        begins with "[ERROR]" and ``vault_path`` is None.

    Raises:
        Does NOT raise — all errors are caught and returned as
        commit_summary prefix. Drift invariant (g) requires audit-safe
        writes; crashing the graph on transient vault errors would
        lose plan context.
    """
    if _KILL_SWITCH:
        return {
            "commit_summary": "Kill switch active — no writes performed",
            "cycle_id": state.get("cycle_id", dt.date.today().isoformat()),
            "vault_path": None,
            "last_step": "commit",
        }

    cycle_id = state.get("cycle_id", dt.date.today().isoformat())
    regime = state.get("regime_state", "MAINTAIN")
    q_he = state.get("q_he_score", 0.65)
    vector_scores = cast(dict[str, float], state.get("vector_scores", {}))
    meta_vector = state.get("meta_vector_score", 0.0)
    corrections_raw: list[dict[str, Any]] = cast(list[dict[str, Any]], state.get("corrections", []))

    # Build cycle-summary frontmatter
    frontmatter: dict[str, Any] = {
        "cycle_id": cycle_id,
        "regime": regime,
        "q_he_score": float(q_he),
        "vector_scores": vector_scores,
        "meta_vector_score": float(meta_vector),
        "corrections_count": len(corrections_raw),
        "persisted_by": "tag_and_persist" if state.get("persisted") else "commit_node",
        "committed_at": dt.datetime.now().isoformat(),
    }

    body = (
        f"# Cycle {cycle_id}\n\n"
        f"- **Regime**: {regime}\n"
        f"- **Q_HE**: {q_he:.4f}\n"
        f"- **Meta vector**: {meta_vector:.4f}\n"
        f"- **Vector scores**: {vector_scores}\n"
        f"- **Corrections**: {len(corrections_raw)}\n"
    )

    vault_path = f"ikigai/cycles/{cycle_id}.md"

    try:
        result_str = vault_write(
            vault_path=vault_path,
            frontmatter=frontmatter,
            body=body,
            actor="agent",
        )
    except Exception as exc:  # belt-and-braces — vault_write already catches internally
        return {
            "commit_summary": f"[ERROR] vault_write raised {type(exc).__name__}: {exc}",
            "cycle_id": cycle_id,
            "vault_path": None,
            "last_step": "commit",
        }

    # vault_write returns a JSON string. Check for error envelope.
    try:
        result = json.loads(result_str)
    except (json.JSONDecodeError, TypeError):
        result = {}

    if isinstance(result, dict) and "error" in result:
        return {
            "commit_summary": f"[ERROR] {result['error']}",
            "cycle_id": cycle_id,
            "vault_path": None,
            "last_step": "commit",
        }

    summary = (
        f"cycle={cycle_id} regime={regime} q_he={q_he:.4f} "
        f"vectors={vector_scores} meta={meta_vector:.2f} "
        f"corrections={len(corrections_raw)} vault={vault_path}"
    )
    return {
        "commit_summary": summary,
        "cycle_id": cycle_id,
        "vault_path": vault_path,
        "last_step": "commit",
    }


def set_kill_switch(active: bool) -> None:
    """Toggle kill switch for guarded writes."""
    global _KILL_SWITCH
    _KILL_SWITCH = active
