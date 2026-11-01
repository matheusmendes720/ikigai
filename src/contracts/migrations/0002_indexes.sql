-- 0002_indexes.sql — the indexes that make the structured, full-text and
-- semantic queries actually fast. A query that has to scan the table is the
-- same as a query that greps the vault.

create index ix_artifacts_kind_quarter on ikig.artifacts (kind, quarter) where deleted_at is null;
create index ix_artifacts_quarter_status on ikig.artifacts (quarter, status) where deleted_at is null;
create index ix_artifacts_parent on ikig.artifacts (parent_uid);
create index ix_artifacts_updated on ikig.artifacts (updated_at desc);
create index ix_artifacts_title_trgm on ikig.artifacts using gin (title gin_trgm_ops);
create index ix_artifacts_body_fts on ikig.artifacts using gin (to_tsvector('portuguese', coalesce(title,'') || ' ' || coalesce(body,'')));

create index ix_relations_dst on ikig.artifact_relations (dst_uid, rel);
create index ix_revisions_uid on ikig.artifact_revisions (uid, revision desc);

-- The vector dimension must equal EMBEDDING_DIM in src/contracts/store.py.
-- An HNSW index is built for exactly one dimension, so a mismatch here is a
-- migration error, not something to fix in the index definition.
alter table ikig.artifacts add column embedding vector(1536);
create index ix_artifacts_embedding_hnsw on ikig.artifacts
    using hnsw (embedding vector_cosine_ops) with (m = 16, ef_construction = 64);
