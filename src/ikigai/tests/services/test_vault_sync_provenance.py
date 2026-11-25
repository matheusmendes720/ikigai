"""The provenance guard: an unchanged vault must not clobber a client edit.

The W47 regression: the owner corrected a review in the store via a client
write, the vault file kept the old bytes, and the next ingestion overwrote the
correction with the stale prose. The guard reads provenance from the revision
log (the writer of each revision), not the row's client_id (the creator's).

Service-level, against the in-memory double. The real-Postgres counterpart is
`tests/store/test_vault_sync_client_edit.py`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from src.contracts.dom import WriteRequest
from src.ikigai.tests.services.test_artifacts_service import FakeRepository
from src.services.sync import VaultSource, VaultSync


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _vault(tmp_path: Path) -> tuple[Path, Path]:
    vault = tmp_path / "closing-2026"
    directory = vault / "02-q4-2026" / "03-revisões-semanais"
    directory.mkdir(parents=True)
    return vault, directory / "2026-w47.md"


ALPHA = "# Revisão W47\n\n14 à sexta, 19 no fim da semana.\n"
BETA = "# Revisão W47\n\n11 à sexta (contagem corrigida pelo owner).\n"
GAMMA = "# Revisão W47\n\nversão nova escrita no vault.\n"


async def test_unchanged_vault_does_not_clobber_a_client_edit(tmp_path: Path) -> None:
    vault, note = _vault(tmp_path)
    note.write_text(ALPHA, encoding="utf-8")
    repo = FakeRepository()
    sync = VaultSync(repo, sources=[VaultSource(vault, "closing")])  # type: ignore[arg-type]

    first = await sync.ingest()
    assert first.created == 1
    uid = next(iter(repo.artifacts))
    stored = repo.artifacts[uid]

    corrected = stored.model_copy(update={"body": BETA, "body_hash": _hash(BETA)})
    await repo.upsert(
        WriteRequest(
            artifact=corrected,
            expected_revision=stored.revision,
            idempotency_key="client-fix-1",
            client_id="telegram-bot",
        )
    )
    assert repo.artifacts[uid].body == BETA

    second = await sync.ingest()

    assert repo.artifacts[uid].body == BETA, "the vault clobbered the client's correction"
    assert second.updated == 0
    assert any("2026-w47.md" in entry for entry in second.skipped)


async def test_a_vault_edit_after_a_client_edit_still_wins(tmp_path: Path) -> None:
    vault, note = _vault(tmp_path)
    note.write_text(ALPHA, encoding="utf-8")
    repo = FakeRepository()
    sync = VaultSync(repo, sources=[VaultSource(vault, "closing")])  # type: ignore[arg-type]
    await sync.ingest()
    uid = next(iter(repo.artifacts))
    stored = repo.artifacts[uid]
    corrected = stored.model_copy(update={"body": BETA, "body_hash": _hash(BETA)})
    await repo.upsert(
        WriteRequest(
            artifact=corrected,
            expected_revision=stored.revision,
            idempotency_key="client-fix-1",
            client_id="telegram-bot",
        )
    )

    note.write_text(GAMMA, encoding="utf-8")
    third = await sync.ingest()

    assert third.updated == 1, "a genuine vault edit must reach the store"
    assert repo.artifacts[uid].body == GAMMA


async def test_a_file_reverted_to_earlier_content_still_updates(tmp_path: Path) -> None:
    vault, note = _vault(tmp_path)
    repo = FakeRepository()
    sync = VaultSync(repo, sources=[VaultSource(vault, "closing")])  # type: ignore[arg-type]

    note.write_text(ALPHA, encoding="utf-8")
    assert (await sync.ingest()).created == 1
    note.write_text(BETA, encoding="utf-8")
    assert (await sync.ingest()).updated == 1
    note.write_text(ALPHA, encoding="utf-8")
    third = await sync.ingest()

    assert third.updated == 1, "the revert was swallowed as a replay"
    uid = next(iter(repo.artifacts))
    assert repo.artifacts[uid].body == ALPHA
    assert repo.artifacts[uid].revision == 3
