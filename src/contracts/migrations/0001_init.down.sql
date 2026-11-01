-- 0001_init.down.sql — reverse of 0001_init.sql.
-- Destructive by nature; the runner requires an explicit confirmation flag.

drop table if exists ikig.idempotency_keys;
drop table if exists ikig.artifact_revisions;
drop table if exists ikig.artifact_relations;
drop table if exists ikig.artifact_decs;
drop table if exists ikig.artifact_okr;
drop table if exists ikig.artifact_kpi;
drop table if exists ikig.artifact_tarefa;
drop table if exists ikig.artifact_plano;
drop table if exists ikig.artifact_sonho;
drop table if exists ikig.artifacts;
