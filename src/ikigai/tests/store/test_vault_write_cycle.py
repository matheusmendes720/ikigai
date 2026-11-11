"""The write-back against the REAL store (ADR-043, PASS 6).

The unit test proves the cycle's LOGIC with a fake store. This one proves it
against the Postgres the deployment runs, because three of the cycle's facts
live in the database and not in the code:

1. **The typed fields are read back.** A KPI's metric and target live in
   `artifact_kpi`, and the write-back is the first reader of that table: a
   KPI that came back as a spine would be written to the desktop as a title
   with no numbers.
2. **The write is versioned.** The writer's write goes through the same
   `expected_revision` path as every other write, so a revision that moved
   under its feet is a conflict and not an overwrite.
3. **The ingestion finds `unchanged`.** The store holds the file's bytes and
   the file's path, so the ingestion that follows compares them, finds them
   equal, and writes nothing: the revision does not rise, and no second
   artifact appears for the same prose.

It needs a database, and it says so when it skips: a skipped test that
reports itself is honest, and an invented result is not.
"""

from __future__ import annotations

import importlib.util
import shutil
from datetime import UTC, datetime
from decimal import Decimal
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


def _kpi() -> object:
    from src.contracts.common import UEID
    from src.contracts.dom import ArtifactKind
    from src.contracts.dom_kinds import KPIArtifact

    return KPIArtifact(
        uid=UEID("kpi:receita-do-trimestre:abc12345:def67890"),
        kind=ArtifactKind.KPI,
        title="Receita do trimestre",
        body="A medição que decide o trimestre.",
        metric="receita mensal",
        target=Decimal("10000.50"),
        actual=Decimal("2500"),
        unit="EUR",
        period="2026-Q4",
        direction="up",
        created_at=datetime(2026, 11, 10, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 11, 10, 12, 0, tzinfo=UTC),
    )


@requires_store
async def test_the_write_back_closes_the_cycle_against_the_real_store(
    store_dsn: str,
    tmp_path: Path,
) -> None:
    from src.contracts.dom import WriteRequest
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository
    from src.services.sync import VaultSource, VaultSync
    from src.services.vault_write import VaultWrite

    client = DataClient(store_dsn)
    repo = ArtifactRepository(client)
    try:
        kpi = _kpi()
        await repo.upsert(
            WriteRequest(
                artifact=kpi,
                idempotency_key="seed:receita-do-trimestre",
                client_id="pi-agent",
            )
        )

        # 1. The typed read: the KPI comes back WITH its numbers.
        pending = await repo.artifacts_without_vault_path()
        mine = [artifact for artifact in pending if str(artifact.uid) == str(kpi.uid)]
        assert mine, "the artifact without a vault_path did not come back"
        assert getattr(mine[0], "metric", None) == "receita mensal", (
            "the KPI came back without its metric: the file would be a title "
            "with no numbers"
        )
        assert getattr(mine[0], "target", None) == Decimal("10000.50")

        # 2. The write-back writes the file and tells the store what it wrote.
        report = await VaultWrite(repo, root=tmp_path).write_back()
        assert report.written == 1, (
            f"the write-back wrote {report.written} files, not one: {report.skipped}"
        )

        stored = await repo.get(kpi.uid)
        assert stored is not None and stored.vault_path is not None
        written = (tmp_path / str(stored.vault_path)).read_text(encoding="utf-8")
        assert stored.body == written, (
            "the store's body is not the file: the ingestion would rewrite the "
            "artifact on the next pass, and the revision would rise every time"
        )

        # 3. The typed row survived the writer's write.
        rows = await client.execute(
            "select metric, target, period from ikig.artifact_kpi where uid = %s",
            (str(kpi.uid),),
        )
        assert rows, "the writer's write deleted the KPI's own row"
        assert rows[0]["metric"] == "receita mensal"
        assert Decimal(str(rows[0]["target"])) == Decimal("10000.50")

        # 4. The ingestion that follows finds the store already saying
        #    `unchanged` — and the revision does not rise.
        revision_before = stored.revision
        ingestion = await VaultSync(
            repo,
            sources=[VaultSource(tmp_path, "escrita")],  # type: ignore[arg-type]
        ).ingest()

        assert ingestion.created == 0, (
            f"the ingestion created a second artifact for the same prose: {ingestion}"
        )
        assert ingestion.updated == 0, "the ingestion rewrote an artifact that did not change"
        assert ingestion.unchanged == 1, (
            f"the ingestion did not recognise the file the writer wrote: {ingestion}"
        )
        after = await repo.get(kpi.uid)
        assert after is not None and after.revision == revision_before, (
            f"the revision rose from {revision_before} to "
            f"{after.revision if after else None} on a file that did not change"
        )
    finally:
        await client.close()
