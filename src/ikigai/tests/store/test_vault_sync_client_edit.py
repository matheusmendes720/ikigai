"""The provenance guard against the REAL store — the W47 regression.

A client corrects a review in the store; the vault file keeps the old bytes;
the next ingestion must NOT overwrite the correction. Provenance is read from
`ikig.artifact_revisions` (the writer of each revision), because the artifacts
row's client_id is the creator's and is never rewritten on update.

Needs a database, and says so when it skips. The service-level counterpart is
`tests/services/test_vault_sync_provenance.py`.
"""

from __future__ import annotations

import hashlib
import importlib.util
import shutil
from pathlib import Path

import pytest

requires_store = pytest.mark.skipif(
    not (
        importlib.util.find_spec("psycopg") is not None
        and importlib.util.find_spec("testcontainers") is not None
        and shutil.which("docker") is not None
    ),
    reason="needs psycopg, testcontainers and Docker to reach a real Postgres",
)


@pytest.fixture(scope="module")
def store_dsn() -> str:
    from testcontainers.postgres import PostgresContainer

    from src.data.client import with_connect_timeout

    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        dsn = postgres.get_connection_url().replace("postgresql+psycopg2://", "postgresql://")
        dsn = dsn.replace("localhost", "127.0.0.1")
        dsn = with_connect_timeout(dsn)

        import psycopg

        from src.contracts.migrations.apply import BOOTSTRAP_SQL, apply_pending

        with psycopg.connect(dsn) as conn:
            conn.execute(BOOTSTRAP_SQL)
            apply_pending(conn)
        yield dsn


ALPHA = "# Revisão W47\n\n14 à sexta, 19 no fim da semana.\n"
BETA = "# Revisão W47\n\n11 à sexta (contagem corrigida pelo owner).\n"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@requires_store
async def test_vault_sync_does_not_overwrite_a_client_edit(store_dsn: str, tmp_path: Path) -> None:
    from src.contracts.dom import WriteRequest
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository
    from src.services.sync import VaultSource, VaultSync

    client = DataClient(store_dsn)
    repo = ArtifactRepository(client)
    try:
        root = tmp_path / "vault"
        relative = "revisao/2026-w47.md"
        path = root / relative
        path.parent.mkdir(parents=True)
        path.write_text(ALPHA, encoding="utf-8")
        sync = VaultSync(repo, sources=[VaultSource(root, "escrita")])  # type: ignore[arg-type]

        first = await sync.ingest()
        assert first.created == 1, f"the file did not reach the store: {first}"
        rows = await client.execute("select uid from ikig.artifacts")
        uid = rows[0]["uid"]

        stored = await repo.require(uid)
        corrected = stored.model_copy(update={"body": BETA, "body_hash": _hash(BETA)})
        outcome = await repo.upsert(
            WriteRequest(
                artifact=corrected,
                expected_revision=stored.revision,
                idempotency_key="client-fix-1",
                client_id="telegram-bot",
            )
        )
        assert outcome.outcome == "updated"

        second = await sync.ingest()

        row = (await client.execute("select revision, body, body_hash from ikig.artifacts"))[0]
        assert row["body"] == BETA, "the vault clobbered the client's correction"
        assert row["body_hash"] == _hash(BETA)
        assert row["revision"] == 2, "the guard must not advance the revision"
        assert second.updated == 0
        assert any(relative in entry for entry in second.skipped)
    finally:
        await client.close()
