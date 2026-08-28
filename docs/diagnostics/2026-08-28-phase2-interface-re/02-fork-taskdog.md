# 02 — taskdog fork: reverse-engineering audit

**Date:** 2026-08-28
**Source fork:** `C:/Users/mathe/code_space/life-oss/interfaces/taskdog/packages/`
**Upstream:** Kohei Wada's taskdog, v0.23.0 (MIT)
**Runtime:** Python 3.11+, uv workspace (4 packages) — `taskdog-core` + `taskdog-mcp` + `taskdog-server` + `taskdog-client` + `taskdog-ui`
**MCP transport:** stdio JSON-RPC (FastMCP `mcp>=1.2.0,<2.0.0`); HTTP+WebSocket exposed by taskdog-server (FastAPI)
**Phase 1 baseline:** `docs/diagnostics/2026-08-28-phase1-audit/01-verified.md` B-01 (gateways.yaml cwd paths MISSING) + OQ-8 (two MCP transports). Fork is correctly placed under `life-oss/interfaces/taskdog/packages/` but `gateways.yaml:9` still points at the missing `apps/dev-tools/taskdog` path. Reorg executed `2026-08-28` (see memory [[windows-orphan-dir-delete]]).

---

## Package map

taskdog is a **5-package uv workspace** (`packages/`). Each has its own `pyproject.toml` at v0.23.0.

| Package | Role | Entry | Key deps |
|---------|------|-------|----------|
| **taskdog-core** | Domain + application + infrastructure + controllers (Clean Architecture, 4 layers) | `from taskdog_core.controllers import …` | SQLAlchemy 2.0, Alembic, Pydantic v2 |
| **taskdog-server** | FastAPI HTTP + WebSocket server (NOT MCP) | `taskdog_server.api.app:app` → uvicorn | FastAPI ≥0.115, uvicorn, websockets |
| **taskdog-client** | HTTP client facade (`TaskdogApiClient`) + WebSocket client | `from taskdog_client import TaskdogApiClient` | httpx ≥0.27, websockets ≥14 |
| **taskdog-mcp** | FastMCP stdio MCP server (wraps taskdog-client HTTP calls) | `python -m taskdog_mcp.main` | mcp ≥1.2,<2, taskdog-client, taskdog-core, OpenTelemetry trio |
| **taskdog-ui** | CLI (Click + LazyGroup) + Textual TUI | `taskdog` console-script | click, rich, textual ≥8.0, textual-plotext, taskdog-client, taskdog-core |

### taskdog-core layers (`packages/taskdog-core/src/taskdog_core/`) — 146 Python files

| Layer | Subpackage | Responsibility |
|-------|-----------|----------------|
| **domain** | `domain/entities/` | Pure `@dataclass` entities (`Task`, `TaskStatus` enum); `audit_log.py` |
| **domain** | `domain/repositories/` | Abstract repository interfaces (ABC) — `task_repository.py`, `audit_log_repository.py`, `notes_repository.py` |
| **domain** | `domain/services/` | Domain service interfaces — `backup_store.py`, `holiday_checker.py`, `time_provider.py` |
| **domain** | `domain/exceptions/` | Typed exception hierarchy (`TaskError`, `TaskNotFoundException`, etc.) |
| **application** | `application/dto/` | 32 Pydantic v2 DTO files (`BaseModel`, `ConfigDict`, `Field` — `task_dto.py:12`) |
| **application** | `application/use_cases/` | 19 use cases (`CreateTaskUseCase`, `StartTaskUseCase`, `OptimizeScheduleUseCase`) |
| **application** | `application/queries/` | Query/filter system (`task_query_service.py`, `filters/`, `task_filter_builder.py`) |
| **application** | `application/services/` | Domain service impls (`task_statistics_calculator`, `dependency_graph_service`, `task_status_service`) + `optimization/` with 11 strategy files (greedy, balanced, backward, priority_first, earliest_deadline, round_robin, dependency_aware, genetic, monte_carlo) |
| **application** | `application/validators/` | 6 validators (`validator_registry.py` + Status/Dependency/Datetime/NumericField/Field validators) |
| **infrastructure** | `infrastructure/persistence/database/` | SQLAlchemy 2.0 ORM + Alembic — `engine_factory.py`, `migration_runner.py`, `base_repository.py`, `models/`, `query_builders/`, `mutation_builders/`, `migrations/`, `sqlite_*_repository.py` |
| **infrastructure** | `infrastructure/persistence/mappers/` | ORM ↔ entity mapping (`task_db_mapper.py`, `tag_resolver.py`) |
| **infrastructure** | `infrastructure/holiday_checker.py`, `time_provider.py` | Domain interface impls |
| **controllers** | `controllers/` | 11 controllers — `TaskCrudController`, `TaskLifecycleController`, `TaskRelationshipController`, `TaskAnalyticsController`, `QueryController`, `NotesController`, `AuditLogController`, `BulkTaskController`, `BackupController`, `BaseTaskController` |
| **shared** | `shared/` | TOML config loader, XDG paths, date/time utils |

**Package design gap:** `controllers/__init__.py:1-13` re-exports only 4 controllers (`AuditLogController`, `BulkTaskController`, `NotesController`, `QueryController`) — the other 7 are importable via direct path but **NOT re-exported**. Downstream consumers using `from taskdog_core.controllers import …` will hit `ImportError` for the missing 7.

### taskdog-server (`packages/taskdog-server/src/taskdog_server/`) — 10 routers

`api/app.py:37-121` `create_app()` factory; lifespan inits `api_context`, `server_config`, `ConnectionManager` in `app.state`; registers 10 routers (see Server components).

### taskdog-client (`packages/taskdog-client/src/taskdog_client/`)

Re-exports 11 public symbols (`__init__.py:1-32`, incl. `TaskdogApiClient`, `WebSocketClient`, `ConnectionState`). Holds 9 specialized clients via `BaseApiClient` — `task_client.py`, `lifecycle_client.py`, `relationship_client.py`, `query_client.py`, `analytics_client.py`, `notes_client.py`, `audit_client.py`, `bulk_client.py`, `backup_client.py`. `py.typed` present (PEP 561 marker).

### taskdog-ui (`packages/taskdog-ui/src/taskdog/`)

`cli_main.py:131-200` Click `TaskdogGroup` extends `LazyGroup` (line 110) — 22 lazy subcommands (`cli_main.py:20-104`); ASCII art in `format_help` (line 113-128). CLI commands in `cli/commands/*.py` (30+ modules). Textual TUI in `tui/` (screens, widgets, services, state, commands, palette, dialogs, forms, styles).

### taskdog-mcp (`packages/taskdog-mcp/src/taskdog_mcp/`) — 12 Python files

See MCP tool inventory section below.

---

## Core entity models

### `Task` entity (`domain/entities/task.py:23-459`)

Plain `@dataclass`, **NOT Pydantic** (unlike DTOs). Fields:

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `name` | `str` | required | Validated non-empty, ≤MAX_TASK_NAME_LENGTH |
| `priority` | `int \| None` | None | >MIN_PRIORITY_EXCLUSIVE (must be positive when set) |
| `id` | `int \| None` | None | Auto-assigned by repo |
| `status` | `TaskStatus` | PENDING | Enum PENDING/IN_PROGRESS/COMPLETED/CANCELED (`task.py:16-20`) |
| `created_at`, `updated_at` | `datetime` | now() | Auto-managed |
| `planned_start`, `planned_end` | `datetime \| None` | None | Scheduler output |
| `deadline` | `datetime \| None` | None | Hard due date |
| `actual_start`, `actual_end` | `datetime \| None` | None | Recorded on lifecycle events |
| `actual_duration` | `float \| None` | None | Explicit hours; overrides calc |
| `estimated_duration` | `float \| None` | None | Required for scheduling |
| `daily_allocations` | `dict[date, float]` | {} | **MIGRATED** to normalized table in m006 |
| `depends_on` | `list[int]` | [] | JSON TEXT in DB |
| `is_fixed` | `bool` | False | Protected from optimizer |
| `tags` | `list[str]` | [] | Validated: non-empty, unique, ≤MAX_TAGS_PER_TASK, ≤MAX_TAG_LENGTH each |
| `is_archived` | `bool` | False | Soft-delete flag (2025-10-31 design: archive preserves status) |

**Invariants** enforced in `__post_init__` (`task.py:79-132`): `_validate_name`, `_validate_priority`, `_validate_durations`, `_validate_tags`. All raise `TaskValidationError`.

**Computed properties:** `actual_duration_hours` (`task.py:134-154`, priority explicit→calc→None), `is_active`, `is_finished`, `can_be_modified`.

**State machine** (`task.py:278-351`): `start(timestamp)`, `complete(timestamp)`, `cancel(timestamp)`, `pause()`, `reopen()`, `fix_actual_times(...)` with Ellipsis sentinel pattern (`task.py:353-409`) for partial updates.

**Schedulability logic** (`task.py:185-231`): `is_schedulable(force_override)`, `get_unschedulable_reason()`, `validate_schedulable()` (raises `TaskNotSchedulableError`).

### Other entities
- `audit_log.py` — audit log entity
- `NoteModel` — DB-backed notes (no domain entity file; notes go directly through ORM)

### DTOs (Pydantic v2)

`task_dto.py:12` confirms `from pydantic import BaseModel, ConfigDict, Field`. **32 DTO files** under `application/dto/` — `create_task_input.py`, `update_task_input.py`, `task_operation_output.py`, `task_update_output.py`, `task_dto.py`, `task_detail_output.py`, `restore_result.py`, `bulk_operation_output.py`, `optimize_schedule_input.py`, `gantt_overlay.py`, etc.

### Exception hierarchy (`domain/exceptions/task_exceptions.py`)

```
TaskError (base)
├── TaskNotFoundException(task_id)
├── TaskValidationError
│   ├── TaskAlreadyFinishedError / TaskAlreadyInProgressError / TaskNotStartedError
│   ├── DependencyNotMetError / TaskNotSchedulableError / NoSchedulableTasksError
├── ServerConnectionError(base_url, original_error)
├── AuthenticationError(message)
└── ServerError(status_code, message)
```

### Hybrid design pattern (note)

taskdog uses **`@dataclass` for domain entities + Pydantic `BaseModel` for DTOs**. Avoids validation overhead in the domain layer. Mirrors a pattern life could adopt for `src/contracts/` (currently Pydantic everywhere is heavier than necessary for hot-path domain logic).

---

## Database schema + migrations

### Stack
- **ORM:** SQLAlchemy 2.0 (`mapped_column`, `Mapped` typing) — `models/task_model.py:9-17`
- **Migrations:** Alembic — `pyproject.toml:21` (`alembic>=1.13.0`)
- **Engine factory:** `infrastructure/persistence/database/engine_factory.py:19-58` — enables WAL, busy_timeout=30000, synchronous=NORMAL, foreign_keys=ON
- **Auto-migration on startup:** `engine_factory.py:54-56` calls `run_migrations(engine)` once per engine; thread-safe via `migration_runner.py:23` (`_migration_lock`)
- **Existing DB stamping:** `migration_runner.py:111-114` — if `tasks` table exists but no `alembic_version`, stamps with `001_initial` (avoids destructive re-creation). Robust against pre-existing DBs — pattern life could adopt for `data/vibe_ops.db` (currently `user_version=0` per Phase 1 B-05).

### Tables (5)

| Table | ORM Model | Migration | Purpose |
|-------|-----------|-----------|---------|
| `tasks` | `task_model.py:24-101` | `001_initial_schema.py:36-66` | Main entity; 17 columns; 5 indexes (`idx_status`, `idx_is_archived`, `idx_deadline`, `idx_planned_start`, `idx_priority`) |
| `tags` | `tag_model.py:22-58` | `001_initial_schema.py:69-78` | Normalized tag names (unique) |
| `task_tags` | `tag_model.py:61-93` | `001_initial_schema.py:81-91` | M:N junction (composite PK) |
| `audit_logs` | `audit_log_model.py:19-92` | `001_initial_schema.py:94-125` | Audit trail; 8 indexes (5 single + 3 composite) |
| `notes` | `note_model.py:19-52` | `004_add_notes_table.py:42-54` | DB-backed notes (PK=task_id FK, CASCADE) — replaced filesystem storage |
| `daily_allocations` | `daily_allocation_model.py:24-78` | `005_add_daily_allocations_table.py:55-?` | Normalized allocations (was JSON in tasks); UNIQUE(task_id,date); FK CASCADE |

### Migration chain (`migrations/versions/`)

```
001_initial_schema  (2025-12-26)        ← creates tasks, tags, task_tags, audit_logs
  ↓
002_remove_actual_daily_hours
  ↓
003_make_priority_nullable  (2026-01-24)
  ↓
004_add_notes_table  (2026-01-29)
  ↓
005_add_daily_allocations_table  (2026-02-01)
  ↓
006_remove_daily_allocations_json  (2026-02-01)  ← drops tasks.daily_allocations JSON col
```

`001_initial_schema.py:30-32` uses conditional creation (`if "tasks" not in existing_tables`) — supports both fresh DB and existing-DB bring-under-version-control.

### Repository layer

- `sqlite_task_repository.py:50-82` — `SqliteTaskRepository(SqliteBaseRepository, TaskRepository)` — full CRUD
- `sqlite_notes_repository.py`, `sqlite_audit_log_repository.py`, `sqlite_backup_store.py`
- **Mutation builders:** `mutation_builders/task_{insert,update,delete}_builder.py`, `daily_allocation_builder.py`, `task_tag_relationship_builder.py`
- **Query builder:** `query_builders/task_query_builder.py`
- **Mappers:** `mappers/task_db_mapper.py` (Task ↔ TaskModel), `mappers/tag_resolver.py` (tag normalization)

### DB path resolution

DB lives at `~/.local/share/taskdog/tasks.db` (`XDGDirectories.get_data_home()` per `dependencies.py:60`) — completely independent from `data/vibe_ops.db` (B-05). No interference.

---

## MCP tool inventory (taskdog-mcp)

**Transport:** stdio (FastMCP default — `main.py:31 mcp.run()` with no transport arg). HTTP transport **not** wired. Phase 1 audit OQ-8 ("Two MCP transports") applies: this MCP server is **stdio-only**; gateway talks to it via stdio subprocess.

**Registration:** `server.py:42-58` calls `register_tools(mcp, client)` on 7 tool modules. Each module uses `@instrumented_tool(mcp=mcp, name="..."")` (`observability.py:140-185`) which decorates with `@mcp.tool(name=name)`. JSON-RPC handlers delegated to `mcp.server.fastmcp.FastMCP` (mcp library v1.2+).

**Error handling:** tool functions raise `ValueError` directly (`task_lifecycle.py:140`, `task_optimization.py:65`). Domain errors propagate from `taskdog_client` calls (e.g., `TaskNotFoundException`, `TaskValidationError`). FastMCP converts to MCP error responses.

**Total MCP tools exposed: 26**

### CRUD (6) — `tools/task_crud.py`
| Tool | Params | Returns | Client call |
|------|--------|---------|-------------|
| `list_tasks` | include_archived, status, tags, sort_by, reverse | `{tasks:[...], total:int}` | `client.list_tasks(...)` |
| `get_task` | task_id | task dict incl. notes_content | `client.get_task_detail(task_id)` |
| `create_task` | name, priority?, deadline?, estimated_duration?, tags?, is_fixed?, planned_start?, planned_end? | task_result | `client.create_task(...)` |
| `update_task` | task_id, name?, ... (same optional fields as create) | task_result | `client.update_task(...)` |
| `delete_task` | task_id, hard=False | if hard → "permanently deleted"; else → archived msg | `client.remove_task` or `client.archive_task` |
| `restore_task` | task_id | task_result | `client.restore_task(task_id)` |

### Lifecycle (6) — `tools/task_lifecycle.py:18-159`
`start_task` (`task_lifecycle.py:26`), `complete_task` (`:45`), `pause_task` (`:65`), `cancel_task` (`:80`), `reopen_task` (`:95`), `fix_actual_times` (`:110`, with `clear_start/clear_end/clear_duration` flags).

### Query (3) — `tools/task_query.py`
`get_statistics` (period="all"/"7d"/"30d"), `get_tag_statistics`, `get_executable_tasks` (combines IN_PROGRESS + PENDING by priority desc).

### Decomposition + Relationships + Notes (6) — `tools/task_decomposition.py:78-298`
`decompose_task`, `add_dependency`, `remove_dependency`, `set_task_tags`, `update_task_notes`, `get_task_notes`.

### Tags (1) — `tools/task_tags.py:18-43`
`delete_tag`.

### Audit (2) — `tools/task_audit.py:18-109`
`list_audit_logs` (filters: task_id, operation, client_name, since, until, failed, limit=50), `get_audit_log`.

### Optimization (2) — `tools/task_optimization.py:19-142`
`optimize_schedule` (algorithm, max_hours_per_day, start_date?, task_ids?, force_override=False, include_all_days=False), `list_algorithms`.

**Algorithms exposed (9):** greedy, balanced, backward, priority_first, earliest_deadline, round_robin, dependency_aware, genetic, monte_carlo (per `task_optimization.py:44-47` and `application/services/optimization/`).

### Serializers (`tools/serializers.py:9-47`)
Shared response builders: `iso(dt)`, `parse_iso_datetime(s, field_name)`, `str_list(v)`, `task_result(task, msg, **extra)`.

---

## Gateway routing match matrix

**Source:** `C:/Users/mathe/code_space/apps/mcp-gateway/config/gateways.yaml:7-10`

```yaml
- name: taskdog
  command: ["python", "-m", "taskdog_mcp.main"]
  cwd: "C:/Users/mathe/code_space/apps/dev-tools/taskdog"        # STALE (B-01)
  tool_prefixes: ["taskdog_", "list_tasks", "get_task", "create_task",
                   "update_task", "delete_task", "archive_task", "restore_task"]
```

### Prefix-by-prefix match against actual MCP tools

| Gateway expects | Actual MCP tool name | Exposed? | Notes |
|-----------------|---------------------|----------|-------|
| `taskdog_*` (wildcard) | (none — all tools are unprefixed) | NO MATCH | No tool registered with `taskdog_` prefix in any module |
| `list_tasks` | `list_tasks` (`task_crud.py:31`) | MATCH | CRUD module |
| `get_task` | `get_task` (`task_crud.py:75`) | MATCH | CRUD module |
| `create_task` | `create_task` (`task_crud.py:104`) | MATCH | CRUD module |
| `update_task` | `update_task` (`task_crud.py:150`) | MATCH | CRUD module |
| `delete_task` | `delete_task` (`task_crud.py:201`) | MATCH | CRUD module (MCP tool, NOT REST endpoint `archive_task`) |
| `archive_task` | **NO SUCH TOOL** | NO MATCH | MCP exposes `delete_task(hard=False)` which calls `client.archive_task` REST endpoint, but the MCP tool name is `delete_task`, not `archive_task` |
| `restore_task` | `restore_task` (`task_crud.py:221`) | MATCH | CRUD module |

### Tools exposed by taskdog-mcp but NOT in gateway prefix list (20 unreachable)

`start_task` (`task_lifecycle.py:26`), `complete_task` (`:45`), `pause_task` (`:65`), `cancel_task` (`:80`), `reopen_task` (`:95`), `fix_actual_times` (`:110`), `get_statistics` (`task_query.py:26`), `get_tag_statistics` (`:54`), `get_executable_tasks` (`:70`), `decompose_task` (`task_decomposition.py:81`), `add_dependency` (`:190`), `remove_dependency` (`:212`), `set_task_tags` (`:231`), `update_task_notes` (`:254`), `get_task_notes` (`:271`), `delete_tag` (`task_tags.py:25`), `list_audit_logs` (`task_audit.py:26`), `get_audit_log` (`:85`), `optimize_schedule` (`task_optimization.py:27`), `list_algorithms` (`:123`).

### Issues identified

1. **`taskdog_*` prefix is dead** — gateway expects `taskdog_*` prefix matching, but **no MCP tool uses this prefix**. Either gateway config is wrong or taskdog-mcp was meant to expose `taskdog_*` tools and never did.
2. **`archive_task` mismatch** — gateway expects tool name `archive_task`; MCP exposes `delete_task(hard=False)`. Gateway will never match this tool.
3. **20 of 26 MCP tools unreachable** — even if cwd is fixed (Phase 1 B-01), the gateway prefix list omits lifecycle, query, decomposition, tags, audit, optimization tools entirely.
4. **No HTTP transport** — taskdog-mcp is stdio-only; gateway must launch as subprocess and communicate over stdio JSON-RPC. No HTTP/SSE fallback.

---

## Client API surface

### Public facade (`taskdog_api_client.py:41-456`)
Single `TaskdogApiClient` class with constructor `base_url="http://127.0.0.1:8000"`, `timeout=30.0`, `api_key=None` (line 48-53). Context-manager protocol (line 114-120). Holds 9 specialized clients via `BaseApiClient` (line 65-73). **50+ public methods** delegating to specialized clients.

### Specialized client classes (`taskdog_client/__init__.py:8-17`)

| Class | File | Responsibility |
|-------|------|----------------|
| `BaseApiClient` | `base_client.py:24` | httpx wrapper, error→exception mapping (404/400/422/401/5xx), `X-Client-ID` + `X-Api-Key` headers (`auth_headers()`, line 52-63) |
| `TaskClient` | `task_client.py` | CRUD: create/update/archive/restore/remove |
| `LifecycleClient` | `lifecycle_client.py` | start/complete/pause/cancel/reopen/fix_actual_times |
| `RelationshipClient` | `relationship_client.py` | dep add/remove, set_task_tags, delete_tag |
| `QueryClient` | `query_client.py` | list_tasks/get_by_id/get_detail/get_gantt_data/tag_statistics |
| `AnalyticsClient` | `analytics_client.py` | calculate_statistics, optimize_schedule, get_algorithm_metadata |
| `NotesClient` | `notes_client.py` | get/update/delete task notes |
| `AuditClient` | `audit_client.py` | list_audit_logs, get_audit_log |
| `BulkClient` | `bulk_client.py` | bulk_start/complete/pause/cancel/reopen/archive/restore/delete |
| `BackupClient` | `backup_client.py` | backup (download DB), restore (upload DB) |

### HTTP request/response shapes
- **Req shape:** httpx verbs; `_request_json(method, *args, **kwargs)` at `base_client.py:159-182`; errors mapped to domain exceptions in `taskdog_core.domain.exceptions.task_exceptions` (line 15-21)
- **Res shape:** dicts → Pydantic DTOs via `converters/task_converters.py:_model_validate` (line 18-40) wrapping `ValidationError` as `ConversionError`; DTOs from `taskdog_core.application.dto.*` (12 imports at `taskdog_api_client.py:23-37`)

### WebSocket client (`websocket/websocket_client.py:36-204`)
Appends `?token=<api_key>` query param (line 63-66), connects via `websockets.connect()` (line 176), processes `type=connected` to capture `client_id` (line 138-140), exponential backoff reconnect 1.0s→30.0s (line 171-172).

**Webhook message types handled** (server-side, echoed in client contract per `event_handler_registry.py:54-62`): `connected`, `task_created`, `task_updated`, `task_deleted`, `task_status_changed`, `schedule_optimized`, `bulk_operation_completed`.

**Drift risk:** Client uses DTOs from `taskdog_core.application.dto.*` (`taskdog_api_client.py:23-37` — 12 imports). NO parallel local contracts in client/server/ui. Drift risk lives in `taskdog-core`/`taskdog-mcp`.

---

## Server components

`taskdog-server` IS the non-MCP server — provides HTTP + WebSocket. (MCP package is a separate wrapper.)

### FastAPI app construction (`api/app.py:37-121`)
- **Lifespan** (line 47-82): loads config → `configure_logging()` → `apply_pending_restore()` → `initialize_api_context()` → stores `api_context`, `server_config`, `ConnectionManager()` in `app.state`
- **Middleware:** `LoggingMiddleware` first (line 92) — BaseHTTPMiddleware, logs method/path/status/process_time_ms
- **Exception handlers:** `register_exception_handlers(app)` (line 95) — domain exceptions → HTTP responses

### Routers registered (10, line 98-109)

| Router | Prefix | Tags |
|--------|--------|------|
| `tasks.py` | `/api/v1/tasks` | tasks |
| `bulk.py` | `/api/v1/tasks` | bulk |
| `lifecycle.py` | `/api/v1/tasks` | lifecycle |
| `relationships.py` | `/api/v1/tasks` | relationships |
| `notes.py` | `/api/v1/tasks` | notes |
| `analytics.py` | `/api/v1` | analytics |
| `tags.py` | `/api/v1/tags` | tags |
| `audit.py` | `/api/v1/audit-logs` | audit |
| `backup.py` | `/api/v1` | backup |
| `websocket.py` | (no prefix) | websocket |

### Endpoint inventory (key routes)

| Method | Path | Handler |
|--------|------|---------|
| POST | `/api/v1/tasks` | create (`tasks.py:38`) |
| GET | `/api/v1/tasks` | list with filters (`tasks.py:92`): `all/status/tags/start_date/end_date/sort/reverse/include_gantt/gantt_start_date/gantt_end_date` |
| GET | `/api/v1/tasks/{task_id}` | detail (`tasks.py:167`) |
| PATCH | `/api/v1/tasks/{task_id}` | update (`tasks.py:189`) |
| POST | `/api/v1/tasks/{task_id}/archive` | archive (`tasks.py:251`) |
| POST | `/api/v1/tasks/{task_id}/restore` | restore (`tasks.py:291`) |
| DELETE | `/api/v1/tasks/{task_id}` | delete (`tasks.py:331`) |
| POST | `/api/v1/tasks/{task_id}/{start\|complete\|pause\|cancel\|reopen}` | lifecycle ops (enum loop, `lifecycle.py:50,81`) |
| POST | `/api/v1/tasks/{task_id}/fix-actual` | fix times (`lifecycle.py`) |
| GET/PUT/DELETE | `/api/v1/tasks/{task_id}/notes` | notes (`notes.py:17,41,86`) |
| POST | `/api/v1/tasks/{task_id}/dependencies` | dep add (`relationships.py:21`) |
| DELETE | `/api/v1/tasks/{task_id}/dependencies/{dep_id}` | dep remove (`relationships.py:62`) |
| PUT | `/api/v1/tasks/{task_id}/tags` | set tags (`relationships.py:105`) |
| DELETE | `/api/v1/tags/{tag_name}` | delete tag (`tags.py:15`) |
| GET | `/api/v1/analytics/statistics` | stats (`analytics.py:52`) |
| GET | `/api/v1/analytics/tag-statistics` | tag stats (`analytics.py:193`) |
| GET | `/api/v1/analytics/gantt` | gantt (`analytics.py:219`) |
| POST | `/api/v1/analytics/optimize` | schedule optimize (`analytics.py:289`) |
| GET | `/api/v1/analytics/algorithms` | algorithm metadata (`analytics.py:402`) |
| GET | `/api/v1/audit-logs` | list (`audit.py:18`) |
| GET | `/api/v1/audit-logs/{log_id}` | get (`audit.py:111`) |
| GET | `/api/v1/backup` | download DB (`backup.py:22`) |
| POST | `/api/v1/backup/restore` | upload DB (`backup.py:37`) |
| WS | `/ws?token=…` | websocket (`websocket.py:20`) — ping/pong only (line 83-86); broadcasts via `manager.send_personal_message`/`broadcast` |

### Side effects on every write (`tasks.py` pattern, lines 75, 234, 277, 317, 357)
1. `broadcaster.task_created/updated/deleted(...)` — BackgroundTasks fanout
2. `log_task_operation(...)` via `audit_helpers.py` — appends to `SqliteAuditLogRepository`

### WebSocket message types (server → client)
`task_created`, `task_updated`, `task_deleted`, `task_status_changed`, `schedule_optimized`, `bulk_operation_completed`. Client→server messages are limited to `ping/pong` (`routers/websocket.py:78-87`); all data flow is server→client.

### Dependency injection (`api/dependencies.py:64-141`)
`initialize_api_context()` constructs 9 controllers (`QueryController`, `TaskLifecycleController`, `TaskRelationshipController`, `TaskAnalyticsController`, `TaskCrudController`, `AuditLogController`, `NotesController`, `BulkTaskController`, `BackupController`) — all from `taskdog_core.controllers.*`. Single shared SQLAlchemy engine (line 91).

---

## UI components

### CLI (Click + LazyGroup)
- **Root:** `cli_main.py:131-200` — `TaskdogGroup` (line 110) extends `LazyGroup`; `format_help` injects ASCII art before help (line 113-128)
- **22 lazy subcommands** (`cli_main.py:20-104`) — import deferred to keep startup fast (line 12-19). This is a deliberate perf pattern, not a bug.
- **Aliases:** `ls → list` (line 107)
- **Global options:** `-H/--host`, `-p/--port`, `-k/--api-key` (line 139-159); override `load_cli_config()` (line 176-178)
- **Context init:** creates `TaskdogApiClient` and stores in `CliContext` (line 184-195)
- **Entry-point:** `taskdog = "taskdog.cli_main:cli"` (`pyproject.toml:44`) — **POSITIVE reference** for fixing the orphan `interfaces/cli` entry-point (Phase 1 P1 #8). Has working `[server]` extra (line 39-41) for bundling.

### CLI subcommand inventory
**Top-level** (`cli/commands/*.py`): `add`, `cancel`, `done`, `export`, `fix_times`, `gantt`, `list`, `note`, `optimize`, `pause`, `reopen`, `restore`, `rm`, `show`, `start`, `stats`, `timeline`, `update`, `tui`, plus `common_options.py`, `table_helpers.py`. **Noun subgroups**: `audit/list.py`, `db/backup.py|restore.py`, `dep/add.py|remove.py`, `tag/list.py|set.py|remove.py`.

### TUI (Textual)

**Entry:** `cli/commands/tui.py` → `tui_command` invokes Textual app.

**App composition** (`tui/app.py:13-53`):
- Imports `TaskdogApiClient`, `WebSocketClient` (line 21), `TUIState`, `ConnectionStatusManager`, `TaskUIManager`, `WebSocketHandler`, `ConnectionMonitor`, `MainScreen`, palette providers, command factory
- `CommandFactory` (line 27) — action→command dispatch table from `constants/command_mapping.py:ACTION_TO_COMMAND_MAP` (line 28)

**Screens** (`tui/screens/`):
- `main_screen.py:24-220` — `MainScreen(Screen[None])`; composes Header + Vertical(GanttWidget, TaskTable) + CustomFooter (line 62-84); bindings Ctrl+J/K for focus nav (line 30-47); handlers for `SearchQueryChanged`/`FilterChanged` (debounced 0.15s timer line 115-117), `CustomFooter.Submitted`, `CustomFooter.RefineFilter`
- `audit_log_screen.py` — secondary screen for audit log review

**Widgets** (`tui/widgets/`):
`task_table.py` (main DataTable), `gantt_widget.py` + `gantt_data_table.py` (gantt display, consumes `TaskGanttRowViewModel`), `custom_footer.py` (search input + filter chain display), `task_search_filter.py` + `search_query_parser.py` (query DSL), `task_table_row_builder.py`, `audit_log_table.py` + `audit_log_entry_builder.py`, `vi_navigation_mixin.py` + `vi_select.py` (vim-style nav), `base_widget.py`.

**State** (`tui/state/`):
`tui_state.py:22-246` — `TUIState` dataclass (Single Source of Truth); 7 fields (sort_by/reverse, current_query, filter_chain, gantt_filter_enabled, show_archived, viewmodels_cache, gantt_cache); methods `set_filter/add_to_filter_chain/clear_filters/toggle_gantt_filter`; computed props `is_filtered/filtered_task_ids/filtered_viewmodels/match_count/total_count/filtered_gantt`. Plus `connection_status.py` + `connection_status_manager.py` (connection state tracking).

**Services** (`tui/services/`):
- `task_ui_manager.py:56-321` — `TaskUIManager` orchestrates load (gathers params → fetches on worker thread → applies on UI thread); `FetchParams`/`GanttFetchParams` dataclasses; methods `load_tasks/gather_fetch_params/fetch_with_params/apply_task_data/gather_gantt_params/fetch_gantt/apply_gantt`; error fanout to callback (line 90-99)
- `websocket_handler.py:16-52` — `WebSocketHandler.handle_message()` → `EventHandlerRegistry.dispatch()`
- `event_handler_registry.py:22-227` — registry of 7 message types → handlers; `_handle_task_event` shared pattern (line 86-115); `_get_display_source` (line 175-196) suppresses self-events
- `connection_monitor.py:15-42` — background `run_worker` for health checks (line 36, 40)

**Commands** (`tui/commands/`) — palette/command factory. **Palette providers** (`tui/palette/providers/`) — 10 providers (archive/audit/backup/export/gantt_filter/help/optimize/sort/stats). **Dialogs** (`tui/dialogs/`), **Forms** (`tui/forms/` with `suggesters/` and `validators/`), **Styles** (`tui/styles/*.tcss`).

---

## OTel instrumentation

**KEY FINDING:** OTel instrumentation exists **only in taskdog-mcp**. Zero instrumentation in client, server, or UI.

### Where OTel lives
`taskdog-mcp/build/lib/taskdog_mcp/observability.py:1-191` defines `instrumented_tool(mcp, name)` decorator using `opentelemetry.sdk.trace.TracerProvider` (line 21, 70) + `OTLPSpanExporter` (line 72); wraps each MCP tool at `taskdog-mcp/.../tools/task_crud.py:31,75,104,150,201` and `task_audit.py:26,85`. Optional LangSmith + Langfuse exporters via OTLP/HTTP (gated by env vars).

### Negative evidence
- `grep -rn 'opentelemetry|otel|tracer|span' taskdog-client/src` → 0 hits
- `grep -rn 'opentelemetry|otel|tracer|span' taskdog-server/src` → 0 hits
- `grep -rn 'opentelemetry|otel|tracer|span' taskdog-ui/src` → 0 hits
- `pyproject.toml` files: NO `opentelemetry-*` deps in client/server/ui (only in `taskdog-mcp/pyproject.toml:21-27`)

### What server has instead
- `LoggingMiddleware` (`api/middleware.py:13-83`) — logs method/path/status/process_time_ms via standard `logging` module, no spans
- `configure_logging()` (`infrastructure/logging/config.py`) — plain logging config

**Implication for Phase 3:** If OTel traceability is required for HTTP traffic, must extend server (FastAPI instrumentation) and TUI CLI (manual spans). Currently **ZERO observability between HTTP boundary and DB**. This is a meaningful asymmetry — MCP-tool calls are traced, but the HTTP server calls those MCP tools wrap are not.

---

## Trade-offs

1. **5-package workspace vs monolith.** taskdog-core is the source of truth (entities + DTOs + repos + controllers); taskdog-server, taskdog-client, taskdog-mcp, taskdog-ui each pin to `taskdog-core==0.23.0`. PV pinning forces atomic upgrades. Trade-off: clean separation of concerns vs tight version coupling.

2. **`@dataclass` domain + Pydantic DTO hybrid.** taskdog uses plain `@dataclass` for `Task` (domain) and Pydantic `BaseModel` for DTOs (application boundary). Avoids validation overhead in domain. Trade-off: two model definitions per concept (one internal, one wire).

3. **3-tier architecture: mcp → http → server → controller → use_case → repo.** taskdog-mcp does NOT call controllers directly — it calls `taskdog_client` (HTTP to taskdog-server FastAPI). Adds latency for agent use cases. Trade-off: clean separation vs extra round-trip. life should consider whether MCP server should call Pydantic contracts directly (skipping HTTP layer) for low-latency agent use cases.

4. **Gateway prefix mismatch is THE integration blocker.** Fixing B-01 alone doesn't make tools routable; gateway prefix list must be expanded to cover all 26 tools, OR the gateway dispatcher must auto-prefix at backend-name boundary (`taskdog.list_tasks` becomes virtual `taskdog_list_tasks`).

5. **26-tool surface with 20 unreachable.** 20 of 26 MCP tools are unreachable via gateway due to prefix list gaps. Lifecycle, query, decomposition, tags, audit, optimization all need prefix additions.

6. **`delete_task(hard=False)` vs `archive_task` semantic mismatch.** Gateway expects `archive_task`; MCP exposes `delete_task(hard=False)`. This is a naming inconsistency that the gateway cannot resolve automatically.

7. **Alembic with conditional table creation + DB-stamping** (`migration_runner.py:111-114`). Robust against pre-existing DBs. Trade-off: more complex migration runner code. life could adopt this pattern for `data/vibe_ops.db` (currently `user_version=0` per Phase 1 B-05).

8. **`LazyGroup` startup optimization.** `cli_main.py:12-19` explains deferred imports to avoid dragging in `rich.markdown`, `markdown_it`, `textual` for `--help`. NOT a bug; a deliberate perf pattern. Other forks could adopt.

9. **Audit trail is SQLite-backed.** `dependencies.py:106` wires `SqliteAuditLogRepository`; `audit_helpers.py:capture_old_task`/`diff_task_fields`/`log_task_operation` invoked on every write (`tasks.py:77, 239, 279, 319, 359`). Trade-off: queryable audit, but DB size grows over time (no vacuum strategy documented).

10. **OTel asymmetry.** Only MCP tools instrumented, not HTTP server. Trade-off: easy wire-up at MCP boundary, but no visibility into server→DB calls. Phase 3 must add FastAPI instrumentation if end-to-end traces are required.

11. **WebSocket is bidirectional but client→server messages are limited.** Server `routers/websocket.py:78-87` only handles `ping/pong`; all data flow is server→client. Trade-off: simpler broadcast model, but no interactive WS calls.

12. **Single-source-of-truth for tasks.** taskdog has 1 SQLite file (5 tables) + DB-resident notes (replaced filesystem); single-source-of-truth for that concern. Adding taskdog as a new store means **one additional store** in the mesh (per `02-critic-gaps.md`: "3 storage roots enumerated, 7 stores total").

---

## Cross-references

### Inputs read
- PART reports: `02a-taskdog-core-mcp-REPORT.md` (core + mcp scope), `02b-taskdog-client-ui-REPORT.md` (client + server + ui scope)
- Phase 1 forensic audit: `docs/diagnostics/2026-08-28-phase1-audit/00-INDEX.md`, `01-verified.md` B-01, `02-critic-gaps.md`, `05-open-questions.md` OQ-1/OQ-3/OQ-5/OQ-8/OQ-9
- Phase 2 sister docs: `01-fork-tuiboard.md` (fork #1), `03-fork-solverforge-calendar.md` (fork #3), `04-interfaces-cli.md`, `05-interfaces-tui.md`
- Gateway config (Phase 1 finding B-01): `C:/Users/mathe/code_space/apps/mcp-gateway/config/gateways.yaml:1-16`
- Gateway router: `apps/mcp-gateway/src/mcp_gateway/router.py:4-25`
- Gateway process manager: `apps/mcp-gateway/src/mcp_gateway/process_manager.py:8-47`

### Phase 1 audit connections

| Phase 1 item | Relevance |
|--------------|-----------|
| **B-01** gateways.yaml STALE cwd | `gateways.yaml:9` says `cwd: "C:/Users/mathe/code_space/apps/dev-tools/taskdog"` — **does not exist**. Real path: `C:/Users/mathe/code_space/life-oss/interfaces/taskdog/packages/taskdog-mcp/`. Gateway lives at `C:\Users\mathe\code_space\apps\mcp-gateway\` (sibling of `life-oss/`, not inside `life/`). Fix requires repointing `cwd` AND Python module path — `taskdog-mcp` is at `packages/taskdog-mcp/src/taskdog_mcp/`, so `python -m taskdog_mcp.main` only works if cwd is `packages/taskdog-mcp/`. |
| **OQ-8** Two MCP transports | taskdog-mcp is stdio-only (FastMCP default at `main.py:31`). Gateway talks via stdio subprocess. No HTTP transport here. Compare with solverforge-calendar MCP at `interfaces/solverforge-calendar/src/bin/solverforge-calendar-mcp.rs:878-905` which has dual stdio+HTTP+SSE (HTTP feature-gated stub). |
| **OQ-3** tasks.jsonl THE MESH INTERCHANGE | taskdog uses SQLite (`engine_factory.py` + 6 migrations) for tasks — does NOT touch `tasks.jsonl` from `interfaces/cli/read_tasks.py`. Independent storage topology. |
| **OQ-1** Storage topology | taskdog stores in user-XDG path (`mcp_config_manager.py:73 XDGDirectories.get_config_home() / "mcp.toml"`); SQLite DB path controlled by repo factory (`repository_factory.py`). Pattern C (config-driven) — relevant precedent for life. |
| **OQ-2** Contracts naming | taskdog uses **Pydantic v2 in `application/dto/`** (data contracts) **+ SQLAlchemy ORM in `infrastructure/persistence/database/models/`** (persistence contracts) — two distinct layers, each named for its role. Life's `src/contracts/` (Pydantic only) is more like taskdog's `application/dto/` subset. |
| **OQ-5** Federation vs single source | taskdog has 1 SQLite file (5 tables) + DB-resident notes (replaced filesystem); single-source-of-truth for that concern. |
| **OQ-9** 4 stub workflows | N/A — taskdog has no LangGraph; pure Python controllers + use cases. |
| **02-critic-gaps.md** P0 #3 | `src/ikigai/mcp_config.json` Windows-unrunnable. References pre-reorg `apps/dev-tools/taskdog` cwd. Real location for THIS fork: `C:\Users\mathe\code_space\life-oss\interfaces\taskdog\packages\taskdog-server\` (entry: `taskdog_server.api.app:app`, `server/main.py:64-70`). |
| **02-critic-gaps.md** P0 #4 | Root CLI architectural lie — relates to `life/cli` ↔ `vibe-ops`, NOT taskdog. Taskdog's CLI→HTTP chain IS a real subprocess split. |
| **02-critic-gaps.md** P1 #8 | `interfaces/cli` broken entry-point — taskdog-ui has WORKING entry-point at `pyproject.toml:44` (`taskdog = "taskdog.cli_main:cli"`) + has `__init__.py` at `src/taskdog/__init__.py`. POSITIVE reference for fixing the orphan `interfaces/cli`. |

### Phase 2 fork connections
- **tuiboard** (fork #1) — independent; gateway uses `taskdog_*` prefixes vs tuiboard's `board_*`; no collision
- **solverforge-calendar** (fork #3) — gateway uses `taskdog_*` prefixes vs solverforge's `calendars_/events_/projects_/dependencies_/google_/upi_`; no collision. Solverforge MCP has dual stdio+HTTP transport (HTTP stub) while taskdog-mcp is stdio-only.
- **interfaces/cli** (Phase 2 diagnostic #4) — broken entry-point per Phase 1 audit; taskdog-ui sidesteps this with working entry-point + LazyGroup startup optimization

### Architectural notes for Phase 3 brainstorm
- **Pydantic v2 + dataclass hybrid:** taskdog uses `@dataclass` for domain entities (Task) and Pydantic `BaseModel` for DTOs. Mirrors life's choice (Pydantic everywhere is heavier).
- **3-tier MCP architecture:** mcp → http → server → controller → use_case → repo. Could be flattened to mcp → controller for low-latency agent use cases.
- **Alembic with DB-stamping:** robust pattern against pre-existing DBs. life should consider for `data/vibe_ops.db`.
- **Gateway prefix mismatch is THE integration blocker.** Fixing B-01 alone doesn't make tools routable; gateway prefix list must be expanded to cover all 26 tools.

### Memory references
- [[interfaces-architecture-2026-08-27]] — confirms taskdog fork is user-view, not source-of-truth
- [[windows-orphan-dir-delete]] — used 2026-08-28 to clear `apps/dev-tools/taskdog` (the OLD location Phase 1 B-01 says is missing)
- [[orchestration-clone-playground]] — confirms taskdog is a vendored MIT fork from Kohei Wada

### Pitfalls noted
- `gateways.yaml:9` cwd path is stale — fork actually lives at `life-oss/interfaces/taskdog/packages/taskdog-mcp/`
- Gateway expects `archive_task`; MCP exposes `delete_task(hard=False)` — naming mismatch
- `taskdog_*` prefix in gateway config matches NO tools (all MCP tools are unprefixed)
- 20 of 26 MCP tools are unreachable through current gateway prefix list
- `controllers/__init__.py:1-13` only re-exports 4 of 11 controllers — package design gap
- OTel is MCP-only; HTTP server has zero instrumentation
- `taskdog-mcp` is stdio-only — no HTTP transport wired

---

DONE C:/Users/mathe/code_space/life-oss/life/docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md: 462 lines
