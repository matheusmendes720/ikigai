"""Investigation dispatcher worker — Plan C Task 5.

Pure dispatch consumer (NO LLM). Reads open/in_progress investigations,
checks their crystallization signals (inq_ueid set, payload >threshold,
tags include 'ready'), and either:
  - emits a planning hint (logs + emits event for downstream)
  - transitions to archived if stale (>30 days in_progress)

Cron-invoked (NOT a daemon/hot loop). Idempotent. Skips malformed files.

Drift invariant (h) catches structural issues; this worker assumes
the queue is well-formed.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from contracts.investigation import Investigation
from mesh.investigation_queue import (
    ensure_queue_dir,
    list_by_status,
    log_transition,
    transition,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunables (constants only — no LLM, no scoring)
# ---------------------------------------------------------------------------
STALE_THRESHOLD_DAYS = 30  # in_progress investigations older than this get archived
CRYSTALLIZATION_UEID_PREFIX = ""  # all UEIDs valid; this reserved for future filtering
MIN_PAYLOAD_LEN_FOR_HINT = 20  # payload length threshold to emit a planning hint


def _is_stale(inv: Investigation, now: datetime | None = None) -> bool:
    """in_progress >STALE_THRESHOLD_DAYS old → stale."""
    if inv.status != "in_progress":
        return False
    now = now or datetime.now()
    return (now - inv.updated_at) > timedelta(days=STALE_THRESHOLD_DAYS)


def _has_crystallized(inv: Investigation) -> bool:
    """Crystallization signal: inq_ueid is set (investigation → hierarchy entry)."""
    return inv.inq_ueid is not None


def _should_emit_hint(inv: Investigation) -> bool:
    """Planning-hint emission signal: ready-tag + sufficient payload."""
    return "ready" in inv.tags and len(inv.payload) >= MIN_PAYLOAD_LEN_FOR_HINT


def dispatch_once(now: datetime | None = None) -> dict[str, Any]:
    """Single dispatch pass: process all open/in_progress investigations.

    Returns a summary dict:
        {"processed": int, "archived_stale": int, "crystallized": int,
         "hints_emitted": int, "errors": list[str]}

    Idempotent: safe to call repeatedly. Skips malformed files (logged).
    """
    ensure_queue_dir()
    summary: dict[str, Any] = {
        "processed": 0,
        "archived_stale": 0,
        "crystallized": 0,
        "hints_emitted": 0,
        "errors": [],
    }

    for status in ("open", "in_progress"):
        for inv in list_by_status(status):  # type: ignore[arg-type]
            try:
                summary["processed"] += 1
                # 1. Stale → archive
                if _is_stale(inv, now=now):
                    transition(inv.inq_id, "archived", actor="dispatcher:stale")
                    log_transition(inv.inq_id, inv.status, "archived", "dispatcher:stale")
                    summary["archived_stale"] += 1
                    effective_now = now if now else datetime.now()
                    age_days = (effective_now - inv.updated_at).days
                    logger.info(
                        "archived stale investigation: %s (age=%dd)",
                        inv.inq_id,
                        age_days,
                    )
                    continue

                # 2. Crystallized → emit downstream (currently just count)
                if _has_crystallized(inv):
                    summary["crystallized"] += 1
                    logger.info(
                        "crystallized investigation: %s → ueid=%s",
                        inv.inq_id,
                        inv.inq_ueid,
                    )
                    # Transition to resolved (crystallization = done)
                    transition(inv.inq_id, "resolved", actor="dispatcher:crystallized")
                    log_transition(inv.inq_id, inv.status, "resolved", "dispatcher:crystallized")
                    continue

                # 3. Ready tag + sufficient payload → planning hint
                if _should_emit_hint(inv):
                    summary["hints_emitted"] += 1
                    logger.info(
                        "planning hint emitted: %s (tags=%s, payload_len=%d)",
                        inv.inq_id,
                        inv.tags,
                        len(inv.payload),
                    )
                    # No state change — still 'open' until user acts

            except (ValueError, KeyError, OSError) as exc:
                # Skip malformed/stuck investigations
                summary["errors"].append(f"{inv.inq_id}: {exc}")
                logger.warning("dispatcher skipped %s: %s", inv.inq_id, exc)

    return summary


def main() -> dict[str, Any]:
    """Cron entry point. Single pass, exits 0 on completion."""
    summary = dispatch_once()
    logger.info(
        "dispatcher summary: processed=%d archived_stale=%d crystallized=%d hints=%d errors=%d",
        summary["processed"],
        summary["archived_stale"],
        summary["crystallized"],
        summary["hints_emitted"],
        len(summary["errors"]),
    )
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    main()
