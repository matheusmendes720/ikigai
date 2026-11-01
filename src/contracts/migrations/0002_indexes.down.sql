-- 0002_indexes.down.sql — reverse of 0002_indexes.sql.

drop index if exists ikig.ix_artifacts_embedding_hnsw;
alter table ikig.artifacts drop column if exists embedding;

drop index if exists ikig.ix_artifacts_body_fts;
drop index if exists ikig.ix_artifacts_title_trgm;
drop index if exists ikig.ix_artifacts_updated;
drop index if exists ikig.ix_artifacts_parent;
drop index if exists ikig.ix_artifacts_quarter_status;
drop index if exists ikig.ix_artifacts_kind_quarter;

drop index if exists ikig.ix_revisions_uid;
drop index if exists ikig.ix_relations_dst;
