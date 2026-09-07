"""Checkpoint TypedDicts + schema-control keys (ADR-027 R1, R2, R9).

This module owns the **data shapes** used by checkpoint.py and its
siblings (checkpoint_serialize.py). Pure-data module — no runtime
logic, no I/O, no third-party deps.

TypedDicts:
- ``SubgraphLink`` — one row in ``ikigai_subgraph_links`` (ADR-027 R1)
- ``VaultWriteRecord`` — per-write entry in ``vault_writes_log`` (ADR-027 R4)
- ``SchemaRegistryRow`` — one row in ``ikigai_schema_registry`` (ADR-027 R9)

Constants:
- ``SCHEMA_CONTROL_KEYS`` — 3 fields prepended to every checkpoint
  JSON payload per ADR-027 R2 (schema_version, thread_role, vault_writes_log).

Architectural reference:
- ADR-027 — R1 schema-control tables, R2 JSON payload, R9 versioning

Drift invariants enforced:
- test_canonical_scope :: test_serialize_preserves_every_ikigai_state_dict_field
  (TypedDict shape must match IKIGAiStateDict)

Companion modules:
- ``checkpoint_serialize`` — serialize_checkpoint + deserialize_checkpoint
- ``checkpoint_thread_id`` — build_thread_id + build_subagent_thread_id
- ``checkpoint`` — IkigaiCheckpointer class + constants + re-exports
"""

from __future__ import annotations

from typing import Literal, TypedDict

# ---------------------------------------------------------------------------
# TypedDicts — subgraph link, vault write record, schema registry row
# ---------------------------------------------------------------------------


class SubgraphLink(TypedDict, total=False):
    """One row in ``ikigai_subgraph_links`` (ADR-027 R1).

    Captures parent → child dispatch relationships so the dispatcher can
    reconstruct a cycle's fan-out without parsing the JSON checkpoint
    BLOB. Composite primary key is (parent_thread_id, parent_checkpoint_id,
    child_thread_id, child_checkpoint_id) — UPSERT semantics on duplicate.
    """

    parent_thread_id: str
    parent_checkpoint_id: str
    child_thread_id: str
    child_checkpoint_id: str
    created_at: str  # ISO 8601 UTC
    sub_agent_id: str  # 4-part UEID per ADR-014


class VaultWriteRecord(TypedDict, total=False):
    """Per-write entry in ``vault_writes_log`` (ADR-027 R4).

    Mirrors the canonical ``VaultWriteRecord`` from
    ``src/ikigai/src/ikigai/vault/vault_write.py``. Replicated here as
    a TypedDict to keep this module dependency-free (avoids import cycle
    with vault_write.py).
    """

    vault_path: str  # relative path within vault/
    actor: Literal["user", "agent", "system"]
    timestamp: str  # ISO 8601 UTC
    sha256: str  # sha256 of written body
    operation: Literal["create", "update", "delete"]


class SchemaRegistryRow(TypedDict, total=False):
    """One row in ``ikigai_schema_registry`` (ADR-027 R9)."""

    schema_version: int
    description: str
    applied_at: str  # ISO 8601 UTC


# ---------------------------------------------------------------------------
# Schema-control keys — prepended to every checkpoint JSON per ADR-027 R2
# ---------------------------------------------------------------------------


SCHEMA_CONTROL_KEYS: tuple[str, ...] = (
    "schema_version",
    "thread_role",
    "vault_writes_log",
)


__all__ = [
    "SCHEMA_CONTROL_KEYS",
    "SchemaRegistryRow",
    "SubgraphLink",
    "VaultWriteRecord",
]
