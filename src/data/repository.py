"""Persistence for the DOM. No domain rules live here.

The one behaviour this file exists to guarantee is the optimistic write: a write
carrying a stale `expected_revision` changes nothing and reports a conflict. It
never falls back to an upsert that silently overwrites, because that is how one
client's edit disappears.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any

from src.contracts.dom import (
    Artifact,
    ArtifactBundle,
    Relation,
    RelationType,
    SearchQuery,
    SearchResult,
    WriteOutcome,
    WriteRequest,
)
from src.contracts.dom_kinds import (
    DecisionArtifact,
    KPIArtifact,
    OKRArtifact,
    PlanoArtifact,
    SonhoArtifact,
    TarefaArtifact,
)
from src.contracts.errors import ConflictError, InvalidPayloadError, NotFoundError
from src.contracts.store import KIND_TABLES

from .client import DataClient, rows_as_dicts

try:  # pragma: no cover — the driver is an optional runtime dependency
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover
    Jsonb = None

__all__ = ["ARTIFACT_EVENTS_CHANNEL", "ArtifactRepository"]

_ARTIFACT_COLUMNS = (
    "uid, kind, title, body, body_hash, parent_uid, quarter, status, revision, "
    "created_at, updated_at, deleted_at"
)

#: The channel the change trigger announces on. It is named in one place, and
#: the migration that raises it names the same one — a channel that does not
#: match is a listener that waits forever.
ARTIFACT_EVENTS_CHANNEL = "ikig_artifact_events"


def _to_artifact(row: Mapping[str, Any]) -> Artifact:
    return Artifact(
        uid=row["uid"],
        kind=row["kind"],
        title=row["title"],
        body=row["body"],
        body_hash=row["body_hash"],
        parent_uid=row["parent_uid"],
        quarter=row["quarter"],
        status=row["status"],
        revision=row["revision"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )


def _to_relation(row: Mapping[str, Any]) -> Relation:
    return Relation(
        src_uid=row["src_uid"],
        dst_uid=row["dst_uid"],
        rel=row["rel"],
        weight=row["weight"],
        meta=row["meta"] or {},
    )


def _vector_literal(embedding: Sequence[float]) -> str:
    """Render an embedding as a pgvector literal.

    Doing it here keeps the pgvector python package out of the dependency set:
    the column casts the text, and the driver never has to know what a vector is.
    """
    return "[" + ",".join(repr(float(value)) for value in embedding) + "]"


def _decode_cursor(cursor: str) -> tuple[str, str]:
    """Unpack the opaque pagination cursor into its sort-key parts."""
    try:
        payload = json.loads(cursor)
    except (TypeError, ValueError) as exc:
        raise InvalidPayloadError(f"malformed cursor: {cursor!r}") from exc
    if not isinstance(payload, list) or len(payload) != 2:
        raise InvalidPayloadError(f"malformed cursor: {cursor!r}")
    updated_at, uid = payload
    return str(updated_at), str(uid)


class ArtifactRepository:
    """Every read and write the DOM allows against the store."""

    def __init__(self, client: DataClient) -> None:
        self._client = client

    async def upsert(
        self,
        req: WriteRequest,
        embedding: Sequence[float] | None = None,
    ) -> WriteOutcome:
        """Write the artifact, its edges and its vector in ONE transaction.

        The vector rides with the row on purpose. A row with a body and no
        vector is a row the semantic index cannot see, and the search that
        silently finds nothing is worse than one that fails: it reports "there
        is no such thing" about something the store holds.
        """
        artifact = req.artifact
        uid = str(artifact.uid)
        async with self._client.transaction() as conn:
            replay = await conn.execute(
                "insert into ikig.idempotency_keys(key, client_id, uid) values (%s,%s,%s) "
                "on conflict (key) do nothing",
                (req.idempotency_key, req.client_id, uid),
            )
            if replay.rowcount == 0:
                current = await self._fetch_one(
                    conn, "select revision from ikig.artifacts where uid = %s", (uid,)
                )
                revision = int(current["revision"]) if current else artifact.revision
                return WriteOutcome(
                    uid=artifact.uid,
                    revision=revision,
                    outcome="unchanged",
                    detail="idempotency key already consumed",
                )

            if req.expected_revision is None:
                outcome, revision = await self._create(conn, req, embedding)
            else:
                outcome, revision = await self._update(conn, req, embedding)

            await self._write_extension(conn, artifact)
            await self._insert_revision(conn, artifact, revision, req.client_id)
            await self._write_relations(conn, req.relations)
        return WriteOutcome(uid=artifact.uid, revision=revision, outcome=outcome)

    async def _create(
        self,
        conn: Any,
        req: WriteRequest,
        embedding: Sequence[float] | None = None,
    ) -> tuple[str, int]:
        artifact = req.artifact
        cursor = await conn.execute(
            "insert into ikig.artifacts (uid, kind, title, body, body_hash, parent_uid, "
            "quarter, status, revision, client_id, created_at, updated_at, embedding) "
            "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector) "
            "on conflict (uid) do nothing",
            (
                str(artifact.uid),
                str(artifact.kind),
                artifact.title,
                artifact.body,
                artifact.body_hash,
                str(artifact.parent_uid) if artifact.parent_uid else None,
                artifact.quarter,
                artifact.status,
                artifact.revision,
                req.client_id,
                artifact.created_at,
                artifact.updated_at,
                _vector_literal(embedding) if embedding is not None else None,
            ),
        )
        if cursor.rowcount == 0:
            raise ConflictError(
                f"artifact {artifact.uid} already exists; a create was expected",
                detail="the uid is taken — send expected_revision to update it",
            )
        return "created", artifact.revision

    async def _update(
        self,
        conn: Any,
        req: WriteRequest,
        embedding: Sequence[float] | None = None,
    ) -> tuple[str, int]:
        artifact = req.artifact
        cursor = await conn.execute(
            "update ikig.artifacts set title=%s, body=%s, body_hash=%s, parent_uid=%s, "
            "quarter=%s, status=%s, kind=%s, revision=revision+1, updated_at=now(), "
            "embedding=%s::vector "
            "where uid=%s and revision=%s and deleted_at is null",
            (
                artifact.title,
                artifact.body,
                artifact.body_hash,
                str(artifact.parent_uid) if artifact.parent_uid else None,
                artifact.quarter,
                artifact.status,
                str(artifact.kind),
                _vector_literal(embedding) if embedding is not None else None,
                str(artifact.uid),
                req.expected_revision,
            ),
        )
        if cursor.rowcount == 0:
            raise ConflictError(
                f"artifact {artifact.uid} was changed by someone else",
                detail="expected_revision is stale — reread and reapply",
            )
        return "updated", int(req.expected_revision) + 1

    async def _write_extension(self, conn: Any, artifact: Artifact) -> None:
        if KIND_TABLES.get(artifact.kind) is None:
            return
        if isinstance(artifact, KPIArtifact):
            await conn.execute(
                "insert into ikig.artifact_kpi (uid, metric, target, actual, unit, period, direction) "
                "values (%s,%s,%s,%s,%s,%s,%s) on conflict (uid) do update set metric=excluded.metric, "
                "target=excluded.target, actual=excluded.actual, unit=excluded.unit, "
                "period=excluded.period, direction=excluded.direction",
                (
                    str(artifact.uid),
                    artifact.metric,
                    artifact.target,
                    artifact.actual,
                    artifact.unit,
                    artifact.period,
                    artifact.direction,
                ),
            )
        elif isinstance(artifact, OKRArtifact):
            await conn.execute(
                "insert into ikig.artifact_okr (uid, objective, key_result, kr_target, kr_actual, kr_progress) "
                "values (%s,%s,%s,%s,%s,%s) on conflict (uid) do update set objective=excluded.objective, "
                "key_result=excluded.key_result, kr_target=excluded.kr_target, "
                "kr_actual=excluded.kr_actual, kr_progress=excluded.kr_progress",
                (
                    str(artifact.uid),
                    artifact.objective,
                    artifact.key_result,
                    artifact.kr_target,
                    artifact.kr_actual,
                    artifact.kr_progress,
                ),
            )
        elif isinstance(artifact, DecisionArtifact):
            await conn.execute(
                "insert into ikig.artifact_decs (uid, decision, rationale, decider, outcome) "
                "values (%s,%s,%s,%s,%s) on conflict (uid) do update set decision=excluded.decision, "
                "rationale=excluded.rationale, decider=excluded.decider, outcome=excluded.outcome",
                (
                    str(artifact.uid),
                    artifact.decision,
                    artifact.rationale,
                    artifact.decider,
                    artifact.outcome,
                ),
            )
        elif isinstance(artifact, SonhoArtifact):
            await conn.execute(
                "insert into ikig.artifact_sonho (uid, ikigai_vectors) values (%s,%s) "
                "on conflict (uid) do update set ikigai_vectors=excluded.ikigai_vectors",
                (str(artifact.uid), list(artifact.ikigai_vectors)),
            )
        elif isinstance(artifact, PlanoArtifact):
            await conn.execute(
                "insert into ikig.artifact_plano (uid, plan_tier) values (%s,%s) "
                "on conflict (uid) do update set plan_tier=excluded.plan_tier",
                (str(artifact.uid), str(artifact.plan_tier) if artifact.plan_tier else None),
            )
        elif isinstance(artifact, TarefaArtifact):
            await conn.execute(
                "insert into ikig.artifact_tarefa (uid, priority, estimated_minutes) "
                "values (%s,%s,%s) on conflict (uid) do update set priority=excluded.priority, "
                "estimated_minutes=excluded.estimated_minutes",
                (str(artifact.uid), str(artifact.priority), artifact.estimated_minutes),
            )

    async def _insert_revision(
        self,
        conn: Any,
        artifact: Artifact,
        revision: int,
        client_id: str,
    ) -> None:
        snapshot = json.loads(artifact.model_dump_json())
        payload = Jsonb(snapshot) if Jsonb is not None else snapshot
        await conn.execute(
            "insert into ikig.artifact_revisions (uid, revision, snapshot, author, client_id) "
            "values (%s,%s,%s,%s,%s)",
            (str(artifact.uid), revision, payload, client_id, client_id),
        )

    async def soft_delete(self, uid: Any, expected_revision: int) -> WriteOutcome:
        """Mark an artifact deleted without removing the row.

        The revision guard applies here too: a delete racing another client's
        edit is a conflict, not a silent removal.
        """
        async with self._client.transaction() as conn:
            cursor = await conn.execute(
                "update ikig.artifacts set deleted_at=now(), revision=revision+1, updated_at=now() "
                "where uid=%s and revision=%s and deleted_at is null",
                (str(uid), expected_revision),
            )
            if cursor.rowcount == 0:
                existing = await self._fetch_one(
                    conn, "select revision from ikig.artifacts where uid = %s", (str(uid),)
                )
                if existing is None:
                    raise NotFoundError(f"no artifact with uid {uid}")
                raise ConflictError(
                    f"artifact {uid} was changed by someone else",
                    detail="expected_revision is stale — reread and reapply",
                )
            current = await self._fetch_one(
                conn, "select revision from ikig.artifacts where uid = %s", (str(uid),)
            )
        revision = int(current["revision"]) if current else expected_revision + 1
        return WriteOutcome(uid=uid, revision=revision, outcome="updated", detail="soft deleted")

    async def get(self, uid: Any) -> Artifact | None:
        row = await self._client.fetch_one(
            f"select {_ARTIFACT_COLUMNS} from ikig.artifacts where uid = %s and deleted_at is null",
            (str(uid),),
        )
        return _to_artifact(row) if row else None

    async def require(self, uid: Any) -> Artifact:
        artifact = await self.get(uid)
        if artifact is None:
            raise NotFoundError(f"no artifact with uid {uid}")
        return artifact

    async def get_with_relations(self, uid: Any, depth: int = 1) -> ArtifactBundle:
        artifact = await self.require(uid)
        relations = await self.list_relations(uid)
        neighbors: list[ArtifactBundle] = []
        if depth > 0:
            for relation in relations:
                neighbor = await self.get(relation.dst_uid)
                if neighbor is not None:
                    neighbors.append(ArtifactBundle(artifact=neighbor, relations=(relation,)))
        return ArtifactBundle(
            artifact=artifact,
            relations=tuple(relations),
            neighbors=tuple(neighbors),
        )

    async def list_relations(
        self,
        uid: Any,
        rel: RelationType | None = None,
    ) -> list[Relation]:
        if rel is None:
            rows = await self._client.execute(
                "select src_uid, dst_uid, rel, weight, meta from ikig.artifact_relations "
                "where src_uid = %s or dst_uid = %s order by src_uid, dst_uid, rel",
                (str(uid), str(uid)),
            )
        else:
            rows = await self._client.execute(
                "select src_uid, dst_uid, rel, weight, meta from ikig.artifact_relations "
                "where (src_uid = %s or dst_uid = %s) and rel = %s "
                "order by src_uid, dst_uid, rel",
                (str(uid), str(uid), str(rel)),
            )
        return [_to_relation(row) for row in rows]

    async def upsert_relation(self, relation: Relation, conn: Any | None = None) -> None:
        """Write an edge.

        With a `conn`, the edge joins that transaction; without one, it takes
        its own. The write envelope passes the transaction's connection: an
        edge and the artifact it describes are written together or not at all.
        """
        sql = (
            "insert into ikig.artifact_relations (src_uid, dst_uid, rel, weight, meta) "
            "values (%s,%s,%s,%s,%s) on conflict (src_uid, dst_uid, rel) do update set "
            "weight=excluded.weight, meta=excluded.meta"
        )
        params = (
            str(relation.src_uid),
            str(relation.dst_uid),
            str(relation.rel),
            relation.weight,
            Jsonb(relation.meta) if Jsonb is not None else relation.meta,
        )
        if conn is not None:
            await conn.execute(sql, params)
            return
        await self._client.execute(sql, params)

    async def _write_relations(self, conn: Any, relations: Sequence[Relation]) -> None:
        """Write the envelope's edges on the transaction's own connection."""
        for relation in relations:
            await self.upsert_relation(relation, conn=conn)

    async def search(
        self,
        query: SearchQuery,
        embedding: Sequence[float] | None = None,
    ) -> SearchResult:
        """Find artifacts. The semantic path needs the QUERY's vector.

        The vector is passed IN, never computed here. The data layer does not
        know which model wrote the rows, and a query vector from another model
        lands in another space — where the cosine distance between two spaces
        is a number, not a meaning. The service layer owns the provider, so it
        owns the query vector too.
        """
        if query.semantic:
            return await self._search_semantic(query, embedding)
        return await self._search_structured(query)

    async def _search_structured(self, query: SearchQuery) -> SearchResult:
        clauses = ["deleted_at is null"]
        params: list[Any] = []

        if query.kinds:
            kinds = ",".join("%s" for _ in query.kinds)
            clauses.append(f"kind in ({kinds})")
            params.extend(str(kind) for kind in query.kinds)
        if query.quarter is not None:
            clauses.append("quarter = %s")
            params.append(query.quarter)
        if query.status is not None:
            clauses.append("status = %s")
            params.append(query.status)
        if query.parent_uid is not None:
            clauses.append("parent_uid = %s")
            params.append(str(query.parent_uid))
        if query.text:
            clauses.append(
                "to_tsvector('portuguese', coalesce(title,'') || ' ' || coalesce(body,'')) "
                "@@ plainto_tsquery('portuguese', %s)"
            )
            params.append(query.text)
        if query.cursor:
            last_updated, last_uid = _decode_cursor(query.cursor)
            # The cast is required: the cursor carries the timestamp as text, and
            # Postgres will not compare a timestamptz column with a text
            # parameter without it.
            clauses.append("(updated_at, uid) < (%s::timestamptz, %s)")
            params.extend([last_updated, last_uid])

        where = " and ".join(clauses)
        sql = (
            f"select {_ARTIFACT_COLUMNS} from ikig.artifacts where {where} "
            "order by updated_at desc, uid desc limit %s"
        )
        params.append(query.limit + 1)
        rows = await self._client.execute(sql, tuple(params))
        return self._page(rows, query.limit)

    async def _search_semantic(
        self,
        query: SearchQuery,
        embedding: Sequence[float] | None = None,
    ) -> SearchResult:
        if not query.text:
            return SearchResult(artifacts=())
        if embedding is None:
            raise InvalidPayloadError(
                "a semantic search needs the query vector — the service layer "
                "embeds the query with the same provider that wrote the rows"
            )
        clauses = ["deleted_at is null", "embedding is not null"]
        params: list[Any] = []
        if query.kinds:
            kinds = ",".join("%s" for _ in query.kinds)
            clauses.append(f"kind in ({kinds})")
            params.extend(str(kind) for kind in query.kinds)
        if query.quarter is not None:
            clauses.append("quarter = %s")
            params.append(query.quarter)

        where = " and ".join(clauses)
        sql = (
            f"select {_ARTIFACT_COLUMNS} from ikig.artifacts where {where} "
            "order by embedding <=> %s::vector limit %s"
        )
        params.extend([_vector_literal(embedding), query.limit])
        rows = await self._client.execute(sql, tuple(params))
        return SearchResult(artifacts=tuple(_to_artifact(row) for row in rows))

    async def _embed_for_search(self, text: str) -> str:
        from src.services.embeddings import local_embedding

        return _vector_literal(local_embedding(text))

    async def set_embedding(self, uid: Any, embedding: Sequence[float]) -> None:
        await self._client.execute(
            "update ikig.artifacts set embedding = %s::vector where uid = %s",
            (_vector_literal(embedding), str(uid)),
        )

    async def artifacts_without_embedding(self, limit: int = 500) -> list[dict[str, Any]]:
        """The rows the vector index cannot see yet.

        The backfill reads them, embeds them and writes the vector back. It is
        the repair for a store that was written before the vectors were — or
        whose provider changed underneath it.
        """
        rows = await self._client.execute(
            "select uid, title, body from ikig.artifacts "
            "where embedding is null and deleted_at is null "
            "order by updated_at, uid limit %s",
            (limit,),
        )
        return [dict(row) for row in rows]

    async def artifact_events(self) -> AsyncIterator[Mapping[str, Any]]:
        """The store's change notifications, as they arrive.

        The trigger on ``ikig.artifacts`` announces every write on the channel
        ``ARTIFACT_EVENTS_CHANNEL``, so a process that did NOT write the row
        still learns that it changed. That is what makes the websocket a
        sync channel and not a mirror of its own writes: the vault ingestion
        runs in its own container, and its writes have to reach the clients.
        """
        async with self._client.listen(ARTIFACT_EVENTS_CHANNEL) as notifies:
            async for notify in notifies:
                try:
                    payload = json.loads(notify.payload)
                except (TypeError, ValueError):
                    continue
                if isinstance(payload, dict):
                    yield payload

    async def count(self) -> int:
        row = await self._client.fetch_one("select count(*) as n from ikig.artifacts")
        return int(row["n"]) if row else 0

    @staticmethod
    def _page(rows: Sequence[Mapping[str, Any]], limit: int) -> SearchResult:
        has_more = len(rows) > limit
        visible = rows[:limit]
        artifacts = tuple(_to_artifact(row) for row in visible)
        next_cursor = None
        if has_more and artifacts:
            last = artifacts[-1]
            next_cursor = json.dumps([last.updated_at.isoformat(), str(last.uid)])
        return SearchResult(artifacts=artifacts, next_cursor=next_cursor)

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
