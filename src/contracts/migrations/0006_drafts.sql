-- 0006_drafts.sql — prose that is being written, and is not an artifact yet.
--
-- A draft is the state of a client that has not finished thinking. It lives in
-- the store for the reason the store exists at all: the client is one of
-- several (Telegram, a TUI, a harness), it reconnects, and a draft that dies
-- with the socket is prose the owner has to write twice.
--
-- It is deliberately NOT a row in `ikig.artifacts`:
--
--   * the full-text and vector indexes read every artifact row, so a
--     half-written sentence would rank against finished prose in every query
--     that shares a word with it;
--   * the change feed announces writes to the DOM, and a keystroke is not a
--     change to the DOM — a feed that fires on every keystroke carries
--     nothing;
--   * `artifact_revisions` is append-only and is the history of a thing that
--     exists. A draft is overwritten in place and discarded without a trace.
--
-- The key is (client_id, draft_id) and not a UEID, because a draft has no
-- identity in the DOM: it is not in the DOM yet. Two devices composing at the
-- same time are two drafts, and neither can see the other's.

create table ikig.drafts (
    client_id  text        not null,
    draft_id   text        not null,
    kind       text        not null,
    title      text,
    body       text        not null default '',
    parent_uid text        references ikig.artifacts(uid),
    -- The optimistic guard, and it is the same guard the artifacts carry: a
    -- save that expects a stale revision is a conflict, never a silent
    -- overwrite (ADR-037 D5).
    revision   integer     not null default 1 check (revision >= 1),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (client_id, draft_id),
    constraint drafts_kind_known check (
        kind in ('sonho', 'plano', 'onda', 'fase', 'revisao', 'nota',
                 'kpi', 'desc', 'okr', 'tarefa')
    ),
    constraint drafts_draft_id_not_empty check (length(draft_id) > 0),
    constraint drafts_client_id_not_empty check (length(client_id) > 0)
);

-- The one query a client makes on reconnection: "what was I writing?".
create index ix_drafts_client_updated on ikig.drafts (client_id, updated_at desc);

-- The de-duplication ledger of the saves.
--
-- It is a table of its own, not a row in `ikig.idempotency_keys`, because that
-- ledger carries a `uid` (it points at an artifact) and a draft is not one.
-- A key stored against a uid that does not exist would be a foreign key
-- pointing nowhere, and the honest shape of "this save happened" is a ledger
-- that names the draft.
create table ikig.draft_keys (
    key        text        primary key,
    client_id  text        not null,
    draft_id   text        not null,
    created_at timestamptz not null default now()
);

create index ix_draft_keys_draft on ikig.draft_keys (client_id, draft_id);
