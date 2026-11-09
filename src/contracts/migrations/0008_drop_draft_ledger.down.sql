-- 0008_drop_draft_ledger.down.sql — put the ledger back, empty.
--
-- The reverse recreates the TABLE and not the behaviour: the code that wrote
-- to it is gone (0008's reason), so rolling this migration back gives a
-- database that could accept a ledger and a service that never fills it.
--
-- That is the honest reverse. A reverse that also restored the de-duplication
-- would have to restore the bug the de-duplication caused, and a rollback is
-- for undoing a schema, not for re-deciding a design.

create table if not exists ikig.draft_keys (
    key        text        primary key,
    client_id  text        not null,
    draft_id   text        not null,
    created_at timestamptz not null default now()
);

create index if not exists ix_draft_keys_draft on ikig.draft_keys (client_id, draft_id);
