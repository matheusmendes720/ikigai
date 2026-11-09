-- 0005_vault_path.down.sql — the reverse of the provenance column.
--
-- Dropping the column drops the zone with it: a tree ingested under this
-- migration keeps its rows, but the bucket they were filed under is gone.

drop index if exists ikig.ix_artifacts_vault_path;

alter table ikig.artifacts drop column if exists vault_path;
