-- 0008_drop_draft_ledger.sql — delete the de-duplication ledger the drafts had.
--
-- 0006 gave drafts a ledger of idempotency keys, copying the shape artifacts
-- use. Running the bot in a real conversation showed why that shape does not
-- survive contact with a draft.
--
-- The key was built from the CONTENT and the SECOND:
--
--     draft:<client>:<draft_id>:<sha256(body)[:16]>:<second>
--
-- Two consequences, both wrong:
--
--   * two saves of the SAME text inside one second are the same key, so the
--     second save is silently a no-op that reports `unchanged`. In the
--     conversation that looked like "/rascunho nota" reopening a draft when it
--     had done nothing at all;
--   * for a CREATE it cannot work even in principle. The caller does not know
--     whether the draft exists — that is what the conflict is FOR. A key that
--     has to encode a revision the caller cannot know is a key that lies.
--
-- The revision guard already does the job, and it does it correctly: a retry
-- carries the revision it read, and once the first save has committed that
-- revision is stale, so the retry is a 409 and the client rereads. That is the
-- rule the rest of this store follows, and the drafts do not need a second one.
--
-- Dropping this table loses nothing: it held only hashes of saves that either
-- happened (and are in `ikig.drafts`) or did not (and were never needed).

drop index if exists ikig.ix_draft_keys_draft;
drop table if exists ikig.draft_keys;
