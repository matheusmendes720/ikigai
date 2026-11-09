-- 0004_artifact_events.sql — the store announces its own changes.
--
-- The writers are not all in one process: the vault ingestion runs in its own
-- container, the Telegram client in another, the retrieval layer in a third. A
-- client that only ever learns about its own writes is not synced with
-- anything — it is a mirror of itself.
--
-- So the store says what it did, on a channel, the moment it did it. The
-- trigger below announces the uid and the operation; the payload carries no
-- data, because the store is the only place that has the current version of
-- an artifact. A client that wants more reads it.
--
-- The channel name is `ikig_artifact_events`, and it is named in one place on
-- the other side too — src/data/repository.py, `ARTIFACT_EVENTS_CHANNEL`. A
-- channel that does not match is a listener that waits forever.

create or replace function ikig.notify_artifact_event() returns trigger as $$
declare
    uid_value text;
begin
    -- NEW is unassigned in a DELETE, and reading a field of an unassigned
    -- record is an error in PL/pgSQL. The operation decides which one to read.
    if tg_op = 'DELETE' then
        uid_value := old.uid;
    else
        uid_value := new.uid;
    end if;

    perform pg_notify(
        'ikig_artifact_events',
        json_build_object('uid', uid_value, 'op', tg_op)::text
    );

    -- The return value is ignored by an AFTER trigger.
    return null;
end;
$$ language plpgsql;

create trigger trg_artifacts_event
    after insert or update or delete on ikig.artifacts
    for each row execute function ikig.notify_artifact_event();
