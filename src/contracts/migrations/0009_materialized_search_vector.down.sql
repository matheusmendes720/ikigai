-- 0009_materialized_search_vector.down.sql — o inverso da materialização.
--
-- A coluna gerada e o seu índice saem, e o índice da EXPRESSÃO volta: o
-- estado anterior a esta migração é o estado em que a query é servida
-- pela expressão, e é esse que o `down` tem de restaurar.
--
-- Desfazer um esquema não é re-decidir um desenho (ADR-040 §10.2): o
-- `down` recria o que existia, e o `--drop` da coluna faz o resto.

drop index if exists ikig.ix_artifacts_search_vector;

alter table ikig.artifacts drop column if exists search_vector;

-- O índice que a migração tirou, com a mesma definição de `0002_indexes.sql`.
-- Volta sem `CONCURRENTLY` pelo mesmo motivo de lá: o `down` corre dentro
-- de uma transacção.
create index if not exists ix_artifacts_body_fts
    on ikig.artifacts using gin (
        to_tsvector('portuguese', coalesce(title, '') || ' ' || coalesce(body, ''))
    );
