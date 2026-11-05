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

PROVIDER = "postgres"
"""Self-hosted Postgres, in the same compose as the api and the bot.

Was "supabase" — ratified by the owner on 2026-11-01 (SPEC-02 D10/R1) and
flipped by the renewed scope of 2026-11-02: the store is the owner's own
Postgres on the VPS. The provider is a deployment choice, not an
architectural one — the schema is plain Postgres, so only the DSN changes.
"""

EMBEDDING_DIM = 1536
"""Fixed vector dimension. An HNSW index is built for exactly one dimension."""

SCHEMA_VERSION = 1
"""Bumped when a migration changes the shape of the store."""

DOMAIN = "ikig"
"""The Postgres schema that holds the DOM."""

RLS_CLIENT_CLAIM = "request.jwt.claim.client_id"
"""The session setting the row-level security policies filter on.

It is the setting, not the bare claim name, because that is what a caller
needs: ``select set_config(RLS_CLIENT_CLAIM, <client_id>, true)`` puts the
calling client into the session, and the policies in ``0003_rls.sql`` compare
against it.

This constant is the single source of that name. The migration and the drift
test both derive from it — a copy of the string in either place would let
the policies and the service disagree about the same fact, and nothing would
notice until a write was refused.
"""

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
