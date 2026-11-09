-- 0007_artifact_events_log.down.sql — back to a doorbell with no mailbox.
--
-- The trigger's FUNCTION is restored to what 0004 wrote, and the TRIGGER is
-- recreated on top of it, so a database that rolls this back announces
-- changes exactly as it did before — it only stops keeping them.
--
-- Dropping the table destroys the events nobody has replayed yet. That is the
-- honest cost of the reverse: the log is operational state, not content, and
-- an artifact that changed is still readable through its own row.

create or replace function ikig.notify_artifact_event() returns trigger as $$
declare
    uid_value text;
begin
    if tg_op = 'DELETE' then
        uid_value := old.uid;
    else
        uid_value := new.uid;
    end if;

    perform pg_notify(
        'ikig_artifact_events',
        json_build_object('uid', uid_value, 'op', tg_op)::text
    );

    return null;
end;
$$ language plpgsql;

create or replace trigger trg_artifacts_event
    after insert or update or delete on ikig.artifacts
    for each row execute function ikig.notify_artifact_event();

drop function if exists ikig.prune_artifact_events(integer);
drop index if exists ikig.ix_artifact_events_created;
drop index if exists ikig.ix_artifact_events_seq;
drop table if exists ikig.artifact_events;
