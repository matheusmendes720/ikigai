"""Kill switch — 3-mechanism activation system (ADR-029).

This module implements the kill switch architectural primitive per
ADR-029 (§S1 Activation + §S2 Escalation + §S3 Audit + §S4 Recovery).
The kill switch is the load-bearing safety mechanism for Wave 5 (Scenario C)
and gates 9 downstream tasks (W5.2 / W5.5 / W5.6 / W5.7 / W5.10).

The kill switch has THREE activation mechanisms (priority-ordered):

1. **Env var** ``IKIGAI_KILL_SWITCH=1`` — emergency override (priority 1).
2. **Vault file** ``<vault_root>/.kill_switch.md`` with frontmatter
   ``status: active`` — persistent cross-restart (priority 2).
3. **Data file flag** ``<data_root>/.kill_switch`` — local-dev convenience
   (priority 3).

All tuning constants live in ``prompts/algorithm_constants.json`` (no Python
``DEFAULT_KILL_SWITCH_*`` constants permitted per ADR-019 R2 + ADR-029).

Public API
----------
- :class:`KillSwitchActivationStatus` — Pydantic v2 strict status of all
  3 mechanisms.
- :class:`KillSwitchEvent` — Pydantic v2 strict event model appended to
  ``data/review_queue/`` when the kill switch fires.
- :func:`check_kill_switch` — read all 3 mechanisms, return priority-
  resolved status.
- :func:`fire_kill_switch` — atomically append a KillSwitchEvent to
  the review queue.
- :func:`recover_kill_switch` — operator-only path that clears all
  3 mechanisms.

Drift invariant (e) design (W4.7 retroactive ship)
--------------------------------------------------
Per ADR-029 R12, ``vault_write(actor='agent')`` MUST traverse
``transition_validator``. The wrapper at :mod:`vault_write_wrapper`
ensures this. Drift invariant (e) verifies the wrapper is the only
legal caller of ``vault_write`` in ``agents/v2/*.py``.

This module is the SINGLE source of truth for activation detection;
``vault_write_wrapper`` imports and uses :func:`check_kill_switch`.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from src.contracts.common import UEID

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENV_VAR_NAME = "IKIGAI_KILL_SWITCH"
"""Environment variable checked at priority 1 (emergency override)."""

VAULT_KILL_SWITCH_FILENAME = ".kill_switch.md"
"""Vault file checked at priority 2 (persistent cross-restart)."""

DATA_KILL_SWITCH_FILENAME = ".kill_switch"
"""Data file checked at priority 3 (local-dev convenience)."""

# Module-level enums (frozen Literal types for Pydantic v2 strict).

KillSwitchTrigger = Literal[
    "actor_mismatch",
    "rate_limit_exceeded",
    "manual_override",
    "vault_write_bypass",
]
"""Reason the kill switch fired (per ADR-029 S2)."""

KillSwitchActor = Literal["user", "agent", "system", "unknown"]
"""Actor at fault (per ADR-029 S3)."""

KillSwitchActionStatus = Literal["kill_switch_active"]
"""TaskStatus enum extension value (per ADR-029 S5.4)."""

_UEID_KILL_PREFIX = "kill"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_epoch() -> float:
    """Unix-epoch REAL seconds (ADR-028 R1)."""
    return time.time()


def _generate_event_id() -> str:
    """Generate a ULID/UUID-style event_id matching existing TaskChange entries."""
    return uuid.uuid4().hex


def _make_kill_ueid() -> UEID:
    """Build a 4-part UEID for a kill switch event (ADR-014).

    Format: ``kill:<slug>:<uuid>:<hash>``. Hash is short-hex (16 chars).
    """
    u = str(uuid.uuid4())
    h = uuid.uuid4().hex[:16]
    return UEID(f"{_UEID_KILL_PREFIX}:kill-event:{u}:{h}")


def _generate_timestamp_slug() -> str:
    """Generate a sortable filename slug from epoch seconds.

    Mirrors ``mesh/queue.py`` ``enqueue()`` filename convention
    (``<event_id>.json``); here we use a timestamp-first slug for
    ``ls -lt`` semantic ordering (per ADR-029 S5.1).
    """
    return f"{int(_now_epoch() * 1000):013d}"


# ---------------------------------------------------------------------------
# Pydantic v2 strict schemas
# ---------------------------------------------------------------------------


class KillSwitchActivationStatus(BaseModel):
    """Status of all 3 kill switch activation mechanisms.

    Per ADR-029 S1 + R1. Short-circuit priority: env var > vault file >
    data file. Use :attr:`is_active` for boolean aggregation and
    :attr:`active_reason` for which mechanism wins.

    Pydantic v2 strict: ``frozen=True, extra='forbid'``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    env_var_active: bool
    """True iff ``IKIGAI_KILL_SWITCH=1``."""

    vault_file_active: bool
    """True iff ``<vault_root>/.kill_switch.md`` frontmatter ``status=active``."""

    data_file_active: bool
    """True iff ``<data_root>/.kill_switch`` exists OR content = 'active'."""

    @property
    def is_active(self) -> bool:
        """True if any mechanism is active (R1 priority aggregation)."""
        return self.env_var_active or self.vault_file_active or self.data_file_active

    @property
    def active_reason(self) -> str:
        """First-match-wins priority reason per R1.

        Returns one of ``'env_var'``, ``'vault_file'``, ``'data_file'``,
        ``'none'``.
        """
        if self.env_var_active:
            return "env_var"
        if self.vault_file_active:
            return "vault_file"
        if self.data_file_active:
            return "data_file"
        return "none"


class KillSwitchEvent(BaseModel):
    """Kill switch escalation event — Pydantic v2 strict.

    Per ADR-029 S3 — strict extension of :class:`TaskChange` with
    kill switch-specific fields. All events land in
    ``data/review_queue/`` (filesystem append-only per ADR-029 S5.1).

    Fields:
        event_id: ULID/UUID matching TaskChange convention.
        ueid: 4-part UEID per ADR-014 (the kill_id).
        kill_id: 8-char ULID prefix (used for audit log cross-reference).
        timestamp: Unix-epoch REAL per ADR-028 R1.
        kill_switch_trigger: 4-value enum (actor_mismatch, rate_limit,
            manual_override, vault_write_bypass).
        actor_at_fault: which actor's call triggered the kill switch.
        entity_id: 4-part UEID of the entity being mutated (None if
            no entity in scope).
        context: arbitrary diagnostic info (call site, rate count, etc.).
        recovery_path: human-readable clearance instructions.

    Pydantic v2 strict: ``frozen=True, extra='forbid'``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    ueid: UEID
    kill_id: str
    timestamp: float
    kill_switch_trigger: KillSwitchTrigger
    actor_at_fault: KillSwitchActor
    entity_id: UEID | None
    context: dict[str, Any]
    recovery_path: str


# ---------------------------------------------------------------------------
# Activation detection (S1 + R1)
# ---------------------------------------------------------------------------

_FRONTMATTER_STATUS_RE = re.compile(r"^status:\s*active\s*$", re.MULTILINE)


def _parse_vault_frontmatter(vault_kill_path: Path) -> dict[str, Any] | None:
    """Parse minimal YAML frontmatter from a vault kill switch file.

    Returns ``None`` if the file is missing or unparseable. Only handles
    a single ``key: value`` line per key (sufficient for ``status: active``).
    """
    try:
        if not vault_kill_path.exists():
            return None
        content = vault_kill_path.read_text(encoding="utf-8")
    except OSError:
        return None
    # Frontmatter is delimited by ``---`` lines.
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    fm_block = parts[1].strip()
    parsed: dict[str, Any] = {}
    for line in fm_block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        parsed[k.strip()] = v.strip()
    return parsed


def _check_env_var_active() -> bool:
    """Env var check (priority 1) per ADR-029 S1."""
    return os.environ.get(ENV_VAR_NAME) == "1"


def _check_vault_file_active(vault_root: Path) -> bool:
    """Vault file check (priority 2) per ADR-029 S1."""
    vault_kill = vault_root / VAULT_KILL_SWITCH_FILENAME
    if not vault_kill.exists():
        return False
    fm = _parse_vault_frontmatter(vault_kill)
    if not fm:
        return False
    return str(fm.get("status", "")).lower() == "active"


def _check_data_file_active(data_root: Path) -> bool:
    """Data file flag check (priority 3) per ADR-029 S1."""
    data_kill = data_root / DATA_KILL_SWITCH_FILENAME
    if not data_kill.exists():
        return False
    # Both ``exists()`` AND content=="active" trigger (R1).
    try:
        return data_kill.read_text(encoding="utf-8").strip() == "active"
    except OSError:
        return True  # exists but unreadable -> still active (fail-secure)


def check_kill_switch(vault_root: Path, data_root: Path) -> KillSwitchActivationStatus:
    """S1: Detect all 3 mechanisms + return priority-resolved status.

    Per ADR-029 R1, the priority is env var > vault file > data file.
    The :attr:`KillSwitchActivationStatus.is_active` property aggregates
    the boolean states; :attr:`KillSwitchActivationStatus.active_reason`
    reports the FIRST mechanism that fired (short-circuit semantic).

    Args:
        vault_root: Path to the vault root directory.
        data_root: Path to the data root directory.

    Returns:
        A frozen ``KillSwitchActivationStatus`` enumerating all 3
        mechanisms.
    """
    env_active = _check_env_var_active()
    vault_active = _check_vault_file_active(Path(vault_root))
    data_active = _check_data_file_active(Path(data_root))
    return KillSwitchActivationStatus(
        env_var_active=env_active,
        vault_file_active=vault_active,
        data_file_active=data_active,
    )


# ---------------------------------------------------------------------------
# Escalation (S2)
# ---------------------------------------------------------------------------


def _recovery_path_for_reason(reason: str) -> str:
    """Generate a human-readable recovery instruction per activating reason.

    Mirrors ADR-029 S4 step 2:
    - ``env_var``: ``unset IKIGAI_KILL_SWITCH``
    - ``vault_file``: ``edit vault/.kill_switch.md and set status: inactive``
    - ``data_file``: ``rm data/.kill_switch``
    """
    if reason == "env_var":
        return f"unset {ENV_VAR_NAME}"
    if reason == "vault_file":
        return f"Edit {VAULT_KILL_SWITCH_FILENAME} and set status: inactive (or delete the file)"
    if reason == "data_file":
        return f"rm {DATA_KILL_SWITCH_FILENAME}"
    return "Inspect data/review_queue/ and clear the activating mechanism"


def _atomic_write_json(target: Path, content: str) -> None:
    """Atomic write to ``target`` via temp file + os.replace (per Phase 3 v1).

    Mirrors ``src/mesh/queue.py`` ``_atomic_write_json``.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_kill_switch_", dir=str(target.parent))
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


def _append_audit_log(
    vault_root: Path,
    *,
    actor: str,
    entity_id: str | None,
    trigger: str,
    kill_id: str,
) -> None:
    """Append a kill switch audit entry to ``<vault_root>/.vault_audit.log``.

    Per ADR-029 S2.3 — append-only, never modifies existing entries.
    Mirrors the audit log pattern in ``vault_write.py``. Failures are
    swallowed (audit log MUST NOT fail the kill switch fire).
    """
    try:
        audit_path = Path(vault_root) / ".vault_audit.log"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        ts = _now_epoch()
        line = (
            f"{ts:.6f} kill_switch actor={actor} entity_id={entity_id} "
            f"trigger={trigger} kill_id={kill_id}\n"
        )
        with audit_path.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        # Audit log write failure must NOT fail the kill switch fire.
        pass


def fire_kill_switch(
    event: KillSwitchEvent,
    review_queue_dir: Path,
    vault_root: Path | None = None,
) -> Path:
    """S2: Atomically append ``event`` to the review queue.

    Per ADR-029 S2 — escalation sequence:
    1. Write ``KillSwitchEvent`` to ``data/review_queue/<ts>-<kill_id>.json``
       (atomic via temp + rename, mirrors ``mesh/queue.py``).
    2. Append audit log entry to ``<vault_root>/.vault_audit.log``
       (best-effort, swallowed on failure).

    Args:
        event: The ``KillSwitchEvent`` to emit.
        review_queue_dir: Target directory (typically ``data/review_queue/``).
        vault_root: Optional vault root for audit log appending.

    Returns:
        The ``Path`` of the written JSON file.
    """
    ts_slug = _generate_timestamp_slug()
    target = Path(review_queue_dir) / f"{ts_slug}-{event.kill_id}.json"
    payload = event.model_dump_json()
    _atomic_write_json(target, payload)

    # Audit log extension (best-effort).
    if vault_root is not None:
        _append_audit_log(
            Path(vault_root),
            actor=event.actor_at_fault,
            entity_id=str(event.entity_id) if event.entity_id is not None else None,
            trigger=event.kill_switch_trigger,
            kill_id=event.kill_id,
        )
    return target


def build_kill_switch_event(
    *,
    trigger: KillSwitchTrigger,
    actor_at_fault: KillSwitchActor,
    entity_id: UEID | None,
    context: dict[str, Any],
    recovery_reason: str,
) -> KillSwitchEvent:
    """Construct a fully-formed ``KillSwitchEvent``.

    Helper for callers (``vault_write_wrapper``) that need to build
    the event without manually managing UEID/event_id/timestamp.
    """
    ueid = _make_kill_ueid()
    kill_id = ueid.split(":")[1][:8] if ":" in ueid else ueid[:8]
    return KillSwitchEvent(
        event_id=_generate_event_id(),
        ueid=ueid,
        kill_id=kill_id,
        timestamp=_now_epoch(),
        kill_switch_trigger=trigger,
        actor_at_fault=actor_at_fault,
        entity_id=entity_id,
        context=context,
        recovery_path=_recovery_path_for_reason(recovery_reason),
    )


# ---------------------------------------------------------------------------
# Recovery (S4)
# ---------------------------------------------------------------------------


def recover_kill_switch(vault_root: Path, data_root: Path) -> bool:
    """S4: Clear all 3 kill switch mechanisms.

    Per ADR-029 S4 — manual operator action. Clears:
    1. ``IKIGAI_KILL_SWITCH`` env var (via ``os.environ.pop``).
    2. Vault kill switch file (deletes ``<vault_root>/.kill_switch.md``).
    3. Data kill switch file (deletes ``<data_root>/.kill_switch``).

    Returns:
        True if all 3 mechanisms are clear after the operation.
        The caller may still be in a kill-switched state if new mechanisms
        are activated concurrently (rare; this function does not guard).
    """
    # Priority 1 — env var
    os.environ.pop(ENV_VAR_NAME, None)
    # Priority 2 — vault file
    vault_kill = Path(vault_root) / VAULT_KILL_SWITCH_FILENAME
    if vault_kill.exists():
        try:
            vault_kill.unlink()
        except OSError:
            pass
    # Priority 3 — data file
    data_kill = Path(data_root) / DATA_KILL_SWITCH_FILENAME
    if data_kill.exists():
        try:
            data_kill.unlink()
        except OSError:
            pass
    final = check_kill_switch(Path(vault_root), Path(data_root))
    return not final.is_active


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

__all__ = [
    "DATA_KILL_SWITCH_FILENAME",
    "ENV_VAR_NAME",
    "VAULT_KILL_SWITCH_FILENAME",
    "KillSwitchActivationStatus",
    "KillSwitchActor",
    "KillSwitchEvent",
    "KillSwitchTrigger",
    "build_kill_switch_event",
    "check_kill_switch",
    "fire_kill_switch",
    "recover_kill_switch",
]


# Re-exported for consumer convenience
_ = json  # keep import alive (json is used by callers in test only)
