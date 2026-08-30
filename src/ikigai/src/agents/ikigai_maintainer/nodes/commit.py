"""commit node — persist IKIGAi state to SQLite + markdown vault.

Append-only writes guarded by kill_switch. Emits plan cycle log.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from ..state import IKIGAiStateDict


# Kill switch — set to True to block all writes
_KILL_SWITCH = False


def commit_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Persist cycle results to SQLite and markdown vault.

    Writes are append-only (plan_entities table). Skipped if kill_switch is active.
    Returns summary of what was committed.
    """
    # B5.B.1: lazy import as fallback if eager fails at graph compile time
    # (the ikigai.mcp_server.* package does not exist under src/ikigai/src/ikigai/;
    # the real _write_tasks_to_data is at src/ikigai/src/mcp_server/server.py:188)
    from src.ikigai.src.mcp_server.server import _write_tasks_to_data

    if _KILL_SWITCH:
        return {
            "commit_summary": "Kill switch active — no writes performed",
            "last_step": "commit",
        }

    cycle_id = state.get("cycle_id", dt.date.today().isoformat())
    regime = state.get("regime_state", "MAINTAIN")
    q_he = state.get("q_he_score", 0.65)
    vector_scores = state.get("vector_scores", {})
    meta_vector = state.get("meta_vector_score", 0.0)
    corrections = state.get("corrections", [])

    summary_lines: list[str] = []

    # 1. Write to SQLite via operational persistence layer
    committed = _write_to_sqlite(cycle_id, regime, q_he, vector_scores, meta_vector, corrections)
    summary_lines.append(f"SQLite: {committed}")

    # 2. Append to markdown vault cycle log
    vault_path = _get_vault_path()
    if vault_path:
        appended = _append_to_vault(
            vault_path, cycle_id, regime, q_he, vector_scores, meta_vector, corrections
        )
        summary_lines.append(f"Vault: {appended}")
    else:
        summary_lines.append("Vault: not configured")

    # 3. Write structured tasks to data/tasks.jsonl for interfaces
    structured_tasks = state.get("structured_tasks", [])
    if structured_tasks:
        written = _write_tasks_to_data(structured_tasks)
        summary_lines.append(f"Tasks: {written}")
    else:
        summary_lines.append("Tasks: no structured_tasks in state")

    return {
        "commit_summary": "; ".join(summary_lines),
        "cycle_id": cycle_id,
        "last_step": "commit",
    }


def _write_to_sqlite(
    cycle_id: str,
    regime: str,
    q_he: float,
    vector_scores: dict[str, float],
    meta_vector: float,
    corrections: list[dict],
) -> str:
    """Write cycle record to plan_entities SQLite table via SQLiteAdapter."""
    try:
        from ikigai.propagation.sqlite_adapter import SQLiteAdapter

        db_path = Path.home() / ".ikigai" / "plan_entities.db"
        adapter = SQLiteAdapter(db_path=db_path)

        created_at = dt.datetime.now().isoformat()
        ueid = f"cycle:{cycle_id}"

        adapter.upsert(
            ueid=ueid,
            entity_type="cycle",
            slug=cycle_id,
            title=f"Cycle {cycle_id}",
            description=f"Regime: {regime}, Q_HE: {q_he}",
            status="ACTIVE",
            created_at=created_at,
            updated_at=created_at,
            ikigai_vectors=vector_scores,
            primary_score=q_he,
            regime_at_creation=regime,
            custom={"corrections": corrections, "meta_vector": meta_vector},
        )
        return f"ok (cycle={cycle_id})"
    except Exception as e:
        return f"error: {e}"


def _append_to_vault(
    vault_path: Path,
    cycle_id: str,
    regime: str,
    q_he: float,
    vector_scores: dict[str, float],
    meta_vector: float,
    corrections: list[dict],
) -> str:
    """Append cycle summary to markdown vault log."""
    try:
        log_file = vault_path / "ikigai_cycle_log.md"
        entry = [
            f"\n## Cycle {cycle_id}",
            f"- Date: {dt.date.today().isoformat()}",
            f"- Regime: {regime}",
            f"- Q_HE: {q_he:.4f}",
            f"- Meta-vector: {meta_vector:.2f}",
            f"- Vectors: {vector_scores}",
            f"- Corrections: {len(corrections)}",
        ]
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("\n".join(entry) + "\n")
        return f"ok ({log_file.name})"
    except Exception as e:
        return f"error: {e}"


def _get_vault_path() -> Path | None:
    """Return vault path from config or env."""
    import os

    vault = os.environ.get("IKIGAI_VAULT_PATH")
    if vault:
        return Path(vault)
    default = Path.home() / ".ikigai" / "vault"
    if default.exists():
        return default
    return None


def set_kill_switch(active: bool) -> None:
    """Toggle kill switch for guarded writes."""
    global _KILL_SWITCH
    _KILL_SWITCH = active
