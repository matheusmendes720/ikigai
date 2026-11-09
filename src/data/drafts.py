"""Persistence for drafts. No domain rules live here.

The one behaviour this file exists to guarantee is the same one
`ArtifactRepository` guarantees, applied to prose that is not finished yet:
the optimistic write. A save carrying a stale `expected_revision` changes
nothing and reports a conflict — it never falls back to an upsert that
silently overwrites, because that is how one device's paragraph eats
another's.

The second behaviour is the de-duplication ledger. A client that retries after
a dropped socket sends the same save again, and the same save must not become
two writes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.contracts.drafts import Draft, DraftOutcome, DraftSaveRequest
from src.contracts.errors import ConflictError, NotFoundError

from .client import DataClient, rows_as_dicts

__all__ = ["DraftRepository"]

_DRAFT_COLUMNS = (
    "client_id, draft_id, kind, title, body, parent_uid, revision, created_at, updated_at"
)


def _to_draft(row: Mapping[str, Any]) -> Draft:
    return Draft(
        client_id=row["client_id"],
        draft_id=row["draft_id"],
        kind=row["kind"],
        title=row["title"],
        body=row["body"],
        parent_uid=row["parent_uid"],
        revision=row["revision"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class DraftRepository:
    """Every read and write a draft allows against the store."""

    def __init__(self, client: DataClient) -> None:
        self._client = client

    async def save(self, req: DraftSaveRequest) -> DraftOutcome:
        """Save the draft at the revision it expects.

        There is no de-duplication ledger here, and that is deliberate. A
        content key makes two saves of the same text inside one second the
        same save, so the second is silently a no-op; and for a CREATE it
        cannot work at all, because the caller does not know whether the draft
        exists — which is exactly what the conflict is for.

        The revision guard IS the de-duplication: a retry carries the revision
        it read, and once the first save has committed that revision is stale,
        so the retry is a conflict and the caller rereads.
        """
        draft = req.draft
        async with self._client.transaction() as conn:
            if req.expected_revision is None:
                outcome, revision = await self._create(conn, draft)
            else:
                outcome, revision = await self._update(conn, draft, req.expected_revision)
        return DraftOutcome(
            client_id=draft.client_id,
            draft_id=draft.draft_id,
            revision=revision,
            outcome=outcome,
        )

    async def _create(self, conn: Any, draft: Draft) -> tuple[str, int]:
        cursor = await conn.execute(
            "insert into ikig.drafts (client_id, draft_id, kind, title, body, parent_uid, "
            "revision, created_at, updated_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "on conflict (client_id, draft_id) do nothing",
            (
                draft.client_id,
                draft.draft_id,
                str(draft.kind),
                draft.title,
                draft.body,
                str(draft.parent_uid) if draft.parent_uid else None,
                draft.revision,
                draft.created_at,
                draft.updated_at,
            ),
        )
        if cursor.rowcount == 0:
            raise ConflictError(
                f"draft {draft.draft_id!r} already exists for {draft.client_id!r}",
                detail="the draft is taken — send expected_revision to update it",
            )
        return "created", draft.revision

    async def _update(self, conn: Any, draft: Draft, expected: int) -> tuple[str, int]:
        cursor = await conn.execute(
            "update ikig.drafts set kind=%s, title=%s, body=%s, parent_uid=%s, "
            "created_at=%s, updated_at=%s, revision=revision+1 "
            "where client_id=%s and draft_id=%s and revision=%s",
            (
                str(draft.kind),
                draft.title,
                draft.body,
                str(draft.parent_uid) if draft.parent_uid else None,
                draft.created_at,
                draft.updated_at,
                draft.client_id,
                draft.draft_id,
                expected,
            ),
        )
        if cursor.rowcount == 0:
            raise ConflictError(
                f"draft {draft.draft_id!r} was changed by someone else",
                detail="expected_revision is stale — reread and reapply",
            )
        return "updated", expected + 1

    async def get(self, client_id: str, draft_id: str) -> Draft | None:
        row = await self._client.fetch_one(
            f"select {_DRAFT_COLUMNS} from ikig.drafts where client_id = %s and draft_id = %s",
            (client_id, draft_id),
        )
        return _to_draft(row) if row else None

    async def list(self, client_id: str, limit: int = 50) -> list[Draft]:
        """The drafts a client has open, most recently touched first.

        It is the query a client makes on reconnection — "what was I
        writing?" — so it is a list and not a lookup.
        """
        rows = await self._client.execute(
            f"select {_DRAFT_COLUMNS} from ikig.drafts where client_id = %s "
            "order by updated_at desc limit %s",
            (client_id, limit),
        )
        return [_to_draft(row) for row in rows]

    async def discard(
        self, client_id: str, draft_id: str, expected_revision: int | None = None
    ) -> DraftOutcome:
        """Throw the draft away. Deletes the row; there is no history to keep.

        The revision guard applies here too, when the caller sends one: a
        discard racing another device's save is a conflict, not a silent
        removal — the same rule `soft_delete` follows for an artifact.

        It runs on a TRANSACTION's connection, and not on the client's
        `execute`: that one hands back rows, and the answer to a delete is a
        rowcount. Reading `rowcount` off a list of rows is how a delete comes
        to believe it deleted nothing.
        """
        clauses = ["client_id = %s", "draft_id = %s"]
        params: list[Any] = [client_id, draft_id]
        if expected_revision is not None:
            clauses.append("revision = %s")
            params.append(expected_revision)
        async with self._client.transaction() as conn:
            cursor = await conn.execute(
                f"delete from ikig.drafts where {' and '.join(clauses)}",
                tuple(params),
            )
            if cursor.rowcount == 0:
                # Inside the transaction, and on its own connection: the row
                # that was not deleted is the answer to "why not?".
                current = await self._fetch_one(
                    conn,
                    "select revision from ikig.drafts where client_id = %s and draft_id = %s",
                    (client_id, draft_id),
                )
                if current is None:
                    raise NotFoundError(f"no draft {draft_id!r} for {client_id!r}")
                raise ConflictError(
                    f"draft {draft_id!r} was changed by someone else",
                    detail="expected_revision is stale — reread and reapply",
                )
        return DraftOutcome(
            client_id=client_id,
            draft_id=draft_id,
            revision=expected_revision or 0,
            outcome="discarded",
        )

    @staticmethod
    async def _fetch_one(
        conn: Any,
        sql: str,
        params: Sequence[Any],
    ) -> Mapping[str, Any] | None:
        cursor = await conn.execute(sql, params)
        if cursor.description is None:
            return None
        rows = rows_as_dicts(cursor, await cursor.fetchall())
        return rows[0] if rows else None
