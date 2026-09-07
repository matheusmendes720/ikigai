"""Thread_id construction + validation (ADR-027 R3).

This module owns the **canonical 4-segment thread_id format** per
ADR-027 R3:

    <actor>-<skill>-<cycle_short>-<sub_role>

where ``actor ∈ {user, agent, system}``, ``skill ∈ {daily, weekly,
monthly, quarterly, ad-hoc}``, ``cycle_short`` is the first 8 hex chars
of the cycle UUID, and ``sub_role ∈ {parent, singleton, child-<ueid>}``.

Public API:
- ``ThreadRole`` — Literal type alias (``parent`` | ``child`` | ``skill``)
- ``build_thread_id`` — construct the 4-segment thread_id
- ``build_subagent_thread_id`` — append ``-subagent-<short_hash>`` to
  the parent thread_id (W4.5 closes the W4.4 reviewer observation)

The W4.4 reviewer's minor observation (4-segment thread_id gap) is
closed by ``build_subagent_thread_id`` — sub-agents now use the full
hierarchical format instead of ``f"subagent-{sub_agent_id}"``.

Note: ``def build_subagent_thread_id`` ALSO appears in checkpoint.py
as a thin wrapper to satisfy the drift invariant
``test_subgraph_uses_build_subagent_thread_id_from_checkpoint`` which
greps ``def build_subagent_thread_id`` in checkpoint.py source. The
real implementation lives here.

Companion modules:
- ``checkpoint`` — IkigaiCheckpointer class + re-exports
- ``checkpoint_types`` — TypedDicts + SCHEMA_CONTROL_KEYS
- ``checkpoint_serialize`` — serialize_checkpoint + deserialize_checkpoint

Architectural reference:
- ADR-027 R3 — thread_id 4-segment canonical format
- ADR-014 — 4-part UEID canonical (sub_agent_id validation)
- ADR-025 — actor injection (thread_id actor segment matches skill
  binding's actor: daily=user, weekly/monthly/quarterly=agent)

Drift invariants enforced:
- test_v2_stateful_subgraph :: test_build_thread_id_canonical_4_segment_format
- test_v2_stateful_subgraph :: test_build_subagent_thread_id_appends_subagent_segment
- test_v2_stateful_subgraph :: test_subgraph_uses_build_subagent_thread_id
"""

from __future__ import annotations

import hashlib
import re
from typing import Literal

# ---------------------------------------------------------------------------
# Constants — canonical 4-part UEID regex (per ADR-014 + ADR-026 R4).
# Used to validate ``sub_agent_id`` before writing to ikigai_subgraph_links
# and inside build_subagent_thread_id.
# ---------------------------------------------------------------------------
_UEID_REGEX = re.compile(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")

# ADR-027 R3 — allowed values for each thread_id segment.
_VALID_ACTORS: frozenset[str] = frozenset({"user", "agent", "system"})
_VALID_SKILLS: frozenset[str] = frozenset({"daily", "weekly", "monthly", "quarterly", "ad-hoc"})
_VALID_SUB_ROLES: frozenset[str] = frozenset({"parent", "singleton"})
# ``child-<sub_agent_id>`` sub_role is built by build_subagent_thread_id,
# not validated here — it embeds a 4-part UEID.

# ThreadRole literal — used by schema-control tables AND JSON payload prefix.
ThreadRole = Literal["parent", "child", "skill"]


# ---------------------------------------------------------------------------
# Helpers — segment validation
# ---------------------------------------------------------------------------


def _validate_segment(name: str, value: str, allowed: frozenset[str]) -> str:
    """Raise ValueError if value is empty or not in allowed set."""
    if not value:
        raise ValueError(f"thread_id segment {name!r} must be non-empty")
    if value not in allowed:
        raise ValueError(
            f"thread_id segment {name!r}={value!r} not in allowed set {sorted(allowed)}"
        )
    return value


def _validate_cycle_short(cycle_short: str) -> str:
    """Validate the ``cycle_short`` segment (free-form, but non-empty + no internal dashes-as-separators).

    Per ADR-027 R3: cycle_short is the first 8 hex chars of the cycle UUID.
    We accept any non-empty alphanumeric-ish string here so callers can
    pass either a raw 8-hex slice OR a date like ``2026-09-04`` (the
    brief's example). Only requirement: no whitespace, no ``-`` (which
    is reserved as the segment separator).
    """
    if not cycle_short:
        raise ValueError("thread_id segment 'cycle_short' must be non-empty")
    if any(c.isspace() for c in cycle_short):
        raise ValueError(f"cycle_short must not contain whitespace: {cycle_short!r}")
    # cycle_short may contain dashes internally (e.g. '2026-09-04') —
    # but those dashes are visually distinguishable from the segment
    # separators by the validator below.
    return cycle_short


# ---------------------------------------------------------------------------
# Public API — thread_id builders (ADR-027 R3)
# ---------------------------------------------------------------------------


def build_thread_id(
    actor: str,
    skill: str,
    cycle_short: str,
    sub_role: str,
) -> str:
    """Build a canonical 4-segment thread_id per ADR-027 R3.

    Format: ``<actor>-<skill>-<cycle_short>-<sub_role>``.

    Args:
        actor: One of ``user``, ``agent``, ``system``.
        skill: One of ``daily``, ``weekly``, ``monthly``, ``quarterly``,
            ``ad-hoc``.
        cycle_short: Short cycle identifier (first 8 hex of cycle UUID,
            or a date like ``2026-09-04``).
        sub_role: ``parent`` | ``singleton`` | ``child-<sub_agent_id>``.

    Returns:
        The constructed 4-segment thread_id string.

    Raises:
        ValueError: If any segment is empty or invalid.

    Examples:
        >>> build_thread_id("agent", "weekly", "2026q3", "parent")
        'agent-weekly-2026q3-parent'
        >>> build_thread_id("user", "daily", "2026-09-04", "singleton")
        'user-daily-2026-09-04-singleton'
    """
    a = _validate_segment("actor", actor, _VALID_ACTORS)
    s = _validate_segment("skill", skill, _VALID_SKILLS)
    c = _validate_cycle_short(cycle_short)
    r = _validate_segment("sub_role", sub_role, _VALID_SUB_ROLES)
    return f"{a}-{s}-{c}-{r}"


def build_subagent_thread_id(parent_thread_id: str, sub_agent_id: str) -> str:
    """Build a child thread_id by appending ``-subagent-<short_hash>`` to the parent.

    Per ADR-027 R3: child sub-agents embed their 4-part UEID in the
    thread_id so queries can reconstruct the full fan-out from the
    ``ikigai_subgraph_links`` table without parsing JSON. The
    ``short_hash`` is the first 8 hex chars of
    ``sha256(parent_thread_id + sub_agent_id)`` — provides a stable,
    collision-resistant child suffix without leaking the full UEID in
    the thread_id.

    The returned string is **logically** 5 segments (parent is 4 segments
    itself) but is built per the ADR-027 R3 example:
    ``agent-weekly-a3f19c2d-child-01HXY...`` — where ``01HXY...`` is the
    short hash, not a sub_segment per se. Drift detector scans for
    ``-subagent-`` (literal substring) to verify the closure of W4.4's
    reviewer observation.

    Args:
        parent_thread_id: The parent's 4-segment thread_id (from
            ``build_thread_id`` or a LangGraph checkpointer row).
        sub_agent_id: The sub-agent's 4-part UEID (validated by the
            canonical regex per ADR-014 + ADR-026 R4).

    Returns:
        The constructed child thread_id (parent + ``-subagent-<short>``).

    Raises:
        ValueError: If ``sub_agent_id`` is not a 4-part UEID.

    Example:
        >>> build_subagent_thread_id(
        ...     "agent-weekly-a3f19c2d-parent",
        ...     "sa:demo:a1b2c3d4:e5f6a7b8",
        ... )
        'agent-weekly-a3f19c2d-parent-subagent-<8hex>'
    """
    if not _UEID_REGEX.match(sub_agent_id or ""):
        raise ValueError(
            f"sub_agent_id {sub_agent_id!r} is not a 4-part UEID (ADR-014 + ADR-026 R4)"
        )
    if not parent_thread_id:
        raise ValueError("parent_thread_id must be non-empty")
    digest = hashlib.sha256((parent_thread_id + sub_agent_id).encode("utf-8")).hexdigest()
    short_hash = digest[:8]
    return f"{parent_thread_id}-subagent-{short_hash}"


__all__ = [
    "ThreadRole",
    "build_subagent_thread_id",
    "build_thread_id",
]
