-- 0007_artifact_events_log.sql — the store announces its changes, and KEEPS them.
--
-- 0004 built the announcement: a trigger that calls `pg_notify` with the uid
-- and the operation. It is transactional and it is correct — and it is
-- fire-and-forget. A `NOTIFY` is delivered to whoever is LISTENing at that
-- moment, and to nobody else: a client that was reconnecting when the write
-- happened never learns it happened, and there is no way to ask for it
-- afterwards. The channel is a doorbell, not a mailbox.
--
-- So the same trigger now writes the event to a table, in the SAME
-- transaction as the artifact, and announces the row it wrote. The
-- announcement stays (it is what makes the live feed live); the row is what
-- makes the feed RESUMABLE. A client that reconnects sends the last sequence
-- it saw and gets the gap, in order.
--
-- Two things this buys, and one it does not:
--
--   * **Order.** The sequence is monotonic and assigned by the store, so two
--     clients replaying the same gap see the same order.
--   * **No lost wakeup.** An event written while nobody was listening is
--     still there when somebody asks.
--   * **It does not make the event carry data.** The payload is the uid and
--     the operation, exactly as before: the store is the only place with the
--     current version of an artifact, and a client that wants more reads it.

create table ikig.artifact_events (
    -- The cursor. `bigserial` and not a timestamp: two writes in the same
    -- microsecond are two events, and a clock cannot order them.
    seq        bigserial primary key,
    uid        text        not null,
    op         text        not null,
    created_at timestamptz not null default now(),
    constraint artifact_events_op_known check (op in ('INSERT', 'UPDATE', 'DELETE'))
);

-- The one query a reconnecting client makes: "what happened after N?".
create index ix_artifact_events_seq on ikig.artifact_events (seq);

-- The retention query, and the only reason `created_at` is indexed: an event
-- log is operational state, not content, so it is the one table here that is
-- allowed to forget. See `prune_artifact_events` below.
create index ix_artifact_events_created on ikig.artifact_events (created_at desc);

create or replace function ikig.notify_artifact_event() returns trigger as $$
declare
    uid_value text;
    seq_value bigint;
begin
    -- NEW is unassigned in a DELETE, and reading a field of an unassigned
    -- record is an error in PL/pgSQL. The operation decides which one to read.
    if tg_op = 'DELETE' then
        uid_value := old.uid;
    else
        uid_value := new.uid;
    end if;

    -- The row and the artifact are written in ONE transaction: an event that
    -- describes a write which rolled back is worse than no event at all.
    insert into ikig.artifact_events (uid, op) values (uid_value, tg_op)
    returning seq into seq_value;

    -- The live feed keeps the sequence, so a client that is listening does
    -- not have to re-read the table to learn where it is.
    perform pg_notify(
        'ikig_artifact_events',
        json_build_object('uid', uid_value, 'op', tg_op, 'seq', seq_value)::text
    );

    -- The return value is ignored by an AFTER trigger.
    return null;
end;
$$ language plpgsql;

-- The trigger itself is unchanged in shape: 0004 created it and this
-- migration replaces only the function it calls, so a database that already
-- has the trigger keeps firing it.
create or replace trigger trg_artifacts_event
    after insert or update or delete on ikig.artifacts
    for each row execute function ikig.notify_artifact_event();

create or replace function ikig.prune_artifact_events(keep integer) returns integer as $$
declare
    removed integer;
begin
    if keep is null or keep < 1 then
        raise exception 'prune_artifact_events needs a positive keep, got %', keep;
    end if;

    with doomed as (
        select seq from ikig.artifact_events order by seq desc offset keep
    )
    delete from ikig.artifact_events e using doomed d where e.seq = d.seq;

    get diagnostics removed = row_count;
    return removed;
end;
$$ language plpgsql;
