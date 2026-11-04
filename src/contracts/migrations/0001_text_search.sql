-- 0001_text_search.sql — the full-text configuration the search assumes.
--
-- Postgres creates only `english` and `simple` on a fresh database; every
-- other language is explicit. Both the index in 0002_indexes.sql and the
-- query in src/data/repository.py call to_tsvector('portuguese', ...), so
-- without this configuration the SECOND migration fails and the schema is
-- never built at all.
--
-- The snowball stemmer is used when the image ships the Portuguese
-- dictionary data. Where it does not, the configuration still works on the
-- `simple` template — whitespace tokenisation, no stemming — which is a
-- degraded search rather than a failed one.
--
-- It sorts between 0001_init.sql and 0002_indexes.sql, which is the order
-- the runner applies migrations in.
--
-- THE ARGUMENT LIST IS NAMES, NOT STRINGS. `create text search dictionary`
-- parses its arguments as identifiers — a quoted literal there is a syntax
-- error, and a syntax error in this file aborts the whole migration, so the
-- schema is never built. The template's parameter (the language) is the
-- second name, for the same reason.

do $$
begin
    if not exists (select 1 from pg_ts_config where cfgname = 'portuguese') then
        create text search configuration portuguese (copy = simple);
    end if;
end
$$;

do $$
begin
    if not exists (select 1 from pg_ts_dict where dictname = 'portuguese_stem') then
        create text search dictionary portuguese_stem (snowball, portuguese);
    end if;
    alter text search configuration portuguese
        alter mapping for hword, hword_part, word with portuguese_stem;
exception
    when others then
        raise notice 'the portuguese stemmer is unavailable here: %', sqlerrm;
end
$$;
