-- 0004_artifact_events.down.sql — the store stops announcing its changes.

drop trigger if exists trg_artifacts_event on ikig.artifacts;
drop function if exists ikig.notify_artifact_event();
