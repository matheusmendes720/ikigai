-- 0005_vault_path.sql — the provenance of an artifact that came from a file.
--
-- Until now the store kept the CONTENT of a vault file and forgot where the
-- file was. Two things need that path, and both of them are the same path:
--
--   1. The ZONE. The knowledge tree is a set of buckets — `1_norte`,
--      `2_projeto`, `3_indice`, `4_leitura`, `5_atomicas`, `6_permanentes` —
--      and a client that cannot ask for one bucket gets all of them. The zone
--      is the first segment of the path, so a prefix match answers it.
--   2. The FILE. A write-back needs to know which file to write, and the
--      store is the only place that knows.
--
-- One column, two jobs. It is NULL for an artifact that was never in a file
-- (the Telegram bot writes those), and NULL is the honest answer for those.
--
-- The index is a text_pattern_ops one because the filter is a prefix match:
-- `vault_path like '2_projeto/%'`.

alter table ikig.artifacts add column vault_path text;

create index ix_artifacts_vault_path on ikig.artifacts (vault_path text_pattern_ops);
