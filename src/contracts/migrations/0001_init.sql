-- 0001_init.sql — the DOM schema: the spine, the typed extensions, the graph,
-- the revision history and the idempotency ledger.
--
-- The UID CHECK below is the contract regex from src/contracts/common.py
-- (_UEID_PATTERN), all three branches, copied verbatim. It is not a summary of
-- the pattern: the first branch alone would reject the 16-character content
-- hash that the DOM's own make_uid example produces.

create extension if not exists vector;
create extension if not exists pg_trgm;

create schema if not exists ikig;

-- spine -------------------------------------------------------------------
create table ikig.artifacts (
    uid          text primary key,
    kind         text        not null,
    title        text        not null,
    body         text,
    body_hash    text,
    parent_uid   text        references ikig.artifacts(uid),
    quarter      text,
    status       text,
    revision     integer     not null default 1 check (revision >= 1),
    client_id    text        not null,
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now(),
    deleted_at   timestamptz,
    constraint artifacts_uid_format check (uid ~ '^(?:[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}|[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9-]{8,36}:[a-f0-9]{4,64}|[a-z]{2,8}:[a-z_]+:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8})$'),
    constraint artifacts_kind_known check (kind in ('sonho','plano','onda','fase','revisao','nota','kpi','desc','okr','tarefa'))
);

-- typed extensions per kind ------------------------------------------------
-- A kind gets a table here only when it has fields of its own. The map that
-- keeps the two ends in step is KIND_TABLES in src/contracts/store.py.
create table ikig.artifact_sonho (
    uid            text primary key references ikig.artifacts(uid) on delete cascade,
    ikigai_vectors text[] not null default '{}'
);

create table ikig.artifact_plano (
    uid       text primary key references ikig.artifacts(uid) on delete cascade,
    plan_tier text
);

create table ikig.artifact_tarefa (
    uid               text primary key references ikig.artifacts(uid) on delete cascade,
    priority          text     not null default 'medium',
    estimated_minutes integer
);

create table ikig.artifact_kpi (
    uid        text primary key references ikig.artifacts(uid) on delete cascade,
    metric     text      not null,
    target     numeric,
    actual     numeric,
    unit       text,
    period     text      not null,
    direction  text      not null default 'up' check (direction in ('up','down','flat'))
);

create table ikig.artifact_okr (
    uid          text primary key references ikig.artifacts(uid) on delete cascade,
    objective    text      not null,
    key_result   text      not null,
    kr_target    numeric,
    kr_actual    numeric,
    kr_progress  numeric   check (kr_progress is null or (kr_progress >= 0 and kr_progress <= 1))
);

create table ikig.artifact_decs (
    uid        text primary key references ikig.artifacts(uid) on delete cascade,
    decision   text      not null,
    rationale  text,
    decider    text,
    outcome    text
);

-- graph -------------------------------------------------------------------
create table ikig.artifact_relations (
    src_uid    text not null references ikig.artifacts(uid),
    dst_uid    text not null references ikig.artifacts(uid),
    rel        text not null,
    weight     double precision,
    meta       jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    primary key (src_uid, dst_uid, rel),
    constraint relations_no_self_loop check (src_uid <> dst_uid)
);

-- version history ----------------------------------------------------------
-- No foreign key and no cascading delete: the history outlives the row it
-- describes, because a revision that disappears with its artifact is not a
-- history.
create table ikig.artifact_revisions (
    uid        text        not null,
    revision   integer     not null,
    snapshot   jsonb       not null,
    author     text,
    client_id  text        not null,
    created_at timestamptz not null default now(),
    primary key (uid, revision)
);

-- idempotency ledger -------------------------------------------------------
create table ikig.idempotency_keys (
    key        text        primary key,
    client_id  text        not null,
    uid        text        not null,
    created_at timestamptz not null default now()
);
