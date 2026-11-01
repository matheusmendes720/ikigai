-- 0003_rls.down.sql — reverse of 0003_rls.sql.

drop policy if exists artifact_relations_client on ikig.artifact_relations;
drop policy if exists artifact_decs_client on ikig.artifact_decs;
drop policy if exists artifact_okr_client on ikig.artifact_okr;
drop policy if exists artifact_kpi_client on ikig.artifact_kpi;
drop policy if exists artifact_tarefa_client on ikig.artifact_tarefa;
drop policy if exists artifact_plano_client on ikig.artifact_plano;
drop policy if exists artifact_sonho_client on ikig.artifact_sonho;
drop policy if exists idempotency_keys_client on ikig.idempotency_keys;
drop policy if exists artifact_revisions_client on ikig.artifact_revisions;
drop policy if exists artifacts_client on ikig.artifacts;

alter table ikig.artifact_decs disable row level security;
alter table ikig.artifact_okr disable row level security;
alter table ikig.artifact_kpi disable row level security;
alter table ikig.artifact_tarefa disable row level security;
alter table ikig.artifact_plano disable row level security;
alter table ikig.artifact_sonho disable row level security;
alter table ikig.idempotency_keys disable row level security;
alter table ikig.artifact_revisions disable row level security;
alter table ikig.artifact_relations disable row level security;
alter table ikig.artifacts disable row level security;
