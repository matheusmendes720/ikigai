-- 0006_drafts.down.sql — the reverse of the drafts.
--
-- Drafts are the one kind of state in this store that is NOT append-only, so
-- dropping them destroys nothing that could not be rewritten: a draft is
-- prose in progress, and the finished prose lives in `ikig.artifacts`.

drop index if exists ikig.ix_draft_keys_draft;
drop table if exists ikig.draft_keys;

drop index if exists ikig.ix_drafts_client_updated;
drop table if exists ikig.drafts;
