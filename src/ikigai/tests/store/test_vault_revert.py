"""The revert against the REAL store.

The service-level test proves the key construction with a fake that mirrors
the ledger. This one proves it against the Postgres the deployment runs,
because the answer that swallowed the revert is SQL: `insert ... on conflict
(key) do nothing` reports rowcount 0 and the repository answers `unchanged`
without writing. A fake only proves the fake.

The scenario is the one from the report: a file ingested as A, edited to B
and ingested, then edited back to A. The third ingestion must be an UPDATE —
and the two writes of A must be two different keys in the ledger, or the
third would be answered as a replay of the first.

It needs a database, and it says so when it skips: a skipped test that
reports itself is honest, and an invented result is not.
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
        # The container publishes on IPv4, and 'localhost' resolves to IPv6
        # FIRST — an address nothing listens on, which the driver waits out
        # for the whole OS connect timeout.
        dsn = dsn.replace("localhost", "127.0.0.1")
        dsn = with_connect_timeout(dsn)

        import psycopg

        from src.contracts.migrations.apply import BOOTSTRAP_SQL, apply_pending

        with psycopg.connect(dsn) as conn:
            conn.execute(BOOTSTRAP_SQL)
            apply_pending(conn)
        yield dsn


ALPHA = "# Revert\n\nalpha\n"
BETA = "# Revert\n\nbeta\n"


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@requires_store
async def test_a_reverted_file_reaches_the_row_against_the_real_store(
    store_dsn: str,
    tmp_path: Path,
) -> None:
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository
    from src.services.sync import VaultSource, VaultSync

    client = DataClient(store_dsn)
    repo = ArtifactRepository(client)
    try:
        root = tmp_path / "vault"
        relative = "nota/revert.md"
        _write(root, relative, ALPHA)
        sync = VaultSync(repo, sources=[VaultSource(root, "escrita")])  # type: ignore[arg-type]

        first = await sync.ingest()
        assert first.created == 1, f"the file did not reach the store: {first}"

        _write(root, relative, BETA)
        second = await sync.ingest()
        assert second.updated == 1, f"the edit did not reach the store: {second}"

        _write(root, relative, ALPHA)
        third = await sync.ingest()

        assert third.updated == 1, (
            "the revert was swallowed as a replay of the first write — the store "
            "keeps the edit while the file says the original"
        )
        assert third.unchanged == 0

        rows = await client.execute("select revision, body, body_hash from ikig.artifacts")
        assert len(rows) == 1, f"expected one artifact row, found {len(rows)}"
        row = rows[0]
        assert row["body"] == ALPHA
        assert row["body_hash"] == hashlib.sha256(ALPHA.encode("utf-8")).hexdigest()
        assert row["revision"] == 3, "three writes, three revisions"

        # The two writes of the SAME content are two different keys in the
        # ledger — the revision is the only thing that tells them apart.
        alpha_hash = hashlib.sha256(ALPHA.encode("utf-8")).hexdigest()[:16]
        prefix = f"vault:escrita:{relative}:{alpha_hash}"
        key_rows = await client.execute("select key from ikig.idempotency_keys")
        keys = sorted(str(key_row["key"]) for key_row in key_rows)
        alpha_keys = [key for key in keys if key.startswith(prefix)]
        assert alpha_keys == [f"{prefix}:0", f"{prefix}:2"], (
            "the same content written twice produced keys the ledger cannot tell apart: "
            f"{alpha_keys}"
        )
        assert len(keys) == 3, f"three writes, three keys: {keys}"
    finally:
        await client.close()
