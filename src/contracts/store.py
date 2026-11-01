"""The store's constants — the single source for provider, dimension and wiring.

The provider is a deployment choice, not an architectural one: the schema is
plain Postgres, so replacing Supabase changes connection settings and nothing
else. The embedding dimension is the opposite — an HNSW index is built for one
dimension, so changing it later means a new column, a backfill and an index
swap rather than a config edit.
"""

from __future__ import annotations

from .dom import ArtifactKind

__all__ = [
    "DOMAIN",
    "EMBEDDING_DIM",
    "KIND_TABLES",
    "PROVIDER",
    "RLS_CLIENT_CLAIM",
    "SCHEMA_VERSION",
    "STORE_DSN_ENV",
]

PROVIDER = "supabase"
"""Ratified by the owner on 2026-11-01 (SPEC-02 D10/R1)."""

EMBEDDING_DIM = 1536
"""Fixed vector dimension. An HNSW index is built for exactly one dimension."""

SCHEMA_VERSION = 1
"""Bumped when a migration changes the shape of the store."""

DOMAIN = "ikig"
"""The Postgres schema that holds the DOM."""

RLS_CLIENT_CLAIM = "client_id"
"""The JWT claim the row-level security policies filter on."""

STORE_DSN_ENV = "IKIGAI_STORE_DSN"
"""The environment variable holding the connection string. Never a file."""

KIND_TABLES: dict[ArtifactKind, str | None] = {
    ArtifactKind.SONHO: "artifact_sonho",
    ArtifactKind.PLANO: "artifact_plano",
    ArtifactKind.ONDA: None,
    ArtifactKind.FASE: None,
    ArtifactKind.REVISAO: None,
    ArtifactKind.NOTA: None,
    ArtifactKind.KPI: "artifact_kpi",
    ArtifactKind.OKR: "artifact_okr",
    ArtifactKind.DESC: "artifact_decs",
    ArtifactKind.TAREFA: "artifact_tarefa",
}
"""Which kinds have an extension table of their own. Kinds without extra typed
fields live entirely in the `artifacts` spine.

The map is the contract between the Pydantic kinds and the SQL schema: a kind
with typed fields of its own must have a table here, and a kind with a table
here must have typed fields. The drift test holds both ends to that.
"""
