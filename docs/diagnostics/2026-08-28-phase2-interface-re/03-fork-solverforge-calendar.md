# Fork Reverse-Engineering — `solverforge-calendar`

**Date:** 2026-08-28
**Source:** `C:/Users/mathe/code_space/life-oss/interfaces/solverforge-calendar/`
**Phase:** 2 of `2026-08-28-interface-re`
**Mode:** Reverse-engineering only (no patches, no design proposals)
**Crate:** `solverforge-calendar` v0.3.0 (edition 2021)
**Total Rust LOC in `src/`:** 11,649 lines across 30 files

---

## Module map

Crate re-exports `src/lib.rs:1-20` flat — every public module is sibling-level (no nested namespace):

| Module | File | Lines | Role |
|---|---|---|---|
| `app` | `src/app.rs` | ~370+ | TEA-style `App` state (running flag, view, focused_date, calendars, events, dependencies, DAG, completed set, sidebar focus, form state, status) |
| `calendar_service` | `src/calendar_service.rs` | ~250+ | Validated CRUD over `Calendar` with `CalendarServiceError { NotFound, Validation, Conflict, Internal }` |
| `cli` | `src/cli.rs` | 700+ | clap derive — `Calendars / Projects / Events / Dependencies / Google` subcommands, JSON-first `--json` output |
| `dag` | `src/dag.rs` | 200+ | `EventDag` (forward `edges`, reverse `reverse` HashMaps); Kahn-style topological sort, cycle detection in `add_edge` |
| `db` | `src/db.rs` | 1,267 | rusqlite schema v1+v2, CRUD, UPI helpers, sync_token mgmt, 12 unit tests in `mod tests` |
| `event` | `src/event.rs` | — | `Event` enum (`Key` / `Mouse` / `Resize` / `Tick`) + `EventHandler` with 250 ms tick |
| `google` (mod) | `src/google/mod.rs:1-4` | 4 | Aggregates `auth / discovery / sync / types` |
| `google::auth` | `src/google/auth.rs` | 223 | OAuth2 loopback flow on `127.0.0.1:8989`, keyring storage, refresh-token exchange |
| `google::discovery` | `src/google/discovery.rs` | 195 | `discover_calendars()` → `calendarList?maxResults=250` paginated |
| `google::sync` | `src/google/sync.rs` | 518 | Sync delta application, paginated `events.list`, soft-delete on `status=cancelled` |
| `google::types` | `src/google/types.rs` | 80 | `google_event_to_local(calendar_id, gev)` RFC 3339 → storage format |
| `ical` | `src/ical.rs` | 60+ | `icalendar` 0.17 export (RRULE, all-day DTSTART;VALUE=DATE) |
| `keys` | `src/keys.rs` | 311 | `View` + `Action` enums, `resolve(view, key)` → Action, `hints(view)` → status bar |
| `models` | `src/models.rs` | 171 | `Calendar` / `Project` / `Event` / `EventDependency` structs |
| `models_unified` | `src/models_unified.rs` | — | `UnifiedPlanningItem`, `Dependency`, `IkigaiVectors`, `Provenance`, `TimeBlock` (sync layer) |
| `notifications` | `src/notifications.rs` | 83 | Desktop reminder task via `notify-rust` (D-Bus on Linux, "z" feature) |
| `observability` | `src/observability.rs` | 140 | OpenTelemetry init (LangSmith + Langfuse dual exporters, gated by env vars) |
| `recurrence` | `src/recurrence.rs` | 43 | UI-only `RecurrencePreset` enum (None / Daily / Weekdays / etc.) — wraps rrule 0.14 at the form layer |
| `sync` (mod) | `src/sync/mod.rs:1-9` | 116 | `SyncEngine` aggregating tuiboard / solverforge / taskdog counts |
| `sync::migrations` | `src/sync/migrations.rs` | 74 | CREATE TABLE for `unified_planning_items / sync_map / wikilink_resolution_log / sync_conflicts` |
| `sync::tuiboard_parser` | `src/sync/tuiboard_parser.rs` | 604 | `BoardCardDelta` parser — reads tuiboard markdown, extracts wikilinks |
| `sync::tuiboard_transformer` | `src/sync/tuiboard_transformer.rs` | 383 | `BoardCardDelta → UnifiedPlanningItem` with warnings |
| `sync::tuiboard_writer` | `src/sync/tuiboard_writer.rs` | 549 | UPSERT + 4-strategy wikilink resolver (`board:`, `::`, title, tag) |
| `theme` | `src/theme.rs` | 320 | Color tokens (`#82FB9C` primary, `#0B0C16` background) |
| `ui` (mod) | `src/ui/mod.rs:13-23` | 96 | Top-level render dispatcher: header (1 row) + sidebar (22 cols) + status (1 row) + content |
| `ui::*` | `src/ui/{month,week,day,agenda,calendar_list,event_form,quick_add,google_auth,help,status_bar,util}.rs` | 36–296 each | Per-view ratatui renderers |
| `worker` | `src/worker.rs` | 231 | Background worker returning `WorkerResult` |

**Bin targets** (`Cargo.toml:86-88`):

| Bin | Path | Role |
|---|---|---|
| `solverforge-calendar` (default) | `src/main.rs` | TUI (tokio runtime, crossterm, ratatui) |
| `solverforge-calendar-cli` | `src/bin/solverforge-calendar-cli.rs` | Clap CLI, 40 lines wrapper |
| `solverforge-calendar-mcp` | `src/bin/solverforge-calendar-mcp.rs` | **MCP server (rmcp 3.1, dual transport stdio + HTTP+SSE)** — 963 lines |

---

## Domain entities + rusqlite schema

`src/db.rs:90-189` defines migration v1 (timestamp `20260101000001`) and `src/db.rs:191-208` migration v2 (timestamp `20260406000001`). Migration runner is Rails-compatible via `schema_migrations(version TEXT PRIMARY KEY)` rows (`src/db.rs:52-69`).

### Tables (migration v1)

| Table | Key columns | Notable indexes / constraints |
|---|---|---|
| `calendars` (`db.rs:94-105`) | `id PK` (UUID v4), `name`, `color` (hex), `source` (`local` / `google`), `google_id`, `visible INTEGER`, `position INTEGER`, `created_at / updated_at / deleted_at` (soft-delete) | `idx_calendars_google_id_unique` (`db.rs:194-198`) UNIQUE on `(google_id) WHERE deleted_at IS NULL AND source='google' AND google_id IS NOT NULL` |
| `projects` (`db.rs:108-116`) | `id PK`, `name`, `color`, `description?`, timestamps + `deleted_at` | — |
| `events` (`db.rs:119-137`) | `id PK`, `calendar_id FK→calendars`, `project_id FK→projects`, `title`, `description?`, `location?`, `start_at / end_at` (`%Y-%m-%d %H:%M:%S`), `all_day INTEGER`, **`rrule?` RFC 5545 string**, `google_id?`, `google_etag?`, `reminder_minutes?`, `timezone` (default `'UTC'`), timestamps + `deleted_at` | `idx_events_calendar_id`, `idx_events_project_id`, `idx_events_start_at`, `idx_events_end_at`, `idx_events_google_id` (partial WHERE google_id IS NOT NULL), `idx_events_calendar_google_id_unique` UNIQUE on `(calendar_id, google_id) WHERE deleted_at IS NULL AND google_id IS NOT NULL` (`db.rs:200-203`) |
| `event_dependencies` (`db.rs:149-157`) | `id PK`, `from_event_id FK→events ON DELETE CASCADE`, `to_event_id FK→events ON DELETE CASCADE`, `dependency_type` (`blocks` / `related`), timestamps | `UNIQUE(from_event_id, to_event_id)`, `idx_event_deps_from`, `idx_event_deps_to` |
| `recurrence_exceptions` (`db.rs:164-171`) | `id PK`, `event_id FK→events CASCADE`, `original_start`, `replacement_event_id FK→events`, timestamps | `idx_recurrence_exc_event_id` |
| `sync_tokens` (`db.rs:178-184`) | `id PK`, `calendar_id FK→calendars CASCADE UNIQUE`, `sync_token`, `synced_at` | `UNIQUE(calendar_id)` |

### PRAGMAs

`src/db.rs:37-42` — `journal_mode = WAL`, `foreign_keys = ON`, `synchronous = NORMAL`.

### Domain entity struct mapping

| Entity | Struct location | Fields (excerpt) |
|---|---|---|
| `Calendar` | `src/models.rs:8-20` | id, name, color, source, google_id, visible, position, created_at, updated_at, deleted_at |
| `Project` | `src/models.rs:42-50` | id, name, color, description, timestamps |
| `Event` | `src/models.rs:56-74` | id, calendar_id, project_id, title, description, location, start_at, end_at, all_day, rrule, google_id, google_etag, reminder_minutes, **timezone**, timestamps |
| `EventDependency` | `src/models.rs:147-154` | id, from_event_id, to_event_id, dependency_type, timestamps |
| `DependencyType` | `src/models.rs:156-169` | `blocks` (default) / `related` |
| `CalendarSource` | `src/models.rs:22-36` | `local` / `google` |
| `UnifiedPlanningItem` | `src/models_unified.rs` | UPI = superset with status, time_block, ikigai, provenance, blocked_by, tags — JSON-encoded columns in `unified_planning_items` (sync store) |

### Sync layer (separate `unified_planning.db`)

`src/sync/migrations.rs:16-72` — table created by `migrations::run_migrations()`:
- `unified_planning_items` (id, title, description, status, all_day, start_at, end_at, **time_block JSON**, calendar_id, project_id, **ikigai JSON**, **provenance JSON**, **blocked_by JSON**, **tags JSON**, rrule, timestamps)
- `sync_map` (PRIMARY KEY (system, board_card_id)) — wikilink bridge
- `wikilink_resolution_log`
- `sync_conflicts`

Indexes: `idx_upi_start_at`, `idx_upi_status`, `idx_upi_deleted_at`, `idx_upi_provenance_sys` (JSON path).

### DB path resolution

`src/db.rs:14-19`: `$SOLVERFORGE_DATA_DIR/solverforge/calendar.db` override, otherwise `dirs::data_dir()/solverforge/calendar.db` (e.g. `%APPDATA%/solverforge` on Windows). Comment at `src/db.rs:9-13` explicitly cites IKIGAI persona vault target `life-ops/ikigai/data/matheus/.runtime/`.

### Recurring-event persistence

`recurrence_exceptions` table (`db.rs:164-171`) stores per-occurrence overrides (modify or delete via `replacement_event_id NULL`).

---

## google-calendar3 integration surface

**Dependency:** `google-calendar3 = "7.0"` (`Cargo.toml:33`) — installed but NOT directly imported by solverforge-calendar. Instead, the crate uses `reqwest` 0.12 directly against the Google Calendar REST API (`src/google/auth.rs:55-68`, `src/google/discovery.rs:22-66`, `src/google/sync.rs:91-149`).

### Why google-calendar3 is in `Cargo.toml` but unused

The crate is declared for the transitive dependency on `yup-oauth2` (per `Cargo.toml:32` comment) and may be reserved for future Hub-based flow. Current implementation hand-rolls OAuth + REST calls.

### OAuth2 flow (`src/google/auth.rs`)

| Step | Location | Detail |
|---|---|---|
| 1. Build auth URL | `auth.rs:103-114` | `https://accounts.google.com/o/oauth2/v2/auth?scope=https://www.googleapis.com/auth/calendar&access_type=offline&prompt=consent` |
| 2. Open browser | `auth.rs:117` | `open::that(auth_url)` |
| 3. Loopback listener | `auth.rs:120-138` | `TcpListener::bind("127.0.0.1:8989")`, reads first request line, extracts `code=` query param, writes success HTML |
| 4. Exchange code → refresh_token | `auth.rs:162-186` | POST to `https://oauth2.googleapis.com/token` with `grant_type=authorization_code` |
| 5. Persist | `auth.rs:86-88` | `GoogleClient::save_credentials()` + `save_refresh_token()` to keyring |
| Refresh access token | `auth.rs:47-69` | POST `oauth2.googleapis.com/token` with `grant_type=refresh_token` |

### REST surface used

| Endpoint | Location | Purpose |
|---|---|---|
| `GET https://www.googleapis.com/calendar/v3/users/me/calendarList?maxResults=250` | `src/google/discovery.rs:23` | List user's Google calendars |
| `GET https://www.googleapis.com/calendar/v3/calendars/{id}/events?maxResults=2500&singleEvents=true[&syncToken=...][&timeMin=...][&pageToken=...]` | `src/google/sync.rs:97-150` | Paginated event fetch with sync-token incremental sync |

`google_event_to_local()` (`src/google/types.rs:6-67`) maps each `serde_json::Value` event into the local `Event` struct, handling both `dateTime` (RFC 3339) and `date` (all-day) start/end formats, extracting RRULE from the `recurrence[]` array (only the entry starting with `"RRULE:"`), and timezone fallback to `"UTC"`.

### Sync application (`src/google/sync.rs:42-89`)

- Skips `status: "cancelled"` → soft-deletes by `(calendar_id, google_id)`
- For others: looks up by `(calendar_id, google_id)`, updates if exists, inserts if new
- Persists `nextSyncToken` on last page (`db::upsert_sync_token` at `db.rs:773-783`)

### HTTP dependency note

`google-calendar3 7.0` bundles `yup-oauth2 + hyper + rustls` (`Cargo.toml:32` comment), but solverforge-calendar does NOT use any of these directly — it uses its own `reqwest` 0.12 client. This is a dead dependency adding compile time.

---

## MCP tool inventory

**Source:** `src/bin/solverforge-calendar-mcp.rs` (963 lines).
**Server core:** `McpServer` struct at `solverforge-calendar-mcp.rs:34-48` — wraps `Arc<SyncMutex<rusqlite::Connection>>` (single-threaded DB access).
**Tool routing:** `#[tool_router(router = tool_router)]` at `solverforge-calendar-mcp.rs:268-269` + `#[tool_handler(router = self.tool_router)]` at `solverforge-calendar-mcp.rs:265-266`.
**rmcp 3.1** with features `["server", "macros", "transport-io", "schemars"]` (`Cargo.toml:63`).
**MCP protocol version:** `"2024-11-05"` (`solverforge-calendar-mcp.rs:30`).

### Tool catalog (30 tools)

| Tool | Line | Args | Notes |
|---|---|---|---|
| `calendars_list` | 272 | — | All active calendars |
| `calendars_get` | 288 | `id` | — |
| `calendars_create` | 305 | `name`, `color`, `source?`, `visible?`, `position?` | Generates UUID v4 |
| `calendars_update` | 338 | `id`, optional fields | PATCH semantics |
| `calendars_delete` | 373 | `id`, `cascade_events?` | Soft-delete (param currently ignored) |
| `projects_list` | 391 | — | — |
| `projects_get` | 407 | `id` | — |
| `projects_create` | 424 | `name`, `color`, `description?` | — |
| `projects_update` | 450 | `id`, optional fields | — |
| `projects_delete` | 482 | `id`, `detach_events?` | Soft-delete |
| `events_list` | 500 | `from?`, `to?` (datetime strings) | Date-range filter optional |
| `events_get` | 521 | `id` | — |
| `events_create` | 538 | `calendar_id`, `title`, `start_at`, `end_at`, `timezone?` (default `"UTC"`), project_id/description/location/all_day/rrule/reminder_minutes? | Full create |
| `events_update` | 574 | `id`, optional fields with explicit `clear_*` flags (`clear_project_id`, `clear_description`, `clear_location`, `clear_rrule`, `clear_reminder_minutes`) | Distinguishes "leave alone" vs "set to null" |
| `events_delete` | 636 | `id` | Soft-delete + cascades to dependencies |
| `dependencies_list` | 654 | — | — |
| `dependencies_get` | 670 | `id` | — |
| `dependencies_create` | 687 | `from_event_id`, `to_event_id`, `dependency_type?` (default `"blocks"`) | — |
| `dependencies_update` | 716 | `id`, optional fields | — |
| `dependencies_delete` | 751 | `id` | Hard-delete |
| `google_sync` | 769 | `calendar_id?` | **STUB** — returns `{"status": "not_implemented", "message": "Google sync not yet implemented via MCP"}` (line 773) |
| `upi_sync` | 778 | `boards_dir?` | Full tuiboard→UPI pipeline: read deltas, write to `unified_planning.db` |
| `upi_list` | 805 | `limit`, `offset?` | Pagination |
| `upi_get` | 823 | `id` | — |
| `upi_update` | 840 | `id`, `status?` | Status change only (`pending`/`in_progress`/`done`/`blocked`/`cancelled`) |
| `upi_search` | 858 | `query`, `limit` | Title `LIKE '%query%'` (no FTS) |

### Transport handling (`solverforge-calendar-mcp.rs:878-905`)

```rust
let transport = std::env::var("SOLVERFORGE_MCP_TRANSPORT").unwrap_or_else(|_| "stdio".to_string());
match transport.as_str() {
    "stdio" | "" => run_stdio_server().await?,    // line 888 — default
    #[cfg(feature = "http")] "http" => run_http_server().await?,
    #[cfg(not(feature = "http"))] "http" => { eprintln!("HTTP transport requires --features http"); std::process::exit(1); }
    _ => { eprintln!("Unknown transport..."); std::process::exit(1); }
}
```

- **`run_stdio_server`** (line 907-911): `McpServer::new()?.serve(rmcp::transport::stdio()).await` — instantiates DB, hands to rmcp stdio transport.
- **`run_http_server`** (line 916-958, gated behind `feature = "http"`): axum router on `$SOLVERFORGE_MCP_HTTP_HOST:$SOLVERFORGE_MCP_HTTP_PORT` (defaults `127.0.0.1:3737`), exposes `/health`. **STUB INCOMPLETE**: declares broadcast `tx` channel but never wires SSE — only health endpoint works; comment at line 914 says "TODO: Implement HTTP+SSE transport using rmcp's built-in StreamableHttpService". Note: the `http` feature is NOT in `Cargo.toml` features list, so this branch is always compile-gated out — runtime `http` transport fails with exit 1.

### Error handling

`CallToolResult` errors use `ErrorData::new(ErrorCode::INTERNAL_ERROR, e.to_string(), None)` (e.g. line 282) for `db::` failures and `ErrorData::new(ErrorCode::RESOURCE_NOT_FOUND, Cow::Borrowed("X not found"), None)` (line 348) for missing records. `ErrorCode::INVALID_PARAMS` used at line 851. No structured logging of tool errors beyond `#[instrument]` tracing spans.

### Observability

`solverforge-calendar-mcp.rs:881` — `observability::init_observability()` runs first. Per `observability.rs`, this is gated on `OTEL_ENABLED=true` + either `LANGSMITH_API_KEY` or `LANGFUSE_PUBLIC_KEY+LANGFUSE_SECRET_KEY` (defaults to no-op).

---

## Gateway routing match matrix

**Gateway config:** `C:/Users/mathe/code_space/apps/mcp-gateway/config/gateways.yaml:12-15` declares:
```yaml
  - name: solverforge-calendar
    command: ["cargo", "run", "--bin", "solverforge-calendar-mcp"]
    cwd: "C:/Users/mathe/code_space/apps/calendar/solverforge-calendar"   # ← STALE PATH (B-01)
    tool_prefixes: ["calendars_", "events_", "projects_", "dependencies_", "google_", "upi_"]
```

**Actual tool prefix inventory from MCP source (`src/bin/solverforge-calendar-mcp.rs`):**

| Prefix | Tools exposed | Gateway expects? | Status |
|---|---|---|---|
| `calendars_` | `calendars_list`, `calendars_get`, `calendars_create`, `calendars_update`, `calendars_delete` (5) | YES | Match |
| `events_` | `events_list`, `events_get`, `events_create`, `events_update`, `events_delete` (5) | YES | Match |
| `projects_` | `projects_list`, `projects_get`, `projects_create`, `projects_update`, `projects_delete` (5) | YES | Match |
| `dependencies_` | `dependencies_list`, `dependencies_get`, `dependencies_create`, `dependencies_update`, `dependencies_delete` (5) | YES | Match |
| `google_` | `google_sync` (1) | YES | Match — but the tool is a **stub** (returns `not_implemented` per line 773) |
| `upi_` | `upi_list`, `upi_get`, `upi_update`, `upi_search`, `upi_sync` (5) | YES | Match |

**All 6 prefixes are exposed** (5 fully wired + 1 stubbed `google_sync`). The gateway routing table matches the implementation. **Caveats:**

1. **`google_sync` is a stub** — clients calling it will get `{"status": "not_implemented"}`. Real sync logic lives in `src/google/sync.rs` but is only invoked via the CLI subcommand (`src/cli.rs` Google subcommand), not via MCP.
2. **`google_*` prefix is too narrow** — gateway reserves the prefix, so adding `google_calendar_list`, `google_discover`, etc. as future tools would still be routed correctly, but adding `gcal_*` would NOT.
3. **Path is stale** — per Phase 1 audit B-01 (`2026-08-28-phase1-audit/01-verified.md:9-15`), the `cwd` references the pre-reorg location. The actual binary lives at `C:/Users/mathe/code_space/life-oss/interfaces/solverforge-calendar/`. Without repointing, gateway cannot spawn the MCP server.
4. **No retry/timeout policy** — `gateways.yaml:13` uses `cargo run` which is slow on cold start (~30-60 s first build, ~5 s incremental). No `startup_timeout` declared.

---

## TUI widgets + ratatui keybindings

**Layout** (`src/ui/mod.rs:34-96`):
- **Header bar** — `Constraint::Length(1)`, renders `SolverForge Calendar` title via `status_bar::render_header`
- **Main body** — horizontal split: sidebar (`Length(22)`) + content (`Fill(1)`)
- **Sidebar (always visible)** — `calendar_list::render_calendar_list` showing calendar+project tree
- **Content (per view)** — `month_view / week_view / day_view / agenda_view`, or month view as backdrop for `EventForm / QuickAdd / Help / GoogleAuth`
- **Status bar** — `Length(1)`, `status_bar::render_status_bar` (default) or `quick_add::render_quick_add` for QuickAdd view
- **Overlays** — `event_form / help / google_auth` popup renderers

### View widgets (per `src/ui/mod.rs:55-81`)

| View | Renderer | Source LOC | Notes |
|---|---|---|---|
| Month | `month_view::render_month` | 220 | Calendar grid with day cells |
| Week | `week_view::render_week` | 296 | Time-grid with `week_scroll` offset |
| Day | `day_view::render_day` | 141 | Single-day hour grid |
| Agenda | `agenda_view::render_agenda` | 155 | Scrollable list of events |
| CalendarList (sidebar) | `calendar_list::render_calendar_list` | 159 | Calendar+project toggles |
| EventForm | `event_form::render_event_form` | 159 | 11 fields (Title, Date, Start, End, AllDay, Calendar, Location, Description, Recurrence, Reminder, Project — `app.rs:14-26`) |
| QuickAdd | `quick_add::render_quick_add` | 36 | Single-line input |
| Help | `help::render_help` | 123 | Keybinding reference |
| GoogleAuth | `google_auth::render_google_auth` | 128 | OAuth flow form |
| StatusBar | `status_bar::render_status_bar` | 113 | Hints + status |
| Util | `ui::util` | 105 | Render helpers |

### Keybindings (`src/keys.rs`)

**Global (any view):** `Ctrl+C` / `Ctrl+Q` → `Quit` (line 91-94). `Tab` → `FocusSidebar` from main views (line 120, 151, 179).

**Per-view dispatch table (`src/keys.rs:98-108`):**

| View | Dispatch |
|---|---|
| Month | `resolve_month` (line 111-140) |
| Week / Day | `resolve_time_grid` (line 142-168) |
| Agenda | `resolve_agenda` (line 170-193) |
| CalendarList | `resolve_calendar_list` (line 195-208) |
| EventForm | `resolve_event_form` (line 210-221) |
| QuickAdd | `resolve_input` (line 223-232) |
| Help | `resolve_help` (line 234-244) |
| GoogleAuth | `resolve_google_auth` (line 246-257) |

**Common shortcuts:**

| Key | Action | Views |
|---|---|---|
| `1` / `2` / `3` / `4` | ViewMonth / ViewWeek / ViewDay / ViewAgenda | All (except overlays) |
| `h` / `l` (or ← / →) | PrevDay / NextDay (Month) **or** PrevPeriod / NextPeriod (Week/Day) | main views |
| `H` / `L` | PrevPeriod / NextPeriod | Month |
| `j` / `k` (or ↑ / ↓) | NextUnit / PrevUnit | Month + Week/Day |
| `n` | JumpToday | All main views |
| `g` | JumpToDate | Month |
| `c` | CreateEvent | All main + CalendarList |
| `e` | EditEvent | All main |
| `d` | DeleteEvent | All main |
| `Enter` | SelectEvent | All main |
| `/` | QuickAdd | Month + Week/Day + Agenda |
| `G` / `S` | GoogleSync | All (including CalendarList) |
| `i` / `x` | ImportIcal / ExportIcal | Month only |
| Esc | Escape / Cancel | All |
| `Tab` / `Shift+Tab` | FormNextField / FormPrevField | EventForm + GoogleAuth |
| `?` | Help | All main + CalendarList |
| `Space` | ToggleCalendar | CalendarList |

**Form overlay controls:** `Enter` submits, `Esc` cancels, `Tab`/`Shift+Tab` navigate fields, char input via `InputChar`.

### Hint strings (`src/keys.rs:265-310`)

Per-view hint tuple vectors drive `status_bar::render_status_bar`. Examples:
- Month: `("h/l", "day"), ("H/L", "month"), ("j/k", "row"), ("n", "today"), ("c", "create"), ("e", "edit"), ("d", "del"), ("1-4", "view"), ("Tab", "sidebar"), ("?", "help")`
- Week/Day: `("h/l", "week"), ("j/k", "event"), ("n", "now"), ...`
- Agenda: `("j/k", "scroll"), ...`
- CalendarList: `("j/k", "nav"), ("Space", "toggle"), ("Tab", "main"), ("?", "help")`

### Event loop

`src/main.rs:42-74` — tokio runtime wraps a blocking `loop { terminal.draw(...); events.next() }` with `EventHandler` ticking at 250 ms (`main.rs:52`). Mouse events captured but ignored (`main.rs:61-63`). Resize handled implicitly by ratatui.

---

## rrule + keyring usage

### rrule 0.14

**Cargo.toml:30** — `rrule = { version = "0.14", features = ["serde"] }`.

**Direct usage in Rust source: NONE for expansion.** The crate is wired up via the form layer (`recurrence.rs:1-43`) which exposes `RecurrencePreset` (None / Daily / WeeklyOnDay / Weekdays / Weekly / BiWeekly / Monthly / Yearly / Custom(String)) but does not import `rrule` itself. **RRULE storage** is purely as a string column in `events.rrule` (`db.rs:129`, `models.rs:66`).

**Where rrule strings come from:**
1. `Event::new()` builder (`models.rs:77-104`) — sets `rrule: None` initially.
2. `EventCreateInput` MCP input (`solverforge-calendar-mcp.rs:128-148`) — accepts `rrule: Option<String>` as raw RFC 5545 string.
3. `google_event_to_local()` (`src/google/types.rs:37-44`) — parses the `recurrence[]` JSON array from Google Calendar API, finds the first entry starting with `"RRULE:"`, stores as-is.
4. `ical::export_events` (`src/ical.rs:46-48`) — strips `"RRULE:"` prefix before writing.

**Expansion into individual occurrences is NOT implemented** — the UI uses `rrule: Option<String>` only for display/export; recurring event instances are not auto-generated. The `recurrence_exceptions` table (`db.rs:164-171`) is defined but has no read/write helpers in `db.rs` (no `insert_recurrence_exception` / `load_recurrence_exceptions` exposed). Dead schema for now.

### keyring 3

**Cargo.toml:45** — `keyring = { version = "3", features = ["sync-secret-service", "crypto-rust"] }`.

**Usage is concentrated in `src/google/auth.rs`:**

| Function | Line | What |
|---|---|---|
| `GoogleClient::from_keyring()` | `auth.rs:20-29` | Reads `google_client_id`, `google_client_secret`, `google_refresh_token` |
| `GoogleClient::is_configured()` | `auth.rs:32-34` | Tests `google_refresh_token` |
| `GoogleClient::save_credentials()` | `auth.rs:37-41` | Stores client_id + client_secret |
| `GoogleClient::save_refresh_token()` | `auth.rs:43-45` | Stores refresh_token |
| `read_keyring()` | `auth.rs:72-74` | Helper — `Entry::new("solverforge-calendar", key).get_password()` |
| `write_keyring()` | `auth.rs:76-81` | Helper — `Entry::new(...).set_password(value)` |
| `authorize_and_persist()` | `auth.rs:85-94` | Orchestrates OAuth flow + keyring save |

**Service name:** `"solverforge-calendar"` (`auth.rs:4`) — unique per fork, no collision with tuiboard/taskdog keyring entries.

**Key namespace:** `google_client_id` / `google_client_secret` / `google_refresh_token` (`auth.rs:5-7`).

**Platform note:** features `sync-secret-service` (Linux) + `crypto-rust` (cross-platform encryption). The `windows-native` feature is NOT enabled — meaning keyring access on Windows likely uses the file-based mock backend unless the user has a credential manager installed.

**Access tokens are NOT persisted to keyring** — only refresh tokens. Access tokens are obtained on demand by calling `refresh_access_token()` (`auth.rs:47-69`), then used as `Bearer` tokens in `reqwest` calls (`google/sync.rs:109`, `google/discovery.rs:31`).

---

## Trade-offs

| Decision | Pros | Cons |
|---|---|---|
| **Single `Arc<SyncMutex<Connection>>` in MCP** (`mcp.rs:36`) | Simple, no race conditions, deterministic queries | All DB ops serialized — single tool call at a time; `tokio::task::spawn_blocking` per call (line 276) means overhead per tool invocation |
| **`google-calendar3` declared but unused** (`Cargo.toml:33`) | Available for future Hub-based flow; provides `yup-oauth2` for typed OAuth | Wastes compile time (~15-20s incremental); uses `reqwest` directly anyway, hand-rolling OAuth at `auth.rs:96-186` instead of using `yup-oauth2`'s `Authenticator` |
| **Per-occurrence override table without expansion** (`recurrence_exceptions` table defined, no helpers) | Schema ready for full recurrence handling | Useless without rrule expansion in app logic; iCal export sends RRULE but no client can materialize instances |
| **Loopback OAuth on hardcoded port 8989** (`auth.rs:120-121`) | No public callback needed, works on any desktop | Port conflict if another app binds 8989; no fallback; Windows firewall may block on first run |
| **HTTP+SSE transport is feature-gated stub** (`mcp.rs:916-958`) | Keeps stdio as canonical path, axum wiring scaffolded | The `http` feature is not in `Cargo.toml`, so the branch is always dead code at compile time; runtime `http` choice exits with error; `HttpState.tx` channel unused |
| **Two PRAGMA-style upserts + soft-delete only** (`db.rs:329-393, 514-521, 593-600`) | Reversible deletes; minimal schema churn | `sync_tokens`, `projects`, `events` accumulate over time; no vacuum strategy |
| **Migration IDs are timestamps not sequential** (`db.rs:6-7` `20260101000001`, `20260406000001`) | Rails-compatible format | Two-digit precision — two migrations within the same second would collide; no foreign-key drop policy documented |
| **Single `cli.rs` clap derive module + 1-bin wrapper** (`cli.rs:1-80`) | One source of truth for CLI/MCP parity | The CLI duplicates MCP tool logic — `calendars_create`/`projects_create`/etc. exist in both `cli.rs` and `mcp.rs` |
| **`SyncEngine` aggregates counts but doesn't actually poll** (`sync/mod.rs:34-89`) | Schema migration runs, status queryable | "Sync" is a misnomer — counts are pulled from the local DB, not from external systems (tuiboard / solverforge / taskdog). Polling would require the parser/writer glue code currently only wired via MCP `upi_sync` tool |
| **No FTS for `upi_search`** (`db.rs:947-960` line 953 `title LIKE '%' || ?1 || '%'`) | Trivial, no schema | O(n) per search; degrades with size |
| **Async-unsafe `SyncMutex` (std::sync::Mutex)** (`mcp.rs:36`) | Less overhead than `tokio::sync::Mutex` for short critical sections | Holding across `.await` would deadlock; correct only because `spawn_blocking` is used everywhere (verified in all tool impls) |
| **`open` crate for browser launch** (`Cargo.toml:59`, `auth.rs:117`) | Cross-platform (xdg-open / open / start) | Blocks until browser opens; no error if user cancels |

---

## Cross-references

### Inputs read
- Phase 1 forensic audit: `life/docs/diagnostics/2026-08-28-phase1-audit/00-INDEX.md`, `01-verified.md`, `02-critic-gaps.md`, `05-open-questions.md`
- Gateway routing config: `C:/Users/mathe/code_space/apps/mcp-gateway/config/gateways.yaml`
- Crate manifest: `interfaces/solverforge-calendar/Cargo.toml`
- Library re-exports: `interfaces/solverforge-calendar/src/lib.rs`
- Domain models: `interfaces/solverforge-calendar/src/models.rs`, `src/models_unified.rs`
- Persistence: `interfaces/solverforge-calendar/src/db.rs` (1,267 LOC) + `src/sync/migrations.rs` (74 LOC)
- MCP server: `interfaces/solverforge-calendar/src/bin/solverforge-calendar-mcp.rs` (963 LOC)
- Google integration: `interfaces/solverforge-calendar/src/google/{mod,auth,discovery,sync,types}.rs`
- TUI: `interfaces/solverforge-calendar/src/ui/{mod,month_view,week_view,day_view,agenda_view,calendar_list,event_form,quick_add,google_auth,help,status_bar}.rs` + `src/keys.rs`
- Sync layer: `interfaces/solverforge-calendar/src/sync/{mod,tuiboard_parser,tuiboard_transformer,tuiboard_writer}.rs`

### Open issues uncovered (NOT addressed here — Phase 3 input)
- **`google_sync` MCP tool is a stub** at `mcp.rs:769-774` — returns `not_implemented` despite real sync logic in `src/google/sync.rs`. The `google_*` prefix is registered with the gateway but currently points at a no-op.
- **HTTP+SSE transport is feature-gated out** at `mcp.rs:894-898` — `cargo build --features http` would never compile since the feature is not in `Cargo.toml` features list.
- **`google-calendar3 7.0` dependency is unused** at `Cargo.toml:33` — adds compile time and ships `yup-oauth2` which the code does not consume.
- **`recurrence_exceptions` table is dead schema** at `db.rs:164-171` — no insert/read helpers in `db.rs`; rrule expansion is not implemented anywhere.
- **`gateways.yaml:14` cwd is stale** (Phase 1 B-01) — points to pre-reorg `apps/calendar/solverforge-calendar`, real location is `life-oss/interfaces/solverforge-calendar`.
- **No startup_timeout on gateway entry** at `gateways.yaml:13` — `cargo run` cold start can be 30-60 s.
- **`SyncEngine::poll` doesn't actually poll** at `sync/mod.rs:34-89` — it counts local rows with `provenance = 'X'`, not actual external system reads. The "sync" pipeline is only reachable via MCP `upi_sync` (`mcp.rs:778-803`), not via `SyncEngine`.

### Connections to Phase 2 other forks
- `tuiboard` (Phase 2 fork #1) — shares wikilink `[[…]]` semantics with solverforge-calendar's `tuiboard_writer::resolve_wikilink` (`sync/tuiboard_writer.rs:286-319`); uses identical 4-strategy resolver (explicit `board:`, position `::`, title, tag).
- `taskdog` (Phase 2 fork #2) — gateway uses same pattern of prefixed tool names (`taskdog_*`, `list_tasks`, etc.) at `gateways.yaml:8-10`.
- `interfaces/cli` (Phase 2 diagnostic #4) — broken entry-point per Phase 1 audit; solverforge-calendar sidesteps this entirely with its own `cli.rs` derive, so the broken CLI does not affect this fork.

### Connections to Phase 1 OQ items
- **OQ-1 (Storage topology)** — solverforge-calendar dual-stores: `calendar.db` (per fork) and `unified_planning.db` (sync); `$SOLVERFORGE_DATA_DIR` override exists but no documented coordination with `~/.ikigai/` or `life/data/`.
- **OQ-3 (tasks.jsonl role)** — solverforge-calendar is JSON-free on the wire (sqlite only); provides no `.jsonl` integration; would feed Phase 3 data mesh via MCP, not file.
- **OQ-8 (Two MCP transports)** — solverforge-calendar MCP has the dual stdio+HTTP transport pattern that OQ-8 contemplates, but the HTTP branch is dead code today.

---

DONE C:/Users/mathe/code_space/life-oss/life/docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md: 384 lines
