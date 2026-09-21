"""Recall stage: gathers context for reasoning (decision #9).

M88: Real implementation - fetches recent daily intentions and weekly
aggregations from memory_db. Used by reason_node to ground proposals
in actual project history rather than empty stub data.

Falls back to empty context if memory_db doesn't exist or is empty.
"""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _resolve_memory_db() -> str | None:
    """Find the memory SQLite DB. Returns path or None if not found.

    Looks in:
    1. IKIGAI_MEMORY_DB env var (explicit override)
    2. <project_root>/data/memory.db
    3. <project_root>/data/ikigai.db
    """
    explicit = os.environ.get("IKIGAI_MEMORY_DB")
    if explicit and Path(explicit).exists():
        return explicit

    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    for candidate in ["data/memory.db", "data/ikigai.db"]:
        path = project_root / candidate
        if path.exists():
            return str(path)
    return None


def recall_node(state: dict[str, Any]) -> dict[str, Any]:
    """Fetch recent context from memory_db (M88).

    Reads the last 14 days of daily intentions + last week's aggregation.
    Stores in state['context']. All failures are graceful: returns
    partial context with error info, never crashes the graph.
    """
    state = dict(state)
    context = dict(state.get("context") or {})

    memory_db = _resolve_memory_db()
    today = date.today()
    two_weeks_ago = today - timedelta(days=14)

    context["recalled_at"] = today.isoformat()
    context["recall_attempt"] = (context.get("recall_attempt") or 0) + 1

    if memory_db is None:
        context["strategics_loaded"] = False
        context["recall_error"] = "no memory_db found"
        context["daily_intentions_count"] = 0
        context["weekly_aggregations_count"] = 0
        state["context"] = context
        state["last_step"] = "recall"
        return state

    # Lazy import to avoid hard dep on memory_db module
    try:
        from src.ikigai.src.agents.v2.memory_read import (
            read_daily_intentions,
            read_weekly_aggregations,
        )

        daily = read_daily_intentions(memory_db, (two_weeks_ago, today))
        weekly = read_weekly_aggregations(memory_db, (two_weeks_ago, today))

        context["strategics_loaded"] = True
        context["daily_intentions_count"] = len(daily)
        context["weekly_aggregations_count"] = len(weekly)
        # Keep last 5 daily intentions inline for reason_node to consume.
        # DailyIntentionRecord has body_markdown (full text), not
        # pre-parsed intentions list - we expose the body so reason
        # can ground its proposals in actual journal content.
        context["recent_intentions"] = [
            {
                "ueid": d.get("daily_ueid"),
                "ts": d.get("ts"),
                "vault_path": d.get("vault_path"),
                "body_markdown": d.get("body_markdown", ""),
                "actor": d.get("actor"),
            }
            for d in daily[-5:]
        ]
        context["memory_db"] = memory_db
    except Exception as exc:  # noqa: BLE001
        logger.warning("recall_node memory_read failed: %s", exc)
        context["strategics_loaded"] = False
        context["recall_error"] = f"{type(exc).__name__}: {exc}"
        context["daily_intentions_count"] = 0
        context["weekly_aggregations_count"] = 0

    state["context"] = context
    state["last_step"] = "recall"
    return state
