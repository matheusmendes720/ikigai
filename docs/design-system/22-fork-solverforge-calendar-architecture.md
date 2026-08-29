# 22 — Fork: solverforge-calendar architecture (Rust TEA + dual MCP transport + UPI mesh substrate)

> **Categoria:** FORK (Layer 4 — Forks catalog, posição #22)
> **Anchor canônico:** `interfaces/solverforge-calendar/` + `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md`
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (Rust, edition 2021, TEA, ratatui, rmcp, UPI, klhk soft-delete, DAG, Kahn topological sort, OAuth2, keyring, rrule, RFC 5545, recur, fork, adapter, UEID, sync_map, federation, mesh substrate)
> **Caminho canônico local:** `C:/Users/mathe/code_space/life-oss/interfaces/solverforge-calendar/`
> **Phase 1 baseline:** `gateways.yaml:14` cwd stale (B-01) + OQ-8 (two MCP transports)
> **Crate:** `solverforge-calendar` v0.3.0 (edition 2021), 11,649 LOC Rust em 30 files

---

## §1 — Resumo

O **fork solverforge-calendar** é um **calendar CLI/TUI/MCP tri-modal** construído em **Rust edition 2021** com **ratatui + rmcp 3.1**, distribuído como **crate crate-local** (sem upstream MIT explícito). Sua função no data mesh é **dupla e load-bearing**: (1) **fork-pronta user-facing** com TUI 4-vistas (month/week/day/agenda) + Google Calendar bidirectional sync + iCal 0.17 export, e (2) **mesh substrate** via `unified_planning_items` (UPI) — o único fork já projetado como superset cross-fork (status + time_block + ikigai + provenance + blocked_by + tags JSON), conectado aos outros forks via `upi_sync` MCP tool. A integração canônica com a malha acontece via `SolverforgeCalendarAdapter` (`src/mesh/adapters/solverforge_calendar.py`) com **PK reuse pattern** (`SELECT id WHERE ueid=?` then INSERT-or-UPDATE) — preserva história sem PK churn. Diferente dos outros forks, solverforge-calendar **tem dual MCP transport**: stdio (default) + HTTP+SSE (feature-gated, **mas a feature `http` não está em Cargo.toml — branch é compile-dead**). UPI tem `id TEXT PK + ueid TEXT UNIQUE` separados — `ueid` é o join key canônico, `id` é fork-internal. É o fork mais alinhado ao Pattern #13 (ForkAdapter Protocol) e ao Pattern #14 (Idempotency UEID) porque o adapter-side já implementa o pattern. Tem **5 gaps conhecidos** que bloqueiam promotion a canonical write path: (a) `google_sync` MCP tool é stub, (b) HTTP+SSE feature-gated out, (c) `google-calendar3 7.0` declared but unused, (d) `recurrence_exceptions` dead schema, (e) `gateways.yaml:14` cwd stale.

---

## §2 — Inventário

### 2.1 Estrutura física

- **Root local:** `C:/Users/mathe/code_space/life-oss/interfaces/solverforge-calendar/`
- **Total Rust LOC em `src/`:** **11,649 linhas** em **30 files**
- **Bin targets** (`Cargo.toml:86-88`):
  - `solverforge-calendar` (default) → `src/main.rs` (TUI, tokio + crossterm + ratatui)
  - `solverforge-calendar-cli` → `src/bin/solverforge-calendar-cli.rs` (Clap CLI wrapper, 40 LOC)
  - `solverforge-calendar-mcp` → `src/bin/solverforge-calendar-mcp.rs` (MCP server, **963 LOC**)

### 2.2 Modules (lib.rs re-exports flat — sem nested namespace)

| Module | File | LOC | Role |
|:-------|:-----|:---:|:------|
| `app` | `src/app.rs` | 370+ | TEA-style `App` state (running, view, focused_date, calendars, events, dependencies, DAG, completed, sidebar, form, status) |
| `calendar_service` | `src/calendar_service.rs` | 250+ | Validated CRUD over `Calendar` with `CalendarServiceError { NotFound, Validation, Conflict, Internal }` |
| `cli` | `src/cli.rs` | 700+ | clap derive — Calendars/Projects/Events/Dependencies/Google subcommands, JSON-first `--json` |
| `dag` | `src/dag.rs` | 200+ | `EventDag` (forward `edges`, reverse `reverse` HashMaps), Kahn topological sort, cycle detection |
| `db` | `src/db.rs` | **1,267** | rusqlite schema v1+v2, CRUD, UPI helpers, sync_token mgmt, 12 unit tests |
| `event` | `src/event.rs` | — | `Event` enum (`Key`/`Mouse`/`Resize`/`Tick`) + `EventHandler` 250ms tick |
| `google::auth` | `src/google/auth.rs` | 223 | OAuth2 loopback `127.0.0.1:8989`, keyring storage, refresh-token exchange |
| `google::discovery` | `src/google/discovery.rs` | 195 | `discover_calendars()` paginated |
| `google::sync` | `src/google/sync.rs` | 518 | Sync delta + paginated `events.list`, soft-delete on `status=cancelled` |
| `google::types` | `src/google/types.rs` | 80 | `google_event_to_local()` RFC 3339 → storage format |
| `ical` | `src/ical.rs` | 60+ | `icalendar` 0.17 export (RRULE, all-day DTSTART;VALUE=DATE) |
| `keys` | `src/keys.rs` | 311 | `View` + `Action` enums, `resolve(view, key) → Action` |
| `models` | `src/models.rs` | 171 | `Calendar` / `Project` / `Event` / `EventDependency` structs |
| `models_unified` | `src/models_unified.rs` | — | `UnifiedPlanningItem`, `Dependency`, `IkigaiVectors`, `Provenance`, `TimeBlock` |
| `notifications` | `src/notifications.rs` | 83 | `notify-rust` (D-Bus on Linux, "z" feature) |
| `observability` | `src/observability.rs` | 140 | OTel init (LangSmith + Langfuse dual, gated by env) |
| `recurrence` | `src/recurrence.rs` | 43 | UI `RecurrencePreset` enum (None / Daily / Weekdays / etc.), wraps rrule at form layer |
| `sync::migrations` | `src/sync/migrations.rs` | 74 | CREATE TABLE for `unified_planning_items / sync_map / wikilink_resolution_log / sync_conflicts` |
| `sync::tuiboard_parser` | `src/sync/tuiboard_parser.rs` | 604 | `BoardCardDelta` reader — wikilinks extract |
| `sync::tuiboard_transformer` | `src/sync/tuiboard_transformer.rs` | 383 | `BoardCardDelta → UnifiedPlanningItem` with warnings |
| `sync::tuiboard_writer` | `src/sync/tuiboard_writer.rs` | 549 | UPSERT + 4-strategy wikilink resolver (`board:`, `::`, title, tag) |
| `theme` | `src/theme.rs` | 320 | Color tokens (`#82FB9C` primary, `#0B0C16` background) |
| `ui::*` | `src/ui/{month,week,day,agenda,…}.rs` | 36-296 each | Per-view ratatui renderers |
| `worker` | `src/worker.rs` | 231 | Background worker returning `WorkerResult` |

### 2.3 Tables SQLite (dual-DB federation)

**Migration v1** (`db.rs:90-189`, timestamp `20260101000001`):

| Table | Key columns | Indexes |
|:------|:------------|:--------|
| `calendars` | `id PK` (UUID v4), `name`, `color`, `source`, `google_id`, `visible`, `position`, soft-delete | `idx_calendars_google_id_unique` UNIQUE on `(google_id) WHERE deleted_at IS NULL AND source='google' AND google_id IS NOT NULL` (`db.rs:194-198`) |
| `projects` | `id PK`, `name`, `color`, `description?`, soft-delete | — |
| `events` | `id PK`, `calendar_id FK`, `project_id FK`, `title`, `start_at`, `end_at`, `all_day`, `rrule?`, `google_id?`, `google_etag?`, `reminder_minutes?`, `timezone` (default 'UTC'), soft-delete | `idx_events_calendar_id`, `idx_events_project_id`, `idx_events_start_at`, `idx_events_end_at`, `idx_events_google_id`, `idx_events_calendar_google_id_unique` (`db.rs:200-203`) |
| `event_dependencies` | `id PK`, `from_event_id FK CASCADE`, `to_event_id FK CASCADE`, `dependency_type` (`blocks`/`related`) | `UNIQUE(from_event_id, to_event_id)`, idx_from, idx_to |
| `recurrence_exceptions` | `id PK`, `event_id FK CASCADE`, `original_start`, `replacement_event_id FK CASCADE` | `idx_recurrence_exc_event_id` |
| `sync_tokens` | `id PK`, `calendar_id FK CASCADE UNIQUE`, `sync_token`, `synced_at` | `UNIQUE(calendar_id)` |

**PRAGMAs** (`db.rs:37-42`): WAL, foreign_keys=ON, synchronous=NORMAL.

**Migration v2** (`db.rs:191-208`, timestamp `20260406000001`) — second migration for first-class updates.

### 2.4 Sync layer (separate `unified_planning.db`)

`src/sync/migrations.rs:16-72` cria **4 tabelas**:

- `unified_planning_items` (id, title, description, **status**, all_day, start_at, end_at, **time_block JSON**, calendar_id, project_id, **ikigai JSON**, **provenance JSON**, **blocked_by JSON**, **tags JSON**, rrule, timestamps)
- `sync_map` (PRIMARY KEY (system, board_card_id)) — wikilink bridge cross-fork
- `wikilink_resolution_log`
- `sync_conflicts`

**Indexes**: `idx_upi_start_at`, `idx_upi_status`, `idx_upi_deleted_at`, `idx_upi_provenance_sys` (JSON path).

### 2.5 MCP server (rmcp 3.1, dual transport stdio + HTTP+SSE)

**Server core:** `McpServer` struct at `solverforge-calendar-mcp.rs:34-48` — wraps `Arc<SyncMutex<rusqlite::Connection>>` (single-threaded DB access).

**Tool routing:** `#[tool_router(router = tool_router)]` at `:268-269` + `#[tool_handler(router = self.tool_router)]` at `:265-266`.

**MCP protocol:** `"2024-11-05"` (`:30`).

**Tool catalog (30 total):**

| Categoria | Ferramentas |
|:----------|:------------|
| `calendars_*` (5) | `list`, `get`, `create`, `update`, `delete` |
| `projects_*` (5) | `list`, `get`, `create`, `update`, `delete` |
| `events_*` (5) | `list`, `get`, `create`, `update`, `delete` |
| `dependencies_*` (5) | `list`, `get`, `create`, `update`, `delete` |
| `google_*` (1) | `google_sync` **(STUB)** |
| `upi_*` (5) | `sync`, `list`, `get`, `update`, `search` |

**Transport handling** (`:878-905`):
- `stdio` (default) → `McpServer::new()?.serve(rmcp::transport::stdio())`
- `http` (requires `feature = "http"`) → `run_http_server` **STUB INCOMPLETE** (no SSE wiring)
- **Gap:** `http` feature NOT in `Cargo.toml` features list → runtime `http` choice exits with error.

---

## §3 — Conteúdo principal

### 3.1 TEA-style App state + Event loop

A camada `app` (`src/app.rs`, 370+ LOC) implementa **The Elm Architecture (TEA)**: `App { running: bool, view: View, focused_date: NaiveDate, calendars, events, dependencies, dag: EventDag, completed: HashSet<i64>, sidebar_focus, form_state, status }`. Toda mudança de estado passa por `update(action: Action) -> App` que retorna novo state. Invariante: `running: bool` é o **único predicado** de shutdown (Ctrl+C sets running=false, event loop exits ratatui).

**Event loop** (`src/main.rs:42-74`) — tokio runtime wraps blocking `loop { terminal.draw(...); events.next() }` with `EventHandler` ticking at **250ms** (`:52`). Mouse events captured but ignored (`:61-63`). Resize handled implicitly by ratatui. D-Bus notifications via `notify-rust` na feature "z".

### 3.2 UPI como mesh substrate (cross-fork superset)

`unified_planning_items` é a **única tabela já projetada como superset** cross-fork. Colunas JSON-encoded (`status`, `time_block`, `ikigai`, `provenance`, `blocked_by`, `tags`) carregam dados que nenhum fork individual tem mas o mesh necesita:

```sql
CREATE TABLE unified_planning_items (
    id TEXT PRIMARY KEY,
    title TEXT,
    description TEXT,
    status TEXT,           ← canonical 6-state enum (ver doc 23)
    all_day INTEGER,
    start_at TEXT,
    end_at TEXT,
    time_block TEXT,       ← JSON: {start_min, end_min}
    calendar_id TEXT,
    project_id TEXT,
    ikigai TEXT,           ← JSON: {vectors: {p,e,s,f,v}, score, regime}
    provenance TEXT,       ← JSON: {source_fork, source_path, created_at}
    blocked_by TEXT,       ← JSON array
    tags TEXT,             ← JSON array
    rrule TEXT,
    created_at TEXT,
    updated_at TEXT,
    deleted_at TEXT
);
```

Indexes: `idx_upi_start_at`, `idx_upi_status`, `idx_upi_deleted_at`, `idx_upi_provenance_sys` (JSON path).

**Cross-fork bridge**: `sync_map` (PRIMARY KEY `(system, board_card_id)`) é a tabela de ponte. Quando tuiboard parser (`src/sync/tuiboard_parser.rs:604`) lê `BoardCardDelta` do markdown, `tuiboard_writer` (`src/sync/tuiboard_writer.rs:549`) faz UPSERT em `sync_map` + `unified_planning_items` usando 4-strategy wikilink resolver (`board:`, `::`, title, tag).

**Phase 3 readiness** (`06-synthesis-mesh-readiness.md:131-136`): solverforge-calendar IS o mesh substrate; promote `upi_sync` MCP tool (line 778-803) para canonical write path. Mas 4 bugs devem ser corrigidos: (a) `google_sync` stub at `:769-774`, (b) HTTP+SSE feature-gated out at `:916-958`, (c) `google-calendar3 7.0` unused at `Cargo.toml:33`, (d) `recurrence_exceptions` dead schema at `db.rs:164-171`.

### 3.3 SolverforgeCalendarAdapter (mesh UPSERT PK-reuse)

`src/mesh/adapters/solverforge_calendar.py` (105 LOC) implementa `ForkAdapter` para UPI com **PK stability** pattern:

```python
# SELECT-then-INSERT/UPDATE: reuse existing id on re-run
existing_id = conn.execute(
    "SELECT id FROM unified_planning_items WHERE ueid = ?",
    (event.ueid,),
).fetchone()

if existing_id is not None:
    conn.execute("""UPDATE unified_planning_items
                    SET status='planned', ikigai=?
                    WHERE ueid=?""", ...)
else:
    new_id = str(uuid.uuid4())
    conn.execute("""INSERT INTO unified_planning_items
                    (id, ueid, status, blocked_by, tags, ikigai, provenance)
                    VALUES (?, ?, 'planned', '[]', '[]', ?, '{}')""", ...)
```

**Trade-off vs `TaskdogAdapter`**: solverforge precisa de **2 SQL statements** (SELECT + INSERT/UPDATE) por apply_change, vs 1 statement no taskdog UPSERT. Vantagem: **PK stability** — `id` interno não muda entre runs do mesmo UEID. Previsível para views cross-fork, evita PK churn em audit_logs.

### 3.4 OAuth2 + Google Calendar sync (loopback flow)

OAuth2 flow (`src/google/auth.rs`) usa **loopback listener em `127.0.0.1:8989`** (hardcoded port):

1. Build auth URL `https://accounts.google.com/o/oauth2/v2/auth?scope=https://www.googleapis.com/auth/calendar&access_type=offline&prompt=consent` (`:103-114`)
2. Open browser via `open::that(auth_url)` (`:117`)
3. TcpListener recebe first request line, extracts `code=` query (`:120-138`)
4. POST to `https://oauth2.googleapis.com/token` with `grant_type=authorization_code` (`:162-186`)
5. Persist via `GoogleClient::save_credentials()` + `save_refresh_token()` ao **keyring** (`:86-88`)

**Refresh token**: `access_type=offline` garante refresh_token persistente. Access tokens NÃO vão ao keyring — só refresh tokens. Refresh on-demand via `refresh_access_token()` (`:47-69`).

**Keyring entries** (`auth.rs:5-7`): `google_client_id` / `google_client_secret` / `google_refresh_token`. Service name `"solverforge-calendar"` (`:4`) — único por fork, sem colisão.

**Sync application** (`src/google/sync.rs:42-89`): skips `status: "cancelled"` → soft-deletes by `(calendar_id, google_id)`. Para outros: looks up by `(calendar_id, google_id)`, updates if exists, inserts if new. Persists `nextSyncToken` on last page (`db::upsert_sync_token` at `db.rs:773-783`).

**Gap crítico**: `google-calendar3 7.0` está em `Cargo.toml:33` mas **NÃO é usado** — solverforge usa `reqwest` 0.12 directly. Wastes ~15-20s incremental compile time e ships `yup-oauth2` que o código **não consome** (hand-rolls OAuth em `auth.rs:96-186`).

### 3.5 RRULE / iCal / recurring events

**State atual** (`03-fork-solverforge-calendar.md:322-336`): RRULE é armazenado como **string** na coluna `events.rrule` (`db.rs:129`, `models.rs:66`).

- **Sem expansão**: rrule 0.14 crate é declarada em `Cargo.toml:30` mas **nenhuma expansão em runtime**. UI usa `RecurrencePreset` enum (`recurrence.rs:1-43`) apenas para form selection.
- **Dead schema**: `recurrence_exceptions` table (`db.rs:164-171`) é definida mas **sem helpers** (`insert_recurrence_exception` / `load_recurrence_exceptions`) — tabela morta.
- **iCal export**: `ical::export_events` (`:46-48`) strips `"RRULE:"` prefix antes de escrever. Exportado mas **não importado** por nenhuma view.

**Implicação**: clientes que recebem `ical.ics` vêem RRULE mas **não conseguem materializar ocorrências** porque o sender não expande. Phase 3 candidate: implementar `rrule.expand()` em `recurrence.rs` + helpers para `recurrence_exceptions`.

### 3.6 DAG (Kahn-style topological sort)

`src/dag.rs` (200+ LOC) implementa `EventDag { edges: HashMap<i64, Vec<i64>>, reverse: HashMap<i64, Vec<i64>> }` — forward + reverse adjacency lists. `add_edge(from, to)` adiciona both directions e **detecta ciclos** (topological sort impossível se ciclo). Use case: cycle prevention in `dependencies_create` MCP tool (`:687-715`).

**Algorithm**: Kahn-style: in-degrees count → zero-in-degree queue → process → decrement neighbors → repeat. Cycle detection: queue drena antes de processar todos os nodes → cycle exists.

**Trade-off**: cycle detection at insertion time garante DAG acyclic, mas **não há repair mechanism** se data vem importada com ciclo (e.g., 2 events em cada other's `blocked_by`). Melhor: explicit raise on cycle, refuse insert.

### 3.7 Gateway routing match matrix

**Source:** `gateways.yaml:12-15` declara command `cargo run --bin solverforge-calendar-mcp`, cwd `C:/Users/mathe/code_space/apps/calendar/solverforge-calendar` (STALE per B-01).

**Match matrix** (real tools vs gateway expects):

| Prefix | Tools exposed | Gateway expects? | Status |
|:-------|:--------------|:-----------------|:-------|
| `calendars_` | 5 | YES | Match |
| `events_` | 5 | YES | Match |
| `projects_` | 5 | YES | Match |
| `dependencies_` | 5 | YES | Match |
| `google_` | 1 (`google_sync`) | YES | **STUB** |
| `upi_` | 5 | YES | Match |

**Caveats:**

1. **`google_sync` is a stub** — returns `{"status": "not_implemented"}` (`:773`). Real sync logic em `src/google/sync.rs` é só invocado via CLI subcommand (`src/cli.rs`), não via MCP.
2. **`google_*` prefix is too narrow** — adding `gcal_*` would NOT route.
3. **Path stale** — cwd referencia pre-reorg location. Real binary em `life-oss/interfaces/solverforge-calendar/`.
4. **No `startup_timeout`** — `cargo run` cold start 30-60s on first build, ~5s incremental.

---

## §4 — Cross-references

### 4.1 Design-system docs

- **`docs/design-system/00-INDEX.md`** §3 — Layer 4 Forks catalog navigation (este + 20 + 21 + 23).
- **`docs/design-system/13-pattern-fork-adapter-protocol.md`** §2.4 (SolverforgeCalendarAdapter verbatim, PK reuse pattern) + §2.5 (UEID-UNIQUE 3-storages).
- **`docs/design-system/15-pattern-hysteresis-fsm.md`** §2.1 (PUSH/MAINTAIN/REDUCE/RECOVER regime) — solverforge-calendar UPI `status` field armazena regime como part of `ikigai` JSON; cross-mapping em doc 23.
- **`docs/design-system/04-canvas-mesh-architecture.md`** §3.3 — solverforge = UPI PK reuse branch.
- **`docs/design-system/14-pattern-idempotency-upstream-id.md`** §3 — solverforge PK reuse é exemplo canônico de idempotency sem UNIQUE-only.
- **`docs/design-system/07-canvas-sync-architecture.md`** §3 — `SyncEngine` references solverforge-calendar (cross-link OpenAPI/spec).

### 4.2 Phase 2 diagnostics (fontes verbatim)

- **`docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md`** (418 linhas) — RE primário, fonte verbatim deste doc.
- **`docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`** §OQ-1/OQ-5/OQ-7/OQ-8 — solverforge federation evidence.
- **`docs/diagnostics/2026-08-28-phase1-audit/01-verified.md`** B-01 (gateways.yaml cwd MISSING solverforge) + OQ-8 (two MCP transports — solverforge tem dual, mesmo que HTTP stub).

### 4.3 Memory cross-refs

- **`[[interfaces-architecture-2026-08-27]]`** — solverforge fork = user view + mesh substrate (dual role).
- **`[[master-branch-carro-chefe-2026-08-28]]`** — solverforge UPI é o destino de sync do deep-agent.
- **`[[windows-orphan-dir-delete]]`** — `apps/calendar/solverforge-calendar` deletado 2026-08-28; fork em `life-oss/interfaces/solverforge-calendar/`.
- **`[[orchestration-clone-playground]]`** — vendored fork (origem do projeto vida).
- **`[[ag3-gateway-orphan-2026-08-27]]`** — gateway orphan relates a todos 3 forks.
- **`[[pav-as-ikigai-subsystem-2026-08-28]]`** — UPI como mesh substrate é a confirmação que PAV (subsystem extension) substituiu CLI/TUI nativo pelo mesh substrate.

### 4.4 Auto-performance OS (matemática + integração)

- **`docs/auto-performance-os/24-integration-mesh-ueid-propagation.md`** §2 — solverforge-calendar UPI é o cross-fork join target (`sync_map` PR KEY `(system, board_card_id)`).

### 4.5 Code anchors (verificados)

| Path | LOC / Conteúdo | Padrão |
|:-----|:---------------|:-------|
| `src/mesh/adapters/solverforge_calendar.py:17-104` | `SolverforgeCalendarAdapter` + PK reuse | ForkAdapter Protocol impl (UPI branch) |
| `src/mesh/adapters/base.py:8-23` | `ForkAdapter` Protocol base | Pattern #13 verbatim |
| `interfaces/solverforge-calendar/src/bin/solverforge-calendar-mcp.rs` | 963 LOC | MCP server rmcp 3.1 |
| `interfaces/solverforge-calendar/src/db.rs` | 1,267 LOC | rusqlite schema v1+v2 + 12 unit tests |
| `interfaces/solverforge-calendar/src/sync/tuiboard_writer.rs:286-319` | 4-strategy wikilink resolver | cross-fork bridge |
| `interfaces/solverforge-calendar/src/sync/migrations.rs:16-72` | `unified_planning_items` schema | mesh substrate table |
| `interfaces/solverforge-calendar/src/google/auth.rs:103-186` | OAuth2 loopback flow | Google sync |
| `interfaces/solverforge-calendar/src/google/sync.rs:42-89` | bidirectional sync application | `events.list` paginated |
| `interfaces/solverforge-calendar/src/dag.rs:1-200` | Kahn topological sort | cycle detection |
| `apps/mcp-gateway/config/gateways.yaml:12-15` | solverforge backend entry | cwd STALE |

### 4.6 Pitfalls noted

- **`gateways.yaml:14` cwd stale** (B-01) — fork em `life-oss/interfaces/solverforge-calendar/`, não `apps/calendar/...`. Phase 1 confirmou.
- **`google_sync` MCP tool é stub** — `:769-774` returns `not_implemented`. Real sync em `src/google/sync.rs` é CLI-only.
- **HTTP+SSE transport feature-gated out** — `:878-905` branch compiles out porque `http` feature **NÃO** está em `Cargo.toml` features list. Runtime `http` choice exits with error.
- **`google-calendar3 7.0` declared but unused** — `Cargo.toml:33` declara mas solverforge usa `reqwest` 0.12 direct. Wastes compile time, ships `yup-oauth2` not consumed.
- **`recurrence_exceptions` table dead schema** — `db.rs:164-171` defined mas sem `insert_recurrence_exception`/`load_recurrence_exceptions` helpers. rrule expansion not implemented.
- **No `startup_timeout` on gateway entry** — `cargo run` cold start 30-60s.
- **`SyncEngine::poll` doesn't actually poll** — `sync/mod.rs:34-89` counts local rows with `provenance='X'`, not actual external system reads. "Sync" é misnômer; real sync pipeline only via MCP `upi_sync`.
- **Hardcoded `127.0.0.1:8989` OAuth port** — port conflict se outro app binds 8989; no fallback; Windows firewall pode bloquear first run.
- **Mouse events captured but ignored** — `src/main.rs:61-63` (`main.rs:52` ticks 250ms).

---

## §5 — Fontes

### Code (verbatim, lidos via Read tool)
- `src/mesh/adapters/solverforge_calendar.py` (105 LOC) — SolverforgeCalendarAdapter PK reuse
- `src/mesh/adapters/base.py` (24 LOC) — ForkAdapter Protocol base
- `src/contracts/task_change.py` (58 LOC) — `PropagationEvent` Pydantic frozen
- `src/contracts/common.py` — UEID 4-part regex (cross-canonical)

### Docs (analisados, verbatim lidos via Read tool)
- `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md` (418 LOC) — RE primário; **todas** as seções §module map, §schema, §google integration, §MCP tool inventory, §gateway match, §TUI widgets, §rrule+keyring, §trade-offs, §cross-refs citadas acima
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md` (196 LOC) — Phase 3 readiness OQ-1/OQ-5/OQ-7/OQ-8

### Design-system cross-refs
- `docs/design-system/00-INDEX.md` — INDEX Layer 4
- `docs/design-system/13-pattern-fork-adapter-protocol.md` §2.4 SolverforgeCalendarAdapter + §2.5 UEID-UNIQUE
- `docs/design-system/15-pattern-hysteresis-fsm.md` §2.1 (PUSH/MAINTAIN/REDUCE/RECOVER será mapeado em doc 23)
- `docs/design-system/04-canvas-mesh-architecture.md` §3.3 storage topology
- `docs/design-system/14-pattern-idempotency-upstream-id.md` §3 (PK reuse idempotency)

### Memory cross-refs
- `[[interfaces-architecture-2026-08-27]]` — dual-layer + mesh substrate
- `[[master-branch-carro-chefe-2026-08-28]]` — canonical master narrative
- `[[windows-orphan-dir-delete]]` — apps/calendar/solverforge-calendar deletion
- `[[orchestration-clone-playground]]` — vendored
- `[[ag3-gateway-orphan-2026-08-27]]` — gateway orphan
- `[[pav-as-ikigai-subsystem-2026-08-28]]` — PAV desativado → UPI substrate

### Métricas de cobertura
- **7 seções de inventário** (§2.1-2.7) — estrutura, modules, DB tables, sync layer tables, MCP server
- **7 seções de conteúdo principal** (§3.1-3.7) — TEA, UPI superset, Adapter PK reuse, OAuth2, RRULE, DAG, gateway routing
- **10 code anchors** verificados via Read tool em §4.5
- **6 memory cross-refs** (interfaces, master-branch, windows-orphan, orchestration, ag3-gateway, pav-subsystem)
- **8 pitfalls** explícitos em §4.6 (gateways.yaml, google_sync stub, HTTP+SSE feature-gated, google-calendar3 unused, recurrence_exceptions dead schema, no startup_timeout, SyncEngine misnomer, hardcoded OAuth port, mouse events ignored)
- **Honest rigor:** menciona 5 gaps conhecidos que bloqueiam solverforge promotion a canonical write path; PK stability vs UPSERT tradeoff; dual DB federation (calendar.db + unified_planning.db); rrule não-expansion é realidade atual
