"""W5.3 — Internal helpers for the kill-switch consumer UX.

Extracted from `kill_switch.py` to keep that file under the CLAUDE.md
500-line guideline (and the design doc's 200-line budget). Everything here
is private to `interfaces.cli.kill_switch` — no external surface.

Modules re-exported by `sys_ikigai.security.kill_switch` (status +
recovery) remain imported directly by the CLI; this module only owns
the audit-append path + history-read helper, both of which are
infrastructure for the consumer UX (not the security layer itself).
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Audit entry model — local Pydantic v2 strict (mirrors TaskChange shape)
# ---------------------------------------------------------------------------


class KillSwitchAuditEntry(BaseModel):
    """Local audit entry model — mirrors TaskChange structure.

    Validated Pydantic v2 strict (frozen=True, extra=forbid). Reuses the
    canonical review-queue field shape (event_id / ueid / action / fields /
    source_fork / timestamp / status) without extending any global contract
    in `src/contracts/`. The `action` field is a string Literal so the
    audit can record `kill_switch_pause` / `kill_switch_resume` without
    extending the TaskAction enum (which would be a schema change).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    ueid: str
    action: Literal["kill_switch_pause", "kill_switch_resume"]
    fields: dict[str, Any]
    source_fork: str
    timestamp: float
    status: str = "pending"


# ---------------------------------------------------------------------------
# Path resolution — shared by all CLI verbs
# ---------------------------------------------------------------------------


def repo_root() -> Path:
    """Return the life/ repo root (parent of interfaces/cli/)."""
    return Path(__file__).resolve().parents[2]


def review_queue_dir() -> Path:
    return repo_root() / "data" / "review_queue"


def audit_killswitch_ueid(reason: str) -> str:
    """Build a 4-part UEID-shaped string for an audit entry.

    Format: ``kill:<reason>:<uuid>:<hash>``. Short-hex hash (16 chars).
    """
    u = str(uuid.uuid4())
    h = uuid.uuid4().hex[:16]
    return f"kill:{reason}:{u}:{h}"


# ---------------------------------------------------------------------------
# History reader — read data/review_queue/ filtered to kill_switch_ events
# ---------------------------------------------------------------------------


_AUDIT_ACTION_PREFIX = "kill_switch_"


def read_kill_switch_history(limit: int) -> list[dict[str, Any]]:
    """Read data/review_queue/*.json filtered to action.startswith('kill_switch_').

    Returns the most recent `limit` entries (sorted newest-first by file
    mtime). Each entry is a raw dict from the JSON file. Used by the
    `history` verb and `compute_rate_limit`.
    """
    qdir = review_queue_dir()
    if not qdir.is_dir():
        return []
    candidates: list[tuple[float, dict[str, Any]]] = []
    for f in qdir.glob("*.json"):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        action = str(payload.get("action", ""))
        if action.startswith(_AUDIT_ACTION_PREFIX):
            candidates.append((f.stat().st_mtime, payload))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [c[1] for c in candidates[:limit]]


def compute_rate_limit(window_s: float = 3600.0) -> dict[str, int]:
    """Sliding-window kill-switch event counts (per ADR-029 R10).

    The threshold value lives in algorithm_constants.json
    (KILL_SWITCH_RATE_LIMIT_PER_HOUR=50); the CLI is pure-consumer and
    doesn't read it directly. This helper just counts events inside the
    sliding window — the consumer decides whether to warn.
    """
    now = time.time()
    cutoff = now - window_s
    qdir = review_queue_dir()
    in_window = 0
    total = 0
    if qdir.is_dir():
        for f in qdir.glob("*.json"):
            try:
                payload = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            action = str(payload.get("action", ""))
            if not action.startswith(_AUDIT_ACTION_PREFIX):
                continue
            total += 1
            if f.stat().st_mtime >= cutoff:
                in_window += 1
    return {
        "events_in_last_window": in_window,
        "total_kill_switch_events": total,
        "window_seconds": int(window_s),
    }


# ---------------------------------------------------------------------------
# Atomic write + audit append
# ---------------------------------------------------------------------------


def atomic_write_json(target: Path, content: str) -> None:
    """Mirror mesh/queue._atomic_write_json — temp file + os.replace."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_killswitch_", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


def append_audit_entry(
    *,
    action: Literal["kill_switch_pause", "kill_switch_resume"],
    reason: str,
    active_reason_at_action: str,
) -> Path:
    """Append a pause/resume audit entry to data/review_queue/.

    Validates via local Pydantic v2 strict `KillSwitchAuditEntry`. Writes
    atomically (temp file + os.replace), mirroring mesh/queue.enqueue().
    Fail-closed: any error halts the operation.
    """
    ueid = audit_killswitch_ueid("audit")
    entry = KillSwitchAuditEntry(
        event_id=f"evt_{uuid.uuid4().hex[:12]}",
        ueid=ueid,
        action=action,
        fields={
            "reason": reason,
            "active_reason_at_action": active_reason_at_action,
        },
        source_fork="interfaces/cli",
        timestamp=time.time(),
    )
    payload = entry.model_dump_json()
    qdir = review_queue_dir()
    filename = f"{int(entry.timestamp * 1000):013d}-{entry.event_id}.json"
    target = qdir / filename
    atomic_write_json(target, payload)
    return target


__all__ = [
    "KillSwitchAuditEntry",
    "repo_root",
    "review_queue_dir",
    "read_kill_switch_history",
    "compute_rate_limit",
    "append_audit_entry",
    "atomic_write_json",
    "audit_killswitch_ueid",
]
