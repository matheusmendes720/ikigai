-- 0009_materialized_search_vector.sql — o vector de busca, materializado.
--
-- A busca estruturada é a única consulta que o produto faz sem parar, e
-- ela custava 1 500 ms num corpus de 2 000 artefactos. A causa foi medida:
--
--   * o índice GIN existe, sobre a expressão exacta que a query usa
--     (`to_tsvector('portuguese', coalesce(title,'') || ' ' || coalesce(body,''))`);
--   * quando o planner o escolhe, a query leva 6 ms;
--   * quando o planner o RECUSA, a query recalcula `to_tsvector()` — o
--     STEMMER português — sobre o corpo inteiro de cada linha que visita:
--     20 069 ms para 1 990 corpos, contra 60 ms para os títulos sozinhos.
--
-- O planner recusa o índice quando o termo é COMUM: `'dia'` está em 324
-- linhas e `'nota'` em 1 192 das 1 974, e um índice GIN com uma lista de
-- postings desse tamanho custa mais do que um scan. O problema é que o
-- planner não sabe estimar quantas linhas casa uma EXPRESSÃO calculada,
-- por isso adivinha — e para um termo raro acerta ('trimestral' está em 8
-- linhas, e a query leva 0,4 ms com o índice).
--
-- `ANALYZE` não corrige: a estimativa para uma expressão continua errada.
--
-- A CORRECÇÃO é tornar o vector uma COLUNA. A expressão passa a ser
-- calculada UMA vez, na escrita, e a query compara uma coluna com uma
-- consulta — o que o planner sabe estimar, e o que o índice serve sem
-- stemming. A coluna é `GENERATED ALWAYS AS ... STORED`: o Postgres
-- recalcula-a em cada `insert` e em cada `update`, e não há trigger — logo
-- não há caminho pelo qual o vector e o corpo deixem de concordar.
--
-- A alternativa — um trigger que mantém a coluna — reintroduz a classe de
-- bug que o trigger de `0004` já tem de ter em conta: um trigger que
-- ninguém dispara deixa a coluna a envelhecer em silêncio. Uma coluna
-- gerada não tem essa falha: ou está certa, ou a escrita não aconteceu.
--
-- O índice antigo (`ix_artifacts_body_fts`) sai. Ele servia a mesma
-- consulta pela via da EXPRESSÃO, e dois índices sobre o mesmo texto só
-- custam tempo de escrita. O GIN sobre a coluna substitui-o.
--
-- O que NÃO muda: a configuração 'portuguese' (de `0001_text_search.sql`),
-- o stemming, e o facto de a busca ser a mesma. Uma linha que casava
-- antes casa agora — a semântica é idêntica, só o custo de a encontrar é
-- que deixa de ser o do stemmer.

alter table ikig.artifacts
    add column search_vector tsvector
    generated always as (
        to_tsvector('portuguese', coalesce(title, '') || ' ' || coalesce(body, ''))
    ) stored;

-- O índice que a coluna precisa. Um GIN sobre a COLUNA, não sobre a
-- expressão: é este que o planner consegue estimar, e portanto o que
-- ele escolhe também quando o termo é comum.
--
-- `CONCURRENTLY` é impossível aqui — o runner aplica cada migração dentro
-- de uma transacção, e o `CONCURRENTLY` não pode correr dentro de uma.
-- A tabela tem 2 000 linhas e 7 MB de prosa: a construção leva segundos.
create index ix_artifacts_search_vector
    on ikig.artifacts using gin (search_vector);

-- O índice da expressão sai. A query passa a ser servida pela coluna, e
-- manter os dois é trabalho de escrita sem nenhum ganho de leitura.
drop index if exists ikig.ix_artifacts_body_fts;
