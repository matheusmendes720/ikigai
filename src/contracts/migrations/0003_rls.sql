-- 0003_rls.sql — row-level security scoped by the calling client's claim.
--
-- The client is one person across several devices, so the claim that matters
-- is `client_id`, not a user identity. The claim arrives on the service's JWT
-- and is read from the request settings. When it is absent the comparison is
-- NULL, which is not true, so nothing is visible: the policy fails closed.

-- Bootstrap role. Creating it needs CREATEROLE, which a managed Postgres may
-- not grant; the migration continues without it in that case, because the
-- policies below work with whatever role the service connects as.
do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'ikigai_service') then
        begin
            create role ikigai_service nologin;
        exception when insufficient_privilege then
            raise notice 'role ikigai_service not created: insufficient privilege';
        end;
    end if;
end $$;

alter table ikig.artifacts enable row level security;
alter table ikig.artifact_relations enable row level security;
alter table ikig.artifact_revisions enable row level security;
alter table ikig.idempotency_keys enable row level security;
alter table ikig.artifact_sonho enable row level security;
alter table ikig.artifact_plano enable row level security;
alter table ikig.artifact_tarefa enable row level security;
alter table ikig.artifact_kpi enable row level security;
alter table ikig.artifact_okr enable row level security;
alter table ikig.artifact_decs enable row level security;

create policy artifacts_client on ikig.artifacts
    using (client_id = current_setting('request.jwt.claim.client_id', true))
    with check (client_id = current_setting('request.jwt.claim.client_id', true));

create policy artifact_revisions_client on ikig.artifact_revisions
    using (client_id = current_setting('request.jwt.claim.client_id', true))
    with check (client_id = current_setting('request.jwt.claim.client_id', true));

create policy idempotency_keys_client on ikig.idempotency_keys
    using (client_id = current_setting('request.jwt.claim.client_id', true))
    with check (client_id = current_setting('request.jwt.claim.client_id', true));

-- The extension tables and the edge table carry no client column of their own:
-- they inherit the isolation of the artifact they belong to.
create policy artifact_kpi_client on ikig.artifact_kpi
    using (exists (select 1 from ikig.artifacts a
                   where a.uid = ikig.artifact_kpi.uid
                     and a.client_id = current_setting('request.jwt.claim.client_id', true)))
    with check (exists (select 1 from ikig.artifacts a
                        where a.uid = ikig.artifact_kpi.uid
                          and a.client_id = current_setting('request.jwt.claim.client_id', true)));

create policy artifact_sonho_client on ikig.artifact_sonho
    using (exists (select 1 from ikig.artifacts a
                   where a.uid = ikig.artifact_sonho.uid
                     and a.client_id = current_setting('request.jwt.claim.client_id', true)))
    with check (exists (select 1 from ikig.artifacts a
                        where a.uid = ikig.artifact_sonho.uid
                          and a.client_id = current_setting('request.jwt.claim.client_id', true)));

create policy artifact_plano_client on ikig.artifact_plano
    using (exists (select 1 from ikig.artifacts a
                   where a.uid = ikig.artifact_plano.uid
                     and a.client_id = current_setting('request.jwt.claim.client_id', true)))
    with check (exists (select 1 from ikig.artifacts a
                        where a.uid = ikig.artifact_plano.uid
                          and a.client_id = current_setting('request.jwt.claim.client_id', true)));

create policy artifact_tarefa_client on ikig.artifact_tarefa
    using (exists (select 1 from ikig.artifacts a
                   where a.uid = ikig.artifact_tarefa.uid
                     and a.client_id = current_setting('request.jwt.claim.client_id', true)))
    with check (exists (select 1 from ikig.artifacts a
                        where a.uid = ikig.artifact_tarefa.uid
                          and a.client_id = current_setting('request.jwt.claim.client_id', true)));

create policy artifact_okr_client on ikig.artifact_okr
    using (exists (select 1 from ikig.artifacts a
                   where a.uid = ikig.artifact_okr.uid
                     and a.client_id = current_setting('request.jwt.claim.client_id', true)))
    with check (exists (select 1 from ikig.artifacts a
                        where a.uid = ikig.artifact_okr.uid
                          and a.client_id = current_setting('request.jwt.claim.client_id', true)));

create policy artifact_decs_client on ikig.artifact_decs
    using (exists (select 1 from ikig.artifacts a
                   where a.uid = ikig.artifact_decs.uid
                     and a.client_id = current_setting('request.jwt.claim.client_id', true)))
    with check (exists (select 1 from ikig.artifacts a
                        where a.uid = ikig.artifact_decs.uid
                          and a.client_id = current_setting('request.jwt.claim.client_id', true)));

create policy artifact_relations_client on ikig.artifact_relations
    using (exists (select 1 from ikig.artifacts a
                   where a.uid = ikig.artifact_relations.src_uid
                     and a.client_id = current_setting('request.jwt.claim.client_id', true)))
    with check (exists (select 1 from ikig.artifacts a
                        where a.uid = ikig.artifact_relations.src_uid
                          and a.client_id = current_setting('request.jwt.claim.client_id', true)));
