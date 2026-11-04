-- 0001_text_search.down.sql — remove the full-text configuration.
--
-- The configuration is dropped before the dictionary: the mapping makes the
-- configuration depend on the dictionary, and the dictionary is not owned by
-- it, so it has to go on its own.

drop text search configuration if exists portuguese;
drop text search dictionary if exists portuguese_stem;
