"""Filesystem-based append-only investigation queue. Atomic writes via temp + rename.

Per Plan C (2026-09-03): investigations are pre-form tasks that don't fit the
6-level SONHO/OBJETIVO/META/PROJETO/ENTREGA/TAREFA hierarchy. They have their
own inq_id (NOT a UEID) and a status lifecycle: open → in_progress →
resolved | archived (terminal).

Mirrors src/mesh/queue.py (TaskChange review queue) for consistency.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from src.contracts.investigation import Investigation, InvestigationStatus

# Project root is 2 levels up from src/mesh/
PROJECT_ROOT = Path(__file__).parent.parent.parent
QUEUE_DIR = PROJECT_ROOT / "data" / "investigation_queue"

# Reuse retry decorator pattern from src/mesh/queue.py
_MAX_ATTEMPTS = 4
_INITIAL_BACKOFF_S = 0.1
_MAX_BACKOFF_S = 2.0
_RETRYABLE_EXCEPTIONS = (OSError, PermissionError)


def _retry_atomic_write(write_fn):  # type: ignore[no-untyped-def]
    """Decorator: retry an atomic file operation on transient OSError."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        backoff = _INITIAL_BACKOFF_S
        last_exc: BaseException | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return write_fn(*args, **kwargs)
            except _RETRYABLE_EXCEPTIONS as exc:
                last_exc = exc
                if attempt >= _MAX_ATTEMPTS:
                    raise
                sleep_for = backoff * (0.5 + (attempt * 0.137) % 1.0)
                time.sleep(min(sleep_for, _MAX_BACKOFF_S))
                backoff = min(backoff * 2.0, _MAX_BACKOFF_S)
        raise RuntimeError(f"unreachable: {last_exc}")

    return wrapper


# ---------------------------------------------------------------------------
# Valid status transitions (append-only — no resurrection)
# ---------------------------------------------------------------------------
_VALID_TRANSITIONS: dict[InvestigationStatus, frozenset[InvestigationStatus]] = {
    "open": frozenset({"in_progress", "archived", "resolved"}),  # resolved for crystallized
    "in_progress": frozenset({"resolved", "archived", "open"}),  # allow back to open if false alarm
    "resolved": frozenset(),  # terminal
    "archived": frozenset(),  # terminal
}


def ensure_queue_dir() -> Path:
    """Create QUEUE_DIR if missing. Idempotent. Returns the path."""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return QUEUE_DIR


def _investigation_path(inq_id: str) -> Path:
    """Resolve a single investigation file path. Filename = inq_id + .json."""
    # Sanitize: inq_id format is inq-YYYYMMDD-NNN. Allow only [a-z0-9-].
    safe = "".join(c for c in inq_id if c.isalnum() or c == "-")
    if safe != inq_id or not safe:
        raise ValueError(f"invalid inq_id: {inq_id!r}")
    return ensure_queue_dir() / f"{safe}.json"


@_retry_atomic_write
def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON atomically: write to tmp, then rename. Reused for all writes."""
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    try:
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        os.replace(tmp, path)  # atomic on POSIX and Windows (Python 3.3+)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass  # best-effort cleanup


def enqueue(inv: Investigation) -> Path:
    """Persist an Investigation to QUEUE_DIR. Idempotent on inq_id.

    The new investigation is written atomically. If a file with the same inq_id
    already exists, it is OVERWRITTEN (this is the only 'edit' allowed —
    Investigations themselves are frozen; only status transitions are mutations).
    """
    path = _investigation_path(inv.inq_id)
    payload = inv.model_dump(mode="json")
    _atomic_write_json(path, payload)
    return path


def transition(
    inq_id: str,
    new_status: InvestigationStatus,
    actor: str,
    inq_ueid: str | None = None,
) -> Investigation:
    """Transition an investigation's status atomically.

    Reads the current record, validates the transition (no resurrection from
    terminal states), updates status + updated_at + actor, then writes back
    atomically.

    Returns the updated Investigation. Raises KeyError if not found, ValueError
    if transition is invalid.
    """
    path = _investigation_path(inq_id)
    if not path.exists():
        raise KeyError(f"investigation not found: {inq_id}")
    current = Investigation.model_validate_json(path.read_text(encoding="utf-8"))
    if current.status == new_status:
        return current  # no-op
    valid = _VALID_TRANSITIONS.get(current.status, frozenset())
    if new_status not in valid:
        raise ValueError(
            f"invalid transition: {current.status} → {new_status} "
            f"(allowed: {sorted(valid)})"
        )
    updated = current.model_copy(
        update={
            "status": new_status,
            "updated_at": datetime.now(),
            "actor": actor,
            "inq_ueid": inq_ueid if inq_ueid is not None else current.inq_ueid,
        }
    )
    payload = updated.model_dump(mode="json")
    _atomic_write_json(path, payload)
    return updated


def get(inq_id: str) -> Investigation:
    """Fetch a single investigation by inq_id. Raises KeyError if not found."""
    path = _investigation_path(inq_id)
    if not path.exists():
        raise KeyError(f"investigation not found: {inq_id}")
    return Investigation.model_validate_json(path.read_text(encoding="utf-8"))


def list_all() -> list[Investigation]:
    """List all investigations, sorted by inq_id. Skips malformed files (logged)."""
    ensure_queue_dir()
    out: list[Investigation] = []
    for p in sorted(QUEUE_DIR.glob("inq-*.json")):
        try:
            out.append(Investigation.model_validate_json(p.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            continue  # skip malformed — drift invariant (h) catches structural issues
    return out


def list_by_status(status: InvestigationStatus) -> list[Investigation]:
    """List investigations filtered by status. Sorted by inq_id."""
    return [inv for inv in list_all() if inv.status == status]


def audit_log_path() -> Path:
    """Audit log: append-only log of every state transition."""
    return ensure_queue_dir() / ".investigation_audit.log"


@_retry_atomic_write
def _append_audit(line: str) -> None:
    """Append a single line to the audit log atomically."""
    with audit_log_path().open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def log_transition(inq_id: str, old: InvestigationStatus, new: InvestigationStatus, actor: str) -> None:
    """Append a transition event to the audit log. Format: ISO8601|inq_id|old→new|actor."""
    ts = datetime.now().isoformat()
    _append_audit(f"{ts}|{inq_id}|{old}->{new}|{actor}")


# Convenience for tests / scripts
def iter_all() -> Iterator[Investigation]:
    """Iterate investigations lazily."""
    for inv in list_all():
        yield inv
