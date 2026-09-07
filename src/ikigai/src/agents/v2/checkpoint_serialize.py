"""Checkpoint JSON serialization (ADR-027 R2).

This module owns the **pure JSON marshaling** layer for checkpoint
BLOBs. ``serialize_checkpoint`` prepends the 3 schema-control fields
(``SCHEMA_CONTROL_KEYS``) to the user state; ``deserialize_checkpoint``
is its inverse. No computation, no I/O — pure persistence per
ADR-013 planner-only.

Companion modules:
- ``checkpoint_types`` — TypedDicts (SubgraphLink / VaultWriteRecord /
  SchemaRegistryRow) + SCHEMA_CONTROL_KEYS
- ``checkpoint_thread_id`` — build_thread_id + build_subagent_thread_id
- ``checkpoint`` — IkigaiCheckpointer class + constants + re-exports

Architectural reference:
- ADR-027 R2 — JSON payload format (3 schema-control prefixes)
- ADR-027 R9 — lazy migration via schema_version inspection
- ADR-013 — planner-only; serialize is pure persistence

Drift invariants enforced:
- test_v2_stateful_subgraph :: test_serialize_deserialize_round_trip
- test_v2_stateful_subgraph :: test_serialize_with_vault_writes_log
- test_v2_stateful_subgraph :: test_serialize_preserves_every_ikigai_state_dict_field
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .checkpoint_types import SCHEMA_CONTROL_KEYS, VaultWriteRecord

if TYPE_CHECKING:
    # ThreadRole is a Literal kept in checkpoint_thread_id to colocate with
    # the thread_id builders; imported only for type-checker visibility.
    from .checkpoint_thread_id import ThreadRole

# ---------------------------------------------------------------------------
# Constants — schema version (canonical location: checkpoint.py)
# ---------------------------------------------------------------------------
# Imported lazily from checkpoint.py to avoid a circular import at module
# load (checkpoint.py imports from this module for serialize_checkpoint
# re-export). The default value 1 matches checkpoint._SCHEMA_VERSION; if
# that ever changes, update the re-export below.
_DEFAULT_SCHEMA_VERSION: int = 1


def serialize_checkpoint(
    state: dict[str, Any],
    *,
    thread_role: ThreadRole = "parent",
    vault_writes_log: list[VaultWriteRecord] | None = None,
    schema_version: int | None = None,
) -> bytes:
    """Serialize an IKIGAiStateDict into a checkpoint BLOB (UTF-8 JSON).

    Per ADR-027 R2: the JSON payload contains 3 schema-control prefixes
    (schema_version, thread_role, vault_writes_log) prepended to the
    state dict, then JSON-serialized as UTF-8 bytes for SqliteSaver.

    No computation occurs here — this is pure persistence per ADR-013
    planner-only.

    Args:
        state: The IKIGAiStateDict (or partial dict) to serialize.
        thread_role: One of ``parent`` | ``child`` | ``skill``.
        vault_writes_log: Append-only list of vault writes from this cycle.
        schema_version: Override the schema version (defaults to 1;
            canonical constant lives in checkpoint._SCHEMA_VERSION).

    Returns:
        UTF-8 encoded JSON bytes ready for SqliteSaver BLOB storage.
    """
    payload: dict[str, Any] = dict(state)  # defensive copy
    payload["schema_version"] = (
        schema_version if schema_version is not None else _DEFAULT_SCHEMA_VERSION
    )
    payload["thread_role"] = thread_role
    payload["vault_writes_log"] = list(vault_writes_log or [])
    return json.dumps(payload, default=str, ensure_ascii=False).encode("utf-8")


def deserialize_checkpoint(blob: bytes) -> dict[str, Any]:
    """Deserialize a checkpoint BLOB back into a state dict (ADR-027 R2).

    Inverse of ``serialize_checkpoint``. The 3 schema-control fields are
    returned alongside the user-state fields; callers can filter them
    out if desired (they are also reachable by key).

    Lazy migration per ADR-027 R9: callers can inspect
    ``payload["schema_version"]`` and apply migration functions from
    ``checkpoint_migrations.py`` if the version is older than
    ``_SCHEMA_VERSION``. This function does NOT mutate the payload —
    pure read.

    Args:
        blob: UTF-8 JSON bytes from a SqliteSaver row.

    Returns:
        Reconstructed state dict (including schema-control fields).
    """
    return json.loads(blob.decode("utf-8"))


__all__ = [
    "SCHEMA_CONTROL_KEYS",
    "deserialize_checkpoint",
    "serialize_checkpoint",
]
