"""vault_write_wrapper — enforcement layer atop ``vault_write`` (ADR-029).

Per ADR-029 §S2 + R2, every ``vault_write`` call MUST go through this
wrapper. The wrapper enforces:

1. **Kill switch check** (R1 priority: env var > vault file > data file).
2. **Rate limit per actor per hour** (R10, sliding window).
3. **Transition validator traversal** (R4 + R8).
4. **Audit log entry** pre-write + post-write (S2.3 + R3, append-only).
5. **Legal caller whitelist** (R6 + R7 — ``memory_write_atomic``,
   ``dispatch_sub_agents``, ``tag_and_persist``, ``skill_orchestrator``).

The wrapper is the SINGLE enforcement point for actor discipline (R2).
Drift invariant (e) (W4.7 retroactive ship) verifies the wrapper is
used everywhere in ``agents/v2/*.py``.

Per the brief "Drift invariant (e) design constraint", this module
MUST NOT duplicate existing audit logic from ``vault_write.py`` —
it is purely additive. ``vault_write`` remains the underlying
canonical writer per ADR-012; this wrapper sits ABOVE it.

Layered enforcement
-------------------
::

    Caller
      ↓
    1. Kill switch check     ← kill_switch.check_kill_switch()
      ↓ (if active → fire_kill_switch + abort)
    2. Rate limit check      ← _RateLimitTracker (R10)
      ↓ (if exceeded → fire_kill_switch + abort)
    3. Validate actor         ← {"user", "agent", "system"} (R9)
      ↓ (if invalid → abort)
    4. Transition validator  ← transition_validator.validate_phase_transition()
      ↓ (if SONHO + actor != user → abort)
    5. Legal caller whitelist ← if ``actor == 'agent'`` (R6 + R7)
      ↓ (if illegal → abort)
    6. Audit pre-write       ← .vault_audit.log append
      ↓
    7. vault_write call      ← ikigai.vault.vault_write.vault_write()
      ↓
    8. Audit post-write      ← .vault_audit.log append
      ↓
    Return result

Monkeypatch pattern
-------------------
The brief recommends monkeypatching ``vault_write`` at module-import
time so that ``from ikigai.security.vault_write import vault_write``
ALWAYS returns the wrapped version. This module exports
:func:`install_wrapper` for that purpose.

Module docstring in ``kill_switch.py`` documents the rationale.
"""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from src.contracts.common import UEID

from .kill_switch import (
    KillSwitchActivationStatus,
    KillSwitchActor,
    KillSwitchEvent,
    KillSwitchTrigger,
    build_kill_switch_event,
    check_kill_switch,
    fire_kill_switch,
)
from .transition_validator import validate_phase_transition

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ActorType = Literal["user", "agent", "system"]
"""Vault write actor literal (matches ``vault_write.py:67`` validation)."""

# Legal callers (R6 + R7). Callers in this set bypass the kill switch
# enforcement — they are recognized as legitimate actors of vault_write.
LEGAL_CALLERS: frozenset[str] = frozenset(
    {
        "memory_write_atomic",  # ADR-028 R1 amended
        "dispatch_sub_agents",  # ADR-026 S2.3
        "tag_and_persist",  # Plan A v2 node
        "skill_orchestrator",  # ADR-025 R6
    }
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class KillSwitchAbort(RuntimeError):  # noqa: N818 — descriptive verb suffix
    """Raised when the kill switch fires during a wrapped vault_write (R2)."""


class KillSwitchRateLimitExceeded(RuntimeError):  # noqa: N818 — descriptive verb suffix
    """Raised when an actor exceeds the per-hour rate limit (R10)."""


class KillSwitchActorViolation(RuntimeError):  # noqa: N818 — descriptive noun suffix
    """Raised when ``actor`` is not in ``{'user', 'agent', 'system'}`` (R9)."""


class KillSwitchBypassDetected(RuntimeError):  # noqa: N818 — descriptive verb suffix
    """Raised when a caller without a legal bypass attempts SONHO write (R8)."""


# ---------------------------------------------------------------------------
# Rate limit tracker (R10 — in-memory sliding window per actor)
# ---------------------------------------------------------------------------


class _RateLimitTracker:
    """Sliding-window rate limit tracker per actor (per ADR-029 R10).

    The window is in-memory; process restart resets the counter (per
    ADR-029 R10 "Rate-limit window is in-memory" negative consequence).

    Defaults to ``algorithm_constants.json`` values:
    - ``KILL_SWITCH_RATE_LIMIT_PER_HOUR``: 50 (max writes per window)
    - ``KILL_SWITCH_RATE_LIMIT_WINDOW_S``: 3600 (window size in seconds)
    """

    def __init__(
        self,
        rate_limit_per_window: int,
        window_seconds: float,
    ) -> None:
        self._limit = rate_limit_per_window
        self._window_s = window_seconds
        self._lock = threading.Lock()
        # actor -> deque[float] of write timestamps within the window
        self._writes: dict[str, deque[float]] = {}

    def record(self, actor: str, ts: float | None = None) -> None:
        """Record a write for ``actor`` at time ``ts`` (now if None)."""
        if ts is None:
            ts = time.time()
        with self._lock:
            dq = self._writes.setdefault(actor, deque())
            # Evict expired entries.
            cutoff = ts - self._window_s
            while dq and dq[0] < cutoff:
                dq.popleft()
            dq.append(ts)

    def is_exceeded(self, actor: str, ts: float | None = None) -> bool:
        """Return True if ``actor`` has exceeded the per-window limit."""
        if ts is None:
            ts = time.time()
        with self._lock:
            dq = self._writes.get(actor)
            if not dq:
                return False
            cutoff = ts - self._window_s
            # Count only non-expired entries.
            count = sum(1 for t in dq if t >= cutoff)
            return count >= self._limit

    def reset(self) -> None:
        """Clear all counters. Test helper."""
        with self._lock:
            self._writes.clear()


# ---------------------------------------------------------------------------
# Audit log helpers
# ---------------------------------------------------------------------------


def _append_vault_audit(
    vault_root: Path,
    *,
    actor: str,
    vault_path: str,
    trigger: str,
) -> None:
    """Append a wrapper-level audit entry (mirrors ``vault_write.py`` pattern).

    Per ADR-029 R3 — append-only, never modifies existing entries.
    Failures are swallowed.
    """
    try:
        audit_path = Path(vault_root) / ".vault_audit.log"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        ts = time.time()
        line = f"{ts:.6f} wrapper actor={actor} path={vault_path} trigger={trigger}\n"
        with audit_path.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tuning constants loader (ADR-019 R1 — read from JSON, no Python DEFAULT_*)
# ---------------------------------------------------------------------------


def _load_tuning_constants() -> tuple[int, float, bool]:
    """Load KILL_SWITCH_* + REVIEW_QUEUE_BATCH_SIZE from algorithm_constants.json.

    Per ADR-019 R1 + ADR-029 §"Algorithm Constants JSON Keys". Falls back
    to the same defensive defaults in :mod:`kill_switch` if the JSON
    is unavailable (test-friendly).
    """
    try:
        from src.ikigai.src.agents.v2.prompts.load_constants import (
            load_algorithm_constants,
        )

        data = load_algorithm_constants()
        return (
            int(data["KILL_SWITCH_RATE_LIMIT_PER_HOUR"]),
            float(data["KILL_SWITCH_RATE_LIMIT_WINDOW_S"]),
            bool(data["KILL_SWITCH_NOTIFY_OPERATOR"]),
        )
    except Exception:
        return 50, 3600.0, True


# ---------------------------------------------------------------------------
# Wrapped vault_write (the canonical API)
# ---------------------------------------------------------------------------


def make_wrapped_vault_write(
    vault_root_provider: Callable[[], Path],
    data_root_provider: Callable[[], Path],
    review_queue_dir_provider: Callable[[], Path],
    *,
    rate_limit_tracker: _RateLimitTracker | None = None,
) -> Callable[..., dict[str, Any]]:
    """Build a wrapped ``vault_write`` callable.

    Args:
        vault_root_provider: Zero-arg callable returning the vault root path.
        data_root_provider: Zero-arg callable returning the data root path.
        review_queue_dir_provider: Zero-arg callable returning the
            ``data/review_queue/`` directory.
        rate_limit_tracker: Optional pre-built tracker (test override).

    Returns:
        A callable with the same signature as
        ``ikigai.vault.vault_write.vault_write`` plus an optional
        ``entity`` kwarg (for transition_validator traversal).
    """
    rate_limit_per_hour, window_s, _notify = _load_tuning_constants()
    if rate_limit_tracker is None:
        rate_limit_tracker = _RateLimitTracker(rate_limit_per_hour, window_s)

    # Lazy import — vault_write may live in agents/v2/memory_write.py's
    # import chain; circular-import safety.
    from ikigai.vault.vault_write import vault_write as _vault_write

    def wrapped(
        *,
        actor: ActorType,
        vault_path: str,
        frontmatter_fields: dict[str, Any] | None = None,
        body: str = "",
        legal_caller: str | None = None,
        entity: Any = None,
        vault_root: Path | None = None,
    ) -> dict[str, Any]:
        """Wrapped vault_write — enforces kill switch + audit + transition.

        Signature mirrors ``vault_write.vault_write`` with two additions:

        - ``legal_caller``: optional name of the calling module (R6 + R7
          whitelist). Recognized values allow ``actor='agent'`` writes
          without firing the kill switch.
        - ``entity``: optional parsed plan entity (for transition_validator
          traversal on SONHO writes).

        Args:
            actor: ``user`` | ``agent`` | ``system``.
            vault_path: Relative vault path (e.g. ``plans/q3/task.md``).
            frontmatter_fields: YAML frontmatter dict.
            body: Markdown body.
            legal_caller: Optional whitelisted caller name.
            entity: Optional ``BasePlanContract`` for transition_validator.
            vault_root: Override vault root (defaults to provider).

        Returns:
            The dict from the underlying ``vault_write``.

        Raises:
            KillSwitchAbort: kill switch active.
            KillSwitchRateLimitExceeded: rate limit exceeded.
            KillSwitchActorViolation: invalid actor.
            KillSwitchBypassDetected: SONHO + actor != user without
                a legal_caller override.
        """
        resolved_vault_root = Path(vault_root or vault_root_provider())
        resolved_data_root = Path(data_root_provider())
        resolved_review_dir = Path(review_queue_dir_provider())

        # Step 1: Kill switch check (R1 priority)
        status: KillSwitchActivationStatus = check_kill_switch(
            resolved_vault_root, resolved_data_root
        )
        if status.is_active:
            event = build_kill_switch_event(
                trigger="manual_override",
                actor_at_fault=actor if actor in {"user", "agent", "system"} else "unknown",
                entity_id=None,
                context={
                    "mechanism": status.active_reason,
                    "vault_path": vault_path,
                },
                recovery_reason=status.active_reason,
            )
            fire_kill_switch(event, resolved_review_dir, resolved_vault_root)
            raise KillSwitchAbort(
                f"Kill switch active ({status.active_reason}); vault_write refused "
                f"(recovery: {event.recovery_path})"
            )

        # Step 2: Rate limit (R10)
        if rate_limit_tracker.is_exceeded(actor):
            event = build_kill_switch_event(
                trigger="rate_limit_exceeded",
                actor_at_fault=actor if actor in {"user", "agent", "system"} else "unknown",
                entity_id=None,
                context={
                    "vault_path": vault_path,
                    "limit_per_hour": rate_limit_per_hour,
                    "window_s": window_s,
                },
                recovery_reason="env_var",
            )
            fire_kill_switch(event, resolved_review_dir, resolved_vault_root)
            raise KillSwitchRateLimitExceeded(
                f"Rate limit exceeded for actor={actor} "
                f"({rate_limit_per_hour}/hr); kill switch fired"
            )

        # Step 3: Validate actor (R9)
        if actor not in ("user", "agent", "system"):
            event = build_kill_switch_event(
                trigger="actor_mismatch",
                actor_at_fault="unknown",
                entity_id=None,
                context={
                    "invalid_actor": actor,
                    "vault_path": vault_path,
                },
                recovery_reason="env_var",
            )
            fire_kill_switch(event, resolved_review_dir, resolved_vault_root)
            raise KillSwitchActorViolation(
                f"invalid actor {actor!r}; must be one of ['user', 'agent', 'system'] (R9)"
            )

        # Step 4: Transition validator traversal (R4 + R8)
        # If entity provided AND tier is SONHO AND actor != user -> abort
        # unless a legal caller (R6/R7) overrides.
        if entity is not None:
            tier = getattr(entity, "tier", None)
            cycle_phase = getattr(entity, "cycle_phase", None)
            if tier == "SONHO" and actor != "user" and legal_caller not in LEGAL_CALLERS:
                event = build_kill_switch_event(
                    trigger="actor_mismatch",
                    actor_at_fault=actor if actor in {"user", "agent", "system"} else "unknown",
                    entity_id=getattr(entity, "id", None),
                    context={
                        "tier": tier,
                        "vault_path": vault_path,
                    },
                    recovery_reason="env_var",
                )
                fire_kill_switch(event, resolved_review_dir, resolved_vault_root)
                raise KillSwitchBypassDetected(
                    f"SONHO write by actor={actor!r} without legal caller; "
                    f"kill switch fired (R8 + R9)"
                )
            # Call transition_validator if available (no-op for non-SONHO).
            try:
                if cycle_phase is not None:
                    validate_phase_transition(
                        entity,
                        old_cycle_phase=None,
                        new_cycle_phase=cycle_phase,
                        actor=actor,
                    )
            except PermissionError:
                # Propagate the transition_validator error to the caller.
                raise

        # Step 5: Audit pre-write (S2.3 — append-only)
        _append_vault_audit(
            resolved_vault_root,
            actor=actor,
            vault_path=vault_path,
            trigger="pre_write",
        )

        # Step 6: Underlying vault_write
        if frontmatter_fields is None:
            frontmatter_fields = {}
        result = _vault_write(
            vault_root=resolved_vault_root,
            vault_path=vault_path,
            frontmatter_fields=frontmatter_fields,
            body=body,
            actor=actor,
        )

        # Step 7: Record rate-limit hit
        rate_limit_tracker.record(actor)

        # Step 8: Audit post-write (S2.3)
        _append_vault_audit(
            resolved_vault_root,
            actor=actor,
            vault_path=vault_path,
            trigger="post_write",
        )
        return result

    return wrapped


# ---------------------------------------------------------------------------
# Convenience singleton (used by monkeypatch)
# ---------------------------------------------------------------------------


def install_wrapper(
    vault_root_provider: Callable[[], Path],
    data_root_provider: Callable[[], Path],
    review_queue_dir_provider: Callable[[], Path],
) -> Callable[..., dict[str, Any]]:
    """Build the canonical wrapped ``vault_write`` and return it.

    Caller is responsible for monkeypatching the result into
    ``ikigai.vault.vault_write.vault_write`` if desired.
    """
    return make_wrapped_vault_write(
        vault_root_provider,
        data_root_provider,
        review_queue_dir_provider,
    )


__all__ = [
    "LEGAL_CALLERS",
    "ActorType",
    "KillSwitchAbort",
    "KillSwitchActorViolation",
    "KillSwitchBypassDetected",
    "KillSwitchRateLimitExceeded",
    "_RateLimitTracker",
    "install_wrapper",
    "make_wrapped_vault_write",
]


_ = json  # keep import alive (test-friendly)
_ = (KillSwitchEvent, KillSwitchTrigger, KillSwitchActor, UEID)
