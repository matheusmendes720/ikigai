"""The drafts: prose a client is writing, which has not been committed yet.

A draft is the STATE of a client that has not finished thinking, and there are
three things these tests hold:

1. **It is not an artifact.** No UEID, no place in the full-text index, no
   place in the vector index, no line in the change feed. A half-written
   sentence that shows up in a search result is prose that pushes the finished
   prose down the ranking of every query that shares a word with it.
2. **It obeys the same write contract as an artifact.** A revision, an
   idempotency key, and a stale revision is a conflict — never a silent
   overwrite.
3. **It is scoped to a client.** Two devices composing at once are two drafts,
   and neither can read the other's.

The last one is the reason a draft is stored at all: a draft that dies with
the socket is prose the owner has to write twice, and a draft that leaks
between devices is not a draft, it is a shared document.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from src.contracts.dom import ArtifactKind
from src.contracts.drafts import Draft, DraftOutcome, DraftSaveRequest
from src.contracts.errors import ConflictError, NotFoundError
from src.data.drafts import DraftRepository
from src.services.drafts import DraftService

MIGRATIONS = Path(__file__).resolve().parents[3] / "contracts" / "migrations"

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _draft(client_id: str = "owner", draft_id: str = "nota-1", **overrides: Any) -> Draft:
    payload: dict[str, Any] = {
        "client_id": client_id,
        "draft_id": draft_id,
        "kind": ArtifactKind.NOTA,
        "title": "Uma nota",
        "body": "primeiro paragrafo",
        "created_at": NOW,
        "updated_at": NOW,
    }
    payload.update(overrides)
    return Draft.model_validate(payload)


class _Column:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeCursor:
    """What a real cursor gives back: a rowcount, and a description of columns."""

    def __init__(self, rowcount: int = 1, rows: list[dict[str, Any]] | None = None) -> None:
        self.rowcount = rowcount
        self._rows = rows or []
        self.description = [_Column(name) for name in (self._rows[0] if self._rows else {})] or None

    async def fetchall(self) -> list[Any]:
        return list(self._rows)


class FakeConnection:
    """The transaction's connection.

    `write_rowcount` is the answer to the only statement that decides anything
    here: "is the revision still the one I read?". There is no ledger to fake —
    a draft has no idempotency key, and the revision guard is the whole guard.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.write_rowcount = 1
        self.rows: list[dict[str, Any]] = []

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> FakeCursor:
        self.calls.append((sql, tuple(params)))
        return FakeCursor(self.write_rowcount, rows=self.rows)


class FakeClient:
    """A client whose `execute` returns ROWS, as `DataClient.execute` does."""

    def __init__(self) -> None:
        self.conn = FakeConnection()
        self.rows: list[dict[str, Any]] = []

    def transaction(self) -> Any:
        client = self

        class _Transaction:
            async def __aenter__(self) -> FakeConnection:
                client.conn.rows = client.rows
                return client.conn

            async def __aexit__(self, *exc: Any) -> None:
                return None

        return _Transaction()

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        self.conn.calls.append((sql, tuple(params)))
        return list(self.rows)

    async def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        self.conn.calls.append((sql, tuple(params)))
        return self.rows[0] if self.rows else None


def _repo() -> tuple[DraftRepository, FakeClient]:
    client = FakeClient()
    return DraftRepository(client), client  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1. The write contract
# ---------------------------------------------------------------------------
async def test_a_save_carries_the_guard_and_no_idempotency_key() -> None:
    """The same envelope an artifact write carries — minus the key it cannot honour.

    A key built from the content and the second makes two saves of the same
    text inside one second the same save, and for a CREATE it cannot work at
    all: the caller does not know whether the draft exists, which is what the
    conflict is for. The revision guard is the de-duplication, and it is
    already here.
    """
    fields = DraftSaveRequest.model_fields
    for required in ("draft", "client_id"):
        assert fields[required].is_required(), f"DraftSaveRequest.{required} must be required"
    assert "expected_revision" in fields, "a draft save without it cannot be guarded"
    assert "idempotency_key" not in fields, (
        "a draft has no idempotency key: the revision guard already de-duplicates a retry"
    )


async def test_a_save_over_a_stale_revision_is_a_conflict() -> None:
    """Never a silent overwrite: one device's paragraph must not eat another's.

    This is also what a retry after a dropped socket gets: the first save
    advanced the revision, so the retry arrives stale and is refused — which
    is the correct answer, and the one the client rereads from.
    """
    repo, client = _repo()
    client.conn.write_rowcount = 0

    with pytest.raises(ConflictError) as raised:
        await repo.save(
            DraftSaveRequest(
                draft=_draft(),
                expected_revision=3,
                client_id="owner",
            )
        )

    # The detail is a field of the error, not part of its message.
    assert "changed by someone else" in str(raised.value)
    assert "stale" in (raised.value.detail or "")


async def test_a_create_over_a_taken_id_is_a_conflict() -> None:
    repo, client = _repo()
    client.conn.write_rowcount = 0

    with pytest.raises(ConflictError) as raised:
        await repo.save(DraftSaveRequest(draft=_draft(), client_id="owner"))

    assert "already exists" in str(raised.value)
    assert "expected_revision" in (raised.value.detail or "")


async def test_the_save_guard_is_on_the_revision_and_the_client() -> None:
    """The WHERE names both halves of the key — a guard on one is no guard."""
    repo, client = _repo()
    client.conn.write_rowcount = 1

    await repo.save(DraftSaveRequest(draft=_draft(), expected_revision=1, client_id="owner"))

    sql, params = next(
        (sql, params) for sql, params in client.conn.calls if sql.startswith("update ikig.drafts")
    )
    assert "client_id=%s and draft_id=%s and revision=%s" in sql
    assert params[-3:] == ("owner", "nota-1", 1)


# ---------------------------------------------------------------------------
# 2. It is scoped to a client
# ---------------------------------------------------------------------------
async def test_the_list_is_scoped_to_one_client() -> None:
    repo, client = _repo()

    await repo.list("owner")

    sql, params = client.conn.calls[-1]
    assert "where client_id = %s" in sql
    assert params[0] == "owner"


async def test_a_read_is_scoped_to_one_client() -> None:
    repo, client = _repo()

    await repo.get("outra-maquina", "nota-1")

    sql, params = client.conn.calls[-1]
    assert "client_id = %s and draft_id = %s" in sql
    assert params == ("outra-maquina", "nota-1")


async def test_a_discard_carries_the_guard_when_the_caller_sends_one() -> None:
    repo, client = _repo()
    client.conn.write_rowcount = 1

    await repo.discard("owner", "nota-1", expected_revision=2)

    sql, params = client.conn.calls[-1]
    assert "revision = %s" in sql
    assert params[-1] == 2


async def test_a_discard_of_something_absent_is_a_not_found() -> None:
    repo, client = _repo()
    client.conn.write_rowcount = 0
    client.rows = []

    with pytest.raises(NotFoundError):
        await repo.discard("owner", "nao-existe")


async def test_a_draft_has_no_uid() -> None:
    """It is not in the DOM, so it has no identity in the DOM."""
    assert "uid" not in Draft.model_fields


# ---------------------------------------------------------------------------
# 3. The service stamps the clock, and only the clock
# ---------------------------------------------------------------------------
async def test_the_service_stamps_both_dates_on_the_first_save() -> None:
    saved: list[DraftSaveRequest] = []

    class Capturing:
        async def save(self, request: DraftSaveRequest) -> DraftOutcome:
            saved.append(request)
            return DraftOutcome(
                client_id=request.client_id,
                draft_id=request.draft.draft_id,
                revision=1,
                outcome="created",
            )

    service = DraftService(Capturing())  # type: ignore[arg-type]
    await service.save(_draft(created_at=NOW, updated_at=NOW))

    stamped = saved[0].draft
    assert stamped.created_at > NOW, "the first save stamps the clock"
    assert stamped.updated_at > NOW


async def test_a_second_save_keeps_the_moment_the_draft_started() -> None:
    """`created_at` is when the draft started, and re-stamping it loses that."""
    saved: list[DraftSaveRequest] = []

    class Capturing:
        async def save(self, request: DraftSaveRequest) -> DraftOutcome:
            saved.append(request)
            return DraftOutcome(
                client_id=request.client_id,
                draft_id=request.draft.draft_id,
                revision=2,
                outcome="updated",
            )

    service = DraftService(Capturing())  # type: ignore[arg-type]
    await service.save(
        _draft(created_at=NOW, updated_at=NOW),
        expected_revision=1,
    )

    assert saved[0].draft.created_at == NOW, "the draft is still the same draft"
    assert saved[0].draft.updated_at > NOW, "but it was just touched"
    assert saved[0].draft.revision == 1


async def test_the_service_does_not_commit() -> None:
    """Committing is `ArtifactService.upsert`, with its own envelope.

    A service that committed on the client's behalf would be a second writer of
    the DOM wearing the draft's name — so the draft layer must not reach the
    artifact service at all.

    The guard reads the CODE and not the prose: this module's own docstrings
    name `ArtifactService` precisely to say it is NOT used, and a test that
    greps the comments would forbid explaining the decision.
    """
    import ast

    source = (Path(__file__).resolve().parents[3] / "services" / "drafts.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)

    assert "src.services.artifacts" not in imported, "the draft layer must not reach the writer"
    assert "ArtifactService" not in imported
    assert not any(name.endswith("services.artifacts") for name in imported)


# ---------------------------------------------------------------------------
# 4. The schema holds the same kinds the contract does
# ---------------------------------------------------------------------------
def _migration() -> str:
    return (MIGRATIONS / "0006_drafts.sql").read_text(encoding="utf-8")


def test_the_migration_exists_with_a_reverse() -> None:
    for name in ("0006_drafts.sql", "0006_drafts.down.sql"):
        path = MIGRATIONS / name
        assert path.exists(), f"{name} is missing"
        assert path.read_text(encoding="utf-8").strip(), f"{name} is empty"


def test_the_kinds_in_the_check_are_the_kinds_in_the_contract() -> None:
    """A copy of the list in the SQL would pass forever, even after they diverge.

    The side that is DERIVED is the SQL: the contract is the source.
    """
    sql = _migration()
    match = re.search(r"drafts_kind_known check \(\s*kind in \(([^)]*)\)", sql)
    assert match is not None, "the drafts table has no kind check"
    declared = set(re.findall(r"'([^']+)'", match.group(1)))
    expected = {kind.value for kind in ArtifactKind}
    assert declared == expected, f"kinds in the SQL check differ: {declared ^ expected}"


def test_a_draft_is_keyed_by_its_client_and_its_own_id() -> None:
    sql = _migration()
    assert "primary key (client_id, draft_id)" in sql


def test_the_draft_table_is_not_the_artifact_table() -> None:
    """A draft in `ikig.artifacts` would enter the indexes and the feed."""
    sql = _migration()
    assert "create table ikig.drafts" in sql
    assert "insert into ikig.artifacts" not in sql
    assert "create table ikig.artifacts" not in sql


def test_the_ledger_was_removed_on_purpose() -> None:
    """It could not be made correct, so it is gone rather than ignored.

    A key built from the content and the second makes two saves of the same
    text inside one second the same save — the second becomes a silent no-op.
    And a CREATE cannot use one at all: the caller does not know whether the
    draft exists. Leaving the table behind while the code stopped writing to it
    would be the "field nobody reads" failure this repository keeps guarding
    against, so a migration drops it.
    """
    history = _migration()  # 0006 created it
    assert "create table ikig.draft_keys" in history

    removal = (MIGRATIONS / "0008_drop_draft_ledger.sql").read_text(encoding="utf-8")
    assert "drop table if exists ikig.draft_keys" in removal
    assert "drop index if exists ikig.ix_draft_keys_draft" in removal


def test_the_code_does_not_write_a_ledger_that_no_longer_exists() -> None:
    """A write to a dropped table is a runtime error nobody would see in review."""
    source = (Path(__file__).resolve().parents[3] / "data" / "drafts.py").read_text(
        encoding="utf-8"
    )

    assert "draft_keys" not in source
